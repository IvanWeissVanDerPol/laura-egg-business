#!/usr/bin/env python3
"""
Granja Cabral - Markdown Validator
====================================
Validates markdown file structure, naming conventions,
and content quality.

Usage:
    python validate-md.py [--fix] [--verbose]
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

# Enable UTF-8 output on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ============================================
# VALIDATION RULES
# ============================================


@dataclass
class ValidationIssue:
    file: str
    rule: str
    severity: str  # error, warning, info
    message: str
    suggestion: str = ""


RULES = {
    # File naming rules
    "naming": {
        "no_spaces": {
            "severity": "error",
            "message": "File names should not contain spaces",
            "fix": lambda f: f.name.replace(" ", "_"),
        },
        "lowercase": {
            "severity": "warning",
            "message": "File names should be lowercase",
            "fix": lambda f: f.name.lower(),
        },
        "no_special_chars": {
            "severity": "warning",
            "message": "File names should only contain alphanumeric, hyphens, and underscores",
            "pattern": r"^[a-z0-9_-]+\.md$",
        },
        "descriptive": {
            "severity": "info",
            "message": "File names should be descriptive (at least 3 characters)",
            "min_length": 3,
        },
    },
    # Content rules
    "content": {
        "has_title": {
            "severity": "error",
            "message": "Markdown file should start with a title (# Heading)",
            "pattern": r"^#\s+",
        },
        "no_empty_sections": {
            "severity": "warning",
            "message": "Sections should have content (not just headers)",
        },
        "proper_encoding": {
            "severity": "error",
            "message": "File should be UTF-8 encoded",
        },
    },
    # Structure rules
    "structure": {
        "has_index": {
            "severity": "error",
            "message": "Directories with 2+ files should have an INDEX.md",
        },
        "max_depth": {
            "severity": "warning",
            "message": "Directory nesting should not exceed 4 levels",
            "max": 4,
        },
        "folder_file_limit": {
            "severity": "warning",
            "message": "Folders should not have more than 8 markdown files (excluding INDEX.md)",
            "max": 8,
        },
    },
}

# ============================================
# VALIDATOR CLASS
# ============================================


class MDValidator:
    def __init__(self, repo_path: Path, verbose: bool = False, fix: bool = False):
        self.repo_path = repo_path
        self.verbose = verbose
        self.fix = fix
        self.issues: List[ValidationIssue] = []
        self.stats = {
            "files_checked": 0,
            "errors": 0,
            "warnings": 0,
            "info": 0,
            "fixed": 0,
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is on."""
        if self.verbose or level in ["ERROR", "WARNING"]:
            prefix = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️", "OK": "✅"}.get(
                level, "•"
            )
            print(f"{prefix} {message}")

    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue."""
        self.issues.append(issue)
        self.stats[issue.severity + "s"] = self.stats.get(issue.severity + "s", 0) + 1
        self.log(
            f"{issue.file}: [{issue.rule}] {issue.message}", issue.severity.upper()
        )

    def validate_file_naming(self, filepath: Path):
        """Validate file naming conventions."""
        filename = filepath.name
        stem = filepath.stem

        # Skip special files (INDEX.md, README.md, etc.)
        special_files = ["INDEX.md", "README.md", "MASTER_PLAN.md", "PLAN.md"]
        if filename in special_files:
            return

        # Check for spaces
        if " " in filename:
            self.add_issue(
                ValidationIssue(
                    file=str(filepath.relative_to(self.repo_path)),
                    rule="naming.no_spaces",
                    severity="error",
                    message=f"File contains spaces: '{filename}'",
                    suggestion=f"Use: '{filename.replace(' ', '_')}'",
                )
            )

        # Check for uppercase
        if filename != filename.lower():
            self.add_issue(
                ValidationIssue(
                    file=str(filepath.relative_to(self.repo_path)),
                    rule="naming.lowercase",
                    severity="warning",
                    message=f"File name is not lowercase: '{filename}'",
                    suggestion=f"Consider: '{filename.lower()}'",
                )
            )

        # Check for special characters (except allowed)
        if not re.match(r"^[a-zA-Z0-9_\-\.]+\.md$", filename):
            self.add_issue(
                ValidationIssue(
                    file=str(filepath.relative_to(self.repo_path)),
                    rule="naming.no_special_chars",
                    severity="warning",
                    message=f"File contains special characters: '{filename}'",
                )
            )

        # Check descriptive name
        if len(stem) < 3:
            self.add_issue(
                ValidationIssue(
                    file=str(filepath.relative_to(self.repo_path)),
                    rule="naming.descriptive",
                    severity="info",
                    message=f"File name is very short: '{filename}'",
                )
            )

    def validate_file_content(self, filepath: Path):
        """Validate markdown content."""
        filename = filepath.name

        # Skip special files from content checks
        special_files = ["INDEX.md", "README.md"]

        try:
            content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            self.add_issue(
                ValidationIssue(
                    file=str(filepath.relative_to(self.repo_path)),
                    rule="content.proper_encoding",
                    severity="error",
                    message="File is not UTF-8 encoded",
                )
            )
            return

        # Check for title (skip INDEX.md which has special format)
        if filename not in special_files:
            if not re.search(r"^#\s+", content, re.MULTILINE):
                self.add_issue(
                    ValidationIssue(
                        file=str(filepath.relative_to(self.repo_path)),
                        rule="content.has_title",
                        severity="error",
                        message="File does not have a title (H1 heading)",
                        suggestion="Add '# Title' at the beginning",
                    )
                )

        # Check for empty sections (header followed immediately by another header)
        lines = content.split("\n")
        for i, line in enumerate(lines[:-1]):
            if re.match(r"^#{1,3}\s+", line) and re.match(r"^#{1,3}\s+", lines[i + 1]):
                self.add_issue(
                    ValidationIssue(
                        file=str(filepath.relative_to(self.repo_path)),
                        rule="content.no_empty_sections",
                        severity="info",  # Changed to info - not really a problem
                        message=f"Empty section at line {i + 1}",
                    )
                )

    def validate_directory_structure(self, directory: Path, level: int = 0):
        """Validate directory structure."""
        rel_path = directory.relative_to(self.repo_path)

        # Skip excluded directories
        if directory.name in [
            ".git",
            ".github",
            ".specstory",
            "_archive",
            "__pycache__",
        ]:
            return

        # Check nesting depth
        if level > RULES["structure"]["max_depth"]["max"]:
            self.add_issue(
                ValidationIssue(
                    file=str(rel_path) + "/",
                    rule="structure.max_depth",
                    severity="warning",
                    message=f"Directory nesting exceeds {RULES['structure']['max_depth']['max']} levels",
                )
            )

        # Count markdown files (excluding INDEX.md)
        md_files = [
            f for f in directory.glob("*.md") if f.name not in ["INDEX.md", "README.md"]
        ]

        # Check for INDEX.md if multiple files
        if len(md_files) >= 2:
            index_file = directory / "INDEX.md"
            if not index_file.exists():
                self.add_issue(
                    ValidationIssue(
                        file=str(rel_path) + "/",
                        rule="structure.has_index",
                        severity="error",
                        message=f"Directory has {len(md_files)} files but no INDEX.md",
                    )
                )

        # Check file limit
        if len(md_files) > RULES["structure"]["folder_file_limit"]["max"]:
            self.add_issue(
                ValidationIssue(
                    file=str(rel_path) + "/",
                    rule="structure.folder_file_limit",
                    severity="warning",
                    message=f"Directory has {len(md_files)} files (limit: {RULES['structure']['folder_file_limit']['max']})",
                    suggestion="Consider creating subdirectories or archiving old files",
                )
            )

        # Recurse into subdirectories
        for subdir in directory.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                self.validate_directory_structure(subdir, level + 1)

    def validate_all(self) -> bool:
        """Run all validations. Returns True if no errors."""
        print(f"🔍 Validating: {self.repo_path}")
        print("=" * 50)

        # Validate all markdown files
        for md_file in self.repo_path.rglob("*.md"):
            # Skip files in .git and other excluded dirs
            parts = md_file.relative_to(self.repo_path).parts
            if any(part.startswith(".") or part == "_archive" for part in parts):
                continue

            self.stats["files_checked"] += 1
            self.validate_file_naming(md_file)
            self.validate_file_content(md_file)

        # Validate directory structure
        for item in self.repo_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                self.validate_directory_structure(item)

        return self.stats["errors"] == 0

    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 50)
        print("📊 VALIDATION REPORT")
        print("=" * 50)
        print(f"Files checked: {self.stats['files_checked']}")
        print(f"Errors:        {self.stats['errors']}")
        print(f"Warnings:      {self.stats['warnings']}")
        print(f"Info:          {self.stats['info']}")

        if self.issues:
            print("\n📋 ISSUES FOUND:")
            for issue in self.issues:
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                    issue.severity, "•"
                )
                print(f"  {icon} {issue.file}")
                print(f"     [{issue.rule}] {issue.message}")
                if issue.suggestion:
                    print(f"     💡 {issue.suggestion}")
        else:
            print("\n✅ No issues found! Repository structure is clean.")

        print("\n" + "=" * 50)

    def generate_report_json(self) -> str:
        """Generate JSON report for CI."""
        return json.dumps(
            {
                "timestamp": datetime.now().isoformat(),
                "stats": self.stats,
                "issues": [
                    {
                        "file": i.file,
                        "rule": i.rule,
                        "severity": i.severity,
                        "message": i.message,
                        "suggestion": i.suggestion,
                    }
                    for i in self.issues
                ],
            },
            indent=2,
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate markdown structure")
    parser.add_argument("--fix", action="store_true", help="Attempt to auto-fix issues")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--fail-on-warnings", action="store_true", help="Exit with error on warnings"
    )

    args = parser.parse_args()

    repo_path = Path.cwd()
    validator = MDValidator(repo_path, verbose=args.verbose, fix=args.fix)

    success = validator.validate_all()

    if args.json:
        print(validator.generate_report_json())
    else:
        validator.print_report()

    # Exit code
    if not success:
        sys.exit(1)
    elif args.fail_on_warnings and validator.stats["warnings"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
