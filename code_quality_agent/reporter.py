"""CLI report formatter for the code quality agent."""

from typing import Any, Dict, List

try:
    import colorama
    colorama.init(autoreset=True)
    _COLORAMA_AVAILABLE = True
except ImportError:
    _COLORAMA_AVAILABLE = False


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

def _supports_color(config: Dict[str, Any]) -> bool:
    return config.get("report", {}).get("color", True) and _COLORAMA_AVAILABLE


def _red(text: str, use_color: bool) -> str:
    if use_color and _COLORAMA_AVAILABLE:
        return colorama.Fore.RED + text + colorama.Style.RESET_ALL
    return text


def _yellow(text: str, use_color: bool) -> str:
    if use_color and _COLORAMA_AVAILABLE:
        return colorama.Fore.YELLOW + text + colorama.Style.RESET_ALL
    return text


def _green(text: str, use_color: bool) -> str:
    if use_color and _COLORAMA_AVAILABLE:
        return colorama.Fore.GREEN + text + colorama.Style.RESET_ALL
    return text


def _cyan(text: str, use_color: bool) -> str:
    if use_color and _COLORAMA_AVAILABLE:
        return colorama.Fore.CYAN + text + colorama.Style.RESET_ALL
    return text


def _bold(text: str, use_color: bool) -> str:
    if use_color and _COLORAMA_AVAILABLE:
        return colorama.Style.BRIGHT + text + colorama.Style.RESET_ALL
    return text


# ---------------------------------------------------------------------------
# Issue colour by checker category
# ---------------------------------------------------------------------------

_CHECKER_COLOR = {
    "style": "_yellow",
    "security": "_red",
    "complexity": "_yellow",
    "duplicates": "_cyan",
}

_CHECKER_LABEL = {
    "style": "STYLE",
    "security": "SECURITY",
    "complexity": "COMPLEXITY",
    "duplicates": "DUPLICATE",
}


def _colorize_issue(issue: Dict, use_color: bool) -> str:
    checker = issue.get("checker", "")
    color_fn_name = _CHECKER_COLOR.get(checker, "_yellow")
    color_fn = globals()[color_fn_name]
    label = _CHECKER_LABEL.get(checker, checker.upper())
    location = f"{issue['filename']}:{issue['line']}:{issue['col']}"
    msg = issue["message"]
    return f"  {color_fn('[' + label + ']', use_color)} {location} — {msg}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def print_report(issues: List[Dict], config: Dict[str, Any]) -> None:
    """Print a formatted report to stdout."""
    use_color = _supports_color(config)
    show_summary = config.get("report", {}).get("show_summary", True)

    if not issues:
        print(_green("✔  No issues found.", use_color))
        return

    # Group issues by file
    by_file: Dict[str, List[Dict]] = {}
    for issue in issues:
        by_file.setdefault(issue["filename"], []).append(issue)

    # Counts by checker
    counts: Dict[str, int] = {}
    for issue in issues:
        checker = issue.get("checker", "unknown")
        counts[checker] = counts.get(checker, 0) + 1

    print()
    for filepath in sorted(by_file):
        file_issues = sorted(by_file[filepath], key=lambda i: (i["line"], i["col"]))
        header = _bold(f"── {filepath} ({len(file_issues)} issue(s))", use_color)
        print(header)
        for issue in file_issues:
            print(_colorize_issue(issue, use_color))
        print()

    if show_summary:
        total = len(issues)
        print(_bold("── Summary", use_color))
        for checker in ("style", "security", "complexity", "duplicates"):
            n = counts.get(checker, 0)
            label = _CHECKER_LABEL.get(checker, checker.upper())
            print(f"  {label:<12} {n:>4} issue(s)")
        print(f"  {'TOTAL':<12} {total:>4} issue(s)")
        if any(v > 0 for v in counts.values()):
            print()
            print(_red("✘  Issues detected. Please review the report above.", use_color))
        print()
