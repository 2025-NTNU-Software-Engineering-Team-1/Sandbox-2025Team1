from pathlib import Path

import pytest

from dispatcher.build_strategy import (BuildStrategyError,
                                       _ensure_single_executable,
                                       prepare_make_interactive)
from dispatcher.constant import (AcceptedFormat, BuildStrategy, ExecutionMode,
                                 Language)
from dispatcher.meta import Meta, Task


def _meta(accepted_format: AcceptedFormat, language: Language,
          teacher_lang: str, teacher_file: str) -> Meta:
    return Meta(
        language=language,
        tasks=[
            Task(taskScore=100, memoryLimit=128, timeLimit=1000, caseCount=1)
        ],
        acceptedFormat=accepted_format,
        executionMode=ExecutionMode.INTERACTIVE,
        buildStrategy=BuildStrategy.MAKE_INTERACTIVE,
        assetPaths={
            "teacherLang": teacher_lang,
            "teacher_file": teacher_file,
        },
    )


def _patch_teacher_assets(monkeypatch, tmp_path, teacher_file: str):
    teacher_asset = tmp_path / teacher_file
    teacher_asset.write_text("int main(){return 0;}")

    def fake_ensure(problem_id, asset_type, filename=None):
        assert asset_type == "teacher_file"
        return teacher_asset

    def fake_compile_at_path(src_dir, lang):
        out = Path(src_dir) / "teacher_main"
        out.write_bytes(b"bin")
        out.chmod(0o755)
        return {"Status": "AC"}

    monkeypatch.setattr("dispatcher.build_strategy.ensure_custom_asset",
                        fake_ensure)
    monkeypatch.setattr(
        "dispatcher.build_strategy.SubmissionRunner.compile_at_path",
        fake_compile_at_path)


def test_prepare_make_interactive_zip_python_requires_main(
        monkeypatch, tmp_path):
    _patch_teacher_assets(monkeypatch, tmp_path, "Teacher_file.py")
    meta = _meta(AcceptedFormat.ZIP, Language.PY, "py", "Teacher_file.py")
    submission_dir = tmp_path / "sub"
    (submission_dir / "src" / "common").mkdir(parents=True)

    with pytest.raises(BuildStrategyError):
        prepare_make_interactive(problem_id=1,
                                 meta=meta,
                                 submission_dir=submission_dir)


def test_prepare_make_interactive_zip_c_requires_makefile(
        monkeypatch, tmp_path):
    _patch_teacher_assets(monkeypatch, tmp_path, "Teacher_file.c")
    meta = _meta(AcceptedFormat.ZIP, Language.C, "c", "Teacher_file.c")
    submission_dir = tmp_path / "sub"
    src_dir = submission_dir / "src" / "common"
    src_dir.mkdir(parents=True)
    (src_dir / "main.c").write_text("int main(){return 0;}")

    with pytest.raises(BuildStrategyError):
        prepare_make_interactive(problem_id=1,
                                 meta=meta,
                                 submission_dir=submission_dir)


def test_prepare_make_interactive_code_skips_make(monkeypatch, tmp_path):
    _patch_teacher_assets(monkeypatch, tmp_path, "Teacher_file.c")
    meta = _meta(AcceptedFormat.CODE, Language.C, "c", "Teacher_file.c")
    submission_dir = tmp_path / "sub"
    src_dir = submission_dir / "src" / "common"
    src_dir.mkdir(parents=True)
    (src_dir / "main.c").write_text("int main(){return 0;}")

    plan = prepare_make_interactive(problem_id=1,
                                    meta=meta,
                                    submission_dir=submission_dir)
    assert plan.needs_make is False
    assert (submission_dir / "teacher" / "common" / "main.c").exists()
    assert (submission_dir / "teacher" / "common" / "teacher_main").exists()


def test_ensure_single_executable_rejects_extra(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.out").write_bytes(b"\x7fELFbin")
    extra = src_dir / "extra"
    extra.write_bytes(b"\x7fELFbin")
    (src_dir / "a.out").chmod(0o755)
    extra.chmod(0o755)

    with pytest.raises(BuildStrategyError):
        _ensure_single_executable(src_dir, allowed={"a.out"})
