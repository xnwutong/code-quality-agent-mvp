import os
import ast
import yaml
from typing import List
from scanner.models import Issue, ScanReport
from scanner.rules import StyleRule, ComplexityRule, SecurityRule, DuplicateRule


class CodeQualityAgent:
    def __init__(self, config_path: str = "config/rule.yaml"):
        self.config = self._load_config(config_path)
        self.report = ScanReport()
        self.dup_rule = DuplicateRule()

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_py_files(self, root: str) -> List[str]:
        file_list = []
        if os.path.isfile(root):
            return [root] if root.endswith(".py") else []
        for root_dir, _, files in os.walk(root):
            for f in files:
                if f.endswith(".py"):
                    file_list.append(os.path.join(root_dir, f))
        return file_list

    def _scan_single_file(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code)
        except Exception as e:
            self.report.issues.append(Issue(
                level="ERROR",
                type="parse",
                file_path=file_path,
                line=0,
                message=f"文件解析失败: {str(e)}"
            ))
            return

        # 风格检查
        self.report.issues.extend(StyleRule.check_line_length(
            code, self.config["style"]["max_line_length"], file_path
        ))
        self.report.issues.extend(StyleRule.check_func_name(
            tree, self.config["style"]["func_name_pattern"], file_path
        ))

        # 复杂度
        self.report.issues.extend(ComplexityRule.check_complexity(
            tree, self.config["complexity"]["max_cyclomatic"], file_path
        ))

        # 安全
        self.report.issues.extend(SecurityRule.check_sensitive(
            code, self.config["security"]["sensitive_keywords"], file_path
        ))
        self.report.issues.extend(SecurityRule.check_risk_pattern(
            code, self.config["security"]["risk_patterns"], file_path
        ))

        # 重复代码
        if self.config["duplicate"]["enable"]:
            self.report.issues.extend(self.dup_rule.check_dup(code, file_path))

    def run_scan(self, target_path: str):
        self.report = ScanReport()
        py_files = self._get_py_files(target_path)
        self.report.total_files = len(py_files)

        for f in py_files:
            self._scan_single_file(f)

        # 统计
        self.report.total_issues = len(self.report.issues)
        self.report.error_count = sum(1 for i in self.report.issues if i.level == "ERROR")
        self.report.warn_count = sum(1 for i in self.report.issues if i.level == "WARNING")
        return self.report

    def print_report(self):
        rep = self.report
        print("\n" + "="*60)
        print("          Code Quality Agent MVP Report")
        print("="*60)
        print(f"扫描文件总数 : {rep.total_files}")
        print(f"发现问题总数 : {rep.total_issues}")
        print(f"❌ 严重错误   : {rep.error_count}")
        print(f"⚠️  警告提示   : {rep.warn_count}")
        print("-"*60)

        for item in rep.issues:
            print(f"[{item.level}] [{item.type}] {item.file_path}:{item.line}")
            print(f"   → {item.message}\n")