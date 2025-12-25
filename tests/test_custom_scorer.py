import json

from dispatcher.custom_scorer import _parse_scorer_output, ensure_custom_scorer


def test_ensure_custom_scorer_copies_asset(tmp_path, monkeypatch):
    src = tmp_path / "score.py"
    src.write_text("print('ok')")

    monkeypatch.setattr("dispatcher.custom_scorer.ensure_custom_asset",
                        lambda problem_id, asset_type: src)

    submission_path = tmp_path / "submission"
    submission_path.mkdir()

    target = ensure_custom_scorer(1, submission_path)
    assert target == submission_path / "scorer" / "score.py"
    assert target.read_text() == "print('ok')"


def test_parse_scorer_output_invalid_json():
    result = _parse_scorer_output({
        "stdout": "not-json",
        "stderr": "",
        "exit_code": 0,
    })
    assert result["status"] == "JE"
    assert result["message"] == "Invalid scorer output"
    assert result["stdout"] == "not-json"


def test_parse_scorer_output_non_int_score_defaults_zero():
    stdout = json.dumps({
        "score": "10",
        "message": "ok",
    })
    result = _parse_scorer_output({
        "stdout": stdout,
        "stderr": "",
        "exit_code": 0,
    })
    assert result["status"] == "OK"
    assert result["score"] == 0
    assert result["message"] == "ok"


def test_parse_scorer_output_nonzero_exit_uses_stderr():
    stdout = json.dumps({
        "score": 10,
        "message": "ok",
    })
    result = _parse_scorer_output({
        "stdout": stdout,
        "stderr": "boom",
        "exit_code": 2,
    })
    assert result["status"] == "JE"
    assert result["message"] == "boom"
