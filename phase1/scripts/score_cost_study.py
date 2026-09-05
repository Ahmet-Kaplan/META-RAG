#!/usr/bin/env python3
"""
score_cost_study.py — Analyze the E4 cost-study results.

E4 (DSS paper, RQ4) measures what LLM metadata enrichment COSTS in cataloger
time and editing effort versus cataloging from scratch. Input is one results
CSV per cataloger (exported from the instrument HTML or the workbook
fallback): columns id, condition, title, author, year, llm_subjects, llm_ddc,
time_s, final_subjects, final_ddc.

Reports, per cataloger and pooled:
  1. Time: mean seconds/record in M vs V (paired where the same cataloger did
     both; the two halves are disjoint records, so this is an independent
     comparison, not paired-by-record — paired by cataloger via per-cataloger
     means).
  2. Edits (V only): how much the cataloger changed the draft — fraction of
     records with >=1 edit, mean changed headings, draft-kept-as-is rate.
  3. Quality parity: final headings scored against gold with the LIBRA-CAT
     multi-level rubric (exact / semantic / acceptable), M vs V, so we can say
     whether verifying costs less time at equal quality.
  4. Draft quality as a floor: the unedited draft's score vs the cataloger's
     final score in V (does editing improve on the draft?).

Usage:
  python3 phase1/scripts/score_cost_study.py [--data phase1/data/panel/e4]
  (place each cataloger's exported CSV in the data dir as
   cataloger_<X>_results.csv before running)
"""

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "phase2" / "scripts"))
from score_libra_cat import norm, main_heading  # noqa: E402  (pure string fns)

try:
    from embeddings import embed  # noqa: E402
    import numpy as np
    HAVE_EMB = True
except Exception:
    HAVE_EMB = False


def semantic_matcher(texts):
    """Cosine matcher over normalized headings (MiniLM), like score_libra_cat."""
    if not HAVE_EMB:
        return None
    uniq = sorted({t for t in texts if t})
    mat = embed(list(uniq))
    mat = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    idx = {t: i for i, t in enumerate(uniq)}
    def sim(a, b):
        if a not in idx or b not in idx:
            return 0.0
        return float(mat[idx[a]] @ mat[idx[b]])
    return sim


def best_level(preds, golds, sim):
    """Best LIBRA-CAT level at which the gold headings are covered by preds."""
    levels = []
    for g in golds:
        gn = norm(g)
        if any(norm(p) == gn for p in preds):
            levels.append("exact")
        elif sim is not None and any(sim(norm(p), gn) >= 0.75 for p in preds):
            levels.append("semantic")
        elif main_heading(g) and any(main_heading(p) == main_heading(g)
                                     for p in preds):
            levels.append("acceptable")
        else:
            levels.append("miss")
    # summary per record: share of gold headings covered at each level
    n = len(levels)
    return {lv: levels.count(lv) / n for lv in ("exact", "semantic",
                                                "acceptable", "miss")}


def parse_headings(text):
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "panel" / "e4"))
    args = ap.parse_args()
    data_dir = Path(args.data)

    master = {}   # id -> gold
    for f in sorted(data_dir.glob("cataloger_*_items.jsonl")):
        for l in f.read_text().splitlines():
            if l.strip():
                it = json.loads(l)
                master[it["id"]] = it

    results = []
    for f in sorted(data_dir.glob("cataloger_*_results.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["id"] not in master:
                    continue
                results.append({**row, "cataloger": f.name.split("_")[1]})
    if not results:
        raise SystemExit(f"no cataloger_*_results.csv found in {data_dir}")

    sim = semantic_matcher([g for it in master.values() for g in it.get("gold_subjects", [])])
    print(f"{len(results)} scored records across "
          f"{len({r['cataloger'] for r in results})} cataloger(s)")

    # per-cataloger time in M vs V
    per_cat = defaultdict(lambda: {"M": [], "V": []})
    for r in results:
        try:
            t = float(r.get("time_s") or 0)
        except ValueError:
            t = 0.0
        per_cat[r["cataloger"]][r["condition"]].append(t)

    print("\n=== Time per record (seconds) ===")
    m_all, v_all = [], []
    for cat in sorted(per_cat):
        m = per_cat[cat]["M"]; v = per_cat[cat]["V"]
        m_all += m; v_all += v
        if m and v:
            print(f"cataloger {cat}: M mean={statistics.mean(m):.0f}s "
                  f"(n={len(m)})  V mean={statistics.mean(v):.0f}s (n={len(v)})  "
                  f"saving={100*(1-statistics.mean(v)/statistics.mean(m)):.0f}%")
    if m_all and v_all:
        print(f"POOLED: M mean={statistics.mean(m_all):.0f}s (n={len(m_all)})  "
              f"V mean={statistics.mean(v_all):.0f}s (n={len(v_all)})  "
              f"saving={100*(1-statistics.mean(v_all)/statistics.mean(m_all)):.0f}%")

    # edits in V
    print("\n=== Edits in verify (V) condition ===")
    n_edited = n_v = 0
    for r in results:
        if r["condition"] != "V":
            continue
        n_v += 1
        draft = parse_headings(r.get("llm_subjects"))
        final = parse_headings(r.get("final_subjects"))
        if set(final) != set(draft):
            n_edited += 1
    if n_v:
        print(f"{n_edited}/{n_v} ({n_edited/n_v:.0%}) V records differ from the draft")

    # quality parity M vs V against gold
    print("\n=== Final quality vs gold (share of gold headings covered) ===")
    agg = defaultdict(lambda: defaultdict(list))
    for r in results:
        golds = master[r["id"]]["gold_subjects"]
        preds = parse_headings(r.get("final_subjects"))
        if not golds or not preds:
            continue
        lv = best_level(preds, golds, sim)
        agg[r["condition"]]["exact"].append(lv["exact"])
        agg[r["condition"]]["any"].append(lv["exact"] + lv["semantic"] +
                                          lv["acceptable"])
    for cond in ("M", "V"):
        d = agg.get(cond)
        if d and d["exact"]:
            print(f"{cond}: exact={statistics.mean(d['exact']):.1%}  "
                  f"any-level={statistics.mean(d['any']):.1%}  (n={len(d['exact'])})")

    # draft as floor (V): draft score vs cataloger final score
    print("\n=== Draft vs cataloger-final in V (does editing improve?) ===")
    d_ex, f_ex = [], []
    for r in results:
        if r["condition"] != "V":
            continue
        golds = master[r["id"]]["gold_subjects"]
        draft = parse_headings(r.get("llm_subjects"))
        final = parse_headings(r.get("final_subjects"))
        if not golds or not (draft or final):
            continue
        if draft:
            dl = best_level(draft, golds, sim)
            d_ex.append(dl["exact"] + dl["semantic"] + dl["acceptable"])
        if final:
            fl = best_level(final, golds, sim)
            f_ex.append(fl["exact"] + fl["semantic"] + fl["acceptable"])
    if d_ex and f_ex:
        print(f"draft any-level={statistics.mean(d_ex):.1%}  "
              f"cataloger-final any-level={statistics.mean(f_ex):.1%}  "
              f"(n={len(f_ex)})")

    print("\nNOTE: time comparisons are per-cataloger means (M/V on disjoint "
          "records); report per-cataloger variance, not just pooled means.")


if __name__ == "__main__":
    main()
