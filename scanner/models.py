from dataclasses import dataclass
from typing import List


@dataclass
class Issue:
    level: str    # ERROR / WARNING
    type: str     # style / security / complexity / duplicate
    file_path: str
    line: int
    message: str


@dataclass
class ScanReport:
    total_files: int = 0
    total_issues: int = 0
    error_count: int = 0
    warn_count: int = 0
    issues: List[Issue] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []