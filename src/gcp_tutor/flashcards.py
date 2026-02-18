"""Flashcard session logic with SM-2 scheduling."""
from datetime import date, timedelta
from gcp_tutor.db import get_connection
from gcp_tutor.sm2 import sm2_update


def get_due_cards(db_path: str, limit: int = 15) -> list:
    conn = get_connection(db_path)
    today = date.today().isoformat()
    cards = conn.execute(
        """SELECT * FROM flashcards
        WHERE next_review IS NULL OR next_review <= ?
        ORDER BY next_review ASC NULLS FIRST, RANDOM()
        LIMIT ?""",
        (today, limit),
    ).fetchall()
    conn.close()
    return cards


def get_cards_for_domain(db_path: str, domain_id: int, limit: int = 15) -> list:
    conn = get_connection(db_path)
    today = date.today().isoformat()
    cards = conn.execute(
        """SELECT * FROM flashcards
        WHERE domain_id = ? AND (next_review IS NULL OR next_review <= ?)
        ORDER BY next_review ASC NULLS FIRST, RANDOM()
        LIMIT ?""",
        (domain_id, today, limit),
    ).fetchall()
    conn.close()
    return cards


def record_flashcard_result(db_path: str, card_id: int, rating: int) -> None:
    conn = get_connection(db_path)
    card = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    updated = sm2_update(
        quality=rating,
        repetitions=card["repetitions"],
        ease_factor=card["ease_factor"],
        interval=card["interval"],
    )
    next_review = (date.today() + timedelta(days=updated["interval"])).isoformat()
    conn.execute(
        """UPDATE flashcards SET ease_factor=?, interval=?, repetitions=?, next_review=?
        WHERE id=?""",
        (updated["ease_factor"], updated["interval"], updated["repetitions"], next_review, card_id),
    )
    conn.execute(
        "INSERT INTO flashcard_results (flashcard_id, rating, reviewed_at) VALUES (?, ?, ?)",
        (card_id, rating, date.today().isoformat()),
    )
    conn.commit()
    conn.close()
