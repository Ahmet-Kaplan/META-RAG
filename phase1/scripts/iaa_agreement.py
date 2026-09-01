#!/usr/bin/env python3
"""
iaa_agreement.py — Inter-annotator agreement for LIBRA-QA review and the
cataloger panel. Computes Cohen's kappa (2 annotators) and Fleiss' kappa
(any number of annotators).

Input: JSONL with {"id": ..., "annotator": "A", "label": "keep|edit|reject"} or
       {"id": ..., "annotator": "C1", "label": "accept|accept-variant|..."}.

Usage:
  python3 iaa_agreement.py --labels labels.jsonl
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cohen_kappa(a, b, labels):
    """Cohen's kappa for two annotators' label sequences."""
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


def fleiss_kappa(items):
    """items: dict id -> list of labels (one per annotator)."""
    n_subjects = len(items)
    n_raters = len(next(iter(items.values())))
    labels = sorted({l for labels in items.values() for l in labels})
    if n_subjects == 0 or n_raters < 2:
        return float("nan")
    # P_j per subject
    P = []
    for labels_i in items.values():
        cnt = defaultdict(int)
        for l in labels_i:
            cnt[l] += 1
        P.append((sum(c * c for c in cnt.values()) - n_raters) / (n_raters * (n_raters - 1)))
    P_bar = sum(P) / n_subjects
    # P_e
    P_e = 0.0
    for lab in labels:
        c = sum(1 for labels_i in items.values() for l in labels_i if l == lab)
        p = c / (n_subjects * n_raters)
        P_e += p * p
    return (P_bar - P_e) / (1 - P_e) if P_e < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.labels, encoding="utf-8") if l.strip()]
    by_id = defaultdict(dict)
    for r in rows:
        by_id[r["id"]][r["annotator"]] = r["label"]
    annotators = sorted({a for d in by_id.values() for a in d})
    print(f"Subjects: {len(by_id)} · Annotators: {annotators}")

    if len(annotators) == 2:
        a0, a1 = annotators
        seq_a = [d[a0] for d in by_id.values() if a0 in d and a1 in d]
        seq_b = [d[a1] for d in by_id.values() if a0 in d and a1 in d]
        n = len(seq_a)
        labels = sorted(set(seq_a) | set(seq_b))
        k = cohen_kappa(seq_a, seq_b, labels)
        agree = sum(1 for x, y in zip(seq_a, seq_b) if x == y) / n if n else float("nan")
        print(f"Paired subjects: {n} · Agreement: {agree:.2%} · Cohen's kappa: {k:.3f}")
        verdict = "substantial" if k >= 0.7 else ("moderate" if k >= 0.4 else "poor")
        print(f"Verdict: {verdict} (target >= 0.7; if < 0.6 revise rubric/rules and re-run)")
    else:
        k = fleiss_kappa(by_id)
        print(f"Fleiss' kappa ({len(annotators)} annotators): {k:.3f}")


if __name__ == "__main__":
    main()
