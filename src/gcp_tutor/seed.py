"""Seed the database with exam domains, subtopics, and study plan."""
import json
from pathlib import Path
from gcp_tutor.db import get_connection

CONTENT_DIR = Path(__file__).parent / "content"


def is_seeded(db_path: str) -> bool:
    """Check whether the database has already been seeded with domains."""
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
    conn.close()
    return count > 0


def seed_domains(db_path: str) -> None:
    """Insert all exam domains and subtopics from domains.json."""
    data = json.loads((CONTENT_DIR / "domains.json").read_text())
    conn = get_connection(db_path)
    for domain in data["domains"]:
        conn.execute(
            "INSERT OR IGNORE INTO domains (id, name, section_number, exam_weight, description) VALUES (?, ?, ?, ?, ?)",
            (domain["id"], domain["name"], domain["section_number"], domain["exam_weight"], domain["description"]),
        )
        for subtopic in domain["subtopics"]:
            conn.execute(
                "INSERT INTO subtopics (domain_id, name, description) VALUES (?, ?, ?)",
                (domain["id"], subtopic["name"], subtopic["description"]),
            )
    conn.commit()
    conn.close()


def seed_study_plan(db_path: str) -> None:
    """Create the 30-day study plan, ordered by exam weight (heaviest first)."""
    # Domain order by exam weight: 3(25%), 1(20%), 4(20%), 2(17.5%), 5(17.5%)
    plan = [
        (3, 6),    # Days 1-6
        (1, 4),    # Days 7-10
        (4, 4),    # Days 11-14
        (2, 4),    # Days 15-18
        (5, 4),    # Days 19-22
        (None, 4), # Days 23-26: mixed review
        (None, 2), # Days 27-28: practice exams
        (None, 2), # Days 29-30: final review
    ]
    conn = get_connection(db_path)
    day = 1
    for domain_id, count in plan:
        for _ in range(count):
            conn.execute(
                "INSERT INTO study_days (day_number, domain_id, status) VALUES (?, ?, 'pending')",
                (day, domain_id),
            )
            day += 1
    conn.commit()
    conn.close()
