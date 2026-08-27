from datetime import datetime

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DueWord(BaseModel):
    word_id: int
    word: str
    pos: str | None
    category_code: str | None
    category_name: str | None
    meaning_zh: str | None
    phonetic_kk: str | None
    tier: str  # "flashcard" | "recall" | "cloze"
    due: datetime
    cloze_sentence: str | None = None
    cloze_hint_prefix: str | None = None
    cloze_hint_suffix: str | None = None


class DueResponse(BaseModel):
    due_count: int
    overdue_count: int
    words: list[DueWord]


class ReviewSubmission(BaseModel):
    word_id: int
    rating: int  # 1=Again 2=Hard 3=Good 4=Easy
    task_type: str = "flashcard"
    response_time_ms: int | None = None


class ReviewResult(BaseModel):
    word_id: int
    next_due: datetime
    state: int
    stability: float | None
    difficulty: float | None


class MCOption(BaseModel):
    word_id: int
    word: str


class MCQuestion(BaseModel):
    word_id: int          # 正確答案
    meaning_zh: str        # 題目：中文釋義
    options: list[MCOption]  # 4 個選項（已洗牌），其中一個是正確答案


class MCAnswerRequest(BaseModel):
    word_id: int           # 題目對應的正確答案
    selected_word_id: int  # 使用者選的
    response_time_ms: int | None = None


class MCAnswerResult(BaseModel):
    correct: bool
    correct_word: str
    correct_meaning: str
    rating: int
    next_due: datetime
