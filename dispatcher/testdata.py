import io
import json
import secrets
import shutil
import hashlib
from pathlib import Path
from zipfile import ZipFile
import requests as rq

from .constant import BuildStrategy, ExecutionMode, Language, SubmissionMode
from .meta import Meta
from .file_manager import _safe_extract_zip
from .utils import (
    get_redis_client,
    logger,
)
from .config import (
    BACKEND_API,
    SANDBOX_TOKEN,
    TESTDATA_ROOT,
)

META_DIR = TESTDATA_ROOT / "meta"
META_DIR.mkdir(exist_ok=True)


def calc_checksum(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def handle_problem_response(resp: rq.Response):
    if resp.status_code == 404:
        raise ValueError("Problem not found")
    if resp.status_code == 401:
        raise PermissionError()
    if not resp.ok:
        logger().error(f"Error during get problem data [resp: {resp.text}]")
        raise RuntimeError()


# TODO: Schema validation
def fetch_problem_meta(problem_id: int) -> str:
    logger().debug(f"fetch problem meta [problem_id: {problem_id}]")
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/meta",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)
    content = json.dumps(resp.json()["data"])
    (META_DIR / f"{problem_id}.json").write_text(content)
    return content


def fetch_problem_asset(problem_id: int, asset_type: str) -> bytes:
    logger().debug(
        f"fetch problem asset [problem_id: {problem_id}, asset_type: {asset_type}]"
    )
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/asset/{asset_type}",
        params={
            "token": SANDBOX_TOKEN,
            "assetType": asset_type,
        },
    )
    handle_problem_response(resp)
    return resp.content


def get_problem_meta(problem_id: int, language: Language) -> Meta:
    meta_path = META_DIR / f"{problem_id}.json"
    if not meta_path.exists():
        fetch_problem_meta(problem_id)
    obj = json.load(meta_path.open())
    obj["language"] = int(language)
    obj.setdefault("submissionMode", int(SubmissionMode.CODE))
    exec_mode = obj.get("executionMode", ExecutionMode.GENERAL.value)
    if isinstance(exec_mode, str):
        mapping = {
            "general": ExecutionMode.GENERAL.value,
            "functionOnly": ExecutionMode.FUNCTION_ONLY.value,
            "interactive": ExecutionMode.INTERACTIVE.value,
        }
        exec_mode = mapping.get(exec_mode, ExecutionMode.GENERAL.value)
    obj["executionMode"] = exec_mode
    build_strategy = obj.get("buildStrategy", BuildStrategy.COMPILE.value)
    if isinstance(build_strategy, str):
        mapping = {
            "compile": BuildStrategy.COMPILE.value,
            "makeNormal": BuildStrategy.MAKE_NORMAL.value,
            "makeFunctionOnly": BuildStrategy.MAKE_FUNCTION_ONLY.value,
            "makeInteractive": BuildStrategy.MAKE_INTERACTIVE.value,
        }
        build_strategy = mapping.get(build_strategy,
                                     BuildStrategy.COMPILE.value)
    obj["buildStrategy"] = int(build_strategy)
    obj.setdefault("assetPaths", {})
    obj.setdefault("teacherFirst", False)
    obj.setdefault("customChecker", False)
    if obj.get("assetPaths",
               {}).get("checker") and not obj.get("checkerAsset"):
        obj["checkerAsset"] = obj["assetPaths"]["checker"]
    scorer_asset = (obj.get("assetPaths", {}) or {}).get("scoring_script")
    scoring_script = obj.get("scoringScript", False)
    if isinstance(scoring_script, dict):
        scoring_script = scoring_script.get("custom", False)
    obj["scoringScript"] = bool(scoring_script)
    if scorer_asset and not obj.get("scorerAsset"):
        obj["scorerAsset"] = scorer_asset
    obj.setdefault("artifactCollection", [])
    obj.setdefault("resourceData", False)
    return Meta.parse_obj(obj)


def get_problem_root(problem_id: int) -> Path:
    return TESTDATA_ROOT / str(problem_id)


def fetch_testdata(problem_id: int):
    """
    Fetch testdata from backend server
    """
    logger().debug(f"fetch problem testdata [problem_id: {problem_id}]")
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/testdata",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)
    return resp.content


def get_checksum(problem_id: int) -> str:
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/checksum",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)
    return resp.json()["data"]


def ensure_testdata(problem_id: int):
    """
    Ensure the testdata of problem is up to date
    """
    client = get_redis_client()
    key = f"problem-{problem_id}-checksum"
    lock_key = f"{key}-lock"
    with client.lock(lock_key, timeout=60):
        curr_checksum = client.get(key)
        if curr_checksum is not None:
            curr_checksum = curr_checksum.decode()
            checksum = get_checksum(problem_id)
            if secrets.compare_digest(curr_checksum, checksum):
                logger().debug(
                    f"problem testdata is up to date [problem_id: {problem_id}]"
                )
                return
        logger().info(f"refresh problem testdata [problem_id: {problem_id}]")
        testdata = fetch_testdata(problem_id)
        problem_root = get_problem_root(problem_id)
        if problem_root.exists():
            shutil.rmtree(problem_root)
        with ZipFile(io.BytesIO(testdata)) as zf:
            _safe_extract_zip(zf, problem_root)
        meta = fetch_problem_meta(problem_id)
        checksum = calc_checksum(testdata + meta.encode())
        client.setex(key, 600, checksum)


# === Trial Submission Support ===

# Directory for trial-specific test data
TRIAL_TESTDATA_DIR = TESTDATA_ROOT / "trial"
TRIAL_TESTDATA_DIR.mkdir(exist_ok=True)


def get_public_testdata_root(problem_id: int) -> Path:
    """Get the path for public test data (Trial Mode)."""
    return TESTDATA_ROOT / str(problem_id) / "public"


def get_custom_testdata_root(submission_id: str) -> Path:
    """Get the path for custom test data (Trial Mode, per-submission)."""
    return TRIAL_TESTDATA_DIR / submission_id


def fetch_public_testdata(problem_id: int) -> bytes:
    """Fetch public test data ZIP from backend server."""
    logger().debug(f"fetch public testdata [problem_id: {problem_id}]")
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/public-testdata",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)
    return resp.content


def get_public_checksum(problem_id: int) -> str:
    """Get checksum of public test data from backend."""
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/public-checksum",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)
    data = resp.json().get("data", {})
    return data.get("checksum") if isinstance(data, dict) else data


def ensure_public_testdata(problem_id: int):
    """
    Ensure public test data for Trial Mode is up to date.
    Similar to ensure_testdata() but for public cases.
    """
    client = get_redis_client()
    key = f"problem-{problem_id}-public-checksum"
    lock_key = f"{key}-lock"
    with client.lock(lock_key, timeout=60):
        curr_checksum = client.get(key)
        if curr_checksum is not None:
            curr_checksum = curr_checksum.decode()
            try:
                checksum = get_public_checksum(problem_id)
                if checksum and secrets.compare_digest(curr_checksum,
                                                       checksum):
                    logger().debug(
                        f"public testdata is up to date [problem_id: {problem_id}]"
                    )
                    return
            except Exception as exc:
                logger().warning(
                    f"Failed to verify public testdata checksum: {exc}")

        logger().info(f"refresh public testdata [problem_id: {problem_id}]")
        testdata = fetch_public_testdata(problem_id)
        public_root = get_public_testdata_root(problem_id)
        if public_root.exists():
            shutil.rmtree(public_root)
        public_root.mkdir(parents=True, exist_ok=True)
        with ZipFile(io.BytesIO(testdata)) as zf:
            _safe_extract_zip(zf, public_root)
        checksum = calc_checksum(testdata)
        client.setex(key, 600, checksum)


def scan_and_generate_tasks(testdata_path: Path,
                            default_time_limit: int = 1000,
                            default_memory_limit: int = 65536) -> list:
    """
    Scan test data directory and generate tasks configuration.
    Used for Trial Mode where we dynamically generate tasks from actual .in files.
    
    Note: Scores are distributed evenly to satisfy Meta validator (sum must be 100).
    
    Args:
        testdata_path: Path to test data directory
        default_time_limit: Default time limit in ms (default: 1000)
        default_memory_limit: Default memory limit in KB (default: 65536)
    
    Returns:
        List of task dictionaries with caseCount, taskScore, timeLimit, memoryLimit
    """
    from collections import defaultdict

    task_cases = defaultdict(int)

    # Scan all .in files
    for in_file in testdata_path.glob("*.in"):
        # Filename format: TTCC.in (e.g., 0000.in, 0001.in, 0100.in)
        stem = in_file.stem
        if len(stem) >= 4 and stem[:4].isdigit():
            task_no = int(stem[:2])
            task_cases[task_no] += 1
        else:
            # Unknown format, treat as task 0
            task_cases[0] += 1

    if not task_cases:
        logger().warning(f"No .in files found in {testdata_path}")
        return []

    # Generate tasks list (sorted by task number)
    # Distribute scores evenly to satisfy Meta validator (sum must be 100)
    num_tasks = len(task_cases)
    base_score = 100 // num_tasks
    remainder = 100 % num_tasks

    tasks = []
    for idx, task_no in enumerate(sorted(task_cases.keys())):
        # Give extra 1 point to first 'remainder' tasks to ensure sum is 100
        task_score = base_score + (1 if idx < remainder else 0)
        tasks.append({
            "caseCount": task_cases[task_no],
            "taskScore": task_score,
            "timeLimit": default_time_limit,
            "memoryLimit": default_memory_limit,
        })

    return tasks


def cleanup_custom_testdata(submission_id: str):
    """Remove custom test data directory after judging is complete."""
    custom_dir = get_custom_testdata_root(submission_id)
    if custom_dir.exists():
        try:
            shutil.rmtree(custom_dir)
            logger().debug(
                f"Cleaned up custom testdata [submission_id: {submission_id}]")
        except Exception as exc:
            logger().warning(
                f"Failed to cleanup custom testdata [submission_id: {submission_id}]: {exc}"
            )


# === AC Code Support ===

# Directory for AC code cache
AC_CODE_DIR = TESTDATA_ROOT / "ac_code"
AC_CODE_DIR.mkdir(exist_ok=True)


def get_ac_code_root(problem_id: int) -> Path:
    """Get the path for AC code cache."""
    return AC_CODE_DIR / str(problem_id)


def fetch_ac_code(problem_id: int) -> tuple:
    """
    Fetch AC code ZIP from backend server.
    
    Returns:
        Tuple of (content_bytes, language_int)
    """
    logger().debug(f"fetch AC code [problem_id: {problem_id}]")
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/ac-code",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)

    # Language is passed in response header
    language = resp.headers.get("X-AC-Code-Language")
    language = int(language) if language else None

    return resp.content, language


def get_ac_code_checksum(problem_id: int) -> tuple:
    """
    Get checksum and language of AC code from backend.
    
    Returns:
        Tuple of (checksum_str, language_int)
    """
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/ac-code-checksum",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    handle_problem_response(resp)
    data = resp.json().get("data", {})
    if isinstance(data, dict):
        return data.get("checksum"), data.get("language")
    return data, None


def _normalize_ac_code_filename(ac_code_root: Path, language: int) -> None:
    """
    Ensure AC code has the correct filename for sandbox execution.
    
    Sandbox expects:
    - Python: main.py
    - C: main.c
    - C++: main.cpp
    
    If the extracted file has a different name (e.g., ac_code.py),
    rename it to the expected name.
    """
    expected_names = {
        Language.PY: "main.py",
        Language.C: "main.c",
        Language.CPP: "main.cpp",
    }

    extensions = {
        Language.PY: ".py",
        Language.C: ".c",
        Language.CPP: ".cpp",
    }

    try:
        lang_enum = Language(language)
    except ValueError:
        logger().warning(f"Unknown language code: {language}")
        return

    expected_name = expected_names.get(lang_enum)
    extension = extensions.get(lang_enum)

    if not expected_name or not extension:
        return

    expected_path = ac_code_root / expected_name

    # If expected file already exists, nothing to do
    if expected_path.exists():
        return

    # Find source files with the correct extension
    source_files = list(ac_code_root.glob(f"*{extension}"))

    if not source_files:
        logger().warning(
            f"No {extension} files found in AC code directory: {ac_code_root}")
        return

    # Use the first source file found
    source_file = source_files[0]

    logger().info(
        f"Renaming AC code file: {source_file.name} -> {expected_name}")
    source_file.rename(expected_path)


def ensure_ac_code(problem_id: int) -> tuple:
    """
    Ensure AC code for Trial Mode is up to date.
    
    Returns:
        Tuple of (ac_code_path, language_int)
    """
    client = get_redis_client()
    key = f"problem-{problem_id}-ac-code-checksum"
    lock_key = f"{key}-lock"

    ac_code_root = get_ac_code_root(problem_id)

    with client.lock(lock_key, timeout=60):
        curr_checksum = client.get(key)
        if curr_checksum is not None:
            curr_checksum = curr_checksum.decode()
            try:
                checksum, language = get_ac_code_checksum(problem_id)
                if checksum and secrets.compare_digest(curr_checksum,
                                                       checksum):
                    logger().debug(
                        f"AC code is up to date [problem_id: {problem_id}]")
                    # Read cached language
                    lang_file = ac_code_root / ".language"
                    if lang_file.exists():
                        language = int(lang_file.read_text().strip())
                    # Ensure filename is normalized even for cached files
                    if language is not None:
                        _normalize_ac_code_filename(ac_code_root, language)
                    return ac_code_root, language
            except Exception as exc:
                logger().warning(f"Failed to verify AC code checksum: {exc}")

        logger().info(f"refresh AC code [problem_id: {problem_id}]")
        ac_code_content, language = fetch_ac_code(problem_id)

        if ac_code_root.exists():
            shutil.rmtree(ac_code_root)
        ac_code_root.mkdir(parents=True, exist_ok=True)

        with ZipFile(io.BytesIO(ac_code_content)) as zf:
            _safe_extract_zip(zf, ac_code_root)

        # Normalize filename to expected name (e.g., ac_code.py -> main.py)
        if language is not None:
            _normalize_ac_code_filename(ac_code_root, language)

        # Cache language info
        if language is not None:
            (ac_code_root / ".language").write_text(str(language))

        checksum = calc_checksum(ac_code_content)
        client.setex(key, 600, checksum)

        return ac_code_root, language


# === AI Checker Support ===


def fetch_checker_api_key(problem_id: int) -> str | None:
    """
    Fetch AI API key for custom checker from backend.

    Returns:
        API key string, or None if not available/configured.
    """
    logger().debug(f"fetch checker API key [problem_id: {problem_id}]")
    try:
        resp = rq.get(
            f"{BACKEND_API}/problem/{problem_id}/checker-api-key",
            params={
                "token": SANDBOX_TOKEN,
            },
        )
        if resp.status_code == 404:
            # AI Checker not enabled or API Key not configured
            return None
        if resp.status_code == 401:
            logger().error("Invalid sandbox token for checker API key request")
            return None
        if not resp.ok:
            logger().warning(
                f"Failed to fetch checker API key: {resp.status_code} {resp.text}"
            )
            return None
        data = resp.json().get("data", {})
        return data.get("apiKey")
    except Exception as exc:
        logger().warning(f"Exception fetching checker API key: {exc}")
        return None
