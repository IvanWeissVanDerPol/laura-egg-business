#!/usr/bin/env python3
"""
Granja Cabral - AI-Powered Markdown Organizer
==============================================
Advanced content analysis, smart classification, and intelligent organization.

Features:
- Content-based classification (contact, plan, research, guide, etc.)
- Auto-tagging with priority detection
- Related file detection using content similarity
- Smart subgroup recommendations
- Metadata extraction from content
- Duplicate/redundancy detection

Usage:
    python ai_organizer.py [--analyze] [--tags] [--related] [--organize] [--dry-run]
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field, asdict
import math

# Enable UTF-8 output on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ============================================
# AI CLASSIFICATION RULES
# ============================================


@dataclass
class FileAnalysis:
    """Complete analysis of a markdown file."""

    path: str
    filename: str
    content_type: str = "unknown"
    subtype: str = ""
    tags: List[str] = field(default_factory=list)
    priority: str = "normal"  # low, normal, high, critical
    keywords: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    word_count: int = 0
    section_count: int = 0
    has_tables: bool = False
    has_contacts: bool = False
    has_financials: bool = False
    related_files: List[str] = field(default_factory=list)
    content_hash: str = ""
    summary: str = ""
    confidence: float = 0.0


# Content type patterns (Spanish + English)
CONTENT_TYPES = {
    "contact": {
        "keywords": [
            "contacto",
            "telefono",
            "teléfono",
            "direccion",
            "dirección",
            "email",
            "whatsapp",
            "cliente",
            "proveedor",
            "establecimiento",
            "hotel",
            "restaurante",
            "supermercado",
            "panaderia",
            "panadería",
            "phone",
            "address",
            "contact",
            "customer",
            "supplier",
        ],
        "patterns": [
            r"\|\s*#\s*\|.*nombre.*\|.*direcci",  # Table with name/address
            r"\*\*[A-Z][a-záéíóú]+\*\*",  # Bold names
            r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",  # Phone numbers
            r"km\.?\s*\d+",  # KM markers (Paraguay addresses)
        ],
        "weight": 10,
    },
    "plan": {
        "keywords": [
            "plan",
            "estrategia",
            "estrategia",
            "objetivo",
            "meta",
            "fase",
            "etapa",
            "proyecto",
            "implementacion",
            "implementación",
            "timeline",
            "cronograma",
            "action plan",
            "roadmap",
            "planeamiento",
            "planificacion",
            "planificación",
        ],
        "patterns": [
            r"##\s+FASE\s+\d",
            r"##\s+ETAPA\s+\d",
            r"(?:semana|mes|año)\s+\d",
            r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
        ],
        "weight": 10,
    },
    "research": {
        "keywords": [
            "investigacion",
            "investigación",
            "estudio",
            "analisis",
            "análisis",
            "mercado",
            "tendencia",
            "dato",
            "estadistica",
            "estadística",
            "benchmark",
            "comparativo",
            "research",
            "market",
            "data",
            "fuente",
            "source",
            "referencia",
            "evidencia",
        ],
        "patterns": [
            r"\d+%",  # Percentages
            r"Gs\.?\s*[\d.,]+",  # Guaranies amounts
            r"\$\s*[\d.,]+",  # Dollar amounts
            r"(?:según|de acuerdo|basado en|según datos)",
        ],
        "weight": 10,
    },
    "guide": {
        "keywords": [
            "guia",
            "guía",
            "manual",
            "tutorial",
            "como hacer",
            "cómo hacer",
            "instrucciones",
            "paso a paso",
            "quick start",
            "getting started",
            "instruccion",
            "instrucción",
            "procedimiento",
            "protocolo",
            "best practice",
            "mejor practica",
            "mejor práctica",
        ],
        "patterns": [
            r"##\s+PASO\s+\d",
            r"###\s+\d+[\.\)]\s",
            r"(?:primero|segundo|tercero|luego|despues|después)",
            r"(?:1|2|3|4|5)[\.\)]\s+\w",
        ],
        "weight": 8,
    },
    "financial": {
        "keywords": [
            "financiero",
            "financiero",
            "costo",
            "precio",
            "ingreso",
            "egreso",
            "ganancia",
            "perdida",
            "pérdida",
            "margen",
            "presupuesto",
            "budget",
            "break-even",
            "roi",
            "inversion",
            "inversión",
            "financiamiento",
            "prestamo",
            "préstamo",
            "facturacion",
            "facturación",
            "cobro",
            "pago",
        ],
        "patterns": [
            r"Gs\.?\s*[\d.,]+",  # Guaranies
            r"\$\s*[\d.,]+",  # Dollars
            r"\d+\s*(?:guaranies|gs|g\.|PYG)",
            r"(?:ingreso|egreso|costo|precio|venta|compra)",
        ],
        "weight": 12,
    },
    "product": {
        "keywords": [
            "producto",
            "productos",
            "huevos",
            "pollo",
            "aves",
            "derivado",
            "elaborado",
            "procesado",
            "calidad",
            "certificacion",
            "certificación",
            "organico",
            "orgánico",
            "premium",
            "gourmet",
            "fresco",
            "natural",
        ],
        "patterns": [
            r"huevos?\s+(?:fresco|premium|organico|organico)",
            r"pollo\s+(?:fresco|natural|organico)",
            r"(?:unidad|docena|kg|kilo|libra)",
        ],
        "weight": 10,
    },
    "supplier": {
        "keywords": [
            "proveedor",
            "proveedores",
            "insumo",
            "insumos",
            "compra",
            "adquisicion",
            "adquisición",
            "abastecimiento",
            "molino",
            "balanceado",
            "alimento",
            "veterinaria",
            "equipo",
            "materia prima",
        ],
        "patterns": [
            r"(?:proveedor|supplier|vendor)",
            r"(?:comprar|adquirir|surtir|abastecer)",
            r"(?:pedido|minimo|volumen)",
        ],
        "weight": 10,
    },
    "legal": {
        "keywords": [
            "legal",
            "regulacion",
            "regulación",
            "ley",
            "decreto",
            "permiso",
            "licencia",
            "registro",
            "normativa",
            "cumplimiento",
            "senave",
            "magra",
            "ministerio",
            "registro",
            "patente",
        ],
        "patterns": [
            r"(?:resolucion|resolución|decreto|ley)\s+\d+",
            r"(?:registro|inscripcion|inscripción)",
            r"(?:senave|magra|dinac|ministerio)",
        ],
        "weight": 12,
    },
    "sustainability": {
        "keywords": [
            "sustentable",
            "sostenible",
            "sustentabilidad",
            "sostenibilidad",
            "ambiental",
            "ecologico",
            "ecológico",
            "verde",
            "green",
            "compost",
            "biogas",
            "biogás",
            "reciclaje",
            "energia",
            "energía",
            "renovable",
            "huella",
            "carbono",
            "emision",
        ],
        "patterns": [
            r"(?:compost|biogas|biogás|reciclaje)",
            r"(?:co2|emision|emisión|carbono)",
            r"(?:renovable|solar|eolica|eólica)",
        ],
        "weight": 10,
    },
    "innovation": {
        "keywords": [
            "innovacion",
            "innovación",
            "tecnologia",
            "tecnología",
            "mejora",
            "optimizacion",
            "optimización",
            "futuro",
            "nuevo",
            "novedad",
            "oportunidad",
            "tendencia",
            "automatizacion",
            "automatización",
            "digital",
        ],
        "patterns": [
            r"(?:tecnolog[ií]a|innovaci[oó]n|futuro)",
            r"(?:nuevo|nueva|emergente)",
            r"(?:oportunidad|potencial|posibilidad)",
        ],
        "weight": 8,
    },
}

# Priority detection patterns
PRIORITY_PATTERNS = {
    "critical": [
        r"URGENTE",
        r"CRITICAL",
        r"EMERGENCIA",
        r"INMEDIATO",
        r"PRIORIDAD\s+ALTA",
        r"HIGH\s+PRIORITY",
    ],
    "high": [
        r"⭐",
        r"IMPORTANT",
        r"IMPORTANTE",
        r"PRIORIDAD",
        r"ALTA\s+PRIORIDAD",
        r"KEY",
        r"PRIORITARIO",
    ],
    "low": [
        r"OPCIONAL",
        r"FUTURE",
        r"FUTURO",
        r"IDEA",
        r"EXPLORAR",
        r"STRETCH",
        r"LOW\s+PRIORITY",
    ],
}

# Entity extraction patterns
ENTITY_PATTERNS = {
    "locations": [
        r"(?:Coronel Oviedo|Cnel\. Oviedo|Oviedo)",
        r"(?:Asunción|Asuncion|Capital)",
        r"(?:Caaguazú|Caaguazu)",
        r"(?:Ruta\s+\d+)",
        r"(?:Km\.?\s*\d+)",
    ],
    "organizations": [
        r"(?:SENAVE|MAGRA|DINAC|MINISTERIO)",
        r"(?:AVIPAR|Pechugón|Supermix)",
    ],
    "people": [
        r"(?:Laura|Jorge|Cabral)",
    ],
    "money": [
        r"Gs\.?\s*[\d.,]+",
        r"\$\s*[\d.,]+",
    ],
}


# ============================================
# AI ANALYZER CLASS
# ============================================


class AIAnalyzer:
    """AI-powered content analyzer for markdown files."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.analyses: Dict[str, FileAnalysis] = {}
        self.content_cache: Dict[str, str] = {}

    def read_file(self, filepath: Path) -> str:
        """Read file with caching."""
        rel_path = str(filepath.relative_to(self.repo_path))
        if rel_path not in self.content_cache:
            try:
                self.content_cache[rel_path] = filepath.read_text(encoding="utf-8")
            except Exception:
                self.content_cache[rel_path] = ""
        return self.content_cache[rel_path]

    def extract_keywords(self, content: str, top_n: int = 10) -> List[str]:
        """Extract important keywords from content using TF-like scoring."""
        # Common Spanish/English stop words
        stop_words = {
            "de",
            "la",
            "el",
            "en",
            "y",
            "a",
            "los",
            "las",
            "del",
            "un",
            "una",
            "que",
            "por",
            "con",
            "para",
            "es",
            "su",
            "al",
            "lo",
            "como",
            "más",
            "pero",
            "sus",
            "le",
            "ya",
            "o",
            "este",
            "si",
            "porque",
            "esta",
            "son",
            "entre",
            "cuando",
            "muy",
            "sin",
            "sobre",
            "también",
            "me",
            "hasta",
            "donde",
            "quien",
            "desde",
            "nos",
            "durante",
            "todos",
            "the",
            "and",
            "or",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "can",
            "could",
            "may",
            "might",
            "must",
            "shall",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "about",
            # Business context stop words
            "granja",
            "cabral",
            "paraguay",
            "marzo",
            "2026",
            "archivos",
        }

        # Normalize and tokenize
        words = re.findall(r"\b[a-záéíóúñ]{4,}\b", content.lower())

        # Count word frequency
        word_counts = Counter(w for w in words if w not in stop_words)

        # Return top keywords
        return [word for word, _ in word_counts.most_common(top_n)]

    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract named entities from content."""
        entities = defaultdict(list)

        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                entities[entity_type].extend(matches)

        # Deduplicate
        return {k: list(set(v)) for k, v in entities.items() if v}

    def detect_priority(self, content: str, filename: str) -> str:
        """Detect priority level from content."""
        combined = f"{filename} {content}"

        for priority, patterns in PRIORITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    return priority

        return "normal"

    def classify_content(self, content: str, filename: str) -> Tuple[str, str, float]:
        """Classify content type using weighted scoring."""
        combined = f"{filename} {content[:5000]}".lower()  # First 5000 chars
        scores = {}

        for content_type, rules in CONTENT_TYPES.items():
            score = 0

            # Keyword matching
            for keyword in rules["keywords"]:
                occurrences = combined.count(keyword.lower())
                score += occurrences * rules["weight"]

            # Pattern matching
            for pattern in rules["patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    score += rules["weight"] * 2

            scores[content_type] = score

        # Get best match
        if not scores or max(scores.values()) == 0:
            return "general", "", 0.0

        best_type = max(scores.items(), key=lambda x: x[1])[0]
        total_score = sum(scores.values())
        confidence = scores[best_type] / total_score if total_score > 0 else 0

        # Determine subtype
        subtype = self._determine_subtype(content, best_type)

        return best_type, subtype, confidence

    def _determine_subtype(self, content: str, content_type: str) -> str:
        """Determine content subtype."""
        content_lower = content.lower()

        subtypes = {
            "contact": {
                "hotel": ["hotel", "posada", "hosteria"],
                "restaurant": [
                    "restaurante",
                    "churrasqueria",
                    "churrasquería",
                    "parrilla",
                ],
                "supermarket": ["supermercado", "tienda", "almacen"],
                "bakery": ["panaderia", "panadería", "pasteleria"],
                "institution": [
                    "institucion",
                    "institución",
                    "hospital",
                    "escuela",
                    "colegio",
                ],
            },
            "product": {
                "eggs": ["huevo", "huevos", "docena"],
                "poultry": ["pollo", "aves", "gallina"],
                "derived": ["derivado", "elaborado", "procesado", "liquido", "polvo"],
            },
            "plan": {
                "business": ["negocio", "empresa", "comercial"],
                "marketing": ["marketing", "publicidad", "promocion"],
                "operations": ["operacion", "operación", "produccion", "producción"],
            },
        }

        if content_type in subtypes:
            for subtype, keywords in subtypes[content_type].items():
                if any(kw in content_lower for kw in keywords):
                    return subtype

        return ""

    def generate_tags(self, analysis: FileAnalysis) -> List[str]:
        """Generate smart tags based on analysis."""
        tags = set()

        # Content type tag
        tags.add(f"type:{analysis.content_type}")

        # Subtype tag
        if analysis.subtype:
            tags.add(f"subtype:{analysis.subtype}")

        # Priority tag
        if analysis.priority != "normal":
            tags.add(f"priority:{analysis.priority}")

        # Feature tags
        if analysis.has_tables:
            tags.add("format:table")
        if analysis.has_contacts:
            tags.add("feature:contacts")
        if analysis.has_financials:
            tags.add("feature:financials")

        # Keyword tags (top 3)
        for kw in analysis.keywords[:3]:
            tags.add(f"topic:{kw}")

        # Location tags
        if "locations" in analysis.entities:
            tags.add("geo:local")

        # Size tag
        if analysis.word_count > 1000:
            tags.add("size:large")
        elif analysis.word_count > 300:
            tags.add("size:medium")
        else:
            tags.add("size:small")

        return sorted(list(tags))

    def calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate content similarity using Jaccard similarity of keywords."""
        words1 = set(re.findall(r"\b[a-záéíóúñ]{4,}\b", content1.lower()))
        words2 = set(re.findall(r"\b[a-záéíóúñ]{4,}\b", content2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def find_related_files(
        self, filepath: Path, threshold: float = 0.15
    ) -> List[Tuple[str, float]]:
        """Find related files based on content similarity."""
        content = self.read_file(filepath)
        related = []

        for other_path, other_content in self.content_cache.items():
            if str(filepath.relative_to(self.repo_path)) == other_path:
                continue

            similarity = self.calculate_similarity(content, other_content)
            if similarity >= threshold:
                related.append((other_path, similarity))

        return sorted(related, key=lambda x: x[1], reverse=True)[:5]

    def detect_content_hash(self, content: str) -> str:
        """Generate hash for duplicate detection."""
        # Normalize content for comparison
        normalized = re.sub(r"\s+", " ", content.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

    def generate_summary(self, content: str, max_sentences: int = 3) -> str:
        """Generate a brief summary of the content."""
        # Simple extractive summary - get first meaningful paragraphs
        paragraphs = content.split("\n\n")
        summary_parts = []

        for para in paragraphs:
            para = para.strip()
            # Skip headers, tables, and empty lines
            if para.startswith("#") or para.startswith("|") or not para:
                continue

            # Clean up markdown
            para = re.sub(r"[*_`#]", "", para)
            para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)  # Links

            if len(para) > 20:
                summary_parts.append(para)

            if len(summary_parts) >= max_sentences:
                break

        return " ".join(summary_parts)[:200] + "..." if summary_parts else ""

    def analyze_file(self, filepath: Path) -> FileAnalysis:
        """Perform complete AI analysis of a file."""
        rel_path = str(filepath.relative_to(self.repo_path))
        content = self.read_file(filepath)

        analysis = FileAnalysis(
            path=rel_path,
            filename=filepath.name,
        )

        # Basic metrics
        analysis.word_count = len(content.split())
        analysis.section_count = len(re.findall(r"^#{1,3}\s+", content, re.MULTILINE))
        analysis.has_tables = bool(re.search(r"^\|.*\|.*\|", content, re.MULTILINE))
        analysis.has_contacts = any(
            kw in content.lower()
            for kw in ["telefono", "teléfono", "contacto", "whatsapp", "email"]
        )
        analysis.has_financials = bool(re.search(r"Gs\.?\s*[\d.,]+", content))

        # Content hashing
        analysis.content_hash = self.detect_content_hash(content)

        # Classification
        content_type, subtype, confidence = self.classify_content(
            content, filepath.name
        )
        analysis.content_type = content_type
        analysis.subtype = subtype
        analysis.confidence = confidence

        # Priority
        analysis.priority = self.detect_priority(content, filepath.name)

        # Keywords
        analysis.keywords = self.extract_keywords(content)

        # Entities
        analysis.entities = self.extract_entities(content)

        # Tags
        analysis.tags = self.generate_tags(analysis)

        # Summary
        analysis.summary = self.generate_summary(content)

        # Related files
        related = self.find_related_files(filepath)
        analysis.related_files = [r[0] for r in related]

        # Store analysis
        self.analyses[rel_path] = analysis

        return analysis

    def analyze_all(self, progress_callback=None) -> Dict[str, FileAnalysis]:
        """Analyze all markdown files in the repository."""
        md_files = list(self.repo_path.rglob("*.md"))
        total = len(md_files)

        for i, filepath in enumerate(md_files):
            # Skip excluded directories
            parts = filepath.relative_to(self.repo_path).parts
            if any(part.startswith(".") or part == "_archive" for part in parts):
                continue

            # Analyze file
            self.analyze_file(filepath)

            if progress_callback:
                progress_callback(i + 1, total, filepath.name)

        return self.analyses

    def find_duplicates(self) -> List[List[str]]:
        """Find potential duplicate files."""
        hash_groups = defaultdict(list)

        for path, analysis in self.analyses.items():
            hash_groups[analysis.content_hash].append(path)

        return [paths for paths in hash_groups.values() if len(paths) > 1]

    def get_statistics(self) -> Dict:
        """Get analysis statistics."""
        stats = {
            "total_files": len(self.analyses),
            "by_type": Counter(),
            "by_priority": Counter(),
            "by_subtype": Counter(),
            "avg_confidence": 0,
            "tables_count": 0,
            "contacts_count": 0,
            "financial_count": 0,
        }

        confidences = []
        for analysis in self.analyses.values():
            stats["by_type"][analysis.content_type] += 1
            stats["by_priority"][analysis.priority] += 1
            if analysis.subtype:
                stats["by_subtype"][f"{analysis.content_type}/{analysis.subtype}"] += 1
            confidences.append(analysis.confidence)
            if analysis.has_tables:
                stats["tables_count"] += 1
            if analysis.has_contacts:
                stats["contacts_count"] += 1
            if analysis.has_financials:
                stats["financial_count"] += 1

        stats["avg_confidence"] = (
            sum(confidences) / len(confidences) if confidences else 0
        )

        return stats


# ============================================
# MAIN INTERFACE
# ============================================


def print_progress(current, total, filename):
    """Print progress indicator."""
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r  [{bar}] {current}/{total} - {filename[:30]:<30}", end="", flush=True)


def print_analysis(analysis: FileAnalysis, verbose: bool = False):
    """Print analysis results for a file."""
    priority_icons = {"critical": "🔴", "high": "🟠", "normal": "⚪", "low": "🔵"}
    icon = priority_icons.get(analysis.priority, "⚪")

    print(f"\n{icon} {analysis.filename}")
    print(
        f"   Type: {analysis.content_type}/{analysis.subtype or '—'} (confidence: {analysis.confidence:.0%})"
    )
    print(f"   Tags: {', '.join(analysis.tags[:5])}")

    if verbose:
        print(f"   Words: {analysis.word_count} | Sections: {analysis.section_count}")
        print(
            f"   Tables: {'✓' if analysis.has_tables else '✗'} | Contacts: {'✓' if analysis.has_contacts else '✗'} | Financial: {'✓' if analysis.has_financials else '✗'}"
        )
        if analysis.keywords:
            print(f"   Keywords: {', '.join(analysis.keywords[:5])}")
        if analysis.related_files:
            print(f"   Related: {len(analysis.related_files)} files")
        if analysis.summary:
            print(f"   Summary: {analysis.summary[:80]}...")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI-Powered Markdown Analyzer")
    parser.add_argument("--analyze", action="store_true", help="Analyze all files")
    parser.add_argument("--tags", action="store_true", help="Show tags for all files")
    parser.add_argument("--related", action="store_true", help="Show related files")
    parser.add_argument("--duplicates", action="store_true", help="Find duplicates")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", type=str, help="Analyze specific file")

    args = parser.parse_args()

    repo_path = Path.cwd()
    analyzer = AIAnalyzer(repo_path)

    print("🤖 AI-Powered Markdown Analyzer")
    print("=" * 50)
    print(f"📁 Repository: {repo_path.name}")
    print()

    # Run analysis
    print("🔍 Analyzing files...")
    analyzer.analyze_all(progress_callback=print_progress)
    print("\n")

    if args.file:
        # Analyze specific file
        filepath = repo_path / args.file
        if filepath.exists():
            analysis = analyzer.analyze_file(filepath)
            print_analysis(analysis, verbose=True)
        else:
            print(f"❌ File not found: {args.file}")
            sys.exit(1)

    elif args.json:
        # JSON output
        data = {
            "timestamp": datetime.now().isoformat(),
            "statistics": analyzer.get_statistics(),
            "analyses": {k: asdict(v) for k, v in analyzer.analyses.items()},
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.stats:
        # Statistics
        stats = analyzer.get_statistics()
        print("📊 STATISTICS")
        print("-" * 40)
        print(f"Total files analyzed: {stats['total_files']}")
        print(f"Average confidence: {stats['avg_confidence']:.0%}")
        print(f"Files with tables: {stats['tables_count']}")
        print(f"Files with contacts: {stats['contacts_count']}")
        print(f"Files with financials: {stats['financial_count']}")
        print()
        print("📂 By Content Type:")
        for type_name, count in stats["by_type"].most_common():
            print(f"   {type_name}: {count}")
        print()
        print("⚡ By Priority:")
        for priority, count in stats["by_priority"].most_common():
            print(f"   {priority}: {count}")

    elif args.duplicates:
        # Find duplicates
        duplicates = analyzer.find_duplicates()
        if duplicates:
            print("🔄 POTENTIAL DUPLICATES")
            print("-" * 40)
            for group in duplicates:
                print(f"  • {', '.join(group)}")
        else:
            print("✅ No duplicates found")

    elif args.related:
        # Show related files
        print("🔗 RELATED FILES")
        print("-" * 40)
        for path, analysis in analyzer.analyses.items():
            if analysis.related_files:
                print(f"\n{path}:")
                for related in analysis.related_files[:3]:
                    print(f"  → {related}")

    elif args.tags:
        # Show tags
        print("🏷️ TAGS")
        print("-" * 40)
        for path, analysis in sorted(analyzer.analyses.items()):
            if analysis.tags:
                print(f"\n{path}:")
                for tag in analysis.tags:
                    print(f"  [{tag}]")

    else:
        # Default: show all analyses
        print("📋 CONTENT ANALYSIS")
        print("-" * 40)
        for path, analysis in sorted(analyzer.analyses.items()):
            print_analysis(analysis, verbose=args.verbose)

    # Summary
    print("\n" + "=" * 50)
    print("✅ Analysis complete!")


if __name__ == "__main__":
    main()
