import math
from dataclasses import dataclass
from typing import Dict
import docker


class CustomCheckerError(Exception):
    """Raised when custom checker cannot be executed."""


@dataclass
class CustomCheckerRunner:
    submission_id: str
    case_no: str
    image: str
    docker_url: str
    workdir: str
    checker_relpath: str
    time_limit_ms: int
    mem_limit_kb: int

    def run(self) -> Dict[str, str]:
        client = docker.APIClient(base_url=self.docker_url)
        binds = {
            self.workdir: {
                "bind": "/workspace",
                "mode": "rw",
            }
        }
        host_config = client.create_host_config(
            binds=binds,
            network_mode="none",
            mem_limit=f"{max(self.mem_limit_kb,0)}k",
            tmpfs={"/tmp": "rw,noexec,nosuid"},
        )
        timeout_sec = max(5, math.ceil(self.time_limit_ms / 1000) * 5)
        command = [
            "python3",
            f"/workspace/{self.checker_relpath}",
            "/workspace/input.in",
            "/workspace/student.out",
            "/workspace/answer.out",
        ]
        container = client.create_container(
            image=self.image,
            command=command,
            working_dir="/workspace",
            host_config=host_config,
        )
        try:
            client.start(container)
            exit_status = client.wait(container, timeout=timeout_sec)
            logs_stdout = client.logs(container, stdout=True,
                                      stderr=False).decode("utf-8", "ignore")
            logs_stderr = client.logs(container, stdout=False,
                                      stderr=True).decode("utf-8", "ignore")
        except Exception as exc:
            try:
                client.remove_container(container, v=True, force=True)
            finally:
                pass
            raise CustomCheckerError(f"custom checker failed: {exc}") from exc
        finally:
            try:
                client.remove_container(container, v=True, force=True)
            except Exception:
                pass

        status_code = exit_status.get("StatusCode", 1) if exit_status else 1
        if exit_status is None:
            raise CustomCheckerError("custom checker timed out")
        return {
            "exit_code": status_code,
            "stdout": logs_stdout,
            "stderr": logs_stderr,
        }
