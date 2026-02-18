# tests/test_flashcards.py
from datetime import date
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_flashcards
from gcp_tutor.flashcards import get_due_cards, get_cards_for_domain, record_flashcard_result

def test_get_due_cards_returns_new_cards(tmp_db):
    """Cards with no next_review date are due."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=10)
    assert len(cards) == 10

def test_get_cards_for_domain(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_cards_for_domain(tmp_db, domain_id=3, limit=5)
    assert len(cards) == 5
    assert all(c["domain_id"] == 3 for c in cards)

def test_record_flashcard_result_updates_sm2(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=1)
    card_id = cards[0]["id"]
    record_flashcard_result(tmp_db, card_id, rating=4)
    conn = get_connection(tmp_db)
    updated = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    assert updated["repetitions"] == 1
    assert updated["interval"] == 1
    result = conn.execute("SELECT * FROM flashcard_results WHERE flashcard_id = ?", (card_id,)).fetchone()
    assert result["rating"] == 4
    conn.close()
