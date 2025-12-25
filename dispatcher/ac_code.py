"""
AC Code Business Logic Layer

Handles caching, preparation, and batch processing for AC Code execution.
Uses runner/ac_code_runner.py for actual execution.
"""

from pathlib import Path
from typing import Tuple

from .constant import Language
from .utils import logger
from .testdata import ensure_ac_code
from runner.ac_code_runner import ACCodeRunner, ACCodeCompileError, ACCodeRunError

# Language enum to runner lang_key mapping
LANG_KEY_MAP = {
    Language.C: "c11",
    Language.CPP: "cpp17",
    Language.PY: "python3",
}


def get_ac_runner(problem_id: int) -> ACCodeRunner:
    """
    Get a compiled/ready AC Code Runner for a problem.
    
    This function:
    1. Fetches AC code from cache (downloads if needed)
    2. Compiles if C/C++
    3. Returns ready-to-use runner
    
    Args:
        problem_id: Problem ID
    
    Returns:
        ACCodeRunner instance ready for execution
    
    Raises:
        ValueError: If AC code not found or language unknown
        ACCodeCompileError: If compilation fails
    """
    ac_code_path, language = ensure_ac_code(problem_id)

    if language is None:
        raise ValueError(
            f"AC code language not found for problem {problem_id}")

    lang_enum = Language(language)
    lang_key = LANG_KEY_MAP.get(lang_enum)

    if lang_key is None:
        raise ValueError(f"Unsupported AC code language: {language}")

    runner = ACCodeRunner(src_dir=ac_code_path, lang_key=lang_key)

    # Compile C/C++
    if lang_enum in (Language.C, Language.CPP):
        logger().info(f"Compiling AC code for problem {problem_id}")
        result = runner.compile()

        if result.get("Status") != "AC":
            stderr = result.get("Stderr", "Unknown error")
            raise ACCodeCompileError(
                f"AC code compile failed for problem {problem_id}: {stderr}")

        logger().info(
            f"AC code compiled successfully for problem {problem_id}")

    return runner


def generate_ac_outputs(
    problem_id: int,
    testdata_dir: Path,
    time_limit: int = 30000,
    mem_limit: int = 1048576,
) -> int:
    """
    Generate .out files for all .in files in the test data directory.
    
    This function:
    1. Gets compiled AC code runner
    2. Iterates through all .in files
    3. Executes AC code and writes .out files
    
    Args:
        problem_id: Problem ID to get AC code for
        testdata_dir: Directory containing .in files
        time_limit: Time limit per case in ms (default: 30s)
        mem_limit: Memory limit per case in KB (default: 1GB)
    
    Returns:
        Number of .out files generated
    
    Raises:
        ValueError: If AC code not found
        ACCodeCompileError: If AC code fails to compile
    """
    runner = get_ac_runner(problem_id)
    count = 0

    for in_file in sorted(testdata_dir.glob("*.in")):
        out_file = in_file.with_suffix(".out")

        # Skip if .out already exists and is non-empty
        # (empty .out files may be from previous failed attempts)
        if out_file.exists() and out_file.stat().st_size > 0:
            logger().debug(f"Skipping {in_file.name} - .out already exists")
            continue

        logger().debug(f"Generating output for {in_file.name}")

        try:
            result = runner.run_single(in_file, time_limit, mem_limit)

            # Check for errors
            if result["status"] in ("TLE", "MLE", "RE", "OLE"):
                logger().error(
                    f"AC code error for {in_file.name}: {result['status']} - {result['stderr']}"
                )
                # Write empty file to avoid breaking flow
                out_file.write_text("")
            else:
                # Write stdout to output file
                out_file.write_text(result["stdout"] or "")

            count += 1

        except ACCodeRunError as exc:
            logger().error(
                f"Failed to generate output for {in_file.name}: {exc}")
            # Create empty .out file to avoid breaking the flow
            out_file.write_text("")
            count += 1

    logger().info(f"Generated {count} .out files for problem {problem_id}")
    return count
