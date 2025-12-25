import json
import pathlib
import pytest


@pytest.mark.parametrize(
    "stdout, answer, excepted",
    [
        # exactly the same
        ("aaa\nbbb\n", "aaa\nbbb\n", True),
        # trailing space before new line
        ("aaa  \nbbb\n", "aaa\nbbb\n", True),
        # redundant new line at the end
        ("aaa\nbbb\n\n", "aaa\nbbb\n", True),
        # redundant new line in the middle
        ("aaa\n\nbbb\n", "aaa\nbbb\n", False),
        # trailing space at the start
        ("aaa\n bbb\b", "aaa\nbbb\n", False),
        # empty string
        ("", "", True),
        # only new line
        ("\n\n\n\n", "", True),
        # empty character
        ("\t\r\n", "", True),
        # crlf
        ("crlf\r\n", "crlf\n", True),
    ],
)
def test_strip_func(TestSubmissionRunner, stdout, answer, excepted):
    assert (TestSubmissionRunner.strip(stdout) == TestSubmissionRunner.strip(
        answer)) is excepted


def test_c_tle(submission_generator, TestSubmissionRunner):
    submission_id = [
        _id for _id, pn in submission_generator.submission_ids.items()
        if pn == "c-TLE"
    ][0]
    submission_path = submission_generator.get_submission_path(submission_id)

    runner = TestSubmissionRunner(
        submission_id=submission_id,
        time_limit=1000,
        mem_limit=32768,
        testdata_input_path=submission_path + "/testcase/0000.in",
        testdata_output_path=submission_path + "/testcase/0000.out",
        lang="c11",
    )

    # Patch Sandbox to avoid real docker
    from runner import sandbox as sb
    import runner.submission as subm

    class DummySandbox:

        def __init__(self, *args, **kwargs):
            self.compile_need = kwargs.get('compile_need', False)

        def run(self):
            if self.compile_need:
                return sb.Result(Status='Exited Normally',
                                 Duration=0,
                                 MemUsage=0,
                                 Stdout='',
                                 Stderr='',
                                 ExitMsg='',
                                 DockerError='',
                                 DockerExitCode=0)
            return sb.Result(Status='TLE',
                             Duration=0,
                             MemUsage=0,
                             Stdout='',
                             Stderr='',
                             ExitMsg='',
                             DockerError='',
                             DockerExitCode=124)

    sb_backup = sb.Sandbox
    sb_sub_backup = subm.Sandbox
    sb.Sandbox = DummySandbox
    subm.Sandbox = DummySandbox
    try:
        res = runner.compile()
        assert res['Status'] == 'AC', json.dumps(res)
        res = runner.run()
        assert res['Status'] == 'TLE', json.dumps(res)
    finally:
        sb.Sandbox = sb_backup
        subm.Sandbox = sb_sub_backup


def test_non_strict_diff(submission_generator, TestSubmissionRunner):
    submission_id = [
        _id for _id, pn in submission_generator.submission_ids.items()
        if pn == "space-before-lf"
    ][0]
    submission_path = submission_generator.get_submission_path(submission_id)

    runner = TestSubmissionRunner(
        submission_id=submission_id,
        time_limit=1000,
        mem_limit=32768,
        testdata_input_path=submission_path + "/testcase/0000.in",
        testdata_output_path=submission_path + "/testcase/0000.out",
        lang="python3",
    )

    expected_output = pathlib.Path(submission_path +
                                   '/testcase/0000.out').read_text()

    from runner import sandbox as sb
    import runner.submission as subm

    class DummySandbox:

        def __init__(self, *args, **kwargs):
            self.compile_need = kwargs.get('compile_need', False)

        def run(self):
            if self.compile_need:
                return sb.Result(Status='Exited Normally',
                                 Duration=0,
                                 MemUsage=0,
                                 Stdout='',
                                 Stderr='',
                                 ExitMsg='',
                                 DockerError='',
                                 DockerExitCode=0)
            return sb.Result(Status='Exited Normally',
                             Duration=0,
                             MemUsage=0,
                             Stdout=expected_output,
                             Stderr='',
                             ExitMsg='',
                             DockerError='',
                             DockerExitCode=0)

    sb_backup = sb.Sandbox
    sb_sub_backup = subm.Sandbox
    sb.Sandbox = DummySandbox
    subm.Sandbox = DummySandbox
    try:
        res = runner.run()
        assert res['Status'] == 'AC', res
    finally:
        sb.Sandbox = sb_backup
        subm.Sandbox = sb_sub_backup


def _patch_docker_client(monkeypatch, status_code):

    class DummyClient:

        def __init__(self, base_url=None):
            self.status_code = status_code

        def create_host_config(self, binds):
            return binds

        def create_container(self, **kwargs):
            return {"Id": "dummy"}

        def start(self, container):
            return

        def wait(self, container):
            return {"StatusCode": self.status_code}

        def logs(self, container, stdout=False, stderr=False):
            return b"stdout" if stdout else b"stderr"

        def remove_container(self, container, v=True, force=True):
            return

    monkeypatch.setattr("runner.submission.docker.APIClient", DummyClient)


def _ensure_src_dir(runner: "SubmissionRunner"):
    src_dir = pathlib.Path(runner.working_dir)
    src_dir.mkdir(parents=True, exist_ok=True)
    return src_dir


def test_build_with_make_success(monkeypatch, TestSubmissionRunner):
    runner = TestSubmissionRunner(
        submission_id="zip-success",
        time_limit=1000,
        mem_limit=32768,
        testdata_input_path="",
        testdata_output_path="",
        lang="cpp17",
    )
    _ensure_src_dir(runner)
    _patch_docker_client(monkeypatch, status_code=0)
    res = runner.build_with_make()
    assert res["Status"] == "AC"
    assert res["DockerExitCode"] == 0


def test_build_with_make_failure(monkeypatch, TestSubmissionRunner):
    runner = TestSubmissionRunner(
        submission_id="zip-fail",
        time_limit=1000,
        mem_limit=32768,
        testdata_input_path="",
        testdata_output_path="",
        lang="cpp17",
    )
    _ensure_src_dir(runner)
    _patch_docker_client(monkeypatch, status_code=2)
    res = runner.build_with_make()
    assert res["Status"] == "CE"
    assert res["DockerExitCode"] == 2


def test_sandbox_run_skips_stdin_bind_when_missing(monkeypatch, tmp_path):
    from runner.sandbox import Sandbox

    class DummyDockerClient:

        def __init__(self):
            self.last_binds = None
            self.last_volumes = None

        def create_host_config(self, **kwargs):
            self.last_binds = kwargs.get("binds")
            return {"_host_config": kwargs}

        def create_container(
            self,
            image,
            command,
            volumes,
            network_disabled,
            working_dir,
            host_config,
            environment=None,
        ):
            self.last_volumes = volumes
            return {"Id": "dummy", "Warning": None}

        def start(self, container):
            return None

        def wait(self, container, timeout=None):
            return {"StatusCode": 0}

        def remove_container(self, container, v=True, force=True):
            return None

    def _fake_get(self, container, path, filename):
        if filename == "result":
            return "Exited Normally\nWEXITSTATUS() = 0\n0\n0\n"
        return ""

    monkeypatch.chdir(pathlib.Path(__file__).resolve().parents[1])
    client = DummyDockerClient()
    monkeypatch.setattr("runner.sandbox.docker.APIClient",
                        lambda base_url: client)
    monkeypatch.setattr(Sandbox, "get", _fake_get)

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    runner = Sandbox(
        time_limit=1000,
        mem_limit=1024,
        image="dummy",
        src_dir=str(src_dir),
        lang_id="0",
        compile_need=False,
        stdin_path=None,
    )
    runner.run()

    assert client.last_binds is not None
    assert client.last_volumes is not None
    assert all(
        mount.get("bind") != "/testdata/in"
        for mount in client.last_binds.values())
    assert all(
        mount.get("bind") != "/testdata/in"
        for mount in client.last_volumes.values())


@pytest.mark.parametrize(
    ("network_mode", "expected_flag", "expected_disabled"),
    [
        ("none", "0", True),
        ("noj-net-1", "1", False),
    ],
)
def test_sandbox_run_sets_allow_write_and_network(monkeypatch, tmp_path,
                                                  network_mode, expected_flag,
                                                  expected_disabled):
    from runner.sandbox import Sandbox

    class DummyDockerClient:

        def __init__(self):
            self.container_kwargs = None
            self.host_config_kwargs = None

        def create_host_config(self, **kwargs):
            self.host_config_kwargs = kwargs
            return {"_host_config": kwargs}

        def create_container(
            self,
            image,
            command,
            volumes,
            network_disabled,
            working_dir,
            host_config,
            environment=None,
        ):
            self.container_kwargs = {
                "image": image,
                "command": command,
                "volumes": volumes,
                "network_disabled": network_disabled,
                "working_dir": working_dir,
                "host_config": host_config,
                "environment": environment,
            }
            return {"Id": "dummy", "Warning": None}

        def start(self, container):
            return None

        def wait(self, container, timeout=None):
            return {"StatusCode": 0}

        def remove_container(self, container, v=True, force=True):
            return None

    def _fake_get(self, container, path, filename):
        if filename == "result":
            return "Exited Normally\nWEXITSTATUS() = 0\n0\n0\n"
        return ""

    monkeypatch.chdir(pathlib.Path(__file__).resolve().parents[1])
    client = DummyDockerClient()
    monkeypatch.setattr("runner.sandbox.docker.APIClient",
                        lambda base_url: client)
    monkeypatch.setattr(Sandbox, "get", _fake_get)

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    stdin_path = tmp_path / "input.in"
    stdin_path.write_text("1")

    runner = Sandbox(
        time_limit=1000,
        mem_limit=1024,
        image="dummy",
        src_dir=str(src_dir),
        lang_id="0",
        compile_need=False,
        stdin_path=str(stdin_path),
        allow_write=True,
        network_mode=network_mode,
    )
    runner.run()

    parts = client.container_kwargs["command"].split()
    assert parts[-2] == expected_flag
    assert client.container_kwargs["environment"] == {
        "SANDBOX_ALLOW_WRITE": "1"
    }
    assert client.container_kwargs["network_disabled"] is expected_disabled
    expected_net_mode = None if expected_disabled else network_mode
    assert client.host_config_kwargs["network_mode"] == expected_net_mode
