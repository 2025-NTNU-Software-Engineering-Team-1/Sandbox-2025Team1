import io
import zipfile
from dispatcher.dispatcher import Dispatcher
from dispatcher.exception import *
from dispatcher.constant import ExecutionMode, Language, SubmissionMode
from runner.submission import SubmissionRunner
from tests.submission_generator import SubmissionGenerator
import dispatcher.pipeline
import pytest
from dispatcher.meta import Meta, Task


def test_create_dispatcher():
    docker_dispatcher = Dispatcher()
    assert docker_dispatcher is not None


def test_start_dispatcher(docker_dispatcher: Dispatcher):
    docker_dispatcher.start()


def _mock_pipeline(monkeypatch):
    monkeypatch.setattr(dispatcher.pipeline, "fetch_problem_rules",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr("dispatcher.dispatcher.fetch_problem_rules",
                        lambda *args, **kwargs: None)


def test_normal_submission(
    docker_dispatcher: Dispatcher,
    submission_generator,
    monkeypatch,
):
    _mock_pipeline(monkeypatch)

    docker_dispatcher.start()
    _ids = []
    for _id, prob in submission_generator.submission_ids.items():
        if prob == "normal-submission":
            _ids.append((_id, prob))

    assert len(_ids) != 0

    for _id, prob in _ids:
        docker_dispatcher.handle(_id, 1)


def test_duplicated_submission(
    docker_dispatcher: Dispatcher,
    submission_generator,
    monkeypatch,
):
    _mock_pipeline(monkeypatch)
    import random

    docker_dispatcher.start()

    _id, prob = random.choice(list(
        submission_generator.submission_ids.items()))

    assert _id is not None
    assert prob is not None

    docker_dispatcher.handle(_id, 1)

    try:
        docker_dispatcher.handle(_id, 1)
    except DuplicatedSubmissionIdError:
        return
    assert False


def test_prepare_zip_submission_success(monkeypatch, tmp_path):
    dispatcher = Dispatcher()
    dispatcher.SUBMISSION_DIR = tmp_path
    submission_id = "zip-sub"
    src_dir = tmp_path / submission_id / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "Makefile").write_text("all:\n\t@true\n")

    def fake_build(self):
        (src_dir / "a.out").write_text("binary")
        return {
            "Status": "AC",
            "Stdout": "",
            "Stderr": "",
            "DockerExitCode": 0
        }

    monkeypatch.setattr(SubmissionRunner, "build_with_make", fake_build)
    dispatcher.prepare_zip_submission(submission_id, Language.CPP)
    assert (src_dir / "main").exists()
    assert not (src_dir / "a.out").exists()


def test_prepare_zip_submission_failure(monkeypatch, tmp_path):
    dispatcher = Dispatcher()
    dispatcher.SUBMISSION_DIR = tmp_path
    submission_id = "zip-sub-fail"
    src_dir = tmp_path / submission_id / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "Makefile").write_text("all:\n\t@true\n")

    def fake_build(self):
        return {
            "Status": "CE",
            "Stdout": "",
            "Stderr": "boom",
            "DockerExitCode": 1
        }

    monkeypatch.setattr(SubmissionRunner, "build_with_make", fake_build)
    with pytest.raises(ValueError):
        dispatcher.prepare_zip_submission(submission_id, Language.C)


def _function_only_meta(language: Language) -> Meta:
    return Meta(
        language=language,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.FUNCTION_ONLY,
        assetPaths={
            'makefile': 'problem/1/makefile.zip',
        },
    )


def test_prepare_function_only_submission(monkeypatch, tmp_path):
    dispatcher = Dispatcher()
    dispatcher.SUBMISSION_DIR = tmp_path
    submission_id = "func-sub"
    src_dir = tmp_path / submission_id / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.c").write_text("int foo(){return 0;}")

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, 'w') as zf:
        zf.writestr('Makefile', 'all:\n\t@touch a.out\n')
        zf.writestr('function.h', '// template')
    bundle_bytes = bundle.getvalue()
    monkeypatch.setattr(
        "dispatcher.dispatcher.fetch_problem_asset",
        lambda problem_id, asset_type: bundle_bytes)

    def fake_build(self):
        (src_dir / "a.out").write_text("binary")
        return {
            "Status": "AC",
            "Stdout": "",
            "Stderr": "",
            "DockerExitCode": 0
        }

    monkeypatch.setattr(SubmissionRunner, "build_with_make", fake_build)
    dispatcher.prepare_function_only_submission(
        submission_id=submission_id,
        problem_id=1,
        meta=_function_only_meta(Language.C),
    )
    assert (src_dir / "function.h").read_text() == "int foo(){return 0;}"
    assert (src_dir / "main").exists()


def test_prepare_function_only_python(monkeypatch, tmp_path):
    dispatcher = Dispatcher()
    dispatcher.SUBMISSION_DIR = tmp_path
    submission_id = "func-py"
    src_dir = tmp_path / submission_id / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("print('hi')")

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, 'w') as zf:
        zf.writestr('Makefile', 'all:\n\t@true\n')
        zf.writestr('student_impl.py', '# existing')
        zf.writestr('main.py', 'print("teacher")')
    bundle_bytes = bundle.getvalue()
    monkeypatch.setattr(
        "dispatcher.dispatcher.fetch_problem_asset",
        lambda problem_id, asset_type: bundle_bytes)

    def fake_build(self):
        return {
            "Status": "AC",
            "Stdout": "",
            "Stderr": "",
            "DockerExitCode": 0
        }

    monkeypatch.setattr(SubmissionRunner, "build_with_make", fake_build)
    dispatcher.prepare_function_only_submission(
        submission_id=submission_id,
        problem_id=1,
        meta=_function_only_meta(Language.PY),
    )
    assert (src_dir / "student_impl.py").read_text() == "print('hi')"
