from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Mapping


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads(
  id TEXT PRIMARY KEY,
  platform TEXT,
  url TEXT,
  title TEXT,
  text TEXT,
  author TEXT,
  score INTEGER,
  followers INTEGER,
  created_ts REAL,
  draft TEXT
)
"""


class DB:
    """Simple SQLite-backed storage for leads and drafted replies."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def upsert_lead(self, lead: Mapping[str, object]) -> bool:
        """Insert a lead if it does not already exist.

        Returns True if the lead was newly inserted.
        """

        placeholders = (
            lead["id"],
            lead["platform"],
            lead["url"],
            lead["title"],
            lead["text"],
            lead["author"],
            lead.get("score"),
            lead.get("followers"),
            lead["created_ts"],
            lead.get("draft"),
        )
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO leads(
                    id, platform, url, title, text, author,
                    score, followers, created_ts, draft
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                placeholders,
            )
            self.conn.commit()
            return cur.rowcount == 1
        finally:
            cur.close()

    def fetch_all(self) -> List[Mapping[str, object]]:
        cur = self.conn.execute(
            "SELECT id, platform, url, title, text, author, score, followers, created_ts, draft FROM leads ORDER BY created_ts DESC"
        )
        columns = [c[0] for c in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return rows

    def fetch_undrafted(self, limit: int = 50) -> List[Mapping[str, object]]:
        cur = self.conn.execute(
            "SELECT id, platform, url, title, text, author, score, followers, created_ts FROM leads WHERE draft IS NULL ORDER BY created_ts DESC LIMIT ?",
            (limit,),
        )
        columns = [c[0] for c in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return rows

    def attach_draft(self, lead_id: str, draft: str) -> None:
        self.conn.execute("UPDATE leads SET draft = ? WHERE id = ?", (draft, lead_id))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
