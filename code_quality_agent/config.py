"""Configuration loader for the code quality agent."""

import os
from typing import Any, Dict

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

# Default configuration used when no YAML file is found or for missing keys.
_DEFAULTS: Dict[str, Any] = {
    "style": {
        "enabled": True,
        "max_line_length": 79,
        "ignore_codes": [],
        "check_naming": True,
    },
    "security": {
        "enabled": True,
        "check_hardcoded_secrets": True,
        "check_sql_injection": True,
    },
    "complexity": {
        "enabled": True,
        "max_complexity": 10,
    },
    "duplicates": {
        "enabled": True,
        "min_lines": 6,
        "min_duplicate_count": 2,
    },
    "report": {
        "color": True,
        "show_summary": True,
    },
}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge *override* into a copy of *base*."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Return a configuration dictionary.

    Priority (highest wins):
    1. Values from the YAML file at *path* (or ``config.yaml`` in cwd)
    2. Built-in defaults
    """
    config = dict(_DEFAULTS)

    if not _YAML_AVAILABLE:
        return config

    candidates = []
    if path:
        candidates.append(path)
    else:
        candidates.append(os.path.join(os.getcwd(), "config.yaml"))

    for candidate in candidates:
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                user_cfg = yaml.safe_load(fh) or {}
            config = _deep_merge(config, user_cfg)
            break

    return config
