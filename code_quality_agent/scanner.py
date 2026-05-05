"""Scanner — orchestrates all checkers for a file or directory."""

import os
from typing import Any, Dict, List

from .checkers import style_checker, security_checker, complexity_checker, duplicate_checker


def _collect_python_files(path: str) -> List[str]:
    """Return all ``*.py`` files under *path* (file or directory)."""
    if os.path.isfile(path):
        return [path] if path.endswith(".py") else []
    files = []
    for root, _dirs, filenames in os.walk(path):
        for name in filenames:
            if name.endswith(".py"):
                files.append(os.path.join(root, name))
    return sorted(files)


def scan(path: str, config: Dict[str, Any]) -> List[Dict]:
    """Scan *path* (file or directory) and return all issues."""
    python_files = _collect_python_files(path)
    if not python_files:
        return []

    issues: List[Dict] = []

    for filepath in python_files:
        issues.extend(style_checker.check_file(filepath, config))
        issues.extend(security_checker.check_file(filepath, config))
        issues.extend(complexity_checker.check_file(filepath, config))

    # Duplicate detection is cross-file, so we pass all files at once.
    issues.extend(duplicate_checker.check_files(python_files, config))

    return issues
