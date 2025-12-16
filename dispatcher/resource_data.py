import shutil
from pathlib import Path
from typing import Optional

from .asset_cache import ensure_extracted_resource
from .utils import logger


class ResourceDataError(Exception):
    pass


def _copy_from_extracted(
    problem_id: int,
    asset_type: str,
    target_dir: Path,
    clean: bool = True,
) -> Optional[Path]:
    """
    Copy files from extracted/ directory to target_dir.
    Returns target_dir if successful, None if asset not configured.
    """
    extracted_dir = ensure_extracted_resource(problem_id, asset_type)
    if not extracted_dir or not extracted_dir.exists():
        return None

    if target_dir.exists() and clean:
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        for item in extracted_dir.iterdir():
            dest = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    except Exception as exc:
        raise ResourceDataError(f"failed to copy {asset_type}: {exc}") from exc

    return target_dir


def prepare_resource_data(problem_id: int, submission_path: Path,
                          asset_paths: dict | None) -> Optional[Path]:
    """
    Student resource data copied into submission_path/resource_data.
    Copies from pre-extracted sandbox-testdata/{pid}/resource_data/extracted/.
    """
    if not asset_paths or not asset_paths.get("resource_data"):
        return None

    return _copy_from_extracted(
        problem_id=problem_id,
        asset_type="resource_data",
        target_dir=submission_path / "resource_data",
    )


def prepare_teacher_resource_data(problem_id: int, submission_path: Path,
                                  asset_paths: dict | None) -> Optional[Path]:
    """
    Teacher resource data copied into submission_path/resource_data_teacher.
    Copies from pre-extracted sandbox-testdata/{pid}/resource_data_teacher/extracted/.
    Does not delete existing teacher artifacts (for interactive teacher code).
    """
    if not asset_paths or not asset_paths.get("resource_data_teacher"):
        return None

    return _copy_from_extracted(
        problem_id=problem_id,
        asset_type="resource_data_teacher",
        target_dir=submission_path / "resource_data_teacher",
        clean=False,
    )


def copy_resource_for_case(
    submission_path: Path,
    case_dir: Path,
    task_no: int,
    case_no: int,
) -> list:
    """
    Copy resource files for specific case into case_dir, stripping prefix.
    Reads from submission_path/resource_data/.
    
    Example: 0000_input.bmp -> case_dir/input.bmp
    """
    resource_dir = submission_path / "resource_data"
    if not resource_dir.exists():
        return []

    prefix = f"{task_no:02d}{case_no:02d}_"
    copied = []

    for path in resource_dir.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if not name.startswith(prefix):
            continue
        dest_name = name[len(prefix):]
        dest = case_dir / dest_name
        try:
            if dest.exists():
                dest.unlink()
            shutil.copy(path, dest)
            copied.append(dest)
            logger().debug(
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

    return copied


def prepare_teacher_for_case(
    submission_path: Path,
    task_no: int,
    case_no: int,
    teacher_common_dir: Optional[Path] = None,
    copy_testcase: bool = True,
) -> Path:
    """
    Prepare teacher/cases/{case_id}/ directory for a specific case.
    
    Creates:
    - teacher/cases/{task_no:02d}{case_no:02d}/
    - Copies all files from teacher_common_dir if provided (for interactive)
    - Copies testcase/{case_id}.in -> testcase.in if copy_testcase=True
    - Copies resource_data_teacher files (stripped prefix)
    
    Returns: teacher case directory path
    """
    case_id = f"{task_no:02d}{case_no:02d}"
    teacher_case_dir = submission_path / "teacher" / "cases" / case_id

    # Clean and create
    if teacher_case_dir.exists():
        shutil.rmtree(teacher_case_dir)
    teacher_case_dir.mkdir(parents=True, exist_ok=True)

    # Copy teacher common files (interactive teacher executable)
    if teacher_common_dir and teacher_common_dir.exists():
        for item in teacher_common_dir.iterdir():
            dest = teacher_case_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    # Copy testcase.in
    if copy_testcase:
        testcase_in = submission_path / "testcase" / f"{case_id}.in"
        if testcase_in.exists():
            dest_in = teacher_case_dir / "testcase.in"
            shutil.copy(testcase_in, dest_in)

    # Copy teacher resource data (stripped prefix)
    teacher_res_dir = submission_path / "resource_data_teacher"
    if teacher_res_dir.exists():
        prefix = f"{case_id}_"
        for path in teacher_res_dir.rglob("*"):
            if not path.is_file():
                continue
            name = path.name
            if not name.startswith(prefix):
                continue
            dest_name = name[len(prefix):]
            dest = teacher_case_dir / dest_name
            try:
                if dest.exists():
                    dest.unlink()
                shutil.copy(path, dest)
                logger().debug(
                    "teacher resource copied [case=%s]: %s -> %s",
                    case_id,
                    path.name,
                    dest,
                )
            except Exception as exc:
                logger().warning(
                    "teacher resource copy failed [case=%s file=%s]: %s",
                    case_id,
                    path,
                    exc,
                )

    return teacher_case_dir


def cleanup_resource_files(src_dir: Path, files):
    """Clean up copied resource files."""
    for f in files or []:
        try:
            if f.exists():
                f.unlink()
        except Exception:
            continue
