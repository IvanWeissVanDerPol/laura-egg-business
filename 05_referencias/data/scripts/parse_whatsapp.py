import re
import pandas as pd
from datetime import datetime

# For file dialogs:
import tkinter as tk
from tkinter import filedialog

def parse_whatsapp_txt(input_txt_path, output_xlsx_path):
    """
    Reads a WhatsApp .txt export of egg sales messages and writes the parsed
    rows to an Excel file with columns:
        Fecha, Cliente, Cantidad, Concepto, Precio Unitario, Ingreso, Check, Raw, TripNumber

    - Allows decimal 'cantidad' and 'precio_unitario' (e.g. "1.5 B x 20" or "52 A x 21.5").
    - Multiplies precio_unitario by 1000.
    - Checks if ingreso == cantidad * precio_unitario (within a tiny margin).
    - Always stores the original line in a 'Raw' column, for reference.
    - Adds a 'TripNumber' column, which counts how many distinct dates occur in that month
      (i.e. the nth unique date in the month).
    """

    # Regex to detect the start of a WhatsApp message (DD/MM/YYYY, HH:MM - Sender:)
    message_start_regex = re.compile(
        r'^(\d{1,2}/\d{1,2}/\d{4}),\s*\d{1,2}:\d{2}\s*-\s*(.+?):'
    )

    # Regex to parse lines like "52A x 21.5= 1.118.000" or "1.5 B x 20 = 30.000"
    # Also accepts decimal comma or dot for quantity and price: [.,]
    sale_line_regex = re.compile(
        r'^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s*x\s*(\d+(?:[.,]\d+)?)\s*=\s*([\d\.]+)\s*$'
    )

    parsed_rows = []

    current_date = None
    current_client = None

    def add_row(fecha, cliente, cantidad, concepto, precio, ingreso, check_result, raw_line):
        parsed_rows.append({
            "Fecha": fecha,
            "Cliente": cliente,
            "Cantidad": cantidad,
            "Concepto": concepto,
            "Precio Unitario": precio,
            "Ingreso": ingreso,
            " - ": "",
            "Check": check_result,
            "Original": raw_line
        })

    with open(input_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            original_line = line.rstrip('\n')  # store exactly what was read (minus trailing \n)
            stripped_line = line.strip()
            if not stripped_line:
                continue  # skip empty lines

            # Check if this line starts a new WhatsApp message
            msg_match = message_start_regex.match(stripped_line)
            if msg_match:
                date_str = msg_match.group(1)  # e.g. "27/8/2024"
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                    current_date = dt.strftime('%d/%m/%Y')
                except ValueError:
                    current_date = f"???:{date_str}"
                continue

            # Check if this line matches the "cantidad concept x precio = ingreso" pattern
            sale_match = sale_line_regex.match(stripped_line)
            if sale_match:
                cantidad_str = sale_match.group(1)    # e.g. "1.5" or "52" or "1,5"
                concepto_str = sale_match.group(2)    # e.g. "B", "A", "S"
                precio_str = sale_match.group(3)      # e.g. "20", "21.5", "21,5"
                ingreso_str = sale_match.group(4)     # e.g. "30.000", "1.118.000"

                # Normalize commas to dots in quantity & price
                cantidad_str = cantidad_str.replace(',', '.')
                precio_str = precio_str.replace(',', '.')

                # Parse quantity
                try:
                    cantidad = float(cantidad_str)
                except ValueError:
                    cantidad = f"???({cantidad_str})"

                concepto = concepto_str.upper()

                # Parse price, then multiply by 1000
                try:
                    precio_unitario = float(precio_str) * 1000
                except ValueError:
                    precio_unitario = f"???({precio_str})"

                # Parse ingreso: remove '.' then interpret as float
                clean_ingreso = ingreso_str.replace('.', '')
                try:
                    ingreso_val = float(clean_ingreso)
                except ValueError:
                    ingreso_val = f"???({ingreso_str})"

                # Check if ingreso == cantidad * precio_unitario
                # (only if we have valid floats)
                if (isinstance(cantidad, float) and 
                    isinstance(precio_unitario, float) and
                    isinstance(ingreso_val, float)):
                    calculated = cantidad * precio_unitario
                    if abs(calculated - ingreso_val) < 0.001:
                        check_result = "OK"
                    else:
                        check_result = "Mismatch"
                else:
                    check_result = "???"

                add_row(
                    fecha=current_date if current_date else "???DateMissing",
                    cliente=current_client if current_client else "???ClientMissing",
                    cantidad=cantidad,
                    concepto=concepto,
                    precio=precio_unitario,
                    ingreso=ingreso_val,
                    check_result=check_result,
                    raw_line=original_line
                )

            else:
                # If no 'x' or '=' is found, likely it's the client name
                if ' x ' not in stripped_line and '=' not in stripped_line:
                    current_client = stripped_line
                else:
                    # Unparseable line with 'x' or '=' => store placeholders
                    add_row(
                        fecha=current_date if current_date else "???DateMissing",
                        cliente=current_client if current_client else "???ClientMissing",
                        cantidad="???",
                        concepto="???",
                        precio="???",
                        ingreso="???",
                        check_result="???",
                        raw_line=original_line
                    )

    # Build a DataFrame
    df = pd.DataFrame(
        parsed_rows,
        columns=[
            "Fecha",
            "Cliente",
            "Cantidad",
            "Concepto",
            "Precio Unitario",
            "Ingreso",
            "Check",
            "Raw"
        ]
    )

    # --- Add a "TripNumber" column, counting how many distinct dates so far in each month ---
    # 1) Convert Fecha into an actual datetime, ignoring rows that are malformed
    def try_parse_date(d):
        # This helper tries dd/mm/yyyy
        # If it fails, returns NaT, so we can skip those in ranking
        try:
            return datetime.strptime(d, '%d/%m/%Y')
        except:
            return pd.NaT

    df["Date_dt"] = df["Fecha"].apply(try_parse_date)

    # 2) Group by year-month and apply a "dense rank" over the date
    #    so that the nth unique date in that month is (1, 2, 3, etc.)
    #    If Date_dt is NaT, they won't get a rank (it becomes NaN).
    df["TripNumber"] = (
        df.groupby([df["Date_dt"].dt.year, df["Date_dt"].dt.month])["Date_dt"]
          .transform(lambda series_of_dates: series_of_dates.rank(method='dense').astype('Int64'))
    )

    # 3) Optionally, drop the helper Date_dt column if you don't want it in the final Excel
    #    or keep it for debugging. Here, I'll keep it for demonstration.
    #    If you prefer not to see it, uncomment the line below:
    # -- Add day, month, and year columns --
    df["Dia"] = df["Date_dt"].dt.day
    df["Mes"] = df["Date_dt"].dt.month
    df["Año"] = df["Date_dt"].dt.year

	# -- Now drop the helper Date_dt column --
    df = df.drop(columns=["Date_dt"])

    # Write the final to Excel
    df.to_excel(output_xlsx_path, index=False)
    print(f"Done! Parsed data has been written to {output_xlsx_path}.")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # Ask the user to pick the input .txt file
    input_txt = filedialog.askopenfilename(
        title="Select the WhatsApp text export",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not input_txt:
        print("No file was selected. Exiting.")
        exit()

    # Ask the user for an output .xlsx file to save
    output_xlsx = filedialog.asksaveasfilename(
        title="Save output Excel file as",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )
    if not output_xlsx:
        print("No output file specified. Exiting.")
        exit()

    parse_whatsapp_txt(input_txt, output_xlsx)
