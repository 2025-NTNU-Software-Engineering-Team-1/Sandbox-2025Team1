import io
import threading
import zipfile
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from dispatcher.dispatcher import Dispatcher
from dispatcher.exception import *
from dispatcher.constant import BuildStrategy, ExecutionMode, Language, SubmissionMode
from dispatcher.build_strategy import (
    BuildPlan,
    BuildStrategyError,
    prepare_function_only_submission,
    prepare_make_normal,
)
import dispatcher.pipeline
from dispatcher.meta import Meta, Task
import dispatcher.job as dispatcher_job

# --- Fixtures ---


@pytest.fixture
def mock_network_controller(monkeypatch):
    """
    Mock NetworkController to avoid real Docker interactions.
    """
    mock_nc_cls = MagicMock()
    monkeypatch.setattr("dispatcher.dispatcher.NetworkController", mock_nc_cls)

    mock_instance = mock_nc_cls.return_value
    mock_instance.setup_sidecars.return_value = []
    mock_instance.setup_router.return_value = "mock_router_id"
    mock_instance.get_network_mode.return_value = "none"
    mock_instance.ensure_sidecar_images.return_value = None

    return mock_instance


@pytest.fixture
def docker_dispatcher(mock_network_controller, tmp_path):
    """
    Initialize Dispatcher with mocked components.
    """
    d = Dispatcher()
    d.SUBMISSION_DIR = tmp_path / "submissions"
    d.SUBMISSION_DIR.mkdir()
    d.testing = True
    return d


@pytest.fixture
def submission_generator():
    """
    Mock submission generator or data provider.
    """

    class Generator:
        submission_ids = {
            "sub-001": "normal-submission",
            "sub-002": "failed-submission",
        }

    return Generator()


# --- Tests ---


def test_create_dispatcher(docker_dispatcher):
    assert docker_dispatcher is not None


def test_start_dispatcher(docker_dispatcher):

    docker_dispatcher.start()
    assert docker_dispatcher.is_alive()
    docker_dispatcher.stop()
    docker_dispatcher.join(timeout=3)
    assert not docker_dispatcher.is_alive()


def _mock_pipeline(monkeypatch):
    # Mock pipeline functions to avoid backend requests
    monkeypatch.setattr(dispatcher.pipeline, "fetch_problem_rules",
                        lambda *args, **kwargs: {})
    monkeypatch.setattr(dispatcher.pipeline, "fetch_problem_network_config",
                        lambda *args, **kwargs: {})
    # Also mock internal calls within dispatcher
    monkeypatch.setattr("dispatcher.dispatcher.fetch_problem_rules",
                        lambda *args, **kwargs: {})
    monkeypatch.setattr("dispatcher.dispatcher.fetch_problem_network_config",
                        lambda *args, **kwargs: {})


def test_normal_submission_handle(docker_dispatcher: Dispatcher,
                                  submission_generator, monkeypatch, tmp_path):
    """
    Test the handle() method for a normal submission flow.
    """
    _mock_pipeline(monkeypatch)

    sub_id = "sub-001"
    sub_dir = docker_dispatcher.SUBMISSION_DIR / sub_id
    sub_dir.mkdir(parents=True)

    meta = Meta(
        language=Language.PY,
        tasks=[
            Task(taskScore=100, memoryLimit=128, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.
        COMPILE,  # Python doesn't build, but consistent with flow
    )
    (sub_dir / "meta.json").write_text(json.dumps(meta.dict()))

    docker_dispatcher.handle(sub_id, 1)

    assert docker_dispatcher.contains(sub_id)

    assert not docker_dispatcher.queue.empty()
    job = docker_dispatcher.queue.get()
    if isinstance(job, dispatcher_job.Compile):
        pass
    else:
        assert isinstance(job, dispatcher_job.Execute)
        assert job.submission_id == sub_id


def test_handle_duplicated_submission(docker_dispatcher: Dispatcher, tmp_path,
                                      monkeypatch):
    _mock_pipeline(monkeypatch)

    sub_id = "dup-sub"
    sub_dir = docker_dispatcher.SUBMISSION_DIR / sub_id
    sub_dir.mkdir(parents=True)

    meta = Meta(
        language=Language.C,
        tasks=[
            Task(taskScore=100, memoryLimit=128, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.COMPILE,
    )
    (sub_dir / "meta.json").write_text(json.dumps(meta.dict()))

    docker_dispatcher.handle(sub_id, 1)

    with pytest.raises(DuplicatedSubmissionIdError):
        docker_dispatcher.handle(sub_id, 1)


def test_handle_triggers_background_pull(docker_dispatcher: Dispatcher,
                                         monkeypatch, tmp_path):
    """
    Verify that handle starts a background thread to pull images
    """
    _mock_pipeline(monkeypatch)

    # 1. Mock fetch_problem_network_config to return sidecar
    sidecar_config = [{"name": "db", "image": "mysql", "env": {}, "args": []}]
    monkeypatch.setattr(
        "dispatcher.dispatcher.fetch_problem_network_config",
        lambda pid: {"sidecars": sidecar_config},
    )

    # 2. Prepare fake files
    sub_id = "pull-test"
    sub_dir = docker_dispatcher.SUBMISSION_DIR / sub_id
    sub_dir.mkdir(parents=True)
    meta = Meta(
        language=Language.PY,
        tasks=[
            Task(taskScore=100, memoryLimit=128, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.COMPILE,
    )
    (sub_dir / "meta.json").write_text(json.dumps(meta.dict()))

    # 3. Mock threading.Thread to intercept
    with patch("dispatcher.dispatcher.threading.Thread") as mock_thread:
        docker_dispatcher.handle(sub_id, 1)

        # 4. Check if a Thread targeting ensure_sidecar_images was started
        found = False
        target_method = docker_dispatcher.network_controller.ensure_sidecar_images

        for call_args in mock_thread.call_args_list:
            # call_args.kwargs['target'] or call_args[1]['target']
            kwargs = call_args.kwargs
            if kwargs.get("target") == target_method:
                found = True
                assert kwargs.get("daemon") is True
                break

        assert found, "Should start a background daemon thread for image pulling"


# --- Build Strategy Tests (Original logic preserved) ---


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
            "makefile": "problem/1/makefile.zip",
        },
    )


def test_prepare_function_only_submission(monkeypatch, tmp_path):
    submission_id = "func-sub"
    submission_dir = tmp_path / submission_id
    src_dir = submission_dir / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.c").write_text("int foo(){return 0;}")

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.writestr("Makefile", "all:\n\t@touch a.out\n")
        zf.writestr("function.h", "// template")
    bundle_bytes = bundle.getvalue()
    monkeypatch.setattr(
        "dispatcher.build_strategy.fetch_problem_asset",
        lambda problem_id, asset_type: bundle_bytes,
    )

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
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.writestr("Makefile", "all:\n\t@true\n")
        zf.writestr("student_impl.py", "# existing")
        zf.writestr("main.py", 'print("teacher")')
    bundle_bytes = bundle.getvalue()
    monkeypatch.setattr(
        "dispatcher.build_strategy.fetch_problem_asset",
        lambda problem_id, asset_type: bundle_bytes,
    )

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
    dispatcher_obj = Dispatcher()
    dispatcher_obj.SUBMISSION_DIR = tmp_path
    dispatcher_obj.testing = False
    dispatcher_obj.network_controller = MagicMock()  # Mock NetworkController

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
    dispatcher_obj.result[submission_id] = (meta, task_content)
    dispatcher_obj.locks[submission_id] = threading.Lock()
    dispatcher_obj.compile_locks[submission_id] = threading.Lock()
    dispatcher_obj.created_at[submission_id] = datetime.now()
    dispatcher_obj.build_locks[submission_id] = threading.Lock()
    dispatcher_obj.build_plans[submission_id] = BuildPlan(
        needs_make=True,
        lang_key="c11",
        finalize=None,
    )
    dispatcher_obj.queue.put(
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

    dispatcher_obj.build(submission_id=submission_id, lang=Language.C)
    assert not dispatcher_obj.contains(submission_id)
    assert dispatcher_obj.queue.empty()
