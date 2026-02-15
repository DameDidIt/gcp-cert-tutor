# GCP ACE Cert Tutor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool that prepares learners to pass the GCP Associate Cloud Engineer cert in 30 study sessions.

**Architecture:** Interactive Python CLI using Typer + Rich, backed by SQLite. Content seeded from the official ACE exam guide. SM-2 spaced repetition for flashcards. Readiness scoring via weighted composite of quiz scores, flashcard retention, and study completion.

**Tech Stack:** Python 3.11+, Typer, Rich, SQLite3 (stdlib), PyPDF2, python-docx, pyyaml, beautifulsoup4, markdown, pytest

---

## Project Structure

```
gcp_cert_tutor/
├── pyproject.toml
├── src/
│   └── gcp_tutor/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── db.py
│       ├── models.py
│       ├── seed.py
│       ├── sm2.py
│       ├── flashcards.py
│       ├── quiz.py
│       ├── study.py
│       ├── dashboard.py
│       ├── review.py
│       ├── importer.py
│       └── content/
│           ├── domains.json
│           ├── flashcards.json
│           └── questions.json
├── tests/
│   ├── conftest.py
│   ├── test_db.py
│   ├── test_sm2.py
│   ├── test_flashcards.py
│   ├── test_quiz.py
│   ├── test_study.py
│   ├── test_dashboard.py
│   ├── test_review.py
│   └── test_importer.py
└── docs/plans/
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/gcp_tutor/__init__.py`
- Create: `src/gcp_tutor/__main__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "gcp-tutor"
version = "0.1.0"
description = "GCP Associate Cloud Engineer certification prep tool"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "PyPDF2>=3.0.0",
    "python-docx>=1.0.0",
    "markdown>=3.5.0",
    "pyyaml>=6.0.0",
    "beautifulsoup4>=4.12",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0"]

[project.scripts]
gcp-tutor = "gcp_tutor.app:main"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2: Create `src/gcp_tutor/__init__.py`**

```python
"""GCP Associate Cloud Engineer certification prep tool."""
```

**Step 3: Create `src/gcp_tutor/__main__.py`**

```python
from gcp_tutor.app import main

if __name__ == "__main__":
    main()
```

**Step 4: Create `tests/conftest.py`**

```python
import os
import sqlite3
import pytest

@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path for tests."""
    db_path = str(tmp_path / "test_tutor.db")
    return db_path
```

**Step 5: Install in dev mode and run pytest to verify setup**

```bash
cd /Users/dbowens/claude_projects/gcp_cert_tutor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```
Expected: 0 tests collected, no errors.

**Step 6: Commit**

```bash
git add pyproject.toml src/ tests/conftest.py
git commit -m "feat: project scaffolding with pyproject.toml and package structure"
```

---

### Task 2: Database Schema and Connection

**Files:**
- Create: `src/gcp_tutor/db.py`
- Create: `tests/test_db.py`

**Step 1: Write failing tests for database initialization**

```python
# tests/test_db.py
from gcp_tutor.db import init_db, get_connection

def test_init_db_creates_tables(tmp_db):
    init_db(tmp_db)
    conn = get_connection(tmp_db)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    expected = {
        "domains", "subtopics", "study_days", "flashcards",
        "quiz_questions", "user_progress", "quiz_results",
        "flashcard_results", "imported_content", "user_settings",
    }
    assert expected.issubset(tables)
    conn.close()

def test_init_db_is_idempotent(tmp_db):
    init_db(tmp_db)
    init_db(tmp_db)  # should not raise
    conn = get_connection(tmp_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    assert len(cursor.fetchall()) > 0
    conn.close()

def test_get_connection_returns_row_factory(tmp_db):
    init_db(tmp_db)
    conn = get_connection(tmp_db)
    conn.execute("INSERT INTO user_settings (key, value) VALUES ('test', 'val')")
    row = conn.execute("SELECT key, value FROM user_settings WHERE key='test'").fetchone()
    assert row["key"] == "test"
    conn.close()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement `src/gcp_tutor/db.py`**

```python
"""Database initialization and connection management."""
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = str(Path.home() / ".gcp_tutor" / "tutor.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    section_number INTEGER NOT NULL,
    exam_weight REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS subtopics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS study_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_number INTEGER NOT NULL UNIQUE,
    domain_id INTEGER REFERENCES domains(id),
    subtopic_ids TEXT,  -- JSON array of subtopic IDs
    reading_content TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    subtopic_id INTEGER REFERENCES subtopics(id),
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    source TEXT DEFAULT 'seeded',
    ease_factor REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    next_review TEXT
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id),
    subtopic_id INTEGER REFERENCES subtopics(id),
    stem TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT NOT NULL,
    choice_d TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    source TEXT DEFAULT 'seeded'
);

CREATE TABLE IF NOT EXISTS user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_day INTEGER NOT NULL,
    completed_at TEXT,
    calendar_date TEXT,
    reading_done INTEGER DEFAULT 0,
    flashcards_done INTEGER DEFAULT 0,
    quiz_done INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_question_id INTEGER NOT NULL REFERENCES quiz_questions(id),
    user_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    answered_at TEXT
);

CREATE TABLE IF NOT EXISTS flashcard_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flashcard_id INTEGER NOT NULL REFERENCES flashcards(id),
    rating INTEGER NOT NULL,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS imported_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    domain_id INTEGER REFERENCES domains(id),
    content_text TEXT,
    imported_at TEXT
);

CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT
);
"""


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/gcp_tutor/db.py tests/test_db.py
git commit -m "feat: database schema and connection management"
```

---

### Task 3: Data Models

**Files:**
- Create: `src/gcp_tutor/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing tests**

```python
# tests/test_models.py
from gcp_tutor.models import Domain, Subtopic, Flashcard, QuizQuestion

def test_domain_creation():
    d = Domain(id=1, name="Deploying", section_number=3, exam_weight=0.25, description="Deploy stuff")
    assert d.name == "Deploying"
    assert d.exam_weight == 0.25

def test_flashcard_defaults():
    f = Flashcard(id=1, domain_id=1, front="Q?", back="A")
    assert f.ease_factor == 2.5
    assert f.interval == 0
    assert f.repetitions == 0

def test_quiz_question_creation():
    q = QuizQuestion(
        id=1, domain_id=1, stem="What is GKE?",
        choice_a="A", choice_b="B", choice_c="C", choice_d="D",
        correct_answer="a", explanation="GKE is Kubernetes Engine"
    )
    assert q.correct_answer == "a"
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/models.py`**

```python
"""Data classes for the tutor domain model."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Domain:
    id: int
    name: str
    section_number: int
    exam_weight: float
    description: str = ""


@dataclass
class Subtopic:
    id: int
    domain_id: int
    name: str
    description: str = ""


@dataclass
class Flashcard:
    id: int
    domain_id: int
    front: str
    back: str
    subtopic_id: Optional[int] = None
    source: str = "seeded"
    ease_factor: float = 2.5
    interval: int = 0
    repetitions: int = 0
    next_review: Optional[str] = None


@dataclass
class QuizQuestion:
    id: int
    domain_id: int
    stem: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str
    correct_answer: str
    subtopic_id: Optional[int] = None
    explanation: str = ""
    source: str = "seeded"


@dataclass
class StudyDay:
    id: int
    day_number: int
    domain_id: Optional[int]
    subtopic_ids: str = "[]"  # JSON
    reading_content: str = ""
    status: str = "pending"


@dataclass
class UserProgress:
    id: int
    session_day: int
    completed_at: Optional[str] = None
    calendar_date: Optional[str] = None
    reading_done: bool = False
    flashcards_done: bool = False
    quiz_done: bool = False
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/models.py tests/test_models.py
git commit -m "feat: data model classes for domains, flashcards, quizzes, progress"
```

---

### Task 4: Content Seeding — Domains, Subtopics, Study Plan

**Files:**
- Create: `src/gcp_tutor/content/domains.json`
- Create: `src/gcp_tutor/seed.py`
- Create: `tests/test_seed.py`

**Step 1: Create `src/gcp_tutor/content/domains.json`**

This file contains the 5 exam domains and all their subtopics from the official exam guide. Full JSON structure:

```json
{
  "domains": [
    {
      "id": 1,
      "name": "Setting Up a Cloud Solution Environment",
      "section_number": 1,
      "exam_weight": 0.20,
      "description": "Setting up cloud projects, accounts, and billing",
      "subtopics": [
        {"name": "Setting up cloud projects and accounts", "description": "Resource hierarchy, org policies, IAM roles, Cloud Identity, APIs, operations suite, quotas"},
        {"name": "Managing billing configuration", "description": "Billing accounts, linking projects, budgets/alerts, billing exports"}
      ]
    },
    {
      "id": 2,
      "name": "Planning and Configuring a Cloud Solution",
      "section_number": 2,
      "exam_weight": 0.175,
      "description": "Planning compute, storage, and network resources",
      "subtopics": [
        {"name": "Planning and configuring compute resources", "description": "Compute Engine, GKE, Cloud Run, Cloud Functions, Spot VMs, custom machine types"},
        {"name": "Planning and configuring data storage options", "description": "Cloud SQL, BigQuery, Firestore, Spanner, Bigtable, storage classes"},
        {"name": "Planning and configuring network resources", "description": "Load balancing, resource locations, Network Service Tiers"}
      ]
    },
    {
      "id": 3,
      "name": "Deploying and Implementing a Cloud Solution",
      "section_number": 3,
      "exam_weight": 0.25,
      "description": "Deploying compute, data, and networking resources",
      "subtopics": [
        {"name": "Deploying Compute Engine resources", "description": "Instances, autoscaled MIGs, OS Login, VM Manager"},
        {"name": "Deploying GKE resources", "description": "kubectl, cluster configs (Autopilot, regional, private, Enterprise), containerized apps"},
        {"name": "Deploying Cloud Run and Cloud Functions", "description": "Deploying apps, event handling, Pub/Sub, Eventarc"},
        {"name": "Deploying data solutions", "description": "Cloud SQL, Firestore, BigQuery, Spanner, Pub/Sub, Dataflow, Cloud Storage, AlloyDB"},
        {"name": "Deploying networking resources", "description": "VPC/subnets, firewall rules/policies, Cloud VPN, VPC Peering"},
        {"name": "Infrastructure as code", "description": "Terraform, Cloud Foundation Toolkit, Config Connector, Helm"}
      ]
    },
    {
      "id": 4,
      "name": "Ensuring Successful Operation of a Cloud Solution",
      "section_number": 4,
      "exam_weight": 0.20,
      "description": "Managing and monitoring cloud resources",
      "subtopics": [
        {"name": "Managing Compute Engine resources", "description": "Remote connect, VM inventory, snapshots, images"},
        {"name": "Managing GKE resources", "description": "Cluster inventory, Artifact Registry, node pools, autoscaling"},
        {"name": "Managing Cloud Run resources", "description": "New versions, traffic splitting, scaling parameters"},
        {"name": "Managing storage and database solutions", "description": "Cloud Storage lifecycle, queries, backups, job status"},
        {"name": "Managing networking resources", "description": "Subnets, IP addresses, Cloud DNS, Cloud NAT"},
        {"name": "Monitoring and logging", "description": "Alerts, custom metrics, log exports, log routers, audit logs, Ops Agent, Managed Prometheus"}
      ]
    },
    {
      "id": 5,
      "name": "Configuring Access and Security",
      "section_number": 5,
      "exam_weight": 0.175,
      "description": "IAM and service account management",
      "subtopics": [
        {"name": "Managing IAM", "description": "IAM policies, role types (basic, predefined, custom)"},
        {"name": "Managing service accounts", "description": "Creation, minimum permissions, impersonation, short-lived credentials"}
      ]
    }
  ]
}
```

**Step 2: Write failing tests for seed**

```python
# tests/test_seed.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_study_plan, is_seeded

def test_seed_domains(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    conn = get_connection(tmp_db)
    domains = conn.execute("SELECT * FROM domains").fetchall()
    assert len(domains) == 5
    subtopics = conn.execute("SELECT * FROM subtopics").fetchall()
    assert len(subtopics) == 19  # total subtopics across all domains
    conn.close()

def test_seed_study_plan(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_study_plan(tmp_db)
    conn = get_connection(tmp_db)
    days = conn.execute("SELECT * FROM study_days ORDER BY day_number").fetchall()
    assert len(days) == 30
    # First 6 days should be domain 3 (heaviest weight)
    assert days[0]["domain_id"] == 3
    assert days[5]["domain_id"] == 3
    conn.close()

def test_is_seeded(tmp_db):
    init_db(tmp_db)
    assert not is_seeded(tmp_db)
    seed_domains(tmp_db)
    assert is_seeded(tmp_db)
```

**Step 3: Implement `src/gcp_tutor/seed.py`**

```python
"""Seed the database with exam domains, subtopics, and study plan."""
import json
from pathlib import Path
from gcp_tutor.db import get_connection

CONTENT_DIR = Path(__file__).parent / "content"


def is_seeded(db_path: str) -> bool:
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
    conn.close()
    return count > 0


def seed_domains(db_path: str) -> None:
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
    # Domain order by exam weight: 3(25%), 1(20%), 4(20%), 2(17.5%), 5(17.5%)
    plan = [
        (3, 6),   # Days 1-6
        (1, 4),   # Days 7-10
        (4, 4),   # Days 11-14
        (2, 4),   # Days 15-18
        (5, 4),   # Days 19-22
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
```

**Step 4: Run tests, verify pass**

```bash
pytest tests/test_seed.py -v
```

**Step 5: Commit**

```bash
git add src/gcp_tutor/content/domains.json src/gcp_tutor/seed.py tests/test_seed.py
git commit -m "feat: content seeding for domains, subtopics, and 30-day study plan"
```

---

### Task 5: Content Seeding — Flashcards and Quiz Questions

**Files:**
- Create: `src/gcp_tutor/content/flashcards.json`
- Create: `src/gcp_tutor/content/questions.json`
- Modify: `src/gcp_tutor/seed.py` (add `seed_flashcards`, `seed_questions`)
- Modify: `tests/test_seed.py`

**Step 1: Create `src/gcp_tutor/content/flashcards.json`**

Seed a minimum of 10 flashcards per subtopic (19 subtopics = ~190 cards). Structure:

```json
{
  "flashcards": [
    {
      "domain_id": 3,
      "subtopic": "Deploying Compute Engine resources",
      "front": "What gcloud command creates a VM instance with a custom machine type of 4 vCPUs and 16 GB RAM?",
      "back": "gcloud compute instances create INSTANCE_NAME --custom-cpu=4 --custom-memory=16GB"
    }
  ]
}
```

The implementer should create **at least 190 flashcards** covering all 19 subtopics, sourced from the official exam guide topics listed in domains.json. Focus on gcloud CLI commands, service comparisons, and key concepts.

**Step 2: Create `src/gcp_tutor/content/questions.json`**

Seed a minimum of 5 quiz questions per subtopic (~95 questions). Structure:

```json
{
  "questions": [
    {
      "domain_id": 3,
      "subtopic": "Deploying Compute Engine resources",
      "stem": "You need to create a managed instance group that automatically scales based on CPU usage. Which sequence of steps is correct?",
      "choice_a": "Create instance template → Create MIG → Configure autoscaler",
      "choice_b": "Create MIG → Create instance template → Configure autoscaler",
      "choice_c": "Create autoscaler → Create instance template → Create MIG",
      "choice_d": "Create instance → Create snapshot → Create MIG",
      "correct_answer": "a",
      "explanation": "You must first create an instance template that defines the VM configuration, then create a managed instance group from that template, then configure the autoscaler with target CPU utilization."
    }
  ]
}
```

The implementer should create **at least 95 quiz questions** covering all 19 subtopics. All questions should be multiple choice with 4 options and include explanations.

**Step 3: Add seed functions to `src/gcp_tutor/seed.py`**

```python
def seed_flashcards(db_path: str) -> None:
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
```

**Step 4: Add tests**

```python
def test_seed_flashcards(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    conn = get_connection(tmp_db)
    cards = conn.execute("SELECT * FROM flashcards").fetchall()
    assert len(cards) >= 190
    # Verify all 5 domains have cards
    domain_ids = {c["domain_id"] for c in cards}
    assert domain_ids == {1, 2, 3, 4, 5}
    conn.close()

def test_seed_questions(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    conn = get_connection(tmp_db)
    questions = conn.execute("SELECT * FROM quiz_questions").fetchall()
    assert len(questions) >= 95
    conn.close()

def test_seed_all_idempotent(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    seed_all(tmp_db)  # second call should be no-op
    conn = get_connection(tmp_db)
    assert conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0] == 5
    conn.close()
```

**Step 5: Run tests, verify pass**

**Step 6: Commit**

```bash
git add src/gcp_tutor/content/ src/gcp_tutor/seed.py tests/test_seed.py
git commit -m "feat: seed flashcards (190+) and quiz questions (95+) from exam guide"
```

---

### Task 6: SM-2 Spaced Repetition Engine

**Files:**
- Create: `src/gcp_tutor/sm2.py`
- Create: `tests/test_sm2.py`

**Step 1: Write failing tests**

```python
# tests/test_sm2.py
from gcp_tutor.sm2 import sm2_update

def test_sm2_first_review_correct():
    """First correct answer: interval=1, repetitions=1."""
    result = sm2_update(quality=4, repetitions=0, ease_factor=2.5, interval=0)
    assert result["interval"] == 1
    assert result["repetitions"] == 1
    assert result["ease_factor"] == 2.5

def test_sm2_second_review_correct():
    """Second correct answer: interval=6."""
    result = sm2_update(quality=4, repetitions=1, ease_factor=2.5, interval=1)
    assert result["interval"] == 6
    assert result["repetitions"] == 2

def test_sm2_third_review_correct():
    """Third+ correct: interval = old_interval * ease_factor."""
    result = sm2_update(quality=4, repetitions=2, ease_factor=2.5, interval=6)
    assert result["interval"] == 15  # round(6 * 2.5)
    assert result["repetitions"] == 3

def test_sm2_incorrect_resets():
    """Quality < 3 resets repetitions and interval."""
    result = sm2_update(quality=1, repetitions=5, ease_factor=2.5, interval=30)
    assert result["repetitions"] == 0
    assert result["interval"] == 1

def test_sm2_ease_factor_minimum():
    """Ease factor never drops below 1.3."""
    result = sm2_update(quality=0, repetitions=0, ease_factor=1.3, interval=0)
    assert result["ease_factor"] >= 1.3

def test_sm2_easy_increases_ease():
    """Quality 5 increases ease factor."""
    result = sm2_update(quality=5, repetitions=2, ease_factor=2.5, interval=6)
    assert result["ease_factor"] > 2.5
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/sm2.py`**

```python
"""SM-2 spaced repetition algorithm."""


def sm2_update(
    quality: int,
    repetitions: int,
    ease_factor: float,
    interval: int,
) -> dict:
    """Calculate next review parameters using SM-2.

    Args:
        quality: Rating 0-5 (0=complete blackout, 5=perfect)
        repetitions: Number of consecutive correct reviews
        ease_factor: Current ease factor (minimum 1.3)
        interval: Current interval in days

    Returns:
        Dict with updated interval, repetitions, ease_factor.
    """
    # Update ease factor
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)

    if quality >= 3:
        # Correct response
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)
        new_repetitions = repetitions + 1
    else:
        # Incorrect — reset
        new_repetitions = 0
        new_interval = 1

    return {
        "interval": new_interval,
        "repetitions": new_repetitions,
        "ease_factor": round(new_ef, 2),
    }
```

**Step 4: Run tests, verify pass**

```bash
pytest tests/test_sm2.py -v
```

**Step 5: Commit**

```bash
git add src/gcp_tutor/sm2.py tests/test_sm2.py
git commit -m "feat: SM-2 spaced repetition algorithm"
```

---

### Task 7: Flashcard Session Logic

**Files:**
- Create: `src/gcp_tutor/flashcards.py`
- Create: `tests/test_flashcards.py`

**Step 1: Write failing tests**

```python
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
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/flashcards.py`**

```python
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
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/flashcards.py tests/test_flashcards.py
git commit -m "feat: flashcard session logic with SM-2 scheduling"
```

---

### Task 8: Quiz Engine

**Files:**
- Create: `src/gcp_tutor/quiz.py`
- Create: `tests/test_quiz.py`

**Step 1: Write failing tests**

```python
# tests/test_quiz.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_questions
from gcp_tutor.quiz import get_quiz_questions, get_questions_for_domain, record_quiz_answer, get_quiz_score

def test_get_quiz_questions(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=10)
    assert len(questions) == 10

def test_get_questions_for_domain(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_questions_for_domain(tmp_db, domain_id=3, count=5)
    assert len(questions) == 5
    assert all(q["domain_id"] == 3 for q in questions)

def test_record_quiz_answer_correct(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    conn = get_connection(tmp_db)
    result = conn.execute("SELECT * FROM quiz_results WHERE quiz_question_id = ?", (q["id"],)).fetchone()
    assert result["is_correct"] == 1
    conn.close()

def test_record_quiz_answer_incorrect(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    wrong = "b" if q["correct_answer"] != "b" else "c"
    record_quiz_answer(tmp_db, q["id"], wrong)
    conn = get_connection(tmp_db)
    result = conn.execute("SELECT * FROM quiz_results WHERE quiz_question_id = ?", (q["id"],)).fetchone()
    assert result["is_correct"] == 0
    conn.close()

def test_get_quiz_score(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=4)
    # Answer 3 correct, 1 wrong
    for q in questions[:3]:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    wrong = "b" if questions[3]["correct_answer"] != "b" else "c"
    record_quiz_answer(tmp_db, questions[3]["id"], wrong)
    score = get_quiz_score(tmp_db)
    assert score == 75.0  # 3/4
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/quiz.py`**

```python
"""Quiz engine for practice questions."""
from datetime import datetime
from gcp_tutor.db import get_connection


def get_quiz_questions(db_path: str, count: int = 10) -> list:
    conn = get_connection(db_path)
    questions = conn.execute(
        "SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT ?", (count,)
    ).fetchall()
    conn.close()
    return questions


def get_questions_for_domain(db_path: str, domain_id: int, count: int = 10) -> list:
    conn = get_connection(db_path)
    questions = conn.execute(
        "SELECT * FROM quiz_questions WHERE domain_id = ? ORDER BY RANDOM() LIMIT ?",
        (domain_id, count),
    ).fetchall()
    conn.close()
    return questions


def get_questions_for_subtopic(db_path: str, subtopic_id: int, count: int = 10) -> list:
    conn = get_connection(db_path)
    questions = conn.execute(
        "SELECT * FROM quiz_questions WHERE subtopic_id = ? ORDER BY RANDOM() LIMIT ?",
        (subtopic_id, count),
    ).fetchall()
    conn.close()
    return questions


def record_quiz_answer(db_path: str, question_id: int, user_answer: str) -> bool:
    conn = get_connection(db_path)
    question = conn.execute(
        "SELECT correct_answer FROM quiz_questions WHERE id = ?", (question_id,)
    ).fetchone()
    is_correct = user_answer.lower().strip() == question["correct_answer"].lower().strip()
    conn.execute(
        "INSERT INTO quiz_results (quiz_question_id, user_answer, is_correct, answered_at) VALUES (?, ?, ?, ?)",
        (question_id, user_answer, int(is_correct), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return is_correct


def get_quiz_score(db_path: str) -> float:
    """Overall quiz score as percentage."""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM quiz_results"
    ).fetchone()
    conn.close()
    if row["total"] == 0:
        return 0.0
    return round((row["correct"] / row["total"]) * 100, 1)


def get_domain_quiz_scores(db_path: str) -> dict:
    """Quiz scores broken down by domain."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT q.domain_id, COUNT(*) as total, SUM(r.is_correct) as correct
        FROM quiz_results r
        JOIN quiz_questions q ON r.quiz_question_id = q.id
        GROUP BY q.domain_id"""
    ).fetchall()
    conn.close()
    return {
        row["domain_id"]: round((row["correct"] / row["total"]) * 100, 1)
        for row in rows
    }
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/quiz.py tests/test_quiz.py
git commit -m "feat: quiz engine with scoring and domain filtering"
```

---

### Task 9: Study Session Logic and Progress Tracking

**Files:**
- Create: `src/gcp_tutor/study.py`
- Create: `tests/test_study.py`

**Step 1: Write failing tests**

```python
# tests/test_study.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, complete_reading,
    complete_session_component, get_start_date, start_new_session,
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
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/study.py`**

```python
"""Study session management and progress tracking."""
from datetime import date, datetime
from gcp_tutor.db import get_connection


def get_setting(db_path: str, key: str, default: str = None) -> str | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT value FROM user_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(db_path: str, key: str, value: str) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO user_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?",
        (key, value, value),
    )
    conn.commit()
    conn.close()


def get_start_date(db_path: str) -> str | None:
    return get_setting(db_path, "start_date")


def get_current_session_day(db_path: str) -> int:
    return int(get_setting(db_path, "current_session_day", "1"))


def get_total_sessions(db_path: str) -> int:
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM study_days").fetchone()[0]
    conn.close()
    return count


def get_todays_plan(db_path: str) -> dict | None:
    day = get_current_session_day(db_path)
    conn = get_connection(db_path)
    plan = conn.execute(
        """SELECT sd.*, d.name as domain_name
        FROM study_days sd
        LEFT JOIN domains d ON sd.domain_id = d.id
        WHERE sd.day_number = ?""",
        (day,),
    ).fetchone()
    conn.close()
    return dict(plan) if plan else None


def start_new_session(db_path: str) -> dict:
    day = get_current_session_day(db_path)
    if not get_start_date(db_path):
        set_setting(db_path, "start_date", date.today().isoformat())
    conn = get_connection(db_path)
    existing = conn.execute("SELECT * FROM user_progress WHERE session_day = ?", (day,)).fetchone()
    if existing:
        conn.close()
        return dict(existing)
    conn.execute(
        "INSERT INTO user_progress (session_day, calendar_date) VALUES (?, ?)",
        (day, date.today().isoformat()),
    )
    conn.commit()
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = ?", (day,)).fetchone()
    conn.close()
    return dict(progress)


def complete_session_component(db_path: str, session_day: int, component: str) -> None:
    valid = {"reading": "reading_done", "flashcards": "flashcards_done", "quiz": "quiz_done"}
    column = valid[component]
    conn = get_connection(db_path)
    conn.execute(
        f"UPDATE user_progress SET {column} = 1 WHERE session_day = ?",
        (session_day,),
    )
    # Check if all components done
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = ?", (session_day,)).fetchone()
    if progress["reading_done"] and progress["flashcards_done"] and progress["quiz_done"]:
        conn.execute(
            "UPDATE user_progress SET completed_at = ? WHERE session_day = ?",
            (datetime.now().isoformat(), session_day),
        )
        # Advance session day
        conn.execute(
            "INSERT INTO user_settings (key, value) VALUES ('current_session_day', ?) ON CONFLICT(key) DO UPDATE SET value=?",
            (str(session_day + 1), str(session_day + 1)),
        )
    conn.commit()
    conn.close()


def get_calendar_days_elapsed(db_path: str) -> int:
    start = get_start_date(db_path)
    if not start:
        return 0
    start_date = date.fromisoformat(start)
    return (date.today() - start_date).days + 1


def get_completed_sessions(db_path: str) -> int:
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM user_progress WHERE completed_at IS NOT NULL").fetchone()[0]
    conn.close()
    return count
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/study.py tests/test_study.py
git commit -m "feat: study session management and progress tracking"
```

---

### Task 10: Readiness Dashboard Scoring

**Files:**
- Create: `src/gcp_tutor/dashboard.py`
- Create: `tests/test_dashboard.py`

**Step 1: Write failing tests**

```python
# tests/test_dashboard.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import start_new_session, complete_session_component
from gcp_tutor.quiz import record_quiz_answer, get_quiz_questions
from gcp_tutor.flashcards import get_due_cards, record_flashcard_result
from gcp_tutor.dashboard import (
    calc_readiness_score, get_readiness_label, get_domain_scores,
    get_study_stats,
)

def test_readiness_score_zero_with_no_data(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    score = calc_readiness_score(tmp_db)
    assert score == 0.0

def test_readiness_label():
    assert get_readiness_label(85) == "READY"
    assert get_readiness_label(70) == "LIKELY"
    assert get_readiness_label(55) == "NEEDS WORK"
    assert get_readiness_label(40) == "NOT READY"

def test_readiness_score_with_data(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    # Complete a session
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    complete_session_component(tmp_db, 1, "flashcards")
    complete_session_component(tmp_db, 1, "quiz")
    # Answer some quiz questions
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    # Review some flashcards
    cards = get_due_cards(tmp_db, limit=5)
    for c in cards:
        record_flashcard_result(tmp_db, c["id"], rating=4)
    score = calc_readiness_score(tmp_db)
    assert 0 < score <= 100

def test_get_study_stats(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    stats = get_study_stats(tmp_db)
    assert "sessions_completed" in stats
    assert "flashcards_reviewed" in stats
    assert "quizzes_taken" in stats
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/dashboard.py`**

```python
"""Readiness dashboard scoring and statistics."""
from gcp_tutor.db import get_connection
from gcp_tutor.study import get_completed_sessions, get_total_sessions


def get_readiness_label(score: float) -> str:
    if score >= 80:
        return "READY"
    elif score >= 65:
        return "LIKELY"
    elif score >= 50:
        return "NEEDS WORK"
    return "NOT READY"


def get_readiness_color(score: float) -> str:
    if score >= 80:
        return "green"
    elif score >= 65:
        return "yellow"
    elif score >= 50:
        return "dark_orange"
    return "red"


def _quiz_score(db_path: str) -> float:
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) as t, SUM(is_correct) as c FROM quiz_results").fetchone()
    conn.close()
    if not row["t"]:
        return 0.0
    return (row["c"] / row["t"]) * 100


def _flashcard_retention(db_path: str) -> float:
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) as t, SUM(CASE WHEN rating >= 3 THEN 1 ELSE 0 END) as c FROM flashcard_results").fetchone()
    conn.close()
    if not row["t"]:
        return 0.0
    return (row["c"] / row["t"]) * 100


def _study_completion(db_path: str) -> float:
    completed = get_completed_sessions(db_path)
    total = get_total_sessions(db_path)
    if total == 0:
        return 0.0
    return (completed / total) * 100


def calc_readiness_score(db_path: str) -> float:
    quiz = _quiz_score(db_path)
    flash = _flashcard_retention(db_path)
    study = _study_completion(db_path)
    # Weighted: quiz 50%, flashcard 30%, study 20%
    score = quiz * 0.5 + flash * 0.3 + study * 0.2
    return round(score, 1)


def get_domain_scores(db_path: str) -> list[dict]:
    conn = get_connection(db_path)
    domains = conn.execute("SELECT * FROM domains ORDER BY section_number").fetchall()
    results = []
    for d in domains:
        row = conn.execute(
            """SELECT COUNT(*) as t, SUM(r.is_correct) as c
            FROM quiz_results r JOIN quiz_questions q ON r.quiz_question_id = q.id
            WHERE q.domain_id = ?""",
            (d["id"],),
        ).fetchone()
        quiz_pct = (row["c"] / row["t"] * 100) if row["t"] else 0.0
        flash_row = conn.execute(
            """SELECT COUNT(*) as t, SUM(CASE WHEN fr.rating >= 3 THEN 1 ELSE 0 END) as c
            FROM flashcard_results fr JOIN flashcards f ON fr.flashcard_id = f.id
            WHERE f.domain_id = ?""",
            (d["id"],),
        ).fetchone()
        flash_pct = (flash_row["c"] / flash_row["t"] * 100) if flash_row["t"] else 0.0
        combined = quiz_pct * 0.6 + flash_pct * 0.4
        results.append({
            "domain_id": d["id"],
            "name": d["name"],
            "section_number": d["section_number"],
            "score": round(combined, 1),
            "label": get_readiness_label(combined),
        })
    conn.close()
    return results


def get_study_stats(db_path: str) -> dict:
    conn = get_connection(db_path)
    sessions = conn.execute("SELECT COUNT(*) FROM user_progress WHERE completed_at IS NOT NULL").fetchone()[0]
    flashcards = conn.execute("SELECT COUNT(*) FROM flashcard_results").fetchone()[0]
    quizzes = conn.execute("SELECT COUNT(DISTINCT answered_at) FROM quiz_results").fetchone()[0]
    avg_row = conn.execute("SELECT AVG(is_correct) * 100 as avg FROM quiz_results").fetchone()
    avg_quiz = round(avg_row["avg"], 1) if avg_row["avg"] else 0.0
    conn.close()
    return {
        "sessions_completed": sessions,
        "flashcards_reviewed": flashcards,
        "quizzes_taken": quizzes,
        "avg_quiz_score": avg_quiz,
    }
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/dashboard.py tests/test_dashboard.py
git commit -m "feat: readiness dashboard scoring with weighted composite"
```

---

### Task 11: Weak Area Review Logic

**Files:**
- Create: `src/gcp_tutor/review.py`
- Create: `tests/test_review.py`

**Step 1: Write failing tests**

```python
# tests/test_review.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.quiz import get_quiz_questions, record_quiz_answer
from gcp_tutor.flashcards import get_due_cards, record_flashcard_result
from gcp_tutor.review import get_weak_subtopics, get_weak_domains

def test_get_weak_subtopics_empty(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    weak = get_weak_subtopics(tmp_db)
    assert weak == []  # no results yet, nothing is "weak"

def test_get_weak_subtopics_with_errors(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    # Answer questions wrong for domain 3
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    weak = get_weak_subtopics(tmp_db)
    assert len(weak) > 0
    assert weak[0]["error_rate"] > 0

def test_get_weak_domains(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    weak = get_weak_domains(tmp_db)
    assert len(weak) > 0
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/review.py`**

```python
"""Weak area identification and review session logic."""
from gcp_tutor.db import get_connection


def get_weak_subtopics(db_path: str, threshold: float = 70.0) -> list[dict]:
    """Get subtopics where error rate is above threshold (sorted worst first)."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT s.id, s.name, s.domain_id, d.name as domain_name,
            COUNT(*) as total,
            SUM(CASE WHEN r.is_correct = 0 THEN 1 ELSE 0 END) as errors
        FROM quiz_results r
        JOIN quiz_questions q ON r.quiz_question_id = q.id
        JOIN subtopics s ON q.subtopic_id = s.id
        JOIN domains d ON s.domain_id = d.id
        GROUP BY s.id
        HAVING (CAST(errors AS REAL) / total) * 100 > ?
        ORDER BY (CAST(errors AS REAL) / total) DESC""",
        (100 - threshold,),
    ).fetchall()
    conn.close()
    return [
        {
            "subtopic_id": r["id"],
            "subtopic_name": r["name"],
            "domain_id": r["domain_id"],
            "domain_name": r["domain_name"],
            "total": r["total"],
            "errors": r["errors"],
            "error_rate": round((r["errors"] / r["total"]) * 100, 1),
        }
        for r in rows
    ]


def get_weak_domains(db_path: str, threshold: float = 70.0) -> list[dict]:
    """Get domains where score is below threshold."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT d.id, d.name, d.section_number,
            COUNT(*) as total,
            SUM(r.is_correct) as correct
        FROM quiz_results r
        JOIN quiz_questions q ON r.quiz_question_id = q.id
        JOIN domains d ON q.domain_id = d.id
        GROUP BY d.id
        HAVING (CAST(correct AS REAL) / total) * 100 < ?
        ORDER BY (CAST(correct AS REAL) / total) ASC""",
        (threshold,),
    ).fetchall()
    conn.close()
    return [
        {
            "domain_id": r["id"],
            "domain_name": r["name"],
            "section_number": r["section_number"],
            "total": r["total"],
            "correct": r["correct"],
            "score": round((r["correct"] / r["total"]) * 100, 1),
        }
        for r in rows
    ]
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/review.py tests/test_review.py
git commit -m "feat: weak area identification by subtopic and domain"
```

---

### Task 12: Smart Import

**Files:**
- Create: `src/gcp_tutor/importer.py`
- Create: `tests/test_importer.py`

**Step 1: Write failing tests**

```python
# tests/test_importer.py
from pathlib import Path
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains
from gcp_tutor.importer import read_file_content, categorize_content, import_file

def test_read_txt_file(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("IAM roles are important for access control in GCP.")
    content = read_file_content(str(f))
    assert "IAM roles" in content

def test_read_md_file(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("# GKE\n\nKubernetes Engine manages containers.")
    content = read_file_content(str(f))
    assert "Kubernetes" in content

def test_read_json_file(tmp_path):
    f = tmp_path / "notes.json"
    f.write_text('{"notes": "VPC networking fundamentals"}')
    content = read_file_content(str(f))
    assert "VPC" in content

def test_categorize_content():
    text = "gcloud compute instances create my-vm --zone=us-central1-a"
    domain_id = categorize_content(text)
    assert domain_id == 3  # Deploying & implementing

def test_categorize_iam_content():
    text = "IAM policies and service accounts for security"
    domain_id = categorize_content(text)
    assert domain_id == 5  # Access & security

def test_import_file(tmp_path, tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    f = tmp_path / "study.txt"
    f.write_text("Cloud Monitoring alerts help ensure operational success.")
    import_file(tmp_db, str(f))
    conn = get_connection(tmp_db)
    imported = conn.execute("SELECT * FROM imported_content").fetchall()
    assert len(imported) == 1
    assert "Cloud Monitoring" in imported[0]["content_text"]
    conn.close()
```

**Step 2: Run tests, verify failure**

**Step 3: Implement `src/gcp_tutor/importer.py`**

```python
"""Smart import for various file formats."""
import json
from datetime import datetime
from pathlib import Path
from gcp_tutor.db import get_connection

# Keyword mapping for auto-categorization
DOMAIN_KEYWORDS = {
    1: ["project", "billing", "organization", "quota", "cloud identity", "resource hierarchy", "org policy", "apis enable"],
    2: ["planning", "machine type", "spot vm", "storage class", "nearline", "coldline", "archive", "load balancing", "network service tier", "bigtable", "spanner", "cloud sql"],
    3: ["deploy", "compute instance", "gcloud compute", "kubectl", "gke", "kubernetes", "cloud run", "cloud functions", "eventarc", "pub/sub", "dataflow", "vpc", "subnet", "firewall", "vpn", "peering", "terraform", "helm", "instance template", "managed instance group"],
    4: ["snapshot", "image", "monitoring", "logging", "alert", "ops agent", "prometheus", "cloud nat", "cloud dns", "traffic splitting", "node pool", "lifecycle", "log router", "audit log", "autoscal"],
    5: ["iam", "service account", "role", "permission", "impersonat", "credential", "access control", "policy binding", "custom role"],
}


def read_file_content(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return path.read_text()
    elif suffix == ".json":
        data = json.loads(path.read_text())
        return json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
    elif suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(path.read_text())
        return str(data)
    elif suffix == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    elif suffix in (".html", ".htm"):
        from bs4 import BeautifulSoup
        html = path.read_text()
        return BeautifulSoup(html, "html.parser").get_text()
    else:
        # Try reading as plain text
        return path.read_text()


def categorize_content(text: str) -> int | None:
    """Auto-categorize content into a domain by keyword matching. Returns domain_id or None."""
    text_lower = text.lower()
    scores = {}
    for domain_id, keywords in DOMAIN_KEYWORDS.items():
        scores[domain_id] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def import_file(db_path: str, file_path: str, domain_id: int | None = None) -> dict:
    """Import a file into the database. Auto-categorizes if domain_id not provided."""
    content = read_file_content(file_path)
    if domain_id is None:
        domain_id = categorize_content(content)
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO imported_content (filename, domain_id, content_text, imported_at) VALUES (?, ?, ?, ?)",
        (Path(file_path).name, domain_id, content, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"filename": Path(file_path).name, "domain_id": domain_id, "length": len(content)}
```

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add src/gcp_tutor/importer.py tests/test_importer.py
git commit -m "feat: smart import supporting PDF, TXT, MD, DOCX, HTML, JSON, YAML"
```

---

### Task 13: Interactive CLI App (Rich UI)

**Files:**
- Create: `src/gcp_tutor/app.py`

This is the main interactive menu that ties everything together. This task is **not TDD** — it's UI glue code that's best verified manually.

**Step 1: Implement `src/gcp_tutor/app.py`**

```python
"""Interactive CLI application."""
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

from gcp_tutor.db import init_db, DEFAULT_DB_PATH
from gcp_tutor.seed import seed_all, is_seeded
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, start_new_session,
    complete_session_component, get_calendar_days_elapsed, get_completed_sessions,
    get_total_sessions,
)
from gcp_tutor.flashcards import get_due_cards, get_cards_for_domain, record_flashcard_result
from gcp_tutor.quiz import (
    get_quiz_questions, get_questions_for_domain, record_quiz_answer, get_quiz_score,
)
from gcp_tutor.dashboard import (
    calc_readiness_score, get_readiness_label, get_readiness_color,
    get_domain_scores, get_study_stats,
)
from gcp_tutor.review import get_weak_subtopics, get_weak_domains
from gcp_tutor.importer import import_file

console = Console()


def show_welcome():
    console.print(Panel(
        "[bold]GCP Associate Cloud Engineer[/bold]\n[dim]Certification Prep Tool[/dim]",
        title="Welcome", border_style="blue",
    ))


def show_menu():
    console.print("\n[bold]Commands:[/bold]")
    commands = [
        ("study", "Today's study session"),
        ("quiz", "Practice quiz"),
        ("flashcards", "Flashcard drill"),
        ("dashboard", "Readiness score + progress"),
        ("review", "Drill weak areas"),
        ("import", "Add study material"),
        ("plan", "View 30-day plan"),
        ("quit", "Exit"),
    ]
    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:<14}[/cyan] {desc}")


def run_flashcard_session(db_path: str, cards: list) -> None:
    if not cards:
        console.print("[yellow]No flashcards due right now![/yellow]")
        return
    console.print(f"\n[bold]Flashcard Session[/bold] — {len(cards)} cards\n")
    for i, card in enumerate(cards, 1):
        console.print(Panel(card["front"], title=f"Card {i}/{len(cards)}", border_style="cyan"))
        Prompt.ask("[dim]Press Enter to reveal answer[/dim]")
        console.print(Panel(card["back"], border_style="green"))
        rating = IntPrompt.ask(
            "Rate yourself (0=forgot, 3=hard, 4=good, 5=easy)", choices=["0","1","2","3","4","5"],
        )
        record_flashcard_result(db_path, card["id"], rating)
        console.print()


def run_quiz_session(db_path: str, questions: list) -> tuple[int, int]:
    if not questions:
        console.print("[yellow]No questions available![/yellow]")
        return 0, 0
    correct = 0
    console.print(f"\n[bold]Quiz[/bold] — {len(questions)} questions\n")
    for i, q in enumerate(questions, 1):
        console.print(f"[bold]Q{i}.[/bold] {q['stem']}\n")
        console.print(f"  [cyan]a)[/cyan] {q['choice_a']}")
        console.print(f"  [cyan]b)[/cyan] {q['choice_b']}")
        console.print(f"  [cyan]c)[/cyan] {q['choice_c']}")
        console.print(f"  [cyan]d)[/cyan] {q['choice_d']}")
        answer = Prompt.ask("\nYour answer", choices=["a", "b", "c", "d"])
        is_correct = record_quiz_answer(db_path, q["id"], answer)
        if is_correct:
            console.print("[green]Correct![/green]")
            correct += 1
        else:
            console.print(f"[red]Incorrect.[/red] Answer: [green]{q['correct_answer']}[/green]")
        if q["explanation"]:
            console.print(f"[dim]{q['explanation']}[/dim]")
        console.print()
    console.print(f"[bold]Score: {correct}/{len(questions)} ({correct/len(questions)*100:.0f}%)[/bold]\n")
    return correct, len(questions)


def cmd_study(db_path: str):
    plan = get_todays_plan(db_path)
    if not plan:
        console.print("[yellow]You've completed all sessions! Use 'review' to keep studying.[/yellow]")
        return
    day = get_current_session_day(db_path)
    total = get_total_sessions(db_path)
    cal_days = get_calendar_days_elapsed(db_path)
    console.print(Panel(
        f"Session Day [bold]{day}[/bold] of {total}" + (f" (Calendar Day {cal_days})" if cal_days else "")
        + (f"\n[cyan]Domain: {plan.get('domain_name', 'Mixed Review')}[/cyan]" if plan.get("domain_name") else "\n[cyan]Mixed Review / Practice Exam[/cyan]"),
        title="Today's Study Session",
    ))
    progress = start_new_session(db_path)

    # Reading
    if not progress.get("reading_done"):
        console.print("\n[bold]1. Reading Material[/bold]")
        if plan.get("reading_content"):
            console.print(plan["reading_content"])
        else:
            console.print(f"[dim]Review the key concepts for: {plan.get('domain_name', 'all domains')}[/dim]")
        Prompt.ask("[dim]Press Enter when done reading[/dim]")
        complete_session_component(db_path, day, "reading")
        console.print("[green]Reading complete![/green]\n")

    # Flashcards
    if not progress.get("flashcards_done"):
        console.print("[bold]2. Flashcards[/bold]")
        if plan.get("domain_id"):
            cards = get_cards_for_domain(db_path, plan["domain_id"], limit=12)
        else:
            cards = get_due_cards(db_path, limit=12)
        run_flashcard_session(db_path, cards)
        complete_session_component(db_path, day, "flashcards")
        console.print("[green]Flashcards complete![/green]\n")

    # Quiz
    if not progress.get("quiz_done"):
        console.print("[bold]3. Quiz[/bold]")
        if plan.get("domain_id"):
            questions = get_questions_for_domain(db_path, plan["domain_id"], count=8)
        else:
            questions = get_quiz_questions(db_path, count=8)
        run_quiz_session(db_path, questions)
        complete_session_component(db_path, day, "quiz")
        console.print("[green]Quiz complete! Session done.[/green]")


def cmd_quiz(db_path: str):
    console.print("\n[bold]Practice Quiz[/bold]")
    mode = Prompt.ask("Quiz mode", choices=["all", "domain"], default="all")
    count = IntPrompt.ask("Number of questions", default=10)
    if mode == "domain":
        from gcp_tutor.db import get_connection
        conn = get_connection(db_path)
        domains = conn.execute("SELECT * FROM domains ORDER BY section_number").fetchall()
        conn.close()
        for d in domains:
            console.print(f"  [cyan]{d['id']}[/cyan]) {d['name']}")
        domain_id = IntPrompt.ask("Select domain", choices=[str(d["id"]) for d in domains])
        questions = get_questions_for_domain(db_path, domain_id, count=count)
    else:
        questions = get_quiz_questions(db_path, count=count)
    run_quiz_session(db_path, questions)


def cmd_flashcards(db_path: str):
    console.print("\n[bold]Flashcard Drill[/bold]")
    cards = get_due_cards(db_path, limit=15)
    run_flashcard_session(db_path, cards)


def cmd_dashboard(db_path: str):
    score = calc_readiness_score(db_path)
    label = get_readiness_label(score)
    color = get_readiness_color(score)
    day = get_current_session_day(db_path)
    total = get_total_sessions(db_path)
    cal_days = get_calendar_days_elapsed(db_path)
    stats = get_study_stats(db_path)

    # Header
    header = f"Session Day {day} of {total}"
    if cal_days:
        header += f" (Calendar Day {cal_days})"
    console.print(Panel(f"[bold]{header}[/bold]", title="GCP ACE Readiness Dashboard", border_style="blue"))

    # Overall score
    bar_filled = int(score / 5)
    bar_empty = 20 - bar_filled
    bar = f"[{color}]{'█' * bar_filled}{'░' * bar_empty}[/{color}]"
    console.print(f"\n  Overall Readiness: [bold]{score}%[/bold] {bar} [{color}]{label}[/{color}]\n")

    # Domain table
    domain_scores = get_domain_scores(db_path)
    table = Table(title="Domain Breakdown")
    table.add_column("Domain", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Status")
    for ds in domain_scores:
        sc_color = get_readiness_color(ds["score"])
        table.add_row(
            f"{ds['section_number']}. {ds['name']}",
            f"{ds['score']}%",
            f"[{sc_color}]{ds['label']}[/{sc_color}]",
        )
    console.print(table)

    # Stats
    console.print(f"\n  Sessions: [bold]{stats['sessions_completed']}[/bold]  |  "
                  f"Flashcards: [bold]{stats['flashcards_reviewed']}[/bold]  |  "
                  f"Quizzes: [bold]{stats['quizzes_taken']}[/bold]  |  "
                  f"Avg Quiz: [bold]{stats['avg_quiz_score']}%[/bold]")

    # Recommendation
    if domain_scores:
        weakest = min(domain_scores, key=lambda d: d["score"])
        if weakest["score"] < 70:
            console.print(f"\n  [yellow]Recommendation: Focus on {weakest['name']}[/yellow]")


def cmd_review(db_path: str):
    console.print("\n[bold]Weak Area Review[/bold]\n")
    weak_domains = get_weak_domains(db_path)
    if not weak_domains:
        console.print("[green]No weak areas detected! Keep up the good work.[/green]")
        return
    table = Table(title="Weak Domains")
    table.add_column("Domain")
    table.add_column("Score", justify="right")
    table.add_column("Questions Attempted", justify="right")
    for wd in weak_domains:
        table.add_row(wd["domain_name"], f"{wd['score']}%", str(wd["total"]))
    console.print(table)

    weak_subs = get_weak_subtopics(db_path)
    if weak_subs:
        console.print("\n[bold]Weakest Subtopics:[/bold]")
        for ws in weak_subs[:5]:
            console.print(f"  [red]{ws['error_rate']}% errors[/red] — {ws['subtopic_name']} ({ws['domain_name']})")

    # Drill weakest domain
    if weak_domains:
        weakest = weak_domains[0]
        console.print(f"\n[bold]Drilling: {weakest['domain_name']}[/bold]")
        cards = get_cards_for_domain(db_path, weakest["domain_id"], limit=10)
        run_flashcard_session(db_path, cards)
        questions = get_questions_for_domain(db_path, weakest["domain_id"], count=5)
        run_quiz_session(db_path, questions)


def cmd_import(db_path: str):
    file_path = Prompt.ask("File path")
    if not Path(file_path).exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return
    result = import_file(db_path, file_path)
    domain_msg = f"domain {result['domain_id']}" if result["domain_id"] else "uncategorized"
    console.print(f"[green]Imported {result['filename']} ({result['length']} chars) → {domain_msg}[/green]")


def cmd_plan(db_path: str):
    from gcp_tutor.db import get_connection
    conn = get_connection(db_path)
    days = conn.execute(
        """SELECT sd.day_number, d.name as domain_name, sd.status,
        CASE WHEN up.completed_at IS NOT NULL THEN 'Done' ELSE '' END as completed
        FROM study_days sd
        LEFT JOIN domains d ON sd.domain_id = d.id
        LEFT JOIN user_progress up ON sd.day_number = up.session_day
        ORDER BY sd.day_number"""
    ).fetchall()
    conn.close()
    table = Table(title="30-Day Study Plan")
    table.add_column("Day", justify="right")
    table.add_column("Domain")
    table.add_column("Status")
    current = get_current_session_day(db_path)
    for day in days:
        marker = " ←" if day["day_number"] == current else ""
        status = day["completed"] or ("Current" if day["day_number"] == current else "")
        table.add_row(
            str(day["day_number"]),
            day["domain_name"] or "Mixed Review",
            f"[green]{status}[/green]" if status == "Done" else f"[cyan]{status}[/cyan]",
        )
    console.print(table)


def main():
    db_path = DEFAULT_DB_PATH
    init_db(db_path)
    if not is_seeded(db_path):
        console.print("[dim]Setting up for first use...[/dim]")
        seed_all(db_path)
        console.print("[green]Ready![/green]\n")

    show_welcome()

    while True:
        show_menu()
        choice = Prompt.ask("\n[bold]>[/bold]", default="study").strip().lower()
        try:
            if choice == "study":
                cmd_study(db_path)
            elif choice == "quiz":
                cmd_quiz(db_path)
            elif choice == "flashcards":
                cmd_flashcards(db_path)
            elif choice == "dashboard":
                cmd_dashboard(db_path)
            elif choice == "review":
                cmd_review(db_path)
            elif choice == "import":
                cmd_import(db_path)
            elif choice == "plan":
                cmd_plan(db_path)
            elif choice in ("quit", "exit", "q"):
                console.print("[dim]Good luck on your exam![/dim]")
                break
            else:
                console.print("[red]Unknown command. Try again.[/red]")
        except KeyboardInterrupt:
            console.print("\n[dim]Use 'quit' to exit.[/dim]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

**Step 2: Manually test by running**

```bash
python -m gcp_tutor
```

**Step 3: Commit**

```bash
git add src/gcp_tutor/app.py
git commit -m "feat: interactive CLI menu with Rich UI for all commands"
```

---

### Task 14: Integration Test — Full Workflow

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

```python
# tests/test_integration.py
"""End-to-end test of the core workflow."""
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, start_new_session,
    complete_session_component,
)
from gcp_tutor.flashcards import get_cards_for_domain, record_flashcard_result
from gcp_tutor.quiz import get_questions_for_domain, record_quiz_answer
from gcp_tutor.dashboard import calc_readiness_score, get_domain_scores, get_study_stats
from gcp_tutor.review import get_weak_domains


def test_full_session_workflow(tmp_db):
    """Simulate a complete study session and verify all systems work together."""
    # Setup
    init_db(tmp_db)
    seed_all(tmp_db)

    # Day 1
    assert get_current_session_day(tmp_db) == 1
    plan = get_todays_plan(tmp_db)
    assert plan["domain_id"] == 3

    progress = start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")

    # Flashcards
    cards = get_cards_for_domain(tmp_db, plan["domain_id"], limit=5)
    for c in cards:
        record_flashcard_result(tmp_db, c["id"], rating=4)
    complete_session_component(tmp_db, 1, "flashcards")

    # Quiz
    questions = get_questions_for_domain(tmp_db, plan["domain_id"], count=5)
    for q in questions[:3]:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    for q in questions[3:]:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    complete_session_component(tmp_db, 1, "quiz")

    # Verify advancement
    assert get_current_session_day(tmp_db) == 2

    # Dashboard
    score = calc_readiness_score(tmp_db)
    assert score > 0
    domain_scores = get_domain_scores(tmp_db)
    assert len(domain_scores) == 5
    stats = get_study_stats(tmp_db)
    assert stats["sessions_completed"] == 1
    assert stats["flashcards_reviewed"] == 5

    # Weak areas (we got 2 wrong)
    weak = get_weak_domains(tmp_db, threshold=80)
    # Domain 3 should show up as weak (60% correct)
    assert any(w["domain_id"] == 3 for w in weak)
```

**Step 2: Run all tests**

```bash
pytest tests/ -v
```
Expected: All tests pass.

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test for full study session workflow"
```

---

### Task 15: Final Polish and README

**Files:**
- Create: `README.md` (brief usage instructions only — user requested this tool)

**Step 1: Verify full test suite passes**

```bash
pytest tests/ -v --tb=short
```

**Step 2: Verify the app runs**

```bash
python -m gcp_tutor
```

**Step 3: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final polish and README"
```

---

## Task Dependency Summary

```
Task 1 (scaffolding) → Task 2 (db) → Task 3 (models) → Task 4 (seed domains)
                                                              ↓
Task 5 (seed content) → Task 6 (SM-2) → Task 7 (flashcards) → Task 8 (quiz)
                                                                     ↓
Task 9 (study) → Task 10 (dashboard) → Task 11 (review) → Task 12 (import)
                                                                 ↓
                                              Task 13 (CLI app) → Task 14 (integration)
                                                                       ↓
                                                                 Task 15 (polish)
```
