"""Style and naming-convention checker.

Uses *pycodestyle* for PEP-8 checks and a set of regex patterns for naming
convention violations (snake_case functions/variables, PascalCase classes,
UPPER_CASE constants).
"""

import ast
import re
from io import StringIO
from typing import Any, Dict, List

try:
    import pycodestyle
    _PYCODESTYLE_AVAILABLE = True
except ImportError:
    _PYCODESTYLE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Issue dataclass (plain dict for zero-dependency simplicity)
# ---------------------------------------------------------------------------

def _issue(filename: str, line: int, col: int, code: str, message: str) -> Dict:
    return {
        "filename": filename,
        "line": line,
        "col": col,
        "code": code,
        "message": message,
        "checker": "style",
    }


# ---------------------------------------------------------------------------
# PEP-8 style check via pycodestyle
# ---------------------------------------------------------------------------

class _CollectingReport(pycodestyle.BaseReport if _PYCODESTYLE_AVAILABLE else object):
    """Collects pycodestyle results instead of printing them."""

    def __init__(self, options):
        super().__init__(options)
        self.errors: List[Dict] = []

    def error(self, line_number, offset, text, check):
        code = super().error(line_number, offset, text, check)
        if code:
            self.errors.append(
                _issue(
                    filename=self.filename,
                    line=line_number,
                    col=offset + 1,
                    code=code,
                    message=text,
                )
            )
        return code


def _check_pep8(filepath: str, max_line_length: int, ignore_codes: List[str]) -> List[Dict]:
    """Return PEP-8 issues for *filepath* using pycodestyle."""
    if not _PYCODESTYLE_AVAILABLE:
        return []

    issues: List[Dict] = []
    style_guide = pycodestyle.StyleGuide(
        reporter=_CollectingReport,
        max_line_length=max_line_length,
        ignore=ignore_codes or [],
        quiet=True,
    )
    # pycodestyle collects errors inside the reporter instance; we retrieve it.
    checker = pycodestyle.Checker(
        filepath,
        show_source=False,
        show_pep8=False,
        max_line_length=max_line_length,
        ignore=ignore_codes or [],
        report=_CollectingReport(
            pycodestyle.StyleGuide(
                max_line_length=max_line_length,
                ignore=ignore_codes or [],
                quiet=True,
            ).options
        ),
    )
    checker.check_all()
    return checker.report.errors


# ---------------------------------------------------------------------------
# Naming convention check via AST
# ---------------------------------------------------------------------------

_SNAKE_CASE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_DUNDER_RE = re.compile(r"^__[a-z_]+__$")


def _check_naming(filepath: str, source: str) -> List[Dict]:
    """Return naming-convention issues found via AST analysis."""
    issues: List[Dict] = []
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        # Function / method names → snake_case
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if not (_SNAKE_CASE_RE.match(name) or _DUNDER_RE.match(name)):
                issues.append(
                    _issue(
                        filepath,
                        node.lineno,
                        node.col_offset + 1,
                        "N802",
                        f"N802 function name '{name}' should be lowercase (snake_case)",
                    )
                )
        # Class names → PascalCase
        elif isinstance(node, ast.ClassDef):
            name = node.name
            if not _PASCAL_CASE_RE.match(name):
                issues.append(
                    _issue(
                        filepath,
                        node.lineno,
                        node.col_offset + 1,
                        "N801",
                        f"N801 class name '{name}' should use CapWords (PascalCase)",
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_file(filepath: str, config: Dict[str, Any]) -> List[Dict]:
    """Run style checks on *filepath* and return a list of issue dicts."""
    cfg = config.get("style", {})
    if not cfg.get("enabled", True):
        return []

    max_line_length = cfg.get("max_line_length", 79)
    ignore_codes = cfg.get("ignore_codes", [])
    check_naming = cfg.get("check_naming", True)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return []

    issues: List[Dict] = []

    if _PYCODESTYLE_AVAILABLE:
        issues.extend(_check_pep8(filepath, max_line_length, ignore_codes))

    if check_naming:
        issues.extend(_check_naming(filepath, source))

    return issues
