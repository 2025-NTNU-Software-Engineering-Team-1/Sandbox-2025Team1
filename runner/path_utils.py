from __future__ import annotations

from pathlib import Path
from dispatcher import config as dispatcher_config


class PathTranslator:
    """
    Translate paths between sandbox view and host (docker) view.
    """

    def __init__(self, config_path: str | Path | None = None):
        self.cfg = dispatcher_config.get_submission_config(config_path)
        self.working_dir = Path(self.cfg["working_dir"]).expanduser()
        self.sandbox_root = (Path(
            self.cfg.get("sandbox_root",
                         self.working_dir.parent)).expanduser().resolve())
        self.host_root = (Path(self.cfg.get(
            "host_root", self.sandbox_root)).expanduser().resolve())

    def to_host(self, path: str | Path) -> Path:
        """
        Convert a sandbox path (or absolute path) to host path for Docker binds.
        """
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (self.sandbox_root / p).resolve()
        try:
            rel = p.relative_to(self.sandbox_root)
            return (self.host_root / rel).resolve()
        except ValueError:
            return p.resolve()
