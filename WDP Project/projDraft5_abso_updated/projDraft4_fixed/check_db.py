import sqlite3
from pathlib import Path

db_path = Path('instance') / 'reconnect.db'
print('DB path:', db_path.resolve())
print('Exists:', db_path.exists())

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', tables)

conn.close()
