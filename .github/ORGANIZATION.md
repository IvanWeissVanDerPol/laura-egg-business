# 📁 Granja Cabral - Organization System

## Overview

This repository uses an **AI-powered CI/CD system** to keep markdown files organized, professional, and maintainable.

## 🤖 AI Features

| Feature | Description | Command |
|---------|-------------|---------|
| **Content Classification** | Auto-detects file type (contact, plan, research, etc.) | `--analyze` |
| **Smart Tagging** | Auto-generates tags based on content | `--tags` |
| **Related Files** | Finds files with similar content | `--related` |
| **Duplicate Detection** | Identifies redundant files | `--duplicates` |
| **Priority Analysis** | Detects urgent/important items | Built-in |
| **Entity Extraction** | Extracts locations, people, organizations | Built-in |

### AI Classification Types

| Type | Subtypes | Confidence |
|------|----------|------------|
| `contact` | hotel, restaurant, supermarket, bakery, institution | 80%+ |
| `plan` | business, marketing, operations | 75%+ |
| `research` | market, benchmark, statistics | 85%+ |
| `guide` | tutorial, manual, procedure | 70%+ |
| `financial` | costs, revenue, budget | 80%+ |
| `product` | eggs, poultry, derived | 85%+ |
| `supplier` | vendor, feed_mill, equipment | 80%+ |
| `legal` | permits, regulations, compliance | 85%+ |
| `sustainability` | compost, bio_energy, recycling | 80%+ |
| `innovation` | tech, future, improvement | 70%+ |

---

## 🔄 How It Works

```
Push to main → GitHub Actions triggers → AI Analysis → Auto-organize → Changes committed
      ↓                    ↓                   ↓              ↓                ↓
   *.md changed      validate            classify        archive old      INDEX.md
                                         tag files       create subgroups  updated
                                         find related    move duplicates
```

## 📋 Organization Rules

### File Limits
| Rule | Limit | Action |
|------|-------|--------|
| Max files per folder | 8 | Create subgroups |
| Archive after | 180 days | Move to `_archive/` |
| Min age before archive | 30 days | Protect recent files |

### Auto-Subgroup Creation
When a folder exceeds 8 files, the system automatically creates subgroups:

**Example: `03_sales/contacts/` with 15 files:**
```
03_sales/contacts/
├── INDEX.md
├── hotels/          ← auto-created
│   ├── INDEX.md
│   └── hotel_grande.md
├── restaurants/     ← auto-created
│   ├── INDEX.md
│   └── rest_deco.md
├── bakeries/        ← auto-created
│   └── ...
└── retail/          ← auto-created
    └── ...
```

### Auto-Archive
Files older than 180 days are archived to `_archive/YYYY-MM/`:
```
_archive/
├── 2026-03/
│   ├── core_old_report.md
│   └── old_contact.md
├── 2026-04/
│   └── ...
└── README.md  ← auto-generated index
```

---

## 🛠️ AI Commands

### Run Full AI Analysis
```bash
python .github/scripts/ai_organizer.py
```

### Get Statistics
```bash
python .github/scripts/ai_organizer.py --stats
```

### Find Duplicates
```bash
python .github/scripts/ai_organizer.py --duplicates
```

### Find Related Files
```bash
python .github/scripts/ai_organizer.py --related
```

### Show All Tags
```bash
python .github/scripts/ai_organizer.py --tags
```

### Analyze Specific File
```bash
python .github/scripts/ai_organizer.py --file 03_sales/contacts/hotels_restaurants/01_restaurants_hotels.md --verbose
```

### JSON Output (for automation)
```bash
python .github/scripts/ai_organizer.py --json > analysis.json
```

---

## 🛠️ Organization Commands

### Dry Run (Preview Changes)
```bash
python .github/scripts/organize-md.py --dry-run
```

### Run Organization
```bash
python .github/scripts/organize-md.py --report
```

### Validate Structure
```bash
python .github/scripts/validate-md.py --verbose
```

### Custom Configuration
```bash
# Archive files older than 90 days
python .github/scripts/organize-md.py --archive-days 90

# Change max files per folder
python .github/scripts/organize-md.py --max-files 6
```

---

## 🔄 CI/CD Workflows

### 1. MD Organizer (`.github/workflows/md-organizer.yml`)
- **Triggers**: Push to main, weekly (Sunday), manual
- **Actions**: Archive old files, create subgroups, update INDEX.md

### 2. AI Analysis (`.github/workflows/ai-analysis.yml`)
- **Triggers**: Push to main, weekly (Monday), manual
- **Actions**: Content classification, tagging, duplicate detection

### 3. PR Check
- **Triggers**: Pull requests
- **Actions**: Validate structure, warn if organization needed

---

## 📂 Protected Files/Directories

These are never archived or moved:

| Type | Examples |
|------|----------|
| Critical Files | `INDEX.md`, `README.md`, `MASTER_PLAN.md` |
| Critical Directories | `01_core_operations/`, `03_sales/contacts/` |
| Recent Files | < 30 days old |

## 📊 INDEX.md Auto-Generation

Every directory with markdown files gets an auto-generated `INDEX.md`:

```markdown
# 📁 VENTAS Y DISTRIBUCIÓN
## Granja Cabral

| Archivo | Descripción | Última actualización |
|---------|-------------|---------------------|
| `file1.md` | Description | 2026-03-19 |
| `file2.md` | Description | 2026-03-18 |
```

---

## 🧠 AI Tag System

Files are auto-tagged with the following format:

| Tag Pattern | Example | Meaning |
|-------------|---------|---------|
| `type:` | `type:contact` | Content type |
| `subtype:` | `subtype:restaurant` | Content subtype |
| `priority:` | `priority:high` | Priority level |
| `topic:` | `topic:huevos` | Main topic |
| `format:` | `format:table` | Has tables |
| `feature:` | `feature:contacts` | Contains contacts |
| `feature:` | `feature:financials` | Contains financial data |
| `geo:` | `geo:local` | Geographical reference |
| `size:` | `size:large` | File size category |

---

## 🔧 Configuration

Edit `.github/scripts/organize-md.py` to customize:

```python
CONFIG = {
    "max_files_per_folder": 8,      # Files before subgrouping
    "archive_after_days": 180,      # Days before archiving
    "min_age_to_archive": 30,       # Protect recent files
    "protected_dirs": [             # Never archive from
        "01_core_operations",
        "03_sales/contacts",
    ],
    "subgroup_patterns": {          # Auto-subgroup rules
        r"(hotel|posada)": "hotels",
        r"(restaurante)": "restaurants",
    },
}
```

Edit `.github/scripts/ai_organizer.py` to add content types:

```python
CONTENT_TYPES = {
    "contact": {
        "keywords": ["contacto", "telefono", ...],
        "patterns": [r"\|\s*#\s*\|.*nombre.*\|", ...],
        "weight": 10,
    },
    # Add custom types...
}
```

---

## 🚨 Troubleshooting

### Files were archived unexpectedly
Check if file was:
- Older than 180 days
- Marked with "archived" or "obsoleto" in content

### AI classification seems wrong
The AI uses keyword/pattern matching. You can:
1. Edit `CONTENT_TYPES` in `ai_organizer.py`
2. Add more keywords for your content type
3. Adjust weights for better accuracy

### Subgroup created incorrectly
The pattern matching may have matched your filename. Edit `subgroup_patterns` in config.

### INDEX.md missing
Run: `python .github/scripts/organize-md.py`

### Want to prevent archiving
Add to protected_dirs or use a filename like `MASTER_PLAN.md`

---

## 📈 Weekly Report

Every Sunday/Monday at 8am/6am UTC, the system:
1. Runs full organization + AI analysis
2. Generates report in `_archive/report-YYYYMMDD-HHMM.md`
3. Creates JSON analysis in artifacts
4. Commits any changes

---

*Powered by AI 🤖 | Maintained by Granja Cabral Bot*
