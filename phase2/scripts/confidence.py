#!/usr/bin/env python3
"""
confidence.py — Confidence intervals and seed sensitivity for every reported
retrieval number.

The paper's tables are point estimates on one 300-question sample drawn with
one seed. This evaluates every configuration on the *entire* in-corpus question
pool, which removes the sampling question rather than bounding it, and then
reports bootstrap 95% CIs. Per-question scores are cached, so seed sensitivity
(what a 300-question sample would have given under other seeds) costs nothing
extra.

Outputs:
  phase2/reports/confidence.json + .md

Usage:
  python3 phase2/scripts/confidence.py [--bootstrap 10000]
"""

import argparse
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from retrieval import MetaIndex  # noqa: E402

logger = logging.getLogger(__name__)
TYPES = ("known_item", "topical", "bib_fact")

def build_configs(prefix: str):
    """(label, index dir, mode, needs chunk retrieval) for one corpus build."""
    cfgs = [
        ("dense", prefix, "dense", True),
        ("bm25", prefix, "bm25", True),
        ("hybrid", prefix, "hybrid", True),
        ("meta", prefix, "meta", False),
        # four-way fusion ablation: needs the chunk side, unlike plain meta
        ("meta4", prefix, "meta4", True),
        ("loop_none", f"{prefix}_loop_none", "meta", False),
        ("loop_llm", f"{prefix}_loop_llm", "meta", False),
        ("loop_llm_matched", f"{prefix}_loop_llm_matched", "meta", False),
        ("loop_gold", f"{prefix}_loop_gold", "meta", False),
    ]
    for lvl in ("0.00", "0.25", "0.50", "0.75", "1.00"):
        cfgs.append((f"sp_base{lvl}", f"{prefix}_sp_base{lvl}", "meta", False))
        cfgs.append((f"sp_enr{lvl}", f"{prefix}_sp_enr{lvl}", "meta", False))
        cfgs.append((f"noise{lvl}", f"{prefix}_n{lvl}", "meta", False))
    return cfgs


def ndcg_at_10(ranked: List[str], gold: str) -> float:
    return sum(1 / math.log2(i + 2) for i, r in enumerate(ranked[:10]) if r == gold)


def bootstrap_ci(values: List[float], n: int, rng: random.Random) -> Tuple[float, float]:
    """Percentile bootstrap CI. Vectorized: a pure-Python resample loop over
    ~1k values x 10k replicates per cell is minutes of pointless work."""
    if not values:
        return (float("nan"), float("nan"))
    import numpy as np
    arr = np.asarray(values, dtype=float)
    gen = np.random.default_rng(rng.randrange(2 ** 32))
    idx = gen.integers(0, len(arr), size=(n, len(arr)))
    means = arr[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return (float(lo), float(hi))


def run_config(label: str, idx_name: str, mode: str, needs_chunks: bool,
               questions: List[Dict], chunk_to_work: Dict[str, str]) -> Dict[str, float]:
    idx_dir = ROOT / "data" / idx_name
    if not idx_dir.exists():
        logger.warning("skipping %s: %s missing", label, idx_dir)
        return {}
    idx = MetaIndex(str(idx_dir))
    if needs_chunks and not idx.chunk_ids:
        # A record-only index built against a stub chunk side would score every
        # chunk-based mode at 0.0 with no error. Skip loudly instead.
        logger.warning("skipping %s: %s has no chunk side, and mode %s needs one",
                       label, idx_dir.name, mode)
        return {}
    scores: Dict[str, float] = {}
    for q in questions:
        chunks, records = idx.retrieve(q["question_polished"], mode=mode,
                                       topk_chunks=50, skip_chunks=not needs_chunks)
        if mode in ("meta", "meta4"):
            # meta4 fuses the projected chunk rankings into its *record* ranking
            # already; re-deriving records from the chunk list here threw that
            # ranking away and scored plain hybrid under the meta4 label.
            rec_ids = [r for r, _ in records]
        else:
            rec_ids, seen = [], set()
            for cid, _ in chunks:
                wk = chunk_to_work.get(cid)
                if wk and wk not in seen:
                    seen.add(wk)
                    rec_ids.append(wk)
            rec_ids = rec_ids[:10]
        scores[q["qid"]] = ndcg_at_10(rec_ids, q["work_key"])
    return scores


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seeds", default="11,12,13,14,15")
    ap.add_argument("--sample-size", type=int, default=300)
    ap.add_argument("--index-prefix", default="index_scaled")
    ap.add_argument("--tag", default="", help="suffix for output filenames")
    ap.add_argument("--refresh", default="",
                    help="comma-separated config labels to rescore even if "
                         "they are already in the per-question cache")
    ap.add_argument("--max-questions", type=int, default=0,
                    help="0 = whole in-corpus pool; otherwise a fixed seeded sample "
                         "(the chunk-based baselines are ~1-2.5 s/question)")
    args = ap.parse_args()
    configs = build_configs(args.index_prefix)

    corpus = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    keys = {r["work_key"] for r in corpus}
    chunk_to_work = {c["chunk_id"]: r["work_key"] for r in corpus
                     for c in r.get("chunks", []) if c.get("chunk_id")}
    qa = [json.loads(l) for l in open(args.qa, encoding="utf-8") if l.strip()]
    pool = [q for q in qa if q.get("work_key") in keys]
    if args.max_questions and len(pool) > args.max_questions:
        pool = random.Random(11).sample(pool, args.max_questions)
        logger.info("evaluating a %d-question sample of the in-corpus pool",
                    len(pool))
    else:
        logger.info("evaluating the full in-corpus pool: %d questions", len(pool))
    results_meta = {"n_books": len(corpus),
                    # records keep n_chunks after the chunk bodies are stripped,
                    # so this is right for slim corpora too
                    "n_chunks": sum(r.get("n_chunks", 0) for r in corpus),
                    "n_gold_covered": sum(1 for r in corpus if r.get("subjects")),
                    "n_no_gold": sum(1 for r in corpus if not r.get("subjects"))}

    # Per-config cache, not all-or-nothing: rebuilding only the metadata side
    # (e.g. dropping DDC from the record index) leaves the metadata-blind
    # baselines bit-identical, and rescoring dense/bm25/hybrid over ~460k chunks
    # is hours of work for numbers that cannot have changed. --refresh forces a
    # config to be rescored.
    cache_path = ROOT / "reports" / f"confidence_per_question{args.tag}.json"
    per_q = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    refresh = {r for r in args.refresh.split(",") if r}
    if per_q:
        logger.info("loaded cached per-question scores (%d configs)", len(per_q))
    for label, idx_name, mode, needs in configs:
        if per_q.get(label) and label not in refresh:
            continue
        per_q[label] = run_config(label, idx_name, mode, needs, pool, chunk_to_work)
        if per_q[label]:
            vals = list(per_q[label].values())
            logger.info("%-16s overall=%.3f (n=%d)", label, sum(vals) / len(vals), len(vals))
        cache_path.write_text(json.dumps(per_q))

    qtype = {q["qid"]: q["type"] for q in pool}
    rng = random.Random(7)
    results = {"n_pool": len(pool), "bootstrap": args.bootstrap,
               **results_meta, "configs": {}}

    for label, scores in per_q.items():
        if not scores:
            continue
        entry = {}
        for t in (*TYPES, "overall"):
            vals = [v for qid, v in scores.items() if t == "overall" or qtype.get(qid) == t]
            lo, hi = bootstrap_ci(vals, args.bootstrap, rng)
            entry[t] = {"n": len(vals), "mean": round(sum(vals) / len(vals), 3),
                        "ci95": [round(lo, 3), round(hi, 3)]}
        results["configs"][label] = entry

    # seed sensitivity: what a 300-question sample would have given, per seed
    seeds = [int(s) for s in args.seeds.split(",")]
    sens = {}
    for label, scores in per_q.items():
        if not scores:
            continue
        per_seed = []
        for sd in seeds:
            sample = random.Random(sd).sample(pool, min(args.sample_size, len(pool)))
            vals = [scores[q["qid"]] for q in sample if q["qid"] in scores]
            per_seed.append(sum(vals) / len(vals))
        mean = sum(per_seed) / len(per_seed)
        sd_ = math.sqrt(sum((x - mean) ** 2 for x in per_seed) / (len(per_seed) - 1))
        sens[label] = {"seeds": seeds, "values": [round(v, 3) for v in per_seed],
                       "mean": round(mean, 3), "sd": round(sd_, 3),
                       "range": round(max(per_seed) - min(per_seed), 3)}
    results["seed_sensitivity"] = sens

    (ROOT / "reports" / f"confidence{args.tag}.json").write_text(json.dumps(results, indent=2))

    md = ["# Confidence intervals and seed sensitivity", "",
          f"- Every configuration evaluated on the **full in-corpus pool "
          f"({len(pool)} questions)**, not a 300-question sample",
          f"- Bootstrap 95% CIs, {args.bootstrap:,} resamples", "",
          "| Configuration | known_item | topical | bib_fact | overall |",
          "|---|---|---|---|---|"]
    for label, e in results["configs"].items():
        row = " | ".join(f"{e[t]['mean']:.3f} [{e[t]['ci95'][0]:.3f}, {e[t]['ci95'][1]:.3f}]"
                         for t in (*TYPES, "overall"))
        md.append(f"| {label} | {row} |")
    md += ["", f"## Seed sensitivity ({args.sample_size}-question subsamples, "
               f"seeds {', '.join(map(str, seeds))})", "",
           "| Configuration | values | mean | sd | range |", "|---|---|---|---|---|"]
    for label, v in sens.items():
        md.append(f"| {label} | {', '.join(f'{x:.3f}' for x in v['values'])} | "
                  f"{v['mean']:.3f} | {v['sd']:.3f} | {v['range']:.3f} |")
    (ROOT / "reports" / f"confidence{args.tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
