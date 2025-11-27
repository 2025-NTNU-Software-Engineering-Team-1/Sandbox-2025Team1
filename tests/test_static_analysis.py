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


def test_zip_static_analysis_python_return_blacklist(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def f(x):\n"
                                     "    if x > 0:\n"
                                     "        return x\n"
                                     "    return -x\n")
    (src_dir / "Makefile").write_text("run:\n\tpython main.py\n")
    rules = {"model": "black", "syntax": ["return"]}
    res = StaticAnalyzer().analyze_zip_sources(
        source_dir=src_dir,
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "return" in res.violations


def test_zip_static_analysis_disallowed_language_files(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('ok')")
    (src_dir / "bad.cpp").write_text("int main(){return 0;}")
    rules = {"model": "black", "syntax": []}
    res = StaticAnalyzer().analyze_zip_sources(
        source_dir=src_dir,
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "Disallowed language files" in res.message
