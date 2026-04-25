import pandas as pd
import os

data = {
    "Día": [1, 2, 3, 4, 5, 6, 7, 8] + list(range(9, 31)),
    "Aves": [2428, 2427, 2427, 2427, 2427, 2427, 2427, 2427] + [None]*22,
    "08:00": [515, 496, 508, 548, 581, 581, 542, 515] + [None]*22,
    "10:00": [742, 800, 1017, 905, 931, 949, 1050, 931] + [None]*22,  
    "16:00": [678, 615, 397, 465, 434, 461, 400, 578] + [None]*22,  
    "Total_Huevos": [1935, 1911, 1922, 1918, 1946, 1991, 1992, 2027] + [None]*22,
    "Maple_A": [45, 42, 47, 43, 47, 43, 43, 48] + [None]*22,
    "Maple_S": [7, 7, 0, 6, 5, 5, 4, 6] + [None]*22,
    "Maple_J": [0, 0, 0, 0, 0, 0, 0, 0] + [None]*22,
    "Maple_B": [12, 14, 15, 15, 17, 17, 19, 13] + [None]*22,
    "Maple_C": [0, 0, 0, 0, 0, 0, 0, 0] + [None]*22,
    "Total_Maples": [64, 63, 62, 64, 69, 65, 66, 67] + [None]*22,
    "%Postura": [79.7, 78.7, 79.2, 79.0, 80.2, 82.0, 82.1, 83.5] + [None]*22
}

df = pd.DataFrame(data)

for i in range(8):
    aves = df.at[i, "Aves"]
    huevos = df.at[i, "Total_Huevos"]
    if pd.notna(aves) and pd.notna(huevos):
        df.at[i, "%Postura"] = round((huevos / aves) * 100, 1)

output_path = r"c:\Users\jandr\Documents\laura-egg-business\00_fuente_de_verdad\datos_crudos\produccion_G1_abril_2026.csv"
df.to_csv(output_path, index=False, sep=";", decimal=",")
print(f"CSV file created successfully at {output_path}")
