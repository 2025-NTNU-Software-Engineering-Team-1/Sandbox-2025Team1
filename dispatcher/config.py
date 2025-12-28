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


# ============================================================
# Sidecar Resource Limits Configuration
# ============================================================
SIDECAR_MEM_LIMIT = os.getenv('SIDECAR_MEM_LIMIT', '512m')
SIDECAR_CPU_PERIOD = int(os.getenv('SIDECAR_CPU_PERIOD', '100000'))
SIDECAR_CPU_QUOTA = int(os.getenv('SIDECAR_CPU_QUOTA', '50000'))
SIDECAR_PIDS_LIMIT = int(os.getenv('SIDECAR_PIDS_LIMIT', '100'))
# Delay (in seconds) to wait for container services (e.g., HTTP servers) to be ready
# after the container is in 'running' state
SERVICE_STARTUP_DELAY = float(os.getenv('SERVICE_STARTUP_DELAY', '5.0'))

# ============================================================
# Docker Image Security Configuration
# ============================================================
# Comma-separated list of allowed registries
# Default: docker.io (Docker Hub official images)
_allowed_registries_raw = os.getenv('ALLOWED_REGISTRIES', 'docker.io')
ALLOWED_REGISTRIES = [
    r.strip() for r in _allowed_registries_raw.split(',') if r.strip()
]

# ============================================================
# Docker Build Configuration
# ============================================================
DOCKER_BUILD_TIMEOUT = int(os.getenv('DOCKER_BUILD_TIMEOUT',
                                     '300'))  # 5 minutes
