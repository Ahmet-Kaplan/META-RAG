#!/usr/bin/env python3
"""
permutation_fullpool.py — Paired permutation tests over the full question pool.

Reads the per-question nDCG cache written by phase2/scripts/confidence.py and
writes phase2/reports/permutation_fullpool{tag}.json, which finalize_fullpool.py
turns into the paper's p-value macros.

Usage:
  python3 permutation_fullpool.py [--tag _1300] [--iters 20000]
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TYPES = ("known_item", "topical", "bib_fact")
PAIRS = {"meta_vs_hybrid": ("meta", "hybrid"),
         "enr_vs_base": ("sp_enr1.00", "sp_base1.00")}


def perm_p(a, b, iters, seed=11):
    rng = random.Random(seed)
    d = [x - y for x, y in zip(a, b)]
    obs = abs(sum(d))
    cnt = sum(1 for _ in range(iters)
              if abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= obs)
    return (cnt + 1) / (iters + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--qa", default=str(ROOT / "phase1/data/libra_qa_drafts_scaled_polished.jsonl"))
    args = ap.parse_args()

    per_q = json.loads((ROOT / f"phase2/reports/confidence_per_question{args.tag}.json").read_text())
    qtype = {json.loads(l)["qid"]: json.loads(l)["type"] for l in open(args.qa)}
    qids = sorted(per_q["meta"])

    out = {}
    for label, (A, B) in PAIRS.items():
        if A not in per_q or B not in per_q:
            print(f"skip {label}: missing {A} or {B}")
            continue
        out[label] = {}
        for t in TYPES:
            ids = [q for q in qids if qtype.get(q) == t]
            a = [per_q[A][q] for q in ids]
            b = [per_q[B][q] for q in ids]
            p = perm_p(a, b, args.iters)
            out[label][t] = {"n": len(ids), "p": p}
            print(f"{label:16s} {t:11s} n={len(ids):4d}  "
                  f"{A}={sum(a)/len(a):.3f} {B}={sum(b)/len(b):.3f}  p={p:.5f}")
    dest = ROOT / f"phase2/reports/permutation_fullpool{args.tag}.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
