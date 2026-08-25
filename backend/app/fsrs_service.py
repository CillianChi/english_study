"""Wraps the `fsrs` package (v6.3) and maps it onto the `learning_state` table.

learning_state columns (state, step, stability, difficulty, due, last_review)
are a 1:1 mirror of fsrs.Card's fields, so a DB row can be round-tripped
through Card(**fields) -> scheduler.review_card(...) -> card.to_dict()
without any extra translation layer.
"""
from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State

scheduler = Scheduler()

# Once a word's memory stability crosses this many days, it's mature enough
# to be tested with a harder, production-style task instead of recognition.
CLOZE_STABILITY_THRESHOLD_DAYS = 21
RECALL_STABILITY_THRESHOLD_DAYS = 3


def new_learning_state_fields() -> dict:
    card = Card()
    return {
        "state": int(card.state),
        "step": card.step or 0,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "due": card.due,
        "last_review": card.last_review,
        "reps": 0,
        "lapses": 0,
    }


def _row_to_card(row: dict) -> Card:
    return Card(
        card_id=row["word_id"],
        state=State(row["state"]),
        step=row["step"],
        stability=row["stability"],
        difficulty=row["difficulty"],
        due=row["due"],
        last_review=row["last_review"],
    )


def apply_review(row: dict, rating: int) -> dict:
    """Run one review through FSRS and return the updated learning_state fields
    (including reps/lapses, which FSRS itself doesn't track)."""
    card = _row_to_card(row)
    new_card, _log = scheduler.review_card(card, Rating(rating))

    return {
        "state": int(new_card.state),
        "step": new_card.step or 0,
        "stability": new_card.stability,
        "difficulty": new_card.difficulty,
        "due": new_card.due,
        "last_review": new_card.last_review,
        "reps": row["reps"] + 1,
        "lapses": row["lapses"] + (1 if rating == int(Rating.Again) else 0),
    }


def derive_tier(state: int, stability: float | None, reps: int) -> str:
    """Decide which review task to present: recognition -> recall -> production."""
    if stability is None or reps < 2 or State(state) != State.Review:
        return "flashcard"
    if stability >= CLOZE_STABILITY_THRESHOLD_DAYS:
        return "cloze"
    if stability >= RECALL_STABILITY_THRESHOLD_DAYS:
        return "recall"
    return "flashcard"
