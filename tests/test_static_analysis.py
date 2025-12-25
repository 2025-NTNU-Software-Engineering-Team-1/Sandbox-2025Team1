import json
from pathlib import Path
from dispatcher.static_analysis import StaticAnalyzer, _collect_sources_from_makefile
from dispatcher.constant import Language

BASE = Path(__file__).resolve().parent


def test_python_static_analysis_violations():
    test_file_path = BASE / "static_analysis" / "test_file"
    rules_path = test_file_path / "rules.json"

    if not rules_path.exists():
        return

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    # prepare common layout
    common = test_file_path / "src" / "common"
    common.mkdir(parents=True, exist_ok=True)
    for fname in ("main.py", ):
        src = test_file_path / fname
        if src.exists():
            (common / fname).write_bytes(src.read_bytes())

    analyzer = StaticAnalyzer()

    result = analyzer.analyze(
        submission_id=str(test_file_path),
        language=Language.PY,
        rules=rules,
    )


def test_c_static_analysis_violations():
    test_file_path = BASE / "static_analysis" / "test_file"
    rules_path = test_file_path / "rules.json"

    if not rules_path.exists():
        return

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    common = test_file_path / "src" / "common"
    common.mkdir(parents=True, exist_ok=True)
    for fname in ("_main.c", "main.cpp"):
        src = test_file_path / fname
        if src.exists():
            (common / Path(fname).name).write_bytes(src.read_bytes())

    analyzer = StaticAnalyzer()
    result = analyzer.analyze(
        submission_id=str(test_file_path),
        language=Language.C,
        rules=rules,
    )


def test_python_syntax_blacklist_custom(tmp_path):
    common = tmp_path / "src" / "common"
    common.mkdir(parents=True, exist_ok=True)
    src = common / "main.py"
    src.write_text("def f(x):\n"
                   "    if x > 0:\n"
                   "        return x\n"
                   "    return -x\n")
    rules = {
        "model": "black",
        "syntax": ["return", "if"],
    }
    res = StaticAnalyzer().analyze(
        submission_id=str(tmp_path),
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "return" in res.message
    assert "if" in res.message


def test_python_syntax_whitelist_custom(tmp_path):
    common = tmp_path / "src" / "common"
    common.mkdir(parents=True, exist_ok=True)
    src = common / "main.py"
    src.write_text("def f(x):\n"
                   "    if x > 0:\n"
                   "        return x\n"
                   "    return -x\n")
    rules = {
        "model": "white",
        "syntax": ["return"],
    }
    res = StaticAnalyzer().analyze(
        submission_id=str(tmp_path),
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "if" in res.message


def test_zip_static_analysis_python_return_blacklist(tmp_path):
    src_dir = tmp_path / "src" / "common"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("def f(x):\n"
                                     "    if x > 0:\n"
                                     "        return x\n"
                                     "    return -x\n")
    (src_dir / "Makefile").write_text("run:\n\tpython main.py\n")
    rules = {"model": "black", "syntax": ["return"]}
    res = StaticAnalyzer().analyze_zip_sources(
        source_dir=src_dir,
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "return" in res.message


def test_zip_static_analysis_disallowed_language_files(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('ok')")
    (src_dir / "bad.cpp").write_text("int main(){return 0;}")
    rules = {"model": "black", "syntax": []}
    res = StaticAnalyzer().analyze_zip_sources(
        source_dir=src_dir,
        language=Language.PY,
        rules=rules,
    )
    assert not res.is_success()
    assert "Disallowed language files" in res.message


# === Path Traversal Protection Tests ===


def test_makefile_path_traversal_blocked(tmp_path, caplog):
    """Makefile 中的 ../ 路徑應該被阻擋"""
    import logging
    caplog.set_level(logging.WARNING)

    # 建立目錄結構
    src_dir = tmp_path / "submission" / "src"
    src_dir.mkdir(parents=True)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    # 在目錄外建立一個檔案
    (outside_dir / "secret.c").write_text("// secret code")

    # 建立包含路徑穿越的 Makefile
    (src_dir / "Makefile").write_text("CC=gcc\n"
                                      "SOURCES=main.c ../../outside/secret.c\n"
                                      "all:\n\t$(CC) $(SOURCES)\n")
    (src_dir / "main.c").write_text("int main() { return 0; }")

    # 收集原始檔
    sources = _collect_sources_from_makefile(src_dir, Language.C)

    # 應該只包含 main.c，不應包含 secret.c
    source_names = [s.name for s in sources]
    assert "main.c" in source_names
    assert "secret.c" not in source_names

    # 應該有警告日誌
    assert "Path traversal blocked" in caplog.text


def test_makefile_normal_paths_allowed(tmp_path):
    """Makefile 中的正常路徑應該正常處理"""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    subdir = src_dir / "lib"
    subdir.mkdir()

    (src_dir / "main.c").write_text("int main() { return 0; }")
    (subdir / "helper.c").write_text("void help() {}")
    (src_dir / "Makefile").write_text("SOURCES=main.c lib/helper.c\n"
                                      "all:\n\tgcc $(SOURCES)\n")

    sources = _collect_sources_from_makefile(src_dir, Language.C)
    source_names = [s.name for s in sources]

    assert "main.c" in source_names
    assert "helper.c" in source_names


def test_get_violations_python_blacklist_imports_and_functions():
    analyzer = StaticAnalyzer()
    facts = {
        "imports": [{
            "name": "os",
            "line": 1,
        }],
        "function_calls": [{
            "name": "eval",
            "line": 2,
        }],
        "syntax": [{
            "name": "return",
            "line": 3,
        }],
    }
    rules = {
        "model": "black",
        "imports": ["os"],
        "functions": ["eval"],
        "syntax": ["return"],
    }
    violations = analyzer.get_violations(facts, rules, Language.PY)
    assert violations["model"] == "black"
    assert violations["imports"][0]["content"] == "os"
    assert violations["functions"][0]["content"] == "eval"
    assert violations["syntax"][0]["content"] == "return"
    assert "headers" not in violations


def test_get_violations_python_whitelist_blocks_unlisted_import():
    analyzer = StaticAnalyzer()
    facts = {
        "imports": [{
            "name": "os",
            "line": 1,
        }, {
            "name": "sys",
            "line": 2,
        }],
        "function_calls": [],
        "syntax": [],
    }
    rules = {
        "model": "white",
        "imports": ["os"],
        "functions": [],
        "syntax": [],
    }
    violations = analyzer.get_violations(facts, rules, Language.PY)
    assert any(item["content"] == "sys" for item in violations["imports"])
