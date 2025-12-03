import io
import zipfile
from pathlib import Path

from dispatcher.resource_data import prepare_resource_data, copy_resource_for_case


class DummyAsset:

    def __init__(self, path: Path):
        self.path = path


def test_prepare_and_copy_resource_data(tmp_path, monkeypatch):
    # create fake resource zip
    res_zip = tmp_path / "resource_data.zip"
    with zipfile.ZipFile(res_zip, "w") as zf:
        zf.writestr("0000_config.txt", "cfg0")
        zf.writestr("0001_config.txt", "cfg1")

    # mock ensure_custom_asset to return our zip
    def fake_ensure(problem_id, asset_type, filename=None):
        return res_zip

    monkeypatch.setattr("dispatcher.resource_data.ensure_custom_asset",
                        fake_ensure)

    submission_path = tmp_path / "submissions" / "s1"
    submission_path.mkdir(parents=True, exist_ok=True)

    res_dir = prepare_resource_data(
        problem_id=1,
        submission_path=submission_path,
        asset_paths={"resource_data": "resource_data.zip"},
    )
    assert res_dir and res_dir.exists()

    src_dir = submission_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    copied = copy_resource_for_case(
        resource_dir=res_dir,
        src_dir=src_dir,
        task_no=0,
        case_no=0,
    )
    assert (src_dir / "config.txt").read_text() == "cfg0"
    # cleanup copied
    from dispatcher.resource_data import cleanup_resource_files
    cleanup_resource_files(src_dir, copied)
    assert not (src_dir / "config.txt").exists()
