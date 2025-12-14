import io
import os
import shutil
import zipfile
import logging
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from .constant import Language, SubmissionMode
from .meta import Meta
from .asset_cache import ensure_custom_asset, AssetNotFoundError
from runner.submission import SubmissionRunner


class BuildStrategyError(ValueError):
    """Raised when a build strategy cannot be applied."""


_LANG_KEYS = {
    Language.C: "c11",
    Language.CPP: "cpp17",
    Language.PY: "python3",
}


@dataclass
class BuildPlan:
    needs_make: bool
    lang_key: Optional[str] = None
    finalize: Optional[Callable[[], None]] = None


def prepare_interactive_teacher_artifacts(
    problem_id: int,
    meta: Meta,
    submission_dir: Path,
) -> None:
    """
    Unified teacher artifact preparation for interactive mode.
    1. Fetch teacher source
    2. Extract to submission_dir/teacher
    3. Compile if needed
    """
    try:
        _prepare_teacher_artifacts(
            problem_id=problem_id,
            meta=meta,
            submission_dir=submission_dir,
        )
    except Exception as exc:
        raise BuildStrategyError(
            f"failed to prepare teacher artifacts: {exc}") from exc


def prepare_make_normal(
    meta: Meta,
    submission_dir: Path,
) -> BuildPlan:
    return _build_plan_for_student_artifacts(
        language=meta.language,
        src_dir=submission_dir / "src" / "common",
    )


def prepare_make_interactive(
    problem_id: int,
    meta: Meta,
    submission_dir: Path,
) -> BuildPlan:
    """
    Interactive handler: prepares teacher, then validates student code/zip.
    - ZIP: python requires main.py; C/C++ requires Makefile (strict CE)
    - CODE: direct compile (needs_make=False)
    """
    prepare_interactive_teacher_artifacts(
        problem_id=problem_id,
        meta=meta,
        submission_dir=submission_dir,
    )

    src_dir = submission_dir / "src" / "common"
    language = Language(meta.language)
    submission_mode = SubmissionMode(meta.submissionMode)

    if submission_mode == SubmissionMode.ZIP:
        if language == Language.PY:
            if not (src_dir / "main.py").exists():
                raise BuildStrategyError(
                    "interactive zip requires main.py for python submissions")
            return BuildPlan(needs_make=False)
        # C/C++ strict Makefile requirement
        if not (src_dir / "Makefile").exists():
            raise BuildStrategyError(
                "interactive zip requires Makefile for C/C++ submissions")
        return _build_plan_for_student_artifacts(
            language=language,
            src_dir=src_dir,
        )

    # CODE upload: compile directly, no make
    return BuildPlan(needs_make=False)


def prepare_function_only_submission(
    problem_id: int,
    meta: Meta,
    submission_dir: Path,
) -> BuildPlan:
    src_dir = submission_dir / "src" / "common"
    student_path = _student_entry_path(src_dir=src_dir, language=meta.language)
    if not student_path.exists():
        raise BuildStrategyError("student source not found")
    student_code = student_path.read_text()
    make_asset = meta.assetPaths.get("makefile")
    if not make_asset:
        raise BuildStrategyError("functionOnly mode requires makefile asset")
    makefile_asset = Path(make_asset).name if make_asset else "makefile.zip"
    try:
        archive_path = ensure_custom_asset(problem_id,
                                           "makefile",
                                           filename=makefile_asset)
    except AssetNotFoundError as exc:
        raise BuildStrategyError(str(exc)) from exc
    except Exception as exc:
        raise BuildStrategyError(f"failed to fetch makefile: {exc}") from exc
    _reset_directory(src_dir)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(src_dir)
    template_name = ("function.h" if meta.language
                     in (Language.C, Language.CPP) else "student_impl.py")
    template_path = src_dir / template_name
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(student_code)

    def finalize():
        _finalize_function_only_artifacts(src_dir=src_dir,
                                          language=meta.language)

    return BuildPlan(
        needs_make=True,
        lang_key=_lang_key(meta.language),
        finalize=finalize,
    )


def _build_plan_for_student_artifacts(language: Language,
                                      src_dir: Path) -> BuildPlan:
    if language == Language.PY:
        _ensure_main_python(src_dir)
        return BuildPlan(needs_make=False)
    _ensure_makefile(src_dir)

    def finalize():
        _finalize_compiled_binary(src_dir=src_dir, language=language)

    return BuildPlan(
        needs_make=True,
        lang_key=_lang_key(language),
        finalize=finalize,
    )


def _reset_directory(target: Path):
    for child in target.iterdir():
        if child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)


def _student_entry_path(src_dir: Path, language: Language) -> Path:
    suffix = {
        Language.C: ".c",
        Language.CPP: ".cpp",
        Language.PY: ".py",
    }.get(language)
    if suffix is None:
        raise BuildStrategyError(f"unsupported language: {language}")
    return src_dir / f"main{suffix}"


def _ensure_main_python(src_dir: Path):
    entry = src_dir / "main.py"
    if not entry.exists():
        raise BuildStrategyError("main.py not found in submission archive")


def _ensure_makefile(src_dir: Path):
    makefile = src_dir / "Makefile"
    if not makefile.exists():
        raise BuildStrategyError("Makefile not found in submission directory")


def _lang_key(language: Language) -> str:
    try:
        return _LANG_KEYS[Language(language)]
    except (KeyError, ValueError):
        raise BuildStrategyError(f"unsupported language: {language}") from None


def _finalize_compiled_binary(src_dir: Path, language: Language):
    if language not in (Language.C, Language.CPP):
        return
    binary_path = src_dir / "a.out"
    if not binary_path.exists():
        raise BuildStrategyError("a.out not found after running make")
    _ensure_single_executable(src_dir, allowed={"a.out"})
    target = src_dir / "main"
    if target.exists():
        target.unlink()
    os.replace(binary_path, target)
    os.chmod(target, target.stat().st_mode | 0o111)
    if not target.exists():
        raise BuildStrategyError("failed to create main executable")


def _finalize_function_only_artifacts(src_dir: Path, language: Language):
    if language in (Language.C, Language.CPP):
        _finalize_compiled_binary(src_dir=src_dir, language=language)
        return
    entry = src_dir / "main.py"
    if not entry.exists():
        raise BuildStrategyError("main.py not found after running make")


def _ensure_single_executable(src_dir: Path, allowed: Iterable[str]):
    allowed = set(allowed)
    exec_files = [
        item for item in src_dir.iterdir()
        if item.is_file() and os.access(item, os.X_OK)
    ]
    extras = [item for item in exec_files if item.name not in allowed]
    if extras:
        raise BuildStrategyError(
            "only one executable named a.out is allowed in zip submissions")


def _prepare_teacher_artifacts(meta: Meta,
                               submission_dir: Path,
                               problem_id: int | None = None):
    teacher_lang_val = (meta.assetPaths or {}).get("teacherLang")
    teacher_lang_map = {
        "c": Language.C,
        "cpp": Language.CPP,
        "py": Language.PY,
    }
    teacher_lang = teacher_lang_map.get(str(teacher_lang_val or "").lower())
    if teacher_lang is None:
        raise BuildStrategyError("interactive mode requires teacherLang")
    teacher_path = meta.assetPaths.get("teacher_file") if getattr(
        meta, "assetPaths", None) else None
    if not teacher_path:
        raise BuildStrategyError("interactive mode requires Teacher_file")
    # Use teacher/common for compiled teacher artifacts
    teacher_dir = submission_dir / "teacher" / "common"
    parent_dir = submission_dir / "teacher"
    if parent_dir.exists():
        shutil.rmtree(parent_dir)
    teacher_dir.mkdir(parents=True, exist_ok=True)
    teacher_filename = Path(teacher_path).name
    try:
        teacher_asset_path = ensure_custom_asset(
            problem_id=problem_id,
            asset_type="teacher_file",
            filename=teacher_filename,
        )
    except AssetNotFoundError as exc:
        raise BuildStrategyError(str(exc)) from exc
    except Exception as exc:
        raise BuildStrategyError(
            f"failed to fetch teacher file: {exc}") from exc
    ext = {
        Language.C: ".c",
        Language.CPP: ".cpp",
        Language.PY: ".py",
    }.get(teacher_lang)
    if ext is None:
        raise BuildStrategyError("unsupported teacher language")
    src_path = teacher_dir / f"main{ext}"
    src_path.write_bytes(teacher_asset_path.read_bytes())
    # Compile if needed
    if teacher_lang == Language.PY:
        if not src_path.exists():
            raise BuildStrategyError("teacher script missing")
        return
    compile_res = SubmissionRunner.compile_at_path(
        src_dir=str(teacher_dir.resolve()),
        lang=_lang_key(teacher_lang),
    )
    if compile_res.get("Status") != "AC":
        err_msg = compile_res.get("Stderr") or compile_res.get(
            "ExitMsg") or "teacher compile failed"
        logging.getLogger(__name__).error("Teacher compile failed",
                                          extra={
                                              "problem_id": problem_id,
                                              "error": err_msg,
                                          })
        raise BuildStrategyError(
            "Interactive judge program failed to compile. Please contact course staff."
        )
    binary = teacher_dir / "Teacher_main"
    if not binary.exists():
        raise BuildStrategyError("teacher binary missing after compile")
    # also ensure ./main exists for sandbox execution
    main_exec = teacher_dir / "main"
    if not main_exec.exists():
        try:
            os.link(binary, main_exec)
        except Exception:
            try:
                import shutil

                shutil.copy(binary, main_exec)
            except Exception:
                pass
    os.chmod(binary, binary.stat().st_mode | 0o111)
    if main_exec.exists():
        try:
            os.chmod(main_exec, main_exec.stat().st_mode | 0o111)
        except Exception:
            pass


def _resolve_teacher_lang(meta: Meta, teacher_dir: Path) -> Language:
    # priority: assetPaths.teacherLang -> file suffix -> meta.language
    teacher_lang_val = (meta.assetPaths.get("teacherLang") if getattr(
        meta, "assetPaths", None) else None)
    if isinstance(teacher_lang_val, str):
        mapping = {"c": Language.C, "cpp": Language.CPP, "py": Language.PY}
        if teacher_lang_val in mapping:
            return mapping[teacher_lang_val]
    # infer by existing files
    if (teacher_dir / "main.py").exists():
        return Language.PY
    if (teacher_dir / "main.cpp").exists():
        return Language.CPP
    if (teacher_dir / "main.c").exists():
        return Language.C
    return Language(meta.language)
