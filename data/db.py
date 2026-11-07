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


def list_api_keys() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM api_keys ORDER BY id").fetchall()
    conn.close()
    return rows


def add_api_key(label: str, key: str, model_default: str | None = None) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO api_keys (label, key, model_default, is_active) VALUES (?, ?, ?, 0)",
        (label, key, model_default),
    )
    conn.commit()
    conn.close()


def set_active_api_key(key_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE api_keys SET is_active = 0")
    conn.execute("UPDATE api_keys SET is_active = 1 WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()


def delete_api_key(key_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB done: {DB_PATH}")
