import sys, os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pathlib import Path
from dispatcher.static_analysis import StaticAnalyzer
from dispatcher.constant import Language

submission_path = Path(
    "/mnt/d/university/using/Normal-OJ-2025Team1/Sandbox/tests/static_analysis/test_file"
)
rules_path = Path(
    "/mnt/d/university/using/Normal-OJ-2025Team1/Sandbox/tests/static_analysis/test_file/rules.json"
)
rules = json.loads(rules_path.read_text(encoding="utf-8"))
res = StaticAnalyzer.analyze(
    source_code_path=submission_path,
    language=Language.CPP,
    rules=rules,
)

print(res.is_success(), res.message)
