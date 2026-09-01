#!/usr/bin/env python3
"""
gain_law.py — From a sparsity curve to a transferable decision rule.

sparsity_sweep.py measures how the benefit of LLM cataloging shrinks as a
catalog gets more complete, on one collection. A curve on one collection is a
description. The decision-relevant question is whether the relationship holds
on a catalog it was not fitted to, because that is what lets a library estimate
its own expected gain from its own completeness statistic instead of running
the experiment.

Design:
  fit collection      the 227-book collection the paper reports
  held-out collection the 1,011 books in the 1,300-book build that are NOT in
                      the 227 -- disjoint records and disjoint questions

The regressor is the baseline catalog's actual subject-access completeness
(records carrying a heading / records), not the masking fraction: masking never
touches records that had no gold heading to begin with, so at mask=1.0 the 227
collection is still only 156/227 = 69% complete, and a curve plotted against
the mask fraction cannot be read as a statement about real catalogs.

Reachability r (the share of headingless records for which an LLM prediction
exists) differs between the collections and is carried as a covariate.

Models, all fitted on the fit collection only and scored out-of-sample:
  M1  gain = g0 (1 - x)          enrichment only touches uncovered records
  M2  gain = a + b x             unconstrained linear
  M3  gain = g0 (1 - x) r        M1 corrected for reachability  [the "law"]
  M4  gain = g0 exp(-k x)        diminishing returns

Outputs:
  phase2/reports/gain_law.json + .md

Usage:
  python3 phase2/scripts/gain_law.py
"""

import argparse
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import exp_common as ec  # noqa: E402

logger = logging.getLogger(__name__)


def sweep(name: str, records: List[Dict], preds: Dict[str, Dict],
          pool: List[Dict], qtype: Dict[str, str], chunk_index: Path,
          levels: Sequence[float], seed: int, per_q: Dict, cache_path: Path,
          fields: str) -> List[Dict]:
    """Baseline/enriched topical nDCG at each masking level, plus the catalog
    statistics (completeness, reachability) that the models regress on."""
    with_gold = sorted(r["work_key"] for r in records if r.get("subjects"))
    rows = []
    for c in levels:
        rng = random.Random(seed)                    # same mask for both arms
        keep = set(rng.sample(with_gold, int(round(c * len(with_gold)))))
        masked = [r if r["work_key"] in keep else ec.strip_meta(r) for r in records]
        arms = {}
        for arm, recs in (("base", masked),
                          ("enr", [ec.enrich(r, preds) for r in masked])):
            label = f"{name}_{arm}{c:.3f}"
            if label not in per_q:
                idx = ec.build_index(recs, f"gl_{label}", chunk_index, fields=fields)
                per_q[label] = ec.score_pool(idx, pool)
                ec.save_cache(per_q, cache_path)
            arms[arm] = per_q[label]
        n_cov = len(keep)
        headingless = [r for r in masked if not r.get("subjects")]
        reach = (sum(1 for r in headingless if r["work_key"] in preds) /
                 len(headingless)) if headingless else 0.0
        b = ec.mean(ec.by_type(arms["base"], qtype, "topical"))
        e = ec.mean(ec.by_type(arms["enr"], qtype, "topical"))
        rows.append({"mask": c, "completeness": n_cov / len(records),
                     "reachability": reach, "n_covered": n_cov,
                     "base": round(b, 4), "enriched": round(e, 4),
                     "gain": round(e - b, 4)})
        logger.info("%-8s mask=%.3f completeness=%.3f reach=%.2f  base=%.3f enr=%.3f gain=%+.3f",
                    name, c, n_cov / len(records), reach, b, e, e - b)
    return rows


# ------------------------------------------------------------------- models

def fit_models(rows: List[Dict]) -> Dict[str, Dict]:
    """Least squares on the fit collection. M1-M3 are linear in their
    parameters; M4 is fitted in log space over the strictly positive points."""
    x = np.array([r["completeness"] for r in rows])
    r_ = np.array([r["reachability"] for r in rows])
    y = np.array([r["gain"] for r in rows])
    out: Dict[str, Dict] = {}

    def lstsq(A):
        return np.linalg.lstsq(A, y, rcond=None)[0]

    g1 = lstsq((1 - x)[:, None])
    out["M1"] = {"form": "g0*(1-x)", "params": {"g0": float(g1[0])}}
    ab = lstsq(np.column_stack([np.ones_like(x), x]))
    out["M2"] = {"form": "a + b*x", "params": {"a": float(ab[0]), "b": float(ab[1])}}
    g3 = lstsq(((1 - x) * r_)[:, None])
    out["M3"] = {"form": "g0*(1-x)*r", "params": {"g0": float(g3[0])}}

    pos = y > 1e-6
    if pos.sum() >= 2:
        coef = np.polyfit(x[pos], np.log(y[pos]), 1)
        out["M4"] = {"form": "g0*exp(-k*x)",
                     "params": {"g0": float(math.exp(coef[1])), "k": float(-coef[0])},
                     "fitted_on": int(pos.sum())}
    else:
        out["M4"] = {"form": "g0*exp(-k*x)", "params": None,
                     "note": "not fitted: fewer than two strictly positive gains"}
    return out


def predict(model: Dict, x: float, r: float) -> float:
    p = model.get("params")
    if p is None:
        return float("nan")
    f = model["form"]
    if f == "g0*(1-x)":
        return p["g0"] * (1 - x)
    if f == "a + b*x":
        return p["a"] + p["b"] * x
    if f == "g0*(1-x)*r":
        return p["g0"] * (1 - x) * r
    return p["g0"] * math.exp(-p["k"] * x)


def score_model(model: Dict, rows: List[Dict]) -> Dict:
    y = np.array([r["gain"] for r in rows])
    yh = np.array([predict(model, r["completeness"], r["reachability"]) for r in rows])
    if not np.all(np.isfinite(yh)):
        return {"mae": None, "rmse": None, "r2": None}
    ss_res = float(((y - yh) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"mae": round(float(np.abs(y - yh).mean()), 4),
            "rmse": round(math.sqrt(ss_res / len(y)), 4),
            "r2": (round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else None),
            "predictions": [round(float(v), 4) for v in yh]}


def threshold(model: Dict, eps: float, r: float) -> float:
    """Completeness above which the model puts the expected gain below eps.
    Solved on a fine grid: the closed forms differ per model and the grid is
    exact to 0.001, which is finer than the curve is measured."""
    grid = np.linspace(0, 1, 1001)
    below = [x for x in grid if predict(model, float(x), r) < eps]
    return float(min(below)) if below else float("nan")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit-corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--pool-corpus", default=str(ROOT / "data" / "corpus_1300.jsonl"))
    ap.add_argument("--chunk-index", default=str(ROOT / "data" / "index_scaled"))
    ap.add_argument("--fit-qa", default=str(ROOT.parent / "phase1" / "data" /
                                            "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--holdout-qa", default=str(ROOT.parent / "phase1" / "data" /
                                                "libra_qa_full_polished.jsonl"))
    ap.add_argument("--fit-preds", nargs="+", default=[
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions.jsonl"),
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions_corpus.jsonl")])
    ap.add_argument("--holdout-preds", nargs="+", default=[
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions_1300.jsonl")])
    ap.add_argument("--levels", default="0,0.125,0.25,0.375,0.5,0.625,0.75,0.875,1.0")
    ap.add_argument("--eps", type=float, default=0.02,
                    help="gain below this is treated as not worth the cataloging cost")
    ap.add_argument("--max-holdout-questions", type=int, default=0,
                    help="0 = the whole held-out pool")
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--fields", default="title+subj",
                    help="record index fields; DDC is excluded by default "
                         "because it carries no measurable topical signal "
                         "(see reports/field_ablation.md)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    levels = [float(x) for x in args.levels.split(",")]

    fit_recs = ec.slim_corpus(Path(args.fit_corpus), ROOT / "data" / "slim_scaled.jsonl")
    fit_keys = {r["work_key"] for r in fit_recs}
    fit_pool = ec.question_pool(args.fit_qa, fit_keys)
    fit_qtype = {q["qid"]: q["type"] for q in fit_pool}
    fit_preds = ec.load_predictions([Path(p) for p in args.fit_preds])

    all_1300 = ec.slim_corpus(Path(args.pool_corpus), ROOT / "data" / "slim_1300.jsonl")
    ho_recs = [r for r in all_1300 if r["work_key"] not in fit_keys]
    ho_keys = {r["work_key"] for r in ho_recs}
    ho_pool = ec.question_pool(args.holdout_qa, ho_keys)
    if args.max_holdout_questions and len(ho_pool) > args.max_holdout_questions:
        ho_pool = random.Random(11).sample(ho_pool, args.max_holdout_questions)
    ho_qtype = {q["qid"]: q["type"] for q in ho_pool}
    ho_preds = ec.load_predictions([Path(p) for p in args.holdout_preds])
    # the held-out collection has no chunk index and never needs one: meta-mode
    # record rankings do not read the chunk side
    ho_chunks = ec.stub_chunk_index(ROOT / "data" / "index_holdout_stub")

    logger.info("fit: %d records / %d questions | held-out: %d records / %d questions",
                len(fit_recs), len(fit_pool), len(ho_recs), len(ho_pool))
    if not ho_pool:
        raise SystemExit("held-out question pool is empty -- check --holdout-qa")

    cache_path = ROOT / "reports" / f"gain_law_per_question{args.tag}.json"
    per_q = ec.cache(cache_path)

    fit_rows = sweep("fit", fit_recs, fit_preds, fit_pool, fit_qtype,
                     Path(args.chunk_index), levels, args.seed, per_q, cache_path,
                     args.fields)
    ho_rows = sweep("holdout", ho_recs, ho_preds, ho_pool, ho_qtype,
                    ho_chunks, levels, args.seed, per_q, cache_path,
                    args.fields)

    models = fit_models(fit_rows)
    out = {"levels": levels, "eps": args.eps, "seed": args.seed,
           "fit": {"n_records": len(fit_recs), "n_questions": len(fit_pool),
                   "curve": fit_rows},
           "holdout": {"n_records": len(ho_recs), "n_questions": len(ho_pool),
                       "curve": ho_rows},
           "models": {}}
    mean_r = float(np.mean([r["reachability"] for r in ho_rows]))
    for name, m in models.items():
        out["models"][name] = {**m,
                               "in_sample": score_model(m, fit_rows),
                               "out_of_sample": score_model(m, ho_rows),
                               "completeness_threshold": round(threshold(m, args.eps, mean_r), 3)}

    (ROOT / "reports" / f"gain_law{args.tag}.json").write_text(json.dumps(out, indent=2))

    md = ["# Enrichment-gain law: does the sparsity curve transfer?", "",
          f"- Fitted on the {len(fit_recs)}-book collection "
          f"({len(fit_pool)} questions), validated on the {len(ho_recs)} books of the "
          f"1,300-book build that are disjoint from it ({len(ho_pool)} questions)",
          "- x = baseline subject-access completeness; r = share of headingless "
          "records an LLM prediction exists for; y = topical nDCG@10 gain from enrichment",
          f"- Models are fitted on the fit curve only; out-of-sample columns are "
          f"predictions for a collection no parameter saw", "",
          "## Measured curves", "",
          "| Collection | completeness | reachability | base | enriched | gain |",
          "|---|---|---|---|---|---|"]
    for name, rows in (("fit", fit_rows), ("held-out", ho_rows)):
        for r in rows:
            md.append(f"| {name} | {r['completeness']:.3f} | {r['reachability']:.2f} | "
                      f"{r['base']:.3f} | {r['enriched']:.3f} | **{r['gain']:+.3f}** |")
    md += ["", "## Model fit and transfer", "",
           "| Model | form | in-sample MAE | out-of-sample MAE | out-of-sample R2 | "
           f"completeness where gain < {args.eps} |", "|---|---|---|---|---|---|"]
    def num(v, fmt="{:.4f}"):
        return "--" if v is None else fmt.format(v)

    for name, m in out["models"].items():
        i, o = m["in_sample"], m["out_of_sample"]
        md.append(f"| {name} | `{m['form']}` | {num(i['mae'])} | {num(o['mae'])} | "
                  f"{'--' if o['r2'] is None else o['r2']} | "
                  f"{m['completeness_threshold']} |")

    (ROOT / "reports" / f"gain_law{args.tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
