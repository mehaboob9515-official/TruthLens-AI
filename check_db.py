import sqlite3

conn = sqlite3.connect("truthlens.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM history")
rows = cursor.fetchall()

print(rows)

conn.close()