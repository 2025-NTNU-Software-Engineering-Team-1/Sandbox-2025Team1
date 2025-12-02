import logging
from pathlib import Path
from dispatcher.artifact_collector import ArtifactCollector


class DummyResp:

    def __init__(self, ok=True, status_code=200, text="ok"):
        self.ok = ok
        self.status_code = status_code
        self.text = text


def test_artifact_collector_snapshot_and_upload(tmp_path, monkeypatch):
    calls = []

    def fake_put(url, params=None, data=None, timeout=None, headers=None):
        calls.append({
            "url": url,
            "params": params,
            "headers": headers,
            "data_len": len(data or b""),
        })
        return DummyResp()

    monkeypatch.setattr("dispatcher.artifact_collector.requests.put", fake_put)

    workdir = tmp_path / "submissions" / "s1" / "src"
    workdir.mkdir(parents=True, exist_ok=True)
    # snapshot before
    collector = ArtifactCollector(logger=logging.getLogger(__name__))
    collector.snapshot_before_case("s1", 0, 0, workdir)
    # create new file and stdout/stderr
    f = workdir / "out.txt"
    f.write_text("hello")
    # simulate executable binary
    bin_path = workdir / "main"
    bin_path.write_bytes(b"\x7fELFbinary")
    bin_path.chmod(0o755)
    collector.record_case_artifact("s1",
                                   0,
                                   0,
                                   workdir,
                                   stdout="foo",
                                   stderr="")
    collector.collect_binary("s1", workdir)

    collector.upload_all("s1")

    # expect two uploads: case artifact + binary
    assert len(calls) == 2
    case_call = next(c for c in calls if "artifact/upload/case" in c["url"])
    bin_call = next(c for c in calls if "artifact/upload/binary" in c["url"])
    assert case_call["data_len"] > 0
    assert bin_call["data_len"] == len(bin_path.read_bytes())
