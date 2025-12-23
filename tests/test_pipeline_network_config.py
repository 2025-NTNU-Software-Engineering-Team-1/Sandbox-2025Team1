import json
from pathlib import Path

import dispatcher.pipeline as pipeline


def _write_meta(root: Path, problem_id: int, data: dict) -> None:
    meta_dir = root / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / f"{problem_id}.json").write_text(json.dumps(data))


def test_fetch_problem_network_config_missing_meta(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "TESTDATA_ROOT", tmp_path)
    assert pipeline.fetch_problem_network_config(1) == {}


def test_fetch_problem_network_config_top_level_and_custom_env(
        monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "TESTDATA_ROOT", tmp_path)
    data = {
        "networkAccessRestriction": {
            "sidecars": [{
                "name": "db",
                "image": "mysql:5.7",
                "env": {},
                "args": []
            }]
        },
        "assetPaths": {
            "network_dockerfile": "Dockerfiles.zip"
        },
    }
    _write_meta(tmp_path, 1, data)
    cfg = pipeline.fetch_problem_network_config(1)
    assert cfg["sidecars"][0]["name"] == "db"
    assert cfg["custom_env"]["enabled"] is True


def test_fetch_problem_network_config_from_config_block(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "TESTDATA_ROOT", tmp_path)
    _write_meta(tmp_path, 2, {"config": {"networkAccessRestriction": None}})
    assert pipeline.fetch_problem_network_config(2) == {}

    data = {
        "config": {
            "networkAccessRestriction": {
                "external": {
                    "url": "http://example.test"
                }
            }
        }
    }
    _write_meta(tmp_path, 3, data)
    cfg = pipeline.fetch_problem_network_config(3)
    assert cfg["external"]["url"] == "http://example.test"
