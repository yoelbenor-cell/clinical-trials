import sqlite3
conn = sqlite3.connect('trials.db')
cur = conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table'")
for row in cur.fetchall():
    print(row[0])
    print()

# Check if enrollment field exists
cur.execute("PRAGMA table_info(trials)")
print("trials columns:")
for col in cur.fetchall():
    print(" ", col)
conn.close()
