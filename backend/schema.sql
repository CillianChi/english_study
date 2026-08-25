-- TOEIC 背單字系統 — Postgres schema
-- 5 張表：users / words / learning_state / review_log / cloze_items

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 拼字相似度，用來挑「長得很像」的選擇題誘答選項

-- 使用者
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 詞庫（全域共用，不分使用者）
CREATE TABLE words (
    id            SERIAL PRIMARY KEY,
    word          TEXT NOT NULL UNIQUE,
    pos           TEXT,
    category_code TEXT,
    category_name TEXT,
    meaning_zh    TEXT
);

CREATE INDEX idx_words_category ON words(category_code);
CREATE INDEX idx_words_word_trgm ON words USING gin (word gin_trgm_ops);

-- 每個使用者、每個字的 FSRS 狀態
-- state/step/stability/difficulty/due/last_review 直接對應 fsrs.Card 的欄位，
-- 方便讀出來後用 Card(**row) 重建、review 完再用 card.to_dict() 寫回去。
CREATE TABLE learning_state (
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_id       INT  NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    state         SMALLINT NOT NULL DEFAULT 1,   -- 1=Learning 2=Review 3=Relearning (fsrs.State)
    step          SMALLINT NOT NULL DEFAULT 0,
    stability     DOUBLE PRECISION,
    difficulty    DOUBLE PRECISION,
    due           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_review   TIMESTAMPTZ,
    reps          INT NOT NULL DEFAULT 0,        -- 自行維護，決定題型 tier 用
    lapses        INT NOT NULL DEFAULT 0,        -- rating=Again 的累計次數
    PRIMARY KEY (user_id, word_id)
);

CREATE INDEX idx_learning_state_due ON learning_state(user_id, due);

-- 複習歷史（append-only，供 FSRS 分析與個人化用）
CREATE TABLE review_log (
    id                BIGSERIAL PRIMARY KEY,
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_id           INT  NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    reviewed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    rating            SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4), -- fsrs.Rating: 1=Again 2=Hard 3=Good 4=Easy
    response_time_ms  INT,
    task_type         TEXT NOT NULL DEFAULT 'flashcard'
                        CHECK (task_type IN ('flashcard', 'recall', 'cloze', 'mc'))
);

CREATE INDEX idx_review_log_user_word ON review_log(user_id, word_id);

-- AI 離線批次生成的填空題快取（全域共用，不分使用者）
CREATE TABLE cloze_items (
    id                 SERIAL PRIMARY KEY,
    word_id            INT NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    sentence_template  TEXT NOT NULL,   -- 例: "The manager decided to ___ the meeting."
    hint_prefix        TEXT,            -- 例: "po"
    hint_suffix        TEXT,            -- 例: "e"
    generated_by_model TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cloze_items_word ON cloze_items(word_id);
