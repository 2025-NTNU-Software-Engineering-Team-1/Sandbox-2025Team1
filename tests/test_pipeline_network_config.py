import json
from pathlib import Path

import dispatcher.pipeline as pipeline
from dispatcher.pipeline import _translate_legacy_network_schema


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


# === Legacy Schema Translation Tests ===


def test_translate_legacy_schema_empty():
    """空設定應返回空 dict"""
    assert _translate_legacy_network_schema({}) == {}
    assert _translate_legacy_network_schema(None) == {}


def test_translate_legacy_schema_new_format_passthrough():
    """新格式應該直接返回，不做轉換"""
    new_config = {
        "external": {
            "model": "White",
            "ip": ["1.2.3.4"],
            "url": []
        },
        "sidecars": [{
            "name": "db",
            "image": "mysql:5.7"
        }],
        "custom_env": {
            "env_list": ["local_service"]
        }
    }
    result = _translate_legacy_network_schema(new_config)
    assert result == new_config


def test_translate_legacy_schema_firewall_whitelist():
    """舊格式 firewallExtranet whitelist 應轉換為 external White"""
    legacy_config = {
        "enabled": True,
        "firewallExtranet": {
            "mode":
            "whitelist",
            "rules": [
                {
                    "type": "ip",
                    "value": "192.168.1.1",
                    "action": "allow"
                },
                {
                    "type": "url",
                    "value": "https://api.example.com",
                    "action": "allow"
                },
            ]
        }
    }
    result = _translate_legacy_network_schema(legacy_config)
    assert result["external"]["model"] == "White"
    assert "192.168.1.1" in result["external"]["ip"]
    assert "https://api.example.com" in result["external"]["url"]
    assert result.get("enabled") is True


def test_translate_legacy_schema_firewall_blacklist():
    """舊格式 firewallExtranet blacklist 應轉換為 external Black"""
    legacy_config = {
        "firewallExtranet": {
            "mode": "blacklist",
            "rules": [
                {
                    "type": "ip",
                    "value": "10.0.0.1"
                },
            ]
        }
    }
    result = _translate_legacy_network_schema(legacy_config)
    assert result["external"]["model"] == "Black"
    assert "10.0.0.1" in result["external"]["ip"]


def test_translate_legacy_schema_connect_with_local_warning(caplog):
    """connectWithLocal 應該記錄警告（目前無直接對應）"""
    import logging
    caplog.set_level(logging.WARNING)
    legacy_config = {
        "connectWithLocal": {
            "mode": "whitelist",
            "rules": [{
                "type": "ip",
                "value": "127.0.0.1"
            }]
        }
    }
    result = _translate_legacy_network_schema(legacy_config)
    assert "connectWithLocal" in caplog.text


def test_fetch_problem_network_config_legacy_format(monkeypatch, tmp_path):
    """完整測試：從 meta 讀取舊格式並自動轉換"""
    monkeypatch.setattr(pipeline, "TESTDATA_ROOT", tmp_path)
    data = {
        "networkAccessRestriction": {
            "enabled": True,
            "firewallExtranet": {
                "mode": "whitelist",
                "rules": [
                    {
                        "type": "ip",
                        "value": "8.8.8.8"
                    },
                ]
            }
        }
    }
    _write_meta(tmp_path, 100, data)
    cfg = pipeline.fetch_problem_network_config(100)
    # 應該被轉換為新格式
    assert cfg["external"]["model"] == "White"
    assert "8.8.8.8" in cfg["external"]["ip"]
