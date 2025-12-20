import shutil
import textwrap
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import TESTDATA_ROOT
from .asset_cache import ensure_custom_asset, AssetNotFoundError
from .result_factory import make_checker_result
from runner.path_utils import PathTranslator
from runner.custom_checker_runner import CustomCheckerRunner, CustomCheckerError
from .constant import ExecutionMode


def ensure_custom_checker(problem_id: int, submission_path: Path,
                          execution_mode: ExecutionMode) -> Optional[Path]:
    """Download/cache custom checker and copy into submission folder.

    Returns submission-local checker path, or None if execution mode
    blocks custom checker (e.g., interactive).
    """
    if execution_mode == ExecutionMode.INTERACTIVE:
        return None
    try:
        checker_path = ensure_custom_asset(problem_id, "checker")
    except AssetNotFoundError as exc:
        raise CustomCheckerError(str(exc)) from exc
    except Exception as exc:
        raise CustomCheckerError(
            f"custom checker asset not found: {exc}") from exc
    # copy to submission workspace for isolation
    submission_checker_dir = submission_path / "checker"
    submission_checker_dir.mkdir(parents=True, exist_ok=True)
    target = submission_checker_dir / "custom_checker.py"
    shutil.copyfile(checker_path, target)
    return target


def run_custom_checker_case(
    submission_id: str,
    case_no: str,
    checker_path: Path,
    case_in_path: Path,
    case_ans_path: Path,
    student_output: str,
    time_limit_ms: int,
    mem_limit_kb: int,
    image: str,
    docker_url: str,
    student_workdir: Path | None = None,
    teacher_dir: Path | None = None,
) -> Dict[str, str]:
    """Execute custom checker for a single case and return status/message."""
    workdir = checker_path.parent / "work" / case_no
    workdir.mkdir(parents=True, exist_ok=True)

    try:
        # Prepare files
        _copy_file(case_in_path, workdir / "input.in")
        _copy_file(case_ans_path, workdir / "answer.out")
        (workdir / "student.out").write_text(student_output)
        local_checker = workdir / "custom_checker.py"
        shutil.copyfile(checker_path, local_checker)

        translator = PathTranslator()
        host_workdir = translator.to_host(workdir)
        student_dir_host = translator.to_host(student_workdir) if (
            student_workdir is not None) else None
        teacher_dir_host = translator.to_host(teacher_dir) if (
            teacher_dir is not None) else None

        runner = CustomCheckerRunner(
            submission_id=submission_id,
            case_no=case_no,
            image=image,
            docker_url=docker_url,
            workdir=str(host_workdir),
            checker_relpath="custom_checker.py",
            time_limit_ms=time_limit_ms,
            mem_limit_kb=mem_limit_kb,
            student_dir=str(student_dir_host)
            if student_dir_host is not None else None,
            teacher_dir=str(teacher_dir_host)
            if teacher_dir_host is not None else None,
        )
        result = runner.run()
    except CustomCheckerError as exc:
        _cleanup(workdir)
        return make_checker_result(status="JE", message=str(exc))
    finally:
        _cleanup(workdir)

    status, message = _parse_checker_output(result.get("stdout", ""))
    exit_code = result.get("exit_code", 1)
    stderr = result.get("stderr", "")
    if status is None:
        status = "JE"
        message = message or "Invalid custom checker output"
    if exit_code != 0:
        status = "JE"
        if stderr:
            message = stderr
    if not message and stderr:
        message = stderr
    return {
        "status": status,
        "message": message or "",
        "stdout": result.get("stdout", ""),
        "stderr": stderr,
    }


def _parse_checker_output(raw_stdout: str) -> Tuple[Optional[str], str]:
    status = None
    message = ""
    for line in raw_stdout.splitlines():
        if line.startswith("STATUS:"):
            status = line.split("STATUS:", 1)[1].strip()
        elif line.startswith("MESSAGE:"):
            message = line.split("MESSAGE:", 1)[1].strip()
    if status not in {"AC", "WA"}:
        return None, message or raw_stdout
    return status, message


def _copy_file(src: Path, dst: Path):
    if not src.exists():
        raise CustomCheckerError(f"missing checker dependency: {src.name}")
    shutil.copyfile(src, dst)


def _cleanup(path: Path):
    try:
        if path.exists():
            shutil.rmtree(path)
    except Exception:
        # best effort cleanup only
        pass
