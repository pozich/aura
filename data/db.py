import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "aura.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB done: {DB_PATH}")
