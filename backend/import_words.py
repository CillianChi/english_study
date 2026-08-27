"""Import toeic3000_categorized.csv (+ Chinese meanings + KK phonetics) into
the words table.

Usage:
    python import_words.py [path/to/csv] [path/to/meanings.json] [path/to/phonetics.json]

Reads DATABASE_URL from .env (same format as app/config.py).
"""
import csv
import json
import os
import sys

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "..", "toeic3000_categorized.csv")
DEFAULT_MEANINGS = os.path.join(os.path.dirname(__file__), "..", "toeic3000_meanings.json")
DEFAULT_PHONETICS = os.path.join(os.path.dirname(__file__), "..", "toeic3000_phonetics.json")


def parse_database_url(url: str) -> str:
    # psycopg2 doesn't understand the "+psycopg2" SQLAlchemy dialect suffix.
    return url.replace("postgresql+psycopg2://", "postgresql://")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    meanings_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MEANINGS
    phonetics_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PHONETICS
    database_url = parse_database_url(os.environ["DATABASE_URL"])

    meanings = {}
    if os.path.exists(meanings_path):
        with open(meanings_path, encoding="utf-8") as f:
            for entry in json.load(f):
                meanings[entry["w"]] = entry.get("d")

    phonetics = {}
    if os.path.exists(phonetics_path):
        with open(phonetics_path, encoding="utf-8") as f:
            phonetics = json.load(f)

    word_rows = []
    categories_by_word = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            word_rows.append((
                r["word"], r["pos"], meanings.get(r["word"]), phonetics.get(r["word"]),
            ))
            categories_by_word[r["word"]] = r["category_codes"].split("|")

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            id_rows = execute_values(
                cur,
                """
                INSERT INTO words (word, pos, meaning_zh, phonetic_kk)
                VALUES %s
                ON CONFLICT (word) DO UPDATE SET
                    pos = EXCLUDED.pos,
                    meaning_zh = EXCLUDED.meaning_zh,
                    phonetic_kk = EXCLUDED.phonetic_kk
                RETURNING id, word
                """,
                word_rows,
                fetch=True,
            )
            word_ids = {word: wid for wid, word in id_rows}

            cat_rows = [
                (word_ids[word], code, order)
                for word, codes in categories_by_word.items()
                for order, code in enumerate(codes)
            ]
            cur.execute(
                "DELETE FROM word_categories WHERE word_id = ANY(%s)",
                (list(word_ids.values()),),
            )
            execute_values(
                cur,
                "INSERT INTO word_categories (word_id, category_code, sort_order) VALUES %s",
                cat_rows,
            )
        conn.commit()
    finally:
        conn.close()

    with_meaning = sum(1 for r in word_rows if r[2])
    with_phonetic = sum(1 for r in word_rows if r[3])
    print(
        f"Imported {len(word_rows)} words from {csv_path} "
        f"({with_meaning} with Chinese meaning, {with_phonetic} with KK phonetics)"
    )
    print(f"Inserted {len(cat_rows)} word-category tags")


if __name__ == "__main__":
    main()
