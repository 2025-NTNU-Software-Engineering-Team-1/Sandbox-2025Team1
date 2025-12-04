from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import docker
from runner.path_utils import PathTranslator


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
    case_dir: Path | None = None
    student_allow_write: bool = False

    def run(self) -> dict:
        translator = PathTranslator()
        cfg = translator.cfg
        docker_url = cfg.get("docker_url", "unix://var/run/docker.sock")
        interactive_image = cfg.get("interactive_image") or cfg["image"][
            self.lang_key]

        submission_root = translator.working_dir / self.submission_id
        host_root = translator.host_root
        teacher_dir = submission_root / "teacher"
        if self.case_dir is None:
            raise ValueError("case_dir is required for interactive run")
        student_dir = self.case_dir
        if not student_dir.exists():
            raise ValueError(f"interactive case_dir missing: {student_dir}")
        testcase_dir = submission_root / "testcase"
        submission_root_host = translator.to_host(submission_root)
        teacher_dir_host = translator.to_host(teacher_dir)
        student_dir_host = translator.to_host(student_dir)
        testcase_dir_host = translator.to_host(testcase_dir)
        if self.teacher_lang_key is None:
            raise ValueError(
                "teacher_lang_key is required for interactive mode")
        teacher_lang_key = self.teacher_lang_key

        client = docker.APIClient(base_url=docker_url)
        binds = {
            str(student_dir_host): {
                "bind": "/src",
                "mode": "rw"
            },
            str(teacher_dir_host): {
                "bind": "/teacher",
                "mode": "rw"
            },
            str(testcase_dir_host): {
                "bind": "/workspace/testcase",
                "mode": "ro"
            },
            str(host_root): {
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
            "/usr/bin/env",
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
        if self.student_allow_write:
            command += ["--allow-write-student", "1"]
        else:
            command += ["--allow-write-student", "0"]

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
