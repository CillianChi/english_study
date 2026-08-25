from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import game_service
from ..db import get_db
from ..deps import get_current_user_id
from ..review_service import record_review
from ..schemas import MCAnswerRequest, MCAnswerResult, MCQuestion

router = APIRouter(prefix="/game/mc", tags=["game"])


def _select_target_words(db: Session, user_id: str, count: int) -> list[dict]:
    now = datetime.now(timezone.utc)

    due_rows = db.execute(
        text(
            """
            SELECT w.id AS word_id, w.word, w.meaning_zh
            FROM learning_state ls
            JOIN words w ON w.id = ls.word_id
            WHERE ls.user_id = :uid AND ls.due <= :now AND w.meaning_zh IS NOT NULL
            ORDER BY ls.due ASC
            LIMIT :count
            """
        ),
        {"uid": user_id, "now": now, "count": count},
    ).mappings().all()

    words = [dict(r) for r in due_rows]
    if len(words) < count:
        remaining = count - len(words)
        fresh_rows = db.execute(
            text(
                """
                SELECT w.id AS word_id, w.word, w.meaning_zh
                FROM words w
                LEFT JOIN learning_state ls ON ls.word_id = w.id AND ls.user_id = :uid
                WHERE ls.word_id IS NULL AND w.meaning_zh IS NOT NULL
                ORDER BY w.id ASC
                LIMIT :remaining
                """
            ),
            {"uid": user_id, "remaining": remaining},
        ).mappings().all()
        words += [dict(r) for r in fresh_rows]

    return words


@router.get("/questions", response_model=list[MCQuestion])
def get_questions(
    count: int = Query(10, le=30),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    targets = _select_target_words(db, user_id, count)
    return [
        game_service.build_question(db, t["word_id"], t["word"], t["meaning_zh"])
        for t in targets
    ]


@router.post("/answer", response_model=MCAnswerResult)
def answer_question(
    body: MCAnswerRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    target = db.execute(
        text("SELECT word, meaning_zh FROM words WHERE id = :wid"),
        {"wid": body.word_id},
    ).mappings().first()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "word not found")

    correct = body.selected_word_id == body.word_id
    rating = game_service.derive_rating(correct, body.response_time_ms)

    fields = record_review(
        db, user_id, body.word_id, rating, "mc", body.response_time_ms
    )

    return MCAnswerResult(
        correct=correct,
        correct_word=target["word"],
        correct_meaning=target["meaning_zh"],
        rating=rating,
        next_due=fields["due"],
    )
