#!/usr/bin/env python3
"""
grounded_enrichment.py — Can a label-free *quality* signal find the headroom
that selective_enrichment.py proved exists?

selective_enrichment.py established two things. An oracle that ranks records by
their measured gain recovers ~104% of the full-enrichment benefit at half the
cataloging cost -- so some LLM enrichments actively hurt, and a good triage rule
would beat enriching everything. And neither of the two record-poverty
heuristics found that rule (best +0.042, p=0.063).

Those heuristics scored the *record*. This scores the *prediction*, on the
theory that the enrichments which hurt are the ones the book does not support.

  groundedness(record) = IDF-weighted fraction of the predicted headings'
  content vocabulary that actually occurs in that book's own full text.

It is label-free (no questions, no gold headings, no retrieval scores) and it
is the cataloging analogue of the citation-verification check the paper already
applies to generated answers.

Two policies are measured, because they are different interventions:

  triage   per *record*: spend a budget of b% of the cataloging calls on the
           best-grounded records. Comparable to selective_enrichment.py.
  filter   per *heading*: catalog everything, but drop individual headings
           below a groundedness threshold before indexing. No budget saved;
           the question is whether withholding bad headings beats indexing
           them.

`ungrounded` (triage in reverse) is run as a direction check: if groundedness
carries signal, inverting it must hurt.

NOTE ON A REJECTED DESIGN: the pre-registered plan was to filter on LC
authority validity. Measured on this corpus it cannot work -- the cached
authority verdicts cover 81 of 227 records, and 80 of those 81 are 100% valid.
A signal that is constant across 99% of records has no discriminative power,
whatever its face validity. Groundedness replaces it because it is continuous
and computable for every record.

Outputs:
  phase2/reports/grounded_enrichment.json + .md

Usage:
  python3 phase2/scripts/grounded_enrichment.py
"""

import argparse
import json
import logging
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import exp_common as ec  # noqa: E402

logger = logging.getLogger(__name__)
STOP = {"the", "of", "and", "in", "a", "to", "for", "on", "with", "as", "by",
        "from", "at", "or", "an", "is", "be", "it", "its", "this", "that"}


def toks(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOP and len(t) > 2]


def book_vocab(rec: Dict) -> set:
    """Every content token in the book's own full text."""
    v = set()
    for c in rec.get("chunks", []):
        v.update(toks(c.get("text", "")))
    return v


def idf_over_books(vocabs: Dict[str, set]) -> Dict[str, float]:
    df = Counter()
    for v in vocabs.values():
        df.update(v)
    n = len(vocabs)
    return {t: math.log(n / (1 + d)) + 1.0 for t, d in df.items()}


def heading_groundedness(heading: str, vocab: set, idf: Dict[str, float]) -> float:
    """IDF-weighted share of a heading's tokens present in the book text.
    Weighting by IDF stops common words from making every heading look grounded."""
    t = toks(heading)
    if not t:
        return 0.0
    total = sum(idf.get(x, 1.0) for x in t)
    hit = sum(idf.get(x, 1.0) for x in t if x in vocab)
    return hit / total if total else 0.0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--chunk-index", default=str(ROOT / "data" / "index_scaled"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--preds", nargs="+", default=[
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions.jsonl"),
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions_corpus.jsonl")])
    ap.add_argument("--budgets", default="0.1,0.25,0.5,0.75")
    ap.add_argument("--thresholds", default="0.25,0.5,0.75")
    ap.add_argument("--random-seeds", default="1,2,3,4,5")
    ap.add_argument("--fields", default="title+subj")
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    logger.info("reading corpus with chunks (needed for groundedness)")
    full = ec.read_jsonl(args.corpus)
    vocabs = {r["work_key"]: book_vocab(r) for r in full}
    idf = idf_over_books(vocabs)
    records = [{k: v for k, v in r.items() if k != "chunks"} for r in full]
    del full

    preds = ec.load_predictions([Path(p) for p in args.preds])
    keys = {r["work_key"] for r in records}
    matched = sum(1 for k in keys if k in preds)
    if not matched:
        raise SystemExit("no corpus record has an LLM prediction; run refused")
    pool = ec.question_pool(args.qa, keys)
    qtype = {q["qid"]: q["type"] for q in pool}

    # groundedness per heading and per record
    per_heading: Dict[str, List[float]] = {}
    for wk in keys:
        p = preds.get(wk)
        if not p:
            continue
        per_heading[wk] = [heading_groundedness(h, vocabs.get(wk, set()), idf)
                           for h in (p.get("pred_subjects") or [])]
    rec_score = {wk: (sum(v) / len(v) if v else 0.0) for wk, v in per_heading.items()}
    enrichable = sorted(per_heading)
    allg = [g for v in per_heading.values() for g in v]
    logger.info("%d records, %d enrichable, %d predicted headings; "
                "groundedness mean=%.3f median=%.3f", len(records), len(enrichable),
                len(allg), sum(allg) / len(allg), sorted(allg)[len(allg) // 2])

    stripped = [ec.strip_meta(r) for r in records]
    cache_path = ROOT / "reports" / f"grounded_per_question{args.tag}.json"
    per_q = ec.cache(cache_path)

    def score(label: str, recs: List[Dict]) -> Dict[str, float]:
        if label in per_q:
            return per_q[label]
        idx = ec.build_index(recs, f"ge_{label}{args.tag}", Path(args.chunk_index),
                             fields=args.fields)
        per_q[label] = ec.score_pool(idx, pool)
        ec.save_cache(per_q, cache_path)
        logger.info("%-24s topical=%.3f", label,
                    ec.mean(ec.by_type(per_q[label], qtype, "topical")))
        return per_q[label]

    def enrich_subset(chosen: Sequence[str], thresh: float = -1.0) -> List[Dict]:
        """Enrich `chosen` records; with thresh >= 0, keep only headings whose
        groundedness clears it."""
        sel = set(chosen)
        out = []
        for r in stripped:
            wk = r["work_key"]
            if wk not in sel or wk not in preds:
                out.append(r)
                continue
            hs = preds[wk].get("pred_subjects") or []
            gs = per_heading[wk]
            kept = [h for h, g in zip(hs, gs) if g >= thresh] if thresh >= 0 else list(hs)
            r2 = dict(r)
            r2["subjects"] = kept
            out.append(r2)
        return out

    base = score("base", stripped)
    full_enr = score("full", enrich_subset(enrichable))
    t0 = ec.mean(ec.by_type(base, qtype, "topical"))
    t1 = ec.mean(ec.by_type(full_enr, qtype, "topical"))
    span = t1 - t0

    budgets = [float(b) for b in args.budgets.split(",")]
    seeds = [int(s) for s in args.random_seeds.split(",")]
    thresholds = [float(t) for t in args.thresholds.split(",")]

    # oracle, recomputed here so this script stands alone
    gains: Dict[str, List[float]] = defaultdict(list)
    for q in pool:
        if q["type"] == "topical" and q["qid"] in full_enr:
            gains[q["work_key"]].append(full_enr[q["qid"]] - base[q["qid"]])
    oracle = {wk: ec.mean(gains.get(wk, [0.0])) for wk in enrichable}

    policies = {"grounded": rec_score,
                "ungrounded": {k: -v for k, v in rec_score.items()},
                "oracle": oracle}
    curves: Dict[str, Dict[str, float]] = {}
    for name, sc in policies.items():
        order = sorted(enrichable, key=lambda wk: (-sc[wk], wk))
        curves[name] = {f"{b:.2f}": ec.mean(ec.by_type(
            score(f"{name}_{b:.2f}", enrich_subset(order[:int(round(b * len(enrichable)))])),
            qtype, "topical")) for b in budgets}
    curves["random"] = {}
    for b in budgets:
        k = int(round(b * len(enrichable)))
        curves["random"][f"{b:.2f}"] = ec.mean([ec.mean(ec.by_type(
            score(f"random{sd}_{b:.2f}",
                  enrich_subset(random.Random(sd).sample(enrichable, k))), qtype, "topical"))
            for sd in seeds])

    # per-heading filtering at full budget
    filt = {}
    for th in thresholds:
        s = score(f"filter{th:.2f}", enrich_subset(enrichable, thresh=th))
        kept = sum(1 for wk in enrichable for g in per_heading[wk] if g >= th)
        filt[f"{th:.2f}"] = {"topical": ec.mean(ec.by_type(s, qtype, "topical")),
                             "headings_kept": kept, "headings_total": len(allg)}

    out = {"n_records": len(records), "n_enrichable": len(enrichable),
           "n_questions": len(pool), "n_headings": len(allg),
           "topical_base": round(t0, 4), "topical_full": round(t1, 4),
           "full_gain": round(span, 4), "budgets": budgets, "thresholds": thresholds,
           "curves": {}, "filter": {}, "significance": {}}
    for name, c in curves.items():
        out["curves"][name] = {b: {"topical": round(v, 4),
                                   "frac_of_full_gain": (round((v - t0) / span, 3)
                                                         if span else None)}
                               for b, v in c.items()}
    for th, v in filt.items():
        a, b_ = ec.paired(per_q[f"filter{float(th):.2f}"], per_q["full"], qtype, "topical")
        d = [x - y for x, y in zip(a, b_)]
        lo, hi = ec.bootstrap_ci(d, args.bootstrap)
        out["filter"][th] = {**{k: (round(x, 4) if isinstance(x, float) else x)
                                for k, x in v.items()},
                             "delta_vs_unfiltered": round(ec.mean(d), 4),
                             "ci95": [round(lo, 4), round(hi, 4)],
                             "p": round(ec.perm_p(a, b_, args.iters), 5)}
    for name in ("grounded", "ungrounded"):
        out["significance"][name] = {}
        for b in budgets:
            tag = f"{b:.2f}"
            a, r = ec.paired(per_q[f"{name}_{tag}"], per_q[f"random{seeds[0]}_{tag}"],
                             qtype, "topical")
            d = [x - y for x, y in zip(a, r)]
            lo, hi = ec.bootstrap_ci(d, args.bootstrap)
            out["significance"][name][tag] = {"delta": round(ec.mean(d), 4),
                                              "ci95": [round(lo, 4), round(hi, 4)],
                                              "p": round(ec.perm_p(a, r, args.iters), 5)}

    (ROOT / "reports" / f"grounded_enrichment{args.tag}.json").write_text(json.dumps(out, indent=2))

    md = ["# Grounded enrichment: does prediction quality find the headroom?", "",
          f"- {len(records)} records, {len(enrichable)} enrichable, {len(allg)} predicted "
          f"headings, {len(pool)} questions",
          f"- Stripped catalog topical {t0:.3f}; enrich-all {t1:.3f} (gain {span:+.3f})",
          "- Groundedness = IDF-weighted share of a heading's tokens found in the "
          "book's own full text (label-free)", "",
          "## Per-record triage (budget = share of cataloging calls spent)", "",
          "| Policy | " + " | ".join(f"{100*b:.0f}%" for b in budgets) + " |",
          "|---" * (len(budgets) + 1) + "|"]
    for name in ("random", "grounded", "ungrounded", "oracle"):
        md.append(f"| {name} | " + " | ".join(
            f"{out['curves'][name][f'{b:.2f}']['topical']:.3f} "
            f"({out['curves'][name][f'{b:.2f}']['frac_of_full_gain']:.0%})"
            for b in budgets) + " |")
    md += ["", "| Policy | budget | delta vs random | 95% CI | p |", "|---|---|---|---|---|"]
    for name, rows in out["significance"].items():
        for b, v in rows.items():
            md.append(f"| {name} | {float(b):.0%} | {v['delta']:+.4f} | "
                      f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {v['p']:.4f} |")
    md += ["", "## Per-heading filtering (full budget; drop headings below threshold)", "",
           "| Threshold | headings kept | topical | delta vs unfiltered | 95% CI | p |",
           "|---|---|---|---|---|---|"]
    for th, v in out["filter"].items():
        md.append(f"| {float(th):.2f} | {v['headings_kept']}/{v['headings_total']} | "
                  f"{v['topical']:.3f} | {v['delta_vs_unfiltered']:+.4f} | "
                  f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {v['p']:.4f} |")
    (ROOT / "reports" / f"grounded_enrichment{args.tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
