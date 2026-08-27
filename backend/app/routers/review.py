import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import fsrs_service
from ..categories import CATEGORY_NAMES
from ..db import get_db
from ..deps import get_current_user_id
from ..review_service import record_review
from ..schemas import DueResponse, DueWord, ReviewResult, ReviewSubmission

router = APIRouter(tags=["review"])

NEW_WORDS_PER_SESSION = 10


def _primary_category(row: dict) -> str:
    """A word can carry several tags; sort_order 0 (codes[0]) is its primary
    one and is all interleaving needs — a representative bucket key, not
    the full tag list (which still goes to the client as category_codes)."""
    codes = row.get("category_codes")
    return codes[0] if codes else ""


def _interleave_by_category(rows: list[dict]) -> list[dict]:
    """Round-robin across each word's primary category so a session doesn't
    run through one whole category before touching another (interleaving >
    blocking)."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[_primary_category(r)].append(r)
    for bucket in buckets.values():
        random.shuffle(bucket)

    queue = []
    bucket_lists = list(buckets.values())
    while any(bucket_lists):
        for bucket in bucket_lists:
            if bucket:
                queue.append(bucket.pop())
        bucket_lists = [b for b in bucket_lists if b]
    return queue


@router.get("/due", response_model=DueResponse)
def get_due(
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    now = datetime.now(timezone.utc)
    overdue_cutoff = now - timedelta(days=1)

    due_count = db.execute(
        text(
            "SELECT count(*) FROM learning_state WHERE user_id = :uid AND due <= :now"
        ),
        {"uid": user_id, "now": now},
    ).scalar_one()

    overdue_count = db.execute(
        text(
            "SELECT count(*) FROM learning_state WHERE user_id = :uid AND due <= :cutoff"
        ),
        {"uid": user_id, "cutoff": overdue_cutoff},
    ).scalar_one()

    # word_categories.sort_order = 0 is each word's primary tag; array_agg
    # (ordered) gives the full multi-tag list for display. Both come from
    # the one join instead of a per-word N+1 query.
    category_join = """
        LEFT JOIN LATERAL (
            SELECT
                array_agg(wc.category_code ORDER BY wc.sort_order) AS codes
            FROM word_categories wc
            WHERE wc.word_id = w.id
        ) wc_agg ON true
    """

    due_rows = db.execute(
        text(
            f"""
            SELECT ls.word_id, ls.state, ls.stability, ls.difficulty, ls.due,
                   ls.reps, ls.lapses, w.word, w.pos, w.meaning_zh, w.phonetic_kk,
                   wc_agg.codes AS category_codes
            FROM learning_state ls
            JOIN words w ON w.id = ls.word_id
            {category_join}
            WHERE ls.user_id = :uid AND ls.due <= :now
            ORDER BY ls.due ASC
            LIMIT :limit
            """
        ),
        {"uid": user_id, "now": now, "limit": limit},
    ).mappings().all()

    fresh_rows = db.execute(
        text(
            f"""
            SELECT w.id AS word_id, w.word, w.pos, w.meaning_zh, w.phonetic_kk,
                   wc_agg.codes AS category_codes
            FROM words w
            LEFT JOIN learning_state ls ON ls.word_id = w.id AND ls.user_id = :uid
            {category_join}
            WHERE ls.word_id IS NULL
            ORDER BY w.id ASC
            LIMIT :limit
            """
        ),
        {"uid": user_id, "limit": NEW_WORDS_PER_SESSION},
    ).mappings().all()

    candidates = [dict(r) for r in due_rows] + [dict(r) for r in fresh_rows]
    queue = _interleave_by_category(candidates)[:limit]

    results = []
    for row in queue:
        is_new = "state" not in row or row.get("state") is None
        if is_new:
            tier = "flashcard"
            due = now
        else:
            tier = fsrs_service.derive_tier(row["state"], row["stability"], row["reps"])
            due = row["due"]

        cloze = None
        if tier == "cloze":
            cloze = db.execute(
                text(
                    "SELECT sentence_template, hint_prefix, hint_suffix "
                    "FROM cloze_items WHERE word_id = :wid ORDER BY random() LIMIT 1"
                ),
                {"wid": row["word_id"]},
            ).mappings().first()
            if cloze is None:
                tier = "recall"  # no AI-generated content cached yet, fall back

        codes = row.get("category_codes") or []
        results.append(
            DueWord(
                word_id=row["word_id"],
                word=row["word"],
                pos=row["pos"],
                category_codes=codes,
                category_names=[CATEGORY_NAMES.get(c, c) for c in codes],
                meaning_zh=row["meaning_zh"],
                phonetic_kk=row["phonetic_kk"],
                tier=tier,
                due=due,
                cloze_sentence=cloze["sentence_template"] if cloze else None,
                cloze_hint_prefix=cloze["hint_prefix"] if cloze else None,
                cloze_hint_suffix=cloze["hint_suffix"] if cloze else None,
            )
        )

    return DueResponse(due_count=due_count, overdue_count=overdue_count, words=results)


@router.post("/review", response_model=ReviewResult)
def submit_review(
    body: ReviewSubmission,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if not 1 <= body.rating <= 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rating must be 1-4")

    fields = record_review(
        db, user_id, body.word_id, body.rating, body.task_type, body.response_time_ms
    )

    return ReviewResult(
        word_id=body.word_id,
        next_due=fields["due"],
        state=fields["state"],
        stability=fields["stability"],
        difficulty=fields["difficulty"],
    )
