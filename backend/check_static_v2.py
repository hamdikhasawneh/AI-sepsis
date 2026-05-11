import pandas as pd

excel_path = r"C:\Users\hrhkh\Downloads\icu_dst_simulation_data.xlsx"

# Inspect first few rows of Static_Features_127 without skipping header
df_static_raw = pd.read_excel(excel_path, sheet_name="Static_Features_127", header=None, nrows=5)
print("=== Static_Features_127 Raw Head (header=None) ===")
print(df_static_raw.to_string())
