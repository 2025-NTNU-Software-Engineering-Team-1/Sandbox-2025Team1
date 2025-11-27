import subprocess, shlex
import pathlib
import ast
import json
import re

try:
    import clang.cindex  # type: ignore
except ImportError:
    pass

from dispatcher import config as dispatcher_config
from .constant import Language
from .utils import logger


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
        if isinstance(v, set):
            target[k] = target.get(k, set()) | v
        elif isinstance(v, list):
            target.setdefault(k, []).extend(v)
        else:
            target[k] = v


def build_sa_payload(analysis_result, status: str) -> dict:
    """
    Build a structured payload for static analysis report.
    """

    def _txt(field):
        return str(field).strip() if field else ""

    parts = [
        _txt(analysis_result.message),
        _txt(analysis_result.violations),
        _txt(analysis_result.rules),
        _txt(analysis_result.facts)
    ]
    report = "\n".join(p for p in parts if p).strip()
    return {
        "status": status,
        "message": _txt(analysis_result.message),
        "violations": _txt(analysis_result.violations),
        "rules": _txt(analysis_result.rules),
        "report": report,
    }


class StaticAnalysisError(Exception):
    """
    for debug
    """

    pass


class AnalysisResult:
    """
    write analysis report
    """

    def __init__(self,
                 success=True,
                 message="",
                 rules="",
                 facts="",
                 violations=""):
        self._success = success
        self.message = message
        self.rules = rules
        self.facts = facts
        self.violations = violations

    def is_success(self):
        return self._success

    def good_look_output_rules(self, rules: dict):
        if not rules:
            rules_str = "No rules applied."
            return rules_str
        rules_items = []
        max_key_len = max(len(key) for key in rules.keys()) + 1
        for key, value in rules.items():
            if isinstance(value, list):
                value_str = self._format_list_value(key, value, max_key_len)
            else:
                value_str = self._format_scalar_value(value)
            rules_items.append(f"  {key.ljust(max_key_len)}: {value_str}")

        rules_str = "\n".join(rules_items)
        self.rules += f"\n------------------------------ Applied Rules ------------------------------"
        self.rules += f"\n{rules_str}\n"
        # self.rules += f"\n---------------------------------------------------------------------------"

        return rules_str

    def good_look_output_facts(self, facts: dict):
        facts_items = []
        max_key_len = max(len(key) for key in facts.keys()) + 1

        for key, value in facts.items():
            if isinstance(value, (list, set)):
                value_str = self._format_list_value(key, value, max_key_len)
            else:
                value_str = self._format_scalar_value(value)
            facts_items.append(f"  {key.ljust(max_key_len)}: {value_str}")
        facts_str = "\n".join(facts_items)
        self.facts += f"\n----------------------------- Collected Facts -----------------------------"
        self.facts += f"\n{facts_str}"
        # self.facts += f"\n---------------------------------------------------------------------------"

    def good_look_output_violations(self, violations: dict):
        violations_items = []
        max_key_len = max(len(key) for key in violations.keys()) + 1

        for key, value in violations.items():
            value_str = self._format_list_value(key, value, max_key_len)
            violations_items.append(f"  {key.ljust(max_key_len)}: {value_str}")

        violations_str = "\n".join(violations_items)

        self.violations += f"\n-------------------------- Static Analysis Failed -------------------------"
        self.violations += f"\n{violations_str}\n"
        # self.violations += f"\n---------------------------------------------------------------------------"

    def _format_scalar_value(self, value) -> str:
        if value == "black":
            return "Disallow"
        if value == "white":
            return "Only Allow"
        return str(value)

    def _format_list_value(self, key: str, value_list: list,
                           max_key_len: int) -> str:
        if not value_list:
            return "(empty)"
        value_list = sorted(value_list)
        str_values = [str(v) for v in value_list]
        chunk_size = 5
        if len(str_values) <= chunk_size:
            return ", ".join(str_values)
        chunks = [
            str_values[i:i + chunk_size]
            for i in range(0, len(str_values), chunk_size)
        ]
        joined_chunks = [", ".join(chunk) for chunk in chunks]
        line_indent = " " * (2 + max_key_len + 2)
        return f"\n{line_indent}".join(joined_chunks)


class StaticAnalyzer:

    def __init__(self):
        self.result = AnalysisResult()

    def analyze(
        self,
        submission_id: str,
        language: Language,
        rules: dict = None,
    ):
        """
        HERE is entrance
        main Analyzer
        """
        source_code_path = pathlib.Path(submission_id)
        if not source_code_path.exists():
            submission_cfg = dispatcher_config.get_submission_config()
            source_code_path = pathlib.Path(
                submission_cfg["working_dir"]) / str(submission_id)
        if (source_code_path / "src").exists():
            source_code_path = source_code_path / "src"
        source_code_path = source_code_path.resolve()

        logger().debug(f"Analysis: {source_code_path} (lang: {language})")
        if not isinstance(rules, dict):
            rules = {}
        try:
            self.result.good_look_output_rules(rules)
            if language == Language.PY:
                self._analyze_python(source_code_path, rules)

            elif language == Language.C or language == Language.CPP:
                if "clang" not in globals():
                    self.result._success = False
                    self.result.message += (
                        "Libclang is not installed; skip static analysis.")
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
            logger().error(
                f"An unexpected error occurred during static analysis: {e}",
                exc_info=True,
            )
            raise StaticAnalysisError(
                f"An unexpected error occurred: {e}") from e

        if self.result.is_success():
            logger().debug("Static analysis passed.")

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
        self.result.good_look_output_rules(rules)

        # 1. Check for disallowed files (security check)
        # Ensure no other language files exist in the submission
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
        # Priority: Makefile > Extension-based
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
            if "clang" not in globals():
                self.result._success = False
                self.result.message += (
                    "Libclang is not installed; skip static analysis.")
                return self.result
            self._analyze_c_cpp(source_dir, rules, language, files=sources)
        else:
            self.result._success = False
            self.result.message += f"unsupported language: {language}"
        return self.result

    def _analyze_python(
        self,
        source_path: pathlib.Path,
        rules: dict,
        files: list[pathlib.Path] | None = None,
    ):
        """
        for python use ast
        """
        target_files = files or [source_path / "main.py"]
        facts = {
            "imports": set(),
            "function_calls": set(),
            "for_loops": [],
            "while_loops": [],
            "recursive_calls": [],
            "return_stmts": [],
            "syntax_tags": set(),
            "syntax_lines": {},
        }

        for path in target_files:
            if not path.exists():
                raise StaticAnalysisError(
                    f"Not found '{path.name}'. Source path: {path.parent}")
            with open(path, "r") as f:
                content = f.read()

            try:
                tree = ast.parse(content)
                def_visitor = FunctionDefVisitor()
                def_visitor.visit(tree)
                user_defined_functions = def_visitor.defined_functions
                visitor = PythonAstVisitor(
                    user_defined_functions=user_defined_functions)
                visitor.visit(tree)
                _merge_facts(facts, visitor.facts)
            except SyntaxError as e:
                self.result._success = False
                self.result.message += (
                    f"\nSyntax Error could not analyze {path}:\n{e}")
                return self.result

        logger().debug(f"Python analysis facts: {facts}")
        violations = self.get_violations(facts, rules, Language.PY)
        if violations:
            logger().debug("Static analysis failed.")
            self.result._success = False
            self.result.good_look_output_violations(violations)
        else:
            self.result._success = True
            self.result.message += f"\nGOOD JOB, passed static analysis."

        self.result.good_look_output_facts(facts)
        return self.result

    def _analyze_c_cpp(
        self,
        source_path: pathlib.Path,
        rules: dict,
        language: Language,
        files: list[pathlib.Path] | None = None,
    ):
        """
        for C/C++ use libclang
        """
        target_paths: list[pathlib.Path] = []
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
            "headers": set(),
            "function_calls": set(),
            "for_loops": [],
            "while_loops": [],
            "recursive_calls": [],
            "return_stmts": [],
            "syntax_tags": set(),
            "syntax_lines": {},
        }

        for target_path in target_paths:
            try:
                index = clang.cindex.Index.create()
                lang_args = []
                if language == Language.C:
                    lang_args = ["-x", "c", "-std=c11"]
                else:
                    lang_args = ["-x", "c++", "-std=c++17"]

                translation_unit = index.parse(
                    str(target_path),
                    args=lang_args + detect_include_args(),
                    options=clang.cindex.TranslationUnit.
                    PARSE_DETAILED_PROCESSING_RECORD,
                )

            except clang.cindex.LibclangError as e:
                raise StaticAnalysisError(f"Libclang init failed: {e}")

            if not translation_unit:
                self.result._success = False
                self.result.message += (
                    f"[Syntax Error] Clang could not analyze {target_path}")
                return self.result

            analyze_c_ast(translation_unit.cursor, facts, None,
                          str(target_path))
        logger().debug(f"C/C++ analysis facts: {facts}")
        # for debug
        # print(facts)
        # (2) fact vs rules
        violations = self.get_violations(facts, rules, language)

        # (3) Result
        if violations:
            logger().debug("Static analysis failed.")
            self.result._success = False
            self.result.good_look_output_violations(violations)
        else:
            self.result._success = True
            self.result.message += f"\nGOOD JOB, passed static analysis."

        self.result.good_look_output_facts(facts)
        return self.result

    def get_violations(self, facts: dict, rules: dict,
                       language: Language) -> dict:
        violations_dict = {}
        model = rules.get("model", "black")

        if language == Language.PY:
            list_violation = self._check_list_violations(
                facts["imports"], rules.get("imports", []), model, "Imports")
            if list_violation:
                violations_dict[list_violation[0]] = list_violation[1]
        else:
            list_violation = self._check_list_violations(
                facts["headers"], rules.get("headers", []), model, "Headers")
            if list_violation:
                violations_dict[list_violation[0]] = list_violation[1]

        syntax_violations_list = self._check_syntax_violations(
            facts, rules.get("syntax", []), model)
        for key, lines in syntax_violations_list:
            violations_dict[key] = lines

        list_violation = self._check_list_violations(
            facts["function_calls"], rules.get("functions", []), model,
            "Functions")
        if list_violation:
            violations_dict[list_violation[0]] = list_violation[1]

        return violations_dict

    def _check_list_violations(self, used_items: set, rule_items: list,
                               model: str, item_type: str) -> tuple | None:
        rule_set = set(rule_items)

        if model == "black":
            violations_found = used_items.intersection(rule_set)
            if violations_found:
                return (f"Disallowed {item_type}",
                        sorted(list(violations_found)))
        elif model == "white":
            violations_found = used_items.difference(rule_set)
            if violations_found:
                return (f"Non-whitelisted {item_type}",
                        sorted(list(violations_found)))

        return None

    def _check_syntax_violations(self, facts: dict, rule_syntax: list,
                                 model: str) -> list:
        violations_data = []
        rule_set = {str(s).lower() for s in rule_syntax}
        syntax_checks = {
            "for": ("for_loops", "For Loop"),
            "while": ("while_loops", "While Loop"),
            "recursive": ("recursive_calls", "Recursive Call"),
            "return": ("return_stmts", "Return Statement"),
        }
        syntax_tags = facts.get("syntax_tags", set())
        syntax_lines = facts.get("syntax_lines", {})

        # compatibility for existing facts (for/while/recursive/return)
        for syntax_key, (fact_key, message) in syntax_checks.items():
            lines = facts.get(fact_key, [])
            if lines:
                syntax_tags.add(syntax_key)
                if syntax_key not in syntax_lines:
                    syntax_lines[syntax_key] = []
                syntax_lines[syntax_key].extend(lines)

        if model == "black":
            matched = sorted(syntax_tags.intersection(rule_set))
            for tag in matched:
                violations_data.append(
                    (f"Disallowed Syntax ({tag})", syntax_lines.get(tag, [])))
        elif model == "white":
            unmatched = sorted(syntax_tags.difference(rule_set))
            for tag in unmatched:
                violations_data.append((f"Non-whitelisted Syntax ({tag})",
                                        syntax_lines.get(tag, [])))

        return violations_data


class FunctionDefVisitor(ast.NodeVisitor):

    def __init__(self):
        self.defined_functions = set()

    def visit_FunctionDef(self, node):
        self.defined_functions.add(node.name)
        self.generic_visit(node)


class PythonAstVisitor(ast.NodeVisitor):
    """
    for python analyze
    """

    def __init__(self, user_defined_functions: set):
        # log used "fact"
        self.facts = {
            "imports": set(),
            "function_calls": set(),
            "for_loops": [],
            "while_loops": [],
            "recursive_calls": [],
            "return_stmts": [],
            "syntax_tags": set(),
            "syntax_lines": {},
        }

        # for recursive check
        self.current_function_stack = []
        self.user_defined_functions = user_defined_functions

    def visit_Import(self, node):
        self._record_tag(node)
        for alias in node.names:
            self.facts["imports"].add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self._record_tag(node)
        if node.module:
            self.facts["imports"].add(node.module)
        self.generic_visit(node)

    def visit_For(self, node):
        self._record_tag(node)
        self.facts["for_loops"].append(node.lineno)
        self.generic_visit(node)

    def visit_While(self, node):
        self._record_tag(node)
        self.facts["while_loops"].append(node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._record_tag(node)
        current_function_name = node.name
        self.current_function_stack.append(current_function_name)
        self.generic_visit(node)
        self.current_function_stack.pop()

    def visit_Call(self, node):
        self._record_tag(node)
        function_name_called = None
        is_user_defined = False

        if isinstance(node.func, ast.Name):
            function_name_called = node.func.id
            if function_name_called in self.user_defined_functions:
                is_user_defined = True
        elif isinstance(node.func, ast.Attribute):
            function_name_called = node.func.attr

        if function_name_called and not is_user_defined:
            self.facts["function_calls"].add(function_name_called)

        if (self.current_function_stack
                and function_name_called == self.current_function_stack[-1]):
            self.facts["recursive_calls"].append(node.lineno)
        self.generic_visit(node)

    def visit_Return(self, node):
        self._record_tag(node)
        self.facts["return_stmts"].append(node.lineno)
        self.generic_visit(node)

    def generic_visit(self, node):
        # record any other node kinds to allow arbitrary syntax rules
        self._record_tag(node)
        super().generic_visit(node)

    def _record_tag(self, node):
        tag = node.__class__.__name__.lower()
        self.facts["syntax_tags"].add(tag)
        lineno = getattr(node, "lineno", None)
        if lineno is not None:
            self.facts["syntax_lines"].setdefault(tag, []).append(lineno)


def analyze_c_ast(node, facts, current_func_cursor, main_file_path: str):
    if node.kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE:
        if node.location.file and node.location.file.name == main_file_path:
            facts["headers"].add(node.displayname)
        return
    in_main = (node.location and node.location.file
               and node.location.file.name == main_file_path)

    if in_main:
        # record syntax tag for arbitrary rule matching
        tag = node.kind.name.lower()
        facts["syntax_tags"].add(tag)
        if tag.endswith("_stmt") or tag.endswith("_expr"):
            base = tag.rsplit("_", 1)[0]
            facts["syntax_tags"].add(base)
            facts["syntax_lines"].setdefault(base,
                                             []).append(node.location.line)
        facts["syntax_lines"].setdefault(tag, []).append(node.location.line)
        if node.kind in (
                clang.cindex.CursorKind.FOR_STMT,
                clang.cindex.CursorKind.CXX_FOR_RANGE_STMT,
        ):
            facts["for_loops"].append(node.location.line)

        elif node.kind == clang.cindex.CursorKind.WHILE_STMT:
            facts["while_loops"].append(node.location.line)

        elif node.kind == clang.cindex.CursorKind.RETURN_STMT:
            facts["return_stmts"].append(node.location.line)

        elif node.kind == clang.cindex.CursorKind.CALL_EXPR:
            callee = node.referenced
            is_user_defined_in_main = False
            if callee and callee.location and callee.location.file:
                is_user_defined_in_main = callee.location.file.name == main_file_path

            if not is_user_defined_in_main:
                if callee and callee.spelling:
                    facts["function_calls"].add(callee.spelling)
                else:
                    name = node.spelling or node.displayname
                    if name:
                        facts["function_calls"].add(name)

            if (current_func_cursor is not None and callee is not None
                    and callee.get_usr() and current_func_cursor.get_usr()
                    and callee.get_usr() == current_func_cursor.get_usr()):
                facts["recursive_calls"].append(node.location.line)

    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        new_func_cursor = node
        for child in node.get_children():
            analyze_c_ast(child, facts, new_func_cursor, main_file_path)
    else:
        for child in node.get_children():
            analyze_c_ast(child, facts, current_func_cursor, main_file_path)
