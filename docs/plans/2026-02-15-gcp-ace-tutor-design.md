# GCP Associate Cloud Engineer Cert Tutor — Design Document

**Date:** 2026-02-15
**Status:** Approved

## Overview

A Python CLI tool that prepares learners to pass the Google Cloud Associate Cloud Engineer (ACE) certification in 30 study sessions. Features a daily study plan, flashcards with spaced repetition, practice quizzes, a readiness dashboard, weak area review, and the ability to import custom study material.

**Cost:** Zero. Runs entirely locally with no cloud dependencies.

## Architecture

- **Language:** Python 3.11+
- **CLI Framework:** Typer (command routing) + Rich (terminal UI: tables, progress bars, panels)
- **Database:** SQLite (single local file)
- **Content Source:** Curated from Google's official ACE exam guide (5 domains, weighted)
- **Custom Content:** Smart import supporting PDF, TXT, Markdown, DOCX, HTML, JSON, YAML

### Interactive Menu

The tool launches into an interactive menu (not subcommands with prefixes):

```
study          — Today's study session (reading + flashcards + mini quiz)
quiz           — Practice quiz (configurable by domain and question count)
flashcards     — Spaced-repetition flashcard drill
dashboard      — Readiness score + progress overview
review         — Drill weak areas only
import         — Add your own study material (any common file format)
plan           — View/reset your 30-day plan
quit           — Exit
```

## 30-Day Study Plan

Organized by the 5 official exam domains, ordered by exam weight (heaviest first):

| Sessions | Domain | Exam Weight |
|----------|--------|-------------|
| 1–6 | Section 3: Deploying & Implementing a Cloud Solution | 25% |
| 7–10 | Section 1: Setting Up a Cloud Solution Environment | 20% |
| 11–14 | Section 4: Ensuring Successful Operation | 20% |
| 15–18 | Section 2: Planning & Configuring a Cloud Solution | 17.5% |
| 19–22 | Section 5: Configuring Access & Security | 17.5% |
| 23–26 | Mixed review + weak area focus | — |
| 27–28 | Full-length practice exams (50 questions each) | — |
| 29–30 | Final weak area review | — |

Each daily session includes:
- Key concept reading material for the day's topics
- 10–15 flashcards (spaced repetition)
- 5–10 quiz questions on the day's topic

### Day Tracking

- Tracks **session days**, not calendar days. Skipping a real-world day doesn't skip content.
- Displays both session day and calendar day elapsed: "Session Day 12 of 30 (Calendar Day 18)"
- On return after a gap, suggests a brief warm-up review of the last studied topic.

### Extended Mode

If the learner completes 30 sessions but readiness is below 80%:
- The tool generates a custom extension plan targeting weak domains/subtopics
- Extension continues until 80%+ readiness or the learner decides to stop
- Dashboard shows: "Extended prep — Session 33. Focus: Access & Security, GKE."

## Exam Domains (Source of Truth)

Based on the official ACE exam guide (https://cloud.google.com/learn/certification/guides/cloud-engineer/):

### Section 1: Setting Up a Cloud Solution Environment (20%)
- 1.1 Setting up cloud projects and accounts (resource hierarchy, org policies, IAM roles, Cloud Identity, APIs, operations suite, quotas)
- 1.2 Managing billing configuration (billing accounts, linking projects, budgets/alerts, billing exports)

### Section 2: Planning and Configuring a Cloud Solution (17.5%)
- 2.1 Planning and configuring compute resources (Compute Engine, GKE, Cloud Run, Cloud Functions, Spot VMs, custom machine types)
- 2.2 Planning and configuring data storage options (Cloud SQL, BigQuery, Firestore, Spanner, Bigtable, storage classes)
- 2.3 Planning and configuring network resources (load balancing, resource locations, Network Service Tiers)

### Section 3: Deploying and Implementing a Cloud Solution (25%)
- 3.1 Compute Engine resources (instances, autoscaled MIGs, OS Login, VM Manager)
- 3.2 GKE resources (kubectl, cluster configs, containerized apps)
- 3.3 Cloud Run and Cloud Functions (deploying apps, event handling, Eventarc)
- 3.4 Data solutions (Cloud SQL, Firestore, BigQuery, Spanner, Pub/Sub, Dataflow, AlloyDB)
- 3.5 Networking resources (VPC/subnets, firewall rules, Cloud VPN, VPC Peering)
- 3.6 Infrastructure as code (Terraform, Cloud Foundation Toolkit, Config Connector, Helm)

### Section 4: Ensuring Successful Operation (20%)
- 4.1 Managing Compute Engine (remote connect, VM inventory, snapshots, images)
- 4.2 Managing GKE (cluster inventory, Artifact Registry, node pools, autoscaling)
- 4.3 Managing Cloud Run (new versions, traffic splitting, scaling)
- 4.4 Managing storage and databases (Cloud Storage lifecycle, queries, backups, job status)
- 4.5 Managing networking (subnets, IP addresses, Cloud DNS, Cloud NAT)
- 4.6 Monitoring and logging (alerts, custom metrics, log exports, log routers, audit logs, Ops Agent, Managed Prometheus)

### Section 5: Configuring Access and Security (17.5%)
- 5.1 Managing IAM (policies, role types, custom roles)
- 5.2 Managing service accounts (creation, minimum permissions, impersonation, short-lived credentials)

## Flashcards

- **Algorithm:** SM-2 spaced repetition (industry standard, used by Anki)
- Each card has: front (question/prompt), back (answer/explanation), domain tag, subtopic tag
- Metadata tracked: ease_factor, interval, repetitions, next_review_date
- Cards seeded from exam content; supplemented by imported material

## Practice Quizzes

- Multiple choice (4 options), matching the real exam format
- Each question has: stem, 4 choices, correct answer, explanation, domain tag, subtopic tag
- Configurable: by domain, by subtopic, by question count, or full-length (50 questions)
- Every answer recorded for weak area analysis

## Readiness Dashboard

### Score Calculation

Weighted composite:
- **Quiz scores** (50%) — rolling average across domains, weighted by exam domain percentages
- **Flashcard retention** (30%) — spaced repetition success rate
- **Study completion** (20%) — sessions completed / total sessions

### Thresholds
- 80%+ → READY (high chance of passing)
- 65–79% → LIKELY (on track)
- 50–64% → NEEDS WORK (focus on weak areas)
- Below 50% → NOT READY (consider extending timeline)

### Display
- Overall readiness percentage with progress bar
- Per-domain score table with status labels
- Study streak, flashcards reviewed, quizzes taken, avg quiz score
- Personalized recommendation (e.g., "Focus on Access & Security")

## Weak Area Review

The `review` command:
1. Aggregates all incorrect answers (quizzes + flashcards)
2. Groups by domain → subtopic
3. Ranks subtopics by error rate (worst first)
4. Runs a targeted session: re-reads material, drills flashcards, quizzes on weak subtopics only

## Smart Import

Accepts any common file format: PDF, TXT, Markdown, DOCX, HTML, JSON, YAML.

Process:
1. Read file content using appropriate Python library (PyPDF2, python-docx, markdown, etc.)
2. Parse into chunks of study content
3. Auto-categorize into exam domains by keyword matching
4. For uncategorized chunks, prompt the user to assign a domain
5. Store in SQLite as supplementary material for flashcards and quizzes

## Data Model (SQLite)

### Tables

**domains**
- id, name, section_number, exam_weight, description

**subtopics**
- id, domain_id, name, description

**study_days**
- id, day_number, domain_id, subtopic_ids (JSON), reading_content, status

**flashcards**
- id, domain_id, subtopic_id, front, back, source (seeded/imported)
- ease_factor, interval, repetitions, next_review (SM-2 fields)

**quiz_questions**
- id, domain_id, subtopic_id, stem, choice_a, choice_b, choice_c, choice_d, correct_answer, explanation, source

**user_progress**
- id, session_day, completed_at, calendar_date, reading_done, flashcards_done, quiz_done

**quiz_results**
- id, quiz_question_id, user_answer, is_correct, answered_at

**flashcard_results**
- id, flashcard_id, rating (0-5), reviewed_at

**imported_content**
- id, filename, domain_id, content_text, imported_at

**user_settings**
- id, key, value (start_date, current_session_day, etc.)

## Dependencies

```
typer>=0.9.0        # CLI framework
rich>=13.0.0        # Terminal UI (tables, panels, progress bars)
PyPDF2>=3.0.0       # PDF import
python-docx>=1.0.0  # DOCX import
markdown>=3.5.0     # Markdown import
pyyaml>=6.0.0       # YAML import
beautifulsoup4>=4.12 # HTML import
```

## Content Freshness

- Exam domains and subtopics are seeded from the official exam guide
- Content can be updated by re-running a seed/update command
- User can import additional current material at any time
- The tool's question bank can be versioned and updated independently of the code

## Sources

- Official ACE Exam Guide: https://cloud.google.com/learn/certification/guides/cloud-engineer/
- Certification Page: https://cloud.google.com/learn/certification/cloud-engineer/
- Exam Guide PDF: https://services.google.com/fh/files/misc/associate_cloud_engineer_exam_guide_english.pdf
