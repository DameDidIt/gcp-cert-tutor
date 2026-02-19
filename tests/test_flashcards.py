# tests/test_flashcards.py
from datetime import date, timedelta
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


# --- Edge case tests ---


def test_get_due_cards_empty_db(tmp_db):
    """No cards seeded returns empty list."""
    init_db(tmp_db)
    cards = get_due_cards(tmp_db, limit=10)
    assert cards == []


def test_get_due_cards_all_reviewed_future(tmp_db):
    """Cards with future next_review are not due."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    # Set all cards to have a future review date
    future = (date.today() + timedelta(days=30)).isoformat()
    conn = get_connection(tmp_db)
    conn.execute("UPDATE flashcards SET next_review = ?", (future,))
    conn.commit()
    conn.close()
    cards = get_due_cards(tmp_db, limit=10)
    assert len(cards) == 0


def test_get_due_cards_past_review_date_included(tmp_db):
    """Cards with past next_review dates are due."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    # Set all cards to future except one to past
    future = (date.today() + timedelta(days=30)).isoformat()
    past = (date.today() - timedelta(days=1)).isoformat()
    conn = get_connection(tmp_db)
    conn.execute("UPDATE flashcards SET next_review = ?", (future,))
    conn.execute("UPDATE flashcards SET next_review = ? WHERE id = 1", (past,))
    conn.commit()
    conn.close()
    cards = get_due_cards(tmp_db, limit=10)
    assert len(cards) == 1
    assert cards[0]["id"] == 1


def test_get_due_cards_today_review_date_included(tmp_db):
    """Cards with today's next_review are due."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    future = (date.today() + timedelta(days=30)).isoformat()
    today = date.today().isoformat()
    conn = get_connection(tmp_db)
    conn.execute("UPDATE flashcards SET next_review = ?", (future,))
    conn.execute("UPDATE flashcards SET next_review = ? WHERE id = 1", (today,))
    conn.commit()
    conn.close()
    cards = get_due_cards(tmp_db, limit=10)
    assert len(cards) == 1


def test_get_due_cards_respects_limit(tmp_db):
    """Limit parameter caps the number of returned cards."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=3)
    assert len(cards) == 3


def test_get_cards_for_domain_nonexistent_domain(tmp_db):
    """Non-existent domain returns empty list."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_cards_for_domain(tmp_db, domain_id=999, limit=5)
    assert cards == []


def test_get_cards_for_domain_respects_review_date(tmp_db):
    """Domain cards with future review dates are excluded."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    future = (date.today() + timedelta(days=30)).isoformat()
    conn = get_connection(tmp_db)
    conn.execute("UPDATE flashcards SET next_review = ? WHERE domain_id = 3", (future,))
    conn.commit()
    conn.close()
    cards = get_cards_for_domain(tmp_db, domain_id=3, limit=5)
    assert len(cards) == 0


def test_record_flashcard_result_rating_zero_resets(tmp_db):
    """Rating 0 (complete blackout) resets SM-2 state."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=1)
    card_id = cards[0]["id"]
    # First review (correct)
    record_flashcard_result(tmp_db, card_id, rating=4)
    # Second review (blackout)
    record_flashcard_result(tmp_db, card_id, rating=0)
    conn = get_connection(tmp_db)
    updated = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    assert updated["repetitions"] == 0
    assert updated["interval"] == 1
    conn.close()


def test_record_flashcard_result_rating_five_increases_ease(tmp_db):
    """Rating 5 (easy) increases ease factor."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=1)
    card_id = cards[0]["id"]
    record_flashcard_result(tmp_db, card_id, rating=5)
    conn = get_connection(tmp_db)
    updated = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    assert updated["ease_factor"] > 2.5
    conn.close()


def test_record_flashcard_multiple_reviews_updates_interval(tmp_db):
    """Multiple correct reviews increase the interval progressively."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=1)
    card_id = cards[0]["id"]

    # Review 1: interval should be 1
    record_flashcard_result(tmp_db, card_id, rating=4)
    conn = get_connection(tmp_db)
    c = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    assert c["interval"] == 1
    assert c["repetitions"] == 1

    # Review 2: interval should be 6
    record_flashcard_result(tmp_db, card_id, rating=4)
    c = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    assert c["interval"] == 6
    assert c["repetitions"] == 2

    # Review 3: interval = round(6 * ease_factor)
    record_flashcard_result(tmp_db, card_id, rating=4)
    c = conn.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    assert c["interval"] > 6
    assert c["repetitions"] == 3
    conn.close()


def test_record_flashcard_result_creates_result_row(tmp_db):
    """Each review creates a flashcard_results entry with correct reviewed_at."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=1)
    card_id = cards[0]["id"]
    record_flashcard_result(tmp_db, card_id, rating=3)
    record_flashcard_result(tmp_db, card_id, rating=5)
    conn = get_connection(tmp_db)
    results = conn.execute(
        "SELECT * FROM flashcard_results WHERE flashcard_id = ? ORDER BY id", (card_id,)
    ).fetchall()
    assert len(results) == 2
    assert results[0]["rating"] == 3
    assert results[1]["rating"] == 5
    assert results[0]["reviewed_at"] == date.today().isoformat()
    conn.close()


def test_record_flashcard_result_sets_next_review(tmp_db):
    """After review, next_review is set to today + interval."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    cards = get_due_cards(tmp_db, limit=1)
    card_id = cards[0]["id"]
    record_flashcard_result(tmp_db, card_id, rating=4)
    conn = get_connection(tmp_db)
    updated = conn.execute("SELECT next_review FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    expected = (date.today() + timedelta(days=1)).isoformat()
    assert updated["next_review"] == expected
    conn.close()


def test_get_cards_for_each_domain_returns_correct_domain(tmp_db):
    """Each domain's cards are correctly filtered."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    for domain_id in range(1, 6):
        cards = get_cards_for_domain(tmp_db, domain_id=domain_id, limit=3)
        assert len(cards) > 0, f"Domain {domain_id} should have cards"
        assert all(c["domain_id"] == domain_id for c in cards)
