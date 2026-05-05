"""Tests for code_quality_agent.checkers.style_checker"""

import os
import tempfile
import pytest
from code_quality_agent.checkers import style_checker

_BASE_CONFIG = {
    "style": {
        "enabled": True,
        "max_line_length": 79,
        "ignore_codes": [],
        "check_naming": True,
    }
}


def _write_tmp(content: str) -> str:
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    )
    fh.write(content)
    fh.close()
    return fh.name


def test_no_issues_on_clean_code():
    source = "def my_func():\n    return 1\n"
    path = _write_tmp(source)
    try:
        issues = style_checker.check_file(path, _BASE_CONFIG)
        naming_issues = [i for i in issues if i["code"].startswith("N")]
        assert naming_issues == []
    finally:
        os.unlink(path)


def test_camelcase_function_flagged():
    source = "def myFunction():\n    pass\n"
    path = _write_tmp(source)
    try:
        issues = style_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "N802" in codes
    finally:
        os.unlink(path)


def test_non_pascal_class_flagged():
    source = "class my_class:\n    pass\n"
    path = _write_tmp(source)
    try:
        issues = style_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "N801" in codes
    finally:
        os.unlink(path)


def test_pascal_class_clean():
    source = "class MyClass:\n    pass\n"
    path = _write_tmp(source)
    try:
        issues = style_checker.check_file(path, _BASE_CONFIG)
        naming_issues = [i for i in issues if i["code"].startswith("N")]
        assert naming_issues == []
    finally:
        os.unlink(path)


def test_checker_disabled():
    config = {"style": {"enabled": False}}
    source = "def myFunction():\n    pass\n"
    path = _write_tmp(source)
    try:
        issues = style_checker.check_file(path, config)
        assert issues == []
    finally:
        os.unlink(path)


def test_dunder_method_not_flagged():
    source = "class Foo:\n    def __init__(self):\n        pass\n"
    path = _write_tmp(source)
    try:
        issues = style_checker.check_file(path, _BASE_CONFIG)
        naming_issues = [i for i in issues if i["code"] == "N802"]
        assert naming_issues == []
    finally:
        os.unlink(path)
