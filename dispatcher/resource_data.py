import shutil
import zipfile
from pathlib import Path

from .asset_cache import ensure_custom_asset, AssetNotFoundError
from .utils import logger


class ResourceDataError(Exception):
    pass


def prepare_resource_data(problem_id: int, submission_path: Path,
                          asset_paths: dict | None) -> Path | None:
    """Download and extract resource_data asset into submission_path/resource_data."""
    if not asset_paths:
        return None
    res_path = asset_paths.get("resource_data")
    if not res_path:
        return None
    try:
        filename = Path(res_path).name
        asset_file = ensure_custom_asset(problem_id,
                                         "resource_data",
                                         filename=filename)
    except AssetNotFoundError:
        logger().warning("resource_data asset not found [problem_id=%s]",
                         problem_id)
        return None
    except Exception as exc:
        raise ResourceDataError(
            f"failed to fetch resource data: {exc}") from exc

    target_dir = submission_path / "resource_data"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(asset_file) as zf:
            zf.extractall(target_dir)
    except Exception as exc:
        raise ResourceDataError(f"invalid resource data zip: {exc}") from exc
    return target_dir


def copy_resource_for_case(resource_dir: Path, src_dir: Path, task_no: int,
                           case_no: int):
    """Copy resource files for specific case into src_dir, stripping prefix."""
    if not resource_dir or not resource_dir.exists():
        return
    prefix = f"{task_no:02d}{case_no:02d}_"
    copied = []
    for path in resource_dir.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if not name.startswith(prefix):
            continue
        dest_name = name[len(prefix):]
        dest = src_dir / dest_name
        try:
            if dest.exists():
                dest.unlink()
            shutil.copy(path, dest)
            copied.append(dest)
        except Exception as exc:
            logger().warning(
                "resource copy failed [task=%s case=%s file=%s]: %s",
                task_no,
                case_no,
                path,
                exc,
            )

    return copied


def cleanup_resource_files(src_dir: Path, files):
    for f in files or []:
        try:
            if f.exists():
                f.unlink()
        except Exception:
            continue
