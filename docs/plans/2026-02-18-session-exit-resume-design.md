# Session Exit & Resume Design

## Problem

Users cannot exit a study session mid-way and return to the main menu. The only escape is Ctrl+C which exits the entire app. If a user needs to take a break or can't finish, they lose their place.

## Solution: Sentinel-Based Exit with DB Progress Tracking

### 1. SessionExitRequested Exception

A custom exception in `app.py`. Raised when the user types `q` or `menu` at any input prompt during a study session. Caught by `cmd_study()` to return to the main menu.

### 2. Session-Aware Input Wrappers

`session_prompt()` and `session_int_prompt()` — thin wrappers around Rich's `Prompt.ask()` / `IntPrompt.ask()` that check for `q`/`menu` input and raise `SessionExitRequested`. Used only within study session context.

### 3. session_items DB Table

Tracks which specific items were completed within a session component:

```sql
CREATE TABLE IF NOT EXISTS session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_day INTEGER NOT NULL,
    component TEXT NOT NULL,  -- 'flashcard' or 'quiz'
    item_id INTEGER NOT NULL,
    UNIQUE(session_day, component, item_id)
);
```

Populated as each flashcard/quiz item is completed during `cmd_study()`. Queried on resume to filter out already-done items.

### 4. Resume/Restart Prompt

When `cmd_study()` detects an incomplete session (progress row exists, not all components done), prompt:

```
You have an incomplete session for Day X.
  resume  - Pick up where you left off
  restart - Start the day over
```

- **resume**: proceed normally; component flags skip done components, session_items filters done items
- **restart**: delete session_items for that day, reset component flags to 0

### 5. Modified run_flashcard_session / run_quiz_session

Both gain an optional `session_day` parameter:
- When provided (called from `cmd_study()`): use session-aware prompts, record to session_items
- When not provided (standalone flashcards/quiz/review): work exactly as before

### 6. User Decisions

- **Granular save**: individual flashcard ratings and quiz answers saved as they go
- **Exit UX**: type `q` or `menu` at any prompt to return to main menu
- **Resume UX**: prompt to resume or restart when returning to an incomplete session
