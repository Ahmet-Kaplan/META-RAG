#!/usr/bin/env python3
"""
build_libra_cat.py — Build LIBRA-CAT from the joined corpus.

Ground truth per record:
  - subjects: Project Gutenberg LCSH-format subject headings (derived from
    Library of Congress subject cataloging; kept only if they contain the
    LCSH subdivision marker " -- ").
  - ddc: Dewey Decimal numbers from the matched OpenLibrary record
    (aggregated from library MARC records).

Tiers:
  Tier 1: subjects + DDC both present  (primary benchmark split)
  Tier 2: subjects only                 (secondary; DDC gold absent)

Sampling: stratified across DDC hundreds (000..900) toward `--target` Tier-1
records, then Tier-2 fill if Tier-1 yield is low.

Usage:
  python3 build_libra_cat.py [--matches ../data/join_pilot_matches.jsonl] [--target 600]
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DDC_RE = re.compile(r"^\d{3}(\.\d+)?$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", default=str(ROOT / "data" / "join_pilot_matches.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "libra_cat_records.jsonl"))
    ap.add_argument("--target", type=int, default=600)
    args = ap.parse_args()

    with open(args.matches, encoding="utf-8") as f:
        matches = [json.loads(l) for l in f if l.strip()]

    tier1, tier2 = [], []
    for m in matches:
        subs = [s for s in (m.get("gutenberg_subjects") or []) if " -- " in s]
        ddcs = [d for d in (m.get("ddc") or []) if DDC_RE.match(d)]
        if not subs:
            continue
        rec = {
            "gutenberg_id": m.get("gutenberg_id"),
            "work_key": m.get("work_key"),
            "title": m.get("gutenberg_title") or m.get("ol_title"),
            "author_name": m.get("gutenberg_authors") or m.get("ol_authors"),
            "first_publish_year": m.get("first_publish_year"),
            "gold_subjects": subs,           # LCSH-format (Gutenberg)
            "ddc": ddcs,                     # OL MARC-derived
            "plaintext_url": m.get("plaintext_url"),
        }
        (tier1 if ddcs else tier2).append(rec)

    print(f"Joined matches: {len(matches)} | Tier1 (subjects+DDC): {len(tier1)} | Tier2 (subjects only): {len(tier2)}")

    # Stratified sample across DDC classes
    by_class = {}
    for r in tier1:
        by_class.setdefault(r["ddc"][0][:3], []).append(r)
    selected = []
    per_class = {}
    for cls in sorted(by_class):
        pool = by_class[cls]
        k = max(1, len(pool) // max(1, (args.target // max(1, len(by_class)))))
        chosen = pool[::k][: max(1, args.target // max(1, len(by_class)))]
        selected.extend(chosen)
        per_class[cls] = len(chosen)
    # fill from Tier2 to reach target
    if len(selected) < args.target and tier2:
        fill = tier2[: args.target - len(selected)]
        for r in fill:
            r["tier"] = 2
        selected.extend(fill)
    for r in selected:
        r.setdefault("tier", 1)

    with open(args.out, "w", encoding="utf-8") as f:
        for r in selected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "total": len(selected),
        "tier1": sum(1 for r in selected if r["tier"] == 1),
        "tier2": sum(1 for r in selected if r["tier"] == 2),
        "per_ddc_class": per_class,
        "avg_subjects": round(sum(len(r["gold_subjects"]) for r in selected) / max(1, len(selected)), 2),
        "with_ddc": sum(1 for r in selected if r["ddc"]),
        "source_matches_used": len(matches),
    }
    with open(ROOT / "reports" / "libra_cat_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(selected)} LIBRA-CAT records -> {args.out}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
