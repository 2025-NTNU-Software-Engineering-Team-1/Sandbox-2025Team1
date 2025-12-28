from pathlib import Path

from dispatcher.custom_checker import _parse_checker_output, run_custom_checker_case


def test_parse_checker_output_accepts_ac():
    status, message = _parse_checker_output("STATUS: AC\nMESSAGE: ok\n")
    assert status == "AC"
    assert message == "ok"


def test_parse_checker_output_invalid_status_returns_none():
    status, message = _parse_checker_output("STATUS: CE\nMESSAGE: bad\n")
    assert status is None
    assert message == "bad"


def test_run_custom_checker_case_ai_env(monkeypatch, tmp_path):
    checker_path = tmp_path / "custom_checker.py"
    checker_path.write_text("print('ok')")
    case_in = tmp_path / "0000.in"
    case_out = tmp_path / "0000.out"
    case_in.write_text("1")
    case_out.write_text("1")

    class DummyTranslator:

        def __init__(self):
            pass

        def to_host(self, path):
            return Path(path)

    captured = {}

    class DummyRunner:

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self):
            return {
                "stdout": "STATUS: AC\nMESSAGE: ok\n",
                "exit_code": 0,
                "stderr": "",
            }

    monkeypatch.setattr("dispatcher.custom_checker.PathTranslator",
                        DummyTranslator)
    monkeypatch.setattr("dispatcher.custom_checker.CustomCheckerRunner",
                        DummyRunner)
    monkeypatch.setattr("dispatcher.testdata.fetch_checker_api_key",
                        lambda pid: "key-123")

    result = run_custom_checker_case(
        submission_id="sub-1",
        case_no="0000",
        checker_path=checker_path,
        case_in_path=case_in,
        case_ans_path=case_out,
        student_output="1",
        time_limit_ms=1000,
        mem_limit_kb=1024,
        image="dummy",
        docker_url="unix://dummy",
        ai_checker_config={
            "enabled": True,
            "model": "fake-model",
        },
        problem_id=1,
    )

    assert result["status"] == "AC"
    assert captured["env"]["AI_API_KEY"] == "key-123"
    assert captured["env"]["AI_MODEL"] == "fake-model"
    assert captured["enable_ai_network"] is True
