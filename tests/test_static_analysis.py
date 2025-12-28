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
