"""Security vulnerability scanner.

Detects:
* Hardcoded secrets — passwords, API keys, tokens, and similar credentials
  assigned as string literals.
* SQL injection risks — string formatting / concatenation used to build
  SQL queries rather than parameterised queries.
"""

import ast
import re
import tokenize
from io import StringIO
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _issue(filename: str, line: int, col: int, code: str, message: str) -> Dict:
    return {
        "filename": filename,
        "line": line,
        "col": col,
        "code": code,
        "message": message,
        "checker": "security",
    }


# ---------------------------------------------------------------------------
# Hardcoded-secrets detection
# ---------------------------------------------------------------------------

# Variable / attribute names that commonly hold credentials.
_SECRET_NAME_RE = re.compile(
    r"(password|passwd|pwd|secret|api[_-]?key|apikey|auth[_-]?token|"
    r"access[_-]?token|private[_-]?key|client[_-]?secret|db[_-]?pass|"
    r"database[_-]?password)",
    re.IGNORECASE,
)

# Patterns that indicate a value is a placeholder, not a real secret.
_PLACEHOLDER_PATTERNS = [
    re.compile(r"^$"),                        # empty string
    re.compile(r"^your[_\-]", re.IGNORECASE),  # your_password / your-key
    re.compile(r"^<.*>$"),                    # <placeholder>
    re.compile(r"^\$\{.*\}$"),               # ${VAR}
    re.compile(r"^%.*%$"),                   # %placeholder%
    re.compile(r"^x+$", re.IGNORECASE),      # xxx / XXXX
    re.compile(r"^dummy", re.IGNORECASE),    # dummy*
    re.compile(r"^example", re.IGNORECASE),  # example*
    re.compile(r"^changeme$", re.IGNORECASE),
    re.compile(r"^placeholder", re.IGNORECASE),
    re.compile(r"^todo$", re.IGNORECASE),
    re.compile(r"^fixme$", re.IGNORECASE),
    re.compile(r"^\*+$"),                    # ****
]


def _is_placeholder(val: str) -> bool:
    stripped = val.strip()
    return any(p.match(stripped) for p in _PLACEHOLDER_PATTERNS)


class _SecretVisitor(ast.NodeVisitor):
    """Walk an AST looking for hardcoded secrets."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: List[Dict] = []

    def _check_name_value(self, name: str, value_node: ast.expr, lineno: int, col: int):
        if not _SECRET_NAME_RE.search(name):
            return
        # Only flag string literals
        if not isinstance(value_node, ast.Constant) or not isinstance(value_node.value, str):
            return
        val = value_node.value
        if not val or _is_placeholder(val):
            return
        self.issues.append(
            _issue(
                self.filepath,
                lineno,
                col + 1,
                "S001",
                f"S001 possible hardcoded secret in variable '{name}'",
            )
        )

    # assignment: password = "s3cr3t"
    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_name_value(target.id, node.value, node.lineno, node.col_offset)
            elif isinstance(target, ast.Attribute):
                self._check_name_value(target.attr, node.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    # keyword argument: connect(password="s3cr3t")
    def visit_Call(self, node: ast.Call):
        for kw in node.keywords:
            if kw.arg:
                self._check_name_value(kw.arg, kw.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    # annotated assignment: password: str = "s3cr3t"
    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.value and isinstance(node.target, ast.Name):
            self._check_name_value(node.target.id, node.value, node.lineno, node.col_offset)
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# SQL-injection risk detection
# ---------------------------------------------------------------------------

# Patterns in source text that suggest unsafe SQL construction.
_SQL_KEYWORD_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b",
    re.IGNORECASE,
)
_FORMAT_SQL_RE = re.compile(
    r"""
    (?:f["']|["'].*?["']\s*%\s*\(|["'].*?["']\s*\.\s*format\s*\()
    .*?
    (?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


class _SQLVisitor(ast.NodeVisitor):
    """Walk an AST looking for SQL injection patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: List[Dict] = []

    def _is_sql_string(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return bool(_SQL_KEYWORD_RE.search(node.value))
        return False

    def _flag(self, lineno: int, col: int):
        self.issues.append(
            _issue(
                self.filepath,
                lineno,
                col + 1,
                "S002",
                "S002 possible SQL injection: SQL query built with string formatting",
            )
        )

    # f-string containing SQL keyword
    def visit_JoinedStr(self, node: ast.JoinedStr):
        # Check if the f-string contains any SQL keyword in its string parts
        parts = [
            v.value
            for v in node.values
            if isinstance(v, ast.Constant) and isinstance(v.value, str)
        ]
        combined = " ".join(parts)
        if _SQL_KEYWORD_RE.search(combined):
            self._flag(node.lineno, node.col_offset)
        self.generic_visit(node)

    # "SELECT ... " % (var,), "SELECT ...".format(var), or "SELECT ..." + var
    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, ast.Mod) and self._is_sql_string(node.left):
            self._flag(node.lineno, node.col_offset)
        elif isinstance(node.op, ast.Add):
            if self._is_sql_string(node.left) or self._is_sql_string(node.right):
                self._flag(node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # "SELECT ...".format(...)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and self._is_sql_string(node.func.value)
        ):
            self._flag(node.lineno, node.col_offset)
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_file(filepath: str, config: Dict[str, Any]) -> List[Dict]:
    """Run security checks on *filepath* and return a list of issue dicts."""
    cfg = config.get("security", {})
    if not cfg.get("enabled", True):
        return []

    check_secrets = cfg.get("check_hardcoded_secrets", True)
    check_sql = cfg.get("check_sql_injection", True)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return []

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    issues: List[Dict] = []

    if check_secrets:
        visitor = _SecretVisitor(filepath)
        visitor.visit(tree)
        issues.extend(visitor.issues)

    if check_sql:
        visitor2 = _SQLVisitor(filepath)
        visitor2.visit(tree)
        issues.extend(visitor2.issues)

    return issues
