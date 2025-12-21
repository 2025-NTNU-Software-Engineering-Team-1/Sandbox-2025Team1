#!/usr/bin/env python3
import sys

print(f"Python path: {sys.path}")
print(f"Working directory: {__file__}")

try:
    from runner.ac_code_runner import ACCodeRunner
    print(f"Success! ACCodeRunner: {ACCodeRunner}")
except ImportError as e:
    print(f"Import failed: {e}")

try:
    from dispatcher.ac_code import get_ac_runner
    print(f"Success! get_ac_runner: {get_ac_runner}")
except ImportError as e:
    print(f"Import failed: {e}")
