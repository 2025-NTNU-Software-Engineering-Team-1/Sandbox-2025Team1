import io
from zipfile import ZipFile
from pathlib import Path

import pytest

from dispatcher import file_manager
from dispatcher.meta import Meta
from dispatcher.constant import ExecutionMode, SubmissionMode


def _build_meta(mode: SubmissionMode, execution_mode: ExecutionMode = ExecutionMode.GENERAL) -> Meta:
    return Meta.parse_obj({
        "language":
        1,
        "submissionMode":
        int(mode),
        "executionMode":
        int(execution_mode),
        "tasks": [{
            "taskScore": 100,
            "memoryLimit": 32768,
            "timeLimit": 1000,
            "caseCount": 1
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
    meta = _build_meta(SubmissionMode.ZIP)
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
    assert (submission_dir / "src" / "Makefile").exists()
    assert (submission_dir / "testcase" / "0000.in").exists()


def test_extract_zip_submission_requires_makefile(tmp_path):
    meta = _build_meta(SubmissionMode.ZIP)
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


def test_function_only_rejects_zip_submission(tmp_path):
    meta = _build_meta(SubmissionMode.ZIP, ExecutionMode.FUNCTION_ONLY)
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
