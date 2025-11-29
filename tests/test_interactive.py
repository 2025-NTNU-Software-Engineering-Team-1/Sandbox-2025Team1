import os
import json
import shutil
import subprocess
from pathlib import Path

import docker
import pytest

from dispatcher.build_strategy import BuildStrategyError, _prepare_teacher_artifacts
from dispatcher.constant import Language
from dispatcher.meta import Meta, Task, SubmissionMode, ExecutionMode, BuildStrategy
from runner.interactive_runner import InteractiveRunner

SUBMISSION_CFG = json.loads(Path(".config/submission.json").read_text())
WORKDIR = Path(SUBMISSION_CFG["working_dir"]).resolve()
INTERACTIVE_IMAGE = SUBMISSION_CFG.get("interactive_image", "noj-interactive")
INTERACTIVE_CFG_PATH = Path(".config/interactive.json")


def _has_image(name: str) -> bool:
    try:
        cli = docker.APIClient(base_url=SUBMISSION_CFG.get(
            "docker_url", "unix://var/run/docker.sock"))
        for img in cli.images():
            for tag in img.get("RepoTags", []) or []:
                if tag and tag.split(":")[0] == name:
                    return True
        return False
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_image(INTERACTIVE_IMAGE),
                                reason="interactive image not available")


def _compile_c(src: Path, output: Path):
    cmd = ["gcc", "-std=c11", "-O2", "-w", str(src), "-o", str(output)]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"compile failed: {res.stdout.decode()}\n{res.stderr.decode()}")
    output.chmod(0o755)


def _prepare_submission(sub_id: str,
                        teacher_code: str,
                        student_code: str,
                        teacher_lang: str = "c11",
                        student_lang: str = "c11"):
    WORKDIR.mkdir(parents=True, exist_ok=True)
    root = WORKDIR / sub_id
    if root.exists():
        # clean with privileged container to handle sandbox-owned paths
        subprocess.run([
            "docker", "run", "--rm", "-v", f"{root}:/data", "alpine", "sh",
            "-c", "rm -rf /data/*"
        ],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)

        def _onerror(func, path, excinfo):
            try:
                os.chmod(path, 0o777)
            except Exception:
                pass
            try:
                os.remove(path)
            except Exception:
                try:
                    shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass

        shutil.rmtree(root, onerror=_onerror)
    (root / "teacher").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "testcase").mkdir()
    (root / "testcase" / "0000.in").write_text("")

    if teacher_lang == "python3":
        t_src = root / "teacher" / "main.py"
        t_src.write_text(teacher_code)
    else:
        t_src = root / "teacher" / "main.c"
        t_src.write_text(teacher_code)
        t_bin = root / "teacher" / "Teacher_main"
        _compile_c(t_src, t_bin)
        t_main = root / "teacher" / "main"
        if t_main.exists():
            t_main.unlink()
        os.link(t_bin, t_main)
        t_main.chmod(0o755)

    if student_lang == "python3":
        s_src = root / "src" / "main.py"
        s_src.write_text(student_code)
    else:
        s_src = root / "src" / "main.c"
        s_src.write_text(student_code)
        s_bin = root / "src" / "main"
        _compile_c(s_src, s_bin)
    return root


def _run(sub_id: str,
         teacher_first: bool = True,
         pipe_mode: str = "devfd",
         teacher_lang: str = "c11",
         student_lang: str = "c11",
         case_name: str = "0000.in"):
    case_path = WORKDIR / sub_id / "testcase" / case_name
    runner = InteractiveRunner(
        submission_id=sub_id,
        time_limit=2000,
        mem_limit=65536,
        case_in_path=str(case_path),
        teacher_first=teacher_first,
        lang_key=student_lang,
        teacher_lang_key=teacher_lang,
        pipe_mode=pipe_mode,
    )
    return runner.run()


@pytest.fixture
def clean_submission():
    created = []
    yield created
    for sub_id in created:
        path = WORKDIR / sub_id
        if path.exists():
            if os.getenv("KEEP_INTERACTIVE_SUBMISSIONS"):
                continue
            # use docker root to clean even if owned by sandbox uid
            subprocess.run([
                "docker", "run", "--rm", "-v", f"{path}:/data", "alpine", "sh",
                "-c", "rm -rf /data/*"
            ],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
            shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def interactive_config_guard():
    original = json.loads(INTERACTIVE_CFG_PATH.read_text())
    yield
    INTERACTIVE_CFG_PATH.write_text(json.dumps(original))


def test_interactive_ac(clean_submission):
    sub_id = "it-ac"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[128]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; if(strncmp(buf,"pong",4)==0) fprintf(f,"STATUS: AC\nMESSAGE: ok\n"); else fprintf(f,"STATUS: WA\nMESSAGE: bad\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){char buf[128]; if(fgets(buf,sizeof(buf),stdin)){printf("pong\n"); fflush(stdout);} return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "AC"
    assert res["teacherExit"] == 0 and res["studentExit"] == 0
    assert res["pipeMode"] in ("fifo", "devfd")


def test_interactive_wa(clean_submission):
    sub_id = "it-wa"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[64]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; if(strncmp(buf,"pong",4)==0) fprintf(f,"STATUS: AC\nMESSAGE: ok\n"); else fprintf(f,"STATUS: WA\nMESSAGE: wrong\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){puts("oops"); fflush(stdout); return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "WA"
    assert "wrong" in res["Stderr"]


def test_interactive_missing_check_result(clean_submission):
    sub_id = "it-missing-cr"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){printf("ping\n"); fflush(stdout); return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){char buf[16]; fgets(buf,sizeof(buf),stdin); printf("pong\n"); fflush(stdout); return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "CE"
    assert "Check_Result" in res["Stderr"]


def test_interactive_student_first(clean_submission):
    sub_id = "it-stu-first"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[128]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; if(strncmp(buf,"pong",4)==0) fprintf(f,"STATUS: AC\nMESSAGE: ok\n"); else fprintf(f,"STATUS: WA\nMESSAGE: bad\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){printf("pong\n"); fflush(stdout); return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id, teacher_first=False)
    assert res["Status"] == "AC"


def test_interactive_devfd(clean_submission):
    sub_id = "it-devfd"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[16]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: AC\nMESSAGE: devfd\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){char buf[16]; if(fgets(buf,sizeof(buf),stdin)) {printf("pong\n"); fflush(stdout);} return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id, pipe_mode="devfd")
    assert res["Status"] == "AC"
    assert res["pipeMode"] == "devfd"


def test_fifo_forced_devfd_when_student_write_disabled(
        clean_submission, interactive_config_guard):
    cfg = json.loads(INTERACTIVE_CFG_PATH.read_text())
    cfg["studentAllowWrite"] = False
    INTERACTIVE_CFG_PATH.write_text(json.dumps(cfg))
    sub_id = "it-fifo-fallback"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[16]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: AC\nMESSAGE: ok\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){char buf[16]; if(fgets(buf,sizeof(buf),stdin)) {printf("pong\n"); fflush(stdout);} return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id, pipe_mode="fifo")
    assert res["Status"] == "AC"
    assert res["pipeMode"] == "devfd"  # auto fallback


def test_fifo_allowed_when_student_write_enabled(clean_submission,
                                                 interactive_config_guard):
    cfg = json.loads(INTERACTIVE_CFG_PATH.read_text())
    cfg["studentAllowWrite"] = True
    INTERACTIVE_CFG_PATH.write_text(json.dumps(cfg))
    sub_id = "it-fifo-allowed"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[32]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: AC\nMESSAGE: fifo\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){char buf[32]; if(fgets(buf,sizeof(buf),stdin)) {printf("pong\n"); fflush(stdout);} return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id, pipe_mode="fifo")
    # FIFO 在學生可寫時預期可用，但某些環境仍可能退回 devfd；至少不應因 pipe 失敗而 CE
    assert res["Status"] in ("AC", "TLE", "WA", "RE")
    assert res["pipeMode"] in ("fifo", "devfd")


def test_interactive_student_write_denied(clean_submission):
    sub_id = "it-stu-write"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[16]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: WA\nMESSAGE: should_not_reach\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){FILE*f=fopen("hack.txt","w"); if(f){fprintf(f,"x"); fclose(f);} return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] in ("RE", "CE", "WA")


def test_interactive_teacher_can_write(clean_submission):
    sub_id = "it-teacher-write"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){FILE*f=fopen("tmp.txt","w"); if(f){fprintf(f,"ok"); fclose(f);} FILE*c=fopen("Check_Result","w"); if(!c)return 1; fprintf(c,"STATUS: AC\nMESSAGE: write_ok\n"); fclose(c); return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){printf("pong\n"); fflush(stdout); return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "AC"
    tmpfile = WORKDIR / sub_id / "teacher" / "tmp.txt"
    assert tmpfile.exists()


def test_tmpdir_permissions(clean_submission, monkeypatch):
    # tmpdir 位於容器 /workspace，未掛載到 host，無法直接檢查，測試略過
    pytest.skip("tmpdir is container-local; skip host-side permission check")


def test_interactive_python_teacher(clean_submission):
    sub_id = "it-py-teacher"
    clean_submission.append(sub_id)
    teacher = r'''
import os
def main():
    data = ""
    if os.path.exists("testcase.in"):
        data = open("testcase.in").read()
    with open("Check_Result","w") as f:
        f.write("STATUS: AC\nMESSAGE: py %s\n" % data.strip())
if __name__ == "__main__":
    main()
'''
    student = r'''
    #include <stdio.h>
    int main(){printf("pong\n"); fflush(stdout); return 0;}
    '''
    _prepare_submission(sub_id, teacher, student, teacher_lang="python3")
    # put content to testcase
    (WORKDIR / sub_id / "testcase" / "0000.in").write_text("hello")
    res = _run(sub_id, teacher_lang="python3")
    assert res["Status"] == "AC"


def test_interactive_invalid_check_status(clean_submission):
    sub_id = "it-bad-cr"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: XX\nMESSAGE: bad\n"); fclose(f); return 0;}
    '''
    student = r'''
    #include <stdio.h>
    int main(){return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "CE"
    assert "Invalid Check_Result" in res["Stderr"]


def test_interactive_student_tle(clean_submission):
    sub_id = "it-stu-tle"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){printf("ping\n"); fflush(stdout); FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: WA\nMESSAGE: timeout\n"); fclose(f); return 0;}
    '''
    student = r'''
    int main(){while(1){} return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "TLE"


def test_interactive_teacher_tle(clean_submission):
    sub_id = "it-teacher-tle"
    clean_submission.append(sub_id)
    teacher = r'''
    int main(){while(1){} return 0;}
    '''
    student = r'''
    int main(){return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "TLE"


def test_interactive_testcase_cleanup(clean_submission):
    sub_id = "it-case-clean"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: AC\nMESSAGE: ok\n"); fclose(f); return 0;}
    '''
    student = r'''
    int main(){return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    (WORKDIR / sub_id / "testcase" / "0000.in").write_text("abc")
    res = _run(sub_id)
    assert res["Status"] == "AC"
    assert not (WORKDIR / sub_id / "teacher" / "testcase.in").exists()


def test_interactive_python_student_write_denied(clean_submission):
    sub_id = "it-py-stu-write"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){FILE*f=fopen("Check_Result","w"); if(!f)return 1; fprintf(f,"STATUS: WA\nMESSAGE: no\n"); fclose(f); return 0;}
    '''
    student = r'''
import os
open("hack.txt","w").write("bad")
    '''
    _prepare_submission(sub_id, teacher, student, student_lang="python3")
    res = _run(sub_id, student_lang="python3")
    assert res["Status"] in ("RE", "CE", "WA")


def test_teacher_compile_fail_build_strategy(tmp_path):
    teacher_dir = tmp_path / "teacher"
    teacher_dir.mkdir(parents=True)
    bad = teacher_dir / "main.c"
    bad.write_text("int main(){ oops }\n")
    meta = Meta(
        language=Language.C,
        tasks=[Task(taskScore=100, memoryLimit=1, timeLimit=1, caseCount=1)],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.INTERACTIVE,
        buildStrategy=BuildStrategy.MAKE_INTERACTIVE,
        assetPaths={})
    with pytest.raises(BuildStrategyError):
        _prepare_teacher_artifacts(problem_id=1,
                                   meta=meta,
                                   submission_dir=tmp_path)


def test_prepare_teacher_file_respects_teacher_lang(tmp_path, monkeypatch):
    import dispatcher.build_strategy as bs

    def fake_fetch(pid, asset):
        return b'print("ok")'

    monkeypatch.setattr(bs, "fetch_problem_asset", fake_fetch)
    meta = Meta(
        language=Language.C,
        tasks=[Task(taskScore=100, memoryLimit=1, timeLimit=1, caseCount=1)],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.INTERACTIVE,
        buildStrategy=BuildStrategy.MAKE_INTERACTIVE,
        assetPaths={
            "teacherLang": "py",
            "teacher_file": "ignored"
        })
    bs.prepare_interactive_teacher_artifacts(problem_id=1,
                                             meta=meta,
                                             submission_dir=tmp_path)
    assert (tmp_path / "teacher" / "main.py").exists()


def test_prepare_teacher_file_missing_teacher_lang(tmp_path, monkeypatch):
    import dispatcher.build_strategy as bs

    def fake_fetch(pid, asset):
        return b'int main(){return 0;}'

    monkeypatch.setattr(bs, "fetch_problem_asset", fake_fetch)
    meta = Meta(
        language=Language.C,
        tasks=[Task(taskScore=100, memoryLimit=1, timeLimit=1, caseCount=1)],
        submissionMode=SubmissionMode.CODE,
        executionMode=ExecutionMode.INTERACTIVE,
        buildStrategy=BuildStrategy.MAKE_INTERACTIVE,
        assetPaths={"teacher_file": "ignored"})
    with pytest.raises(BuildStrategyError):
        bs.prepare_interactive_teacher_artifacts(problem_id=1,
                                                 meta=meta,
                                                 submission_dir=tmp_path)


def test_interactive_teacher_disk_growth_limit(clean_submission):
    sub_id = "it-teacher-ole"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){FILE*f=fopen("big.bin","w"); if(!f)return 1; for(long i=0;i<120000000;i++) fputc('A',f); fclose(f); FILE*c=fopen("Check_Result","w"); if(!c)return 1; fprintf(c,"STATUS: AC\\nMESSAGE: big\\n"); fclose(c); return 0;}
    '''
    student = r'''
    int main(){return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    # RLIMIT_FSIZE should trigger OLE/RE
    assert res["Status"] in ("OLE", "RE", "CE", "TLE")


def test_interactive_teacher_too_many_files(clean_submission):
    sub_id = "it-teacher-files"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    int main(){ for(int i=0;i<600;i++){ char name[32]; sprintf(name,"f%03d.txt",i); FILE*f=fopen(name,"w"); if(f){fputs("x",f); fclose(f);} } FILE*c=fopen("Check_Result","w"); if(!c)return 1; fprintf(c,"STATUS: AC\nMESSAGE: ok\n"); fclose(c); return 0;}
    '''
    student = r'''
    int main(){return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id)
    assert res["Status"] == "CE"
    assert "too many files" in res["Stderr"]


def test_interactive_student_cannot_read_teacher(clean_submission):
    sub_id = "it-hide-teacher"
    clean_submission.append(sub_id)
    teacher = r'''
    #include <stdio.h>
    #include <string.h>
    int main(){printf("ping\n"); fflush(stdout); char buf[64]; if(fgets(buf,sizeof(buf),stdin)){FILE*f=fopen("Check_Result","w"); if(!f)return 1; if(strncmp(buf,"leak",4)==0) fprintf(f,"STATUS: WA\nMESSAGE: leak\n"); else fprintf(f,"STATUS: AC\nMESSAGE: ok\n"); fclose(f);} return 0;}
    '''
    student = r'''
    #include <stdio.h>
    #include <unistd.h>
    int main(){FILE*f=fopen("/teacher/main.c","r"); if(f){printf("leak\\n"); fclose(f);} else {printf("pong\\n");} fflush(stdout); return 0;}
    '''
    _prepare_submission(sub_id, teacher, student)
    res = _run(sub_id, teacher_first=False)
    assert res["Status"] == "AC"
    assert "ok" in res["Stderr"]
