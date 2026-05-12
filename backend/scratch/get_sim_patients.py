import sqlite3
conn = sqlite3.connect('sepsis.db')
cur = conn.cursor()
cur.execute("SELECT patient_id, full_name, status, ward_name FROM patients WHERE ward_name = 'Simulation Lab'")
print(cur.fetchall())
