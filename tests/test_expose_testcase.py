import io
import zipfile
from pathlib import Path

from dispatcher.file_manager import extract
from dispatcher.meta import Meta, Task
from dispatcher.constant import Language, SubmissionMode, ExecutionMode


def _make_meta():
    return Meta(
        language=Language.C,
        tasks=[
            Task(taskScore=100,
                 memoryLimit=256000,
                 timeLimit=1000,
                 caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=0,
        artifactCollection=[],
        exposeTestcase=True,
    )


def test_expose_testcase_copies_in_files(tmp_path):
    root = tmp_path
    submission_id = "s1"
    meta = _make_meta()
    # build fake source zip
    src_zip = io.BytesIO()
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("main.c", "int main(){return 0;}")
    src_zip.seek(0)
    # build fake testcase with .in
    testdata = tmp_path / "data"
    testdata.mkdir()
    (testdata / "00.in").write_text("input")
    extract(
        root_dir=root,
        submission_id=submission_id,
        meta=meta,
        source=src_zip,
        testdata=testdata,
    )
    src_dir = root / submission_id / "src"
    assert (src_dir / "00.in").exists()
