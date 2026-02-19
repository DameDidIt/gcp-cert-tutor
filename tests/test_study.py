# tests/test_study.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, complete_reading,
    complete_session_component, get_start_date, start_new_session,
    reset_all_progress,
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
