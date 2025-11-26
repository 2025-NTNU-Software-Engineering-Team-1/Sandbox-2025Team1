import io
import threading
import zipfile
from datetime import datetime
from dispatcher.dispatcher import Dispatcher
from dispatcher.exception import *
from dispatcher.constant import BuildStrategy, ExecutionMode, Language, SubmissionMode
from dispatcher.build_strategy import (
    BuildPlan,
    BuildStrategyError,
    prepare_function_only_submission,
    prepare_make_normal,
)
from tests.submission_generator import SubmissionGenerator
import dispatcher.pipeline
import pytest
from dispatcher.meta import Meta, Task
import dispatcher.job as dispatcher_job


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


def _zip_meta(language: Language, strategy: BuildStrategy) -> Meta:
    return Meta(
        language=language,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.ZIP,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=strategy,
    )


def test_prepare_zip_submission_success(tmp_path):
    submission_id = "zip-sub"
    submission_dir = tmp_path / submission_id
    src_dir = submission_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "Makefile").write_text("all:\n\t@true\n")

    plan = prepare_make_normal(
        meta=_zip_meta(Language.CPP, BuildStrategy.MAKE_NORMAL),
        submission_dir=submission_dir,
    )
    assert plan.needs_make is True
    assert plan.lang_key == "cpp17"
    assert plan.finalize is not None
    (src_dir / "a.out").write_text("binary")
    plan.finalize()
    assert (src_dir / "main").exists()
    assert not (src_dir / "a.out").exists()


def test_make_normal_finalize_requires_aout(tmp_path):
    submission_dir = tmp_path / "zip-missing"
    src_dir = submission_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "Makefile").write_text("all:\n\t@true\n")
    plan = prepare_make_normal(
        meta=_zip_meta(Language.C, BuildStrategy.MAKE_NORMAL),
        submission_dir=submission_dir,
    )
    assert plan.finalize is not None
    with pytest.raises(BuildStrategyError):
        plan.finalize()


def _function_only_meta(language: Language) -> Meta:
    return Meta(
        language=language,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.FUNCTION_ONLY,
        buildStrategy=BuildStrategy.MAKE_FUNCTION_ONLY,
        assetPaths={
            'makefile': 'problem/1/makefile.zip',
        },
    )


def test_prepare_function_only_submission(monkeypatch, tmp_path):
    submission_id = "func-sub"
    submission_dir = tmp_path / submission_id
    src_dir = submission_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.c").write_text("int foo(){return 0;}")

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, 'w') as zf:
        zf.writestr('Makefile', 'all:\n\t@touch a.out\n')
        zf.writestr('function.h', '// template')
    bundle_bytes = bundle.getvalue()
    monkeypatch.setattr("dispatcher.build_strategy.fetch_problem_asset",
                        lambda problem_id, asset_type: bundle_bytes)

    plan = prepare_function_only_submission(
        problem_id=1,
        meta=_function_only_meta(Language.C),
        submission_dir=submission_dir,
    )
    assert plan.needs_make is True
    assert plan.lang_key == "c11"
    assert plan.finalize is not None
    assert (src_dir / "function.h").read_text() == "int foo(){return 0;}"
    (src_dir / "a.out").write_text("binary")
    plan.finalize()
    assert (src_dir / "main").exists()


def test_prepare_function_only_python(monkeypatch, tmp_path):
    submission_id = "func-py"
    submission_dir = tmp_path / submission_id
    src_dir = submission_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("print('hi')")

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, 'w') as zf:
        zf.writestr('Makefile', 'all:\n\t@true\n')
        zf.writestr('student_impl.py', '# existing')
        zf.writestr('main.py', 'print("teacher")')
    bundle_bytes = bundle.getvalue()
    monkeypatch.setattr("dispatcher.build_strategy.fetch_problem_asset",
                        lambda problem_id, asset_type: bundle_bytes)

    plan = prepare_function_only_submission(
        problem_id=1,
        meta=_function_only_meta(Language.PY),
        submission_dir=submission_dir,
    )
    assert plan.needs_make is True
    assert plan.lang_key == "python3"
    assert plan.finalize is not None
    assert (src_dir / "student_impl.py").read_text() == "print('hi')"
    plan.finalize()


def test_make_normal_python_skips_make(tmp_path):
    submission_id = "zip-py"
    submission_dir = tmp_path / submission_id
    src_dir = submission_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("print('ok')")

    plan = prepare_make_normal(
        meta=_zip_meta(Language.PY, BuildStrategy.MAKE_NORMAL),
        submission_dir=submission_dir,
    )
    assert plan.needs_make is False
    assert plan.finalize is None


def test_build_failure_clears_submission(monkeypatch, tmp_path):
    dispatcher = Dispatcher()
    dispatcher.SUBMISSION_DIR = tmp_path
    dispatcher.testing = False
    submission_id = "build-ce"
    meta = Meta(
        language=Language.C,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.MAKE_NORMAL,
    )
    task_content = {"0000": None}
    dispatcher.result[submission_id] = (meta, task_content)
    dispatcher.locks[submission_id] = threading.Lock()
    dispatcher.compile_locks[submission_id] = threading.Lock()
    dispatcher.created_at[submission_id] = datetime.now()
    dispatcher.build_locks[submission_id] = threading.Lock()
    dispatcher.build_plans[submission_id] = BuildPlan(
        needs_make=True,
        lang_key="c11",
        finalize=None,
    )
    dispatcher.queue.put(
        dispatcher_job.Execute(submission_id=submission_id,
                               task_id=0,
                               case_id=0))

    class DummyResp:
        ok = True
        status_code = 200
        text = "ok"

    monkeypatch.setattr("dispatcher.dispatcher.requests.put",
                        lambda *args, **kwargs: DummyResp())
    monkeypatch.setattr("dispatcher.dispatcher.file_manager.clean_data",
                        lambda *_: None)
    monkeypatch.setattr("dispatcher.dispatcher.file_manager.backup_data",
                        lambda *_: None)

    def fake_build(self):
        return {
            "Status": "CE",
            "Stdout": "",
            "Stderr": "boom",
            "DockerExitCode": 2,
        }

    monkeypatch.setattr(
        "dispatcher.dispatcher.SubmissionRunner.build_with_make", fake_build)

    dispatcher.build(submission_id=submission_id, lang=Language.C)
    assert not dispatcher.contains(submission_id)
    assert dispatcher.queue.empty()
