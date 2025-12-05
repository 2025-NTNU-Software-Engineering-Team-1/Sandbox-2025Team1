#!/usr/bin/env python3
from dispatcher import config
from runner.path_utils import PathTranslator
from pathlib import Path

print("=== Config ===")
print(f"SUBMISSION_DIR: {config.SUBMISSION_DIR}")
print(f"SUBMISSION_DIR.absolute(): {config.SUBMISSION_DIR.absolute()}")

print("\n=== PathTranslator ===")
translator = PathTranslator()
print(f"working_dir: {translator.working_dir}")
print(f"sandbox_root: {translator.sandbox_root}")
print(f"host_root: {translator.host_root}")

print("\n=== Path Conversion Test ===")
# Simulate case_dir
case_dir = config.SUBMISSION_DIR / "test_submission" / "src" / "cases" / "0000"
print(f"case_dir (sandbox): {case_dir}")
print(f"case_dir.absolute(): {case_dir.absolute()}")

# Convert to host path
host_path = translator.to_host(case_dir)
print(f"host_path: {host_path}")
