import pandas as pd

excel_path = r"C:\Users\hrhkh\Downloads\icu_dst_simulation_data.xlsx"

# Read row 0 and 1
df_rows = pd.read_excel(excel_path, sheet_name="Static_Features_127", header=None, nrows=2)
print("=== Static_Features_127 Row 0 ===")
print(df_rows.iloc[0].tolist()[:10])
print("\n=== Static_Features_127 Row 1 ===")
print(df_rows.iloc[1].tolist()[:10])
