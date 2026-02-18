# GCP Associate Cloud Engineer Cert Tutor

A local Python CLI tool that helps you prepare for the Google Cloud Associate Cloud Engineer (ACE) certification. It guides you through a structured 30-session study plan with daily reading, flashcards (spaced repetition), and practice quizzes — all running on your machine with no internet or cloud account required.

---

## Features

- **30-day study plan** organized by exam domain and weight
- **Flashcards** using SM-2 spaced repetition (same algorithm as Anki)
- **Practice quizzes** filtered by domain or subtopic
- **Readiness dashboard** with a weighted score and per-domain breakdown
- **Weak area review** targeting your lowest-performing topics
- **Custom import** — bring in your own notes in PDF, TXT, Markdown, DOCX, HTML, JSON, or YAML

---

## Requirements

- Python 3.11 or higher
- `pip` (comes with Python)
- `git` (to clone the repo)

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/gcp_cert_tutor.git
cd gcp_cert_tutor
```

**2. Create a virtual environment**

```bash
python3 -m venv .venv
```

**3. Activate the virtual environment**

- macOS / Linux:
  ```bash
  source .venv/bin/activate
  ```
- Windows:
  ```bash
  .venv\Scripts\activate
  ```

**4. Install the tool**

```bash
pip install -e .
```

---

## Running the Tool

Once installed, start the interactive menu with:

```bash
gcp-tutor
```

You'll see a menu with the following options:

| Command | Description |
|---|---|
| `study` | Today's study session — reading, flashcards, and a mini quiz |
| `quiz` | Practice quiz, configurable by domain and question count |
| `flashcards` | Spaced-repetition flashcard drill |
| `dashboard` | Readiness score and progress overview |
| `review` | Drill your weak areas only |
| `import` | Add your own study material from a file |
| `plan` | View or reset your 30-day plan |
| `quit` | Exit |

---

## Deactivating the Virtual Environment

When you're done studying, deactivate the virtual environment:

```bash
deactivate
```

---

## Data Storage

All progress, flashcards, and quiz results are stored in a local SQLite database file on your machine. Nothing is sent anywhere.
