import re
import ast
import hashlib
from typing import Dict
from scanner.models import Issue


class StyleRule:
    @staticmethod
    def check_line_length(code: str, max_len: int, file_path: str) -> List[Issue]:
        issues = []
        lines = code.splitlines()
        for idx, line in enumerate(lines):
            if len(line) > max_len:
                issues.append(Issue(
                    level="WARNING",
                    type="style",
                    file_path=file_path,
                    line=idx + 1,
                    message=f"行过长：{len(line)} 字符，最大允许 {max_len}"
                ))
        return issues

    @staticmethod
    def check_func_name(tree: ast.AST, pattern: str, file_path: str) -> List[Issue]:
        issues = []
        reg = re.compile(pattern)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not reg.match(node.name):
                    issues.append(Issue(
                        level="WARNING",
                        type="style",
                        file_path=file_path,
                        line=node.lineno,
                        message=f"函数命名不规范 `{node.name}`，请使用蛇形命名法"
                    ))
        return issues


class ComplexityRule:
    @staticmethod
    def calc_cyclomatic(node: ast.FunctionDef) -> int:
        cnt = 1
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                cnt += 1
        return cnt

    @staticmethod
    def check_complexity(tree: ast.AST, max_limit: int, file_path: str) -> List[Issue]:
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                c = ComplexityRule.calc_cyclomatic(node)
                if c > max_limit:
                    issues.append(Issue(
                        level="WARNING",
                        type="complexity",
                        file_path=file_path,
                        line=node.lineno,
                        message=f"函数 `{node.name}` 圈复杂度 {c}，超过阈值 {max_limit}"
                    ))
        return issues


class SecurityRule:
    @staticmethod
    def check_sensitive(code: str, keywords: list, file_path: str) -> List[Issue]:
        issues = []
        lines = code.splitlines()
        for idx, line in enumerate(lines):
            lower_line = line.lower()
            for kw in keywords:
                if re.search(rf"{kw}\s*=\s*['\"].+['\"]", lower_line):
                    issues.append(Issue(
                        level="ERROR",
                        type="security",
                        file_path=file_path,
                        line=idx + 1,
                        message=f"检测到硬编码敏感字段：{kw}，有泄露风险"
                    ))
        return issues

    @staticmethod
    def check_risk_pattern(code: str, patterns: list, file_path: str) -> List[Issue]:
        issues = []
        for p in patterns:
            if re.search(p, code):
                issues.append(Issue(
                    level="ERROR",
                    type="security",
                    file_path=file_path,
                    line=0,
                    message=f"检测到高危代码模式：{p}"
                ))
        return issues


class DuplicateRule:
    def __init__(self):
        self.hash_map: Dict[str, str] = {}

    def check_dup(self, code: str, file_path: str) -> List[Issue]:
        issues = []
        clean = re.sub(r"\s+", "", code)
        h = hashlib.md5(clean.encode("utf-8")).hexdigest()
        if h in self.hash_map:
            issues.append(Issue(
                level="WARNING",
                type="duplicate",
                file_path=file_path,
                line=0,
                message=f"与 `{self.hash_map[h]}` 代码高度重复"
            ))
        else:
            self.hash_map[h] = file_path
        return issues