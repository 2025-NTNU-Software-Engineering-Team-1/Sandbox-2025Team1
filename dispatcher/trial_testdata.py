"""
Trial Test Data Preparation

Handles preparation of custom test cases for Trial Submissions.
"""

import io
import shutil
from pathlib import Path
from zipfile import ZipFile
from typing import Optional

import requests as rq

from .constant import ExecutionMode
from .utils import logger
from .config import BACKEND_API, SANDBOX_TOKEN
from .testdata import (
    get_custom_testdata_root,
    handle_problem_response,
)
from .asset_cache import ensure_custom_asset


def download_custom_testcases(custom_testcases_path: str) -> bytes:
    """
    Download custom test cases ZIP from MinIO via backend.
    
    Args:
        custom_testcases_path: MinIO path to custom test cases
    
    Returns:
        ZIP file content as bytes
    """
    logger().debug(
        f"Downloading custom testcases from: {custom_testcases_path}")

    # The backend should provide an endpoint to download from MinIO path
    # For now, we assume the path is accessible via a generic download endpoint
    resp = rq.get(
        f"{BACKEND_API}/trial-submission/download-testcases",
        params={
            "token": SANDBOX_TOKEN,
            "path": custom_testcases_path,
        },
    )
    handle_problem_response(resp)
    return resp.content


def convert_custom_testcase_filenames(source_dir: Path,
                                      target_dir: Path) -> int:
    """
    Convert custom testcase filenames from sequential format to task/case format.
    
    Input format: 0001.in, 0002.in, 0003.in, ...
    Output format: 0000.in, 0001.in, 0002.in, ... (all in task 00)
    
    Args:
        source_dir: Directory containing source .in files
        target_dir: Directory to write converted files
    
    Returns:
        Number of files converted
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    # Get all .in files sorted
    in_files = sorted(source_dir.glob("*.in"))

    count = 0
    for idx, in_file in enumerate(in_files):
        # Convert to task 00, case idx format
        new_name = f"00{idx:02d}.in"
        target_path = target_dir / new_name
        shutil.copy(in_file, target_path)
        count += 1
        logger().debug(f"Converted {in_file.name} -> {new_name}")

    return count


def copy_checker_to_testdata(problem_id: int, testdata_dir: Path) -> bool:
    """
    Copy custom checker to test data directory if the problem has one.
    
    Args:
        problem_id: Problem ID
        testdata_dir: Target test data directory
    
    Returns:
        True if checker was copied
    """
    try:
        checker_path = ensure_custom_asset(problem_id, "checker")
        if checker_path and checker_path.exists():
            checker_dir = testdata_dir / "checker"
            checker_dir.mkdir(parents=True, exist_ok=True)
            target = checker_dir / "custom_checker.py"
            shutil.copy(checker_path, target)
            logger().debug(f"Copied checker for problem {problem_id}")
            return True
    except Exception as exc:
        logger().warning(
            f"Failed to copy checker for problem {problem_id}: {exc}")
    return False


def prepare_custom_testdata(
    problem_id: int,
    submission_id: str,
    custom_testcases_path: str,
    meta,
) -> Path:
    """
    Prepare custom test data for a Trial Submission.
    
    This function:
    1. Downloads custom .in files from MinIO
    2. Converts filenames to task/case format (all in task 00)
    3. Generates .out files using AC code (unless Interactive mode)
    4. Copies checker if problem uses custom checker
    
    Args:
        problem_id: Problem ID
        submission_id: Trial submission ID
        custom_testcases_path: MinIO path to custom test cases ZIP
        meta: Problem meta (contains executionMode, customChecker, etc.)
    
    Returns:
        Path to prepared test data directory
    """
    from .ac_code import generate_ac_outputs

    custom_dir = get_custom_testdata_root(submission_id)
    custom_dir.mkdir(parents=True, exist_ok=True)

    # Check if .in files already exist (rejudge scenario)
    existing_in_files = list(custom_dir.glob("*.in"))

    if existing_in_files:
        # Rejudge: only remove .out files, keep .in files
        logger().info(
            f"Rejudge detected: removing existing .out files for submission {submission_id}"
        )
        for out_file in custom_dir.glob("*.out"):
            out_file.unlink()
        case_count = len(existing_in_files)
    else:
        # First submission: download and extract .in files
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                testcases_content = download_custom_testcases(
                    custom_testcases_path)
                with ZipFile(io.BytesIO(testcases_content)) as zf:
                    zf.extractall(temp_path)
            except Exception as exc:
                logger().error(
                    f"Failed to download/extract custom testcases: {exc}")
                raise ValueError(f"Failed to download custom testcases: {exc}")

            # Convert filenames (0001.in -> 0000.in, all in task 00)
            case_count = convert_custom_testcase_filenames(
                temp_path, custom_dir)
            if case_count == 0:
                raise ValueError("No .in files found in custom testcases")

    logger().info(
        f"Prepared {case_count} custom test cases for submission {submission_id}"
    )

    # 3. Generate .out files using AC code (unless Interactive mode)
    execution_mode = getattr(meta, "executionMode", ExecutionMode.GENERAL)
    if isinstance(execution_mode, int):
        execution_mode = ExecutionMode(execution_mode)

    if execution_mode != ExecutionMode.INTERACTIVE:
        try:
            # Get time/memory limits from meta if available
            time_limit = 30000  # Default 30s for AC code
            mem_limit = 1048576  # Default 1GB
            if hasattr(meta, "tasks") and meta.tasks:
                time_limit = max(t.timeLimit
                                 for t in meta.tasks) * 2  # Double the limit
                mem_limit = max(t.memoryLimit for t in meta.tasks) * 2

            generate_ac_outputs(problem_id, custom_dir, time_limit, mem_limit)
        except Exception as exc:
            logger().error(f"Failed to generate outputs with AC code: {exc}")
            raise ValueError(f"Failed to generate test outputs: {exc}")
    else:
        logger().info(f"Skipping output generation for Interactive mode")

    # 4. Copy checker if problem uses custom checker
    if getattr(meta, "customChecker", False):
        copy_checker_to_testdata(problem_id, custom_dir)

    return custom_dir
