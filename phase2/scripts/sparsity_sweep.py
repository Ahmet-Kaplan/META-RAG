#!/usr/bin/env python3
"""
sparsity_sweep.py — At what catalog sparsity does LLM enrichment pay off?

loop_closing.py answers the question at one point: this collection, where 156 of
227 records carry a gold subject heading. Real catalogs vary enormously in how
complete their subject access is, so the decision-relevant object is a curve,
not a point.

For each coverage level c, gold headings are retained on a random c fraction of
the records that have them and stripped from the rest, giving a synthetic
catalog of that sparsity. Two conditions are then evaluated:

  baseline@c   the sparse catalog as-is
  enriched@c   the same catalog, with LLM headings written into every record
               that lacks one after masking

The gap between the curves is the value of LLM cataloging at that sparsity.
Both conditions share the same mask at a given c (same seed), so the only
difference is the enrichment.

Outputs:
  phase2/reports/sparsity_sweep.json + .md
  figures/fig_sparsity.pdf/.png

Usage:
  python3 phase2/scripts/sparsity_sweep.py
"""

import argparse
import json
import logging
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
TYPES = ("known_item", "topical", "bib_fact")

logger = logging.getLogger(__name__)


def load_predictions(paths: List[Path]) -> Dict[str, Dict]:
    preds: Dict[str, Dict] = {}
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if not r.get("error"):
                    preds[r["work_key"]] = r
    return preds


def make_records(corpus: List[Dict], keep: set, enrich: bool,
                 preds: Dict[str, Dict]) -> List[Dict]:
    """Records with gold kept only for work_keys in `keep`; optionally enriched."""
    out = []
    for rec in corpus:
        r = {k: v for k, v in rec.items() if k != "chunks"}
        if rec["work_key"] in keep:
            pass                                   # keep the record's gold fields
        else:
            r["subjects"], r["ddc"] = [], []
        if enrich and not r["subjects"]:
            p = preds.get(rec["work_key"])
            if p:
                r["subjects"] = list(p["pred_subjects"])
                r["ddc"] = [p["pred_ddc"]] if p.get("pred_ddc") else []
        out.append(r)
    return out


def evaluate(tag: str, recs: List[Dict], args) -> Dict:
    rec_path = ROOT / "data" / f"{args.index_prefix}_records_sp_{tag}.jsonl"
    rec_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                        encoding="utf-8")
    idx_dir = ROOT / "data" / f"{args.index_prefix}_sp_{tag}"
    r1 = subprocess.run(
        [PY, "scripts/index.py", "--corpus", str(rec_path), "--outdir", str(idx_dir),
         "--fields", args.fields, "--records-only",
         "--chunk-index", args.chunk_index],
        cwd=ROOT, capture_output=True, text=True)
    if r1.returncode != 0:
        raise RuntimeError(f"[{tag}] index failed: {r1.stderr[-400:]}")
    rep = ROOT / "reports" / f"sp_{tag}.md"
    r2 = subprocess.run(
        [PY, "scripts/evaluate.py", "--index", str(idx_dir), "--qa", args.qa,
         "--corpus", str(rec_path), "--mode", "meta",
         "--questions", str(args.questions), "--report", str(rep)],
        cwd=ROOT, capture_output=True, text=True)
    jp = rep.with_suffix(".json")
    if r2.returncode != 0 or not jp.exists():
        raise RuntimeError(f"[{tag}] eval failed: {r2.stderr[-400:]}")
    j = json.loads(jp.read_text())
    return {"overall": j["overall"]["meta"],
            "per_type": {t: j["per_type"][t]["meta"] for t in TYPES},
            "records_with_subjects": sum(1 for r in recs if r["subjects"])}


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
    ap.add_argument("--levels", default="0,0.25,0.5,0.75,1.0")
    ap.add_argument("--questions", type=int, default=300)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--fields", default="title+subj",
                    help="record index fields; DDC is excluded by default "
                         "because it carries no measurable topical signal "
                         "(see reports/field_ablation.md)")
    ap.add_argument("--index-prefix", default="index_scaled")
    args = ap.parse_args()

    corpus = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    preds = load_predictions([Path(p) for p in args.preds])
    with_gold = [r["work_key"] for r in corpus if r.get("subjects")]
    matched = sum(1 for r in corpus if r["work_key"] in preds)
    logger.info("%d records, %d with gold subjects, %d with LLM predictions",
                len(corpus), len(with_gold), matched)
    if not matched:
        raise SystemExit(
            f"no corpus record has an LLM prediction (checked {len(args.preds)} "
            f"file(s): {', '.join(str(p) for p in args.preds)}). Every enrichment "
            f"condition would silently equal its baseline, so this run is refused. "
            f"Pass --preds as absolute paths, or check the work_key join.")

    levels = [float(x) for x in args.levels.split(",")]
    results = {"n_records": len(corpus), "n_with_gold": len(with_gold),
               "n_questions": args.questions, "seed": args.seed, "levels": levels,
               "baseline": {}, "enriched": {}}

    for c in levels:
        rng = random.Random(args.seed)             # same mask for both conditions
        k = int(round(c * len(with_gold)))
        keep = set(rng.sample(with_gold, k))
        tag = f"{c:.2f}"
        results["baseline"][tag] = evaluate(f"base{tag}", make_records(corpus, keep, False, preds), args)
        results["enriched"][tag] = evaluate(f"enr{tag}", make_records(corpus, keep, True, preds), args)
        b, e = results["baseline"][tag], results["enriched"][tag]
        logger.info("coverage %4.0f%% (%3d/%d gold): topical baseline=%.3f enriched=%.3f  (+%.3f)",
                    100 * c, k, len(with_gold), b["per_type"]["topical"],
                    e["per_type"]["topical"], e["per_type"]["topical"] - b["per_type"]["topical"])

    (ROOT / "reports" / "sparsity_sweep.json").write_text(json.dumps(results, indent=2))

    md = ["# Sparsity sweep: when does LLM enrichment pay off?", "",
          f"- {len(corpus)} books, {args.questions} questions, META-RAG record index",
          f"- Coverage = fraction of the {len(with_gold)} gold-bearing records that keep their headings",
          f"- `enriched` adds LLM headings to every record left without one (seed {args.seed})", "",
          "| Gold coverage | records w/ subjects (base -> enr) | topical base | topical enriched | gain |",
          "|---|---|---|---|---|"]
    for c in levels:
        tag = f"{c:.2f}"
        b, e = results["baseline"][tag], results["enriched"][tag]
        bt, et = b["per_type"]["topical"], e["per_type"]["topical"]
        md.append(f"| {100*c:.0f}% | {b['records_with_subjects']} -> {e['records_with_subjects']} | "
                  f"{bt:.3f} | {et:.3f} | **+{et-bt:.3f}** |")
    (ROOT / "reports" / "sparsity_sweep.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
