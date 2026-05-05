"""Tests for code_quality_agent.checkers.complexity_checker"""

import os
import tempfile
import pytest
from code_quality_agent.checkers import complexity_checker

_BASE_CONFIG = {
    "complexity": {
        "enabled": True,
        "max_complexity": 5,
    }
}


def _write_tmp(content: str) -> str:
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    )
    fh.write(content)
    fh.close()
    return fh.name


def test_simple_function_not_flagged():
    source = "def add(a, b):\n    return a + b\n"
    path = _write_tmp(source)
    try:
        issues = complexity_checker.check_file(path, _BASE_CONFIG)
        assert issues == []
    finally:
        os.unlink(path)


def test_complex_function_flagged():
    # Build a function with many branches to exceed threshold=5
    branches = "\n".join(
        f"    if x == {i}:\n        pass" for i in range(7)
    )
    source = f"def complex_func(x):\n{branches}\n    return x\n"
    path = _write_tmp(source)
    try:
        issues = complexity_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "C001" in codes
    finally:
        os.unlink(path)


def test_checker_disabled():
    branches = "\n".join(
        f"    if x == {i}:\n        pass" for i in range(7)
    )
    source = f"def complex_func(x):\n{branches}\n    return x\n"
    config = {"complexity": {"enabled": False, "max_complexity": 5}}
    path = _write_tmp(source)
    try:
        issues = complexity_checker.check_file(path, config)
        assert issues == []
    finally:
        os.unlink(path)


def test_threshold_respected():
    """With a very high threshold nothing should be flagged."""
    branches = "\n".join(
        f"    if x == {i}:\n        pass" for i in range(7)
    )
    source = f"def complex_func(x):\n{branches}\n    return x\n"
    config = {"complexity": {"enabled": True, "max_complexity": 100}}
    path = _write_tmp(source)
    try:
        issues = complexity_checker.check_file(path, config)
        assert issues == []
    finally:
        os.unlink(path)
