import pandas as pd

excel_path = r"C:\Users\hrhkh\Downloads\icu_dst_simulation_data.xlsx"

# Inspect Hourly_Sequence_25
df_hourly = pd.read_excel(excel_path, sheet_name="Hourly_Sequence_25", header=1)
print("=== Hourly_Sequence_25 Columns ===")
print(df_hourly.columns.tolist())
print("\n=== First 2 rows of Hourly_Sequence_25 ===")
print(df_hourly.head(2).to_string())

# Inspect Static_Features_127
df_static = pd.read_excel(excel_path, sheet_name="Static_Features_127")
print("\n=== Static_Features_127 Columns ===")
print(df_static.columns.tolist())
print("\n=== First 2 rows of Static_Features_127 ===")
print(df_static.head(2).to_string())
