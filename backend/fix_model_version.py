import sqlite3

conn = sqlite3.connect('sepsis.db')
cur = conn.cursor()
cur.execute("UPDATE predictions SET model_version = 'Dynamic Survival Transformer' WHERE model_version != 'Dynamic Survival Transformer'")
conn.commit()
print(f"Updated {cur.rowcount} rows to 'Dynamic Survival Transformer'")
conn.close()
