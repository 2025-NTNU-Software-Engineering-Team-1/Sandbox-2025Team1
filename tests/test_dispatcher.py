import io
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from dispatcher.dispatcher import Dispatcher
from dispatcher.custom_checker import run_custom_checker_case
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


def test_custom_checker_run(tmp_path):
    try:
        import docker
        client = docker.from_env()
        client.ping()
        if not any(img.tags and "python:3.11-slim" in img.tags
                   for img in client.images.list()):
            pytest.skip("python:3.11-slim image not available")
    except Exception:
        pytest.skip("docker not available")
    submission_id = "checker-sub"
    case_no = "0000"
    checker_path = tmp_path / "custom_checker.py"
    checker_path.write_text(
        "import sys\nprint('STATUS: AC')\nprint('MESSAGE: ok')\n")
    case_in = tmp_path / "input.in"
    case_ans = tmp_path / "answer.out"
    case_in.write_text("1")
    case_ans.write_text("1")
    result = run_custom_checker_case(
        submission_id=submission_id,
        case_no=case_no,
        checker_path=checker_path,
        case_in_path=case_in,
        case_ans_path=case_ans,
        student_output="1",
        time_limit_ms=3000,
        mem_limit_kb=256000,
        image="python:3.11-slim",
        docker_url="unix://var/run/docker.sock",
    )
    assert result["status"] == "AC"
    assert "ok" in result["message"]


def test_custom_checker_nonzero_exit(tmp_path, monkeypatch):
    submission_id = "checker-sub-je"
    case_no = "0001"
    checker_path = tmp_path / "custom_checker.py"
    checker_path.write_text(
        "import sys\nprint('STATUS: AC')\nprint('MESSAGE: ok')\n")
    case_in = tmp_path / "input.in"
    case_ans = tmp_path / "answer.out"
    case_in.write_text("1")
    case_ans.write_text("1")

    def fake_run(self):
        return {
            "exit_code": 1,
            "stdout": "STATUS: WA\nMESSAGE: bad",
            "stderr": "boom",
        }

    monkeypatch.setattr("dispatcher.custom_checker.CustomCheckerRunner.run",
                        fake_run)
    result = run_custom_checker_case(
        submission_id=submission_id,
        case_no=case_no,
        checker_path=checker_path,
        case_in_path=case_in,
        case_ans_path=case_ans,
        student_output="1",
        time_limit_ms=3000,
        mem_limit_kb=256000,
        image="python:3.11-slim",
        docker_url="unix://var/run/docker.sock",
    )
    assert result["status"] == "JE"
    assert "boom" in result["message"]


def test_custom_checker_missing_asset_sets_error():
    dispatcher = Dispatcher()
    submission_id = "checker-missing"
    meta = Meta(
        language=Language.PY,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.COMPILE,
        customChecker=True,
        assetPaths={},
    )
    dispatcher.custom_checker_info = {}
    dispatcher._prepare_custom_checker(
        submission_id=submission_id,
        problem_id=1,
        meta=meta,
        submission_path=dispatcher.SUBMISSION_DIR / submission_id,
    )
    assert dispatcher.custom_checker_info[submission_id]["enabled"] is True
    assert "missing" in dispatcher.custom_checker_info[submission_id]["error"]


def test_prepare_custom_scorer_disabled_when_not_configured():
    dispatcher = Dispatcher()
    submission_id = "scorer-disabled"
    meta = Meta(
        language=Language.PY,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.COMPILE,
        scoringScript=False,
        assetPaths={},
    )
    dispatcher.custom_scorer_info = {}
    dispatcher._prepare_custom_scorer(
        submission_id=submission_id,
        problem_id=1,
        meta=meta,
        submission_path=dispatcher.SUBMISSION_DIR / submission_id,
    )
    assert dispatcher.custom_scorer_info[submission_id]["enabled"] is False


def test_run_custom_scorer_payload(monkeypatch):
    dispatcher = Dispatcher()
    submission_id = "score-sub"
    dispatcher.problem_ids[submission_id] = 99
    dispatcher.custom_scorer_info[submission_id] = {
        "enabled": True,
        "scorer_path": Path("/tmp/score.py"),
        "image": "noj-custom-checker-scorer",
    }
    meta = Meta(
        language=Language.C,
        tasks=[
            Task(taskScore=100, memoryLimit=1024, timeLimit=1000, caseCount=1)
        ],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.GENERAL,
        buildStrategy=BuildStrategy.COMPILE,
        scoringScript=True,
    )
    monkeypatch.setattr(dispatcher, "_fetch_late_seconds", lambda _sid: 0)
    monkeypatch.setattr(
        "dispatcher.dispatcher.run_custom_scorer",
        lambda **kwargs: {
            "status": "OK",
            "score": 77,
            "message": "ok",
            "breakdown": {
                "partial": [77]
            },
            "stdout": "out",
            "stderr": "",
        },
    )
    scoring_payload, status_override = dispatcher._run_custom_scorer_if_needed(
        submission_id=submission_id,
        meta=meta,
        submission_result=[[{
            "status": "AC",
            "execTime": 10,
            "memoryUsage": 20
        }]],
        sa_payload={"status": "pass"},
        checker_payload=None,
    )
    assert scoring_payload["score"] == 77
    assert scoring_payload["status"] == "OK"
    assert scoring_payload["breakdown"] == {"partial": [77]}
    assert scoring_payload["message"] == "ok"
    assert status_override is None
