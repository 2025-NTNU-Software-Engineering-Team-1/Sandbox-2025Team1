#!/usr/bin/env python3
"""Test path conversion and resource copying"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, '/home/camel0311/code/NOJ_Repo/Normal-OJ-2025Team1/Sandbox')

from dispatcher import config
from runner.path_utils import PathTranslator
from runner.submission import SubmissionRunner

print("=== Testing Path Conversion ===")
translator = PathTranslator()

# Simulate the case_dir path
case_dir_relative = config.SUBMISSION_DIR / "test_id" / "src" / "cases" / "0000"
print(f"case_dir (relative): {case_dir_relative}")

# Create the directory
case_dir_absolute = case_dir_relative.absolute()
print(f"case_dir (absolute): {case_dir_absolute}")

# Convert to host path (this is what gets passed to Docker)
host_path = translator.to_host(case_dir_relative)
print(f"host_path: {host_path}")

# Now test with a string path (as passed to SubmissionRunner)
case_dir_str = str(case_dir_relative)
print(f"\ncase_dir_str: {case_dir_str}")


# Create a test SubmissionRunner to see how it handles the path
class MockRunner:

    def __init__(self, case_dir):
        self.translator = PathTranslator()
        self.case_dir = Path(case_dir) if case_dir else None

    def _run_src_dir(self):
        if self.case_dir:
            return str(self.case_dir)
        return "common"

    def get_docker_src_dir(self):
        return str(self.translator.to_host(self._run_src_dir()))


runner = MockRunner(case_dir_str)
print(f"\n_run_src_dir(): {runner._run_src_dir()}")
print(f"docker_src_dir: {runner.get_docker_src_dir()}")

print("\n=== Testing Actual File Check ===")
# Check if we can create the directory and verify the path
test_dir = Path(
    "/home/camel0311/code/NOJ_Repo/Normal-OJ-2025Team1/Sandbox/submissions/test_debug/src/cases/0000"
)
test_dir.mkdir(parents=True, exist_ok=True)

# Create a test file
test_file = test_dir / "input.bmp"
test_file.write_text("test content")
print(f"Created test file: {test_file}")
print(f"File exists: {test_file.exists()}")

# Check what the Docker container would see
# The container mounts host_root -> /src
# So host_root/submissions/test_debug/src/cases/0000 -> /src
print(f"\nIn Docker container, '/src' would be: {test_dir}")
print(f"And '/src/input.bmp' would exist: {test_file.exists()}")

# Cleanup
shutil.rmtree(test_dir.parent.parent.parent.parent)
print("\nCleaned up test directory")
