# tests/test_study.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, complete_reading,
    complete_session_component, get_start_date, start_new_session,
    reset_all_progress, record_session_item, get_completed_session_items,
    clear_session_items, is_session_incomplete,
)

def test_get_current_session_day_default(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    assert get_current_session_day(tmp_db) == 1

def test_start_new_session(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    progress = start_new_session(tmp_db)
    assert progress["session_day"] == 1

def test_get_todays_plan(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    plan = get_todays_plan(tmp_db)
    assert plan is not None
    assert plan["day_number"] == 1
    assert plan["domain_id"] == 3  # First 6 days = domain 3

def test_complete_session_component(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, session_day=1, component="reading")
    conn = get_connection(tmp_db)
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = 1").fetchone()
    assert progress["reading_done"] == 1
    conn.close()

def test_reset_all_progress(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    # Complete a full session to build up progress
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    complete_session_component(tmp_db, 1, "flashcards")
    complete_session_component(tmp_db, 1, "quiz")
    assert get_current_session_day(tmp_db) == 2

    reset_all_progress(tmp_db)

    # Session day back to 1
    assert get_current_session_day(tmp_db) == 1
    # No progress rows
    conn = get_connection(tmp_db)
    assert conn.execute("SELECT COUNT(*) FROM user_progress").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM quiz_results").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM flashcard_results").fetchone()[0] == 0
    # SM-2 state reset
    card = conn.execute("SELECT * FROM flashcards LIMIT 1").fetchone()
    assert card["ease_factor"] == 2.5
    assert card["interval"] == 0
    assert card["repetitions"] == 0
    assert card["next_review"] is None
    conn.close()

def test_record_and_get_session_items(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=5)
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=10)
    items = get_completed_session_items(tmp_db, session_day=1, component="flashcard")
    assert items == {5, 10}

def test_record_session_item_duplicate_ignored(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=1, component="quiz", item_id=3)
    record_session_item(tmp_db, session_day=1, component="quiz", item_id=3)
    items = get_completed_session_items(tmp_db, session_day=1, component="quiz")
    assert items == {3}

def test_clear_session_items(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=5)
    clear_session_items(tmp_db, session_day=1)
    items = get_completed_session_items(tmp_db, session_day=1, component="flashcard")
    assert items == set()

def test_is_session_incomplete_no_progress(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    assert is_session_incomplete(tmp_db) is False

def test_is_session_incomplete_partial(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    assert is_session_incomplete(tmp_db) is True

def test_is_session_incomplete_all_done(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    complete_session_component(tmp_db, 1, "flashcards")
    complete_session_component(tmp_db, 1, "quiz")
    assert is_session_incomplete(tmp_db) is False

def test_reset_clears_session_items(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=5)
    reset_all_progress(tmp_db)
    items = get_completed_session_items(tmp_db, session_day=1, component="flashcard")
    assert items == set()
