import io
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Set
from zipfile import ZipFile

import requests

from .config import BACKEND_API, SANDBOX_TOKEN

_CASE_FILE_LIMIT = 5 * 1024 * 1024  # 5 MB per file
_CASE_ZIP_LIMIT = 10 * 1024 * 1024  # 10 MB per case zip
_SUBMISSION_TOTAL_LIMIT = 100 * 1024 * 1024  # 100 MB per submission
_BINARY_LIMIT = 50 * 1024 * 1024  # 50 MB compiled binary


class ArtifactCollector:
    """
    Collect extra artifacts (besides stdout/stderr) and compiled binary.
    Uses pre/post snapshots to find new/updated files. stdout/stderr are
    expected to reuse backend-generated zip; this collector only adds extra files.
    """

    def __init__(self,
                 backend_url: str | None = None,
                 token: str | None = None,
                 logger: Optional[logging.Logger] = None):
        self.backend_url = backend_url or BACKEND_API
        self.token = token or SANDBOX_TOKEN
        self._logger = logger or logging.getLogger(__name__)
        self._snapshots: Dict[str, Dict[str, Dict[str, os.stat_result]]] = {}
        self._case_artifacts: Dict[str, Dict[int, Dict[int, bytes]]] = {}
        self._binary: Dict[str, bytes] = {}
        self._binary_uploaded: Dict[str, bool] = {}

    # ---------- Snapshot helpers ----------
    def snapshot_before_case(self, submission_id: str, task_no: int,
                             case_no: int, workdir: Path):
        snaps = self._snapshots.setdefault(submission_id, {})
        key = self._case_key(task_no, case_no)
        snaps[key] = self._scan(workdir)

    def record_case_artifact(self, submission_id: str, task_no: int,
                             case_no: int, workdir: Path, stdout: str,
                             stderr: str):
        pre = (self._snapshots.get(submission_id,
                                   {}).get(self._case_key(task_no, case_no),
                                           {}))
        post = self._scan(workdir)
        changed = self._diff(pre, post)
        buf = io.BytesIO()
        total_size = 0
        with ZipFile(buf, "w") as zf:
            # stdout/stderr - always write to preserve data from sandbox result
            # even if empty, to maintain consistency with backend expectations
            zf.writestr("stdout", stdout or "")
            total_size += len((stdout or "").encode("utf-8", "ignore"))
            zf.writestr("stderr", stderr or "")
            total_size += len((stderr or "").encode("utf-8", "ignore"))
            # extra files
            for rel_path in changed:
                fpath = workdir / rel_path
                try:
                    size = fpath.stat().st_size
                except FileNotFoundError:
                    continue
                if size > _CASE_FILE_LIMIT:
                    self._logger.warning(
                        "artifact file too large, skip [id=%s task=%s case=%s file=%s size=%s]",
                        submission_id,
                        task_no,
                        case_no,
                        rel_path,
                        size,
                    )
                    continue
                if total_size + size > _CASE_ZIP_LIMIT:
                    self._logger.warning(
                        "artifact zip limit reached, skip remaining files [id=%s task=%s case=%s]",
                        submission_id,
                        task_no,
                        case_no,
                    )
                    break
                try:
                    with open(fpath, "rb") as fh:
                        data = fh.read()
                    zf.writestr(rel_path, data)
                    total_size += size
                except Exception as exc:
                    self._logger.warning(
                        "failed to read artifact file [id=%s task=%s case=%s file=%s]: %s",
                        submission_id,
                        task_no,
                        case_no,
                        rel_path,
                        exc,
                    )
                    continue
        buf.seek(0)
        self._add_case_artifact(submission_id, task_no, case_no,
                                buf.getvalue())

    # ---------- Binary helpers ----------
    def collect_binary(self, submission_id: str, src_dir: Path):
        if submission_id in self._binary:
            return
        candidates = ["main", "a.out"]
        for name in candidates:
            path = src_dir / name
            if path.exists() and os.access(path, os.X_OK):
                try:
                    data = path.read_bytes()
                    if not data.startswith(b"\x7fELF"):
                        self._logger.warning(
                            "binary is not ELF header, skip [id=%s path=%s]",
                            submission_id,
                            path,
                        )
                        return
                except Exception as exc:
                    self._logger.warning(
                        "failed to read binary [id=%s path=%s]: %s",
                        submission_id,
                        path,
                        exc,
                    )
                    return
                if len(data) > _BINARY_LIMIT:
                    self._logger.warning(
                        "binary too large, skip upload [id=%s size=%s]",
                        submission_id,
                        len(data),
                    )
                    return
                self._binary[submission_id] = data
                return

    def upload_binary_only(self, submission_id: str):
        payload = self._binary.get(submission_id)
        if not payload:
            return
        if self._upload_binary(submission_id, payload):
            self._binary_uploaded[submission_id] = True
            self._binary.pop(submission_id, None)

    # ---------- Upload ----------
    def upload_all(self, submission_id: str):
        used = 0
        cases = self._case_artifacts.get(submission_id, {})
        binary = self._binary.get(submission_id)
        # upload case artifacts per case
        for task_no, case_map in cases.items():
            for case_no, payload in case_map.items():
                if used + len(payload) > _SUBMISSION_TOTAL_LIMIT:
                    self._logger.warning(
                        "skip artifact upload due to submission total limit [id=%s]",
                        submission_id,
                    )
                    return
                ok = self._upload_case(submission_id, task_no, case_no,
                                       payload)
                if ok:
                    used += len(payload)
        # upload binary once
        if binary and not self._binary_uploaded.get(submission_id):
            if used + len(binary) <= _SUBMISSION_TOTAL_LIMIT:
                if self._upload_binary(submission_id, binary):
                    used += len(binary)
                    self._binary_uploaded[submission_id] = True

    def cleanup(self, submission_id: str):
        self._snapshots.pop(submission_id, None)
        self._case_artifacts.pop(submission_id, None)
        self._binary.pop(submission_id, None)
        self._binary_uploaded.pop(submission_id, None)

    # ---------- Static helpers ----------
    @staticmethod
    def should_collect_artifacts(meta) -> bool:
        try:
            return "zip" in (getattr(meta, "artifactCollection", []) or [])
        except Exception:
            return False

    @staticmethod
    def should_collect_binary(meta) -> bool:
        try:
            return "compiledBinary" in (getattr(meta, "artifactCollection", [])
                                        or [])
        except Exception:
            return False

    # ---------- Internal ----------
    def _scan(self, workdir: Path) -> Dict[str, os.stat_result]:
        res = {}
        if not workdir.exists():
            return res
        for root, _, files in os.walk(workdir):
            for fname in files:
                path = Path(root) / fname
                rel = path.relative_to(workdir)
                # skip common noise
                if rel.name.startswith("."):
                    continue
                if rel.name in {"a.out", "main"}:
                    continue
                if rel.suffix in {
                        ".c", ".cpp", ".py", ".h", ".hpp", ".o", ".a"
                }:
                    continue
                try:
                    res[str(rel)] = path.stat()
                except FileNotFoundError:
                    continue
        return res

    def _diff(self, before: Dict[str, os.stat_result],
              after: Dict[str, os.stat_result]) -> Set[str]:
        """Return set of relative paths that changed between snapshots."""
        for rel, st in after.items():
            prev = before.get(rel)
            if prev is None or (st.st_mtime, st.st_size) != (prev.st_mtime,
                                                             prev.st_size):
                # path will be resolved later from workdir; store placeholder
                pass
        # actual path reconstruction happens in record_case_artifact
        return {
            rel
            for rel in after.keys()
            if rel not in before or (after[rel].st_mtime, after[rel].st_size)
            != (before[rel].st_mtime, before[rel].st_size)
        }

    def _add_case_artifact(self, submission_id: str, task_no: int,
                           case_no: int, data: bytes):
        self._case_artifacts.setdefault(submission_id,
                                        {}).setdefault(task_no,
                                                       {})[case_no] = data

    def _upload_case(self, submission_id: str, task_no: int, case_no: int,
                     payload: bytes) -> bool:
        url = f"{self.backend_url}/submission/{submission_id}/artifact/upload/case"
        params = {"task": task_no, "case": case_no, "token": self.token}
        for attempt in range(3):
            try:
                resp = requests.put(
                    url,
                    params=params,
                    data=payload,
                    timeout=30,
                    headers={"Content-Type": "application/zip"},
                )
                if resp.ok:
                    return True
                self._logger.warning(
                    "upload case artifact failed [id=%s task=%s case=%s status=%s resp=%s]",
                    submission_id,
                    task_no,
                    case_no,
                    resp.status_code,
                    resp.text,
                )
            except Exception as exc:
                self._logger.warning(
                    "upload case artifact error [id=%s task=%s case=%s attempt=%s]: %s",
                    submission_id,
                    task_no,
                    case_no,
                    attempt,
                    exc,
                )
            time.sleep(1)
        return False

    def _upload_binary(self, submission_id: str, payload: bytes) -> bool:
        url = f"{self.backend_url}/submission/{submission_id}/artifact/upload/binary"
        params = {"token": self.token}
        for attempt in range(3):
            try:
                resp = requests.put(
                    url,
                    params=params,
                    data=payload,
                    timeout=30,
                    headers={"Content-Type": "application/octet-stream"},
                )
                if resp.ok:
                    return True
                self._logger.warning(
                    "upload binary failed [id=%s status=%s resp=%s]",
                    submission_id,
                    resp.status_code,
                    resp.text,
                )
            except Exception as exc:
                self._logger.warning(
                    "upload binary error [id=%s attempt=%s]: %s",
                    submission_id,
                    attempt,
                    exc,
                )
            time.sleep(1)
        return False

    @staticmethod
    def _case_key(task_no: int, case_no: int) -> str:
        return f"{task_no:02d}{case_no:02d}"
