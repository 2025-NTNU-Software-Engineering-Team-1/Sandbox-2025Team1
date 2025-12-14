import hashlib
import secrets
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import requests

from .config import BACKEND_API, SANDBOX_TOKEN, TESTDATA_ROOT
from .testdata import fetch_problem_asset
from .utils import get_redis_client, logger
from .file_manager import _safe_extract_zip

ASSET_FILENAME_MAP = {
    "checker": "custom_checker.py",
    "scoring_script": "score.py",
    "makefile": "makefile.zip",
    "resource_data": "resource_data.zip",
    "resource_data_teacher": "resource_data_teacher.zip",
    "network_dockerfile": "Dockerfiles.zip"
}


class AssetNotFoundError(Exception):
    """Raised when asset is not configured or checksum unavailable."""


def get_asset_checksum(problem_id: int, asset_type: str) -> Optional[str]:
    """
    Fetch asset checksum from Backend.

    Backend expects query param `asset_type`.
    """

    url = f"{BACKEND_API}/problem/{problem_id}/asset-checksum"
    resp = requests.get(
        url,
        params={
            "token": SANDBOX_TOKEN,
            # Backend Request.args camel-cases keys; use assetType to avoid type error
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


def ensure_extracted_resource(
    problem_id: int,
    asset_type: str,
) -> Optional[Path]:
    """
    Ensure resource zip is extracted to extracted/ directory.
    
    Uses Redis lock to prevent concurrent extraction.
    Returns extracted/ directory path, or None if asset not configured.
    
    asset_type: "resource_data" | "resource_data_teacher" | "network_dockerfile"
    """
    if asset_type not in ("resource_data", "resource_data_teacher",
                          "network_dockerfile"):
        raise ValueError(f"invalid asset_type for extraction: {asset_type}")

    # First ensure the zip file is up-to-date
    try:
        zip_path = ensure_custom_asset(problem_id, asset_type)
    except AssetNotFoundError:
        logger().debug(
            "asset not configured, skip extraction [problem_id=%s, asset_type=%s]",
            problem_id,
            asset_type,
        )
        return None

    client = get_redis_client()
    extracted_key = f"problem-{problem_id}-{asset_type}-extracted"
    lock_key = f"{extracted_key}-lock"

    cache_dir = TESTDATA_ROOT / str(problem_id) / asset_type
    extracted_dir = cache_dir / "extracted"

    with client.lock(lock_key, timeout=60):
        # Get zip checksum to compare with extracted state
        zip_checksum = _md5_bytes(zip_path.read_bytes())

        # Check if already extracted with same checksum
        cached_extracted = client.get(extracted_key)
        if cached_extracted:
            cached_extracted = cached_extracted.decode()
            if (secrets.compare_digest(cached_extracted, zip_checksum)
                    and extracted_dir.exists()
                    and any(extracted_dir.iterdir())):
                # Already extracted, refresh TTL
                client.setex(extracted_key, 600, zip_checksum)
                logger().debug(
                    "extracted cache hit [problem_id=%s, asset_type=%s]",
                    problem_id,
                    asset_type,
                )
                return extracted_dir

        # Need to extract
        logger().info(
            "extracting resource [problem_id=%s, asset_type=%s]",
            problem_id,
            asset_type,
        )

        # Clean and recreate extracted directory
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)
        extracted_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                # 原本的寫法使用 zf.extractall(extracted_dir)
                # 這在解壓縮時，沒有驗證壓縮包內部的路徑合法性，容易造成 ZIP 路徑穿越（Zip Slip）安全漏洞
                # _safe_extract_zip 則應該是在解壓前有做過安全檢查，確保檔案不會被寫到目標目錄外
                # 因此建議取代成 _safe_extract_zip 來避免安全問題
                _safe_extract_zip(zf, extracted_dir)
        except Exception as exc:
            logger().error(
                "failed to extract resource [problem_id=%s, asset_type=%s]: %s",
                problem_id,
                asset_type,
                exc,
            )
            return None

        # Store extraction state
        client.setex(extracted_key, 600, zip_checksum)
        return extracted_dir
