"""四選一小遊戲：中文釋義選正確英文單字，誘答選項故意挑拼字很像的字。

相似度用 Postgres pg_trgm 的 `<->` distance 算（trigram 越接近，distance 越小），
比自己刻 Levenshtein/edit-distance 划算，2900 字的資料量對 GIN index 來說很輕鬆。
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

# 選對且在這個時間內作答，視為「很熟」給 Easy；選對但較慢給 Good
FAST_ANSWER_MS = 3000


def pick_distractors(db: Session, word_id: int, word: str, meaning_zh: str, k: int = 3) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id AS word_id, word
            FROM words
            WHERE id != :wid
              AND (meaning_zh IS NULL OR meaning_zh != :meaning)
            ORDER BY word <-> :word
            LIMIT :k
            """
        ),
        {"wid": word_id, "word": word, "meaning": meaning_zh, "k": k},
    ).mappings().all()
    return [dict(r) for r in rows]


def build_question(db: Session, word_id: int, word: str, meaning_zh: str) -> dict:
    distractors = pick_distractors(db, word_id, word, meaning_zh, k=3)
    options = [{"word_id": word_id, "word": word}] + distractors
    random.shuffle(options)
    return {"word_id": word_id, "meaning_zh": meaning_zh, "options": options}


def derive_rating(correct: bool, response_time_ms: int | None) -> int:
    if not correct:
        return 1  # fsrs.Rating.Again
    if response_time_ms is not None and response_time_ms <= FAST_ANSWER_MS:
        return 4  # fsrs.Rating.Easy
    return 3  # fsrs.Rating.Good
