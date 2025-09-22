"""Utility for manually invoking the sandbox runner.

Run this helper inside the sandbox container to execute a prepared
submission and inspect the raw sandbox response.  It wraps the
:class:`runner.sandbox.Sandbox` class directly so all diagnostic fields
(status, stdout, stderr, exit message, docker exit code, …) are printed
without the post-processing that :class:`runner.submission.SubmissionRunner`
performs.

Example::

    python manual_runner.py \
        --submission 68d0478037f252dba0bda786 \
        --lang c11 \
        --stdin /app/submissions/68d0478037f252dba0bda786/testcase/0000.in \
        --time-limit 1000 \
        --mem-limit 134218

Add ``--compile-first`` to trigger the compilation stage before running.
Use ``--no-run`` when you only care about the compile result.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from runner.sandbox import Sandbox


def load_config(config_path: Path) -> Dict[str, Any]:
    """Return parsed submission runner configuration."""

    with config_path.open() as handle:
        return json.load(handle)


def run_sandbox(
    *,
    submission_id: str,
    lang: str,
    stdin_path: str | None,
    time_limit: int,
    mem_limit: int,
    compile_need: bool,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute the sandbox with the provided configuration."""

    working_dir = Path(config["working_dir"])
    src_dir = working_dir / submission_id / "src"
    if not src_dir.exists():
        raise FileNotFoundError(f"source directory not found: {src_dir}")

    sandbox = Sandbox(
        time_limit=time_limit,
        mem_limit=mem_limit,
        image=config["image"][lang],
        src_dir=str(src_dir),
        lang_id=config["lang_id"][lang],
        compile_need=compile_need,
        stdin_path=stdin_path,
    )
    return asdict(sandbox.run())


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submission",
        required=True,
        help="submission ID to run",
    )
    parser.add_argument(
        "--lang",
        default="c11",
        choices=("c11", "cpp17", "python3"),
        help="language key used in .config/submission.json",
    )
    parser.add_argument(
        "--stdin",
        help="absolute path to testcase input file (omit for empty stdin)",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=1000,
        help="time limit in milliseconds",
    )
    parser.add_argument(
        "--mem-limit",
        type=int,
        default=262144,
        help="memory limit in kilobytes",
    )
    parser.add_argument(
        "--compile-first",
        action="store_true",
        help="run compilation before executing the testcase",
    )
    parser.add_argument(
        "--run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="execute the testcase after compilation (default: true)",
    )
    parser.add_argument(
        "--config",
        default=Path(".config/submission.json"),
        type=Path,
        help="path to submission runner configuration file",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    args = parse_args()
    config = load_config(args.config)

    if args.compile_first:
        compile_result = run_sandbox(
            submission_id=args.submission,
            lang=args.lang,
            stdin_path=None,
            time_limit=20000,
            mem_limit=1048576,
            compile_need=True,
            config=config,
        )
        print("=== compile ===")
        print(json.dumps(compile_result, indent=2, ensure_ascii=False))

    if args.run:
        run_result = run_sandbox(
            submission_id=args.submission,
            lang=args.lang,
            stdin_path=args.stdin,
            time_limit=args.time_limit,
            mem_limit=args.mem_limit,
            compile_need=False,
            config=config,
        )
        print("=== run ===")
        print(json.dumps(run_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
