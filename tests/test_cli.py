"""Integration tests for main.py CLI"""

import os
import sys
import tempfile
import pytest

# Make the root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import main


_CLEAN_SOURCE = """\
def add(a, b):
    return a + b


class Calculator:
    def multiply(self, x, y):
        return x * y
"""

_DIRTY_SOURCE = """\
password = "s3cr3t_pw"

def myBadFunc():
    pass
"""


def _write_tmp(content: str) -> str:
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    )
    fh.write(content)
    fh.close()
    return fh.name


def test_clean_file_exits_zero():
    path = _write_tmp(_CLEAN_SOURCE)
    try:
        rc = main([path, "--no-color"])
        assert rc == 0
    finally:
        os.unlink(path)


def test_dirty_file_exits_one():
    path = _write_tmp(_DIRTY_SOURCE)
    try:
        rc = main([path, "--no-color"])
        assert rc == 1
    finally:
        os.unlink(path)


def test_no_security_flag_disables_security():
    """--no-security should suppress security issues."""
    path = _write_tmp('password = "hunter2"\n')
    try:
        # Only security issue; with --no-security it might be clean
        rc = main([path, "--no-color", "--no-security", "--no-style", "--no-complexity", "--no-duplicates"])
        assert rc == 0
    finally:
        os.unlink(path)


def test_max_complexity_override():
    """--max-complexity 1 should flag even a simple function."""
    source = "def foo(x):\n    if x:\n        return 1\n    return 0\n"
    path = _write_tmp(source)
    try:
        rc = main([path, "--no-color", "--no-style", "--no-security", "--no-duplicates",
                   "--max-complexity", "1"])
        assert rc == 1
    finally:
        os.unlink(path)
