from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import docker
from dispatcher import config as dispatcher_config


@dataclass
class InteractiveRunner:
    submission_id: str
    time_limit: int  # ms
    mem_limit: int  # KB
    case_in_path: str
    teacher_first: bool
    lang_key: str  # c11 | cpp17 | python3
    teacher_lang_key: str | None = None
    pipe_mode: str = "auto"

    def run(self) -> dict:
        cfg = dispatcher_config.get_submission_config()
        docker_url = cfg.get("docker_url", "unix://var/run/docker.sock")
        interactive_image = cfg.get("interactive_image") or cfg["image"][
            self.lang_key]
        working_dir = Path(cfg["working_dir"]) / self.submission_id
        submission_root = working_dir
        teacher_dir = submission_root / "teacher"
        student_dir = submission_root / "src"
        testcase_dir = submission_root / "testcase"

        client = docker.APIClient(base_url=docker_url)
        binds = {
            str(student_dir): {
                "bind": "/src",
                "mode": "rw"
            },
            str(teacher_dir): {
                "bind": "/teacher",
                "mode": "rw"
            },
            str(testcase_dir): {
                "bind": "/workspace/testcase",
                "mode": "ro"
            },
            str(Path(__file__).resolve().parent.parent): {
                "bind": "/app",
                "mode": "ro"
            },
        }
        host_config = client.create_host_config(
            binds=binds,
            network_mode="none",
            mem_limit=f"{max(self.mem_limit,0)}k",
            tmpfs={"/tmp": "rw,noexec,nosuid"},
        )
        case_path_container = str(
            Path("/workspace/testcase") / Path(self.case_in_path).name)

        command = [
            "python3",
            "/app/runner/interactive_orchestrator.py",
            "--workdir",
            "/workspace",
            "--teacher-dir",
            "/teacher",
            "--student-dir",
            "/src",
            "--student-lang",
            self.lang_key,
            "--teacher-lang",
            self.teacher_lang_key or self.lang_key,
            "--time-limit",
            str(self.time_limit),
            "--mem-limit",
            str(self.mem_limit),
            "--pipe-mode",
            self.pipe_mode,
        ]
        if self.teacher_first:
            command.append("--teacher-first")
        if case_path_container:
            command += ["--case-path", case_path_container]

        env = {}
        for key in ("KEEP_INTERACTIVE_TMP", "KEEP_INTERACTIVE_SUBMISSIONS"):
            if key in os.environ:
                env[key] = os.environ[key]

        container = client.create_container(
            image=interactive_image,
            command=command,
            working_dir="/workspace",
            host_config=host_config,
            environment=env or None,
        )
        try:
            client.start(container)
            exit_status = client.wait(container)
            logs = client.logs(container, stdout=True,
                               stderr=True).decode("utf-8", "ignore")
        finally:
            try:
                client.remove_container(container, v=True, force=True)
            except Exception:
                pass

        status_code = exit_status.get("StatusCode", 1)
        try:
            payload = json.loads(logs.strip().splitlines()[-1])
        except Exception:
            payload = {
                "Status": "JE",
                "Stdout": "",
                "Stderr": f"interactive runner failed: {logs}",
                "Duration": -1,
                "MemUsage": -1,
                "DockerExitCode": status_code,
                "pipeMode": "unknown",
            }
        payload.setdefault("DockerExitCode", status_code)
        return payload
