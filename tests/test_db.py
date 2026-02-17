"""Tests for database initialization and connection management."""
from gcp_tutor.db import init_db, get_connection


def test_init_db_creates_tables(tmp_db):
    init_db(tmp_db)
    conn = get_connection(tmp_db)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    expected = {
        "domains", "subtopics", "study_days", "flashcards",
        "quiz_questions", "user_progress", "quiz_results",
        "flashcard_results", "imported_content", "user_settings",
    }
    assert expected.issubset(tables)
    conn.close()


def test_init_db_is_idempotent(tmp_db):
    init_db(tmp_db)
    init_db(tmp_db)  # should not raise
    conn = get_connection(tmp_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    assert len(cursor.fetchall()) > 0
    conn.close()


def test_get_connection_returns_row_factory(tmp_db):
    init_db(tmp_db)
    conn = get_connection(tmp_db)
    conn.execute("INSERT INTO user_settings (key, value) VALUES ('test', 'val')")
    row = conn.execute("SELECT key, value FROM user_settings WHERE key='test'").fetchone()
    assert row["key"] == "test"
    conn.close()
