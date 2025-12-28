"""
Factory functions for creating standardized result dictionaries.

This module provides consistent result structures for:
- Case results (task_content format, lowercase keys)
- Runner results (execution result format, uppercase keys)
- Checker/Scorer results
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .meta import Meta


def make_case_result(
    status: str,
    stderr: str = "",
    stdout: str = "",
    exit_code: int = 1,
    exec_time: float = -1,
    mem_usage: int = -1,
) -> dict:
    """
    Build a single case result (lowercase keys, used in task_content).
    
    Args:
        status: Result status ("JE", "CE", "AE", "AC", "WA", "TLE", "MLE", "RE", "OLE")
        stderr: Error output
        stdout: Standard output
        exit_code: Process exit code
        exec_time: Execution time in ms
        mem_usage: Memory usage in KB
    
    Returns:
        Case result dictionary
    """
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exitCode": exit_code,
        "execTime": exec_time,
        "memoryUsage": mem_usage,
        "status": status,
    }


def make_runner_result(
    status: str,
    stderr: str = "",
    stdout: str = "",
    duration: float = -1,
    mem_usage: int = -1,
    docker_exit_code: int = 1,
) -> dict:
    """
    Build a runner result (uppercase keys, used in create_container).
    
    Args:
        status: Result status ("JE", "CE", "AC", "WA", "TLE", "MLE", "RE", "OLE")
        stderr: Error output
        stdout: Standard output
        duration: Execution duration in ms
        mem_usage: Memory usage in KB
        docker_exit_code: Docker container exit code
    
    Returns:
        Runner result dictionary
    """
    return {
        "Status": status,
        "Stdout": stdout,
        "Stderr": stderr,
        "Duration": duration,
        "MemUsage": mem_usage,
        "DockerExitCode": docker_exit_code,
    }


def make_all_cases_result(
    meta: "Meta",
    status: str,
    stderr: str = "",
) -> dict:
    """
    Build results for all cases in a submission (used for submission-wide failures).
    
    Args:
        meta: Submission metadata containing task information
        status: Result status to apply to all cases
        stderr: Error message to include in all cases
    
    Returns:
        Dictionary mapping case_no to case results
    """
    task_content = {}
    for ti, task in enumerate(meta.tasks):
        for ci in range(task.caseCount):
            case_no = f"{ti:02d}{ci:02d}"
            task_content[case_no] = make_case_result(status=status,
                                                     stderr=stderr)
    return task_content


def make_checker_result(
    status: str,
    message: str = "",
    stdout: str = "",
    stderr: str = "",
) -> dict:
    """
    Build a custom checker result.
    
    Args:
        status: Result status ("AC", "WA", "JE", etc.)
        message: Checker message
        stdout: Checker stdout
        stderr: Checker stderr
    
    Returns:
        Checker result dictionary
    """
    return {
        "status": status,
        "message": message,
        "stdout": stdout,
        "stderr": stderr,
    }


def make_scorer_result(
    status: str,
    score: float = 0,
    message: str = "",
    stdout: str = "",
    stderr: str = "",
) -> dict:
    """
    Build a custom scorer result.
    
    Args:
        status: Result status ("AC", "JE", etc.)
        score: Computed score
        message: Scorer message
        stdout: Scorer stdout
        stderr: Scorer stderr
    
    Returns:
        Scorer result dictionary
    """
    return {
        "status": status,
        "score": score,
        "message": message,
        "stdout": stdout,
        "stderr": stderr,
    }
