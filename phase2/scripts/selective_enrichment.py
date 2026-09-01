#!/usr/bin/env python3
"""
selective_enrichment.py — Is LLM cataloging worth spending on every record?

sparsity_sweep.py enriches every record that lacks a heading. That is the
maximum-cost policy: one LLM cataloging call per uncatalogued record. A library
with 2 million uncatalogued works cannot run it, and does not have to if the
benefit is concentrated in a minority of records.

This measures the cost-effectiveness curve. Starting from a fully stripped
catalog (no subject access anywhere), a policy picks which b% of the enrichable
records to catalog, and topical nDCG@10 is measured for each budget b.

Policies (the two heuristics are declared here in advance; both are reported
whatever they turn out to do, and either may fail to beat random):

  random        uniform sample, averaged over --random-seeds seeds -- the
                honest baseline any triage rule has to beat
  title_poverty enrich the records whose existing text is least informative,
                scored by the IDF mass of their title tokens (ascending).
                Hypothesis: a record already carrying a distinctive title has
                little left to gain from a subject heading.
  novel_idf     enrich where the predicted headings add the most vocabulary the
                record does not already have: IDF mass of prediction tokens
                minus tokens already in the title/authors (descending).
  oracle        rank by each record's *measured* gain under full enrichment.
                Not a usable policy -- it is the upper bound that says how much
                headroom any triage rule could have.

Both heuristics are label-free: they read the record and the candidate
headings, never the questions or the retrieval scores.

Outputs:
  phase2/reports/selective_enrichment.json + .md

Usage:
  python3 phase2/scripts/selective_enrichment.py
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


def tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def idf_table(records: List[Dict]) -> Dict[str, float]:
    """IDF over the record collection's own title+author text -- the vocabulary
    a metadata-blind catalog search actually has to work with."""
    df = Counter()
    for r in records:
        df.update(set(tokens(r.get("title", "")) +
                      tokens(" ".join(r.get("authors") or []))))
    n = len(records)
    return {t: math.log(n / (1 + d)) + 1.0 for t, d in df.items()}


def existing_tokens(rec: Dict) -> set:
    return set(tokens(rec.get("title", "")) +
               tokens(" ".join(rec.get("authors") or [])))


def pred_tokens(pred: Dict) -> set:
    out = set()
    for s in (pred.get("pred_subjects") or []):
        out |= set(tokens(s))
    if pred.get("pred_ddc"):
        out |= set(tokens(str(pred["pred_ddc"])))
    return out


def heuristic_scores(records: List[Dict], preds: Dict[str, Dict],
                     enrichable: Sequence[str]) -> Dict[str, Dict[str, float]]:
    """work_key -> priority for each declared heuristic (higher = enrich first)."""
    idf = idf_table(records)
    by_key = {r["work_key"]: r for r in records}
    poverty, novel = {}, {}
    for wk in enrichable:
        rec, pred = by_key[wk], preds[wk]
        have = existing_tokens(rec)
        # low existing IDF mass -> high priority, hence the negation
        poverty[wk] = -sum(idf.get(t, 0.0) for t in have)
        novel[wk] = sum(idf.get(t, 0.0) for t in pred_tokens(pred) - have)
    return {"title_poverty": poverty, "novel_idf": novel}


def topical_mean(scores: Dict[str, float], qtype: Dict[str, str]) -> float:
    return ec.mean(ec.by_type(scores, qtype, "topical"))


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
    ap.add_argument("--random-seeds", default="1,2,3,4,5")
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--fields", default="title+subj",
                    help="record index fields; DDC is excluded by default "
                         "because it carries no measurable topical signal "
                         "(see reports/field_ablation.md)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    records = ec.slim_corpus(Path(args.corpus),
                             ROOT / "data" / f"slim{args.tag or '_scaled'}.jsonl")
    preds = ec.load_predictions([Path(p) for p in args.preds])
    keys = {r["work_key"] for r in records}
    pool = ec.question_pool(args.qa, keys)
    qtype = {q["qid"]: q["type"] for q in pool}

    fields = args.fields
    stripped = [ec.strip_meta(r) for r in records]
    enrichable = sorted(wk for wk in keys if wk in preds)
    budgets = [float(b) for b in args.budgets.split(",")]
    seeds = [int(s) for s in args.random_seeds.split(",")]
    logger.info("%d records, %d enrichable (have an LLM prediction), %d questions",
                len(records), len(enrichable), len(pool))

    cache_path = ROOT / "reports" / f"selective_per_question{args.tag}.json"
    per_q = ec.cache(cache_path)

    def run(label: str, chosen: Sequence[str]) -> Dict[str, float]:
        if label in per_q:
            return per_q[label]
        sel = set(chosen)
        recs = [ec.enrich(r, preds) if r["work_key"] in sel else r for r in stripped]
        idx = ec.build_index(recs, f"se_{label}{args.tag}", Path(args.chunk_index), fields=fields)
        per_q[label] = ec.score_pool(idx, pool)
        ec.save_cache(per_q, cache_path)
        logger.info("%-22s enriched=%-4d topical=%.3f", label, len(sel),
                    topical_mean(per_q[label], qtype))
        return per_q[label]

    base = run("base", [])
    full = run("full", enrichable)

    # oracle ranking: measured per-record topical gain under full enrichment
    gains: Dict[str, List[float]] = defaultdict(list)
    for q in pool:
        if q["type"] == "topical" and q["qid"] in full and q["qid"] in base:
            gains[q["work_key"]].append(full[q["qid"]] - base[q["qid"]])
    oracle_rank = {wk: ec.mean(gains.get(wk, [0.0])) for wk in enrichable}

    policies = heuristic_scores(records, preds, enrichable)
    policies["oracle"] = oracle_rank

    curves: Dict[str, Dict[str, float]] = {}
    for name, score in policies.items():
        ordered = sorted(enrichable, key=lambda wk: (-score[wk], wk))
        curves[name] = {}
        for b in budgets:
            k = int(round(b * len(enrichable)))
            curves[name][f"{b:.2f}"] = topical_mean(
                run(f"{name}_{b:.2f}", ordered[:k]), qtype)

    curves["random"] = {}
    random_detail: Dict[str, List[float]] = {}
    for b in budgets:
        k = int(round(b * len(enrichable)))
        vals = []
        for sd in seeds:
            chosen = random.Random(sd).sample(enrichable, k)
            vals.append(topical_mean(run(f"random{sd}_{b:.2f}", chosen), qtype))
        curves["random"][f"{b:.2f}"] = ec.mean(vals)
        random_detail[f"{b:.2f}"] = [round(v, 4) for v in vals]

    t0, t1 = topical_mean(base, qtype), topical_mean(full, qtype)
    span = t1 - t0

    out = {"n_records": len(records), "n_enrichable": len(enrichable),
           "n_questions": len(pool), "budgets": budgets, "random_seeds": seeds,
           "topical_base": round(t0, 4), "topical_full": round(t1, 4),
           "full_gain": round(span, 4), "curves": {}, "random_per_seed": random_detail,
           "significance_vs_random": {}}
    for name, c in curves.items():
        out["curves"][name] = {b: {"topical": round(v, 4),
                                   "gain": round(v - t0, 4),
                                   "frac_of_full_gain": (round((v - t0) / span, 3)
                                                         if span else None),
                                   "n_llm_calls": int(round(float(b) * len(enrichable)))}
                               for b, v in c.items()}

    # each heuristic vs. the first random seed at the same budget, paired on
    # the topical questions -- the comparison the policy claim rests on
    for name in ("title_poverty", "novel_idf"):
        out["significance_vs_random"][name] = {}
        for b in budgets:
            tag = f"{b:.2f}"
            a, r = ec.paired(per_q[f"{name}_{tag}"], per_q[f"random{seeds[0]}_{tag}"],
                             qtype, "topical")
            diffs = [x - y for x, y in zip(a, r)]
            lo, hi = ec.bootstrap_ci(diffs, args.bootstrap)
            out["significance_vs_random"][name][tag] = {
                "delta": round(ec.mean(diffs), 4), "ci95": [round(lo, 4), round(hi, 4)],
                "p": round(ec.perm_p(a, r, args.iters), 5), "n": len(diffs)}

    (ROOT / "reports" / f"selective_enrichment{args.tag}.json").write_text(json.dumps(out, indent=2))

    md = ["# Selective enrichment: does triage beat cataloging everything?", "",
          f"- {len(records)} records, {len(enrichable)} enrichable, full in-corpus "
          f"pool ({len(pool)} questions)",
          f"- Catalog fully stripped first; topical nDCG@10 at {t0:.3f}, "
          f"{t1:.3f} when every enrichable record is catalogued (gain {span:+.3f})",
          f"- `random` averaged over seeds {', '.join(map(str, seeds))}; "
          f"`oracle` ranks by measured gain and is an upper bound, not a policy", "",
          "| Policy | " + " | ".join(f"{100*b:.0f}% ({int(round(b*len(enrichable)))} calls)"
                                     for b in budgets) + " |",
          "|---" * (len(budgets) + 1) + "|"]
    for name in ("random", "title_poverty", "novel_idf", "oracle"):
        cells = " | ".join(
            f"{out['curves'][name][f'{b:.2f}']['topical']:.3f} "
            f"({out['curves'][name][f'{b:.2f}']['frac_of_full_gain']:.0%} of full gain)"
            if out['curves'][name][f'{b:.2f}']['frac_of_full_gain'] is not None else "--"
            for b in budgets)
        md.append(f"| {name} | {cells} |")
    md += ["", "## Heuristic vs. random at equal budget (paired, topical questions)", "",
           "| Policy | budget | delta | 95% CI | p |", "|---|---|---|---|---|"]
    for name, rows in out["significance_vs_random"].items():
        for b, v in rows.items():
            md.append(f"| {name} | {float(b):.0%} | {v['delta']:+.4f} | "
                      f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {v['p']:.4f} |")
    (ROOT / "reports" / f"selective_enrichment{args.tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
