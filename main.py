#!/usr/bin/env python3
"""Code Quality Agent — command-line entry point.

Usage
-----
    python main.py [path] [options]

Examples
--------
    python main.py src/                   # scan a directory
    python main.py mymodule.py            # scan a single file
    python main.py src/ --config my.yaml  # use a custom config file
    python main.py src/ --no-color        # disable ANSI colours
"""

import argparse
import sys

from code_quality_agent.config import load_config
from code_quality_agent.scanner import scan
from code_quality_agent.reporter import print_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-quality-agent",
        description="Lightweight Python code quality inspection agent.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        default=None,
        help="Path to a YAML configuration file (default: config.yaml in cwd)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable ANSI color output",
    )
    parser.add_argument(
        "--no-style",
        action="store_true",
        default=False,
        help="Skip style checks",
    )
    parser.add_argument(
        "--no-security",
        action="store_true",
        default=False,
        help="Skip security checks",
    )
    parser.add_argument(
        "--no-complexity",
        action="store_true",
        default=False,
        help="Skip complexity checks",
    )
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        default=False,
        help="Skip duplicate code detection",
    )
    parser.add_argument(
        "--max-complexity",
        type=int,
        default=None,
        metavar="N",
        help="Override the cyclomatic complexity threshold",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)

    # Apply CLI flag overrides
    if args.no_color:
        config.setdefault("report", {})["color"] = False
    if args.no_style:
        config.setdefault("style", {})["enabled"] = False
    if args.no_security:
        config.setdefault("security", {})["enabled"] = False
    if args.no_complexity:
        config.setdefault("complexity", {})["enabled"] = False
    if args.no_duplicates:
        config.setdefault("duplicates", {})["enabled"] = False
    if args.max_complexity is not None:
        config.setdefault("complexity", {})["max_complexity"] = args.max_complexity

    issues = scan(args.path, config)
    print_report(issues, config)

    # Exit code: 0 = clean, 1 = issues found
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
