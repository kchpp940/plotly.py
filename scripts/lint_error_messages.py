#!/usr/bin/env python3
"""Lint script to detect raw multi-line error strings bypassing build_error_message()."""

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

TARGET_EXCEPTIONS = {
    "ValueError",
    "ImportError",
    "RuntimeError",
    "EnvironmentError",
    "TypeError",
    "KeyError",
}

DEFAULT_TARGET_FILES = [
    "_plotly_utils/basevalidators.py",
    "plotly/io/_kaleido.py",
    "plotly/io/_orca.py",
    "plotly/io/_renderers.py",
    "plotly/io/_json.py",
    "plotly/io/_base_renderers.py",
    "plotly/express/_core.py",
    "plotly/express/__init__.py",
    "plotly/figure_factory/__init__.py",
    "plotly/missing_anywidget.py",
]

MIN_STRING_LENGTH = 80


@dataclass
class Violation:
    file_path: str
    line_number: int
    error_type: str
    snippet: str
    suggestion: str = "Use build_error_message() instead of raw multi-line string"

    def format(self) -> str:
        snippet_one_line = self.snippet.replace("\n", "\\n")[:120]
        return (
            f"{self.file_path}:{self.line_number}: "
            f"E001 raw multi-line error string for {self.error_type} "
            f"-- {self.suggestion}\n"
            f"  {snippet_one_line}"
        )


def _node_is_build_error_message(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id == "build_error_message"
        if isinstance(func, ast.Attribute):
            return func.attr == "build_error_message"
    return False


def _contains_build_error_message(node: ast.AST) -> bool:
    if _node_is_build_error_message(node):
        return True
    for child in ast.iter_child_nodes(node):
        if _contains_build_error_message(child):
            return True
    return False


def _extract_string_snippet(node: ast.AST, source_lines: List[str]) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                parts.append(val.value)
            elif isinstance(val, ast.FormattedValue):
                parts.append("{...}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _extract_string_snippet(node.left, source_lines)
        right = _extract_string_snippet(node.right, source_lines)
        if left is not None and right is not None:
            return left + right
        if left is not None:
            return left
        if right is not None:
            return right
    start_line = getattr(node, "lineno", None)
    end_line = getattr(node, "end_lineno", None)
    if start_line is not None and end_line is not None and start_line <= len(source_lines):
        start_col = getattr(node, "col_offset", 0)
        end_col = getattr(node, "end_col_offset", None)
        lines = source_lines[start_line - 1 : end_line]
        if lines:
            if len(lines) == 1 and end_col is not None:
                return lines[0][start_col:end_col]
            result = lines[0][start_col:] if lines else ""
            for line in lines[1:-1]:
                result += "\n" + line
            if len(lines) > 1 and end_col is not None:
                result += "\n" + lines[-1][:end_col]
            return result
    return None


def _is_multiline_string_arg(node: ast.AST, source_lines: List[str]) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is not None and end_lineno is not None and end_lineno > lineno:
            return True
        if "\n" in node.value:
            return True
        if len(node.value) >= MIN_STRING_LENGTH:
            return True
        return False
    if isinstance(node, ast.JoinedStr):
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is not None and end_lineno is not None and end_lineno > lineno:
            return True
        snippet = _extract_string_snippet(node, source_lines)
        if snippet and "\n" in snippet:
            return True
        if snippet and len(snippet) >= MIN_STRING_LENGTH:
            return True
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is not None and end_lineno is not None and end_lineno > lineno:
            return True
        return _is_multiline_string_arg(node.left, source_lines) or _is_multiline_string_arg(
            node.right, source_lines
        )
    if isinstance(node, ast.Call):
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is not None and end_lineno is not None and end_lineno > lineno:
            for arg in node.args:
                if _is_multiline_string_arg(arg, source_lines):
                    return True
            for kw in node.keywords:
                if _is_multiline_string_arg(kw.value, source_lines):
                    return True
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    if lineno is not None and end_lineno is not None and end_lineno > lineno:
        return True
    return False


def _get_error_type(node: ast.Call) -> Optional[str]:
    func = node.func
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    else:
        return None
    if name in TARGET_EXCEPTIONS:
        return name
    return None


def scan_file(file_path: Path) -> List[Violation]:
    violations: List[Violation] = []
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    source_lines = source.splitlines()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        exc = node.exc
        if not isinstance(exc, ast.Call):
            continue

        error_type = _get_error_type(exc)
        if error_type is None:
            continue

        if not exc.args:
            continue

        first_arg = exc.args[0]

        if _contains_build_error_message(first_arg):
            continue

        if _is_multiline_string_arg(first_arg, source_lines):
            snippet = _extract_string_snippet(first_arg, source_lines) or ""
            violations.append(
                Violation(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    error_type=error_type,
                    snippet=snippet,
                )
            )

    return violations


def scan_files(file_paths: List[Path]) -> List[Violation]:
    all_violations: List[Violation] = []
    for file_path in file_paths:
        all_violations.extend(scan_file(file_path))
    return all_violations


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint for raw multi-line error strings bypassing build_error_message()"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to scan (defaults to 10 target modules)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent

    if args.paths:
        target_paths: List[Path] = []
        for p in args.paths:
            path = Path(p)
            if not path.is_absolute():
                path = repo_root / path
            if path.is_file():
                target_paths.append(path)
            elif path.is_dir():
                target_paths.extend(sorted(path.rglob("*.py")))
    else:
        target_paths = [repo_root / f for f in DEFAULT_TARGET_FILES]

    violations = scan_files(target_paths)

    for v in violations:
        print(v.format())

    if violations:
        print(f"\nFound {len(violations)} violation(s).")
        return 1

    print("No violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
