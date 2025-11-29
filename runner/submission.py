import dataclasses
import pathlib
import os
import shutil
from typing import Optional
import docker
from runner.sandbox import Sandbox, JudgeError
from runner.path_utils import PathTranslator


class SubmissionRunner:

    def __init__(
        self,
        submission_id: str,
        time_limit: int,  # sec.
        mem_limit: int,  # KB
        testdata_input_path: str,
        testdata_output_path: str,
        special_judge: bool = False,
        lang: Optional[str] = None,
        network_mode: str = "none",
    ):
        # config file
        translator = PathTranslator()
        submission_cfg = translator.cfg
        self.lang = lang
        self.special_judge = special_judge
        self.network_mode = network_mode
        # required
        self.submission_id = submission_id
        self.time_limit = time_limit
        self.mem_limit = mem_limit
        self.testdata_input_path = testdata_input_path  # absoulte path str
        self.testdata_output_path = testdata_output_path  # absoulte path str
        # working_dir
        self.working_dir = submission_cfg["working_dir"]
        self.docker_url = submission_cfg.get("docker_url", "unix://var/run/docker.sock")
        # for language specified settings
        self.lang_id = submission_cfg["lang_id"]
        self.image = submission_cfg["image"]

    def compile(self):
        try:
            # compile must be done in 20 seconds
            result = Sandbox(
                time_limit=20000,  # 20s
                mem_limit=1048576,  # 1GB
                image=self.image[self.lang],
                src_dir=str(self.translator.to_host(self._src_dir())),
                lang_id=self.lang_id[self.lang],
                compile_need=True,
            ).run()
        except JudgeError:
            return {"Status": "JE"}
        if result.Status == "Exited Normally":
            result.Status = "AC"
        else:
            result.Status = "CE"
        return dataclasses.asdict(result)

    @classmethod
    def compile_at_path(cls, src_dir: str, lang: str):
        """Compile sources located at `src_dir` with given lang key."""
        cfg_path = (
            pathlib.Path(__file__).resolve().parent.parent / ".config/submission.json"
        )
        cfg = dispatcher_config.get_submission_config(config_path=cfg_path)
        orig_cwd = pathlib.Path.cwd()
        os.chdir(cfg_path.parent.parent)
        try:
            result = Sandbox(
                time_limit=20000,
                mem_limit=1048576,
                image=cfg["image"][lang],
                src_dir=str(src_dir_host),
                lang_id=cfg["lang_id"][lang],
                compile_need=True,
            ).run()
        except JudgeError:
            return {"Status": "JE"}
        finally:
            os.chdir(orig_cwd)
        if result.Status == "Exited Normally":
            result.Status = "AC"
        else:
            result.Status = "CE"
        payload = dataclasses.asdict(result)
        # rename main -> Teacher_main if present
        bin_path = pathlib.Path(src_dir) / "main"
        target = pathlib.Path(src_dir) / "Teacher_main"
        if bin_path.exists():
            if target.exists():
                target.unlink()
            os.replace(bin_path, target)
            try:
                os.chmod(target, target.stat().st_mode | 0o111)
            except PermissionError:
                pass
        # keep a ./main for sandbox_interactive runtime
        if target.exists() and not bin_path.exists():
            try:
                os.link(target, bin_path)
            except Exception:
                try:
                    shutil.copy(target, bin_path)
                except Exception:
                    pass
            try:
                os.chmod(bin_path, bin_path.stat().st_mode | 0o111)
            except Exception:
                pass
        return payload

    def run(self):
        try:
            result = Sandbox(
                time_limit=self.time_limit,
                mem_limit=self.mem_limit,
                image=self.image[self.lang],
                src_dir=str(self.translator.to_host(self._src_dir())),
                lang_id=self.lang_id[self.lang],
                compile_need=False,
                stdin_path=self.testdata_input_path,
                network_mode=self.network_mode,
            ).run()
        except JudgeError:
            return {"Status": "JE"}
        with open(self.testdata_output_path, "r") as f:
            ans_output = f.read()
        status = {"TLE", "MLE", "RE", "OLE"}
        if result.Status not in status:
            result.Status = "WA"
            res_outs = self.strip(result.Stdout)
            ans_outputs = self.strip(ans_output)
            if res_outs == ans_outputs:
                result.Status = "AC"
        return dataclasses.asdict(result)

    def build_with_make(self):
        src_dir = self._src_dir()
        client = docker.APIClient(base_url=self.docker_url)
        lang_key = self.lang if self.lang in self.image else "cpp17"
        host_config = client.create_host_config(
            binds={src_dir: {"bind": "/src", "mode": "rw"}}
        )
        container = client.create_container(
            image=self.image[lang_key],
            command=["/bin/sh", "-c", "make"],
            working_dir="/src",
            network_disabled=True,
            host_config=host_config,
        )
        exit_status = {"StatusCode": 1}
        stdout = ""
        stderr = ""
        try:
            client.start(container)
            exit_status = client.wait(container)
            stdout = client.logs(container, stdout=True, stderr=False).decode(
                "utf-8", "ignore"
            )
            stderr = client.logs(container, stdout=False, stderr=True).decode(
                "utf-8", "ignore"
            )
        except Exception as exc:
            raise ValueError(f"make execution failed: {exc}") from exc
        finally:
            try:
                client.remove_container(container, v=True, force=True)
            except Exception:
                pass
        status_code = exit_status.get("StatusCode", 1)
        status = "AC" if status_code == 0 else "CE"
        return {
            "Status": status,
            "Stdout": stdout,
            "Stderr": stderr,
            "DockerExitCode": status_code,
        }

    def _src_dir(self) -> str:
        return str(pathlib.Path(self.working_dir) / self.submission_id / "src")

    @classmethod
    def strip(cls, s: str) -> list:
        # strip trailing space for each line
        ss = [s.rstrip() for s in s.splitlines()]
        # strip redundant new line
        while len(ss) and ss[-1] == "":
            del ss[-1]
        return ss
