import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT,
    source_name TEXT,
    title TEXT,
    url TEXT UNIQUE,
    published TEXT,
    summary TEXT,
    country TEXT,
    fetched_at TEXT,
    status TEXT DEFAULT 'new'
);
"""


class Database:
    def __init__(self, db_path: str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def save(self, items) -> int:
        """批量写入，URL 重复的自动跳过，返回新增条数。"""
        now = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        added = 0
        for it in items:
            if not it.url:
                continue
            try:
                cur.execute(
                    """INSERT INTO items
                       (source_id, source_name, title, url, published, summary, country, fetched_at)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(url) DO UPDATE SET
                         title=excluded.title,
                         published=CASE WHEN excluded.published != '' THEN excluded.published ELSE items.published END,
                         summary=excluded.summary""",
                    (it.source_id, it.source_name, it.title, it.url,
                     it.published, it.summary, it.country, now),
                )
                if cur.rowcount > 0:
                    added += 1
            except Exception:
                pass
        self.conn.commit()
        return added

    def summary(self):
        cur = self.conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        by_source = cur.execute(
            "SELECT source_name, COUNT(*) FROM items GROUP BY source_name"
        ).fetchall()
        return total, by_source

    def close(self):
        self.conn.close()
