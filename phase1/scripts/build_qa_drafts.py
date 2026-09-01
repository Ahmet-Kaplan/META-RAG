#!/usr/bin/env python3
"""
build_qa_drafts.py — Draft LIBRA-QA (discovery questions) from joined books.

Question classes:
  - known_item     : locate a book by title/author/year           gold = work_key
  - topical        : find a book about a subject (LCSH-derived)   gold = work_key
  - bib_fact       : factual questions about a record's fields    gold = field value(s)

Design notes:
  * Template-based generation with a seeded RNG => reproducible drafts.
  * Gold answers are derived from the catalog record itself, so they are
    verifiable by construction (a validation pass asserts non-empty gold).
  * LLM hooks: functions `generate_with_llm()` are stubs — once you set an LLM
    API key (see phase1/README.md), swap template questions for LLM-written
    ones with the same gold constraints. Human review + IAA comes after.

Usage:
  python3 build_qa_drafts.py [--matches ../data/join_pilot_matches.jsonl]
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pick_subject(rec):
    """Prefer a medium-length LCSH heading (informative but answerable)."""
    subs = (rec.get("gutenberg_subjects") or []) or (rec.get("ol_lcsh") or [])
    if not subs:
        return None
    subs = [s for s in subs if len(s) <= 90]
    return subs[0] if subs else ((rec.get("gutenberg_subjects") or rec.get("ol_lcsh") or [None])[0])


def short_title(t):
    return re.sub(r"\s*[:(].*$", "", t or "").strip()


def year_str(rec):
    y = rec.get("first_publish_year")
    return str(y) if y else ""


def build_questions(rec, rng):
    qs = []
    title = short_title(rec.get("gutenberg_title") or rec.get("ol_title") or "this book")
    key = rec["work_key"]
    year = year_str(rec)
    authors = rec.get("gutenberg_authors") or rec.get("ol_authors") or []

    # --- known-item ---
    qs.append({
        "type": "known_item",
        "question": f"Find the book titled '{title}' in this collection.",
        "gold": [key],
    })
    if authors and year:
        author = re.sub(r"\s+", " ", authors[0].replace(",", " ")).strip()
        qs.append({
            "type": "known_item",
            "question": f"Locate the work by {author}, published in {year}, in this collection.",
            "gold": [key],
        })
    elif authors:
        author = re.sub(r"\s+", " ", authors[0].replace(",", " ")).strip()
        qs.append({
            "type": "known_item",
            "question": f"Which book in this collection was written by {author}?",
            "gold": [key],
        })

    # --- topical (from LCSH) ---
    subj = pick_subject(rec)
    if subj:
        for _ in range(2):
            variant = rng.choice([
                f"Find a book about {subj} in this collection.",
                f"Which book in this collection covers {subj}?",
            ])
            qs.append({"type": "topical", "question": variant, "gold": [key]})

    # --- bibliographic fact ---
    lcsh = (rec.get("gutenberg_subjects") or []) or (rec.get("ol_lcsh") or [])
    ddc = rec.get("ddc") or []
    if lcsh:
        qs.append({
            "type": "bib_fact",
            "question": f"Under which subject headings is '{title}' filed?",
            "gold": lcsh,
        })
    if ddc:
        qs.append({
            "type": "bib_fact",
            "question": f"What Dewey Decimal class number is assigned to '{title}'?",
            "gold": ddc,
        })
    if authors:
        qs.append({
            "type": "bib_fact",
            "question": f"Who is the author of '{title}'?",
            "gold": authors,
        })
    return qs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", default=str(ROOT / "data" / "join_pilot_matches.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "libra_qa_drafts.jsonl"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-questions", type=int, default=600)
    args = ap.parse_args()

    with open(args.matches, encoding="utf-8") as f:
        recs = [json.loads(l) for l in f if l.strip()]
    rng = random.Random(args.seed)

    out, dist, invalid = [], {}, 0
    for rec in recs:
        for q in build_questions(rec, rng):
            q["qid"] = f"QA-{len(out):05d}"
            q["work_key"] = rec["work_key"]
            q["gutenberg_id"] = rec["gutenberg_id"]
            q["book_title"] = rec.get("gutenberg_title") or rec.get("ol_title")
            q["verifiable"] = bool(q["gold"])
            if not q["verifiable"]:
                invalid += 1
            dist[q["type"]] = dist.get(q["type"], 0) + 1
            out.append(q)
            if len(out) >= args.max_questions:
                break
        if len(out) >= args.max_questions:
            break

    with open(args.out, "w", encoding="utf-8") as f:
        for q in out:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"Wrote {len(out)} draft questions -> {args.out}")
    print(f"  distribution: {dist}")
    print(f"  with empty gold (invalid): {invalid}")

    stats = {"total": len(out), "by_type": dist, "invalid": invalid,
             "books_used": len({q['work_key'] for q in out})}
    with open(ROOT / "reports" / "qa_draft_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
