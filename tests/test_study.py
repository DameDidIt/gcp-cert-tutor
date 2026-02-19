# tests/test_study.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, complete_reading,
    complete_session_component, get_start_date, start_new_session,
    reset_all_progress, record_session_item, get_completed_session_items,
    clear_session_items, is_session_incomplete, restart_session,
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


def test_restart_session(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=5)

    restart_session(tmp_db, session_day=1)

    conn = get_connection(tmp_db)
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = 1").fetchone()
    conn.close()
    assert progress["reading_done"] == 0
    assert progress["flashcards_done"] == 0
    assert progress["quiz_done"] == 0
    assert get_completed_session_items(tmp_db, 1, "flashcard") == set()


# --- Edge case tests ---


def test_full_session_advances_to_next_day(tmp_db):
    """Completing all 3 components advances session day from 1 to 2."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    assert get_current_session_day(tmp_db) == 1
    complete_session_component(tmp_db, 1, "reading")
    assert get_current_session_day(tmp_db) == 1  # not yet
    complete_session_component(tmp_db, 1, "flashcards")
    assert get_current_session_day(tmp_db) == 1  # not yet
    complete_session_component(tmp_db, 1, "quiz")
    assert get_current_session_day(tmp_db) == 2  # now advanced


def test_full_session_sets_completed_at(tmp_db):
    """Completing all components sets completed_at timestamp."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    complete_session_component(tmp_db, 1, "flashcards")
    complete_session_component(tmp_db, 1, "quiz")
    conn = get_connection(tmp_db)
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = 1").fetchone()
    conn.close()
    assert progress["completed_at"] is not None


def test_start_new_session_idempotent(tmp_db):
    """Calling start_new_session twice returns same progress row."""
    init_db(tmp_db)
    seed_all(tmp_db)
    p1 = start_new_session(tmp_db)
    p2 = start_new_session(tmp_db)
    assert p1["id"] == p2["id"]
    assert p1["session_day"] == p2["session_day"]


def test_start_new_session_sets_start_date(tmp_db):
    """First session sets the start_date setting."""
    init_db(tmp_db)
    seed_all(tmp_db)
    assert get_start_date(tmp_db) is None
    start_new_session(tmp_db)
    assert get_start_date(tmp_db) is not None


def test_start_new_session_preserves_start_date(tmp_db):
    """Second session call doesn't overwrite start_date."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    first_date = get_start_date(tmp_db)
    # Complete day 1 to advance
    complete_session_component(tmp_db, 1, "reading")
    complete_session_component(tmp_db, 1, "flashcards")
    complete_session_component(tmp_db, 1, "quiz")
    start_new_session(tmp_db)
    assert get_start_date(tmp_db) == first_date


def test_get_todays_plan_review_days_have_null_domain(tmp_db):
    """Days 23-30 are review/practice exam days with null domain_id."""
    init_db(tmp_db)
    seed_all(tmp_db)
    conn = get_connection(tmp_db)
    review_days = conn.execute(
        "SELECT * FROM study_days WHERE day_number >= 23 ORDER BY day_number"
    ).fetchall()
    conn.close()
    for day in review_days:
        assert day["domain_id"] is None


def test_complete_two_sessions_consecutively(tmp_db):
    """Completing day 1 and day 2 advances to day 3."""
    init_db(tmp_db)
    seed_all(tmp_db)
    # Day 1
    start_new_session(tmp_db)
    for comp in ("reading", "flashcards", "quiz"):
        complete_session_component(tmp_db, 1, comp)
    assert get_current_session_day(tmp_db) == 2
    # Day 2
    start_new_session(tmp_db)
    for comp in ("reading", "flashcards", "quiz"):
        complete_session_component(tmp_db, 2, comp)
    assert get_current_session_day(tmp_db) == 3


def test_get_calendar_days_elapsed_no_start(tmp_db):
    """Returns 0 when no start date is set."""
    init_db(tmp_db)
    seed_all(tmp_db)
    from gcp_tutor.study import get_calendar_days_elapsed
    assert get_calendar_days_elapsed(tmp_db) == 0


def test_get_calendar_days_elapsed_started_today(tmp_db):
    """Returns 1 when started today."""
    init_db(tmp_db)
    seed_all(tmp_db)
    from gcp_tutor.study import get_calendar_days_elapsed
    start_new_session(tmp_db)
    assert get_calendar_days_elapsed(tmp_db) == 1


def test_get_completed_sessions_count(tmp_db):
    """Counts only fully completed sessions."""
    init_db(tmp_db)
    seed_all(tmp_db)
    from gcp_tutor.study import get_completed_sessions
    assert get_completed_sessions(tmp_db) == 0
    # Complete day 1
    start_new_session(tmp_db)
    for comp in ("reading", "flashcards", "quiz"):
        complete_session_component(tmp_db, 1, comp)
    assert get_completed_sessions(tmp_db) == 1
    # Start day 2 but don't complete
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 2, "reading")
    assert get_completed_sessions(tmp_db) == 1  # still 1


def test_get_total_sessions(tmp_db):
    """Total sessions should be 30 after seeding."""
    init_db(tmp_db)
    seed_all(tmp_db)
    from gcp_tutor.study import get_total_sessions
    assert get_total_sessions(tmp_db) == 30


def test_get_set_setting(tmp_db):
    """Settings can be stored and retrieved."""
    init_db(tmp_db)
    from gcp_tutor.study import get_setting, set_setting
    assert get_setting(tmp_db, "test_key") is None
    assert get_setting(tmp_db, "test_key", "default") == "default"
    set_setting(tmp_db, "test_key", "value1")
    assert get_setting(tmp_db, "test_key") == "value1"
    set_setting(tmp_db, "test_key", "value2")  # upsert
    assert get_setting(tmp_db, "test_key") == "value2"


def test_complete_reading_convenience(tmp_db):
    """complete_reading is a shortcut for complete_session_component reading."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_reading(tmp_db, session_day=1)
    conn = get_connection(tmp_db)
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = 1").fetchone()
    conn.close()
    assert progress["reading_done"] == 1


def test_restart_preserves_day_number(tmp_db):
    """Restarting a session doesn't change current_session_day."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    restart_session(tmp_db, session_day=1)
    assert get_current_session_day(tmp_db) == 1


def test_session_items_isolated_by_component(tmp_db):
    """Session items for different components don't interfere."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=5)
    record_session_item(tmp_db, session_day=1, component="quiz", item_id=5)
    fc_items = get_completed_session_items(tmp_db, session_day=1, component="flashcard")
    quiz_items = get_completed_session_items(tmp_db, session_day=1, component="quiz")
    assert fc_items == {5}
    assert quiz_items == {5}
    # Clear only flashcard items
    clear_session_items(tmp_db, session_day=1)
    fc_items = get_completed_session_items(tmp_db, session_day=1, component="flashcard")
    assert fc_items == set()


def test_session_items_isolated_by_day(tmp_db):
    """Session items for different days don't interfere."""
    init_db(tmp_db)
    seed_all(tmp_db)
    # Complete day 1
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=1, component="flashcard", item_id=1)
    for comp in ("reading", "flashcards", "quiz"):
        complete_session_component(tmp_db, 1, comp)
    # Day 2
    start_new_session(tmp_db)
    record_session_item(tmp_db, session_day=2, component="flashcard", item_id=2)
    day1_items = get_completed_session_items(tmp_db, session_day=1, component="flashcard")
    day2_items = get_completed_session_items(tmp_db, session_day=2, component="flashcard")
    assert day1_items == {1}
    assert day2_items == {2}
