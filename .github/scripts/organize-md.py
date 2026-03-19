#!/usr/bin/env python3
"""
Granja Cabral - Markdown File Organizer
=======================================
Auto-organizes markdown files, creates subgroups, archives old files,
and maintains INDEX.md files.

Usage:
    python organize-md.py [--dry-run] [--archive-days 90] [--max-files 8]

Rules:
1. If folder has > max_files files → create subgroups or archive
2. If file hasn't been modified in archive_days → move to _archive
3. Every folder must have an INDEX.md
4. INDEX.md is auto-generated with current file listing
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import re

# Enable UTF-8 output on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    # Maximum files per folder before creating subgroups
    "max_files_per_folder": 8,
    # Days before archiving old files (0 = never archive by age)
    "archive_after_days": 180,
    # Minimum days before a file can be archived (protect recent files)
    "min_age_to_archive": 30,
    # Directories to never archive from (critical business data)
    "protected_dirs": [
        "01_core_operations",
        "03_sales/contacts",
        "04_supply_chain",
        "sources",
    ],
    # Directories to exclude from organization (system folders)
    "excluded_dirs": [
        ".git",
        ".github",
        ".specstory",
        ".cursorindexingignore",
        "_archive",
    ],
    # File patterns that should never be archived
    "protected_files": [
        "INDEX.md",
        "README.md",
        "MASTER_PLAN.md",
        "PLAN.md",
    ],
    # Subgroup naming patterns (regex → subgroup name)
    "subgroup_patterns": {
        r"(hotel|posada|hosteria)": "hotels",
        r"(restaurante|comedor|parrilla|churrasqueria)": "restaurants",
        r"(supermercado|tienda|almacen|kiosko)": "retail",
        r"(panaderia|pasteleria|confiteria)": "bakeries",
        r"(fabrica|industria|procesamiento)": "manufacturing",
        r"(granja|criadero|avicultura)": "farms",
        r"(veterinar|clinica|centro)": "veterinary",
        r"(molino|balanceado|alimento)": "feed_mills",
        r"(molde|equipo|herramienta)": "equipment",
    },
    # Category labels for INDEX.md generation (Spanish)
    "category_labels": {
        "01_core_operations": "🚜 OPERACIONES DEL DÍA A DÍA",
        "02_products": "📦 PRODUCTOS",
        "03_sales": "💵 VENTAS Y DISTRIBUCIÓN",
        "04_supply_chain": "🔗 PROVEEDORES",
        "05_market_intelligence": "📊 INTELIGENCIA DE MERCADO",
        "06_business_plan": "📈 PLAN DE NEGOCIOS",
        "07_innovation": "💡 INNOVACIÓN",
        "08_sustainability": "🌿 SOSTENIBILIDAD",
        "09_references": "📚 REFERENCIAS",
        "sources": "📚 FUENTES",
    },
}

# ============================================
# HELPER FUNCTIONS
# ============================================


def get_file_age(filepath: Path) -> int:
    """Get file age in days based on modification time."""
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    return (datetime.now() - mtime).days


def get_file_metadata(filepath: Path) -> Dict:
    """Extract metadata from markdown file."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")

    # Try to extract frontmatter
    metadata = {
        "name": filepath.name,
        "path": str(filepath),
        "size": filepath.stat().st_size,
        "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        "age_days": get_file_age(filepath),
        "title": "",
        "status": "active",
        "category": "",
    }

    # Extract title from first H1
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        metadata["title"] = h1_match.group(1).strip()

    # Extract status from content
    if "obsoleto" in content.lower() or "deprecated" in content.lower():
        metadata["status"] = "deprecated"
    elif "borrador" in content.lower() or "draft" in content.lower():
        metadata["status"] = "draft"
    elif "archivado" in content.lower() or "archived" in content.lower():
        metadata["status"] = "archived"

    return metadata


def should_archive(filepath: Path, config: Dict) -> Tuple[bool, str]:
    """Determine if a file should be archived."""
    filename = filepath.name

    # Never archive protected files
    if filename in config["protected_files"]:
        return False, "protected file"

    # Check if in protected directory
    rel_path = str(filepath.relative_to(Path.cwd()))
    for protected in config["protected_dirs"]:
        if rel_path.startswith(protected):
            return False, f"protected directory: {protected}"

    # Check age
    age = get_file_age(filepath)
    if age < config["min_age_to_archive"]:
        return False, f"too young ({age} days)"

    if config["archive_after_days"] > 0 and age > config["archive_after_days"]:
        return True, f"age ({age} days > {config['archive_after_days']})"

    # Check if deprecated
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        if "status: archived" in content.lower() or "# archived" in content.lower():
            return True, "marked as archived"
    except:
        pass

    return False, "no archive trigger"


def count_md_files(directory: Path) -> int:
    """Count markdown files in directory (excluding INDEX.md)."""
    if not directory.exists():
        return 0
    return len(
        [f for f in directory.glob("*.md") if f.name not in ["INDEX.md", "README.md"]]
    )


def get_subgroup_name(filename: str, patterns: Dict) -> str:
    """Determine subgroup based on filename patterns."""
    filename_lower = filename.lower()
    for pattern, subgroup in patterns.items():
        if re.search(pattern, filename_lower):
            return subgroup
    return "other"


def create_index_md(directory: Path, files: List[Path], config: Dict) -> str:
    """Generate INDEX.md content for a directory."""
    dir_name = directory.name
    parent_name = directory.parent.name if directory.parent else ""

    # Get category label
    category_key = (
        str(directory.relative_to(Path.cwd())).split("/")[0]
        if directory != Path.cwd()
        else dir_name
    )
    label = config["category_labels"].get(category_key, dir_name)

    lines = [
        f"# {label}",
        f"## Granja Cabral",
        "",
        "---",
        "",
        "## 📁 CONTENIDO",
        "",
        "| Archivo | Descripción | Última actualización |",
        "|---------|-------------|---------------------|",
    ]

    for f in sorted(files):
        if f.name == "INDEX.md":
            continue
        metadata = get_file_metadata(f)
        title = (
            metadata["title"]
            if metadata["title"]
            else f.stem.replace("_", " ").replace("-", " ").title()
        )
        date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
        lines.append(f"| `{f.name}` | {title} | {date} |")

    # Add subdirectories
    subdirs = [
        d
        for d in directory.iterdir()
        if d.is_dir() and d.name not in CONFIG["excluded_dirs"]
    ]
    if subdirs:
        lines.extend(
            [
                "",
                "## 📂 SUBDIRECTORIOS",
                "",
                "| Directorio | Descripción |",
                "|-------------|-------------|",
            ]
        )
        for sd in sorted(subdirs):
            label = config["category_labels"].get(
                sd.name, sd.name.replace("_", " ").title()
            )
            lines.append(f"| `{sd.name}/` | {label} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 🔗 NAVEGACIÓN",
            "",
            f"- ⬆️ [`../../README.md`](../../README.md) — Inicio",
        ]
    )

    # Add sibling navigation
    if parent_name:
        parent_index = directory.parent / "INDEX.md"
        if parent_index.exists():
            lines.append(f"- ⬅️ [`../INDEX.md`](../INDEX.md) — Volver")

    lines.extend(
        [
            "",
            "---",
            f"",
            f"*Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        ]
    )

    return "\n".join(lines)


# ============================================
# MAIN ORGANIZATION LOGIC
# ============================================


class MDOrganizer:
    def __init__(self, repo_path: Path, config: Dict, dry_run: bool = False):
        self.repo_path = repo_path
        self.config = config
        self.dry_run = dry_run
        self.changes = []
        self.archive_dir = repo_path / "_archive"
        self.archive_date = datetime.now().strftime("%Y-%m")

    def log(self, message: str, action: str = "INFO"):
        """Log a change or action."""
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}[{action}] {message}")
        self.changes.append(
            {"action": action, "message": message, "dry_run": self.dry_run}
        )

    def ensure_archive_dir(self):
        """Create archive directory structure."""
        archive_month = self.archive_dir / self.archive_date
        if not self.dry_run:
            archive_month.mkdir(parents=True, exist_ok=True)
            gitkeep = archive_month / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()
        else:
            self.log(f"Would create: {archive_month}", "CREATE")

    def archive_file(self, filepath: Path, reason: str) -> bool:
        """Move a file to archive."""
        if self.dry_run:
            self.log(f"Would archive: {filepath.name} ({reason})", "ARCHIVE")
            return True

        try:
            dest_dir = self.archive_dir / self.archive_date
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Add category prefix to filename
            category = (
                filepath.parent.parent.name
                if filepath.parent.parent != self.repo_path
                else "root"
            )
            new_name = f"{category}_{filepath.name}"
            dest = dest_dir / new_name

            shutil.move(str(filepath), str(dest))
            self.log(
                f"Archived: {filepath.name} → {dest.relative_to(self.repo_path)} ({reason})",
                "ARCHIVE",
            )

            # Create move note in original location
            note = f"# [ARCHIVED]\n\nEste archivo fue archivado el {datetime.now().strftime('%Y-%m-%d')}\n"
            note += f"Razón: {reason}\n\nUbicación actual: `{dest.relative_to(self.repo_path)}`\n"
            note_path = filepath.with_suffix(filepath.suffix + ".archived")
            note_path.write_text(note, encoding="utf-8")

            return True
        except Exception as e:
            self.log(f"Failed to archive {filepath.name}: {e}", "ERROR")
            return False

    def create_subgroup(
        self, parent_dir: Path, subgroup_name: str, files: List[Path]
    ) -> bool:
        """Create a subgroup directory and move files into it."""
        subgroup_dir = parent_dir / subgroup_name

        if self.dry_run:
            self.log(
                f"Would create subgroup: {subgroup_dir.relative_to(self.repo_path)}",
                "SUBGROUP",
            )
            for f in files:
                self.log(f"  → Would move: {f.name}", "MOVE")
            return True

        try:
            subgroup_dir.mkdir(exist_ok=True)

            for f in files:
                dest = subgroup_dir / f.name
                shutil.move(str(f), str(dest))
                self.log(f"Moved: {f.name} → {subgroup_name}/", "MOVE")

            # Create INDEX.md for new subgroup
            index_content = create_index_md(subgroup_dir, files, self.config)
            (subgroup_dir / "INDEX.md").write_text(index_content, encoding="utf-8")

            return True
        except Exception as e:
            self.log(f"Failed to create subgroup {subgroup_name}: {e}", "ERROR")
            return False

    def organize_directory(self, directory: Path) -> Dict:
        """Organize a single directory."""
        stats = {"files": 0, "archived": 0, "subgrouped": 0, "index_updated": 0}

        if not directory.exists():
            return stats

        # Skip excluded directories
        rel_path = str(directory.relative_to(self.repo_path))
        for excluded in self.config["excluded_dirs"]:
            if (
                rel_path.startswith(excluded)
                or directory.name in self.config["excluded_dirs"]
            ):
                return stats

        # Get all MD files
        md_files = [
            f for f in directory.glob("*.md") if f.name not in ["INDEX.md", "README.md"]
        ]
        stats["files"] = len(md_files)

        # Phase 1: Archive old/obsolete files
        files_to_archive = []
        for f in md_files:
            should_arch, reason = should_archive(f, self.config)
            if should_arch:
                files_to_archive.append((f, reason))

        for f, reason in files_to_archive:
            if self.archive_file(f, reason):
                stats["archived"] += 1
                md_files.remove(f)

        # Phase 2: Create subgroups if too many files
        current_count = len(md_files)
        if current_count > self.config["max_files_per_folder"]:
            # Group files by suggested subgroup
            groups = defaultdict(list)
            for f in md_files:
                subgroup = get_subgroup_name(f.name, self.config["subgroup_patterns"])
                groups[subgroup].append(f)

            # Only create subgroups for groups with >1 file
            for subgroup_name, files in groups.items():
                if len(files) > 1 or (
                    len(groups) > 1
                    and current_count > self.config["max_files_per_folder"]
                ):
                    if self.create_subgroup(directory, subgroup_name, files):
                        stats["subgrouped"] += len(files)
                        md_files = [f for f in md_files if f not in files]

        # Phase 3: Regenerate INDEX.md
        remaining_files = [f for f in directory.glob("*.md")]
        index_content = create_index_md(directory, remaining_files, self.config)

        if not self.dry_run:
            (directory / "INDEX.md").write_text(index_content, encoding="utf-8")
            stats["index_updated"] = 1
        else:
            self.log(
                f"Would regenerate INDEX.md for {directory.relative_to(self.repo_path)}",
                "INDEX",
            )

        # Phase 4: Recursively process subdirectories
        for subdir in directory.iterdir():
            if subdir.is_dir() and subdir.name not in self.config["excluded_dirs"]:
                self.organize_directory(subdir)

        return stats

    def generate_report(self) -> str:
        """Generate a summary report of all changes."""
        report = [
            "# 📊 Reporte de Organización Automática",
            f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Modo**: {'DRY RUN (sin cambios reales)' if self.dry_run else 'EJECUTADO'}",
            "",
            "## Cambios Realizados",
            "",
        ]

        actions = defaultdict(list)
        for change in self.changes:
            actions[change["action"]].append(change["message"])

        for action, messages in actions.items():
            report.append(f"### {action} ({len(messages)} archivos)")
            for msg in messages[:20]:  # Limit to 20 per category
                report.append(f"- {msg}")
            if len(messages) > 20:
                report.append(f"- ... y {len(messages) - 20} más")
            report.append("")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Organize markdown files in Granja Cabral repository"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--archive-days", type=int, default=180, help="Days before archiving files"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=8,
        help="Max files per folder before subgrouping",
    )
    parser.add_argument("--report", action="store_true", help="Generate a report file")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check, exit with error if organization needed",
    )

    args = parser.parse_args()

    # Update config from args
    CONFIG["archive_after_days"] = args.archive_days
    CONFIG["max_files_per_folder"] = args.max_files

    repo_path = Path.cwd()
    print(f"📁 Repository: {repo_path}")
    print(f"⚙️  Config: max_files={args.max_files}, archive_days={args.archive_days}")
    print(f"🔧 Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("-" * 50)

    organizer = MDOrganizer(repo_path, CONFIG, dry_run=args.dry_run)
    organizer.ensure_archive_dir()

    # Organize all numbered directories
    total_stats = {"files": 0, "archived": 0, "subgrouped": 0, "index_updated": 0}

    for item in sorted(repo_path.iterdir()):
        if (
            item.is_dir()
            and not item.name.startswith(".")
            and not item.name.startswith("_")
        ):
            if re.match(r"^\d{2}_", item.name) or item.name in ["sources"]:
                print(f"\n📂 Processing: {item.name}")
                stats = organizer.organize_directory(item)
                for key in total_stats:
                    total_stats[key] += stats[key]

    # Generate report
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print(f"  Files scanned: {total_stats['files']}")
    print(f"  Files archived: {total_stats['archived']}")
    print(f"  Files subgrouped: {total_stats['subgrouped']}")
    print(f"  INDEX.md updated: {total_stats['index_updated']}")

    if args.report:
        report = organizer.generate_report()
        report_path = (
            repo_path
            / "_archive"
            / f"report-{datetime.now().strftime('%Y%m%d-%H%M')}.md"
        )
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"\n📝 Report saved: {report_path}")

    # Exit code based on changes (for CI)
    if args.check_only and (
        total_stats["archived"] > 0 or total_stats["subgrouped"] > 0
    ):
        print("\n⚠️  Organization needed! Run without --check-only to apply.")
        sys.exit(1)

    print("\n✅ Organization complete!")
    sys.exit(0)


if __name__ == "__main__":
    main()
