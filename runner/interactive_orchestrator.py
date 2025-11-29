"""
Interactive orchestrator run *inside* the sandbox container.

It launches two sandbox processes (student / teacher) and wires their
stdin/stdout together via FIFO (or /dev/fd fallback). A Check_Result file
written by the teacher determines AC/WA when both sides exit normally.
Any sandbox error (CE/RE/TLE/MLE) from either side overrides Check_Result.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import shutil
import time
import tempfile
import math
import logging
from pathlib import Path
from typing import List, Tuple

LANG_IDS = {"c11": 0, "cpp17": 1, "python3": 2}
CONFIG_PATH = Path("/app/.config/interactive.json")


def load_config():
    default = {
        "outputLimitBytes": 64 * 1024 * 1024,
        "maxTeacherNewFiles": 500,
        "teacherUid": 1450,
        "studentUid": 1451,
        "sandboxGid": 1450,
        "studentAllowRead": False,
        "studentAllowWrite": False,
    }
    try:
        data = json.loads(CONFIG_PATH.read_text())
        default.update({k: v for k, v in data.items() if k in default})
    except Exception:
        pass
    return default


class OrchestratorError(RuntimeError):
    pass


def _read_result(path: Path):
    """Parse sandbox_interactive result file."""
    raw = ""
    if not path.exists():
        return {
            "status": "CE",
            "exit_code": -1,
            "time_ms": -1,
            "mem_kb": -1,
            "message": "result file missing",
            "raw": raw,
        }
    lines = path.read_text().splitlines()
    raw = "\n".join(lines)
    if not lines:
        return {
            "status": "CE",
            "exit_code": -1,
            "time_ms": -1,
            "mem_kb": -1,
            "message": "empty result file",
            "raw": raw,
        }
    status_line = lines[0].strip()
    exit_info = lines[1].strip() if len(lines) > 1 else ""
    try:
        time_ms = int(lines[2]) if len(lines) > 2 else -1
    except ValueError:
        time_ms = -1
    try:
        mem_kb = int(lines[3]) if len(lines) > 3 else -1
    except ValueError:
        mem_kb = -1
    exit_code = -1
    if "WEXITSTATUS() = " in exit_info:
        try:
            exit_code = int(exit_info.split("WEXITSTATUS() = ")[1].split()[0])
        except Exception:
            exit_code = -1
    status_map = {
        "Exited Normally": "AC",
        "TLE": "TLE",
        "MLE": "MLE",
        "RE": "RE",
        "OLE": "OLE",
    }
    status = status_map.get(status_line, "CE")
    return {
        "status": status,
        "exit_code": exit_code,
        "time_ms": time_ms,
        "mem_kb": mem_kb,
        "message": exit_info,
        "raw": raw,
    }


def _parse_check_result(path: Path):
    if not path.exists():
        return None, "Check_Result not found"
    status = None
    message = ""
    for line in path.read_text().splitlines():
        if line.startswith("STATUS:"):
            status = line.split(":", 1)[1].strip()
        elif line.startswith("MESSAGE:"):
            message = line.split(":", 1)[1].strip()
    if status not in ("AC", "WA"):
        return None, "Invalid Check_Result STATUS"
    return status, message


def _ensure_exec(target: Path, candidates: List[Path]):
    """Ensure an executable `target` exists by linking/copying from candidates."""
    if target.exists():
        return target
    for cand in candidates:
        if not cand or not cand.exists():
            continue
        try:
            os.link(cand, target)
        except Exception:
            try:
                shutil.copy(cand, target)
            except Exception:
                continue
        break
    if target.exists():
        try:
            os.chmod(target, target.stat().st_mode | 0o111)
        except Exception:
            pass
    return target


def _dir_file_count(path: Path) -> int:
    count = 0
    for p in path.rglob("*"):
        if p.is_file():
            count += 1
    return count


def _setup_secure_permissions(
    teacher_dir: Path,
    student_dir: Path,
    teacher_uid: int,
    student_uid: int,
    sandbox_gid: int,
    student_allow_read: bool,
    student_allow_write: bool,
):
    """Ensure teacher dir owned by teacher UID (unreadable to student), student dir owned by student UID."""
    logger = logging.getLogger(__name__)
    try:
        for root, dirs, files in os.walk(teacher_dir):
            os.chown(root, teacher_uid, sandbox_gid)
            os.chmod(root, 0o701)
            for f in files:
                fp = os.path.join(root, f)
                os.chown(fp, teacher_uid, sandbox_gid)
                mode = 0o700 if os.access(fp, os.X_OK) else 0o600
                os.chmod(fp, mode)
    except Exception as exc:
        raise OrchestratorError(f"failed to secure teacher dir: {exc}") from exc

    try:
        dir_mode = 0o751
        for root, dirs, files in os.walk(student_dir):
            os.chown(root, student_uid, sandbox_gid)
            os.chmod(root, dir_mode)
            for f in files:
                fp = os.path.join(root, f)
                os.chown(fp, student_uid, sandbox_gid)
                is_exec = os.access(fp, os.X_OK)
                if student_allow_write:
                    mode = 0o755 if is_exec else 0o644
                else:
                    mode = 0o555 if is_exec else 0o444
                if not student_allow_read:
                    mode = 0o511 if is_exec else 0o440
                os.chmod(fp, mode)
    except Exception as exc:
        raise OrchestratorError(f"failed to secure student dir: {exc}") from exc


def _setup_pipes(tmpdir: Path, mode: str):
    if mode == "devfd":
        s2t_r, s2t_w = os.pipe()
        t2s_r, t2s_w = os.pipe()
        for fd in (s2t_r, s2t_w, t2s_r, t2s_w):
            os.set_inheritable(fd, True)
        return {
            "mode": "devfd",
            "student": {
                "stdin": f"/dev/fd/{t2s_r}",
                "stdout": f"/dev/fd/{s2t_w}",
            },
            "teacher": {
                "stdin": f"/dev/fd/{s2t_r}",
                "stdout": f"/dev/fd/{t2s_w}",
            },
            "keep_fds": [s2t_r, s2t_w, t2s_r, t2s_w],
            "kick_student": s2t_w,
            "kick_teacher": t2s_w,
            "kick_bytes": [s2t_w, t2s_w],
        }
    # FIFO mode
    s2t = tmpdir / "s2t.fifo"
    t2s = tmpdir / "t2s.fifo"
    s2t_err = tmpdir / "s2t.err"
    t2s_err = tmpdir / "t2s.err"
    os.mkfifo(s2t)
    os.mkfifo(t2s)
    holder = [
        os.open(s2t, os.O_RDWR | os.O_NONBLOCK),
        os.open(t2s, os.O_RDWR | os.O_NONBLOCK),
    ]
    return {
        "mode": "fifo",
        "student": {
            "stdin": str(t2s),
            "stdout": str(s2t),
            "stderr": str(s2t_err),
        },
        "teacher": {
            "stdin": str(s2t),
            "stdout": str(t2s),
            "stderr": str(t2s_err),
        },
        "keep_fds": [],
        "kick_student": holder[0],
        "kick_teacher": holder[1],
        "holder": holder,
        "kick_bytes": holder,
    }


def orchestrate(args: argparse.Namespace):
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    teacher_dir = Path(args.teacher_dir) if args.teacher_dir else workdir / "teacher"
    student_dir = Path(args.student_dir) if args.student_dir else workdir / "src"
    teacher_lang = args.teacher_lang
    student_lang = args.student_lang
    if teacher_lang not in LANG_IDS or student_lang not in LANG_IDS:
        raise OrchestratorError("unsupported language")

    cfg = load_config()
    output_limit = int(cfg.get("outputLimitBytes", 64 * 1024 * 1024))
    max_new_files = int(cfg.get("maxTeacherNewFiles", 500))
    teacher_uid = int(cfg.get("teacherUid", 1450))
    student_uid = int(cfg.get("studentUid", 1451))
    sandbox_gid = int(cfg.get("sandboxGid", 1450))
    student_allow_read = bool(cfg.get("studentAllowRead", False))
    student_allow_write = bool(cfg.get("studentAllowWrite", False))

    # FIFO 需要學生端開啟寫入 FIFO，若禁用寫入則改用 devfd 以避免卡死
    if args.pipe_mode == "fifo" and not student_allow_write:
        args.pipe_mode = "devfd"

    _setup_secure_permissions(
        teacher_dir,
        student_dir,
        teacher_uid,
        student_uid,
        sandbox_gid,
        student_allow_read,
        student_allow_write,
    )
    teacher_files_before = _dir_file_count(teacher_dir)

    # Ensure teacher binary/script ready
    teacher_main = teacher_dir / (
        "Teacher_main" if teacher_lang != "python3" else "main.py"
    )
    teacher_source = teacher_dir / (
        "main.py" if teacher_lang == "python3" else "main.c"
    )
    if teacher_lang != "python3" and not teacher_main.exists():
        raise OrchestratorError("teacher binary missing")
    if teacher_lang == "python3" and not teacher_source.exists():
        raise OrchestratorError("teacher script missing")
    if teacher_lang != "python3":
        _ensure_exec(teacher_dir / "main", [teacher_main, teacher_dir / "a.out"])
    else:
        _ensure_exec(teacher_dir / "main.py", [teacher_source])

    student_entry = student_dir / ("main.py" if student_lang == "python3" else "main")
    if student_lang != "python3":
        _ensure_exec(student_entry, [student_dir / "a.out", student_entry])
        _ensure_exec(student_dir / "a.out", [student_entry])
    if not student_entry.exists():
        raise OrchestratorError("student entry not found")

    tmpdir = Path(tempfile.mkdtemp(prefix=".interactive-", dir=workdir))
    try:
        os.chown(tmpdir, teacher_uid, sandbox_gid)
    except Exception as exc:
        raise OrchestratorError(f"chown tmpdir failed: {exc}") from exc
    try:
        os.chmod(tmpdir, 0o700)
    except Exception as exc:
        raise OrchestratorError(f"chmod tmpdir failed: {exc}") from exc
    pipe_bundle = _setup_pipes(tmpdir, args.pipe_mode)
    pipe_mode = pipe_bundle["mode"]
    keep_fds = pipe_bundle["keep_fds"]
    kick_student_fd = pipe_bundle.get("kick_student")
    kick_teacher_fd = pipe_bundle.get("kick_teacher")
    holder_fds = pipe_bundle.get("holder", [])
    kick_bytes = pipe_bundle.get("kick_bytes", [])
    kick_dup = None
    if pipe_mode == "fifo":
        fifo_paths = [
            Path(pipe_bundle["student"]["stdin"]),
            Path(pipe_bundle["student"]["stdout"]),
            Path(pipe_bundle["teacher"]["stdin"]),
            Path(pipe_bundle["teacher"]["stdout"]),
        ]
        for fp in fifo_paths:
            try:
                os.chown(fp, teacher_uid, sandbox_gid)
                os.chmod(fp, 0o660)
            except Exception:
                pass

    stu_res = tmpdir / "student.result"
    # sandbox_interactive argv layout:
    # [lang_id, allow_net(0), stdin, stdout, stderr, time_ms, mem_kb, allow_write(1/0), output_limit, proc_limit, result_path]
    student_cmd = [
        "sandbox_interactive",
        str(LANG_IDS[student_lang]),
        "0",  # allow_net
        pipe_bundle["student"]["stdin"],
        pipe_bundle["student"]["stdout"],
        pipe_bundle["student"].get("stderr", str(tmpdir / "student.err")),
        str(args.time_limit),
        str(args.mem_limit),
        "1",  # allow_write flag; env controls actual seccomp
        str(output_limit),
        "10",  # process limit
        str(stu_res),
    ]
    commands = {
        "student": student_cmd,
        "teacher": [
            "sandbox_interactive",
            str(LANG_IDS[teacher_lang]),
            "0",
            pipe_bundle["teacher"]["stdin"],
            pipe_bundle["teacher"]["stdout"],
            pipe_bundle["teacher"].get("stderr", str(tmpdir / "teacher.err")),
            str(args.time_limit),
            str(args.mem_limit),
            "1",  # teacher allowed to write
            str(output_limit),
            "10",
            str(tmpdir / "teacher.result"),
        ],
    }
    env_student = os.environ.copy()
    env_teacher = os.environ.copy()
    # ensure writeable cwd
    env_student["PWD"] = str(student_dir)
    env_teacher["PWD"] = str(teacher_dir)
    env_student["SANDBOX_UID"] = str(student_uid)
    env_student["SANDBOX_GID"] = str(sandbox_gid)
    if student_allow_write:
        env_student["SANDBOX_ALLOW_WRITE"] = "1"
    else:
        env_student.pop("SANDBOX_ALLOW_WRITE", None)
    if student_allow_read:
        env_student["SANDBOX_ALLOW_READ"] = "1"
    else:
        env_student.pop("SANDBOX_ALLOW_READ", None)
    env_teacher["SANDBOX_UID"] = str(teacher_uid)
    env_teacher["SANDBOX_GID"] = str(sandbox_gid)
    # only teacher可寫檔
    env_teacher["SANDBOX_ALLOW_WRITE"] = "1"
    case_local = None
    if args.case_path:
        env_teacher["CASE_PATH"] = args.case_path
        src_case = Path(args.case_path)
        if src_case.exists():
            case_local = teacher_dir / "testcase.in"
            try:
                if case_local.exists():
                    case_local.unlink()
                case_local.write_bytes(src_case.read_bytes())
                os.chmod(case_local, 0o600)
                try:
                    os.chown(case_local, teacher_uid, sandbox_gid)
                except Exception:
                    pass
            except Exception:
                case_local = None
    start_time = time.time()
    procs = {}
    try:
        # start processes (teacher_first toggles order)
        deadline = start_time + (args.time_limit / 1000.0) + 2.0

        def start_teacher():
            procs["teacher"] = subprocess.Popen(
                commands["teacher"],
                cwd=teacher_dir,
                env=env_teacher,
                pass_fds=keep_fds,
            )

        def start_student():
            procs["student"] = subprocess.Popen(
                commands["student"],
                cwd=Path("/src"),
                env=env_student,
                pass_fds=keep_fds,
            )

        if args.teacher_first:
            start_teacher()
            time.sleep(0.05)
            start_student()
        else:
            start_student()
            time.sleep(0.05)
            start_teacher()

        # holders keep FIFO from blocking open; close after both sides are up to allow EOF propagation
        # keep FIFO fds open during spawn to avoid blocking open; close after both sides start
        for fd in holder_fds:
            try:
                os.close(fd)
            except Exception as exc:
                logging.getLogger(__name__).warning("close holder fd failed: %s", exc)
        holder_fds = []
        if kick_student_fd is not None:
            try:
                kick_dup = os.dup(kick_student_fd)
            except Exception as exc:
                logging.getLogger(__name__).warning("dup kick fd failed: %s", exc)
                kick_dup = None
        for fd in keep_fds:
            try:
                os.close(fd)
            except Exception as exc:
                logging.getLogger(__name__).warning("close keep fd failed: %s", exc)
        keep_fds = []

        while time.time() < deadline:
            all_done = True
            for proc in procs.values():
                if proc.poll() is None:
                    all_done = False
            # If student already exited while teacher still waits on FIFO, send newline to unblock.
            if (
                kick_dup is not None
                and "student" in procs
                and procs["student"].poll() is not None
                and procs.get("teacher")
                and procs["teacher"].poll() is None
            ):
                try:
                    os.write(kick_dup, b"\n")
                except Exception as exc:
                    logging.getLogger(__name__).warning("kick write failed: %s", exc)
                try:
                    os.close(kick_dup)
                except Exception as exc:
                    logging.getLogger(__name__).warning("kick close failed: %s", exc)
                kick_dup = None
            if all_done:
                break
            time.sleep(0.05)
        for proc in procs.values():
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
        # ensure waits to collect exit codes
        for proc in procs.values():
            try:
                proc.wait(timeout=0.5)
            except Exception:
                pass
    except Exception as exc:
        for p in procs.values():
            try:
                p.kill()
            except Exception:
                pass
        raise OrchestratorError(f"execution failed: {exc}") from exc
    finally:
        for fd in holder_fds:
            try:
                os.close(fd)
            except Exception:
                pass
        if case_local and case_local.exists():
            try:
                case_local.unlink()
            except Exception:
                try:
                    os.chmod(case_local, 0o600)
                except Exception:
                    pass

    teacher_result = _read_result(tmpdir / "teacher.result")
    student_result = _read_result(stu_res)
    teacher_status = teacher_result["status"]
    student_status = student_result["status"]
    teacher_err = ""
    teacher_err_path = Path(
        pipe_bundle["teacher"].get("stderr", str(tmpdir / "teacher.err"))
    )
    if teacher_err_path.exists():
        teacher_err = teacher_err_path.read_text()
    student_err = ""
    student_err_path = Path(
        pipe_bundle["student"].get("stderr", str(tmpdir / "student.err"))
    )
    if student_err_path.exists():
        student_err = student_err_path.read_text()
    final_status = None
    message = ""
    if student_status != "AC":
        final_status = student_status
        message = student_result["message"] or student_err or student_result["raw"]
    elif teacher_status != "AC":
        final_status = teacher_status
        message = teacher_result["message"] or teacher_err or teacher_result["raw"]
    else:
        check_status, msg = _parse_check_result(teacher_dir / "Check_Result")
        if check_status is None:
            final_status = "CE"
            message = msg
        else:
            final_status = check_status
            message = msg

    duration_ms = int((time.time() - start_time) * 1000)
    mem_usage = max(teacher_result.get("mem_kb", -1), student_result.get("mem_kb", -1))
    if mem_usage < 0:
        mem_usage = -1
    teacher_new_files = _dir_file_count(teacher_dir) - teacher_files_before
    if final_status == "AC" and teacher_new_files > max_new_files:
        final_status = "CE"
        message = f"teacher created too many files ({teacher_new_files})"
    if not os.getenv("KEEP_INTERACTIVE_TMP"):
        try:
            shutil.rmtree(tmpdir)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "failed to remove tmpdir %s: %s", tmpdir, exc
            )
    teacher_exit = procs.get("teacher").returncode if "teacher" in procs else -1
    student_exit = procs.get("student").returncode if "student" in procs else -1
    return {
        "Status": final_status,
        "Stdout": "",
        "Stderr": message,
        "Duration": duration_ms,
        "MemUsage": mem_usage,
        "DockerExitCode": 0,
        "pipeMode": pipe_mode,
        "teacherStderr": teacher_err,
        "teacherExit": teacher_exit,
        "studentStderr": student_err,
        "studentExit": student_exit,
        "studentResult": student_result["raw"],
        "teacherResult": teacher_result["raw"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--teacher-dir")
    parser.add_argument("--student-dir")
    parser.add_argument("--student-lang", required=True)
    parser.add_argument("--teacher-lang", required=True)
    parser.add_argument("--teacher-first", action="store_true")
    parser.add_argument("--time-limit", type=int, required=True)
    parser.add_argument("--mem-limit", type=int, required=True)
    parser.add_argument("--case-path")
    parser.add_argument(
        "--pipe-mode",
        choices=("auto", "fifo", "devfd"),
        default="auto",
        help="Preferred pipe mode; auto tries fifo then devfd fallback.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    result = {}
    pipe_mode = args.pipe_mode
    try:
        if pipe_mode == "auto":
            last_exc = None
            for mode in ("devfd", "fifo"):
                try:
                    args.pipe_mode = mode
                    result = orchestrate(args)
                    break
                except Exception as exc:
                    last_exc = exc
            else:
                raise OrchestratorError(
                    f"failed to establish pipe (devfd/fifo); last error: {last_exc}"
                )
        else:
            result = orchestrate(args)
    except Exception as exc:
        result = {
            "Status": "CE",
            "Stdout": "",
            "Stderr": f"interactive orchestrator failed: {exc}",
            "Duration": -1,
            "MemUsage": -1,
            "DockerExitCode": 1,
            "pipeMode": args.pipe_mode,
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
