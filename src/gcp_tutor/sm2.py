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
