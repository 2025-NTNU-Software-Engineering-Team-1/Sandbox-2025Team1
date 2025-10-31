import subprocess, shlex
import pathlib
import ast

try:
    import clang.cindex  # type: ignore
except ImportError:
    pass

from .constant import Language
from .utils import logger


def detect_include_args():
    args = []

    rdir = subprocess.check_output(["clang", "-print-resource-dir"], text=True).strip()
    args += [f"-I{pathlib.Path(rdir) / 'include'}"]

    # libstdc++ path (auto)
    cxx_inc = subprocess.check_output(
        ["g++", "-print-file-name=include"], text=True
    ).strip()
    args += [f"-I{cxx_inc}"]

    # try these path
    args += ["-I/usr/include", "-I/usr/include/x86_64-linux-gnu"]
    print(args)
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

    def __init__(self, success=True, message="OK"):
        self._success = success
        self.message = message

    def is_success(self):
        return self._success


class StaticAnalyzer:
    @staticmethod
    def analyze(
        submission_id: str,
        language: Language,
        rules: dict = None,
    ):
        """
        HERE is entrance
        main Analyzer
        """
        ## for debug
        source_code_path = pathlib.Path(submission_id).resolve()
        ## for real use
        # working_dir = Path(dispatcher_config.get_submission_config()["working_dir"])
        # source_code_path = (working_dir / submission_id / "src").resolve()

        logger().debug(f"Analysis: {source_code_path} (lang: {language})")

        if not isinstance(rules, dict):
            rules = {}

        try:
            if language == Language.PY:
                result = StaticAnalyzer._analyze_python(source_code_path, rules)

            elif language == Language.C or language == Language.CPP:
                if "clang" not in globals():
                    raise StaticAnalysisError(
                        "Libclang is not installed or import failed"
                    )
                result = StaticAnalyzer._analyze_c_cpp(
                    source_code_path, rules, language
                )

            else:
                logger().warning(f"Unsupported static analysis languages: {language}")
                result = AnalysisResult(success=True)  # default false

        except StaticAnalysisError:
            logger().error(f"Static Analyzer inner error", exc_info=True)
            raise

        except Exception as e:
            logger().error(
                f"An unexpected error occurred during static analysis: {e}",
                exc_info=True,
            )
            raise StaticAnalysisError(f"An unexpected error occurred: {e}") from e

        if result.is_success():
            logger().debug("Static analysis passed.")

        return result

    @staticmethod
    def _analyze_python(source_path: pathlib.Path, rules: dict):
        """
        for python use ast
        """
        main_py_path = source_path / "main.py"
        if not main_py_path.exists():
            raise StaticAnalysisError(
                f"Not found 'main.py'. Source path: {source_path}"
            )

        with open(main_py_path, "r") as f:
            content = f.read()

        # (1) Ast + facts result
        try:
            tree = ast.parse(content)
            visitor = PythonAstVisitor()
            visitor.visit(tree)
            facts = visitor.facts
        except SyntaxError as e:
            return AnalysisResult(
                success=False, message=f"Syntax Error could not analyze: {e}"
            )

        logger().debug(f"Python analysis facts: {facts}")

        # (2) fact vs rules
        violations = []

        # Check 1: Imports
        disallowed_imports = set(rules.get("disallow_imports", []))
        used_disallowed_imports = facts["imports"].intersection(disallowed_imports)
        if used_disallowed_imports:
            violations.append(
                f"\n[Violation] Using the forbidden method: {', '.join(used_disallowed_imports)}"
            )

        # Check 2: for and while loop
        disallowed_syntax = set(rules.get("disallow_syntax", []))

        if "for" in disallowed_syntax:
            for line_num in facts["for_loops"]:
                violations.append(f"\n[Violation] For Loop, line {line_num}")
        if "while" in disallowed_syntax:
            for line_num in facts["while_loops"]:
                violations.append(f"\n[Violation] While Loop, line {line_num}")
        if "recursive" in disallowed_syntax:
            for line_num in facts["recursive_calls"]:
                violations.append(f"\n[Violation] Recursive Call, line {line_num}")

        # Check 3: function call
        disallowed_functions = set(rules.get("disallow_functions", []))
        used_disallowed_functions = facts["function_calls"].intersection(
            disallowed_functions
        )
        if used_disallowed_functions:
            violations.append(
                f"\n[Violation] Using the forbidden method: {', '.join(used_disallowed_functions)}"
            )

        # (3) Result
        if violations:
            msg = f"Static analysis failed:{'; '.join(violations)}"
            logger().warning(msg)
            return AnalysisResult(success=False, message=msg)

        return AnalysisResult(success=True)

    @staticmethod
    def _analyze_c_cpp(source_path: pathlib.Path, rules: dict, language: Language):
        """
        for C/C++ use libclang
        """
        main_c_path = source_path / "main.c"  # C
        main_cpp_path = source_path / "main.cpp"  # C++

        # debug
        # print(main_c_path)
        # print(main_cpp_path)
        target_path = None
        if main_c_path.exists():
            target_path = main_c_path
        elif main_cpp_path.exists():
            target_path = main_cpp_path
        else:
            raise StaticAnalysisError(
                f"Not found 'main.c' or 'main.cpp'.  Source path: {source_path}"
            )
        # debug
        # print(target_path)

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
                options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )

        except clang.cindex.LibclangError as e:
            raise StaticAnalysisError(f"Libclang init failed: {e}")

        if not translation_unit:
            return AnalysisResult(
                success=False,
                message="[Syntax Error] Clang could not analyze",
            )

        facts = {
            "headers": set(),
            "function_calls": set(),
            "for_loops": [],
            "while_loops": [],
            "recursive_calls": [],
        }
        analyze_c_ast(translation_unit.cursor, facts, None, str(target_path))

        # for debug
        print(facts)

        logger().debug(f"C/C++ analysis facts: {facts}")

        # (2) fact vs rules
        violations = []

        # Check 1: header (.h)
        disallowed_headers = set(rules.get("disallow_headers", []))
        used_disallowed_headers = facts["headers"].intersection(disallowed_headers)
        if used_disallowed_headers:
            violations.append(
                # f"[Violation] Using the forbidden method: {', '.join(used_disallowed_headers)}"
                f"\n[Violation] Used Disallowed Headers: {', '.join(used_disallowed_headers)}"
            )

        # Check 2: for and while loop
        disallowed_syntax = set(rules.get("disallow_syntax", []))
        if "for" in disallowed_syntax:
            for line_num in facts["for_loops"]:
                violations.append(f"\n[Violation] For Loop, line {line_num}")
        if "while" in disallowed_syntax:
            for line_num in facts["while_loops"]:
                violations.append(f"\n[Violation] While Loop, line {line_num}")
        if "recursive" in disallowed_syntax:
            for line_num in facts["recursive_calls"]:
                violations.append(f"\n[Violation] Recursive Call, line {line_num}")

        # Check 3: function call
        disallowed_functions = set(rules.get("disallow_functions", []))
        used_disallowed_functions = facts["function_calls"].intersection(
            disallowed_functions
        )
        if used_disallowed_functions:
            violations.append(
                # f"[Violation] Using the forbidden method: {', '.join(used_disallowed_functions)}"
                f"\n[Violation] Used Disallowed Functions: {', '.join(used_disallowed_functions)}"
            )

        # (3) Result
        if violations:
            msg = f"Static analysis failed:{'; '.join(violations)}"
            logger().warning(msg)
            return AnalysisResult(success=False, message=msg)

        return AnalysisResult(success=True)


class PythonAstVisitor(ast.NodeVisitor):
    """
    for python analyze
    """

    def __init__(self):
        # log used "fact"
        self.facts = {
            "imports": set(),  # log moudle name
            "function_calls": set(),  # log func. name
            "for_loops": [],  # log line number
            "while_loops": [],  # log line number
            "recursive_calls": [],  # log line number
        }

        # use stack to trace recursive
        self.current_function_stack = []

    def visit_Import(self, node):
        """
        when import ...
        """
        for alias in node.names:
            self.facts["imports"].add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        when from ... import ...
        """
        if node.module:
            self.facts["imports"].add(node.module)
        self.generic_visit(node)

    def visit_For(self, node):
        """
        when for loop ...
        """
        self.facts["for_loops"].append(node.lineno)
        self.generic_visit(node)

    def visit_While(self, node):
        """
        when while loop ...
        """
        self.facts["while_loops"].append(node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """
        whlie visit func. define
        ex: def dfs():
        """
        current_function_name = node.name
        self.current_function_stack.append(current_function_name)
        self.generic_visit(node)
        self.current_function_stack.pop()

    def visit_Call(self, node):
        """
        whem func. call
        ex: dfs()
        """
        function_name_called = None

        if isinstance(node.func, ast.Name):
            function_name_called = node.func.id
            self.facts["function_calls"].add(function_name_called)
        if (
            self.current_function_stack
            and function_name_called == self.current_function_stack[-1]
        ):
            # Is recursive
            # log line number
            self.facts["recursive_calls"].append(node.lineno)

        self.generic_visit(node)


def analyze_c_ast(node, facts, current_func_cursor, main_file_path: str):
    # 1) include
    if node.kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE:
        if node.location.file and node.location.file.name == main_file_path:
            facts["headers"].add(node.displayname)
        return

    in_main = (
        node.location
        and node.location.file
        and node.location.file.name == main_file_path
    )

    if in_main:
        if node.kind in (
            clang.cindex.CursorKind.FOR_STMT,
            clang.cindex.CursorKind.CXX_FOR_RANGE_STMT,
        ):
            facts["for_loops"].append(node.location.line)

        elif node.kind == clang.cindex.CursorKind.WHILE_STMT:
            facts["while_loops"].append(node.location.line)

        elif node.kind == clang.cindex.CursorKind.CALL_EXPR:
            callee = node.referenced
            if callee and callee.spelling:
                facts["function_calls"].add(callee.spelling)
            else:
                name = node.spelling or node.displayname
                if name:
                    facts["function_calls"].add(name)

            if (
                current_func_cursor is not None
                and callee is not None
                and callee.get_usr()
                and current_func_cursor.get_usr()
                and callee.get_usr() == current_func_cursor.get_usr()
            ):
                facts["recursive_calls"].append(node.location.line)

    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        new_func_cursor = node
        for child in node.get_children():
            analyze_c_ast(child, facts, new_func_cursor, main_file_path)
    else:
        for child in node.get_children():
            analyze_c_ast(child, facts, current_func_cursor, main_file_path)
