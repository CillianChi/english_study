"""Generate KK phonetic transcriptions for the TOEIC 3000 word list.

Uses eng_to_ipa (CMU Pronouncing Dictionary under the hood) to get American
IPA, then applies the two systematic notation differences between that and
traditional KK (Kenyon & Knott) symbols used in Taiwan textbooks:
    eɪ -> e   (day  [de]  not [deɪ])
    oʊ -> o   (go   [go]  not [goʊ])

This is an automated approximation, not a manually verified pronunciation
dictionary -- CMUdict is generally reliable but not perfect, and a handful
of words (compounds/hyphenated forms, plus a few words that are already
truncated in toeic3000_categorized.csv, e.g. "cabine", "kidna") won't
resolve. Those are left with meaning_zh's word as-is and no phonetic.

Usage:
    python generate_phonetics.py
Writes ../toeic3000_phonetics.json  ({ "word": "kk-string", ... })
"""
import json
import os

import eng_to_ipa as ipa

MEANINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "toeic3000_meanings.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "toeic3000_phonetics.json")


def ipa_to_kk(s: str) -> str:
    return s.replace("eɪ", "e").replace("oʊ", "o")


def convert_word(word: str) -> str | None:
    if "-" in word:
        parts = [convert_word(p) for p in word.split("-")]
        if any(p is None for p in parts):
            return None
        return "-".join(parts)

    out = ipa.convert(word)
    if out.endswith("*"):
        return None
    return ipa_to_kk(out)


def main():
    with open(MEANINGS_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    result = {}
    missing = []
    for e in entries:
        w = e["w"]
        kk = convert_word(w)
        if kk is None:
            missing.append(w)
        else:
            result[w] = kk

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=0)

    print(f"generated {len(result)}/{len(entries)} phonetics, {len(missing)} missing")
    print("missing:", missing)


if __name__ == "__main__":
    main()
