import dataclasses
import pathlib
from typing import Optional
import docker
from dispatcher import config as dispatcher_config
from runner.sandbox import Sandbox, JudgeError


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
    ):
        # config file
        submission_cfg = dispatcher_config.get_submission_config()
        self.lang = lang
        self.special_judge = special_judge
        # required
        self.submission_id = submission_id
        self.time_limit = time_limit
        self.mem_limit = mem_limit
        self.testdata_input_path = testdata_input_path  # absoulte path str
        self.testdata_output_path = testdata_output_path  # absoulte path str
        # working_dir
        self.working_dir = submission_cfg['working_dir']
        self.docker_url = submission_cfg.get('docker_url',
                                             'unix://var/run/docker.sock')
        # for language specified settings
        self.lang_id = submission_cfg['lang_id']
        self.image = submission_cfg['image']

    def compile(self):
        try:
            # compile must be done in 20 seconds
            result = Sandbox(
                time_limit=20000,  # 20s
                mem_limit=1048576,  # 1GB
                image=self.image[self.lang],
                src_dir=self._src_dir(),
                lang_id=self.lang_id[self.lang],
                compile_need=True,
            ).run()
        except JudgeError:
            return {'Status': 'JE'}
        if result.Status == 'Exited Normally':
            result.Status = 'AC'
        else:
            result.Status = 'CE'
        return dataclasses.asdict(result)

    def run(self):
        try:
            result = Sandbox(
                time_limit=self.time_limit,
                mem_limit=self.mem_limit,
                image=self.image[self.lang],
                src_dir=self._src_dir(),
                lang_id=self.lang_id[self.lang],
                compile_need=False,
                stdin_path=self.testdata_input_path,
            ).run()
        except JudgeError:
            return {'Status': 'JE'}
        with open(self.testdata_output_path, 'r') as f:
            ans_output = f.read()
        status = {'TLE', 'MLE', 'RE', 'OLE'}
        if result.Status not in status:
            result.Status = 'WA'
            res_outs = self.strip(result.Stdout)
            ans_outputs = self.strip(ans_output)
            if res_outs == ans_outputs:
                result.Status = 'AC'
        return dataclasses.asdict(result)

    def build_with_make(self):
        src_dir = self._src_dir()
        client = docker.APIClient(base_url=self.docker_url)
        lang_key = self.lang if self.lang in self.image else 'cpp17'
        host_config = client.create_host_config(
            binds={src_dir: {
                'bind': '/src',
                'mode': 'rw'
            }})
        container = client.create_container(
            image=self.image[lang_key],
            command=["/bin/sh", "-c", "make"],
            working_dir='/src',
            network_disabled=True,
            host_config=host_config,
        )
        exit_status = {'StatusCode': 1}
        stdout = ''
        stderr = ''
        try:
            client.start(container)
            exit_status = client.wait(container)
            stdout = client.logs(container, stdout=True,
                                 stderr=False).decode('utf-8', 'ignore')
            stderr = client.logs(container, stdout=False,
                                 stderr=True).decode('utf-8', 'ignore')
        except Exception as exc:
            raise ValueError(f"make execution failed: {exc}") from exc
        finally:
            try:
                client.remove_container(container, v=True, force=True)
            except Exception:
                pass
        status_code = exit_status.get('StatusCode', 1)
        status = 'AC' if status_code == 0 else 'CE'
        return {
            'Status': status,
            'Stdout': stdout,
            'Stderr': stderr,
            'DockerExitCode': status_code,
        }

    def _src_dir(self) -> str:
        return str(pathlib.Path(self.working_dir) / self.submission_id / 'src')

    @classmethod
    def strip(cls, s: str) -> list:
        # strip trailing space for each line
        ss = [s.rstrip() for s in s.splitlines()]
        # strip redundant new line
        while len(ss) and ss[-1] == '':
            del ss[-1]
        return ss
