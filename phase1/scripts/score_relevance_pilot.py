#!/usr/bin/env python3
"""
score_relevance_pilot.py — Analyze the human relevance-judgment pilot.

Reads the master items (with LLM grades) and two labeler CSVs, then reports:

  1. labeler coverage (how many items each human judged);
  2. human-human agreement (Cohen's kappa, 3-way and collapsed relevant-vs-not);
  3. human-vs-LLM agreement per labeler (Cohen's kappa + % exact);
  4. per-grade confusion: where humans and the LLM judge disagree.

Outputs a report to stdout and phase1/data/pilot/relevance/report.md.

Usage:
  python3 phase1/scripts/score_relevance_pilot.py
  (after both labelers have filled labeler_A.csv / labeler_B.csv grade columns)
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pilot" / "relevance"


def cohen_kappa(a, b, labels=(0, 1, 2)):
    n = len(a)
    if n == 0:
        return float("nan")
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    exp = 0.0
    for lab in labels:
        pa = sum(1 for x in a if x == lab) / n
        pb = sum(1 for x in b if x == lab) / n
        exp += pa * pb
    return (obs - exp) / (1 - exp) if exp < 1 else 1.0


def load_grades(csv_name):
    path = OUT / csv_name
    if not path.exists():
        return None
    grades = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g = (row.get("grade") or "").strip()
            if g in ("0", "1", "2"):
                grades[row["id"]] = int(g)
    return grades


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-items", type=int, default=30,
                    help="warn if a labeler judged fewer items than this")
    args = ap.parse_args()

    items = [json.loads(l) for l in (OUT / "items.jsonl").read_text().splitlines()
             if l.strip()]
    by_id = {p["id"]: p for p in items}
    llm = {p["id"]: p["llm_grade"] for p in items}

    gA = load_grades("labeler_A.csv") or {}
    gB = load_grades("labeler_B.csv") or {}
    print(f"items: {len(items)} | labeler A judged {len(gA)} | "
          f"labeler B judged {len(gB)}")
    if len(gA) < args.min_items or len(gB) < args.min_items:
        print(f"WARNING: at least one labeler judged < {args.min_items} items; "
              "kappa will be unstable. Ask them to finish before scoring.")

    lines = ["# Relevance pilot — human vs LLM judge", ""]
    lines += [f"- items: {len(items)}",
              f"- labeler A judged: {len(gA)}",
              f"- labeler B judged: {len(gB)}", ""]

    # ---- human-human (on items both judged) ----
    common = sorted(set(gA) & set(gB))
    if len(common) >= 5:
        a = [gA[i] for i in common]
        b = [gB[i] for i in common]
        k3 = cohen_kappa(a, b)
        k2 = cohen_kappa([1 if x == 2 else 0 for x in a],
                         [1 if x == 2 else 0 for x in b])
        agree = sum(1 for x, y in zip(a, b) if x == y) / len(a)
        print(f"human-human: n={len(common)} 3-way kappa={k3:.3f} "
              f"relevant-vs-not kappa={k2:.3f} exact={agree:.1%}")
        lines += ["## Human-human agreement",
                  f"- n = {len(common)} (items both judged)",
                  f"- Cohen's kappa (3-way 0/1/2): **{k3:.3f}**",
                  f"- Cohen's kappa (relevant(2) vs not): **{k2:.3f}**",
                  f"- exact agreement: {agree:.1%}", ""]
    else:
        print("human-human: <5 overlapping judged items; skipping")

    # ---- human vs LLM ----
    for name, g in (("A", gA), ("B", gB)):
        ids = sorted(g)
        if len(ids) < 5:
            print(f"labeler {name}: too few judgments to compare")
            continue
        h = [g[i] for i in ids]
        l = [llm[i] for i in ids]
        k3 = cohen_kappa(h, l)
        k2 = cohen_kappa([1 if x == 2 else 0 for x in h],
                         [1 if x == 2 else 0 for x in l])
        exact = sum(1 for x, y in zip(h, l) if x == y) / len(h)
        conf = Counter(zip(l, h))
        print(f"labeler {name} vs LLM: n={len(ids)} 3-way kappa={k3:.3f} "
              f"rel-vs-not kappa={k2:.3f} exact={exact:.1%}")
        lines += [f"## Labeler {name} vs LLM judge",
                  f"- n = {len(ids)}",
                  f"- Cohen's kappa (3-way): **{k3:.3f}**",
                  f"- Cohen's kappa (relevant vs not): **{k2:.3f}**",
                  f"- exact agreement: {exact:.1%}",
                  f"- confusion (LLM->human): {dict(sorted(conf.items()))}", ""]

    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("wrote", OUT / "report.md")


if __name__ == "__main__":
    main()
