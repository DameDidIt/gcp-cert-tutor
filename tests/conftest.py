import os
import sqlite3
import pytest

@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path for tests."""
    db_path = str(tmp_path / "test_tutor.db")
    return db_path
