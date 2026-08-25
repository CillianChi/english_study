"""Import toeic3000_categorized.csv (+ Chinese meanings) into the words table.

Usage:
    python import_words.py [path/to/csv] [path/to/meanings.json]

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


def parse_database_url(url: str) -> str:
    # psycopg2 doesn't understand the "+psycopg2" SQLAlchemy dialect suffix.
    return url.replace("postgresql+psycopg2://", "postgresql://")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    meanings_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MEANINGS
    database_url = parse_database_url(os.environ["DATABASE_URL"])

    meanings = {}
    if os.path.exists(meanings_path):
        with open(meanings_path, encoding="utf-8") as f:
            for entry in json.load(f):
                meanings[entry["w"]] = entry.get("d")

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((
                r["word"], r["pos"], r["category_codes"], r["category_names"],
                meanings.get(r["word"]),
            ))

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO words (word, pos, category_code, category_name, meaning_zh)
                VALUES %s
                ON CONFLICT (word) DO UPDATE SET
                    pos = EXCLUDED.pos,
                    category_code = EXCLUDED.category_code,
                    category_name = EXCLUDED.category_name,
                    meaning_zh = EXCLUDED.meaning_zh
                """,
                rows,
            )
        conn.commit()
    finally:
        conn.close()

    matched = sum(1 for r in rows if r[4])
    print(f"Imported {len(rows)} words from {csv_path} ({matched} with Chinese meaning)")


if __name__ == "__main__":
    main()
