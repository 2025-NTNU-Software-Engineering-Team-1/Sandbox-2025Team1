import io
from zipfile import ZipFile, ZipInfo
from pathlib import Path

import pytest

from dispatcher import file_manager
from dispatcher.meta import Meta
from dispatcher.constant import BuildStrategy, ExecutionMode, SubmissionMode


def _build_meta(
    mode: SubmissionMode,
    execution_mode: ExecutionMode = ExecutionMode.GENERAL,
    build_strategy: BuildStrategy = BuildStrategy.COMPILE,
    language: int = 1,
) -> Meta:
    return Meta.parse_obj({
        "language":
        language,
        "submissionMode":
        int(mode),
        "executionMode":
        int(execution_mode),
        "buildStrategy":
        build_strategy.value,
        "tasks": [{
            "taskScore": 100,
            "memoryLimit": 32768,
            "timeLimit": 1000,
            "caseCount": 1,
        }],
    })


def _build_zip(content: dict[str, str]) -> io.BytesIO:
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        for name, data in content.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf


def _prepare_testdata(root: Path):
    root.mkdir()
    (root / "0000.in").write_text("1")
    (root / "0000.out").write_text("1")


def test_extract_zip_submission(tmp_path):
    meta = _build_meta(SubmissionMode.ZIP,
                       build_strategy=BuildStrategy.MAKE_NORMAL)
    testdata_root = tmp_path / "testdata"
    _prepare_testdata(testdata_root)
    archive = _build_zip({
        "Makefile": "all:\n\t@true\n",
        "helper.c": "int main(){return 0;}",
    })
    file_manager.extract(
        root_dir=tmp_path,
        submission_id="zip-001",
        meta=meta,
        source=archive,
        testdata=testdata_root,
    )
    submission_dir = tmp_path / "zip-001"
    assert (submission_dir / "src" / "common" / "Makefile").exists()
    assert (submission_dir / "testcase" / "0000.in").exists()


def test_extract_zip_submission_requires_makefile(tmp_path):
    meta = _build_meta(SubmissionMode.ZIP,
                       build_strategy=BuildStrategy.MAKE_NORMAL)
    testdata_root = tmp_path / "testdata"
    _prepare_testdata(testdata_root)
    archive = _build_zip({"helper.c": "int main(){return 0;}"})
    with pytest.raises(ValueError):
        file_manager.extract(
            root_dir=tmp_path,
            submission_id="zip-002",
            meta=meta,
            source=archive,
            testdata=testdata_root,
        )


def test_extract_zip_python_skips_makefile_requirement(tmp_path):
    meta = _build_meta(
        SubmissionMode.ZIP,
        build_strategy=BuildStrategy.MAKE_NORMAL,
        language=2,
    )
    testdata_root = tmp_path / "testdata"
    _prepare_testdata(testdata_root)
    archive = _build_zip({
        "main.py": "print('ok')",
        "helper.txt": "data",
    })
    file_manager.extract(
        root_dir=tmp_path,
        submission_id="zip-py",
        meta=meta,
        source=archive,
        testdata=testdata_root,
    )
    submission_dir = tmp_path / "zip-py"
    assert (submission_dir / "src" / "common" / "main.py").exists()


def test_function_only_rejects_zip_submission(tmp_path):
    meta = _build_meta(SubmissionMode.ZIP,
                       execution_mode=ExecutionMode.FUNCTION_ONLY,
                       build_strategy=BuildStrategy.MAKE_FUNCTION_ONLY)
    testdata_root = tmp_path / "testdata"
    _prepare_testdata(testdata_root)
    archive = _build_zip({
        "Makefile": "all:\n\t@true\n",
    })
    with pytest.raises(ValueError):
        file_manager.extract(
            root_dir=tmp_path,
            submission_id="zip-func",
            meta=meta,
            source=archive,
            testdata=testdata_root,
        )


def test_extract_zip_rejects_symlink(tmp_path):
    meta = _build_meta(SubmissionMode.ZIP,
                       build_strategy=BuildStrategy.MAKE_NORMAL)
    testdata_root = tmp_path / "testdata"
    _prepare_testdata(testdata_root)
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        info = ZipInfo("evil_link")
        # mark as symlink: high nibble 0xA (see external_attr >> 28)
        info.external_attr = (0xA000 << 16)
        zf.writestr(info, b"ignored")
    buf.seek(0)
    with pytest.raises(ValueError):
        file_manager.extract(
            root_dir=tmp_path,
            submission_id="zip-symlink",
            meta=meta,
            source=buf,
            testdata=testdata_root,
        )
