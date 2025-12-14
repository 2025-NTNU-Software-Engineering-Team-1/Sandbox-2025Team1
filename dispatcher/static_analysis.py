import subprocess, shlex
import pathlib
import ast
import json
import re
from typing import TYPE_CHECKING, Tuple, Optional

try:
    import clang.cindex  # type: ignore
except ImportError:
    clang = None  # type: ignore

from dispatcher import config as dispatcher_config
from .constant import Language
from .utils import logger

if TYPE_CHECKING:
    from .meta import Meta

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def detect_include_args():
    args = []
    try:
        rdir = subprocess.check_output(["clang", "-print-resource-dir"],
                                       text=True).strip()
        args += [f"-I{pathlib.Path(rdir) / 'include'}"]

        # libstdc++ path (auto)
        cxx_inc = subprocess.check_output(["g++", "-print-file-name=include"],
                                          text=True).strip()
        args += [f"-I{cxx_inc}"]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    # try these path
    args += ["-I/usr/include", "-I/usr/include/x86_64-linux-gnu"]
    return args


def _allowed_ext_for_language(language: Language) -> set[str]:
    if language == Language.C:
        return {".c", ".h"}
    if language == Language.CPP:
        return {".cpp", ".cc", ".cxx", ".h"}
    if language == Language.PY:
        return {".py"}
    return set()


def _is_code_file(path: pathlib.Path) -> bool:
    return path.suffix.lower() in {".c", ".cpp", ".cc", ".cxx", ".h", ".py"}


def _collect_sources_by_ext(source_dir: pathlib.Path,
                            language: Language) -> list[pathlib.Path]:
    """
    Collect source files based on language extension.
    """
    allowed_ext = _allowed_ext_for_language(language)
    return [
        p for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in allowed_ext
    ]


def _collect_sources_from_makefile(source_dir: pathlib.Path,
                                   language: Language) -> list[pathlib.Path]:
    """
    Parse Makefile to find source files.
    """
    makefile = source_dir / "Makefile"
    if not makefile.exists():
        return []
    text = makefile.read_text(errors="ignore")
    allowed_ext = _allowed_ext_for_language(language)
    pattern = r"[\w./-]+\.(c|cpp|cc|cxx|h|py)\b"
    candidates = set()
    for match in re.finditer(pattern, text):
        candidates.add(match.group(0))
    sources = []
    for cand in candidates:
        p = (source_dir / cand).resolve()
        if p.exists() and p.is_file() and p.suffix.lower() in allowed_ext:
            sources.append(p)
    return sources


def _merge_facts(target: dict, source: dict):
    for k, v in source.items():
        if k not in target:
            target[k] = []
        # v is a list of dicts or list of strings
        if isinstance(v, list):
            target[k].extend(v)


def build_sa_payload(analysis_result, status: str) -> dict:
    """
    Build a structured payload for static analysis report.
    """

    return {
        "status":
        status,
        "message":
        analysis_result.message.strip(),
        "violations": (json.dumps(analysis_result.json_result)
                       if analysis_result.json_result else ""),
        "report":
        analysis_result.message.strip(),
        # Retain raw result for backend if needed
        "json_result":
        analysis_result.json_result,
    }


def format_sa_failure_message(message: str) -> str:
    base = (message or "").strip()
    return f"Static Analysis Not Passed: {base}".strip(
    ) or "Static Analysis Not Passed"


def build_sa_ce_task_content(meta: "Meta", stderr: str) -> dict:
    task_content = {}
    for ti, task in enumerate(meta.tasks):
        for ci in range(task.caseCount):
            case_no = f"{ti:02d}{ci:02d}"
            task_content[case_no] = {
                "stdout": "",
                "stderr": stderr,
                "exitCode": 1,
                "execTime": -1,
                "memoryUsage": -1,
                "status": "CE",
            }
    return task_content


def run_static_analysis(
    submission_id: str,
    submission_path: pathlib.Path,
    meta: "Meta",
    rules_json: Optional[dict],
    *,
    is_zip_mode: bool,
) -> Tuple[bool, Optional[dict], Optional[dict]]:
    """
    Execute static analysis and return (success, payload, task_content_if_fail).
    Dispatcher delegates SA handling here to keep SA concerns contained.
    """
    if not rules_json:
        return True, None, None

    analyzer = StaticAnalyzer()
    try:
        if is_zip_mode:
            src_base = submission_path / "src"
            if (src_base / "common").exists():
                src_base = src_base / "common"
            analysis_result = analyzer.analyze_zip_sources(
                source_dir=src_base,
                language=meta.language,
                rules=rules_json,
            )
        else:
            analysis_result = analyzer.analyze(
                submission_id=submission_id,
                language=meta.language,
                rules=rules_json,
                base_dir=submission_path,
            )
        status = "pass" if analysis_result.is_success() else "fail"
        if getattr(analysis_result, "_skipped", False):
            status = "skip"

        payload = build_sa_payload(analysis_result, status)

        if analysis_result.is_success():
            return True, payload, None

        stderr = format_sa_failure_message(analysis_result.message)
        return False, payload, build_sa_ce_task_content(meta, stderr)

    except StaticAnalysisError as exc:
        logger().error(f"Static analyzer error: {exc}", exc_info=True)
        ar = AnalysisResult(success=False, message=str(exc))
        payload = build_sa_payload(ar, "fail")
        stderr = format_sa_failure_message(str(exc))
        return False, payload, build_sa_ce_task_content(meta, stderr)
    except Exception as exc:
        logger().error(f"Unexpected error during static analysis: {exc}",
                       exc_info=True)
        ar = AnalysisResult(success=False, message=str(exc))
        payload = build_sa_payload(ar, "fail")
        stderr = format_sa_failure_message(str(exc))
        return False, payload, build_sa_ce_task_content(meta, stderr)


class StaticAnalysisError(Exception):
    pass


class AnalysisResult:

    def __init__(self,
                 success=True,
                 message="",
                 rules="",
                 facts="",
                 violations=""):
        self._success = success
        self._skipped = False
        self.message = message
        self.json_result = {}

    def is_success(self):
        return self._success

    def mark_skipped(self, msg: str):
        self._skipped = True
        self._success = True
        self.message += msg

    def set_violations(self, structured_violations: dict):
        self.json_result = structured_violations

        msg = "\n-------------------------- Static Analysis Result -------------------------"
        for item, lines in structured_violations.items():
            if item == "model":
                continue
            if not lines:
                continue
            msg += f"\n [Category: {item}]"
            # Deduplicate lines for display
            seen_lines = set()
            for line in lines:
                val = f"{line['line']}:{line['content']}"
                if val not in seen_lines:
                    msg += f"\n    Line {line['line']:<4} : {line['content']}"
                    seen_lines.add(val)

        self.message += msg

    def to_json_str(self):
        return json.dumps(self.json_result, indent=4)


class StaticAnalyzer:

    def __init__(self):
        self.result = AnalysisResult()

    def analyze(
        self,
        submission_id: str,
        language: Language,
        rules: dict = None,
        base_dir: pathlib.Path | str | None = None,
    ):
        """
        HERE is entrance
        main Analyzer
        """
        if base_dir:
            source_code_path = pathlib.Path(base_dir)
        else:
            source_code_path = pathlib.Path(submission_id)
            if not source_code_path.exists():
                submission_cfg = dispatcher_config.get_submission_config()
                source_code_path = pathlib.Path(
                    submission_cfg["working_dir"]) / str(submission_id)
        if (source_code_path / "src").exists():
            source_code_path = source_code_path / "src"
        common_dir = source_code_path / "common"
        if common_dir.exists():
            source_code_path = common_dir
        else:
            raise StaticAnalysisError(
                f"common dir missing for SA: {common_dir}")
        source_code_path = source_code_path.resolve()

        logger().debug(f"Analysis: {source_code_path} (lang: {language})")
        if not isinstance(rules, dict):
            rules = {}

        try:
            if language == Language.PY:
                self._analyze_python(source_code_path, rules)

            elif language == Language.C or language == Language.CPP:
                if clang is None:
                    logger().warning("libclang missing; skip static analysis")
                    self.result.mark_skipped(
                        "\nlibclang missing; static analysis skipped.")
                    return self.result
                self._analyze_c_cpp(source_code_path, rules, language)

            else:
                logger().warning(
                    f"Unsupported static analysis languages: {language}")
                self.result._success = False
                self.result.message += (
                    f"\nUnsupported static analysis languages: {language}")

        except StaticAnalysisError:
            logger().error(f"Static Analyzer inner error", exc_info=True)
            raise

        except Exception as e:
            logger().error(f"An unexpected error occurred: {e}", exc_info=True)
            raise StaticAnalysisError(
                f"An unexpected error occurred: {e}") from e

        if self.result.is_success():
            logger().debug("Static analysis passed.")
            self.result.message += "\nGOOD JOB, passed static analysis."

        return self.result

    def analyze_zip_sources(
        self,
        source_dir: pathlib.Path,
        language: Language,
        rules: dict | None = None,
    ):
        """
        Analyze source codes in a directory (for ZIP submission).
        It checks for disallowed files, collects source files, and runs static analysis.
        """
        if not isinstance(rules, dict):
            rules = {}

        # 1. Check for disallowed files
        allowed_ext = _allowed_ext_for_language(language)
        disallowed_files = [
            p for p in source_dir.rglob("*") if p.is_file()
            and _is_code_file(p) and p.suffix.lower() not in allowed_ext
        ]
        if disallowed_files:
            self.result._success = False
            bad = ", ".join(
                str(p.relative_to(source_dir)) for p in disallowed_files)
            self.result.message += f"Disallowed language files found: {bad}"
            return self.result

        # 2. Collect source files
        sources = _collect_sources_from_makefile(source_dir, language)
        if not sources:
            sources = _collect_sources_by_ext(source_dir, language)
        if not sources:
            self.result._success = False
            self.result.message += "no source files found for zip submission"
            return self.result

        # 3. Run language-specific analysis
        if language == Language.PY:
            self._analyze_python(source_dir, rules, files=sources)
        elif language in (Language.C, Language.CPP):
            if clang is None:
                logger().warning("libclang missing; skip static analysis")
                self.result.mark_skipped(
                    "\nlibclang missing; static analysis skipped.")
                return self.result
            self._analyze_c_cpp(source_dir, rules, language, files=sources)
        else:
            self.result._success = False
            self.result.message += f"unsupported language: {language}"

        if self.result.is_success():
            logger().debug("Static analysis passed.")
            self.result.message += "\nGOOD JOB, passed static analysis."

        return self.result

    def _analyze_python(
        self,
        source_path: pathlib.Path,
        rules: dict,
        files: list[pathlib.Path] | None = None,
    ):
        """
        for python use ast + mult-file support
        """
        # Determine target files
        if files:
            target_files = files
        else:
            main_py = source_path / "main.py"
            if not main_py.exists():
                raise StaticAnalysisError(
                    f"Not found 'main.py'. Source path: {source_path}")
            target_files = [main_py]

        # Definition Visitor
        global_funcs = set()
        defined_classes = {}
        # Analysis
        parsed_trees = []

        for path in target_files:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                parsed_trees.append((tree, path))

                def_visitor = DefinitionVisitor()
                def_visitor.visit(tree)
                global_funcs.update(def_visitor.global_functions)
                defined_classes.update(def_visitor.defined_classes)
            except SyntaxError as e:
                self.result._success = False
                self.result.message += f"\nSyntax Error could not analyze {path}:\n{e}"
                return self.result

        facts = {
            "imports": [],
            "function_calls": [],
            "syntax": [],
        }

        for tree, path in parsed_trees:
            visitor = PythonAstVisitor(
                global_functions=global_funcs,
                defined_classes=defined_classes,
            )
            visitor.visit(tree)
            visitor.detect_cycles()
            _merge_facts(facts, visitor.facts)

        logger().debug(f"Python analysis facts: {facts}")

        violations_dict = self.get_violations(facts, rules, Language.PY)
        if violations_dict:
            logger().debug("Static analysis failed.")
            self.result._success = False
            self.result.set_violations(violations_dict)

        return self.result

    def _analyze_c_cpp(
        self,
        source_path: pathlib.Path,
        rules: dict,
        language: Language,
        files: list[pathlib.Path] | None = None,
    ):
        """
        for C/C++ use libclang + multi-file support
        """
        if files:
            target_paths = files
        else:
            main_c_path = source_path / "main.c"
            main_cpp_path = source_path / "main.cpp"
            if main_c_path.exists():
                target_paths = [main_c_path]
            elif main_cpp_path.exists():
                target_paths = [main_cpp_path]
            else:
                raise StaticAnalysisError(
                    f"Not found 'main.c' or 'main.cpp'.  Source path: {source_path}"
                )

        facts = {
            "headers": [],
            "function_calls": [],
            "syntax": [],
        }

        # Setup Clang Index
        try:
            index = clang.cindex.Index.create()
            lang_args = []
            if language == Language.C:
                lang_args = ["-x", "c", "-std=c11"]
            else:
                lang_args = ["-x", "c++", "-std=c++17"]

            include_args = detect_include_args()
        except clang.cindex.LibclangError as e:
            raise StaticAnalysisError(f"Libclang init failed: {e}")

        # analyze each file
        for target_path in target_paths:
            translation_unit = index.parse(
                str(target_path),
                args=lang_args + include_args,
                options=clang.cindex.TranslationUnit.
                PARSE_DETAILED_PROCESSING_RECORD,
            )
            if not translation_unit:
                self.result._success = False
                self.result.message += (
                    f"[Syntax Error] Clang could not analyze {target_path.name}"
                )
                return self.result

            visitor = CppAstVisitor(str(target_path))
            visitor.visit(translation_unit.cursor)
            visitor.detect_cycles()
            _merge_facts(facts, visitor.facts)
        logger().debug(f"C/C++ analysis facts: {facts}")

        violations_dict = self.get_violations(facts, rules, language)

        if violations_dict:
            logger().debug("Static analysis failed.")
            self.result._success = False
            self.result.set_violations(violations_dict)

        return self.result

    def get_violations(self, facts: dict, rules: dict,
                       language: Language) -> dict:
        """
        return structured violations dict
        example:
        {
            "model": "black",
            "syntax": [{"content": "while", "line": 10}, ...],
            "headers": [...],
            "functions": [...]
        }
        """
        model = rules.get("model", "black")
        violations_structure = {
            "model": model,
            "syntax": [],
            "headers": [],
            "imports": [],
            "functions": [],
        }
        # import / header check
        if language == Language.PY:
            violations_structure["imports"] = self._check_items(
                facts.get("imports", []), rules.get("imports", []), model)
            del violations_structure["headers"]
        else:
            violations_structure["headers"] = self._check_items(
                facts.get("headers", []), rules.get("headers", []), model)
            del violations_structure["imports"]

        # function call check
        violations_structure["functions"] = self._check_items(
            facts.get("function_calls", []), rules.get("functions", []), model)
        # syntax check
        violations_structure["syntax"] = self._check_items(
            facts.get("syntax", []), rules.get("syntax", []), model)

        has_violations = False
        for key, items in violations_structure.items():
            if key == "model":
                continue
            if items:
                has_violations = True

        if not has_violations:
            return {}
        return violations_structure

    def _check_items(self, used_items: list, rule_items: list,
                     model: str) -> list:
        """
        used_items: [{"name": "sort", "line": 10}, ...]
        rule_items: ["sort", "vector"]
        return: [{"content": "sort", "line": 10}, ...]
        """
        violations = []
        rule_set = set(rule_items)

        for item in used_items:
            name = item["name"]
            lineno = item["line"]
            is_violation = False

            if model == "black":
                if name in rule_set:
                    is_violation = True
                else:
                    for rule in rule_set:
                        if name.endswith("." + rule):
                            is_violation = True
                            break

            elif model == "white":
                is_allowed = False
                if name in rule_set:
                    is_allowed = True
                else:
                    for rule in rule_set:
                        if name.endswith("." + rule):
                            is_allowed = True
                            break

                if not is_allowed:
                    is_violation = True

            if is_violation:
                violations.append({"content": name, "line": lineno})

        # Deduplicate results by line and content
        unique_violations = []
        seen = set()
        for v in violations:
            key = (v["content"], v["line"])
            if key not in seen:
                seen.add(key)
                unique_violations.append(v)

        return sorted(unique_violations, key=lambda x: x["line"])


class DefinitionVisitor(ast.NodeVisitor):

    def __init__(self):
        self.global_functions = set()
        self.defined_classes = {}

    def visit_FunctionDef(self, node):
        self.global_functions.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_name = node.name
        methods = set()
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.add(item.name)
        self.defined_classes[class_name] = methods


class PythonAstVisitor(ast.NodeVisitor):
    """
    for python analyze
    """

    def __init__(self, global_functions: set, defined_classes: dict):
        self.facts = {
            "imports": [],
            "function_calls": [],
            "syntax": [],
        }
        self.current_function_stack = []
        self.global_functions = global_functions
        self.defined_classes = defined_classes
        self.variable_types = {}
        self.call_graph = {}

    def generic_visit(self, node):
        tag_name = node.__class__.__name__.lower()
        if hasattr(node, "lineno"):
            self.facts["syntax"].append({
                "name": tag_name,
                "line": node.lineno
            })
        super().generic_visit(node)

    def _get_full_call_name(self, func_node: ast.AST) -> str | None:
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            base_name = self._get_full_call_name(func_node.value)
            if base_name:
                return f"{base_name}.{func_node.attr}"
            else:
                return func_node.attr
        return None

    def visit_Import(self, node):
        for alias in node.names:
            self.facts["imports"].append({
                "name": alias.name,
                "line": node.lineno
            })

    def visit_ImportFrom(self, node):
        if node.module:
            self.facts["imports"].append({
                "name": node.module,
                "line": node.lineno
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        current_function_name = node.name
        self.current_function_stack.append(current_function_name)

        if current_function_name not in self.call_graph:
            self.call_graph[current_function_name] = []

        self.generic_visit(node)
        self.current_function_stack.pop()

    def visit_Assign(self, node):
        right_side_class = None
        if isinstance(node.value, ast.Call):
            func_name = self._get_full_call_name(node.value.func)
            if func_name in self.defined_classes:
                right_side_class = func_name

        if right_side_class:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    self.variable_types[var_name] = right_side_class
        self.generic_visit(node)

    def visit_Call(self, node):
        full_call_name = self._get_full_call_name(node.func)
        if not full_call_name:
            self.generic_visit(node)
            return

        if "." in full_call_name:
            called_func_name = full_call_name.rsplit(".", 1)[-1]
        else:
            called_func_name = full_call_name

        is_user_defined = False
        if full_call_name in self.global_functions:
            is_user_defined = True
        elif "." in full_call_name:
            parts = full_call_name.rsplit(".", 1)
            if len(parts) == 2:
                obj_name, method_name = parts
                obj_type = self.variable_types.get(obj_name)
                if obj_type and obj_type in self.defined_classes:
                    if method_name in self.defined_classes[obj_type]:
                        is_user_defined = True
                if obj_name == "self":
                    is_user_defined = True

        if is_user_defined:
            if (self.current_function_stack
                    and called_func_name in self.current_function_stack):
                self.facts["syntax"].append({
                    "name": "recursive",
                    "line": node.lineno
                })
            if self.current_function_stack:
                caller = self.current_function_stack[-1]
                callee = called_func_name
                if caller not in self.call_graph:
                    self.call_graph[caller] = []
                self.call_graph[caller].append((callee, node.lineno))
        else:
            self.facts["function_calls"].append({
                "name": full_call_name,
                "line": node.lineno
            })
        self.generic_visit(node)

    def detect_cycles(self):
        visited = set()
        recursion_stack = set()

        def dfs(u):
            visited.add(u)
            recursion_stack.add(u)
            if u in self.call_graph:
                for v, lineno in self.call_graph[u]:
                    if v not in visited:
                        dfs(v)
                    elif v in recursion_stack:
                        # Report recursion if not already reported
                        already_reported = False
                        for item in self.facts["syntax"]:
                            if item["name"] == "recursive" and item[
                                    "line"] == lineno:
                                already_reported = True
                                break
                        if not already_reported:
                            self.facts["syntax"].append({
                                "name": "recursive",
                                "line": lineno
                            })
            recursion_stack.remove(u)

        for node in list(self.call_graph.keys()):
            if node not in visited:
                dfs(node)


class CppAstVisitor:

    def __init__(self, main_file_path: str):
        self.main_file_path = main_file_path
        self.facts = {
            "headers": [],
            "function_calls": [],
            "syntax": [],
        }
        self.call_graph = {}
        self.usr_to_name = {}

    def visit(self, node, current_function_usr=None):
        if node.kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE:
            if str(node.location.file) == self.main_file_path:
                self.facts["headers"].append({
                    "name": node.spelling,
                    "line": node.location.line
                })
            return

        in_main = (node.location and node.location.file
                   and str(node.location.file) == self.main_file_path)

        if node.kind in (
                clang.cindex.CursorKind.FUNCTION_DECL,
                clang.cindex.CursorKind.CXX_METHOD,
                clang.cindex.CursorKind.CONSTRUCTOR,
                clang.cindex.CursorKind.DESTRUCTOR,
        ):
            if node.is_definition():
                current_function_usr = node.get_usr()
                self.usr_to_name[current_function_usr] = node.spelling
                if current_function_usr not in self.call_graph:
                    self.call_graph[current_function_usr] = []

        if in_main:
            if node.kind in (
                    clang.cindex.CursorKind.FOR_STMT,
                    clang.cindex.CursorKind.CXX_FOR_RANGE_STMT,
            ):
                self.facts["syntax"].append({
                    "name": "for",
                    "line": node.location.line
                })
            elif node.kind == clang.cindex.CursorKind.WHILE_STMT:
                self.facts["syntax"].append({
                    "name": "while",
                    "line": node.location.line
                })
            elif node.kind in (
                    clang.cindex.CursorKind.CALL_EXPR,
                    clang.cindex.CursorKind.MEMBER_REF_EXPR,
            ):
                if "operator" not in node.spelling:
                    self._handle_call(node, current_function_usr)

        for child in node.get_children():
            self.visit(child, current_function_usr)

    def _handle_call(self, node, caller_usr):
        callee = node.referenced
        if callee is None:
            return
        callee_usr = callee.get_usr()
        callee_name = callee.spelling

        callee_file = None
        if callee.location and callee.location.file:
            callee_file = str(callee.location.file)

        is_system = True
        if callee_file == self.main_file_path:
            is_system = False

        if is_system:
            if callee_name:
                self.facts["function_calls"].append({
                    "name": callee_name,
                    "line": node.location.line
                })
        else:
            if caller_usr:
                if caller_usr not in self.call_graph:
                    self.call_graph[caller_usr] = []
                self.call_graph[caller_usr].append(
                    (callee_usr, node.location.line))

    def detect_cycles(self):
        visited = set()
        recursion_stack = set()

        def dfs(u):
            visited.add(u)
            recursion_stack.add(u)

            if u in self.call_graph:
                for v, lineno in self.call_graph[u]:
                    if v not in visited:
                        dfs(v)
                    elif v in recursion_stack:
                        already_reported = False
                        for item in self.facts["syntax"]:
                            if item["name"] == "recursive" and item[
                                    "line"] == lineno:
                                already_reported = True
                                break
                        if not already_reported:
                            self.facts["syntax"].append({
                                "name": "recursive",
                                "line": lineno
                            })
            recursion_stack.remove(u)

        for node in list(self.call_graph.keys()):
            if node not in visited:
                dfs(node)
