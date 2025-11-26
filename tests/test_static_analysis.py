import json
from pathlib import Path
from dispatcher.static_analysis import StaticAnalyzer
from dispatcher.constant import Language


def test_python_static_analysis_violations():
    test_file_path = Path("tests/static_analysis/test_file")
    rules_path = test_file_path / "rules.json"

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    analyzer = StaticAnalyzer()

    result = analyzer.analyze(
        submission_id=str(test_file_path),
        language=Language.PY,
        rules=rules,
    )


def test_c_static_analysis_violations():
    test_file_path = Path("tests/static_analysis/test_file")
    rules_path = test_file_path / "rules.json"

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    analyzer = StaticAnalyzer()
    result = analyzer.analyze(submission_id=str(test_file_path),
                              language=Language.C,
                              rules=rules)


def test_python_syntax_blacklist_custom(tmp_path):
    src = tmp_path / "main.py"
    src.write_text("def f(x):\n"
                   "    if x > 0:\n"
                   "        return x\n"
                   "    return -x\n")
    rules = {
        "model": "black",
        "syntax": ["return", "if"],
    }
    res = StaticAnalyzer().analyze(
        submission_id=str(tmp_path),
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "Disallowed Syntax (return)" in res.violations
    assert "Disallowed Syntax (if)" in res.violations


def test_python_syntax_whitelist_custom(tmp_path):
    src = tmp_path / "main.py"
    src.write_text("def f(x):\n"
                   "    if x > 0:\n"
                   "        return x\n"
                   "    return -x\n")
    rules = {
        "model": "white",
        "syntax": ["return"],
    }
    res = StaticAnalyzer().analyze(
        submission_id=str(tmp_path),
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "Non-whitelisted Syntax (if)" in res.violations
