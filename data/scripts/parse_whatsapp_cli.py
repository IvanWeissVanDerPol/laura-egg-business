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


def parse_whatsapp_txt(input_txt_path):
    """
    Parse WhatsApp sales chat and return list of dicts.
    
    Handles formats like:
        10 A x 25 = 250.000
        1.5 B x 20 = 30.000
        52A x 21.5= 1.118.000
    
    Also detects client names and tracks dates.
    """

    # Regex: start of a WhatsApp message line
    # Handles both D/M/YYYY and DD/MM/YYYY, with or without AM/PM
    message_start_regex = re.compile(
        r'^(\d{1,2}/\d{1,2}/\d{4}),\s*\d{1,2}:\d{2}(?:\s*[ap]\.?\s*m\.?)?\s*-\s*(.+?):\s*(.*)'
    )

    # Sale line: "10 A x 25 = 250.000" or "52A x 21.5= 1.118.000"
    sale_line_regex = re.compile(
        r'^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s*x\s*(\d+(?:[.,]\d+)?)\s*=\s*([\d\.]+)\s*$'
    )

    # Lines with client-level info we want to capture
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

    with open(input_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_number += 1
            original_line = line.rstrip('\n')
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Check if this line starts a new WhatsApp message
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
                
                # The rest of the message line might contain client name or sale
                if rest:
                    # Check if rest is a sale line
                    sale_match = sale_line_regex.match(rest)
                    if sale_match:
                        _process_sale(sale_match, current_date, current_client, 
                                     original_line, line_number, current_sender,
                                     add_row, errors)
                    elif payment_regex.search(rest):
                        skipped_lines.append(f"L{line_number}: Payment note: {rest[:80]}")
                    elif 'x' not in rest.lower() and '=' not in rest:
                        current_client = rest.strip()
                    else:
                        # Could be unparseable sale
                        skipped_lines.append(f"L{line_number}: Unparsed msg content: {rest[:80]}")
                continue

            # Not a message start — continuation line
            sale_match = sale_line_regex.match(stripped_line)
            if sale_match:
                _process_sale(sale_match, current_date, current_client,
                             original_line, line_number, current_sender,
                             add_row, errors)
            elif payment_regex.search(stripped_line):
                skipped_lines.append(f"L{line_number}: Payment note: {stripped_line[:80]}")
            elif 'x' in stripped_line.lower() and '=' in stripped_line:
                # Has x and = but didn't match sale regex — potential parsing error
                errors.append(f"L{line_number}: Failed to parse sale: {stripped_line[:100]}")
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
            elif stripped_line.startswith(('<', 'Eliminaste', 'Se eliminó')):
                pass  # System messages
            else:
                # Likely a client name
                current_client = stripped_line.strip('* ')

    return parsed_rows, errors, skipped_lines


def _process_sale(match, current_date, current_client, original_line, 
                  line_number, current_sender, add_row, errors):
    """Process a regex match for a sale line."""
    cantidad_str = match.group(1).replace(',', '.')
    concepto_str = match.group(2).upper()
    precio_str = match.group(3).replace(',', '.')
    ingreso_str = match.group(4)

    try:
        cantidad = float(cantidad_str)
    except ValueError:
        cantidad = None
        errors.append(f"L{line_number}: Bad cantidad '{cantidad_str}'")

    try:
        precio_unitario = float(precio_str) * 1000
    except ValueError:
        precio_unitario = None
        errors.append(f"L{line_number}: Bad precio '{precio_str}'")

    clean_ingreso = ingreso_str.replace('.', '')
    try:
        ingreso_val = float(clean_ingreso)
    except ValueError:
        ingreso_val = None
        errors.append(f"L{line_number}: Bad ingreso '{ingreso_str}'")

    # Verify calculation
    if cantidad is not None and precio_unitario is not None and ingreso_val is not None:
        calculated = cantidad * precio_unitario
        if abs(calculated - ingreso_val) < 1:  # tolerance of 1 Gs
            check_result = "OK"
        else:
            check_result = f"MISMATCH(expected={int(calculated)},got={int(ingreso_val)})"
            errors.append(f"L{line_number}: {check_result}")
    else:
        check_result = "PARSE_ERROR"

    add_row(
        fecha=current_date or "???",
        cliente=current_client or "???",
        cantidad=cantidad if cantidad is not None else "???",
        concepto=concepto_str,
        precio=precio_unitario if precio_unitario is not None else "???",
        ingreso=ingreso_val if ingreso_val is not None else "???",
        check_result=check_result,
        raw_line=original_line,
        lineno=line_number,
        sender=current_sender,
    )


def add_computed_columns(rows):
    """Add TripNumber, Dia, Mes, Año columns."""
    # Parse dates
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
    month_dates = {}  # (year, month) -> set of dates
    for row in rows:
        if row["_dt"]:
            key = (row["_dt"].year, row["_dt"].month)
            if key not in month_dates:
                month_dates[key] = set()
            month_dates[key].add(row["_dt"].date())

    # Sort dates within each month and assign trip numbers
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
    
    print(f"\nTotal registros de venta: {total}")
    print(f"  OK:           {ok} ({ok*100//total if total else 0}%)")
    print(f"  Mismatch:     {mismatches}")
    print(f"  Parse errors: {parse_errors}")
    
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
            print(f"  {t:10s} {int(type_qty.get(t, 0)):>6} maples  Gs {type_revenue[t]:>15,.0f}")
    
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
