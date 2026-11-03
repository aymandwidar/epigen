"""SQLite storage for memories."""

import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("EPIGEN_DB", os.path.join("data", "epigen.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    angle TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    salience REAL NOT NULL,
    source TEXT NOT NULL,
    embedding TEXT NOT NULL
)
"""


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def save_memory(conn: sqlite3.Connection, mem: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO memories"
        " (id, angle, text, created_at, salience, source, embedding)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            mem["id"],
            mem["angle"],
            mem["text"],
            mem["created_at"],
            mem["salience"],
            mem["source"],
            json.dumps(mem["embedding"]),
        ),
    )


def load_memories(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM memories ORDER BY created_at").fetchall()
    mems = []
    for r in rows:
        mems.append(
            {
                "id": r["id"],
                "angle": r["angle"],
                "text": r["text"],
                "created_at": r["created_at"],
                "salience": r["salience"],
                "source": r["source"],
                "embedding": json.loads(r["embedding"]),
            }
        )
    return mems


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
