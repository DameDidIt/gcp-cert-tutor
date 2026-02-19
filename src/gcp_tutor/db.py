"""Database initialization and connection management."""
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = str(Path.home() / ".gcp_tutor" / "tutor.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    section_number INTEGER NOT NULL,
    exam_weight REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS subtopics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS study_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_number INTEGER NOT NULL UNIQUE,
    domain_id INTEGER REFERENCES domains(id),
    reading_content TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    subtopic_id INTEGER REFERENCES subtopics(id),
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    source TEXT DEFAULT 'seeded',
    ease_factor REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    next_review TEXT
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    subtopic_id INTEGER REFERENCES subtopics(id),
    stem TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT NOT NULL,
    choice_d TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    source TEXT DEFAULT 'seeded'
);

CREATE TABLE IF NOT EXISTS user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_day INTEGER NOT NULL,
    completed_at TEXT,
    calendar_date TEXT,
    reading_done INTEGER DEFAULT 0,
    flashcards_done INTEGER DEFAULT 0,
    quiz_done INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_question_id INTEGER NOT NULL REFERENCES quiz_questions(id),
    user_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    answered_at TEXT
);

CREATE TABLE IF NOT EXISTS flashcard_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flashcard_id INTEGER NOT NULL REFERENCES flashcards(id),
    rating INTEGER NOT NULL,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS imported_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    domain_id INTEGER REFERENCES domains(id),
    content_text TEXT,
    imported_at TEXT
);

CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT
);

CREATE TABLE IF NOT EXISTS session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_day INTEGER NOT NULL,
    component TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    UNIQUE(session_day, component, item_id)
);
"""


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the database, creating all tables if they don't exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
