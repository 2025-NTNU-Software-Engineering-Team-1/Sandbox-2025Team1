import json
import os
import threading
import time
import requests
import pathlib
import queue
import textwrap
import shutil
from datetime import datetime
from runner.submission import SubmissionRunner
from runner.interactive_runner import InteractiveRunner
from . import job, file_manager, config
from .exception import *
from .meta import Meta
from .constant import BuildStrategy, ExecutionMode, Language, SubmissionMode
from .build_strategy import (
    BuildPlan,
    BuildStrategyError,
    prepare_interactive_teacher_artifacts,
    prepare_function_only_submission,
    prepare_make_interactive,
    prepare_make_normal,
)
from .utils import logger
from .pipeline import fetch_problem_rules
from .artifact_collector import ArtifactCollector

from .static_analysis import run_static_analysis, build_sa_ce_task_content
from .custom_checker import ensure_custom_checker, run_custom_checker_case
from .custom_scorer import ensure_custom_scorer, run_custom_scorer
from .resource_data import (
    prepare_resource_data,
    prepare_teacher_resource_data,
    copy_resource_for_case,
    prepare_teacher_for_case,
    cleanup_resource_files,
)
from .network_control import NetworkController


class Dispatcher(threading.Thread):

    def __init__(
        self,
        dispatcher_config=".config/dispatcher.json",
        submission_config=".config/submission.json",
    ):
        super().__init__()
        self.testing = False
        # read config
        queue_limit, container_limit = config.get_dispatcher_limits(
            dispatcher_config)
        self.do_run = True
        self.SUBMISSION_DIR = config.SUBMISSION_DIR
        self.MAX_TASK_COUNT = queue_limit
        self.queue = queue.Queue(self.MAX_TASK_COUNT)
        self.result = {}
        # Lock
        self.locks = {}
        self.compile_locks = {}
        self.compile_results = {}
        self.problem_ids = {}
        # manage containers
        self.MAX_CONTAINER_SIZE = container_limit
        self.container_count_lock = threading.Lock()
        self.container_count = 0

        # Configs
        s_config = config.get_submission_config(submission_config)
        self.submission_runner_cwd = pathlib.Path(s_config["working_dir"])
        self.docker_url = s_config.get("docker_url",
                                       "unix://var/run/docker.sock")
        self.custom_checker_image = s_config.get("custom_checker_image",
                                                 "noj-custom-checker-scorer")
        self.custom_scorer_image = s_config.get("custom_scorer_image",
                                                self.custom_checker_image)
        self.custom_checker_info = {}
        self.custom_scorer_info = {}
        self.checker_payloads = {}
        self.timeout = 300
        self.created_at = {}

        # [Network] init
        docker_url = s_config.get("docker_url", "unix://var/run/docker.sock")
        self.network_controller = NetworkController(
            docker_url=docker_url,
            submission_dir=self.SUBMISSION_DIR,
        )
        # [Network] end

        # Build Strategy related
        self.prebuilt_submissions = set()
        self.build_strategies = {}
        self.build_plans = {}
        self.build_locks = {}

        # [Static Analysis] init
        self.sa_payloads = {}
        self.submission_resources = {}
        self.pending_tasks = {}
        # [Static Analysis] end
        self.artifact_collector = ArtifactCollector(
            backend_url=config.BACKEND_API,
            token=config.SANDBOX_TOKEN,
            logger=logger(),
        )
        self.resource_dirs = {}
        self.teacher_resource_dirs = {}

    def compile_need(self, lang: Language):
        return lang in {Language.C, Language.CPP}

    def contains(self, submission_id: str):
        return submission_id in self.result

    def _common_dir(self, submission_id: str) -> pathlib.Path:
        base = self.SUBMISSION_DIR / submission_id / "src"
        common = base / "common"
        if not common.exists():
            common.mkdir(parents=True, exist_ok=True)
        return common

    def _case_dir(self, submission_id: str, case_no: str) -> pathlib.Path:
        return self.SUBMISSION_DIR / submission_id / "src" / "cases" / case_no

    def inc_container(self):
        with self.container_count_lock:
            self.container_count += 1

    def dec_container(self):
        with self.container_count_lock:
            self.container_count -= 1

    def is_timed_out(self, submission_id: str):
        if not self.contains(submission_id):
            return False
        delta = datetime.now() - self.created_at[submission_id]
        # valid minus seconds
        return delta.total_seconds() > self.timeout

    def prepare_submission_dir(
        self,
        root_dir: pathlib.Path,
        submission_id: str,
        meta: Meta,
        source,
        testdata: pathlib.Path,
    ):
        create = lambda: file_manager.extract(
            root_dir=root_dir,
            submission_id=submission_id,
            meta=meta,
            source=source,
            testdata=testdata,
        )
        try:
            create()
        except FileExistsError:
            # no found or time out, retry
            if not self.contains(submission_id) or self.is_timed_out(
                    submission_id):
                self.release(submission_id)
                shutil.rmtree(root_dir / submission_id)
                create()
            else:
                raise

    # [Static Analysis] If SA is failed, mark CE for all cases
    def _handle_sa_failure(self, submission_id: str, payload: dict,
                           task_content: dict):
        logger().warning(
            f"Static analysis failed for {submission_id}, marking CE")
        if self.contains(submission_id):
            if payload:
                self.sa_payloads[submission_id] = payload
            meta, _ = self.result[submission_id]
            self.result[submission_id] = (meta, task_content)

            # END all cases with CE
            self.on_submission_complete(submission_id)

    # [Static Analysis] end

    # [Network] Handle Network Setup Failure
    def _handle_network_failure(self, submission_id, error_msg):
        fail_content = build_sa_ce_task_content(
            self.result[submission_id][0],
            f"Network Setup Failed: {error_msg}")
        self.result[submission_id] = (self.result[submission_id][0],
                                      fail_content)
        self.on_submission_complete(submission_id)

    # [Network] end

    def _mark_submission_je(self, submission_id: str, message: str):
        """Mark all cases of a submission as JE (Judge Error)."""
        logger().warning(
            f"Marking submission JE [id={submission_id}]: {message}")
        if not self.contains(submission_id):
            return
        meta, task_content = self.result[submission_id]
        for case_no in task_content:
            task_content[case_no] = {
                "stdout": "",
                "stderr": message,
                "exitCode": 1,
                "execTime": -1,
                "memoryUsage": -1,
                "status": "JE",
            }
        self.result[submission_id] = (meta, task_content)
        self.on_submission_complete(submission_id)

    # Helper methods for Build Strategy
    def _is_prebuilt_submission(self, submission_id: str) -> bool:
        return submission_id in self.prebuilt_submissions

    def _is_build_pending(self, submission_id: str) -> bool:
        return submission_id in self.build_plans

    # [Static Analysis] To check SA is done or not
    def _is_sa_pending(self, submission_id: str) -> bool:
        return submission_id in self.pending_tasks

    # [Static Analysis] end

    def _clear_submission_jobs(self, submission_id: str):
        pending = []
        while True:
            try:
                job_item = self.queue.get_nowait()
            except queue.Empty:
                break
            if getattr(job_item, "submission_id", None) != submission_id:
                pending.append(job_item)
        for item in pending:
            self.queue.put(item)

    def _use_custom_checker(self, submission_id: str) -> bool:
        info = self.custom_checker_info.get(submission_id) or {}
        return bool(info.get("enabled"))

    def _custom_checker_path(self, submission_id: str):
        info = self.custom_checker_info.get(submission_id) or {}
        return info.get("checker_path")

    def _prepare_custom_checker(
        self,
        submission_id: str,
        problem_id: int,
        meta: Meta,
        submission_path: pathlib.Path,
    ):
        if meta.executionMode == ExecutionMode.INTERACTIVE:
            self.custom_checker_info[submission_id] = {"enabled": False}
            return
        if not getattr(meta, "customChecker", False):
            self.custom_checker_info[submission_id] = {"enabled": False}
            return
        if not (getattr(meta, "assetPaths", {}) or {}).get("checker"):
            self.custom_checker_info[submission_id] = {
                "enabled": True,
                "error": "custom checker asset missing",
            }
            return
        try:
            checker_path = ensure_custom_checker(
                problem_id=problem_id,
                submission_path=submission_path,
                execution_mode=meta.executionMode,
            )
            if checker_path:
                self.custom_checker_info[submission_id] = {
                    "enabled": True,
                    "checker_path": checker_path,
                    "image": self.custom_checker_image,
                }
            else:
                self.custom_checker_info[submission_id] = {"enabled": False}
        except Exception as exc:
            # mark enabled to force JE with proper message later
            self.custom_checker_info[submission_id] = {
                "enabled": True,
                "error": str(exc),
            }

    def _prepare_custom_scorer(
        self,
        submission_id: str,
        problem_id: int,
        meta: Meta,
        submission_path: pathlib.Path,
    ):
        if not getattr(meta, "scoringScript", False):
            self.custom_scorer_info[submission_id] = {"enabled": False}
            return
        scorer_asset = getattr(meta, "scorerAsset", None) or (getattr(
            meta, "assetPaths", {}) or {}).get("scoring_script")
        if not scorer_asset:
            # 無資產時直接降級為預設計分
            self.custom_scorer_info[submission_id] = {"enabled": False}
            return
        try:
            scorer_path = ensure_custom_scorer(
                problem_id=problem_id,
                submission_path=submission_path,
            )
            self.custom_scorer_info[submission_id] = {
                "enabled": True,
                "scorer_path": scorer_path,
                "image": self.custom_scorer_image,
            }
        except Exception as exc:
            self.custom_scorer_info[submission_id] = {
                "enabled": True,
                "error": str(exc),
            }

    def _record_checker_message(
        self,
        submission_id: str,
        case_no: str,
        status: str,
        message: str,
    ):
        payload = self.checker_payloads.setdefault(submission_id, {
            "type": "custom",
            "messages": [],
        })
        payload["messages"].append({
            "case": case_no,
            "status": status,
            "message": message,
        })

    def _fetch_late_seconds(self, submission_id: str) -> int:
        try:
            resp = requests.get(
                f"{config.BACKEND_API}/submission/{submission_id}/late-seconds",
                params={"token": config.SANDBOX_TOKEN},
            )
            if not resp.ok:
                logger().warning(
                    "late-seconds api failed [id=%s, status=%s, resp=%s]",
                    submission_id,
                    resp.status_code,
                    resp.text,
                )
                return -1
            data = resp.json().get("data", {})
            late_seconds = data.get("lateSeconds", -1)
            return int(late_seconds)
        except Exception as exc:
            logger().warning("late-seconds api error [id=%s]: %s",
                             submission_id, exc)
            return -1

    def _scorer_time_limit_ms(self, meta: Meta) -> int:
        try:
            return max(t.timeLimit for t in meta.tasks)
        except Exception:
            return 5000

    def _build_scoring_tasks(self, meta: Meta,
                             submission_result: list) -> tuple[list, int]:
        tasks_payload = []
        total_score = 0
        for idx, task in enumerate(meta.tasks):
            task_cases = submission_result[idx] if idx < len(
                submission_result) else []
            results = []
            all_ac = True
            for case_idx, case in enumerate(task_cases):
                status = case.get("status")
                if status != "AC":
                    all_ac = False
                results.append({
                    "caseIndex": case_idx,
                    "status": status,
                    "runTime": case.get("execTime"),
                    "memoryUsage": case.get("memoryUsage"),
                })
            subtask_score = task.taskScore if (
                all_ac and len(task_cases) == task.caseCount) else 0
            total_score += subtask_score
            tasks_payload.append({
                "taskIndex": idx,
                "taskScore": task.taskScore,
                "caseCount": task.caseCount,
                "results": results,
                "subtaskScore": subtask_score,
            })
        return tasks_payload, total_score

    def _build_scoring_stats(self, submission_result: list) -> dict:
        times = []
        mems = []
        for task_cases in submission_result:
            for case in task_cases:
                t = case.get("execTime")
                m = case.get("memoryUsage")
                if isinstance(t, (int, float)) and t >= 0:
                    times.append(t)
                if isinstance(m, (int, float)) and m >= 0:
                    mems.append(m)

        def _agg(vals):
            if not vals:
                return (0, 0, 0)
            return (max(vals), sum(vals) / len(vals), sum(vals))

        max_t, avg_t, sum_t = _agg(times)
        max_m, avg_m, sum_m = _agg(mems)
        return {
            "maxRunTime": max_t,
            "avgRunTime": round(avg_t, 2) if avg_t else 0,
            "sumRunTime": sum_t,
            "maxMemory": max_m,
            "avgMemory": round(avg_m, 2) if avg_m else 0,
            "sumMemory": sum_m,
        }

    def _checker_artifacts_for_scoring(self, checker_payload: dict | None):
        if not checker_payload:
            return {}
        artifacts = checker_payload.get("artifacts") or {}
        if artifacts:
            return artifacts
        return {"payload": checker_payload}

    def _run_custom_scorer_if_needed(
        self,
        submission_id: str,
        meta: Meta,
        submission_result: list,
        sa_payload: dict | None,
        checker_payload: dict | None,
    ):
        info = self.custom_scorer_info.get(submission_id) or {"enabled": False}
        if not info.get("enabled"):
            return None, None
        if info.get("error"):
            return {
                "status": "JE",
                "score": 0,
                "message": info["error"],
            }, "JE"

        late_seconds = self._fetch_late_seconds(submission_id)
        tasks_payload, default_total = self._build_scoring_tasks(
            meta, submission_result)
        scoring_input = {
            "submissionId":
            submission_id,
            "problemId":
            self.problem_ids.get(submission_id),
            "languageType":
            int(meta.language),
            "tasks":
            tasks_payload,
            "totalScore":
            default_total,
            "staticAnalysis":
            sa_payload,
            "lateSeconds":
            late_seconds,
            "stats":
            self._build_scoring_stats(submission_result),
            "checkerArtifacts":
            self._checker_artifacts_for_scoring(checker_payload),
        }
        scorer_path = info.get("scorer_path")
        image = info.get("image", self.custom_scorer_image)
        runner_result = run_custom_scorer(
            scorer_path=scorer_path,
            payload=scoring_input,
            time_limit_ms=self._scorer_time_limit_ms(meta),
            mem_limit_kb=256000,
            image=image,
            docker_url=self.docker_url,
        )
        status = runner_result.get("status")
        scoring_payload = {
            "status": status or "OK",
            "score": runner_result.get("score", 0),
            "message": runner_result.get("message", ""),
        }
        if runner_result.get("breakdown") is not None:
            scoring_payload["breakdown"] = runner_result.get("breakdown")
        artifacts = {}
        if runner_result.get("stdout"):
            artifacts["stdout"] = runner_result.get("stdout")
        if runner_result.get("stderr"):
            artifacts["stderr"] = runner_result.get("stderr")
        if artifacts:
            scoring_payload["artifacts"] = artifacts
        status_override = "JE" if status == "JE" else None
        return scoring_payload, status_override

    def _handle_build_failure(self, submission_id: str, message: str):
        err_msg = message or "build failed"
        logger().warning(f"build failed [id={submission_id}]: {err_msg}")
        self.build_plans.pop(submission_id, None)
        self.build_locks.pop(submission_id, None)
        self.prebuilt_submissions.discard(submission_id)
        self._clear_submission_jobs(submission_id)
        if submission_id not in self.result:
            return
        _, task_content = self.result[submission_id]
        failure_result = {
            "stdout": "",
            "stderr": err_msg,
            "exitCode": 1,
            "execTime": -1,
            "memoryUsage": -1,
            "status": "CE",
        }
        for case_no in task_content.keys():
            task_content[case_no] = failure_result.copy()
        self.on_submission_complete(submission_id)

    def _prepare_with_build_strategy(
        self,
        submission_id: str,
        problem_id: int,
        meta: Meta,
        submission_path: pathlib.Path,
    ) -> BuildPlan:
        strategy = BuildStrategy(meta.buildStrategy)
        logger().info(
            f"[build] submission={submission_id} strategy={strategy.name}")
        if strategy == BuildStrategy.COMPILE:
            return BuildPlan(needs_make=False)
        if strategy == BuildStrategy.MAKE_NORMAL:
            return prepare_make_normal(
                meta=meta,
                submission_dir=submission_path,
            )
        if strategy == BuildStrategy.MAKE_INTERACTIVE:
            return prepare_make_interactive(
                problem_id=problem_id,
                meta=meta,
                submission_dir=submission_path,
            )
        if strategy == BuildStrategy.MAKE_FUNCTION_ONLY:
            return prepare_function_only_submission(
                problem_id=problem_id,
                meta=meta,
                submission_dir=submission_path,
            )
        raise BuildStrategyError(f"unsupported build strategy: {strategy}")

    def handle(self, submission_id: str, problem_id: int):
        logger().info(
            f"receive submission {submission_id} for problem: {problem_id}.")
        submission_path = self.SUBMISSION_DIR / submission_id
        if not submission_path.exists():
            raise FileNotFoundError(
                f"submission id: {submission_id} file not found.")
        elif not submission_path.is_dir():
            raise NotADirectoryError(f"{submission_path} is not a directory")
        if self.contains(submission_id):
            raise DuplicatedSubmissionIdError(
                f"duplicated submission id {submission_id}.")

        with (submission_path / "meta.json").open() as f:
            submission_config = Meta.parse_obj(json.load(f))
        logger().debug(f"(*_*)[In handle]submission meta: {submission_config}")

        # [Result Init]

        submission_mode = SubmissionMode(submission_config.submissionMode)
        self.problem_ids[submission_id] = problem_id

        # Note: Static Analysis is now handled asynchronously in run() via job.StaticAnalysis

        # prepare custom checker if enabled (non-interactive only)
        self._prepare_custom_checker(
            submission_id=submission_id,
            problem_id=problem_id,
            meta=submission_config,
            submission_path=submission_path,
        )
        self._prepare_custom_scorer(
            submission_id=submission_id,
            problem_id=problem_id,
            meta=submission_config,
            submission_path=submission_path,
        )
        # prepare resource data if enabled
        try:
            if getattr(submission_config, "resourceData", False):
                res_dir = prepare_resource_data(
                    problem_id=problem_id,
                    submission_path=submission_path,
                    asset_paths=getattr(submission_config, "assetPaths", {}),
                )
                if res_dir:
                    self.resource_dirs[submission_id] = res_dir
            if getattr(submission_config, "resourceDataTeacher", False):
                teacher_res_dir = prepare_teacher_resource_data(
                    problem_id=problem_id,
                    submission_path=submission_path,
                    asset_paths=getattr(submission_config, "assetPaths", {}),
                )
                if teacher_res_dir:
                    self.teacher_resource_dirs[submission_id] = teacher_res_dir
        except Exception as exc:
            err_msg = f"resource data preparation failed: {exc}"
            logger().warning(
                "resource data preparation failed [id=%s]: %s",
                submission_id,
                exc,
            )
            task_content = {}
            for ti, task in enumerate(submission_config.tasks):
                for ci in range(task.caseCount):
                    case_no = f"{ti:02d}{ci:02d}"
                    task_content[case_no] = {
                        "stdout": "",
                        "stderr": err_msg,
                        "exitCode": 1,
                        "execTime": -1,
                        "memoryUsage": -1,
                        "status": "JE",
                    }
            self.result[submission_id] = (submission_config, task_content)
            self.on_submission_complete(submission_id)
            return

        # assign submission context
        task_content = {}
        self.result[submission_id] = (submission_config, task_content)
        self.locks[submission_id] = threading.Lock()
        self.compile_locks[submission_id] = threading.Lock()
        self.created_at[submission_id] = datetime.now()
        self.build_strategies[submission_id] = submission_config.buildStrategy
        logger().debug(f"current submissions: {[*self.result.keys()]}")

        # [Build Strategy Plan]
        try:
            build_plan = self._prepare_with_build_strategy(
                submission_id=submission_id,
                problem_id=problem_id,
                meta=submission_config,
                submission_path=submission_path,
            )
        except (BuildStrategyError, Exception) as exc:
            logger().warning(
                f"build strategy failed [id={submission_id}]: {exc}")
            # Report CE instead of crashing/raising
            self.result[submission_id] = (
                submission_config,
                build_sa_ce_task_content(submission_config,
                                         f"Build Failed: {exc}"),
            )
            self.on_submission_complete(submission_id)
            return

        # [Static Analysis] init array for pending work
        tasks_to_run = []

        needs_build = build_plan.needs_make
        if needs_build:
            # Wait for SA before building
            logger().debug(
                f"[build] submission={submission_id} planned to build, waiting for SA"
            )
            self.build_plans[submission_id] = build_plan
            self.build_locks[submission_id] = threading.Lock()
            tasks_to_run.append(job.Build(submission_id=submission_id))

        else:
            if build_plan.finalize:
                build_plan.finalize()
            if not self.compile_need(submission_config.language):
                logger().debug(
                    f"[build] submission={submission_id} marked prebuilt")
                self.prebuilt_submissions.add(submission_id)

        # Prepare pending tasks
        # [Job Dispatching]
        if (not needs_build and not self._is_prebuilt_submission(submission_id)
                and self.compile_need(submission_config.language)):
            tasks_to_run.append(job.Compile(submission_id=submission_id))

        for i, task in enumerate(submission_config.tasks):
            for j in range(task.caseCount):
                case_no = f"{i:02d}{j:02d}"
                task_content[case_no] = None
                tasks_to_run.append(
                    job.Execute(
                        submission_id=submission_id,
                        task_id=i,
                        case_id=j,
                    ))
        self.pending_tasks[submission_id] = tasks_to_run
        try:
            self.queue.put_nowait(
                job.StaticAnalysis(submission_id=submission_id,
                                   problem_id=problem_id))
        except queue.Full as e:
            self.release(submission_id)
            raise e
        # [Static Analysis] end

    def release(self, submission_id: str):
        for v in (
                self.result,
                self.compile_locks,
                self.compile_results,
                self.locks,
                self.created_at,
                self.problem_ids,
        ):
            if submission_id in v:
                del v[submission_id]
        # [Static Analysis] Cleanup
        self.sa_payloads.pop(submission_id, None)
        self.pending_tasks.pop(submission_id, None)
        # [Static Analysis] end

        self.prebuilt_submissions.discard(submission_id)
        self.build_strategies.pop(submission_id, None)
        self.build_plans.pop(submission_id, None)
        self.build_locks.pop(submission_id, None)

        # [Network] Cleanup
        self.network_controller.cleanup(submission_id)
        # [Network] end
        self.custom_checker_info.pop(submission_id, None)
        self.custom_scorer_info.pop(submission_id, None)
        self.checker_payloads.pop(submission_id, None)
        self.artifact_collector.cleanup(submission_id)
        self.resource_dirs.pop(submission_id, None)
        self.teacher_resource_dirs.pop(submission_id, None)

    def run(self):
        self.do_run = True
        logger().debug("start dispatcher loop")
        while True:
            # end the loop
            if not self.do_run:
                logger().debug("exit dispatcher loop")
                break
            # no testcase need to be run
            if self.queue.empty():
                time.sleep(1)
                continue
            # no space for new cotainer now
            if self.container_count >= self.MAX_CONTAINER_SIZE:
                time.sleep(1)
                continue
            # get a case
            _job = self.queue.get()
            submission_id = _job.submission_id
            # if a submission was discarded, it will not appear in the `self.result`
            if not self.contains(submission_id):
                logger().info(f"discarded submission [id={submission_id}]")
                continue
            if self.is_timed_out(submission_id):
                logger().info(f"submission timed out [id={submission_id}]")
                continue
            # get task info
            submission_config, _ = self.result[submission_id]

            # [Static Analysis] Handle Static Analysis Job
            if isinstance(_job, job.StaticAnalysis):
                logger().info(f"Running Static Analysis for {submission_id}")
                submission_path = self.SUBMISSION_DIR / submission_id

                try:
                    rules_json = fetch_problem_rules(_job.problem_id)
                    logger().debug(
                        f"fetched static analysis rules: {rules_json}")
                    is_zip_mode = (SubmissionMode(
                        submission_config.submissionMode) == SubmissionMode.ZIP
                                   )

                    # do SA
                    success, payload, task_content = run_static_analysis(
                        submission_id=submission_id,
                        submission_path=submission_path,
                        meta=submission_config,
                        rules_json=rules_json,
                        is_zip_mode=is_zip_mode,
                    )
                    if payload:
                        self.sa_payloads[submission_id] = payload
                    if success:
                        logger().info(
                            f"Static Analysis succeeded for {submission_id}.  Releasing pending jobs."
                        )
                        # pending_jobs = self.pending_tasks.pop(submission_id, [])
                        # for pj in pending_jobs:
                        #     self.queue.put(pj)
                        self.queue.put(
                            job.NetworkSetup(submission_id=submission_id,
                                             problem_id=_job.problem_id))
                    else:
                        logger().info(
                            f"Static Analysis failed for {submission_id}. Marking CE for all cases."
                        )
                        self._handle_sa_failure(
                            submission_id=submission_id,
                            payload=payload,
                            task_content=task_content,
                        )
                except Exception as e:
                    logger().error(f"Error in SA job for {submission_id}: {e}",
                                   exc_info=True)
                    msg = f"Static Analysis Exception: {e}"
                    fail_content = build_sa_ce_task_content(
                        submission_config,
                        msg,
                    )
                    self._handle_sa_failure(
                        submission_id,
                        {
                            "status": "sys_err",
                            "message": msg
                        },
                        fail_content,
                    )
                continue
            # [Static Analysis] end

            # [Network] Determine Network Mode
            if isinstance(_job, job.NetworkSetup):
                logger().info(f"Setting up network for {submission_id}")
                submission_config, _ = self.result[submission_id]
                logger().debug(
                    f"(*_*)[In NetworkSetup] submission meta: {submission_config}"
                )

                try:
                    self.network_controller.provision_network(
                        submission_id=submission_id,
                        problem_id=_job.problem_id,
                    )
                    pending_jobs = self.pending_tasks.pop(submission_id, [])
                    for pj in pending_jobs:
                        self.queue.put(pj)

                except Exception as e:
                    logger().error(f"Network provision failed: {e}")
                    self._handle_network_failure(submission_id, str(e))
                continue
            # [Network] end

            # 1. Build Job
            if isinstance(_job, job.Build):
                threading.Thread(
                    target=self.build,
                    args=(submission_id, submission_config.language),
                ).start()
                continue

            # Wait for build if needed
            if self._is_build_pending(submission_id):
                self.queue.put(_job)
                time.sleep(0.1)
                continue

            # 2. Compile Job
            if isinstance(_job, job.Compile):
                threading.Thread(
                    target=self.compile,
                    args=(
                        submission_id,
                        submission_config.language,
                    ),
                ).start()
                continue

            # 3. Execution Job
            if (not self._is_prebuilt_submission(submission_id)
                    and self.compile_need(submission_config.language)
                    and self.compile_results.get(submission_id) is None):
                self.queue.put(_job)
            else:
                net_mode = self.network_controller.get_network_mode(
                    submission_id)
                task_info = submission_config.tasks[_job.task_id]
                case_no = f"{_job.task_id:02d}{_job.case_id:02d}"
                logger().info(
                    f"create container [task={submission_id}/{case_no}]")
                logger().debug(f"task info: {task_info}")
                # output path should be the container path
                base_path = self.SUBMISSION_DIR / submission_id / "testcase"
                out_path = str((base_path / f"{case_no}.out").absolute())
                # input path should be the host path
                base_path = self.submission_runner_cwd / submission_id / "testcase"
                in_path = str((base_path / f"{case_no}.in").absolute())

                # debug log
                logger().debug("in path: " + in_path)
                logger().debug("out path: " + out_path)
                # assign a new runner
                threading.Thread(
                    target=self.create_container,
                    args=(
                        submission_id,
                        case_no,
                        task_info.memoryLimit,
                        task_info.timeLimit,
                        in_path,
                        out_path,
                        submission_config.language,
                        submission_config.executionMode,
                        submission_config.teacherFirst,
                        net_mode,  # [Sidecar] Pass network mode
                    ),
                ).start()

    def stop(self):
        self.do_run = False

    # [Standard Methods]
    def compile(
        self,
        submission_id: str,
        lang: Language,
    ):
        if self.compile_locks[submission_id].locked():
            logger().error(
                f"start a compile thread on locked submission {submission_id}")
            return
        if not self.compile_need(lang):
            logger().warning(
                f"try to compile submission {submission_id}"
                f" with language {lang}", )
            return
        with self.compile_locks[submission_id]:
            logger().info(f"start compiling {submission_id}")
            res = SubmissionRunner(
                submission_id=submission_id,
                time_limit=-1,
                mem_limit=-1,
                testdata_input_path="",
                testdata_output_path="",
                lang=["c11", "cpp17"][int(lang)],
                common_dir=str(self._common_dir(submission_id)),
            ).compile()
            self.compile_results[submission_id] = res
            logger().debug(f'finish compiling, get status {res["Status"]}')
            meta_obj, _ = self.result.get(submission_id, (None, None))
            if (res.get("Status") == "AC" and meta_obj
                    and ArtifactCollector.should_collect_binary(meta_obj)):
                try:
                    self.artifact_collector.collect_binary(
                        submission_id=submission_id,
                        src_dir=self._common_dir(submission_id),
                    )
                    self.artifact_collector.upload_binary_only(
                        submission_id=submission_id)
                except Exception as exc:
                    logger().warning(
                        "collect/upload binary after compile failed [id=%s]: %s",
                        submission_id,
                        exc,
                    )

    def build(
        self,
        submission_id: str,
        lang: Language,
    ):
        plan = self.build_plans.get(submission_id)
        if not plan:
            return
        lock = self.build_locks.get(submission_id)
        if lock is None:
            return
        if lock.locked():
            logger().error(
                f"start a build thread on locked submission {submission_id}")
            return

        with lock:
            logger().info(f"start building {submission_id}")
            runner = SubmissionRunner(
                submission_id=submission_id,
                time_limit=-1,
                mem_limit=-1,
                testdata_input_path="",
                testdata_output_path="",
                lang=plan.lang_key or ["c11", "cpp17", "python3"][int(lang)],
                common_dir=str(self._common_dir(submission_id)),
            )
            res = runner.build_with_make()
            if res.get("Status") != "AC":
                self._handle_build_failure(
                    submission_id=submission_id,
                    message=res.get("Stderr") or "make failed",
                )
                return
            try:
                if plan.finalize:
                    plan.finalize()
            except BuildStrategyError as exc:
                self._handle_build_failure(
                    submission_id=submission_id,
                    message=str(exc),
                )
                return
            except Exception as exc:
                self._handle_build_failure(
                    submission_id=submission_id,
                    message=f"build finalization failed: {exc}",
                )
                return
            self.prebuilt_submissions.add(submission_id)
            self.build_plans.pop(submission_id, None)
            self.build_locks.pop(submission_id, None)
            meta_obj, _ = self.result.get(submission_id, (None, None))
            if (meta_obj
                    and ArtifactCollector.should_collect_binary(meta_obj)):
                try:
                    self.artifact_collector.collect_binary(
                        submission_id=submission_id,
                        src_dir=self._common_dir(submission_id),
                    )
                    self.artifact_collector.upload_binary_only(
                        submission_id=submission_id)
                except Exception as exc:
                    logger().warning(
                        "collect/upload binary after build failed [id=%s]: %s",
                        submission_id,
                        exc,
                    )

    def create_container(
        self,
        submission_id: str,
        case_no: str,
        mem_limit: int,
        time_limit: int,
        case_in_path: str,
        case_out_path: str,
        lang: Language,
        execution_mode: ExecutionMode,
        teacher_first: bool = False,
        network_mode: str = "none",
    ):
        lang_key = ["c11", "cpp17", "python3"][int(lang)]
        submission_path = self.SUBMISSION_DIR / submission_id
        meta_obj, _ = self.result.get(submission_id, (None, None))
        collect_artifacts = meta_obj and ArtifactCollector.should_collect_artifacts(
            meta_obj)
        common_dir = self._common_dir(submission_id)
        case_dir = self._case_dir(submission_id, case_no)
        # prepare per-case workdir: clean and copy common + resources
        SANDBOX_UID = 1450
        SANDBOX_GID = 1450
        try:
            if case_dir.exists():
                shutil.rmtree(case_dir)
            case_dir.mkdir(parents=True, exist_ok=True)
            if common_dir.exists():
                shutil.copytree(common_dir,
                                case_dir,
                                dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("cases"))
            # Set permissions for sandbox user to write if allowWrite is enabled
            allow_write_val = bool(getattr(meta_obj, "allowWrite", False))
            if allow_write_val:
                import os
                os.chown(case_dir, SANDBOX_UID, SANDBOX_GID)
                os.chmod(case_dir, 0o755)
                for item in case_dir.rglob("*"):
                    try:
                        os.chown(item, SANDBOX_UID, SANDBOX_GID)
                        if item.is_dir():
                            os.chmod(item, 0o755)
                        else:
                            os.chmod(item, 0o644)
                    except Exception:
                        pass
        except Exception as exc:
            logger().warning(
                "prepare case dir failed [id=%s case=%s]: %s",
                submission_id,
                case_no,
                exc,
            )
            res = {
                "Status": "JE",
                "Stdout": "",
                "Stderr": f"prepare case dir failed: {exc}",
                "Duration": -1,
                "MemUsage": -1,
                "DockerExitCode": 1,
            }
            lock = self.locks.get(submission_id)
            target_fn = self.on_case_complete
            if lock:
                with lock:
                    target_fn(
                        submission_id=submission_id,
                        case_no=case_no,
                        stdout=res["Stdout"],
                        stderr=res["Stderr"],
                        exit_code=res["DockerExitCode"],
                        exec_time=res["Duration"],
                        mem_usage=res["MemUsage"],
                        prob_status=res["Status"],
                    )
            else:
                target_fn(
                    submission_id=submission_id,
                    case_no=case_no,
                    stdout=res["Stdout"],
                    stderr=res["Stderr"],
                    exit_code=res["DockerExitCode"],
                    exec_time=res["Duration"],
                    mem_usage=res["MemUsage"],
                    prob_status=res["Status"],
                )
            return
        # copy resource files for this case (function checks if resource_data/ exists)
        copied_resources = None
        copy_error = None
        try:
            copied_resources = copy_resource_for_case(
                submission_path=submission_path,
                case_dir=case_dir,
                task_no=int(case_no[:2]),
                case_no=int(case_no[2:]),
            )
        except Exception as exc:
            copy_error = exc
            logger().warning(
                "resource copy failed [id=%s case=%s]: %s",
                submission_id,
                case_no,
                exc,
            )
        if copy_error:
            res = {
                "Status": "JE",
                "Stdout": "",
                "Stderr": f"resource copy failed: {copy_error}",
                "Duration": -1,
                "MemUsage": -1,
                "DockerExitCode": 1,
            }
            lock = self.locks.get(submission_id)
            if lock:
                with lock:
                    self.on_case_complete(
                        submission_id=submission_id,
                        case_no=case_no,
                        stdout=res["Stdout"],
                        stderr=res["Stderr"],
                        exit_code=res["DockerExitCode"],
                        exec_time=res["Duration"],
                        mem_usage=res["MemUsage"],
                        prob_status=res["Status"],
                    )
            else:
                self.on_case_complete(
                    submission_id=submission_id,
                    case_no=case_no,
                    stdout=res["Stdout"],
                    stderr=res["Stderr"],
                    exit_code=res["DockerExitCode"],
                    exec_time=res["Duration"],
                    mem_usage=res["MemUsage"],
                    prob_status=res["Status"],
                )
            return
        if collect_artifacts:
            try:
                self.artifact_collector.snapshot_before_case(
                    submission_id=submission_id,
                    task_no=int(case_no[:2]),
                    case_no=int(case_no[2:]),
                    workdir=case_dir,
                )
            except Exception as exc:
                logger().warning(
                    "snapshot before case failed [id=%s case=%s]: %s",
                    submission_id,
                    case_no,
                    exc,
                )
        use_custom_checker = self._use_custom_checker(submission_id)
        checker_info = self.custom_checker_info.get(submission_id, {})
        if ExecutionMode(execution_mode) == ExecutionMode.INTERACTIVE:
            # Fetch teacher language from meta (set by backend) to avoid running teacher with student lang.
            submission_config, _ = self.result.get(submission_id, (None, None))
            teacher_lang_val = (getattr(submission_config, "assetPaths", {})
                                or {}).get("teacherLang")
            student_allow_write = bool(
                getattr(submission_config, "allowWrite", False))
            mapping = {"c": "c11", "cpp": "cpp17", "py": "python3"}
            teacher_lang_key = mapping.get(str(teacher_lang_val or "").lower())
            if teacher_lang_key is None:
                # mark JE for all cases of this submission
                self._mark_submission_je(
                    submission_id=submission_id,
                    message="teacherLang missing/invalid",
                )
                return
            compile_res = self.extract_compile_result(submission_id, lang)
            if self.compile_need(lang) and compile_res.get("Status") == "CE":
                res = compile_res
            else:
                # Prepare teacher case directory with testcase and resources
                teacher_common_dir = submission_path / "teacher" / "common"
                teacher_case_dir = prepare_teacher_for_case(
                    submission_path=submission_path,
                    task_no=int(case_no[:2]),
                    case_no=int(case_no[2:]),
                    teacher_common_dir=teacher_common_dir,
                    copy_testcase=True,
                )
                runner = InteractiveRunner(
                    submission_id=submission_id,
                    time_limit=time_limit,
                    mem_limit=mem_limit,
                    case_in_path=case_in_path,
                    teacher_first=teacher_first,
                    lang_key=lang_key,
                    teacher_lang_key=teacher_lang_key,
                    case_dir=case_dir,
                    student_allow_write=student_allow_write,
                    teacher_case_dir=teacher_case_dir,
                    network_mode=network_mode,  # Pass to InteractiveRunner
                )
                try:
                    self.inc_container()
                    res = runner.run()
                finally:
                    self.dec_container()
                if copied_resources:
                    try:
                        cleanup_resource_files(case_dir, copied_resources)
                    except Exception:
                        pass
        else:
            runner = SubmissionRunner(
                submission_id,
                time_limit,
                mem_limit,
                case_in_path,
                case_out_path,
                lang=lang_key,
                network_mode=network_mode,
                common_dir=str(common_dir),
                case_dir=str(case_dir),
                allow_write=bool(getattr(meta_obj, "allowWrite", False)),
            )
            res = self.extract_compile_result(submission_id, lang)
            if res["Status"] != "CE":
                try:
                    self.inc_container()
                    res = runner.run(skip_diff=use_custom_checker)
                finally:
                    self.dec_container()
                if copied_resources:
                    try:
                        cleanup_resource_files(case_dir, copied_resources)
                    except Exception:
                        pass
            else:
                if copied_resources:
                    try:
                        cleanup_resource_files(case_dir, copied_resources)
                    except Exception:
                        pass
            if use_custom_checker and checker_info.get("error"):
                res = {
                    "Status": "JE",
                    "Stdout": "",
                    "Stderr": checker_info.get("error", ""),
                    "Duration": -1,
                    "MemUsage": -1,
                    "DockerExitCode": 1,
                }
            if use_custom_checker and res.get("Status") not in {
                    "CE", "RE", "TLE", "MLE", "OLE", "JE"
            }:
                checker_path = self._custom_checker_path(submission_id)
                if checker_path:
                    # case_in_path is host path, need to convert to container path for _copy_file
                    # Host: /home/.../Sandbox/submissions/... → Container: /app/submissions/...
                    container_in_path = pathlib.Path(
                        case_in_path.replace(
                            str(self.submission_runner_cwd.parent),
                            str(self.SUBMISSION_DIR.parent)))
                    container_out_path = pathlib.Path(
                        case_out_path.replace(str(self.SUBMISSION_DIR),
                                              str(self.SUBMISSION_DIR)))

                    # Prepare teacher case directory for custom checker
                    # No teacher_common_dir for custom checker (no interactive teacher)
                    teacher_case_dir = prepare_teacher_for_case(
                        submission_path=submission_path,
                        task_no=int(case_no[:2]),
                        case_no=int(case_no[2:]),
                        teacher_common_dir=None,
                        copy_testcase=
                        False,  # custom checker reads from case_in_path
                    )
                    checker_result = run_custom_checker_case(
                        submission_id=submission_id,
                        case_no=case_no,
                        checker_path=checker_path,
                        case_in_path=container_in_path,
                        case_ans_path=container_out_path,
                        student_output=res.get("Stdout", ""),
                        time_limit_ms=time_limit,
                        mem_limit_kb=mem_limit,
                        image=self.custom_checker_image,
                        docker_url=runner.docker_url,
                        student_workdir=case_dir,
                        teacher_dir=teacher_case_dir,
                    )
                    res["Status"] = checker_result["status"]
                    message = checker_result.get("message", "")
                    if message:
                        joined = "\n".join(part for part in [
                            res.get("Stderr", ""),
                            f"[custom_checker] {message}"
                        ] if part)
                        res["Stderr"] = joined
                    self._record_checker_message(
                        submission_id=submission_id,
                        case_no=case_no,
                        status=checker_result["status"],
                        message=message,
                    )
        if collect_artifacts:
            try:
                self.artifact_collector.record_case_artifact(
                    submission_id=submission_id,
                    task_no=int(case_no[:2]),
                    case_no=int(case_no[2:]),
                    workdir=case_dir,
                    stdout=res.get("Stdout", ""),
                    stderr=res.get("Stderr", ""),
                )
            except Exception as exc:
                logger().warning(
                    "collect artifact failed [id=%s case=%s]: %s",
                    submission_id,
                    case_no,
                    exc,
                )
        logger().info(f"finish task {submission_id}/{case_no}")
        with self.locks[submission_id]:
            self.on_case_complete(
                submission_id=submission_id,
                case_no=case_no,
                stdout=res.get("Stdout", ""),
                stderr=res.get("Stderr", ""),
                exit_code=res.get("DockerExitCode", -1),
                exec_time=res.get("Duration", -1),
                mem_usage=res.get("MemUsage", -1),
                prob_status=res["Status"],
            )

        try:
            if case_dir.exists():
                shutil.rmtree(case_dir)
        except Exception:
            pass

    def extract_compile_result(self, submission_id: str, lang: Language):
        """
        Get compile result for specific submission. If the language does
        not need to be compiled, return a AC result.
        """
        try:
            return self.compile_results[submission_id]
        except KeyError:
            if self._is_prebuilt_submission(submission_id):
                status = "AC"
            else:
                status = "CE" if self.compile_need(lang) else "AC"
            return {"Status": status}

    def on_case_complete(
        self,
        submission_id: str,
        case_no: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        exec_time: float,
        mem_usage: int,
        prob_status: str,
    ):
        if submission_id not in self.result:
            raise SubmissionIdNotFoundError(
                f"Unexisted id {submission_id} recieved")

        _, results = self.result[submission_id]
        if case_no not in results:
            raise ValueError(f"Unexisted case {case_no} recieved")
        results[case_no] = {
            "stdout": stdout,
            "stderr": stderr,
            "exitCode": exit_code,
            "execTime": exec_time,
            "memoryUsage": mem_usage,
            "status": prob_status,
        }
        _results = [k for k, v in results.items() if not v]
        logger().debug(f"tasks wait for judge: {_results}")
        if all(results.values()):
            self.on_submission_complete(submission_id)

    def on_submission_complete(self, submission_id: str):
        if not self.contains(submission_id):
            raise SubmissionIdNotFoundError(f"{submission_id} not found!")
        if self.testing:
            logger().info(
                f"skip submission post processing in testing [submission_id={submission_id}]"
            )
            return True
        meta, results = self.result[submission_id]
        sa_payload = self.sa_payloads.get(submission_id)
        checker_payload = self.checker_payloads.get(submission_id)
        # parse results

        submission_result = {}
        for no, r in results.items():
            task_no = int(no[:2])
            case_no = int(no[2:])
            if task_no not in submission_result:
                submission_result[task_no] = {}
            submission_result[task_no][case_no] = r

        for task_no, cases in submission_result.items():
            assert [*cases.keys()] == [*range(len(cases))]
            submission_result[task_no] = [*cases.values()]
        assert [*submission_result.keys()] == [*range(len(submission_result))]
        submission_result = [*submission_result.values()]

        scoring_payload, status_override = self._run_custom_scorer_if_needed(
            submission_id=submission_id,
            meta=meta,
            submission_result=submission_result,
            sa_payload=sa_payload,
            checker_payload=checker_payload,
        )

        submission_data = {
            "tasks": submission_result,
            "token": config.SANDBOX_TOKEN,
        }
        if sa_payload is not None:
            submission_data["staticAnalysis"] = sa_payload
        if checker_payload is not None:
            submission_data["checker"] = checker_payload
        if scoring_payload is not None:
            submission_data["scoring"] = scoring_payload
        if status_override:
            submission_data["statusOverride"] = status_override
        logger().info(f"send to BE [submission_id={submission_id}]")
        resp = None
        try:
            resp = requests.put(
                f"{config.BACKEND_API}/submission/{submission_id}/complete",
                json=submission_data,
            )
            logger().debug(
                f"get BE response: [{resp.status_code}] {resp.text}", )
            # clear
            if resp.ok:
                # collect binary lazily
                try:
                    if self.artifact_collector.should_collect_binary(meta):
                        self.artifact_collector.collect_binary(
                            submission_id=submission_id,
                            src_dir=self._common_dir(submission_id),
                        )
                except Exception as exc:
                    logger().warning(
                        "collect binary failed [id=%s]: %s",
                        submission_id,
                        exc,
                    )
                try:
                    self.artifact_collector.upload_all(submission_id)
                except Exception as exc:
                    logger().warning(
                        "upload artifacts failed [id=%s]: %s",
                        submission_id,
                        exc,
                    )
                file_manager.clean_data(submission_id)
            # copy to another place
            else:
                file_manager.backup_data(submission_id)
        except Exception as exc:
            logger().warning(
                "send to BE failed [submission_id=%s]: %s",
                submission_id,
                exc,
            )
            file_manager.backup_data(submission_id)
        finally:
            self.release(submission_id)

    def get_static_analysis_rules(self, problem_id: int):
        logger().debug(
            f"Try to fetch problem rules. [problem_id: {problem_id}]")
        try:
            rules = fetch_problem_rules(problem_id)
            return rules
        except Exception as e:
            logger().info(
                f"Report to backend failed (Expected in local test): {e}")
