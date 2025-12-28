import json
import os
from pathlib import Path

# backend config
BACKEND_API = os.getenv(
    'BACKEND_API',
    'http://web:8080',
)
# sandbox token
SANDBOX_TOKEN = os.getenv(
    'SANDBOX_TOKEN',
    'KoNoSandboxDa',
)
TESTDATA_ROOT = Path(os.getenv(
    'TESTDATA_ROOT',
    'sandbox-testdata',
))
TESTDATA_ROOT.mkdir(exist_ok=True)
SUBMISSION_DIR = Path(os.getenv(
    'SUBMISSION_DIR',
    'submissions',
))
SUBMISSION_BACKUP_DIR = Path(
    os.getenv(
        'SUBMISSION_BACKUP_DIR',
        'submissions.bk',
    ))
# create directory
SUBMISSION_DIR.mkdir(exist_ok=True)
SUBMISSION_BACKUP_DIR.mkdir(exist_ok=True)

_DEFAULT_DISPATCHER_CONFIG_PATH = Path(
    os.getenv('DISPATCHER_CONFIG', '.config/dispatcher.json'))


def _load_dispatcher_config(path: Path) -> dict:
    try:
        with path.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def get_dispatcher_limits(
        config_path: str | Path | None = None) -> tuple[int, int]:
    path = Path(
        config_path) if config_path else _DEFAULT_DISPATCHER_CONFIG_PATH
    cfg = _load_dispatcher_config(path) if path else {}
    queue_default = cfg.get('QUEUE_SIZE', 16)
    container_default = cfg.get('MAX_CONTAINER_NUMBER', 8)
    queue_size = int(os.getenv('QUEUE_SIZE', queue_default))
    container_limit = int(os.getenv('MAX_CONTAINER_NUMBER', container_default))
    return queue_size, container_limit


_SUBMISSION_CONFIG_PATH = Path(
    os.getenv('SUBMISSION_CONFIG', '.config/submission.json'))


def get_submission_config(config_path: str | Path | None = None) -> dict:
    path = Path(config_path) if config_path else _SUBMISSION_CONFIG_PATH
    cfg = _load_dispatcher_config(path) if path else {}
    working_dir_env = os.getenv('SUBMISSION_WORKING_DIR')
    if working_dir_env:
        cfg['working_dir'] = working_dir_env
    cfg.setdefault('working_dir', str(SUBMISSION_DIR))
    return cfg
