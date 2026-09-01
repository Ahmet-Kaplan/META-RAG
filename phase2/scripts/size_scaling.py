#!/usr/bin/env python3
"""
size_scaling.py — Why does the enrichment-gain curve not transfer?

gain_law.py fitted the enrichment gain against catalog completeness on the
227-book collection and it failed on the disjoint 1,011-book collection: every
model scored a negative out-of-sample R^2, and the held-out gains were 2.1-3.6x
smaller at matched completeness. The *shape* replicated exactly (Kendall tau
-0.944 on both) but the magnitude did not.

The two collections differ in more than completeness, and the most obvious
confound is size: 227 records against 1,011. A bigger catalog is a harder
retrieval problem, so the same headings buy less ranking improvement. This
tests that directly instead of adding a third collection, by holding the
*source* fixed and sweeping size: nested subsamples of the 1,241-book build at
several sizes, each measured at several completeness levels.

Nesting matters. The subsamples are nested (each size is a superset of the one
below) so that size is the only thing that changes between adjacent points --
independent draws would confound size with which books were drawn.

If gain(x, N) factorizes as f(completeness) * g(N), then a library can predict
its own gain from two numbers it already knows, and the cross-collection
failure in gain_law.py is explained rather than merely reported.

LIMIT, stated up front: these are subsamples of one corpus, so this isolates
size while holding collection *character* fixed. It cannot show that the law
transfers between genuinely different libraries -- that needs collections we do
not have. A positive result here is a necessary condition for transfer, not a
sufficient one.

Outputs:
  phase2/reports/size_scaling.json + .md

Usage:
  python3 phase2/scripts/size_scaling.py
"""

import argparse
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import exp_common as ec  # noqa: E402

logger = logging.getLogger(__name__)


def curve(name: str, records: List[Dict], preds: Dict[str, Dict], pool: List[Dict],
          qtype: Dict[str, str], chunks: Path, levels: Sequence[float], seed: int,
          per_q: Dict, cache_path: Path, fields: str) -> List[Dict]:
    with_gold = sorted(r["work_key"] for r in records if r.get("subjects"))
    rows = []
    for c in levels:
        rng = random.Random(seed)
        keep = set(rng.sample(with_gold, int(round(c * len(with_gold)))))
        masked = [r if r["work_key"] in keep else ec.strip_meta(r) for r in records]
        arms = {}
        for arm, recs in (("base", masked),
                          ("enr", [ec.enrich(r, preds) for r in masked])):
            label = f"{name}_{arm}{c:.2f}"
            if label not in per_q:
                idx = ec.build_index(recs, f"ss_{label}", chunks, fields=fields)
                per_q[label] = ec.score_pool(idx, pool)
                ec.save_cache(per_q, cache_path)
            arms[arm] = per_q[label]
        headingless = [r for r in masked if not r.get("subjects")]
        reach = (sum(1 for r in headingless if r["work_key"] in preds) /
                 len(headingless)) if headingless else 0.0
        b = ec.mean(ec.by_type(arms["base"], qtype, "topical"))
        e = ec.mean(ec.by_type(arms["enr"], qtype, "topical"))
        rows.append({"n_records": len(records), "completeness": len(keep) / len(records),
                     "reachability": reach, "base": round(b, 4),
                     "enriched": round(e, 4), "gain": round(e - b, 4)})
        logger.info("N=%-5d completeness=%.2f reach=%.2f  base=%.3f enr=%.3f gain=%+.3f",
                    len(records), len(keep) / len(records), reach, b, e, e - b)
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "slim_1300.jsonl"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_full_polished.jsonl"))
    ap.add_argument("--preds", nargs="+", default=[
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions.jsonl"),
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions_corpus.jsonl"),
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions_1300.jsonl")])
    ap.add_argument("--sizes", default="150,300,600,1241")
    ap.add_argument("--levels", default="0,0.25,0.5,0.75,1.0")
    ap.add_argument("--fields", default="title+subj")
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--sample-seed", type=int, default=5)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    allrecs = ec.read_jsonl(args.corpus)
    preds = ec.load_predictions([Path(p) for p in args.preds])
    if not any(r["work_key"] in preds for r in allrecs):
        raise SystemExit("no corpus record has an LLM prediction; run refused")
    chunks = ec.stub_chunk_index(ROOT / "data" / "index_ss_stub")

    sizes = sorted(int(s) for s in args.sizes.split(","))
    levels = [float(x) for x in args.levels.split(",")]
    # nested subsamples: one shuffle, then prefixes
    order = list(allrecs)
    random.Random(args.sample_seed).shuffle(order)

    cache_path = ROOT / "reports" / f"size_scaling_per_question{args.tag}.json"
    per_q = ec.cache(cache_path)
    out = {"sizes": sizes, "levels": levels, "seed": args.seed,
           "sample_seed": args.sample_seed, "nested": True, "curves": {}}

    for n in sizes:
        recs = order[:n]
        keys = {r["work_key"] for r in recs}
        pool = ec.question_pool(args.qa, keys)
        qtype = {q["qid"]: q["type"] for q in pool}
        logger.info("--- N=%d records, %d in-collection questions ---", len(recs), len(pool))
        out["curves"][str(n)] = {
            "n_questions": len(pool),
            "rows": curve(f"n{n}", recs, preds, pool, qtype, chunks, levels,
                          args.seed, per_q, cache_path, args.fields)}

    # does gain factorize as f(completeness) * g(N)?
    ref = str(sizes[0])
    ref_rows = out["curves"][ref]["rows"]
    fx = np.array([r["gain"] for r in ref_rows])
    out["factorization"] = {"reference_size": int(ref), "scales": {}}
    for n in sizes[1:]:
        y = np.array([r["gain"] for r in out["curves"][str(n)]["rows"]])
        # single free scale relating this size's curve to the reference curve
        g = float((fx @ y) / (fx @ fx)) if float(fx @ fx) else float("nan")
        yhat = g * fx
        ss_res = float(((y - yhat) ** 2).sum()); ss_tot = float(((y - y.mean()) ** 2).sum())
        out["factorization"]["scales"][str(n)] = {
            "g": round(g, 4), "mae": round(float(np.abs(y - yhat).mean()), 4),
            "r2": (round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else None)}

    # is g(N) itself predictable? fit log g = a + b log N over the non-reference sizes
    ns = np.array([float(n) for n in sizes[1:]])
    gs = np.array([out["factorization"]["scales"][str(n)]["g"] for n in sizes[1:]])
    if (gs > 0).all() and len(ns) >= 2:
        b, a = np.polyfit(np.log(ns), np.log(gs), 1)
        out["factorization"]["power_law"] = {
            "form": "g(N) = exp(a) * N^b", "a": round(float(a), 4), "b": round(float(b), 4),
            "predicted_g": {str(int(n)): round(float(math.exp(a) * n ** b), 4) for n in ns}}
    else:
        out["factorization"]["power_law"] = {"note": "not fitted: a scale was non-positive"}

    (ROOT / "reports" / f"size_scaling{args.tag}.json").write_text(json.dumps(out, indent=2))

    md = ["# Size scaling: is the transfer failure a collection-size effect?", "",
          "- Nested subsamples of the 1,241-book build; each size is a superset of the "
          "one below, so size is the only thing that changes",
          "- Gain = topical nDCG@10 (enriched - baseline) at each completeness level",
          "- Subsamples of one corpus: this isolates size, not cross-library transfer", "",
          "| N | questions | completeness | base | enriched | gain |",
          "|---|---|---|---|---|---|"]
    for n in sizes:
        c = out["curves"][str(n)]
        for r in c["rows"]:
            md.append(f"| {n} | {c['n_questions']} | {r['completeness']:.2f} | "
                      f"{r['base']:.3f} | {r['enriched']:.3f} | **{r['gain']:+.3f}** |")
    md += ["", f"## Does the curve factorize? (reference N={ref})", "",
           "One free scale g per size, relating that size's gain curve to the "
           "reference curve.", "",
           "| N | g | MAE | R2 |", "|---|---|---|---|"]
    for n in sizes[1:]:
        v = out["factorization"]["scales"][str(n)]
        md.append(f"| {n} | {v['g']:.3f} | {v['mae']:.4f} | "
                  f"{'--' if v['r2'] is None else v['r2']} |")
    pl = out["factorization"]["power_law"]
    if "b" in pl:
        md += ["", f"Fitted `g(N) = {math.exp(pl['a']):.3f} * N^({pl['b']:.3f})`.",
               "A negative exponent means the same headings buy less ranking "
               "improvement as the catalog grows."]
    (ROOT / "reports" / f"size_scaling{args.tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
