import hashlib
import secrets
import shutil
from pathlib import Path
from typing import Optional

import requests

from .config import BACKEND_API, SANDBOX_TOKEN, TESTDATA_ROOT
from .testdata import fetch_problem_asset
from .utils import get_redis_client, logger

ASSET_FILENAME_MAP = {
    "checker": "custom_checker.py",
    "scoring_script": "score.py",
    "makefile": "makefile.zip",
}


class AssetNotFoundError(Exception):
    """Raised when asset is not configured or checksum unavailable."""


def get_asset_checksum(problem_id: int, asset_type: str) -> Optional[str]:
    """
    Fetch asset checksum from Backend.

    Backend Request.args 會將下底線轉 camelCase（asset_type -> assetType），
    因此統一以 camelCase 呼叫，避免歧義。
    """

    url = f"{BACKEND_API}/problem/{problem_id}/asset-checksum"
    resp = requests.get(
        url,
        params={
            "token": SANDBOX_TOKEN,
            "assetType": asset_type,
        },
    )
    if resp.ok:
        try:
            data = resp.json().get("data", {})
            if isinstance(data, dict):
                return data.get("checksum")
        except Exception:
            pass

    logger().warning(
        "failed to get asset checksum [problem_id=%s, asset_type=%s, status=%s, resp=%s]",
        problem_id,
        asset_type,
        resp.status_code,
        resp.text,
    )
    return None


def _md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def ensure_custom_asset(
    problem_id: int,
    asset_type: str,
    filename: Optional[str] = None,
) -> Path:
    """
    Ensure custom asset is up-to-date using Redis checksum.

    Returns cache file path (TESTDATA_ROOT/<pid>/<asset_type>/<filename>).
    """
    filename = filename or ASSET_FILENAME_MAP.get(asset_type)
    if not filename:
        raise ValueError(
            f"filename required for asset_type '{asset_type}' (no default mapping)"
        )

    client = get_redis_client()
    redis_key = f"problem-{problem_id}-{asset_type}-checksum"
    lock_key = f"{redis_key}-lock"

    cache_dir = TESTDATA_ROOT / str(problem_id) / asset_type
    cache_dir.mkdir(parents=True, exist_ok=True)
    asset_path = cache_dir / filename

    with client.lock(lock_key, timeout=30):
        cached_checksum = client.get(redis_key)
        if cached_checksum:
            cached_checksum = cached_checksum.decode()

        backend_checksum = get_asset_checksum(problem_id, asset_type)
        if backend_checksum is None:
            raise AssetNotFoundError(
                f"asset '{asset_type}' not configured for problem {problem_id}"
            )

        def _local_checksum() -> Optional[str]:
            if not asset_path.exists():
                return None
            try:
                return _md5_bytes(asset_path.read_bytes())
            except Exception:
                return None

        local_checksum = _local_checksum()
        if (backend_checksum and local_checksum
                and secrets.compare_digest(local_checksum, backend_checksum)):
            # 保持 Redis 的 TTL
            client.setex(redis_key, 600, backend_checksum)
            logger().debug(
                "asset cache hit [problem_id=%s, asset_type=%s]",
                problem_id,
                asset_type,
            )
            return asset_path

        # cache miss or outdated -> re-download
        logger().info("refresh asset [problem_id=%s, asset_type=%s]",
                      problem_id, asset_type)
        data = fetch_problem_asset(problem_id, asset_type)
        asset_path.write_bytes(data)
        checksum_to_store = backend_checksum or _md5_bytes(data)
        client.setex(redis_key, 600, checksum_to_store)
        return asset_path
