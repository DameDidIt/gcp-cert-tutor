import pytest
from unittest.mock import patch
from gcp_tutor.app import SessionExitRequested, session_prompt, session_int_prompt


def test_session_exit_requested_is_exception():
    with pytest.raises(SessionExitRequested):
        raise SessionExitRequested()


def test_session_prompt_raises_on_q():
    with patch("gcp_tutor.app.Prompt.ask", return_value="q"):
        with pytest.raises(SessionExitRequested):
            session_prompt("test prompt")


def test_session_prompt_raises_on_menu():
    with patch("gcp_tutor.app.Prompt.ask", return_value="menu"):
        with pytest.raises(SessionExitRequested):
            session_prompt("test prompt")


def test_session_prompt_returns_normal_input():
    with patch("gcp_tutor.app.Prompt.ask", return_value="hello"):
        result = session_prompt("test prompt")
        assert result == "hello"


def test_session_int_prompt_raises_on_q():
    with patch("gcp_tutor.app.Prompt.ask", return_value="q"):
        with pytest.raises(SessionExitRequested):
            session_int_prompt("rate", choices=["0","1","2","3","4","5"])


def test_session_int_prompt_returns_normal_input():
    with patch("gcp_tutor.app.Prompt.ask", return_value="3"):
        result = session_int_prompt("rate", choices=["0","1","2","3","4","5"])
        assert result == 3


from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.app import run_flashcard_session, run_quiz_session
from gcp_tutor.study import (
    start_new_session, get_completed_session_items, record_session_item,
)


def test_run_flashcard_session_exits_on_q(tmp_db):
    """User types 'q' on the second card's reveal prompt — first card saved, exit raised."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    conn = get_connection(tmp_db)
    cards = conn.execute("SELECT * FROM flashcards LIMIT 2").fetchall()
    conn.close()
    cards = [dict(c) for c in cards]

    # Card 1: Enter to reveal, then rate 4. Card 2: 'q' on reveal.
    with patch("gcp_tutor.app.Prompt.ask", side_effect=["", "4", "q"]):
        with pytest.raises(SessionExitRequested):
            run_flashcard_session(tmp_db, cards, session_day=1)

    # First card should be recorded
    done = get_completed_session_items(tmp_db, 1, "flashcard")
    assert cards[0]["id"] in done
    assert cards[1]["id"] not in done


def test_run_flashcard_session_skips_completed_items(tmp_db):
    """When resuming, already-done cards are skipped."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    conn = get_connection(tmp_db)
    cards = conn.execute("SELECT * FROM flashcards LIMIT 3").fetchall()
    conn.close()
    cards = [dict(c) for c in cards]

    # Mark first card as already done
    record_session_item(tmp_db, 1, "flashcard", cards[0]["id"])

    # Should only prompt for cards[1] and cards[2] (2 reveals + 2 ratings = 4 prompts)
    with patch("gcp_tutor.app.Prompt.ask", side_effect=["", "4", "", "3"]):
        run_flashcard_session(tmp_db, cards, session_day=1)

    done = get_completed_session_items(tmp_db, 1, "flashcard")
    assert cards[0]["id"] in done
    assert cards[1]["id"] in done
    assert cards[2]["id"] in done


def test_run_quiz_session_exits_on_q(tmp_db):
    """User answers first question then types 'q' on second."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    conn = get_connection(tmp_db)
    questions = conn.execute("SELECT * FROM quiz_questions LIMIT 2").fetchall()
    conn.close()
    questions = [dict(q) for q in questions]

    # Answer first question with 'a', then 'q' on second
    with patch("gcp_tutor.app.Prompt.ask", side_effect=["a", "q"]):
        with pytest.raises(SessionExitRequested):
            run_quiz_session(tmp_db, questions, session_day=1)

    done = get_completed_session_items(tmp_db, 1, "quiz")
    assert questions[0]["id"] in done
    assert questions[1]["id"] not in done


def test_run_quiz_session_skips_completed_items(tmp_db):
    """When resuming, already-answered questions are skipped."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    conn = get_connection(tmp_db)
    questions = conn.execute("SELECT * FROM quiz_questions LIMIT 3").fetchall()
    conn.close()
    questions = [dict(q) for q in questions]

    # Mark first question as already done
    record_session_item(tmp_db, 1, "quiz", questions[0]["id"])

    # Should only prompt for questions[1] and questions[2]
    with patch("gcp_tutor.app.Prompt.ask", side_effect=["a", "b"]):
        run_quiz_session(tmp_db, questions, session_day=1)

    done = get_completed_session_items(tmp_db, 1, "quiz")
    assert questions[0]["id"] in done
    assert questions[1]["id"] in done
    assert questions[2]["id"] in done
