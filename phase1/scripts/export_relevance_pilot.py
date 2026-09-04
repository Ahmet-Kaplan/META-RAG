#!/usr/bin/env python3
"""
export_relevance_pilot.py — Build the human-relevance-judgment pilot workbook.

WHAT THIS IS FOR
The pooled graded relevance check (§V-G) is entirely LLM-judged: an LLM graded
~11k (query, record) pairs (0/1/2). The AIDL reviewer's last comment asks for
human validation of those judgments. This script samples a STRATIFIED subset
of (query, record) pairs and writes two blinded CSVs — one per labeler — plus
a key file mapping item ids to the LLM judge's grades (NOT shown to labelers).

Both labelers judge the SAME items independently; agreement between them
(human-human kappa) and between each and the LLM (human-LLM kappa) is computed
by score_relevance_pilot.py.

SAMPLING STRATEGY
The LLM judge graded 338 topical queries x ~33 pooled candidates = 11,242
pairs, with a heavily skewed distribution (0: 9845, 1: 636, 2: 761). Humans
should not spend most of their effort on trivially irrelevant pairs, and a
sample with too few grade-2 pairs cannot validate the relevant judgments that
drive the gap-fill result. We therefore:

  - stratify by the LLM grade: sample grade-2 pairs with high probability,
    grade-1 with medium probability, grade-0 with low probability;
  - require that every sampled QUERY contributes at least one pair (so the
    graded-nDCG recomputation in the scorer covers many queries);
  - cap total pairs per labeler at --per-labeler (default 120, ~40-60 min of
    judging per labeler at 20-30 s/pair).

Outputs (phase1/data/pilot/relevance/):
  items.jsonl      master list: id, qid, work_key, question, title, authors,
                   subjects, llm_grade  (llm_grade used by scorer only)
  labeler_A.csv    id, question, title, authors, subjects, blank grade column
  labeler_B.csv    same items in a DIFFERENT random order (order effects)
  rubric.md        judging instructions handed to the labelers

Usage:
  python3 phase1/scripts/export_relevance_pilot.py [--per-labeler 120] [--seed 7]
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QRELS = ROOT.parent / "phase2" / "reports" / "pooled_qrels.json"
QA = ROOT / "data" / "libra_qa_drafts_scaled_polished.jsonl"
CORPUS = ROOT.parent / "phase2" / "data" / "corpus_scaled.jsonl"
OUT = ROOT / "data" / "pilot" / "relevance"

RUBRIC = """# Relevance judgment — instructions

You are judging whether BOOKS are relevant to a PATRON'S REQUEST, exactly as a
reference librarian would. Judge the book, not the wording of the request.

Grade each candidate book:

  2 = clearly relevant — a good answer to the request
  1 = marginally relevant — related, but a poor answer
  0 = not relevant

Rules:
- Base the judgment on the book's title, author, and subject headings only
  (this is all the information a catalog would give a patron).
- A book is relevant only if a patron making this request would be glad to
  receive it. Be strict.
- Judge the book itself; do not try to guess what "the system" expected.
- There is no quota; use all three grades as appropriate.

Work through the rows in order. Enter 0, 1, or 2 in the grade column.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-labeler", type=int, default=120,
                    help="max pairs per labeler (same items for both)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    qrels = json.loads(QRELS.read_text())
    qa = {json.loads(l)["qid"]: json.loads(l)
          for l in QA.read_text().splitlines() if l.strip()}
    corpus = {json.loads(l)["work_key"]: json.loads(l)
              for l in CORPUS.read_text().splitlines() if l.strip()}

    # ---- enumerate all (query, record) pairs with LLM grades ----
    pairs = []
    for qid, recs in qrels.items():
        q = qa.get(qid)
        if not q:
            continue
        for wk, grade in recs.items():
            r = corpus.get(wk, {})
            if not r:
                continue
            pairs.append({
                "qid": qid,
                "work_key": wk,
                "question": q.get("question_polished") or q.get("question", ""),
                "title": r.get("title", ""),
                "authors": "; ".join((r.get("authors") or [])[:3]),
                "subjects": "; ".join((r.get("subjects") or [])[:5]),
                "llm_grade": grade,
            })
    print(f"{len(pairs)} graded (query, record) pairs available")

    rng = random.Random(args.seed)
    # grade-stratified weights: 2s and 1s are the informative judgments
    def weight(p):
        return {0: 0.15, 1: 1.0, 2: 1.6}[p["llm_grade"]]

    # ensure query coverage: shuffle queries, take pairs greedily until the
    # per-labeler cap is reached, weighted toward 1/2 grades within each query.
    by_q = {}
    for p in pairs:
        by_q.setdefault(p["qid"], []).append(p)
    qids = sorted(by_q)
    rng.shuffle(qids)

    chosen = []
    seen_pairs = set()
    for qid in qids:
        if len(chosen) >= args.per_labeler:
            break
        q_pairs = by_q[qid]
        # keep all 2s first (they carry the result), then weighted pick
        q_pairs.sort(key=lambda p: (-p["llm_grade"], rng.random()))
        for p in q_pairs:
            if len(chosen) >= args.per_labeler:
                break
            key = (p["qid"], p["work_key"])
            if key in seen_pairs:
                continue
            # weighted acceptance so 0s don't dominate the tail
            if rng.random() > weight(p) / 2.0 and len(chosen) > 20:
                continue
            seen_pairs.add(key)
            chosen.append(p)

    # add pairs until cap even if weighting over-filtered
    if len(chosen) < args.per_labeler:
        for p in pairs:
            if len(chosen) >= args.per_labeler:
                break
            key = (p["qid"], p["work_key"])
            if key not in seen_pairs:
                seen_pairs.add(key)
                chosen.append(p)

    rng.shuffle(chosen)
    for i, p in enumerate(chosen, 1):
        p["id"] = f"REL-{i:04d}"

    # grade balance report
    from collections import Counter
    bal = Counter(p["llm_grade"] for p in chosen)
    n_q = len({p["qid"] for p in chosen})
    print(f"chosen {len(chosen)} pairs across {n_q} queries")
    print("LLM-grade balance:", dict(bal))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text(
        "\n".join(json.dumps(p) for p in chosen) + "\n")

    def write_csv(name, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "question", "title", "authors", "subjects", "grade"])
            for r in rows:
                w.writerow([r["id"], r["question"], r["title"],
                            r["authors"], r["subjects"], ""])

    write_csv("labeler_A.csv", chosen)
    order_b = chosen[:]
    rng.shuffle(order_b)
    write_csv("labeler_B.csv", order_b)
    (OUT / "rubric.md").write_text(RUBRIC)
    print(f"wrote {OUT/'labeler_A.csv'}, {OUT/'labeler_B.csv'}, rubric.md")


if __name__ == "__main__":
    main()
