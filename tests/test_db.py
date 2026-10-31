def test_schema_creates_all_tables(db_conn):
    tables = {
        row[0]
        for row in db_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = {
        "books",
        "chapters",
        "chapter_segments",
        "notes",
        "notebooks",
        "chat_messages",
        "api_keys",
        "usage_log",
        "reading_progress",
        "ahp_criteria",
        "ahp_results",
    }
    assert expected <= tables


def test_seeded_db_has_book(seeded_db):
    row = seeded_db.execute("SELECT title FROM books").fetchone()
    assert row["title"] == "Мир как воля и представление"
