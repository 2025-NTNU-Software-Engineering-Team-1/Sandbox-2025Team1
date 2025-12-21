"""
AC Code Runner - Pure Execution Layer

Executes AC (Accepted) code in Docker containers.
This module only handles execution logic, no caching or business logic.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


class ACCodeCompileError(Exception):
    """Raised when AC code fails to compile."""
    pass


class ACCodeRunError(Exception):
    """Raised when AC code fails to run."""
    pass


@dataclass
class ACCodeRunner:
    """
    Pure executor for AC Code.
    
    Only handles:
    - Compilation (C/C++)
    - Single test case execution
    
    Does NOT handle:
    - Caching / downloading AC code
    - Batch processing
    - Business logic
    """
    src_dir: Path  # Path to AC code source directory
    lang_key: str  # Language key: c11, cpp17, python3

    def compile(self) -> Dict:
        """
        Compile AC Code (for C/C++).
        
        Returns:
            Result dict with Status, Stdout, Stderr
        """
        from runner.submission import SubmissionRunner

        return SubmissionRunner.compile_at_path(
            src_dir=str(self.src_dir),
            lang=self.lang_key,
        )

    def run_single(
        self,
        in_path: Path,
        time_limit: int = 30000,
        mem_limit: int = 1048576,
    ) -> Dict:
        """
        Execute AC code for a single test case.
        
        Args:
            in_path: Path to input file (.in)
            time_limit: Time limit in ms (default: 30s)
            mem_limit: Memory limit in KB (default: 1GB)
        
        Returns:
            Result dict with status, stdout, stderr
        """
        from runner.sandbox import Sandbox, JudgeError
        from runner.path_utils import PathTranslator

        translator = PathTranslator()
        cfg = translator.cfg

        try:
            result = Sandbox(
                time_limit=time_limit,
                mem_limit=mem_limit,
                image=cfg["image"][self.lang_key],
                src_dir=str(translator.to_host(self.src_dir)),
                lang_id=cfg["lang_id"][self.lang_key],
                compile_need=False,  # Already compiled or interpreted
                stdin_path=str(translator.to_host(in_path)),
            ).run()
        except JudgeError as exc:
            raise ACCodeRunError(f"AC code execution failed: {exc}") from exc

        return {
            "status": result.Status,
            "stdout": result.Stdout,
            "stderr": result.Stderr,
            "duration": result.Duration,
            "mem_usage": result.MemUsage,
        }
