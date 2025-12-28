import hashlib
from pathlib import Path

import pytest

from dispatcher.asset_cache import (ASSET_FILENAME_MAP, AssetNotFoundError,
                                    ensure_custom_asset)


class DummyLock:

    def __init__(self, key):
        self.key = key

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyRedis:

    def __init__(self):
        self.store = {}

    def lock(self, key, timeout=None):
        return DummyLock(key)

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        if isinstance(value, str):
            value = value.encode()
        self.store[key] = value


class DummyResponse:

    def __init__(self, checksum, ok=True, status_code=200, text=""):
        self._checksum = checksum
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(self):
        return {"data": {"checksum": self._checksum}}


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch, tmp_path):
    # patch TESTDATA_ROOT to a temp dir
    from dispatcher import asset_cache
    monkeypatch.setattr(asset_cache, "TESTDATA_ROOT", tmp_path)
    dummy_redis = DummyRedis()
    monkeypatch.setattr(asset_cache, "get_redis_client", lambda: dummy_redis)
    return dummy_redis


def test_asset_cache_hit(monkeypatch, tmp_path):
    from dispatcher import asset_cache

    data = b"cached"
    checksum = hashlib.md5(data).hexdigest()
    monkeypatch.setattr(
        asset_cache, "requests",
        type("req", (), {
            "get": lambda *args, **kwargs: DummyResponse(checksum)
        }))
    # prepare cached file with matching checksum
    asset_dir = tmp_path / str(1) / "checker"
    asset_dir.mkdir(parents=True)
    asset_path = asset_dir / ASSET_FILENAME_MAP["checker"]
    asset_path.write_bytes(data)
    # Redis checksum set manually
    client = asset_cache.get_redis_client()
    client.setex("problem-1-checker-checksum", 600, checksum)

    result_path = ensure_custom_asset(1, "checker")
    assert result_path.read_bytes() == data


def test_asset_cache_miss_download(monkeypatch, tmp_path):
    from dispatcher import asset_cache
    backend_checksum = "newhash"
    monkeypatch.setattr(
        asset_cache, "requests",
        type("req", (), {
            "get": lambda *args, **kwargs: DummyResponse(backend_checksum)
        }))
    download_data = b"fresh"
    monkeypatch.setattr(asset_cache, "fetch_problem_asset",
                        lambda pid, asset_type: download_data)

    result_path = ensure_custom_asset(2, "checker")
    assert result_path.read_bytes() == download_data
    client = asset_cache.get_redis_client()
    assert client.get(
        "problem-2-checker-checksum").decode() == backend_checksum


def test_asset_checksum_none_raises(monkeypatch, tmp_path):
    from dispatcher import asset_cache
    monkeypatch.setattr(
        asset_cache, "requests",
        type("req", (), {
            "get": lambda *args, **kwargs: DummyResponse(None)
        }))
    with pytest.raises(AssetNotFoundError):
        ensure_custom_asset(3, "checker")
