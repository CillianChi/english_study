"""Seed cloze_items from a hand-written JSON file of {word, sentence}.

Each sentence is an original example sentence (not lifted from any book or
article) using the word's exact dictionary form, with "___" marking the
blank. hint_prefix/hint_suffix are derived mechanically from the word
itself (first ~2 letters / last 1 letter, per the convention noted in
schema.sql), so the JSON only needs to carry the sentence.

Usage:
    python seed_cloze.py [path/to/cloze_*.json]
"""
import json
import os
import sys

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DEFAULT_FILE = os.path.join(os.path.dirname(__file__), "cloze_fin.json")
GENERATED_BY = "manual-v1"


def parse_database_url(url: str) -> str:
    return url.replace("postgresql+psycopg2://", "postgresql://")


def derive_hints(word: str) -> tuple[str, str]:
    n = len(word)
    if n <= 3:
        return word[:1], ""
    prefix_len = min(2, n - 2)
    return word[:prefix_len], word[-1:]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
    database_url = parse_database_url(os.environ["DATABASE_URL"])

    with open(path, encoding="utf-8") as f:
        entries = json.load(f)

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, word FROM words WHERE word = ANY(%s)",
                        ([e["word"] for e in entries],))
            word_ids = {word: wid for wid, word in cur.fetchall()}

            missing = [e["word"] for e in entries if e["word"] not in word_ids]
            if missing:
                print(f"WARNING: {len(missing)} words not found in `words` table, skipping: {missing}")

            rows = []
            for e in entries:
                wid = word_ids.get(e["word"])
                if wid is None:
                    continue
                if "___" not in e["sentence"]:
                    print(f"WARNING: no ___ blank in sentence for '{e['word']}', skipping")
                    continue
                prefix, suffix = derive_hints(e["word"])
                rows.append((wid, e["sentence"], prefix, suffix, GENERATED_BY))

            execute_values(
                cur,
                """
                INSERT INTO cloze_items
                    (word_id, sentence_template, hint_prefix, hint_suffix, generated_by_model)
                VALUES %s
                """,
                rows,
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Inserted {len(rows)} cloze items from {path}")


if __name__ == "__main__":
    main()
