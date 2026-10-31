import sqlite3
import pytest

from data.db import SCHEMA_PATH


@pytest.fixture
def db_conn(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()


@pytest.fixture
def seeded_db(db_conn):
    db_conn.execute(
        "INSERT INTO books (title, author, pages) VALUES (?, ?, ?)",
        ("Мир как воля и представление", "А. Шопенгауэр", 512),
    )
    book_id = db_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    db_conn.execute(
        "INSERT INTO chapters (book_id, idx, title, text, page_start) VALUES (?, ?, ?, ?, ?)",
        (book_id, 1, "Введение", "Пример текста главы для теста", 1),
    )
    db_conn.commit()
    return db_conn
