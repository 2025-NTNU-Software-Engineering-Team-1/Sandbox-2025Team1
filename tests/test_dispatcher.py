from dispatcher.dispatcher import Dispatcher
from dispatcher.exception import *
from dispatcher.constant import Language
from runner.submission import SubmissionRunner
from tests.submission_generator import SubmissionGenerator
import dispatcher.pipeline
import pytest


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
        return {"Status": "AC", "Stdout": "", "Stderr": "", "DockerExitCode": 0}

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
        return {"Status": "CE", "Stdout": "", "Stderr": "boom", "DockerExitCode": 1}

    monkeypatch.setattr(SubmissionRunner, "build_with_make", fake_build)
    with pytest.raises(ValueError):
        dispatcher.prepare_zip_submission(submission_id, Language.C)
