import sys, os
import json

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pathlib import Path
from dispatcher.static_analysis import StaticAnalyzer
from dispatcher.constant import Language

# /home/maxcho/Normal-OJ-2025Team1/Sandbox/tests/static_analysis
submission_path = Path("./test_file")
rules_path = Path("./test_file/rules.json")
rules = json.loads(rules_path.read_text(encoding="utf-8"))
analyzer_instance = StaticAnalyzer()

## submission_id IS PATH HERE !!!
analysis_result = analyzer_instance.analyze(
    submission_id=submission_path,
    language=Language.PY,
    rules=rules,
)

print("in dispatcher static result:")
print("==================")
print(analysis_result.message)
print("==================")
print(analysis_result.json_result)
