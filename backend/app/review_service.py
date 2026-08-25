from sqlalchemy import text
from sqlalchemy.orm import Session

from . import fsrs_service


def record_review(
    db: Session,
    user_id: str,
    word_id: int,
    rating: int,
    task_type: str,
    response_time_ms: int | None,
) -> dict:
    """Run one review through FSRS, persist learning_state + review_log.
    Shared by the plain /review endpoint and every game mode so every task
    type (flashcard, recall, cloze, mc, ...) feeds the same scheduler."""
    row = db.execute(
        text(
            "SELECT word_id, state, step, stability, difficulty, due, last_review, reps, lapses "
            "FROM learning_state WHERE user_id = :uid AND word_id = :wid"
        ),
        {"uid": user_id, "wid": word_id},
    ).mappings().first()

    if row is None:
        fields = fsrs_service.new_learning_state_fields()
    else:
        fields = fsrs_service.apply_review(dict(row), rating)
    fields["word_id"] = word_id

    db.execute(
        text(
            """
            INSERT INTO learning_state
                (user_id, word_id, state, step, stability, difficulty, due, last_review, reps, lapses)
            VALUES
                (:uid, :word_id, :state, :step, :stability, :difficulty, :due, :last_review, :reps, :lapses)
            ON CONFLICT (user_id, word_id) DO UPDATE SET
                state = EXCLUDED.state,
                step = EXCLUDED.step,
                stability = EXCLUDED.stability,
                difficulty = EXCLUDED.difficulty,
                due = EXCLUDED.due,
                last_review = EXCLUDED.last_review,
                reps = EXCLUDED.reps,
                lapses = EXCLUDED.lapses
            """
        ),
        {"uid": user_id, **fields},
    )

    db.execute(
        text(
            """
            INSERT INTO review_log (user_id, word_id, rating, response_time_ms, task_type)
            VALUES (:uid, :wid, :rating, :rt, :task_type)
            """
        ),
        {
            "uid": user_id,
            "wid": word_id,
            "rating": rating,
            "rt": response_time_ms,
            "task_type": task_type,
        },
    )

    db.commit()
    return fields
