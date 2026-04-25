#!/usr/bin/env python3
"""
Parse WhatsApp egg sales chat export into structured data.
Outputs both CSV and XLSX. CLI version (no tkinter GUI).

Usage:
    python parse_whatsapp_cli.py <input.txt> [output_base_name]
    
If output_base_name is not given, defaults to 'ventas_parsed'.
Generates: ventas_parsed.xlsx and ventas_parsed.csv
"""

import re
import sys
import os
import csv
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ── Concepts that should NOT have price multiplied by 1000 ──
# These are items priced in raw guaraníes (not thousands)
NO_MULTIPLY_CONCEPTS = {
    'BOLSAS', 'BOLSA', 'U', 'KG',
}

# Concepts where price is per-unit in Gs (e.g. "1 picado x 15 = 15.000")
# Price 15 means Gs 15,000 → multiply by 1000
# But the ingreso "15.000" = 15000 is correct
# So for these, we DO multiply by 1000
PRICE_TIMES_1000_CONCEPTS = {
    'PICADO', 'PICADOS', 'PIC',
}

# Concepts with multi-word names that need special handling
KNOWN_MULTI_WORD = {
    'GALLINAS', 'GALLINA', 'GALLINAZA', 'ABONO', 'POLLITOS',
    'LOCOTE', 'FRUTILLA', 'SURTIDO', 'PICADO',
}


def _parse_price_str(precio_str):
    """
    Parse price string handling both decimal and thousands-separator dots.
    
    Rules:
      - "13.500" (dot + exactly 3 digits) → 13500 (thousands separator, already in Gs)
      - "21.5" or "22,5" (dot/comma + 1-2 digits) → 21.5 or 22.5 (decimal, needs x1000)
      - "20" (no dot) → 20.0 (needs x1000)
    
    Returns (price_in_gs: float, already_full: bool)
      already_full=True means price is already in full guaraníes (no x1000 needed)
    """
    precio_str = precio_str.replace(',', '.').strip()
    
    # Check for thousands-separator pattern: digits.3digits or digits.3digits.3digits
    if re.match(r'^\d{1,3}(\.\d{3})+$', precio_str):
        # It's a thousands-separated number like "13.500" or "1.080.000"
        return float(precio_str.replace('.', '')), True
    
    try:
        val = float(precio_str)
        return val, False
    except ValueError:
        return None, False


def _clean_sale_line(line):
    """Strip known noise from a sale line before parsing."""
    # Remove WhatsApp edit markers
    line = re.sub(r'\s*<Se editó este mensaje\.?>\s*$', '', line)
    # Remove leading "Retira" / "retira"
    line = re.sub(r'^(?:Retira|retira)\s+', '', line)
    # Remove trailing "gs" / "Gs" after price number
    line = re.sub(r'\s+[Gg]s\s*(?==)', '', line)
    # Remove parenthetical notes like "(pollas)"
    line = re.sub(r'\([^)]*\)', '', line)
    return line.strip()


def parse_whatsapp_txt(input_txt_path):
    """
    Parse WhatsApp sales chat and return list of dicts.
    
    Handles many format variations:
        10 A x 25 = 250.000          (standard)
        1.5 B x 20 = 30.000          (decimal quantity)
        52A x 21.5= 1.118.000        (no space before concept)
        80 tipo b x 13.500= 1.080.000 (tipo keyword, thousands price)
        30x14.000= 420.000           (no space, thousands price)
        A 475 x 17= 8.075.000        (reversed: concept before qty)
        264 B X 18 = 4.752.000       (uppercase X)
        15 bolsas abono x 20= 300.000 (multi-word concept)
        15A x 19=                     (missing ingreso)
        <Se editó este mensaje.>      (WhatsApp edit marker stripped)
    """

    # ── Regex patterns ──
    
    # Start of a WhatsApp message line
    message_start_regex = re.compile(
        r'^(\d{1,2}/\d{1,2}/\d{4}),\s*\d{1,2}:\d{2}(?:\s*[ap]\.?\s*m\.?)?\s*-\s*(.+?):\s*(.*)'
    )

    # Pattern 1: Standard "10 A x 25 = 250.000" (concept is letters only)
    # Also handles: no space before concept, uppercase X, optional spaces
    # Also handles: "tipo X" prefix on concept
    sale_regex_standard = re.compile(
        r'^\s*(\d+(?:[.,]\d+)?)\s*'           # quantity (with optional decimal)
        r'(?:tipo\s+)?'                         # optional "tipo " prefix
        r'([a-zA-Z][a-zA-Z]*)'                 # concept (at least 1 letter)
        r'\s*[xX]\s*'                           # x or X separator
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'   # price (decimal or thousands-sep)
        r'\s*=\s*'                              # = separator
        r'([\d.]+)?\s*$'                        # ingreso (optional - may be missing)
    )

    # Pattern 2: No concept letter "64 x 23 = 1.472.000"
    sale_regex_no_concept = re.compile(
        r'^\s*(\d+(?:[.,]\d+)?)\s*'
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Pattern 3: Reversed "A 475 x 17= 8.075.000" (concept before quantity)
    sale_regex_reversed = re.compile(
        r'^\s*([a-zA-Z][a-zA-Z]*)\s+'
        r'(\d+(?:[.,]\d+)?)\s*'
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Pattern 4: Multi-word concept "15 bolsas abono x 20= 300.000"
    # or "10 gallinas G1 x 20= 180.000" or "60 bolsas de gallinaza x 10 = 600.000"
    # or "Frutilla 6kg x 18.000= 108.000" or "Locote 60kg x 6.500= 390.000"
    sale_regex_multiword = re.compile(
        r'^\s*(?:(\d+(?:[.,]\d+)?)\s+)?'        # optional leading quantity
        r'([a-zA-ZáéíóúñÁÉÍÓÚÑ][a-zA-ZáéíóúñÁÉÍÓÚÑ\s\d]*?)'  # concept (multi-word)
        r'(?:\s+(\d+(?:[.,]\d+)?))?\s*'          # optional trailing quantity (or qty in concept)
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Pattern 4b: "Frutilla 6kg x 18.000= 108.000" - product + quantity_with_unit
    sale_regex_product_qty = re.compile(
        r'^\s*([a-zA-ZáéíóúñÁÉÍÓÚÑ]+)\s+'
        r'(\d+(?:[.,]\d+)?)\s*(?:kg|KG|g|lt|unid(?:ades?)?)\s*'
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Pattern 5: Combined types "2A+7B x 23= 207.000" or "50 A + 50 S x 18= 1.800.000"
    sale_regex_combined = re.compile(
        r'^\s*(\d+)\s*([a-zA-Z])\s*\+\s*(\d+)\s*([a-zA-Z])\s*'
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Pattern 6: "N concepto y concepto x price = ingreso" - mixed types with "y"
    sale_regex_mixed_y = re.compile(
        r'^\s*(\d+(?:[.,]\d+)?)\s+'
        r'([a-zA-Z]+)\s+y\s+([a-zA-Z]+)\s*'
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?(?:\.\d{3})*)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Pattern 7: "N concept x price1 y price2 = ingreso" - two prices with "y"
    # e.g. "30 AS x 22 y 23 = 671.000"
    sale_regex_two_prices = re.compile(
        r'^\s*(\d+(?:[.,]\d+)?)\s+'
        r'([a-zA-Z]+)\s*'
        r'[xX]\s*'
        r'(\d+(?:[.,]\d{1,2})?)\s+y\s+(\d+(?:[.,]\d{1,2})?)'
        r'\s*=\s*'
        r'([\d.]+)?\s*$'
    )

    # Lines with client-level info we want to skip
    payment_regex = re.compile(
        r'(?i)(pagado|a cobrar|debe|transferencia|efectivo|saldo)',
    )

    parsed_rows = []
    errors = []
    skipped_lines = []
    
    current_date = None
    current_sender = None
    current_client = None
    line_number = 0

    def add_row(fecha, cliente, cantidad, concepto, precio, ingreso, check_result, raw_line, lineno, sender=None):
        parsed_rows.append({
            "Fecha": fecha,
            "Cliente": cliente,
            "Cantidad": cantidad,
            "Concepto": concepto,
            "Precio Unitario": precio,
            "Ingreso": ingreso,
            "Check": check_result,
            "Original": raw_line,
            "Linea": lineno,
            "Vendedor": sender or "",
        })

    def try_parse_sale(stripped_line, original_line, line_number):
        """Try all sale patterns. Returns True if matched."""
        nonlocal current_client

        cleaned = _clean_sale_line(stripped_line)
        if not cleaned:
            return False

        # ── Pattern 7: Two prices "30 AS x 22 y 23 = 671.000" ──
        m = sale_regex_two_prices.match(cleaned)
        if m:
            cantidad = _parse_cantidad(m.group(1))
            concepto = m.group(2).upper()
            precio1_raw, af1 = _parse_price_str(m.group(3))
            precio2_raw, af2 = _parse_price_str(m.group(4))
            ingreso_str = m.group(5)
            if cantidad is not None and precio1_raw is not None and precio2_raw is not None:
                # Use average of the two prices
                avg_raw = (precio1_raw + precio2_raw) / 2
                precio_gs = _calc_price_gs(avg_raw, af1 and af2, concepto)
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 5: Combined "2A+7B x 23= 207.000" ──
        m = sale_regex_combined.match(cleaned)
        if m:
            qty1, type1, qty2, type2 = int(m.group(1)), m.group(2).upper(), int(m.group(3)), m.group(4).upper()
            precio_raw, already_full = _parse_price_str(m.group(5))
            ingreso_str = m.group(6)
            if precio_raw is not None:
                concepto = f"{type1}+{type2}"
                cantidad = qty1 + qty2
                precio_gs = precio_raw if already_full else precio_raw * 1000
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 6: Mixed "70 S y A x 18= 1.260.000" ──
        m = sale_regex_mixed_y.match(cleaned)
        if m:
            cantidad_str, type1, type2 = m.group(1), m.group(2).upper(), m.group(3).upper()
            cantidad = _parse_cantidad(cantidad_str)
            precio_raw, already_full = _parse_price_str(m.group(4))
            ingreso_str = m.group(5)
            if cantidad is not None and precio_raw is not None:
                concepto = f"{type1}+{type2}"
                precio_gs = precio_raw if already_full else precio_raw * 1000
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 3: Reversed "A 475 x 17= 8.075.000" ──
        m = sale_regex_reversed.match(cleaned)
        if m:
            concepto = m.group(1).upper()
            cantidad = _parse_cantidad(m.group(2))
            precio_raw, already_full = _parse_price_str(m.group(3))
            ingreso_str = m.group(4)
            if cantidad is not None and precio_raw is not None:
                precio_gs = _calc_price_gs(precio_raw, already_full, concepto)
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 1: Standard "10 A x 25 = 250.000" ──
        m = sale_regex_standard.match(cleaned)
        if m:
            cantidad = _parse_cantidad(m.group(1))
            concepto = m.group(2).upper()
            precio_raw, already_full = _parse_price_str(m.group(3))
            ingreso_str = m.group(4)
            if cantidad is not None and precio_raw is not None:
                precio_gs = _calc_price_gs(precio_raw, already_full, concepto)
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 4b: Product with unit "Frutilla 6kg x 18.000= 108.000" ──
        m = sale_regex_product_qty.match(cleaned)
        if m:
            concepto = m.group(1).upper()
            cantidad = _parse_cantidad(m.group(2))
            precio_raw, already_full = _parse_price_str(m.group(3))
            ingreso_str = m.group(4)
            if cantidad is not None and precio_raw is not None:
                precio_gs = precio_raw if already_full else precio_raw * 1000
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 4: Multi-word concept "15 bolsas abono x 20= 300.000" ──
        m = sale_regex_multiword.match(cleaned)
        if m:
            # Groups: 1=optional leading qty, 2=concept, 3=optional trailing qty, 4=price, 5=ingreso
            leading_qty = m.group(1)
            raw_concept = m.group(2).strip()
            trailing_qty = m.group(3)
            precio_raw, already_full = _parse_price_str(m.group(4))
            ingreso_str = m.group(5)
            # Use leading qty if present, else trailing qty
            qty_str = leading_qty or trailing_qty
            cantidad = _parse_cantidad(qty_str) if qty_str else None
            if cantidad is not None and precio_raw is not None:
                concepto = _normalize_multiword_concept(raw_concept)
                precio_gs = _calc_price_gs(precio_raw, already_full, concepto)
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, concepto, precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        # ── Pattern 2: No concept "64 x 23 = 1.472.000" ──
        m = sale_regex_no_concept.match(cleaned)
        if m:
            cantidad = _parse_cantidad(m.group(1))
            precio_raw, already_full = _parse_price_str(m.group(2))
            ingreso_str = m.group(3)
            if cantidad is not None and precio_raw is not None:
                if already_full:
                    precio_gs = precio_raw
                else:
                    # Heuristic: if we have ingreso, check which interpretation fits
                    # "240 x 500 = 120.000" → 240*500=120,000 ✓ (literal)
                    # "64 x 23 = 1.472.000" → 64*23,000=1,472,000 ✓ (x1000)
                    ingreso_check = _parse_ingreso(ingreso_str) if ingreso_str else None
                    if ingreso_check and abs(cantidad * precio_raw - ingreso_check) < 1:
                        precio_gs = precio_raw  # literal Gs works
                    else:
                        precio_gs = precio_raw * 1000  # thousands shorthand
                ingreso_val = _parse_ingreso(ingreso_str) if ingreso_str else cantidad * precio_gs
                check = _check_calc(cantidad, precio_gs, ingreso_val)
                add_row(current_date or "???", current_client or "???",
                        cantidad, "???", precio_gs, ingreso_val, check,
                        original_line, line_number, current_sender)
                return True

        return False

    with open(input_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_number += 1
            original_line = line.rstrip('\n')
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # ── WhatsApp message header ──
            msg_match = message_start_regex.match(stripped_line)
            if msg_match:
                date_str = msg_match.group(1)
                sender = msg_match.group(2).strip()
                rest = msg_match.group(3).strip()
                
                current_sender = sender
                
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                    current_date = dt.strftime('%d/%m/%Y')
                except ValueError:
                    current_date = f"???:{date_str}"
                    errors.append(f"L{line_number}: Bad date '{date_str}'")
                
                if rest:
                    if try_parse_sale(rest, original_line, line_number):
                        pass
                    elif payment_regex.search(rest):
                        skipped_lines.append(f"L{line_number}: Payment note: {rest[:80]}")
                    elif 'x' not in rest.lower() and '=' not in rest:
                        current_client = rest.strip()
                    else:
                        # Try as client name if very short
                        if len(rest) < 40 and 'x' not in rest.lower():
                            current_client = rest.strip()
                        else:
                            skipped_lines.append(f"L{line_number}: Unparsed msg: {rest[:80]}")
                continue

            # ── Continuation line ──
            if try_parse_sale(stripped_line, original_line, line_number):
                continue
            
            if payment_regex.search(stripped_line):
                skipped_lines.append(f"L{line_number}: Payment note: {stripped_line[:80]}")
            elif _has_sale_markers(stripped_line):
                # Has x/X and = but no pattern matched — record as error
                errors.append(f"L{line_number}: Failed to parse sale: {stripped_line[:120]}")
                add_row(
                    fecha=current_date or "???",
                    cliente=current_client or "???",
                    cantidad="???",
                    concepto="???",
                    precio="???",
                    ingreso="???",
                    check_result="PARSE_ERROR",
                    raw_line=original_line,
                    lineno=line_number,
                    sender=current_sender,
                )
            elif stripped_line.startswith(('<', '‎', 'Eliminaste', 'Se eliminó',
                                          'Los mensajes', 'cambió')):
                pass  # System messages
            else:
                # Likely a client name
                cleaned_name = stripped_line.strip('* ')
                if cleaned_name and len(cleaned_name) < 80:
                    current_client = cleaned_name

    return parsed_rows, errors, skipped_lines


def _has_sale_markers(line):
    """Check if a line looks like it could be a sale (has x/X and =)."""
    cleaned = _clean_sale_line(line)
    # Must have both a multiplication marker and equals
    has_x = bool(re.search(r'\bx\b|\bX\b|(?<=\d)[xX](?=\s*\d)', cleaned))
    has_eq = '=' in cleaned
    return has_x and has_eq


def _parse_cantidad(s):
    """Parse quantity string, handling comma/dot decimals."""
    try:
        return float(s.replace(',', '.'))
    except (ValueError, TypeError):
        return None


def _parse_ingreso(ingreso_str):
    """Parse ingreso string, removing thousands dots."""
    if not ingreso_str:
        return None
    clean = ingreso_str.replace('.', '')
    try:
        return float(clean)
    except ValueError:
        return None


def _calc_price_gs(precio_raw, already_full, concepto):
    """
    Calculate price in guaraníes based on concept type and format.
    
    The chat uses shorthand: "x 25" means "x Gs 25,000" for eggs.
    But for small items (bolsas, picado, unidades), the logic varies:
      - BOLSAS: "x 500" = Gs 500 literal (no multiply)
      - U: "x 10" = Gs 1,000 per unit (x1000, same as eggs)
      - PICADO: "x 15" = Gs 15,000 per unit (x1000, same as eggs)
      - KG: "x 5000" = Gs 5,000 literal (already in Gs)
      - GALLINAS: "x 20" = Gs 20,000 (x1000, same as eggs)
      - GALLINAZA: "x 15" = Gs 15,000 (x1000, same as eggs)
      - LOCOTE: "x 7000" = Gs 7,000 literal (already in Gs)
    """
    concepto_upper = concepto.upper() if concepto else ""
    
    # If already parsed as full Gs (thousands separator detected)
    if already_full:
        return precio_raw
    
    # BOLSAS (de balanceado): price is literal Gs (500 = Gs 500)
    if concepto_upper in ('BOLSAS', 'BOLSA'):
        return precio_raw
    
    # BOLSAS_ABONO: "15 bolsas abono x 20 = 300.000" → 15 * 20,000 = 300,000
    # Price is in thousands shorthand (same as eggs)
    if concepto_upper == 'BOLSAS_ABONO':
        return precio_raw * 1000
    
    # U: small unit items — "x 700" means Gs 700, "x 10" means Gs 10
    # But ingreso "10.000" = 10,000 so... "10 U x 10 = 10.000"
    # → 10 * 10 should = 10,000 → price must be 1,000 → multiply by 1000?
    # Actually looking at data: "10 U x 10 = 10.000" → this is unit eggs
    # sold at Gs 1,000 each (written as "10" in thousands shorthand)
    # But "300 U x 700 gs= 210.000" → 300 * 700 = 210,000 ✓ literal Gs
    if concepto_upper == 'U':
        if precio_raw >= 100:
            # Large number like 700 = literal Gs
            return precio_raw
        else:
            # Small number like 10 = thousands shorthand
            return precio_raw * 1000
    
    # KG: price already in Gs (e.g., "5 KG x 5000 = 25.000")
    if concepto_upper == 'KG':
        if precio_raw >= 1000:
            return precio_raw
        else:
            return precio_raw * 1000
    
    # LOCOTE: "60 locote x 7000 = 420.000" → literal Gs
    # But "Locote 60kg x 6.500" is a parse error anyway
    if concepto_upper == 'LOCOTE':
        if precio_raw >= 1000:
            return precio_raw
        else:
            return precio_raw * 1000
    
    # Everything else: standard x1000 shorthand
    # (eggs A/B/S/J/C, gallinas, gallinaza, abono, picado, etc.)
    return precio_raw * 1000


def _check_calc(cantidad, precio_gs, ingreso_val):
    """Verify quantity * price = ingreso."""
    if cantidad is None or precio_gs is None or ingreso_val is None:
        return "MISSING_DATA"
    
    if not isinstance(cantidad, (int, float)):
        return "???"
    if not isinstance(precio_gs, (int, float)):
        return "???"
    if not isinstance(ingreso_val, (int, float)):
        return "???"
    
    calculated = cantidad * precio_gs
    if abs(calculated - ingreso_val) < 1:
        return "OK"
    else:
        return f"MISMATCH(expected={int(calculated)},got={int(ingreso_val)})"


def _normalize_multiword_concept(raw):
    """Normalize multi-word concepts to a standard form."""
    lower = raw.lower().strip()
    
    # Map multi-word concepts
    if 'gallinaza' in lower:
        return 'GALLINAZA'
    if 'gallina' in lower and 'carnea' in lower:
        return 'GALLINAS_CARNEADAS'
    if 'gallina' in lower:
        return 'GALLINAS'
    if 'bolsa' in lower and 'abono' in lower:
        return 'BOLSAS_ABONO'
    if 'bolsa' in lower:
        return 'BOLSAS'
    if 'pollito' in lower or 'polla' in lower:
        return 'POLLITOS'
    if 'abono' in lower:
        return 'ABONO'
    if 'locote' in lower:
        return 'LOCOTE'
    if 'frutilla' in lower:
        return 'FRUTILLA'
    if 'picado' in lower:
        return 'PICADO'
    if 'surtido' in lower:
        return 'SURTIDO'
    
    # If it starts with "tipo " strip that
    if lower.startswith('tipo '):
        return raw[5:].strip().upper()
    
    # For short single-word, return uppercase
    words = raw.split()
    if len(words) == 1:
        return raw.upper()
    
    # Multi-word: join with underscore
    return '_'.join(w.upper() for w in words)


def add_computed_columns(rows):
    """Add TripNumber, Dia, Mes, Año columns."""
    for row in rows:
        try:
            dt = datetime.strptime(row["Fecha"], '%d/%m/%Y')
            row["Dia"] = dt.day
            row["Mes"] = dt.month
            row["Año"] = dt.year
            row["_dt"] = dt
        except (ValueError, TypeError):
            row["Dia"] = ""
            row["Mes"] = ""
            row["Año"] = ""
            row["_dt"] = None

    # Compute TripNumber (nth unique date in each month)
    month_dates = {}
    for row in rows:
        if row["_dt"]:
            key = (row["_dt"].year, row["_dt"].month)
            if key not in month_dates:
                month_dates[key] = set()
            month_dates[key].add(row["_dt"].date())

    month_date_ranks = {}
    for key, dates in month_dates.items():
        sorted_dates = sorted(dates)
        month_date_ranks[key] = {d: i+1 for i, d in enumerate(sorted_dates)}

    for row in rows:
        if row["_dt"]:
            key = (row["_dt"].year, row["_dt"].month)
            row["TripNumber"] = month_date_ranks[key][row["_dt"].date()]
        else:
            row["TripNumber"] = ""
        del row["_dt"]

    return rows


def write_csv(rows, output_path):
    """Write rows to CSV."""
    if not rows:
        print("No rows to write!")
        return
    
    columns = ["Fecha", "Cliente", "Cantidad", "Concepto", "Precio Unitario", 
               "Ingreso", "Check", "Original", "Linea", "Vendedor", 
               "TripNumber", "Dia", "Mes", "Año"]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"CSV written: {output_path} ({len(rows)} rows)")


def write_xlsx(rows, output_path):
    """Write rows to XLSX using pandas + openpyxl."""
    if not HAS_PANDAS or not HAS_OPENPYXL:
        print(f"Skipping XLSX (missing pandas={not HAS_PANDAS}, openpyxl={not HAS_OPENPYXL})")
        return
    
    columns = ["Fecha", "Cliente", "Cantidad", "Concepto", "Precio Unitario",
               "Ingreso", "Check", "Original", "Linea", "Vendedor",
               "TripNumber", "Dia", "Mes", "Año"]
    
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(output_path, index=False)
    print(f"XLSX written: {output_path} ({len(rows)} rows)")


def print_summary(rows, errors, skipped):
    """Print analysis summary."""
    print("\n" + "="*60)
    print("RESUMEN DEL ANÁLISIS")
    print("="*60)
    
    total = len(rows)
    ok = sum(1 for r in rows if r.get("Check") == "OK")
    mismatches = sum(1 for r in rows if isinstance(r.get("Check", ""), str) and "MISMATCH" in r["Check"])
    parse_errors = sum(1 for r in rows if r.get("Check") == "PARSE_ERROR")
    missing = sum(1 for r in rows if r.get("Check") == "MISSING_DATA")
    
    print(f"\nTotal registros de venta: {total}")
    print(f"  OK:            {ok} ({ok*100//total if total else 0}%)")
    print(f"  Mismatch:      {mismatches}")
    print(f"  Parse errors:  {parse_errors}")
    print(f"  Missing data:  {missing}")
    
    # Date range
    dates = [r["Fecha"] for r in rows if r.get("Fecha") and not r["Fecha"].startswith("???")]
    if dates:
        print(f"\nRango de fechas: {dates[0]} - {dates[-1]}")
    
    # Unique clients
    clients = set(r["Cliente"] for r in rows if r.get("Cliente") and r["Cliente"] != "???")
    print(f"Clientes únicos: {len(clients)}")
    
    # Top clients by revenue
    client_revenue = {}
    for r in rows:
        if isinstance(r.get("Ingreso"), (int, float)) and r.get("Cliente") != "???":
            client_revenue[r["Cliente"]] = client_revenue.get(r["Cliente"], 0) + r["Ingreso"]
    
    if client_revenue:
        print("\nTop 10 clientes por ingreso:")
        for client, rev in sorted(client_revenue.items(), key=lambda x: -x[1])[:10]:
            print(f"  {client:25s} Gs {rev:>15,.0f}")
    
    # Revenue by type
    type_revenue = {}
    type_qty = {}
    for r in rows:
        if isinstance(r.get("Ingreso"), (int, float)) and r.get("Concepto") != "???":
            c = r["Concepto"]
            type_revenue[c] = type_revenue.get(c, 0) + r["Ingreso"]
            type_qty[c] = type_qty.get(c, 0) + (r["Cantidad"] if isinstance(r["Cantidad"], (int, float)) else 0)
    
    if type_revenue:
        print("\nVentas por tipo de huevo:")
        for t in sorted(type_revenue.keys()):
            print(f"  {t:20s} {int(type_qty.get(t, 0)):>6} uds  Gs {type_revenue[t]:>15,.0f}")
    
    # Monthly revenue
    monthly = {}
    for r in rows:
        if isinstance(r.get("Ingreso"), (int, float)) and r.get("Mes") and r.get("Año"):
            key = f"{r['Año']}-{r['Mes']:02d}" if isinstance(r['Mes'], int) else None
            if key:
                monthly[key] = monthly.get(key, 0) + r["Ingreso"]
    
    if monthly:
        print("\nIngreso mensual:")
        for m in sorted(monthly.keys()):
            print(f"  {m}: Gs {monthly[m]:>15,.0f}")
    
    # Errors
    if errors:
        print(f"\n{'='*60}")
        print(f"ERRORES ({len(errors)}):")
        print("="*60)
        for e in errors[:50]:
            print(f"  {e}")
        if len(errors) > 50:
            print(f"  ... y {len(errors)-50} más")
    
    if skipped:
        print(f"\nNotas de pago/otros ignorados: {len(skipped)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_base = sys.argv[2] if len(sys.argv) > 2 else "ventas_parsed"
    
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    print(f"Parsing: {input_path}")
    rows, errors, skipped = parse_whatsapp_txt(input_path)
    
    print(f"Parsed {len(rows)} sale records, {len(errors)} errors, {len(skipped)} skipped")
    
    # Add computed columns
    rows = add_computed_columns(rows)
    
    # Write outputs
    output_dir = os.path.dirname(input_path) or "."
    csv_path = os.path.join(output_dir, f"{output_base}.csv")
    xlsx_path = os.path.join(output_dir, f"{output_base}.xlsx")
    
    write_csv(rows, csv_path)
    write_xlsx(rows, xlsx_path)
    
    # Print summary
    print_summary(rows, errors, skipped)
    
    # Write error log
    if errors:
        err_path = os.path.join(output_dir, f"{output_base}_errors.txt")
        with open(err_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(errors))
        print(f"\nError log: {err_path}")


if __name__ == "__main__":
    main()
