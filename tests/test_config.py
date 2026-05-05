"""Tests for code_quality_agent.config"""

import os
import tempfile
import pytest
from code_quality_agent.config import load_config, _DEFAULTS


def test_defaults_returned_without_config_file():
    """load_config() without a file should return the built-in defaults."""
    cfg = load_config(path="/nonexistent/path.yaml")
    assert cfg["style"]["max_line_length"] == _DEFAULTS["style"]["max_line_length"]
    assert cfg["complexity"]["max_complexity"] == _DEFAULTS["complexity"]["max_complexity"]


def test_yaml_overrides_defaults():
    """Values in the YAML file should override defaults."""
    yaml_content = "complexity:\n  max_complexity: 5\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as fh:
        fh.write(yaml_content)
        tmp_path = fh.name

    try:
        cfg = load_config(path=tmp_path)
        assert cfg["complexity"]["max_complexity"] == 5
        # Other defaults should still be intact
        assert cfg["style"]["enabled"] is True
    finally:
        os.unlink(tmp_path)


def test_yaml_partial_merge():
    """Partial YAML should be deep-merged with defaults."""
    yaml_content = "style:\n  max_line_length: 100\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as fh:
        fh.write(yaml_content)
        tmp_path = fh.name

    try:
        cfg = load_config(path=tmp_path)
        assert cfg["style"]["max_line_length"] == 100
        assert cfg["style"]["enabled"] is True  # still from defaults
    finally:
        os.unlink(tmp_path)
