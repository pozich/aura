import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "aura.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, coltype: str
) -> None:
    existing = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db() -> None:
    conn = get_connection()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    # schema.sql CREATE TABLE IF NOT EXISTS не трогает уже существующие таблицы —
    # для новых колонок в уже созданной базе нужна явная миграция.
    _ensure_column(conn, "books", "source_path", "TEXT")
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


def list_categories() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return rows


def add_category(name: str) -> int:
    conn = get_connection()
    cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_category(category_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()


def set_book_category(book_id: int, category_id: int | None) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE books SET category_id = ? WHERE id = ?", (category_id, book_id)
    )
    conn.commit()
    conn.close()


def list_books() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM books ORDER BY added_at DESC").fetchall()
    conn.close()
    return rows


def get_book(book_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return row


def update_book_info(book_id: int, title: str | None = None, author: str | None = None) -> None:
    conn = get_connection()
    if title:
        conn.execute("UPDATE books SET title = ? WHERE id = ?", (title, book_id))
    if author:
        conn.execute("UPDATE books SET author = ? WHERE id = ?", (author, book_id))
    conn.commit()
    conn.close()


def set_book_pages(book_id: int, pages: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE books SET pages = ? WHERE id = ?", (pages, book_id))
    conn.commit()
    conn.close()


def add_book(
    title: str,
    author: str | None = None,
    pages: int | None = None,
    cover_path: str | None = None,
    category_id: int | None = None,
    source_path: str | None = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO books (title, author, pages, cover_path, category_id, source_path)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (title, author, pages, cover_path, category_id, source_path),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_book(book_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()


def set_book_cover(book_id: int, cover_path: str | None) -> None:
    conn = get_connection()
    conn.execute("UPDATE books SET cover_path = ? WHERE id = ?", (cover_path, book_id))
    conn.commit()
    conn.close()


def get_reading_progress(book_id: int) -> int | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_page FROM reading_progress WHERE book_id = ?", (book_id,)
    ).fetchone()
    conn.close()
    return row["last_page"] if row else None


def set_reading_progress(book_id: int, last_page: int) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO reading_progress (book_id, last_page) VALUES (?, ?)
        ON CONFLICT (book_id) DO UPDATE SET last_page = excluded.last_page
        """,
        (book_id, last_page),
    )
    conn.commit()
    conn.close()


def list_notebooks() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM notebooks ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def add_notebook(title: str, text: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO notebooks (title, text) VALUES (?, ?)", (title, text)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_notebook(
    notebook_id: int, title: str | None = None, text: str | None = None
) -> None:
    conn = get_connection()
    if title is not None:
        conn.execute(
            "UPDATE notebooks SET title = ? WHERE id = ?", (title, notebook_id)
        )
    if text is not None:
        conn.execute("UPDATE notebooks SET text = ? WHERE id = ?", (text, notebook_id))
    conn.commit()
    conn.close()


def delete_notebook(notebook_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
    conn.commit()
    conn.close()


def add_chapter(
    book_id: int, idx: int, title: str | None, text: str, page_start: int | None = None
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO chapters (book_id, idx, title, text, page_start) VALUES (?, ?, ?, ?, ?)",
        (book_id, idx, title, text, page_start),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_chapters(book_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chapters WHERE book_id = ? ORDER BY idx", (book_id,)
    ).fetchall()
    conn.close()
    return rows


def delete_chapters_for_book(book_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM chapters WHERE book_id = ?", (book_id,))
    conn.commit()
    conn.close()


def add_chat_message(role: str, content: str, book_id: int | None = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO chat_messages (book_id, role, content) VALUES (?, ?, ?)",
        (book_id, role, content),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_chat_messages() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM chat_messages ORDER BY id").fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print(f"DB done: {DB_PATH}")
