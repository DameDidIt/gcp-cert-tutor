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


def seed_flashcards(db_path: str) -> None:
    """Insert flashcards from flashcards.json."""
    data = json.loads((CONTENT_DIR / "flashcards.json").read_text())
    conn = get_connection(db_path)
    for card in data["flashcards"]:
        # Look up subtopic_id by name
        row = conn.execute(
            "SELECT id FROM subtopics WHERE name = ?", (card["subtopic"],)
        ).fetchone()
        subtopic_id = row["id"] if row else None
        conn.execute(
            "INSERT INTO flashcards (domain_id, subtopic_id, front, back, source) VALUES (?, ?, ?, ?, 'seeded')",
            (card["domain_id"], subtopic_id, card["front"], card["back"]),
        )
    conn.commit()
    conn.close()


def seed_questions(db_path: str) -> None:
    """Insert quiz questions from questions.json."""
    data = json.loads((CONTENT_DIR / "questions.json").read_text())
    conn = get_connection(db_path)
    for q in data["questions"]:
        row = conn.execute(
            "SELECT id FROM subtopics WHERE name = ?", (q["subtopic"],)
        ).fetchone()
        subtopic_id = row["id"] if row else None
        conn.execute(
            """INSERT INTO quiz_questions
            (domain_id, subtopic_id, stem, choice_a, choice_b, choice_c, choice_d, correct_answer, explanation, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'seeded')""",
            (q["domain_id"], subtopic_id, q["stem"], q["choice_a"], q["choice_b"], q["choice_c"], q["choice_d"], q["correct_answer"], q["explanation"]),
        )
    conn.commit()
    conn.close()


def seed_all(db_path: str) -> None:
    """Run all seed functions in order."""
    if is_seeded(db_path):
        return
    seed_domains(db_path)
    seed_study_plan(db_path)
    seed_flashcards(db_path)
    seed_questions(db_path)
