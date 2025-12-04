import shutil
import zipfile
from pathlib import Path

from .asset_cache import ensure_custom_asset, AssetNotFoundError
from .utils import logger


class ResourceDataError(Exception):
    pass


def _prepare_resource_bundle(
    problem_id: int,
    asset_paths: dict | None,
    asset_key: str,
    submission_path: Path,
    target_dir: Path,
    clean: bool = True,
) -> Path | None:
    if not asset_paths:
        return None
    res_path = asset_paths.get(asset_key)
    if not res_path:
        return None
    try:
        filename = Path(res_path).name
        asset_file = ensure_custom_asset(problem_id,
                                         asset_key,
                                         filename=filename)
    except AssetNotFoundError:
        logger().warning("%s asset not found [problem_id=%s]", asset_key,
                         problem_id)
        return None
    except Exception as exc:
        raise ResourceDataError(f"failed to fetch {asset_key}: {exc}") from exc

    if target_dir.exists() and clean:
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(asset_file) as zf:
            zf.extractall(target_dir)
    except Exception as exc:
        raise ResourceDataError(f"invalid {asset_key} zip: {exc}") from exc
    return target_dir


def prepare_resource_data(problem_id: int, submission_path: Path,
                          asset_paths: dict | None) -> Path | None:
    """Student resource data extracted into submission_path/resource_data."""
    return _prepare_resource_bundle(
        problem_id=problem_id,
        asset_paths=asset_paths,
        asset_key="resource_data",
        submission_path=submission_path,
        target_dir=submission_path / "resource_data",
    )


def prepare_teacher_resource_data(problem_id: int, submission_path: Path,
                                  asset_paths: dict | None) -> Path | None:
    """
    Teacher resource data extracted into submission_path/teacher.
    Do not delete existing teacher artifacts (interactive teacher code).
    """
    target_dir = submission_path / "teacher"
    return _prepare_resource_bundle(
        problem_id=problem_id,
        asset_paths=asset_paths,
        asset_key="resource_data_teacher",
        submission_path=submission_path,
        target_dir=target_dir,
        clean=False,
    )


def copy_resource_for_case(resource_dir: Path, src_dir: Path, task_no: int,
                           case_no: int):
    """Copy resource files for specific case into src_dir, stripping prefix."""
    if not resource_dir or not resource_dir.exists():
        logger().warning(
            "resource_dir not found or empty [task=%s case=%s dir=%s]",
            task_no,
            case_no,
            resource_dir,
        )
        return
    prefix = f"{task_no:02d}{case_no:02d}_"
    copied = []
    all_files = list(resource_dir.rglob("*"))
    logger().info(
        "copy_resource_for_case [task=%s case=%s prefix=%s] found %d files in %s",
        task_no,
        case_no,
        prefix,
        len(all_files),
        resource_dir,
    )
    for path in all_files:
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
            logger().info(
                "resource copied [task=%s case=%s]: %s -> %s",
                task_no,
                case_no,
                path.name,
                dest,
            )
        except Exception as exc:
            logger().warning(
                "resource copy failed [task=%s case=%s file=%s]: %s",
                task_no,
                case_no,
                path,
                exc,
            )

    if not copied:
        logger().warning(
            "no files copied for [task=%s case=%s prefix=%s]",
            task_no,
            case_no,
            prefix,
        )
    return copied


def cleanup_resource_files(src_dir: Path, files):
    for f in files or []:
        try:
            if f.exists():
                f.unlink()
        except Exception:
            continue
