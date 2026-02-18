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
    first_run = not is_seeded(db_path)
    if first_run:
        console.print("[dim]Setting up for first use...[/dim]")
    seed_all(db_path)
    if first_run:
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
