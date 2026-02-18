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
