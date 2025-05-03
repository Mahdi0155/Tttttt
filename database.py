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
    print(f"Saving file_id: {file_id} with code: {code}")  # لاگ ذخیره کردن
    cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
    conn.commit()

def get_file(code):
    print(f"Getting file for code: {code}")  # لاگ دریافت فایل
    cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
    row = cur.fetchone()
    if row:
        print(f"Found file_id: {row[0]} for code: {code}")  # لاگ فایل پیدا شده
    else:
        print(f"No file found for code: {code}")  # لاگ اگر هیچ فایلی پیدا نشد
    return row[0] if row else None
