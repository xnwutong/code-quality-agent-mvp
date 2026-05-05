"""Duplicate code detector.

Splits each file into overlapping windows of *min_lines* non-blank lines and
hashes each window. Windows that appear in more than one location (within the
same file or across files) are flagged as duplicates.

This approach is intentionally simple and dependency-free.
"""

import hashlib
from collections import defaultdict
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# Each occurrence: (filepath, starting_line_number)
_Occurrence = Tuple[str, int]


def _issue(filename: str, line: int, code: str, message: str) -> Dict:
    return {
        "filename": filename,
        "line": line,
        "col": 1,
        "code": code,
        "message": message,
        "checker": "duplicates",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_lines(lines: List[str]) -> List[Tuple[int, str]]:
    """Return (original_lineno, stripped_content) for non-blank lines."""
    result = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped:
            result.append((i, stripped))
    return result


def _hash_block(block: List[str]) -> str:
    joined = "\n".join(block)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def _extract_blocks(filepath: str, min_lines: int) -> List[Tuple[str, int]]:
    """Return (hash, first_lineno) pairs for all sliding windows in *filepath*."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return []

    indexed = _strip_lines(raw_lines)
    if len(indexed) < min_lines:
        return []

    result = []
    for i in range(len(indexed) - min_lines + 1):
        window = indexed[i : i + min_lines]
        block_lines = [content for (_, content) in window]
        first_lineno = window[0][0]
        result.append((_hash_block(block_lines), first_lineno))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_files(filepaths: List[str], config: Dict[str, Any]) -> List[Dict]:
    """Detect duplicate code blocks across *filepaths* and return issues."""
    cfg = config.get("duplicates", {})
    if not cfg.get("enabled", True):
        return []

    min_lines = max(cfg.get("min_lines", 6), 3)
    min_count = max(cfg.get("min_duplicate_count", 2), 2)

    # hash → list of (filepath, lineno)
    index: Dict[str, List[_Occurrence]] = defaultdict(list)

    for filepath in filepaths:
        for block_hash, lineno in _extract_blocks(filepath, min_lines):
            index[block_hash].append((filepath, lineno))

    issues: List[Dict] = []
    seen_hashes = set()

    for block_hash, occurrences in index.items():
        if len(occurrences) < min_count:
            continue
        if block_hash in seen_hashes:
            continue
        seen_hashes.add(block_hash)

        # De-duplicate: keep only the earliest occurrence per file.
        earliest: Dict[str, int] = {}
        for filepath, lineno in occurrences:
            if filepath not in earliest or lineno < earliest[filepath]:
                earliest[filepath] = lineno

        locations = "; ".join(
            f"{fp}:{ln}" for fp, ln in sorted(earliest.items())
        )
        for filepath, lineno in sorted(earliest.items()):
            issues.append(
                _issue(
                    filepath,
                    lineno,
                    "D001",
                    f"D001 duplicate code block ({min_lines}+ lines) also found at: {locations}",
                )
            )

    # Suppress issues that overlap (within min_lines) with an earlier issue
    # in the same file — these are just adjacent sliding-window duplicates.
    issues = _suppress_overlapping(issues, min_lines)

    return issues


def _suppress_overlapping(issues: List[Dict], min_lines: int) -> List[Dict]:
    """Remove issues in the same file whose start lines are within *min_lines*
    of a previously seen issue (they represent overlapping windows)."""
    last_seen: Dict[str, int] = {}  # filepath → last kept lineno
    kept = []
    for issue in sorted(issues, key=lambda i: (i["filename"], i["line"])):
        fp = issue["filename"]
        ln = issue["line"]
        if fp in last_seen and ln - last_seen[fp] < min_lines:
            continue  # overlapping window — skip
        last_seen[fp] = ln
        kept.append(issue)
    return kept
