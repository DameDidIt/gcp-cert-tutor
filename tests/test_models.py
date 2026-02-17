"""Tests for data model classes."""
from gcp_tutor.models import Domain, Subtopic, Flashcard, QuizQuestion, StudyDay, UserProgress


def test_domain_creation():
    d = Domain(id=1, name="Deploying", section_number=3, exam_weight=0.25, description="Deploy stuff")
    assert d.name == "Deploying"
    assert d.exam_weight == 0.25
    assert d.section_number == 3
    assert d.id == 1


def test_domain_default_description():
    d = Domain(id=2, name="Planning", section_number=1, exam_weight=0.20)
    assert d.description == ""


def test_subtopic_creation():
    s = Subtopic(id=1, domain_id=1, name="Compute Engine")
    assert s.name == "Compute Engine"
    assert s.domain_id == 1
    assert s.description == ""


def test_flashcard_defaults():
    f = Flashcard(id=1, domain_id=1, front="Q?", back="A")
    assert f.ease_factor == 2.5
    assert f.interval == 0
    assert f.repetitions == 0
    assert f.subtopic_id is None
    assert f.source == "seeded"
    assert f.next_review is None


def test_flashcard_with_values():
    f = Flashcard(id=2, domain_id=1, front="Q?", back="A", ease_factor=3.0, interval=5, repetitions=2)
    assert f.ease_factor == 3.0
    assert f.interval == 5
    assert f.repetitions == 2


def test_quiz_question_creation():
    q = QuizQuestion(
        id=1, domain_id=1, stem="What is GKE?",
        choice_a="A", choice_b="B", choice_c="C", choice_d="D",
        correct_answer="a", explanation="GKE is Kubernetes Engine"
    )
    assert q.correct_answer == "a"
    assert q.explanation == "GKE is Kubernetes Engine"
    assert q.source == "seeded"
    assert q.subtopic_id is None


def test_study_day_defaults():
    sd = StudyDay(id=1, day_number=1, domain_id=1)
    assert sd.subtopic_ids == "[]"
    assert sd.reading_content == ""
    assert sd.status == "pending"


def test_user_progress_defaults():
    up = UserProgress(id=1, session_day=1)
    assert up.completed_at is None
    assert up.calendar_date is None
    assert up.reading_done is False
    assert up.flashcards_done is False
    assert up.quiz_done is False
