"""Data classes for the tutor domain model."""
from dataclasses import dataclass
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
