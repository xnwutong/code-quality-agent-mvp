"""Cyclomatic complexity checker.

Uses *radon* when available; falls back to a simple AST-based branch counter
so the tool remains functional even without radon installed.
"""

import ast
from typing import Any, Dict, List

try:
    from radon.complexity import cc_visit, ComplexityVisitor
    from radon.visitors import ComplexityVisitor as _CV
    _RADON_AVAILABLE = True
except ImportError:
    _RADON_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue(filename: str, line: int, col: int, code: str, message: str) -> Dict:
    return {
        "filename": filename,
        "line": line,
        "col": col,
        "code": code,
        "message": message,
        "checker": "complexity",
    }


# ---------------------------------------------------------------------------
# Fallback: simple AST branch counter
# ---------------------------------------------------------------------------

_BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Assert,
    ast.comprehension,
)


class _FunctionComplexityVisitor(ast.NodeVisitor):
    """Walk function bodies and count decision points."""

    def __init__(self):
        self.results: List[Dict] = []  # {"name", "lineno", "complexity"}

    def _count_branches(self, node: ast.AST) -> int:
        count = 1  # base complexity
        for child in ast.walk(node):
            if isinstance(child, _BRANCH_NODES):
                count += 1
            elif isinstance(child, ast.BoolOp):
                # each extra operand in `and`/`or` adds a branch
                count += len(child.values) - 1
        return count

    def visit_FunctionDef(self, node: ast.FunctionDef):
        complexity = self._count_branches(node)
        self.results.append(
            {"name": node.name, "lineno": node.lineno, "complexity": complexity}
        )
        # do NOT recurse — nested functions are counted separately
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child)

    visit_AsyncFunctionDef = visit_FunctionDef


def _ast_complexity(source: str) -> List[Dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    visitor = _FunctionComplexityVisitor()
    visitor.visit(tree)
    return visitor.results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_file(filepath: str, config: Dict[str, Any]) -> List[Dict]:
    """Return complexity issues for *filepath*."""
    cfg = config.get("complexity", {})
    if not cfg.get("enabled", True):
        return []

    threshold = cfg.get("max_complexity", 10)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return []

    issues: List[Dict] = []

    if _RADON_AVAILABLE:
        try:
            blocks = cc_visit(source)
            for block in blocks:
                if block.complexity > threshold:
                    issues.append(
                        _issue(
                            filepath,
                            block.lineno,
                            block.col_offset + 1 if hasattr(block, "col_offset") else 1,
                            "C001",
                            (
                                f"C001 '{block.name}' has cyclomatic complexity "
                                f"{block.complexity} (threshold: {threshold})"
                            ),
                        )
                    )
        except Exception:
            pass
    else:
        results = _ast_complexity(source)
        for r in results:
            if r["complexity"] > threshold:
                issues.append(
                    _issue(
                        filepath,
                        r["lineno"],
                        1,
                        "C001",
                        (
                            f"C001 '{r['name']}' has cyclomatic complexity "
                            f"{r['complexity']} (threshold: {threshold})"
                        ),
                    )
                )

    return issues
