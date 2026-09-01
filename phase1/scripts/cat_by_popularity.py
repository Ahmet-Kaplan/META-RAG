#!/usr/bin/env python3
"""
cat_by_popularity.py — Is LIBRA-CAT performance memorization?

The corpus is canonical public-domain literature, so a large model may simply
recall the real LCSH and DDC for famous works rather than performing subject
analysis. If that is what is happening, cataloging quality should fall off
sharply for obscure books.

Project Gutenberg download counts give a popularity proxy. This buckets the
LIBRA-CAT predictions by download count and re-scores each bucket with the
same protocol as score_libra_cat.py.

A flat profile across buckets is evidence against the memorization explanation;
a steep one means the headline CAT numbers do not transfer to a working
collection.

Outputs:
  phase1/reports/libra_cat_by_popularity.json + .md

Usage:
  python3 phase1/scripts/cat_by_popularity.py [--buckets 3]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_libra_cat import (  # noqa: E402
    AuthorityChecker, build_semantic_matcher, classify_pred_error, norm,
    score_ddc, score_heading,
)

logger = logging.getLogger(__name__)


def load_downloads(paths: List[Path]) -> Dict[int, int]:
    """gutenberg_id -> download_count."""
    dl: Dict[int, int] = {}
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            gid, n = r.get("gutenberg_id"), r.get("download_count")
            if gid is not None and n is not None:
                dl[gid] = max(n, dl.get(gid, 0))
    return dl


def score_bucket(rows: List[Dict], sim, authority) -> Dict:
    levels = {"exact": 0, "semantic": 0, "acceptable": 0, "miss": 0}
    errors: Dict[str, int] = {}
    ddc_levels: Dict[str, int] = {}
    n_gold = n_pred = 0
    for r in rows:
        preds, golds = r["pred_subjects"], r["gold_subjects"]
        n_gold += len(golds)
        n_pred += len(preds)
        for g in golds:
            levels[score_heading(g, preds, sim)] += 1
        for p in preds:
            if any(score_heading(g, [p], sim) in ("exact", "semantic") for g in golds):
                continue
            b = classify_pred_error(p, golds, authority)
            errors[b] = errors.get(b, 0) + 1
        if r["gold_ddc"]:
            lv = score_ddc(r.get("pred_ddc"), r["gold_ddc"])
            ddc_levels[lv] = ddc_levels.get(lv, 0) + 1
    n_ddc = sum(ddc_levels.values())
    cum_exact = levels["exact"]
    cum_sem = cum_exact + levels["semantic"]
    cum_acc = cum_sem + levels["acceptable"]
    return {
        "n_records": len(rows), "n_gold_headings": n_gold, "n_pred_headings": n_pred,
        "exact": round(cum_exact / n_gold, 3) if n_gold else None,
        "exact_or_semantic": round(cum_sem / n_gold, 3) if n_gold else None,
        "any_level": round(cum_acc / n_gold, 3) if n_gold else None,
        "authority_violation_rate": round(errors.get("authority_violation", 0) / n_pred, 4) if n_pred else None,
        "ddc_n": n_ddc,
        "ddc_exact": round(ddc_levels.get("exact", 0) / n_ddc, 3) if n_ddc else None,
        "ddc_class3": round((ddc_levels.get("exact", 0) + ddc_levels.get("class3", 0)) / n_ddc, 3) if n_ddc else None,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", nargs="+", default=[
        str(ROOT / "data" / "libra_cat_predictions.jsonl"),
        str(ROOT / "data" / "libra_cat_predictions_corpus.jsonl")])
    ap.add_argument("--index", nargs="+", default=[
        str(ROOT / "data" / "gutenberg_index_scaled.jsonl"),
        str(ROOT / "data" / "join_matches_scaled.jsonl")])
    ap.add_argument("--buckets", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "reports" / "libra_cat_by_popularity"))
    args = ap.parse_args()

    rows: List[Dict] = []
    seen = set()
    for p in args.preds:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("error") or r["work_key"] in seen:
                continue
            seen.add(r["work_key"])
            rows.append(r)

    dl = load_downloads([Path(p) for p in args.index])
    scored = [r for r in rows if dl.get(r.get("gutenberg_id")) is not None]
    logger.info("%d predictions, %d with a download count", len(rows), len(scored))
    if not scored:
        sys.exit("no download counts found; cannot bucket by popularity")
    for r in scored:
        r["_dl"] = dl[r["gutenberg_id"]]
    scored.sort(key=lambda r: r["_dl"])

    texts = []
    for r in scored:
        texts += [norm(h) for h in r["gold_subjects"]] + [norm(h) for h in r["pred_subjects"]]
    sim = build_semantic_matcher(texts)
    authority = AuthorityChecker(enabled=True)

    size = len(scored) // args.buckets
    buckets = []
    for i in range(args.buckets):
        lo = i * size
        hi = len(scored) if i == args.buckets - 1 else (i + 1) * size
        chunk = scored[lo:hi]
        label = f"{chunk[0]['_dl']}-{chunk[-1]['_dl']} downloads"
        logger.info("bucket %d/%d: %s (n=%d)", i + 1, args.buckets, label, len(chunk))
        res = score_bucket(chunk, sim, authority)
        res["label"] = label
        res["dl_min"], res["dl_max"] = chunk[0]["_dl"], chunk[-1]["_dl"]
        res["dl_median"] = chunk[len(chunk) // 2]["_dl"]
        buckets.append(res)
        authority.save()
    authority.save()

    out = {"n_scored": len(scored), "n_buckets": args.buckets, "buckets": buckets}
    Path(args.out).with_suffix(".json").write_text(json.dumps(out, indent=2))

    md = ["# LIBRA-CAT by book popularity (memorization probe)", "",
          "Project Gutenberg download count as a popularity proxy. If the headline",
          "cataloging numbers were driven by memorization of famous works, quality",
          "should fall off sharply in the low-popularity buckets.", "",
          f"- {len(scored)} predictions with a download count, {args.buckets} equal-size buckets", "",
          "| Bucket (downloads) | n | LCSH exact | +semantic | any level | DDC class3 | authority viol. |",
          "|---|---|---|---|---|---|---|"]
    for b in buckets:
        md.append(
            f"| {b['label']} | {b['n_records']} | {b['exact']:.3f} | {b['exact_or_semantic']:.3f} | "
            f"{b['any_level']:.3f} | " +
            (f"{b['ddc_class3']:.3f}" if b['ddc_class3'] is not None else "--") +
            f" (n={b['ddc_n']}) | {100*b['authority_violation_rate']:.1f}% |")
    lo, hi = buckets[0], buckets[-1]
    md += ["", "## Reading", "",
           f"- LCSH exact: {lo['exact']:.3f} (least popular) vs {hi['exact']:.3f} (most popular), "
           f"delta {hi['exact']-lo['exact']:+.3f}",
           f"- Any-level:  {lo['any_level']:.3f} vs {hi['any_level']:.3f}, "
           f"delta {hi['any_level']-lo['any_level']:+.3f}"]
    if lo["ddc_class3"] is not None and hi["ddc_class3"] is not None:
        md.append(f"- DDC class3: {lo['ddc_class3']:.3f} vs {hi['ddc_class3']:.3f}, "
                  f"delta {hi['ddc_class3']-lo['ddc_class3']:+.3f}")
    Path(args.out).with_suffix(".md").write_text("\n".join(md) + "\n")
    # paper macros: these three tiers were the only hardcoded numbers left in
    # the manuscript, so they could not be checked against a report file
    tex = ["% popularity_numbers.tex - AUTO-GENERATED by cat_by_popularity.py."]
    for tier, b in zip(("Low", "Mid", "High"), out["buckets"]):
        tex.append(r"\newcommand{\Pop" + tier + r"Exact}{" + f"{b['exact']:.3f}" + "}")
        tex.append(r"\newcommand{\Pop" + tier + r"Ddc}{" +
                   (f"{b['ddc_class3']:.3f}" if b["ddc_class3"] is not None else "--") + "}")
    tex.append(r"\newcommand{\PopNTiers}{" + str(len(out["buckets"])) + "}")
    tex.append(r"\newcommand{\PopPerTier}{" + str(out["buckets"][0]["n_records"]) + "}")
    lo_b, hi_b = out["buckets"][0], out["buckets"][-1]
    tex.append(r"\newcommand{\PopExactDelta}{" + f"{hi_b['exact'] - lo_b['exact']:+.3f}" + "}")
    if lo_b["ddc_class3"] is not None and hi_b["ddc_class3"] is not None:
        tex.append(r"\newcommand{\PopDdcDelta}{" + f"{hi_b['ddc_class3'] - lo_b['ddc_class3']:+.3f}" + "}")
    tex.append(r"\newcommand{\PopLowAuth}{" + f"{100 * lo_b['authority_violation_rate']:.1f}" + "}")
    tex.append(r"\newcommand{\PopHighAuth}{" + f"{100 * hi_b['authority_violation_rate']:.1f}" + "}")
    (ROOT.parent / "paper" / "popularity_numbers.tex").write_text("\n".join(tex) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
