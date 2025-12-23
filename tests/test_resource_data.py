import io
import zipfile
from pathlib import Path

from dispatcher.custom_checker import run_custom_checker_case
from dispatcher.resource_data import (
    prepare_resource_data,
    prepare_teacher_resource_data,
    copy_resource_for_case,
    prepare_teacher_for_case,
)
from runner.path_utils import PathTranslator


class DummyAsset:

    def __init__(self, path: Path):
        self.path = path


def test_prepare_and_copy_resource_data(tmp_path, monkeypatch):
    # create fake extracted directory with resource files
    extracted_dir = tmp_path / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    (extracted_dir / "0000_config.txt").write_text("cfg0")
    (extracted_dir / "0001_config.txt").write_text("cfg1")

    # mock ensure_extracted_resource to return our extracted dir
    def fake_ensure(problem_id, asset_type):
        return extracted_dir

    monkeypatch.setattr("dispatcher.resource_data.ensure_extracted_resource",
                        fake_ensure)

    submission_path = tmp_path / "submissions" / "s1"
    submission_path.mkdir(parents=True, exist_ok=True)

    res_dir = prepare_resource_data(
        problem_id=1,
        submission_path=submission_path,
        asset_paths={"resource_data": "resource_data.zip"},
    )
    assert res_dir and res_dir.exists()

    case_dir = submission_path / "src" / "cases" / "0000"
    case_dir.mkdir(parents=True, exist_ok=True)
    copied = copy_resource_for_case(
        submission_path=submission_path,
        case_dir=case_dir,
        task_no=0,
        case_no=0,
    )
    assert (case_dir / "config.txt").read_text() == "cfg0"
    # cleanup copied
    from dispatcher.resource_data import cleanup_resource_files
    cleanup_resource_files(case_dir, copied)
    assert not (case_dir / "config.txt").exists()


def test_prepare_teacher_resource_data_keeps_existing(tmp_path, monkeypatch):
    # create fake extracted directory with teacher resource files
    extracted_dir = tmp_path / "extracted_teacher"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    (extracted_dir / "0000_teacher.txt").write_text("t0")

    def fake_ensure(problem_id, asset_type):
        assert asset_type == "resource_data_teacher"
        return extracted_dir

    monkeypatch.setattr("dispatcher.resource_data.ensure_extracted_resource",
                        fake_ensure)

    submission_path = tmp_path / "submissions" / "s2"
    # resource_data_teacher dir will be created in submission_path
    res_teacher_dir = submission_path / "resource_data_teacher"
    res_teacher_dir.mkdir(parents=True, exist_ok=True)
    existing = res_teacher_dir / "teacher_main"
    existing.write_text("keep")

    res_dir = prepare_teacher_resource_data(
        problem_id=2,
        submission_path=submission_path,
        asset_paths={"resource_data_teacher": "resource_data_teacher.zip"},
    )
    assert res_dir and res_dir.exists()
    # The existing file should still be there since clean=False
    assert existing.read_text() == "keep"
    assert (res_dir / "0000_teacher.txt").read_text() == "t0"


def test_custom_checker_receives_teacher_dir(tmp_path, monkeypatch):
    submission_id = "s3"
    submission_dir = tmp_path / submission_id
    checker_dir = submission_dir / "checker"
    checker_dir.mkdir(parents=True, exist_ok=True)
    checker_path = checker_dir / "custom_checker.py"
    checker_path.write_text("print('ok')")

    case_in = tmp_path / "0000.in"
    case_out = tmp_path / "0000.out"
    case_in.write_text("1")
    case_out.write_text("1")

    teacher_dir = submission_dir / "teacher"
    teacher_dir.mkdir(parents=True, exist_ok=True)

    captured = {}

    class DummyRunner:

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self):
            return {"stdout": "STATUS:AC\n", "exit_code": 0, "stderr": ""}

    monkeypatch.setattr("dispatcher.custom_checker.CustomCheckerRunner",
                        DummyRunner)

    res = run_custom_checker_case(
        submission_id=submission_id,
        case_no="0000",
        checker_path=checker_path,
        case_in_path=case_in,
        case_ans_path=case_out,
        student_output="1",
        time_limit_ms=1000,
        mem_limit_kb=1024,
        image="dummy",
        docker_url="unix://dummy",
        student_workdir=submission_dir / "src" / "cases" / "0000",
        teacher_dir=teacher_dir,
    )
    host_teacher = str(PathTranslator().to_host(teacher_dir))
    assert captured.get("teacher_dir") == host_teacher
    assert res["status"] == "AC"


def test_prepare_teacher_for_case_copies_resources(tmp_path):
    submission_path = tmp_path / "submissions" / "s4"
    teacher_common = submission_path / "teacher" / "common"
    teacher_common.mkdir(parents=True, exist_ok=True)
    (teacher_common / "teacher_main").write_text("bin")
    (teacher_common / "main").write_text("bin")

    testcase_dir = submission_path / "testcase"
    testcase_dir.mkdir(parents=True, exist_ok=True)
    (testcase_dir / "0000.in").write_text("input")

    teacher_res_dir = submission_path / "resource_data_teacher"
    teacher_res_dir.mkdir(parents=True, exist_ok=True)
    (teacher_res_dir / "0000_data.txt").write_text("data")

    teacher_case_dir = prepare_teacher_for_case(
        submission_path=submission_path,
        task_no=0,
        case_no=0,
        teacher_common_dir=teacher_common,
        copy_testcase=True,
    )

    assert (teacher_case_dir / "teacher_main").read_text() == "bin"
    assert (teacher_case_dir / "main").read_text() == "bin"
    assert (teacher_case_dir / "testcase.in").read_text() == "input"
    assert (teacher_case_dir / "data.txt").read_text() == "data"


def test_copy_resource_for_case_flattens_nested(tmp_path):
    submission_path = tmp_path / "submissions" / "s5"
    resource_dir = submission_path / "resource_data" / "nested"
    resource_dir.mkdir(parents=True, exist_ok=True)
    (resource_dir / "0000_file.txt").write_text("value")

    case_dir = submission_path / "src" / "cases" / "0000"
    case_dir.mkdir(parents=True, exist_ok=True)

    copied = copy_resource_for_case(
        submission_path=submission_path,
        case_dir=case_dir,
        task_no=0,
        case_no=0,
    )
    assert (case_dir / "file.txt").read_text() == "value"
    assert (case_dir / "file.txt") in copied
