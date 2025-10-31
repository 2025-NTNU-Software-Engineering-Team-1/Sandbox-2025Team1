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
    def analyze(source_code_path: pathlib.Path, language: Language, rules: dict = None):
        """
        HERE is entrance
        main Analyzer
        """
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
                result = StaticAnalyzer._analyze_c_cpp(source_code_path, rules)

            else:
                logger().warning(f"Unsupported static analysis languages: {language}")
                result = AnalysisResult(success=False)  # default false

        except StaticAnalysisError as e:
            logger().error(f"Static Analyzer inner error : {e}")
            return AnalysisResult(
                success=False, message="Internal error in the Analyzer (JE)"
            )
        except Exception as e:
            logger().error(
                f"An unexpected error occurred during static analysis: {e}",
                exc_info=True,
            )
            return AnalysisResult(
                success=False,
                message="An unexpected error occurred during static analysis (JE)",
            )

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
                f"[Violation] Using the forbidden method: {', '.join(used_disallowed_imports)}"
            )

        # Check 2: for and while loop
        disallowed_syntax = set(rules.get("disallow_syntax", []))
        if "for" in disallowed_syntax and facts["for_loops"]:
            violations.append(
                f"[Violation] Using the forbidden method: (In line {facts['for_loops'][0]})"
            )
        if "while" in disallowed_syntax and facts["while_loops"]:
            violations.append(
                f"[Violation] Using the forbidden method: (In line {facts['while_loops'][0]})"
            )

        # Check 3: function call
        disallowed_functions = set(rules.get("disallow_functions", []))
        used_disallowed_functions = facts["function_calls"].intersection(
            disallowed_functions
        )
        if used_disallowed_functions:
            violations.append(
                f"[Violation] Using the forbidden method: {', '.join(used_disallowed_functions)}"
            )

        # (3) Result
        if violations:
            msg = f"Static analysis failed:{'; '.join(violations)}"
            logger().warning(msg)
            return AnalysisResult(success=False, message=msg)

        return AnalysisResult(success=True)

    @staticmethod
    def _analyze_c_cpp(source_path: pathlib.Path, rules: dict):
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
            # need to format str(pathlib.Path)，clang does not accept Path Obj.
            translation_unit = index.parse(
                str(target_path), args=["-std=c++17"] + detect_include_args()
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
            "for_loops": [],
            "while_loops": [],
            "function_calls": set(),
            "recursive_calls": [],
        }
        analyze_c_ast(translation_unit.cursor, facts, None, str(target_path))

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
                f"[Violation] used_disallowed_headers {', '.join(used_disallowed_headers)}"
            )

        # Check 2: for and while loop
        disallowed_syntax = set(rules.get("disallow_syntax", []))
        if "for" in disallowed_syntax and facts["for_loops"]:
            violations.append(
                # f"[Violation] Using the forbidden method: (In line {facts['for_loops'][0]})"
                f"[Violation] for_loop In line {facts['for_loops'][0]}"
            )
        if "while" in disallowed_syntax and facts["while_loops"]:
            violations.append(
                # f"[Violation] Using the forbidden method: (In line {facts['while_loops'][0]})"
                f"[Violation] while_loop In line {facts['while_loops'][0]}"
            )

        # Check 3: function call
        disallowed_functions = set(rules.get("disallow_functions", []))
        used_disallowed_functions = facts["function_calls"].intersection(
            disallowed_functions
        )
        if used_disallowed_functions:
            violations.append(
                # f"[Violation] Using the forbidden method: {', '.join(used_disallowed_functions)}"
                f"[Violation] used_disallowed_functions {', '.join(used_disallowed_functions)}"
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
            "for_loops": [],  # log line number
            "while_loops": [],  # log line number
            "recursive_calls": [],  # log line number
            "imports": set(),  # log moudle name
            "function_calls": set(),  # log func. name
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
        # 1. push now func
        current_function_name = node.name
        self.current_function_stack.append(current_function_name)

        # 2. keep going visit this func.
        self.generic_visit(node)

        # 3. finish then pop
        self.current_function_stack.pop()

    def visit_Call(self, node):
        """
        whem func. call
        ex: dfs()
        """
        function_name_called = None

        if isinstance(node.func, ast.Name):
            # e.g., "print('hello')", "eval('1+1')"
            function_name_called = node.func.id
            self.facts["function_calls"].add(function_name_called)

        # check stack is recursive or not
        # check stack is empty or not
        # check the top of stack
        if (
            self.current_function_stack
            and function_name_called == self.current_function_stack[-1]
        ):
            # Is recursive
            # log line number
            self.facts["recursive_calls"].append(node.lineno)

        self.generic_visit(node)


# ... (在 static_analysis.py 中)


def analyze_c_ast(node, facts, current_function_name: str | None, main_file_path: str):
    """
    for c/c++ analyze
    """

    if node.location and node.location.file:
        if node.location.file.name != main_file_path:
            return
    # ---------------------------------

    if node.kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE:
        # e.g., #include <stdio.h>
        facts["headers"].add(node.displayname)  # "stdio.h"

    elif node.kind == clang.cindex.CursorKind.FOR_STMT:
        facts["for_loops"].append(node.location.line)

    elif node.kind == clang.cindex.CursorKind.WHILE_STMT:
        facts["while_loops"].append(node.location.line)

    elif node.kind == clang.cindex.CursorKind.CALL_EXPR:
        called_name = node.displayname
        facts["function_calls"].add(called_name)

        if current_function_name is not None and called_name == current_function_name:
            facts["recursive_calls"].append(node.location.line)

    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        new_func_name = node.displayname
        for child in node.get_children():

            analyze_c_ast(child, facts, new_func_name, main_file_path)
    else:
        for child in node.get_children():

            analyze_c_ast(child, facts, current_function_name, main_file_path)
