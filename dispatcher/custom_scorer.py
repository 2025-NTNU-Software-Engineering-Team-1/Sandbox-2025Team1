import json
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import TESTDATA_ROOT
from .asset_cache import ensure_custom_asset, AssetNotFoundError
from .result_factory import make_scorer_result
from runner.path_utils import PathTranslator
from runner.custom_scorer_runner import CustomScorerRunner, CustomScorerError


class CustomScorerSetupError(Exception):
    """Raised when scorer asset is missing or cannot be prepared."""


def ensure_custom_scorer(problem_id: int, submission_path: Path) -> Path:
    """Download/cache custom scorer and copy into submission folder."""
    try:
        scorer_path = ensure_custom_asset(problem_id, "scoring_script")
    except AssetNotFoundError as exc:
        raise CustomScorerSetupError(str(exc)) from exc
    except Exception as exc:
        raise CustomScorerSetupError(
            f"custom scorer asset not found: {exc}") from exc
    submission_scorer_dir = submission_path / "scorer"
    submission_scorer_dir.mkdir(parents=True, exist_ok=True)
    target = submission_scorer_dir / "score.py"
    shutil.copyfile(scorer_path, target)
    return target


def run_custom_scorer(
    scorer_path: Path,
    payload: Dict,
    time_limit_ms: int,
    mem_limit_kb: int,
    image: str,
    docker_url: str,
) -> Dict[str, object]:
    """Execute custom scorer and return parsed result."""
    workdir = scorer_path.parent / "work"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        local_scorer = workdir / "score.py"
        shutil.copyfile(scorer_path, local_scorer)
        scoring_input_path = workdir / "scoring_input.json"
        scoring_input_path.write_text(json.dumps(payload, ensure_ascii=False))
        translator = PathTranslator()
        host_workdir = translator.to_host(workdir)
        runner = CustomScorerRunner(
            image=image,
            docker_url=docker_url,
            workdir=str(host_workdir),
            scorer_relpath="score.py",
            time_limit_ms=time_limit_ms,
            mem_limit_kb=mem_limit_kb,
        )
        result = runner.run(payload)
    except (CustomScorerError, CustomScorerSetupError) as exc:
        _cleanup(workdir)
        return make_scorer_result(status="JE", message=str(exc))
    except Exception as exc:
        _cleanup(workdir)
        return make_scorer_result(status="JE", message=str(exc))
    finally:
        _cleanup(workdir)

    return _parse_scorer_output(result)


def _parse_scorer_output(raw: Dict[str, str]) -> Dict[str, object]:
    stdout = raw.get("stdout", "")
    stderr = raw.get("stderr", "")
    exit_code = raw.get("exit_code", 1)
    parsed: Dict[str, object] = {}
    try:
        parsed = json.loads(stdout) if stdout else {}
    except Exception:
        return make_scorer_result(status="JE",
                                  message="Invalid scorer output",
                                  stdout=stdout,
                                  stderr=stderr)

    score = parsed.get("score", 0)
    message = parsed.get("message", "")
    breakdown = parsed.get("breakdown")
    status = "OK"
    if exit_code != 0:
        status = "JE"
        if stderr:
            message = stderr
    return {
        "status": status,
        "score": score if isinstance(score, int) else 0,
        "message": message or "",
        "breakdown": breakdown,
        "stdout": stdout,
        "stderr": stderr,
    }


def _cleanup(path: Path):
    try:
        if path.exists():
            shutil.rmtree(path)
    except Exception:
        pass
