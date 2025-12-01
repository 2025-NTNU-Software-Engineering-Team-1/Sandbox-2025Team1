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

from .static_analysis import run_static_analysis, build_sa_ce_task_content
from .custom_checker import ensure_custom_checker, run_custom_checker_case
from .custom_scorer import ensure_custom_scorer, run_custom_scorer


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
        # flag to decided whether the thread should run
        self.do_run = True
        # submission location
        self.SUBMISSION_DIR = config.SUBMISSION_DIR
        # task queue
        # type Queue[Tuple[submission_id, task_no]]
        self.MAX_TASK_COUNT = queue_limit
        self.queue = queue.Queue(self.MAX_TASK_COUNT)
        # task result
        # type: Dict[submission_id, Tuple[submission_info, List[result]]]
        self.result = {}
        # threading locks for each submission
        self.locks = {}
        self.compile_locks = {}
        self.compile_results = {}
        self.problem_ids = {}
        # manage containers
        self.MAX_CONTAINER_SIZE = container_limit
        self.container_count_lock = threading.Lock()
        self.container_count = 0
        # read cwd from submission runner config
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
        self.prebuilt_submissions = set()
        self.build_strategies = {}
        self.build_plans = {}
        self.build_locks = {}
        self.sa_payloads = {}

    def compile_need(self, lang: Language):
        return lang in {Language.C, Language.CPP}

    def contains(self, submission_id: str):
        return submission_id in self.result

    def inc_container(self):
        with self.container_count_lock:
            self.container_count += 1

    def dec_container(self):
        with self.container_count_lock:
            self.container_count -= 1

    def is_timed_out(self, submission_id: str):
        if not self.contains(submission_id):
            return False
        delta = (datetime.now() - self.created_at[submission_id]).seconds
        return delta > self.timeout

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

    def _is_prebuilt_submission(self, submission_id: str) -> bool:
        return submission_id in self.prebuilt_submissions

    def _is_build_pending(self, submission_id: str) -> bool:
        return submission_id in self.build_plans

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
        """Handle build/make failure by clearing queue and finalizing as CE."""
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
        # Run the build helper for this submission so dispatcher can decide
        # whether compile jobs are still needed.
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
        """
        handle a submission, save its config and push into task queue
        """
        logger().info(
            f"receive submission {submission_id} for problem: {problem_id}.")
        submission_path = self.SUBMISSION_DIR / submission_id
        # check whether the submission directory exist
        if not submission_path.exists():
            raise FileNotFoundError(
                f"submission id: {submission_id} file not found.")
        elif not submission_path.is_dir():
            raise NotADirectoryError(f"{submission_path} is not a directory")
        # duplicated
        if self.contains(submission_id):
            raise DuplicatedSubmissionIdError(
                f"duplicated submission id {submission_id}.")
        # read submission meta
        with (submission_path / "meta.json").open() as f:
            submission_config = Meta.parse_obj(json.load(f))

        submission_mode = SubmissionMode(submission_config.submissionMode)
        is_zip_mode = submission_mode == SubmissionMode.ZIP
        self.problem_ids[submission_id] = problem_id

        # [Start] static analysis
        rules_json = fetch_problem_rules(problem_id)
        success, payload, task_content = run_static_analysis(
            submission_id=submission_id,
            submission_path=submission_path,
            meta=submission_config,
            rules_json=rules_json,
            is_zip_mode=is_zip_mode,
        )
        if payload:
            self.sa_payloads[submission_id] = payload
        if rules_json and not success:
            self.result[submission_id] = (
                submission_config,
                task_content or build_sa_ce_task_content(
                    submission_config, "Static Analysis Not Passed"),
            )
            self.on_submission_complete(submission_id)
            return
        # [End] static analysis

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

        # assign submission context
        task_content = {}
        self.result[submission_id] = (submission_config, task_content)
        self.locks[submission_id] = threading.Lock()
        self.compile_locks[submission_id] = threading.Lock()
        self.created_at[submission_id] = datetime.now()
        self.build_strategies[submission_id] = submission_config.buildStrategy
        logger().debug(f"current submissions: {[*self.result.keys()]}")
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
        needs_build = build_plan.needs_make
        if needs_build:
            logger().debug(f"[build] submission={submission_id} queued")
            self.build_plans[submission_id] = build_plan
            self.build_locks[submission_id] = threading.Lock()
            self.queue.put_nowait(job.Build(submission_id=submission_id))
        else:
            if build_plan.finalize:
                build_plan.finalize()
            if not self.compile_need(submission_config.language):
                logger().debug(
                    f"[build] submission={submission_id} marked prebuilt")
                self.prebuilt_submissions.add(submission_id)

        logger().debug(f"current submissions: {[*self.result.keys()]}")
        try:
            if (not needs_build
                    and not self._is_prebuilt_submission(submission_id)
                    and self.compile_need(submission_config.language)):
                self.queue.put_nowait(job.Compile(submission_id=submission_id))
            for i, task in enumerate(submission_config.tasks):
                for j in range(task.caseCount):
                    case_no = f"{i:02d}{j:02d}"
                    task_content[case_no] = None
                    _job = job.Execute(
                        submission_id=submission_id,
                        task_id=i,
                        case_id=j,
                    )
                    self.queue.put_nowait(_job)
        except queue.Full as e:
            self.release(submission_id)
            raise e

    def release(self, submission_id: str):
        """
        Release variable about submission
        """
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
        self.prebuilt_submissions.discard(submission_id)
        self.build_strategies.pop(submission_id, None)
        self.build_plans.pop(submission_id, None)
        self.build_locks.pop(submission_id, None)
        self.sa_payloads.pop(submission_id, None)
        self.custom_checker_info.pop(submission_id, None)
        self.custom_scorer_info.pop(submission_id, None)
        self.checker_payloads.pop(submission_id, None)

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
            if not isinstance(
                    _job, job.Build) and self._is_build_pending(submission_id):
                self.queue.put(_job)
                time.sleep(0.1)
                continue
            if isinstance(_job, job.Compile):
                threading.Thread(
                    target=self.compile,
                    args=(
                        submission_id,
                        submission_config.language,
                    ),
                ).start()
            elif isinstance(_job, job.Build):
                threading.Thread(
                    target=self.build,
                    args=(submission_id, submission_config.language),
                ).start()
                continue
            # if this submission needs compile and it haven't finished
            elif (not self._is_prebuilt_submission(submission_id)
                  and self.compile_need(submission_config.language)
                  and self.compile_results.get(submission_id) is None):
                self.queue.put(_job)
            else:
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
                    ),
                ).start()

    def stop(self):
        self.do_run = False

    def compile(
        self,
        submission_id: str,
        lang: Language,
    ):
        # another thread is compiling this submission, bye
        if self.compile_locks[submission_id].locked():
            logger().error(
                f"start a compile thread on locked submission {submission_id}")
            return
        # this submission should not be compiled!
        if not self.compile_need(lang):
            logger().warning(
                f"try to compile submission {submission_id}"
                f" with language {lang}", )
            return
        # compile this submission. don't forget to acquire the lock
        with self.compile_locks[submission_id]:
            logger().info(f"start compiling {submission_id}")
            res = SubmissionRunner(
                submission_id=submission_id,
                time_limit=-1,
                mem_limit=-1,
                testdata_input_path="",
                testdata_output_path="",
                lang=["c11", "cpp17"][int(lang)],
            ).compile()
            self.compile_results[submission_id] = res
            logger().debug(f'finish compiling, get status {res["Status"]}')

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
    ):
        lang_key = ["c11", "cpp17", "python3"][int(lang)]
        use_custom_checker = self._use_custom_checker(submission_id)
        checker_info = self.custom_checker_info.get(submission_id, {})
        if ExecutionMode(execution_mode) == ExecutionMode.INTERACTIVE:
            # Fetch teacher language from meta (set by backend) to avoid running teacher with student lang.
            submission_config, _ = self.result.get(submission_id, (None, None))
            teacher_lang_val = (getattr(submission_config, "assetPaths", {})
                                or {}).get("teacherLang")
            mapping = {"c": "c11", "cpp": "cpp17", "py": "python3"}
            teacher_lang_key = mapping.get(str(teacher_lang_val or "").lower())
            if teacher_lang_key is None:
                # mark JE for all cases of this submission
                self._mark_submission_je(
                    submission_id=submission_id,
                    message="teacherLang missing/invalid",
                )
                return
            runner = InteractiveRunner(
                submission_id=submission_id,
                time_limit=time_limit,
                mem_limit=mem_limit,
                case_in_path=case_in_path,
                teacher_first=teacher_first,
                lang_key=lang_key,
                teacher_lang_key=teacher_lang_key,
            )
            try:
                self.inc_container()
                res = runner.run()
            finally:
                self.dec_container()
        else:
            runner = SubmissionRunner(
                submission_id,
                time_limit,
                mem_limit,
                case_in_path,
                case_out_path,
                lang=lang_key,
            )
            res = self.extract_compile_result(submission_id, lang)
            # Execute if compile successfully
            if res["Status"] != "CE":
                try:
                    self.inc_container()
                    res = runner.run(skip_diff=use_custom_checker)
                finally:
                    self.dec_container()
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
        logger().info(f"finish task {submission_id}/{case_no}")
        # truncate long stdout/stderr
        _res = res.copy()
        for k in ("Stdout", "Stderr"):
            _res[k] = textwrap.shorten(_res.get(k, ""), 37, placeholder="...")
        logger().debug(f"runner result: {_res}")
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
        exec_time: int,
        mem_usage: int,
        prob_status: str,
    ):
        # if id not exists
        if submission_id not in self.result:
            raise SubmissionIdNotFoundError(
                f"Unexisted id {submission_id} recieved")
        # update case result
        _, results = self.result[submission_id]
        if case_no not in results:
            raise ValueError(f"{submission_id}/{case_no} not found.")
        results[case_no] = {
            "stdout": stdout,
            "stderr": stderr,
            "exitCode": exit_code,
            "execTime": exec_time,
            "memoryUsage": mem_usage,
            "status": prob_status,
        }
        # check completion
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
        # convert to list and check
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
            "token": config.SANDBOX_TOKEN
        }
        if sa_payload is not None:
            submission_data["staticAnalysis"] = sa_payload
        if checker_payload is not None:
            submission_data["checker"] = checker_payload
        if scoring_payload is not None:
            submission_data["scoring"] = scoring_payload
        if status_override:
            submission_data["statusOverride"] = status_override
        self.release(submission_id)
        logger().info(f"send to BE [submission_id={submission_id}]")
        resp = requests.put(
            f"{config.BACKEND_API}/submission/{submission_id}/complete",
            json=submission_data,
        )
        logger().debug(f"get BE response: [{resp.status_code}] {resp.text}", )
        # clear
        if resp.ok:
            file_manager.clean_data(submission_id)
        # copy to another place
        else:
            file_manager.backup_data(submission_id)

    def get_static_analysis_rules(self, problem_id: int):
        logger().debug(
            f"Try to fetch problem rules. [problem_id: {problem_id}]")
        try:
            rules = fetch_problem_rules(problem_id)
            return rules
        except Exception as e:
            logger().warning(
                f"Do not fetch problem rules. [problem_id: {problem_id}] {e}")
            return None
