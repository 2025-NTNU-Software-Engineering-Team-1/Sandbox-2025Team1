import subprocess, shlex
import pathlib
import ast
import json

try:
    import clang.cindex  # type: ignore
except ImportError:
    pass

from dispatcher import config as dispatcher_config
from .constant import Language
from .utils import logger


def detect_include_args():
    args = []

    rdir = subprocess.check_output(["clang", "-print-resource-dir"],
                                   text=True).strip()
    args += [f"-I{pathlib.Path(rdir) / 'include'}"]

    # libstdc++ path (auto)
    cxx_inc = subprocess.check_output(["g++", "-print-file-name=include"],
                                      text=True).strip()
    args += [f"-I{cxx_inc}"]

    # try these path
    args += ["-I/usr/include", "-I/usr/include/x86_64-linux-gnu"]

    return args


class StaticAnalysisError(Exception):
    """
    for debug
    """

    pass


class AnalysisResult:
    """
    write analysis report
    """

    def __init__(self, success=True, message="", rules="", facts=""):
        self._success = success
        self.message = message
        self.json_result = {}

    def is_success(self):
        return self._success

    def set_violations(self, structured_violations: dict):
        # json format
        self.json_result = structured_violations

        msg = "\n-------------------------- Static Analysis Result -------------------------"

        for item, lines in structured_violations.items():
            if item == "model":
                continue
            if not lines:
                continue
            msg += f"\n [Category: {item}]"
            for line in lines:
                msg += f"\n    Line {line['line']:<4} : {line['content']}"

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
    ):
        """
        HERE is entrance
        main Analyzer
        """
        ## for debug
        # source_code_path = pathlib.Path(submission_id)
        # source_code_path = (source_code_path / "src").resolve()
        ## for real use
        submission_cfg = dispatcher_config.get_submission_config()
        working_dir = pathlib.Path(submission_cfg["working_dir"])
        source_code_path = (working_dir / submission_id / "src").resolve()

        logger().debug(f"Analysis: {source_code_path} (lang: {language})")
        if not isinstance(rules, dict):
            rules = {}
        try:
            if language == Language.PY:
                self._analyze_python(source_code_path, rules)

            elif language == Language.C or language == Language.CPP:
                if "clang" not in globals():
                    raise StaticAnalysisError(
                        "Libclang is not installed or import failed")
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

    def _analyze_python(self, source_path: pathlib.Path, rules: dict):
        """
        for python use ast
        """
        main_py_path = source_path / "main.py"
        if not main_py_path.exists():
            raise StaticAnalysisError(
                f"Not found 'main.py'. Source path: {source_path}")
        with open(main_py_path, "r") as f:
            content = f.read()

        # (1) Ast + facts result
        try:
            tree = ast.parse(content)

            def_visitor = DefinitionVisitor()
            def_visitor.visit(tree)

            global_funcs = def_visitor.global_functions
            classes_info = def_visitor.defined_classes

            visitor = PythonAstVisitor(global_functions=global_funcs,
                                       defined_classes=classes_info)
            visitor.visit(tree)
            visitor.detect_cycles()
            facts = visitor.facts
        except SyntaxError as e:
            self.result._success = False
            self.result.message += f"\nSyntax Error could not analyze:\n{e}"
            return self.result
        logger().debug(f"Python analysis facts: {facts}")
        # (2) fact vs rules
        violations_dict = self.get_violations(facts, rules, Language.PY)
        # (3) Result
        if violations_dict:
            logger().debug("Static analysis failed.")
            self.result._success = False
            self.result.set_violations(violations_dict)
        else:
            self.result._success = True
            self.result.message += f"\nGOOD JOB, passed static analysis."

        return self.result

    def _analyze_c_cpp(self, source_path: pathlib.Path, rules: dict,
                       language: Language):
        """
        for C/C++ use libclang
        """
        main_c_path = source_path / "main.c"  # C
        main_cpp_path = source_path / "main.cpp"  # C++

        target_path = None
        if main_c_path.exists():
            target_path = main_c_path
        elif main_cpp_path.exists():
            target_path = main_cpp_path
        else:
            raise StaticAnalysisError(
                f"Not found 'main.c' or 'main.cpp'.  Source path: {source_path}"
            )

        # (1) Ast + facts result
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
            self.result.message += "[Syntax Error] Clang could not analyze"
            return self.result

        visitor = CppAstVisitor(str(target_path))
        visitor.visit(translation_unit.cursor)
        visitor.detect_cycles()

        facts = visitor.facts
        logger().debug(f"C/C++ analysis facts: {facts}")

        violations_dict = self.get_violations(facts, rules, language)

        # (3) Result
        if violations_dict:
            logger().debug("Static analysis failed.")
            self.result._success = False
            self.result.set_violations(violations_dict)
        else:
            self.result._success = True
            self.result.message += f"\nGOOD JOB, passed static analysis."

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
            "headers": [],  # C/CPP
            "imports": [],  # PY
            "functions": [],
        }

        # import / header check
        if language == Language.PY:
            violations_structure["imports"] = self._check_items(
                facts["imports"], rules.get("imports", []), model)
            del violations_structure["headers"]  # PY not use headers
        else:
            violations_structure["headers"] = self._check_items(
                facts["headers"], rules.get("headers", []), model)
            del violations_structure["imports"]  # C/CPP not use imports

        # function call check
        violations_structure["functions"] = self._check_items(
            facts["function_calls"], rules.get("functions", []), model)
        # syntax check
        violations_structure["syntax"] = self._check_items(
            facts["syntax"], rules.get("syntax", []), model)

        has_violations = False
        for key, items in violations_structure.items():
            if key == "model":
                continue
            if items:
                has_violations = True
                break
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

        return violations


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
        # log used "fact"
        self.facts = {"imports": [], "function_calls": [], "syntax": []}

        # for recursive check
        self.current_function_stack = []
        self.global_functions = global_functions
        self.defined_classes = defined_classes
        self.variable_types = {}
        self.call_graph = {}

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
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.facts["imports"].append({
                "name": node.module,
                "line": node.lineno
            })
        self.generic_visit(node)

    def visit_For(self, node):
        self.facts["syntax"].append({"name": "for", "line": node.lineno})
        self.generic_visit(node)

    def visit_While(self, node):
        self.facts["syntax"].append({"name": "while", "line": node.lineno})
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
                    # simple method call within class
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
