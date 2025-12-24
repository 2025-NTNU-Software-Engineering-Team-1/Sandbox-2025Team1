import json
from pathlib import Path

import pytest

import runner.interactive_runner as interactive_runner
from runner.interactive_runner import InteractiveRunner


def _write_submission_config(tmp_path: Path) -> Path:
    cfg = {
        "working_dir": str(tmp_path / "submissions"),
        "sandbox_root": str(tmp_path / "sandbox"),
        "host_root": str(tmp_path / "host"),
        "docker_url": "unix://var/run/docker.sock",
        "lang_id": {
            "c11": 0,
            "cpp17": 1,
            "python3": 2,
        },
        "image": {
            "c11": "noj-c-cpp",
            "cpp17": "noj-c-cpp",
            "python3": "noj-py3",
        },
        "interactive_image": "noj-interactive",
    }
    path = tmp_path / "submission.json"
    path.write_text(json.dumps(cfg))
    return path


class DummyDockerClient:

    def __init__(self, *args, **kwargs):
        self.last_command = None
        self.last_host_config = None

    def create_host_config(self, **kwargs):
        self.last_host_config = kwargs
        return {"_host_config": kwargs}

    def create_container(self,
                         image,
                         command,
                         working_dir,
                         host_config,
                         environment=None):
        self.last_command = command
        return {"Id": "dummy"}

    def start(self, container):
        return None

    def wait(self, container):
        return {"StatusCode": 0}

    def logs(self, container, stdout=True, stderr=True):
        payload = {
            "Status": "AC",
            "Stdout": "",
            "Stderr": "",
            "Duration": 1,
            "MemUsage": 1,
            "DockerExitCode": 0,
            "pipeMode": "devfd",
        }
        return (json.dumps(payload) + "\n").encode("utf-8")

    def remove_container(self, container, v=True, force=True):
        return None


def _get_flag_value(command: list[str], flag: str) -> str | None:
    try:
        idx = command.index(flag)
    except ValueError:
        return None
    if idx + 1 >= len(command):
        return None
    return command[idx + 1]


@pytest.mark.parametrize(
    ("network_mode", "expected_flag"),
    [
        ("none", "0"),
        ("noj-net-123", "1"),
    ],
)
def test_interactive_runner_passes_network_access_flag(monkeypatch, tmp_path,
                                                       network_mode,
                                                       expected_flag):
    cfg_path = _write_submission_config(tmp_path)
    monkeypatch.setenv("SUBMISSION_CONFIG", str(cfg_path))
    (tmp_path / "submissions").mkdir()
    (tmp_path / "sandbox").mkdir()
    (tmp_path / "host").mkdir()

    holder = {}

    def _fake_client(*args, **kwargs):
        holder["client"] = DummyDockerClient()
        return holder["client"]

    monkeypatch.setattr(interactive_runner.docker, "APIClient", _fake_client)

    case_dir = tmp_path / "case"
    teacher_case_dir = tmp_path / "teacher"
    case_dir.mkdir()
    teacher_case_dir.mkdir()

    runner = InteractiveRunner(
        submission_id="sub-1",
        time_limit=1000,
        mem_limit=65536,
        case_in_path=str(tmp_path / "input.in"),
        teacher_first=True,
        lang_key="c11",
        teacher_lang_key="c11",
        case_dir=case_dir,
        teacher_case_dir=teacher_case_dir,
        network_mode=network_mode,
    )

    runner.run()

    command = holder["client"].last_command
    assert command is not None
    assert _get_flag_value(command, "--allow-network-access") == expected_flag
