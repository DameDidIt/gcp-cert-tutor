# Session Exit & Resume Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to exit a study session mid-way, return to the main menu, and resume where they left off.

**Architecture:** Sentinel-based exit using a custom exception (`SessionExitRequested`) raised by session-aware input wrappers. A new `session_items` DB table tracks which individual flashcards/questions were completed within a session, enabling granular resume. Existing standalone flashcard/quiz commands are unaffected.

**Tech Stack:** Python, SQLite, Rich (console UI), pytest

---

### Task 1: Add session_items Table to DB Schema

**Files:**
- Modify: `src/gcp_tutor/db.py:7-96` (add table to SCHEMA)
- Test: `tests/test_db.py`

**Step 1: Write the failing test**

In `tests/test_db.py`, add:

```python
def test_session_items_table_exists(tmp_db):
    init_db(tmp_db)
    conn = get_connection(tmp_db)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_items'"
    ).fetchall()
    conn.close()
    assert len(tables) == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_db.py::test_session_items_table_exists -v`
Expected: FAIL

**Step 3: Write minimal implementation**

In `src/gcp_tutor/db.py`, add to the end of the `SCHEMA` string (before the closing `"""`):

```sql
CREATE TABLE IF NOT EXISTS session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_day INTEGER NOT NULL,
    component TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    UNIQUE(session_day, component, item_id)
);
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_db.py::test_session_items_table_exists -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m pytest -v`
Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add src/gcp_tutor/db.py tests/test_db.py
git commit -m "feat: add session_items table for granular session tracking"
```

---

### Task 2: Add session_items Helper Functions to study.py

**Files:**
- Modify: `src/gcp_tutor/study.py`
- Test: `tests/test_study.py`

**Step 1: Write the failing tests**

In `tests/test_study.py`, add imports for the new functions and these tests:

```python
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, complete_reading,
    complete_session_component, get_start_date, start_new_session,
    reset_all_progress, record_session_item, get_completed_session_items,
    clear_session_items, is_session_incomplete,
)

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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_study.py::test_record_and_get_session_items -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

In `src/gcp_tutor/study.py`, add these functions:

```python
def record_session_item(db_path: str, session_day: int, component: str, item_id: int) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "INSERT OR IGNORE INTO session_items (session_day, component, item_id) VALUES (?, ?, ?)",
        (session_day, component, item_id),
    )
    conn.commit()
    conn.close()


def get_completed_session_items(db_path: str, session_day: int, component: str) -> set[int]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT item_id FROM session_items WHERE session_day = ? AND component = ?",
        (session_day, component),
    ).fetchall()
    conn.close()
    return {row["item_id"] for row in rows}


def clear_session_items(db_path: str, session_day: int) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM session_items WHERE session_day = ?", (session_day,))
    conn.commit()
    conn.close()


def is_session_incomplete(db_path: str) -> bool:
    day = get_current_session_day(db_path)
    conn = get_connection(db_path)
    progress = conn.execute(
        "SELECT * FROM user_progress WHERE session_day = ?", (day,)
    ).fetchone()
    conn.close()
    if not progress:
        return False
    return not (progress["reading_done"] and progress["flashcards_done"] and progress["quiz_done"])
```

Also add `DELETE FROM session_items` to `reset_all_progress()`, after the existing DELETE statements.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_study.py -v`
Expected: All PASS (old and new)

**Step 5: Commit**

```bash
git add src/gcp_tutor/study.py tests/test_study.py
git commit -m "feat: add session_items helpers for granular progress tracking"
```

---

### Task 3: Add restart_session Function to study.py

**Files:**
- Modify: `src/gcp_tutor/study.py`
- Test: `tests/test_study.py`

**Step 1: Write the failing test**

```python
from gcp_tutor.study import restart_session

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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_study.py::test_restart_session -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

In `src/gcp_tutor/study.py`:

```python
def restart_session(db_path: str, session_day: int) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE user_progress SET reading_done = 0, flashcards_done = 0, quiz_done = 0, completed_at = NULL WHERE session_day = ?",
        (session_day,),
    )
    conn.execute("DELETE FROM session_items WHERE session_day = ?", (session_day,))
    conn.commit()
    conn.close()
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_study.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/gcp_tutor/study.py tests/test_study.py
git commit -m "feat: add restart_session to reset a day's progress"
```

---

### Task 4: Add SessionExitRequested Exception and Input Wrappers to app.py

**Files:**
- Modify: `src/gcp_tutor/app.py`
- Test: `tests/test_app.py` (create)

**Step 1: Write the failing tests**

Create `tests/test_app.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

In `src/gcp_tutor/app.py`, add near the top (after imports):

```python
class SessionExitRequested(Exception):
    """Raised when user types 'q' or 'menu' during a study session."""
    pass


def session_prompt(prompt_text: str, **kwargs) -> str:
    result = Prompt.ask(prompt_text, **kwargs)
    if result.strip().lower() in ("q", "menu"):
        raise SessionExitRequested()
    return result


def session_int_prompt(prompt_text: str, choices: list[str] = None, **kwargs) -> int:
    # Use Prompt.ask to allow 'q'/'menu' interception before validating as int
    result = Prompt.ask(prompt_text, choices=(choices or []) + ["q", "menu"], **kwargs)
    if result.strip().lower() in ("q", "menu"):
        raise SessionExitRequested()
    return int(result)
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_app.py -v`
Expected: All PASS

**Step 5: Run full suite**

Run: `python -m pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/gcp_tutor/app.py tests/test_app.py
git commit -m "feat: add SessionExitRequested exception and session input wrappers"
```

---

### Task 5: Modify run_flashcard_session to Support Exit and Session Tracking

**Files:**
- Modify: `src/gcp_tutor/app.py:56-69` (`run_flashcard_session`)

**Step 1: Write the failing test**

In `tests/test_app.py`, add:

```python
from unittest.mock import patch, call
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.app import run_flashcard_session, SessionExitRequested
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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_app.py::test_run_flashcard_session_exits_on_q -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace `run_flashcard_session` in `src/gcp_tutor/app.py`:

```python
def run_flashcard_session(db_path: str, cards: list, session_day: int = None) -> None:
    if not cards:
        console.print("[yellow]No flashcards due right now![/yellow]")
        return

    # Filter out already-completed cards when resuming
    if session_day is not None:
        done_ids = get_completed_session_items(db_path, session_day, "flashcard")
        cards = [c for c in cards if c["id"] not in done_ids]
        if not cards:
            console.print("[yellow]All flashcards already completed![/yellow]")
            return

    total = len(cards)
    console.print(f"\n[bold]Flashcard Session[/bold] — {total} cards\n")

    prompt_fn = session_prompt if session_day is not None else Prompt.ask
    int_prompt_fn = session_int_prompt if session_day is not None else (
        lambda p, **kw: IntPrompt.ask(p, **kw)
    )

    for i, card in enumerate(cards, 1):
        console.print(Panel(card["front"], title=f"Card {i}/{total}", border_style="cyan"))
        prompt_fn("[dim]Press Enter to reveal answer[/dim]")
        console.print(Panel(card["back"], border_style="green"))
        rating = int_prompt_fn(
            "Rate yourself (0=forgot, 3=hard, 4=good, 5=easy)",
            choices=["0", "1", "2", "3", "4", "5"],
        )
        record_flashcard_result(db_path, card["id"], rating)
        if session_day is not None:
            record_session_item(db_path, session_day, "flashcard", card["id"])
        console.print()
```

Add the import at top of `app.py`:

```python
from gcp_tutor.study import (
    ...,
    record_session_item, get_completed_session_items,
)
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_app.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/gcp_tutor/app.py tests/test_app.py
git commit -m "feat: add exit/resume support to flashcard sessions"
```

---

### Task 6: Modify run_quiz_session to Support Exit and Session Tracking

**Files:**
- Modify: `src/gcp_tutor/app.py:72-95` (`run_quiz_session`)

**Step 1: Write the failing test**

In `tests/test_app.py`, add:

```python
from gcp_tutor.app import run_quiz_session


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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_app.py::test_run_quiz_session_exits_on_q -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace `run_quiz_session` in `src/gcp_tutor/app.py`:

```python
def run_quiz_session(db_path: str, questions: list, session_day: int = None) -> tuple[int, int]:
    if not questions:
        console.print("[yellow]No questions available![/yellow]")
        return 0, 0

    # Filter out already-completed questions when resuming
    if session_day is not None:
        done_ids = get_completed_session_items(db_path, session_day, "quiz")
        questions = [q for q in questions if q["id"] not in done_ids]
        if not questions:
            console.print("[yellow]All quiz questions already completed![/yellow]")
            return 0, 0

    correct = 0
    total = len(questions)
    console.print(f"\n[bold]Quiz[/bold] — {total} questions\n")

    prompt_fn = session_prompt if session_day is not None else Prompt.ask

    for i, q in enumerate(questions, 1):
        console.print(f"[bold]Q{i}.[/bold] {q['stem']}\n")
        console.print(f"  [cyan]a)[/cyan] {q['choice_a']}")
        console.print(f"  [cyan]b)[/cyan] {q['choice_b']}")
        console.print(f"  [cyan]c)[/cyan] {q['choice_c']}")
        console.print(f"  [cyan]d)[/cyan] {q['choice_d']}")
        answer = prompt_fn("\nYour answer", choices=["a", "b", "c", "d", "q", "menu"])
        is_correct = record_quiz_answer(db_path, q["id"], answer)
        if session_day is not None:
            record_session_item(db_path, session_day, "quiz", q["id"])
        if is_correct:
            console.print("[green]Correct![/green]")
            correct += 1
        else:
            console.print(f"[red]Incorrect.[/red] Answer: [green]{q['correct_answer']}[/green]")
        if q["explanation"]:
            console.print(f"[dim]{q['explanation']}[/dim]")
        console.print()
    console.print(f"[bold]Score: {correct}/{total} ({correct/total*100:.0f}%)[/bold]\n")
    return correct, total
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_app.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/gcp_tutor/app.py tests/test_app.py
git commit -m "feat: add exit/resume support to quiz sessions"
```

---

### Task 7: Modify cmd_study to Handle Exit and Resume/Restart Prompt

**Files:**
- Modify: `src/gcp_tutor/app.py:98-144` (`cmd_study`)

**Step 1: Write the failing test**

In `tests/test_app.py`, add:

```python
from gcp_tutor.app import cmd_study
from gcp_tutor.study import (
    complete_session_component, is_session_incomplete, restart_session,
    get_current_session_day,
)


def test_cmd_study_resume_prompt_shown(tmp_db, capsys):
    """When session is incomplete, user is prompted to resume or restart."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")

    # User chooses 'resume', then exits during flashcards
    with patch("gcp_tutor.app.Prompt.ask", side_effect=["resume", "q"]):
        cmd_study(tmp_db)

    # Should still be on day 1 (not advanced)
    assert get_current_session_day(tmp_db) == 1
    assert is_session_incomplete(tmp_db) is True


def test_cmd_study_restart_clears_progress(tmp_db):
    """Choosing 'restart' clears component flags and session items."""
    init_db(tmp_db)
    seed_all(tmp_db)
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    record_session_item(tmp_db, 1, "flashcard", 1)

    # User chooses 'restart', then exits during reading
    with patch("gcp_tutor.app.Prompt.ask", side_effect=["restart", "q"]):
        cmd_study(tmp_db)

    # Reading should be reset
    conn = get_connection(tmp_db)
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = 1").fetchone()
    conn.close()
    assert progress["reading_done"] == 0
    # Session items should be cleared
    assert get_completed_session_items(tmp_db, 1, "flashcard") == set()
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_app.py::test_cmd_study_resume_prompt_shown -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace `cmd_study` in `src/gcp_tutor/app.py`. Add needed imports first:

```python
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, start_new_session,
    complete_session_component, get_calendar_days_elapsed, get_completed_sessions,
    get_total_sessions, reset_all_progress,
    record_session_item, get_completed_session_items,
    is_session_incomplete, restart_session, clear_session_items,
)
```

New `cmd_study`:

```python
def cmd_study(db_path: str):
    plan = get_todays_plan(db_path)
    if not plan:
        console.print("[yellow]You've completed all sessions! Use 'review' to keep studying.[/yellow]")
        return
    day = get_current_session_day(db_path)
    total = get_total_sessions(db_path)
    cal_days = get_calendar_days_elapsed(db_path)

    # Check for incomplete session — offer resume/restart
    progress = start_new_session(db_path)
    if is_session_incomplete(db_path) and (
        progress.get("reading_done") or progress.get("flashcards_done") or progress.get("quiz_done")
    ):
        console.print(Panel(
            f"You have an incomplete session for Day {day}.\n"
            "  [cyan]resume[/cyan]  — Pick up where you left off\n"
            "  [cyan]restart[/cyan] — Start the day over",
            title="Incomplete Session",
            border_style="yellow",
        ))
        choice = Prompt.ask("Your choice", choices=["resume", "restart"], default="resume")
        if choice == "restart":
            restart_session(db_path, day)
            progress = start_new_session(db_path)
            console.print("[green]Session restarted![/green]\n")
    else:
        console.print(Panel(
            f"Session Day [bold]{day}[/bold] of {total}" + (f" (Calendar Day {cal_days})" if cal_days else "")
            + (f"\n[cyan]Domain: {plan.get('domain_name', 'Mixed Review')}[/cyan]" if plan.get("domain_name") else "\n[cyan]Mixed Review / Practice Exam[/cyan]"),
            title="Today's Study Session",
        ))

    try:
        # Reading
        if not progress.get("reading_done"):
            console.print("\n[bold]1. Reading Material[/bold]")
            if plan.get("reading_content"):
                console.print(plan["reading_content"])
            else:
                console.print(f"[dim]Review the key concepts for: {plan.get('domain_name', 'all domains')}[/dim]")
            session_prompt("[dim]Press Enter when done reading[/dim]")
            complete_session_component(db_path, day, "reading")
            console.print("[green]Reading complete![/green]\n")

        # Flashcards
        if not progress.get("flashcards_done"):
            console.print("[bold]2. Flashcards[/bold]")
            if plan.get("domain_id"):
                cards = get_cards_for_domain(db_path, plan["domain_id"], limit=12)
            else:
                cards = get_due_cards(db_path, limit=12)
            run_flashcard_session(db_path, cards, session_day=day)
            complete_session_component(db_path, day, "flashcards")
            console.print("[green]Flashcards complete![/green]\n")

        # Quiz
        if not progress.get("quiz_done"):
            console.print("[bold]3. Quiz[/bold]")
            if plan.get("domain_id"):
                questions = get_questions_for_domain(db_path, plan["domain_id"], count=8)
            else:
                questions = get_quiz_questions(db_path, count=8)
            run_quiz_session(db_path, questions, session_day=day)
            complete_session_component(db_path, day, "quiz")
            console.print("[green]Quiz complete! Session done.[/green]")

    except SessionExitRequested:
        console.print("\n[yellow]Session paused. Your progress has been saved.[/yellow]")
        console.print("[dim]Run 'study' again to resume where you left off.[/dim]")
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_app.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `python -m pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/gcp_tutor/app.py tests/test_app.py
git commit -m "feat: add resume/restart prompt and exit handling to cmd_study"
```

---

### Task 8: Integration Test — Full Exit and Resume Flow

**Files:**
- Test: `tests/test_app.py`

**Step 1: Write integration test**

```python
def test_full_exit_and_resume_flow(tmp_db):
    """End-to-end: start session, exit mid-flashcards, resume, complete."""
    init_db(tmp_db)
    seed_all(tmp_db)

    # Start session, complete reading, exit during flashcards
    with patch("gcp_tutor.app.Prompt.ask", side_effect=[
        "",       # Enter for reading
        "",       # Reveal first flashcard
        "4",      # Rate first flashcard
        "q",      # Exit on second flashcard reveal
    ]):
        cmd_study(tmp_db)

    assert get_current_session_day(tmp_db) == 1
    assert is_session_incomplete(tmp_db) is True

    # Resume — should skip reading, skip first flashcard
    # Need enough prompts for remaining flashcards + quiz
    conn = get_connection(tmp_db)
    plan = conn.execute(
        "SELECT sd.domain_id FROM study_days sd WHERE sd.day_number = 1"
    ).fetchone()
    domain_id = plan["domain_id"]
    total_cards = conn.execute(
        "SELECT COUNT(*) FROM flashcards WHERE domain_id = ? AND (next_review IS NULL OR next_review <= date('now'))",
        (domain_id,),
    ).fetchone()[0]
    remaining_cards = min(total_cards, 12) - 1  # minus the one already done
    total_questions = min(8, conn.execute(
        "SELECT COUNT(*) FROM quiz_questions WHERE domain_id = ?", (domain_id,),
    ).fetchone()[0])
    conn.close()

    prompts = ["resume"]  # Resume prompt
    for _ in range(remaining_cards):
        prompts.extend(["", "3"])  # reveal + rate each remaining card
    for _ in range(total_questions):
        prompts.append("a")  # answer each quiz question

    with patch("gcp_tutor.app.Prompt.ask", side_effect=prompts):
        cmd_study(tmp_db)

    assert get_current_session_day(tmp_db) == 2
    assert is_session_incomplete(tmp_db) is False
```

**Step 2: Run test**

Run: `python -m pytest tests/test_app.py::test_full_exit_and_resume_flow -v`
Expected: PASS

**Step 3: Run full suite**

Run: `python -m pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_app.py
git commit -m "test: add integration test for full exit and resume flow"
```

---

### Task 9: Manual Smoke Test

**Step 1: Run the app and test the flow manually**

Run: `python -m gcp_tutor`

1. Type `study` to start a session
2. Complete reading (press Enter)
3. Do 1-2 flashcards, then type `q`
4. Verify "Session paused" message appears and you're back at menu
5. Type `study` again
6. Verify "Incomplete session" prompt appears with resume/restart options
7. Choose `resume` — verify reading is skipped and flashcards start from where you left off
8. Type `q` again, then `study`, choose `restart` — verify it starts from reading

**Step 2: Final commit if any adjustments needed**

```bash
git add -A
git commit -m "fix: adjustments from manual testing"
```
