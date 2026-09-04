#!/usr/bin/env python3
"""
sensitivity_sweep.py — Sensitivity of the shipped retrieval numbers to the
two tuned design constants that the AIDL reviewer flagged as unjustified:

  (i)  the subject-field boost (token repetition ×w in record field text,
       shipped value w=2), and
  (ii) the RRF fusion constant k (shipped value k=60).

Everything is reproduced exactly as the shipped meta configuration:
record field text = title (x1) + each subject x w + authors (x1); fields
title+subj only (DDC excluded, matching the shipped index_scaled_ts);
dense record embeddings over that same repeated text with all-MiniLM-L6-v2
(mean pooling); BM25Okapi over tokenized record text; meta = RRF over the
dense-record ranking and the BM25-record ranking, top-10 records, nDCG@10
against the single gold work_key. Query embeddings are computed once.

Validation: w=2, k=60 must reproduce the shipped full-pool numbers
(topical 0.691, overall 0.851, known 0.897, bib 0.948 on the n=1076 pool).

Outputs:
  phase2/reports/sensitivity_sweep.json  (+ .md)

Usage:
  HF_HOME="$PWD/../.hf_cache" python3 phase2/scripts/sensitivity_sweep.py
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from embeddings import embed  # noqa: E402

WEIGHTS = (1, 2, 4, 8)     # subject token repetition multiplier
K_VALUES = (30, 60, 100, 200)  # RRF constant
TYPES = ("known_item", "topical", "bib_fact")
SHIPPED = {"topical": 0.691, "overall": 0.851, "known_item": 0.897, "bib_fact": 0.948}


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def rrf(rankings, k):
    scores = {}
    for ranking in rankings:
        for rank, i in enumerate(ranking):
            scores[i] = scores.get(i, 0.0) + 1.0 / (k + rank + 1)
    return scores


def record_field_text(rec, w):
    """Same text as index.record_field_text(fields='title+subj') with subject
    boost w (shipped default boost: title x int(1.5)=1, subjects x2, authors
    always present once)."""
    parts = []
    t = rec.get("title") or ""
    if t:
        parts.append(t)
    for s in (rec.get("subjects") or []):
        parts += [s] * w
    parts += [" ".join(rec.get("authors") or [])]
    return " ".join(parts)


def ndcg_at_10(ranked, gold):
    g = gold
    dcg = 0.0
    for i, rid in enumerate(ranked[:10]):
        if rid == g:
            dcg += 1.0 / math.log2(i + 2)
    return dcg  # single gold => idcg = 1


def bootstrap_ci(values, n=10000, seed=7):
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(n, len(arr)))
    means = arr[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_drafts_scaled_polished.jsonl"))
    args = ap.parse_args()

    corpus = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    qa = [json.loads(l) for l in open(args.qa, encoding="utf-8") if l.strip()]
    keys = {r["work_key"] for r in corpus}
    pool = [q for q in qa if q.get("work_key") in keys]
    print(f"corpus={len(corpus)} qa={len(qa)} in-corpus pool={len(pool)}")
    assert len(pool) == 1076, f"expected the n=1076 full pool, got {len(pool)}"

    questions = [q["question_polished"] for q in pool]
    print("embedding %d queries once ..." % len(questions), flush=True)
    qemb = embed(questions)
    qemb = qemb / np.linalg.norm(qemb, axis=1, keepdims=True)

    rec_ids = [r["work_key"] for r in corpus]
    type_of = {q["qid"]: q["type"] for q in pool}

    results = {}   # f"w{w}k{k}" -> {"topical": [..], "known_item": [..], "bib_fact": [..], "overall": [..]}
    per_w = {}     # w -> (record tokens, bm25, record emb normalized)

    for w in WEIGHTS:
        texts = [record_field_text(r, w) for r in corpus]
        toks = [tokenize(t) for t in texts]
        print(f"embedding record texts w={w} ...", flush=True)
        remb = embed(texts)
        remb = remb / np.linalg.norm(remb, axis=1, keepdims=True)
        bm25 = BM25Okapi(toks)
        per_w[w] = (toks, bm25, remb)

        # dense ranking and BM25 ranking for every query, then RRF at each k
        q_toks = [tokenize(q) for q in questions]
        for k in K_VALUES:
            label = f"w{w}k{k}"
            scores = {t: [] for t in TYPES}
            overall = []
            for qi in range(len(pool)):
                dense_order = np.argsort(-(remb @ qemb[qi]))[:50]
                dense_rank = [rec_ids[i] for i in dense_order]
                bm25_rank = bm25.get_top_n(q_toks[qi], rec_ids, n=50)
                fused = rrf([dense_rank, bm25_rank], k)
                top10 = [i for i, _ in sorted(fused.items(), key=lambda x: -x[1])[:10]]
                nd = ndcg_at_10(top10, pool[qi]["work_key"])
                scores[type_of[pool[qi]["qid"]]].append(nd)
                overall.append(nd)
            results[label] = {
                "topical": float(np.mean(scores["topical"])),
                "known_item": float(np.mean(scores["known_item"])),
                "bib_fact": float(np.mean(scores["bib_fact"])),
                "overall": float(np.mean(overall)),
                "topical_ci95": list(bootstrap_ci(scores["topical"])),
                "n_topical": len(scores["topical"]),
            }
            m = results[label]
            print(f"{label}: topical={m['topical']:.3f} known={m['known_item']:.3f} "
                  f"bib={m['bib_fact']:.3f} overall={m['overall']:.3f}", flush=True)

    shipped = results["w2k60"]
    for t, v in SHIPPED.items():
        got = shipped[t]
        assert abs(got - v) < 0.002, \
            f"validation failed: w2k60 {t}={got:.4f}, shipped {v}"

    # markdown report
    lines = ["# Sensitivity sweep: subject boost ×w and RRF k",
             "",
             f"- Pool: all {len(pool)} in-corpus questions · same record index "
             "construction as shipped (title+subj, DDC excluded)",
             f"- Validation: w=2, k=60 reproduces shipped topical "
             f"{shipped['topical']:.3f} / overall {shipped['overall']:.3f}",
             "",
             "| config | topical | overall | known_item | bib_fact |",
             "|---|---|---|---|---|"]
    for label in sorted(results):
        m = results[label]
        lines.append(f"| {label} | {m['topical']:.3f} | {m['overall']:.3f} | "
                     f"{m['known_item']:.3f} | {m['bib_fact']:.3f} |")
    lines += ["", "Subject boost rows (k=60 fixed):", ""]
    for w in WEIGHTS:
        m = results[f"w{w}k60"]
        lines.append(f"- ×{w}: topical {m['topical']:.3f} "
                     f"({m['topical_ci95'][0]:.3f}–{m['topical_ci95'][1]:.3f}) "
                     f"vs shipped ×2 {results['w2k60']['topical']:.3f}")
    lines += ["", "RRF k rows (×2 fixed):", ""]
    for k in K_VALUES:
        m = results[f"w2k{k}"]
        lines.append(f"- k={k}: topical {m['topical']:.3f} overall {m['overall']:.3f}")

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "sensitivity_sweep.json").write_text(
        json.dumps({"pool_n": len(pool), "results": results}, indent=1) + "\n")
    (out / "sensitivity_sweep.md").write_text("\n".join(lines) + "\n")
    print("wrote", out / "sensitivity_sweep.json")


if __name__ == "__main__":
    main()
