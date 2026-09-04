#!/usr/bin/env python3
"""
score_faithfulness_pilot.py — Analyze the human faithfulness-judgment pilot.

Reports, over the items both labelers judged:
  - human-human agreement (Cohen's kappa on binary faithful/not);
  - human-vs-LLM-judge agreement per labeler (kappa + % exact);
  - confusion and disagreement examples (ids only, so quotes stay in the
    workbooks).

Outputs a report to stdout and phase1/data/pilot/faithfulness/report.md.

Usage:
  python3 phase1/scripts/score_faithfulness_pilot.py
  (after both labelers filled labeler_A.csv / labeler_B.csv)
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pilot" / "faithfulness"


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = (sum(a) / n) * (sum(b) / n) + (1 - sum(a) / n) * (1 - sum(b) / n)
    return (obs - pa) / (1 - pa) if pa < 1 else 1.0


def parse_bool(v):
    v = (v or "").strip().lower()
    if v in ("yes", "true", "1", "y", "faithful"):
        return True
    if v in ("no", "false", "0", "n", "unfaithful"):
        return False
    return None


def load_labels(csv_name):
    path = OUT / csv_name
    if not path.exists():
        return None
    labels = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            b = parse_bool(row.get("faithful"))
            if b is not None:
                labels[row["id"]] = b
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-items", type=int, default=20)
    args = ap.parse_args()

    items = [json.loads(l) for l in (OUT / "items.jsonl").read_text().splitlines()
             if l.strip()]
    by_id = {x["id"]: x for x in items}
    llm = {x["id"]: x["llm_faithful"] for x in items}

    gA = load_labels("labeler_A.csv") or {}
    gB = load_labels("labeler_B.csv") or {}
    print(f"items: {len(items)} | A: {len(gA)} | B: {len(gB)}")
    if len(gA) < args.min_items or len(gB) < args.min_items:
        print(f"WARNING: < {args.min_items} items judged by someone; kappa unstable.")

    lines = ["# Faithfulness pilot — human vs LLM judge", "",
             f"- items: {len(items)}",
             f"- labeler A judged: {len(gA)}",
             f"- labeler B judged: {len(gB)}", ""]

    common = sorted(set(gA) & set(gB))
    if len(common) >= 5:
        a = [gA[i] for i in common]
        b = [gB[i] for i in common]
        k = cohen_kappa(a, b)
        agree = sum(1 for x, y in zip(a, b) if x == y) / len(a)
        print(f"human-human: n={len(common)} kappa={k:.3f} exact={agree:.1%}")
        lines += ["## Human-human", f"- n = {len(common)}",
                  f"- Cohen's kappa: **{k:.3f}**", f"- exact: {agree:.1%}", ""]
    else:
        print("human-human: <5 overlapping items; skipping")

    disagree = []
    for name, g in (("A", gA), ("B", gB)):
        ids = sorted(g)
        if len(ids) < 5:
            continue
        h = [g[i] for i in ids]
        l = [llm[i] for i in ids]
        k = cohen_kappa(h, l)
        exact = sum(1 for x, y in zip(h, l) if x == y) / len(h)
        conf = Counter(("LLM" if x else "LLM-not") + "->" + ("H" if y else "H-not")
                       for x, y in zip(l, h))
        mism = [i for i in ids if g[i] != llm[i]]
        disagree += mism
        print(f"labeler {name} vs LLM: n={len(ids)} kappa={k:.3f} exact={exact:.1%} "
              f"confusion={dict(conf)}")
        lines += [f"## Labeler {name} vs LLM judge", f"- n = {len(ids)}",
                  f"- Cohen's kappa: **{k:.3f}**", f"- exact: {exact:.1%}",
                  f"- confusion: {dict(conf)}", ""]

    if disagree:
        ids = sorted(set(disagree))
        print(f"\n{len(ids)} items where a human disagreed with the LLM judge: "
              f"{ids[:20]}{' ...' if len(ids) > 20 else ''}")
        lines += ["## Disagreement item ids",
                  ", ".join(ids[:40]) if len(ids) <= 40 else
                  ", ".join(ids[:40]) + " ...", ""]

    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("wrote", OUT / "report.md")


if __name__ == "__main__":
    main()
