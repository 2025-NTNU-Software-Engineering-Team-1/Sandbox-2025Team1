import io
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from .constant import Language
from .meta import Meta
from .testdata import fetch_problem_asset


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


def prepare_make_normal(
    meta: Meta,
    submission_dir: Path,
) -> BuildPlan:
    return _build_plan_for_student_artifacts(
        language=meta.language,
        src_dir=submission_dir / "src",
    )


def prepare_make_interactive(
    meta: Meta,
    submission_dir: Path,
) -> BuildPlan:
    return _build_plan_for_student_artifacts(
        language=meta.language,
        src_dir=submission_dir / "src",
    )


def prepare_function_only_submission(
    problem_id: int,
    meta: Meta,
    submission_dir: Path,
) -> BuildPlan:
    src_dir = submission_dir / "src"
    student_path = _student_entry_path(src_dir=src_dir, language=meta.language)
    if not student_path.exists():
        raise BuildStrategyError("student source not found")
    student_code = student_path.read_text()
    make_asset = meta.assetPaths.get("makefile")
    if not make_asset:
        raise BuildStrategyError("functionOnly mode requires makefile asset")
    archive = fetch_problem_asset(problem_id, "makefile")
    _reset_directory(src_dir)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
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
