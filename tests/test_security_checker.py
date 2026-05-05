"""Tests for code_quality_agent.checkers.security_checker"""

import os
import tempfile
import pytest
from code_quality_agent.checkers import security_checker

_BASE_CONFIG = {
    "security": {
        "enabled": True,
        "check_hardcoded_secrets": True,
        "check_sql_injection": True,
    }
}


def _write_tmp(content: str) -> str:
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    )
    fh.write(content)
    fh.close()
    return fh.name


# ── Hardcoded secrets ──────────────────────────────────────────────────────


def test_hardcoded_password_flagged():
    source = 'password = "super_secret_123"\n'
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "S001" in codes
    finally:
        os.unlink(path)


def test_empty_password_not_flagged():
    source = 'password = ""\n'
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        s001 = [i for i in issues if i["code"] == "S001"]
        assert s001 == []
    finally:
        os.unlink(path)


def test_placeholder_password_not_flagged():
    source = 'password = "your_password_here"\n'
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        s001 = [i for i in issues if i["code"] == "S001"]
        assert s001 == []
    finally:
        os.unlink(path)


def test_api_key_flagged():
    source = 'api_key = "AKIAIOSFODNN7EXAMPLE"\n'
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "S001" in codes
    finally:
        os.unlink(path)


# ── SQL injection ──────────────────────────────────────────────────────────


def test_sql_fstring_flagged():
    source = (
        'user = "alice"\n'
        'query = f"SELECT * FROM users WHERE name = {user}"\n'
    )
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "S002" in codes
    finally:
        os.unlink(path)


def test_sql_percent_format_flagged():
    source = (
        'name = "alice"\n'
        'query = "SELECT * FROM users WHERE name = \'%s\'" % name\n'
    )
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        codes = [i["code"] for i in issues]
        assert "S002" in codes
    finally:
        os.unlink(path)


def test_parameterised_query_clean():
    source = (
        'name = "alice"\n'
        'query = "SELECT * FROM users WHERE name = ?"\n'
        'cursor.execute(query, (name,))\n'
    )
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, _BASE_CONFIG)
        s002 = [i for i in issues if i["code"] == "S002"]
        assert s002 == []
    finally:
        os.unlink(path)


def test_checker_disabled():
    source = 'password = "secret123"\n'
    config = {"security": {"enabled": False}}
    path = _write_tmp(source)
    try:
        issues = security_checker.check_file(path, config)
        assert issues == []
    finally:
        os.unlink(path)
