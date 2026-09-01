#!/usr/bin/env python3
"""
loop_closing.py — Does LLM-generated metadata actually improve discovery?

The paper's thesis is that LLM cataloging can close the gap left by missing
metadata. This measures it directly: build the record index three ways, change
nothing else, and re-run the same questions.

  none  records carry title/author/year only (the minimal-record baseline)
  llm   subjects and DDC come from deepseek-chat (LIBRA-CAT predictions)
  gold  subjects and DDC come from the professional-derived gold

All three use identical index fields (--fields, default title+subj); only the
*content* of the subject fields differs. Full-text chunks are shared and untouched.

IMPORTANT INTERPRETATION LIMIT: LIBRA-QA topical questions are LLM paraphrases
of each record's *gold* subject heading, so the gold condition is advantaged by
construction. The llm condition is therefore a LOWER bound on the value of
LLM metadata to a patron whose query was not derived from the gold.

Outputs:
  phase2/reports/loop_closing.json + .md

Usage:
  python3 phase2/scripts/loop_closing.py
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
TYPES = ("known_item", "topical", "bib_fact")

logger = logging.getLogger(__name__)


def load_predictions(paths: List[Path]) -> Dict[str, Dict]:
    """work_key -> prediction row. Later files win; failed rows are skipped."""
    preds: Dict[str, Dict] = {}
    for p in paths:
        if not p.exists():
            logger.warning("predictions file missing: %s", p)
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("error"):
                continue
            preds[r["work_key"]] = r
    return preds


def make_records(corpus: List[Dict], condition: str, preds: Dict[str, Dict]) -> List[Dict]:
    """Records-only copies with subjects/DDC set per condition."""
    out = []
    for rec in corpus:
        r = {k: v for k, v in rec.items() if k != "chunks"}
        if condition == "none":
            r["subjects"], r["ddc"] = [], []
        elif condition == "llm":
            p = preds.get(rec["work_key"])
            r["subjects"] = list(p["pred_subjects"]) if p else []
            r["ddc"] = [p["pred_ddc"]] if p and p.get("pred_ddc") else []
        elif condition == "llm_matched":
            # LLM metadata, but only for records that HAVE gold metadata. Isolates
            # heading *quality* from the coverage advantage the LLM gets by also
            # cataloging the records gold leaves empty.
            if rec.get("subjects"):
                p = preds.get(rec["work_key"])
                r["subjects"] = list(p["pred_subjects"]) if p else []
                r["ddc"] = [p["pred_ddc"]] if p and p.get("pred_ddc") else []
            else:
                r["subjects"], r["ddc"] = [], []
        elif condition == "gold":
            pass                      # leave the record's own gold fields
        else:
            raise ValueError(f"unknown condition {condition}")
        out.append(r)
    return out


def run_condition(condition: str, corpus: List[Dict], preds: Dict[str, Dict],
                  args) -> Dict:
    recs = make_records(corpus, condition, preds)
    covered = sum(1 for r in recs if r["subjects"])
    rec_path = ROOT / "data" / f"{args.index_prefix}_records_loop_{condition}.jsonl"
    rec_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
        encoding="utf-8")

    idx_dir = ROOT / "data" / f"{args.index_prefix}_loop_{condition}"
    r1 = subprocess.run(
        [PY, "scripts/index.py", "--corpus", str(rec_path), "--outdir", str(idx_dir),
         "--fields", args.fields, "--records-only",
         "--chunk-index", args.chunk_index],
        cwd=ROOT, capture_output=True, text=True)
    if r1.returncode != 0:
        raise RuntimeError(f"[{condition}] index failed: {r1.stderr[-500:]}")

    rep = ROOT / "reports" / f"loop_{condition}.md"
    r2 = subprocess.run(
        [PY, "scripts/evaluate.py", "--index", str(idx_dir), "--qa", args.qa,
         "--corpus", str(rec_path), "--mode", "meta",
         "--questions", str(args.questions), "--report", str(rep)],
        cwd=ROOT, capture_output=True, text=True)
    jp = rep.with_suffix(".json")
    if r2.returncode != 0 or not jp.exists():
        raise RuntimeError(f"[{condition}] eval failed: {r2.stderr[-500:]}")

    j = json.loads(jp.read_text())
    res = {"overall": j["overall"]["meta"],
           "per_type": {t: j["per_type"][t]["meta"] for t in TYPES},
           "records_with_subjects": covered}
    logger.info("[%s] overall=%.3f topical=%.3f (%d/%d records have subjects)",
                condition, res["overall"], res["per_type"]["topical"],
                covered, len(recs))
    return res


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--chunk-index", default=str(ROOT / "data" / "index_scaled"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--preds", nargs="+", default=[
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions.jsonl"),
        str(ROOT.parent / "phase1" / "data" / "libra_cat_predictions_corpus.jsonl"),
    ])
    ap.add_argument("--questions", type=int, default=300)
    ap.add_argument("--fields", default="title+subj",
                    help="record index fields; DDC is excluded by default "
                         "because it carries no measurable topical signal "
                         "(see reports/field_ablation.md)")
    ap.add_argument("--index-prefix", default="index_scaled")
    args = ap.parse_args()

    corpus = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    preds = load_predictions([Path(p) for p in args.preds])
    hit = sum(1 for r in corpus if r["work_key"] in preds)
    logger.info("corpus %d records; LLM predictions available for %d (%.0f%%)",
                len(corpus), hit, 100 * hit / len(corpus))
    if not hit:
        raise SystemExit(
            f"no corpus record has an LLM prediction (checked: "
            f"{', '.join(str(p) for p in args.preds)}). Every LLM condition would "
            f"silently equal loop_none, so this run is refused. Pass --preds as "
            f"absolute paths, or check the work_key join.")
    if hit < len(corpus):
        logger.warning("%d records lack a prediction and will be indexed with "
                       "empty subjects in the llm condition", len(corpus) - hit)

    results = {"n_records": len(corpus), "n_questions": args.questions,
               "prediction_coverage": hit, "conditions": {}}
    for condition in ("none", "llm_matched", "llm", "gold"):
        results["conditions"][condition] = run_condition(condition, corpus, preds, args)

    out = ROOT / "reports" / "loop_closing.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    c = results["conditions"]
    md = ["# Loop closing: does LLM-generated metadata improve discovery?", "",
          f"- {len(corpus)} books, {args.questions} questions, META-RAG record index",
          f"- LLM metadata available for {hit}/{len(corpus)} records",
          "- Identical index fields in all conditions; only field *content* changes",
          "",
          "| Record metadata | overall | known_item | topical | bib_fact |",
          "|---|---|---|---|---|"]
    for cond in ("none", "llm_matched", "llm", "gold"):
        r = c[cond]
        md.append(f"| {cond} | {r['overall']:.3f} | " +
                  " | ".join(f"{r['per_type'][t]:.3f}" for t in TYPES) + " |")
    t = {k: c[k]["per_type"]["topical"] for k in c}
    gap = t["gold"] - t["none"]
    quality = (t["llm_matched"] - t["none"]) / gap if gap else float("nan")
    coverage = (t["llm"] - t["llm_matched"]) / gap if gap else float("nan")
    md += ["", "## Decomposition of the topical gap", "",
           f"The gap between no metadata ({t['none']:.3f}) and gold metadata "
           f"({t['gold']:.3f}) is {gap:.3f} nDCG@10. LLM cataloging closes "
           f"{100 * (t['llm'] - t['none']) / gap:.0f}% of it, in two parts:", "",
           f"- **Heading quality** ({100 * quality:.0f}% of the gap): at matched "
           f"coverage, LLM headings on the {c['gold']['records_with_subjects']} "
           f"records that have gold reach {t['llm_matched']:.3f} vs. gold's "
           f"{t['gold']:.3f}.",
           f"- **Coverage** ({100 * coverage:.0f}% of the gap): the LLM also "
           f"catalogs the {c['llm']['records_with_subjects'] - c['gold']['records_with_subjects']} "
           f"records that carry no gold heading at all, lifting topical nDCG@10 "
           f"from {t['llm_matched']:.3f} to {t['llm']:.3f}.", "",
           "So parity with gold is real but is not all heading quality: roughly",
           f"{100 * coverage:.0f}% of it comes from enriching records the gold leaves empty.",
           "", "## Interpretation limits", "",
           "1. LIBRA-QA topical questions are paraphrases of each record's *gold*",
           "   heading, so the gold condition is advantaged by construction and",
           "   llm_matched is a lower bound on LLM heading utility.",
           "2. The corpus is canonical public-domain literature; the model may have",
           "   memorized real LCSH for these works, which would inflate both LLM",
           "   conditions relative to a contemporary or obscure collection.",
           "3. Known-item retrieval is *hurt* by both metadata sources relative to",
           f"   title-only ({t['none']:.3f}... see table): subject terms add noise to",
           "   identity lookups, and LLM subjects add slightly more than gold."]
    (ROOT / "reports" / "loop_closing.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    logger.info("Wrote %s and loop_closing.md", out)
    print("\n".join(md))


if __name__ == "__main__":
    main()
