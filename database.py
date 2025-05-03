# database.py

import sqlite3

conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
)
""")
conn.commit()

def save_file(file_id, code):
    cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
    conn.commit()

def get_file(code):
    cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
    row = cur.fetchone()
    return row[0] if row else None
