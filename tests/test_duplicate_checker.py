"""Tests for code_quality_agent.checkers.duplicate_checker"""

import os
import tempfile
import pytest
from code_quality_agent.checkers import duplicate_checker

_BASE_CONFIG = {
    "duplicates": {
        "enabled": True,
        "min_lines": 4,
        "min_duplicate_count": 2,
    }
}

_BLOCK = """\
def helper(x):
    result = x * 2
    result = result + 1
    return result
"""


def _write_tmp(content: str) -> str:
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    )
    fh.write(content)
    fh.close()
    return fh.name


def test_no_duplicates_in_unique_files():
    path1 = _write_tmp("def foo():\n    return 1\n")
    path2 = _write_tmp("def bar():\n    return 2\n")
    try:
        issues = duplicate_checker.check_files([path1, path2], _BASE_CONFIG)
        assert issues == []
    finally:
        os.unlink(path1)
        os.unlink(path2)


def test_duplicate_block_across_files():
    path1 = _write_tmp(_BLOCK)
    path2 = _write_tmp(_BLOCK)
    try:
        issues = duplicate_checker.check_files([path1, path2], _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "D001" in codes
    finally:
        os.unlink(path1)
        os.unlink(path2)


def test_duplicate_block_within_same_file():
    content = _BLOCK + "\n" + _BLOCK
    path = _write_tmp(content)
    try:
        issues = duplicate_checker.check_files([path], _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "D001" in codes
    finally:
        os.unlink(path)


def test_checker_disabled():
    path1 = _write_tmp(_BLOCK)
    path2 = _write_tmp(_BLOCK)
    config = {"duplicates": {"enabled": False, "min_lines": 4, "min_duplicate_count": 2}}
    try:
        issues = duplicate_checker.check_files([path1, path2], config)
        assert issues == []
    finally:
        os.unlink(path1)
        os.unlink(path2)


def test_block_smaller_than_min_lines_not_flagged():
    """Blocks shorter than min_lines should not be flagged even if identical."""
    short_block = "x = 1\ny = 2\n"
    path1 = _write_tmp(short_block)
    path2 = _write_tmp(short_block)
    # min_lines=10 means the 2-line block is too short
    config = {"duplicates": {"enabled": True, "min_lines": 10, "min_duplicate_count": 2}}
    try:
        issues = duplicate_checker.check_files([path1, path2], config)
        assert issues == []
    finally:
        os.unlink(path1)
        os.unlink(path2)
