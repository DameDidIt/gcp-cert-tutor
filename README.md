# GCP Associate Cloud Engineer Cert Tutor

A local Python CLI tool that helps you prepare for the Google Cloud Associate Cloud Engineer (ACE) certification. It guides you through a structured 30-session study plan with daily reading, flashcards (spaced repetition), and practice quizzes — all running on your machine with no internet or cloud account required.

---

## Features

- **30-day study plan** organized by exam domain and weight — sessions are ordered so the heaviest-weighted domains (like Deploying & Implementing at 25%) get the most days
- **Flashcards** using the SM-2 spaced repetition algorithm (same as Anki) — cards you struggle with appear more often, cards you know well space out automatically
- **Practice quizzes** with 95+ questions across all 5 exam domains, filterable by domain or taken as a mixed set
- **Readiness dashboard** with a weighted composite score (50% quiz, 30% flashcard retention, 20% study completion) and per-domain breakdown
- **Weak area review** that identifies your lowest-performing domains and subtopics, then drills you on those specific areas
- **Session exit and resume** — type `q` or `menu` during any flashcard or quiz session to return to the main menu; your progress is saved and you can pick up where you left off
- **Progress reset** — start fresh at any time from the `plan` command without reinstalling
- **Custom import** — bring in your own study notes in PDF, TXT, Markdown, DOCX, HTML, JSON, or YAML; files are auto-categorized into the matching exam domain

---

## Exam Domains Covered

The tool covers all 5 domains from the official GCP ACE exam guide:

| Domain | Exam Weight |
|---|---|
| 1. Setting Up a Cloud Solution Environment | 20% |
| 2. Planning and Configuring a Cloud Solution | 17.5% |
| 3. Deploying and Implementing a Cloud Solution | 25% |
| 4. Ensuring Successful Operation of a Cloud Solution | 20% |
| 5. Configuring Access and Security | 17.5% |

---

## Requirements

- Python 3.11 or higher
- `pip` (comes with Python)
- `git` (to clone the repo)

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/DameDidIt/gcp-cert-tutor.git
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

On first launch the database is automatically created and seeded with all exam content (190+ flashcards, 95+ quiz questions, 30-day study plan). No extra setup needed.

---

## Commands

| Command | Description |
|---|---|
| `study` | Start today's study session (reading, flashcards, quiz) |
| `quiz` | Practice quiz — choose "all" or filter by domain, set question count |
| `flashcards` | Spaced-repetition flashcard drill for due cards |
| `dashboard` | View your overall readiness score and per-domain breakdown |
| `review` | Identify and drill your weakest domains and subtopics |
| `import` | Import your own study material from a file |
| `plan` | View the full 30-day plan with your progress, or reset to Day 1 |
| `quit` | Exit the tool |

---

## How a Study Session Works

Each daily session has three parts:

1. **Reading** — Review the key concepts for that day's domain. Press Enter when done.
2. **Flashcards** — 12 cards focused on the day's domain. Rate yourself 0-5 after each card. The SM-2 algorithm schedules your next review automatically.
3. **Quiz** — 8 multiple-choice questions on the day's domain. You get immediate feedback and explanations for each answer.

Completing all three parts advances you to the next day. If you need to leave mid-session, type `q` or `menu` at any prompt to save your progress and return to the main menu. When you come back, the session resumes where you left off.

---

## Readiness Dashboard

The dashboard shows a composite readiness score:

- **Quiz accuracy** (50% weight) — your overall correct answer rate
- **Flashcard retention** (30% weight) — percentage of flashcard reviews rated 3 or above
- **Study completion** (20% weight) — sessions completed out of 30

Score thresholds:

| Score | Label |
|---|---|
| 80%+ | READY |
| 65-79% | LIKELY |
| 50-64% | NEEDS WORK |
| Below 50% | NOT READY |

The dashboard also shows a per-domain breakdown and recommends which domain to focus on.

---

## Importing Your Own Notes

Use the `import` command to add your own study materials. Supported formats:

- `.txt`, `.md` — plain text and Markdown
- `.pdf` — extracts text from all pages
- `.docx` — extracts paragraph text
- `.html` — strips HTML tags, keeps text content
- `.json`, `.yaml` — reads and stores structured data

Imported files are automatically categorized into the matching exam domain based on keyword analysis (e.g., a file mentioning "IAM", "service accounts", and "roles" maps to Domain 5: Configuring Access and Security).

---

## Resetting Progress

To start over from Day 1:

1. Run the `plan` command
2. Choose "yes" when asked to reset progress
3. Type `reset` to confirm

This erases all quiz results, flashcard history, and session progress. Your imported content is preserved.

---

## Data Storage

All progress, flashcards, and quiz results are stored in a local SQLite database at `~/.gcp_tutor/tutor.db`. Nothing is sent anywhere — everything runs locally on your machine.

---

## Deactivating the Virtual Environment

When you're done studying:

```bash
deactivate
```
