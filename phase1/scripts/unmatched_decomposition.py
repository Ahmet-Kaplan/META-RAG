#!/usr/bin/env python3
"""
unmatched_decomposition.py — Decompose the 932 "valid LCSH, no gold match"
headings that the AIDL reviewer flagged as opaque.

Step 1 replicates score_libra_cat.py's taxonomy *offline* (authority cache
only, no id.loc.gov network calls) and asserts it reproduces the shipped
counts (932 unrelated, 20 authority violations, 51 under-, 14 over-specific)
before anything is trusted.

Step 2 then measures, for each heading in the "unrelated" bucket, evidence
internal to the collection that it is a legitimate alternative rather than an
error:

  (a) gold_elsewhere     exact (normalized) match against the gold headings
                         of OTHER records in LIBRA-CAT — a professional
                         cataloging source assigns this heading to another
                         work, so it is a real LCSH assignment, not a
                         hallucination;
  (b) family_elsewhere   the heading's main heading (pre-"--" string) equals
                         the main heading of some other record's gold;
  (c) near_semantic      max MiniLM cosine vs. the record's OWN gold headings
                         in [0.60, 0.75) — just below the 0.75 semantic
                         threshold used by LIBRA-CAT, i.e. a near-paraphrase
                         of the cataloger's own heading;
  (d) residual           headings with none of (a)-(c).

Categories (a)-(c) are non-exclusive; the report gives both per-category
counts and the union share (>=1 of a/b/c). The union is a *lower bound* on
the plausible-alternative share of the 932 — it is what the cataloger panel
would adjudicate into "legitimate alternative vs error"; the residual (d) is
the ceiling for genuine error.

Outputs:
  phase1/reports/unmatched_decomposition.json  (+ .md)

Usage:
  HF_HOME=.../.hf_cache python3 phase1/scripts/unmatched_decomposition.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT.parent / "phase2" / "scripts"))

from embeddings import embed  # noqa: E402
from score_libra_cat import (SEMANTIC_TAU, norm, main_heading,  # noqa: E402
                             score_heading, classify_pred_error)

CACHE_PATH = ROOT / "data" / "lcsh_authority_cache.json"
SHIPPED = {"unrelated": 932, "authority_violation": 20,
           "under_specific": 51, "over_specific": 14}
NEAR_BAND = 0.60  # lower edge of the "near-semantic" band


class OfflineAuthority:
    """Replay of the id.loc.gov results from the disk cache (no network)."""

    def __init__(self):
        self.cache = json.loads(CACHE_PATH.read_text())
        self.failures = 0

    def is_valid(self, heading):
        term = norm(main_heading(heading))
        if term not in self.cache:
            self.failures += 1
            return None
        return self.cache[term]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default=str(ROOT / "data" / "libra_cat_predictions.jsonl"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.preds, encoding="utf-8") if l.strip()]
    usable = [r for r in rows if not r.get("error")]

    texts = []
    for r in usable:
        texts += [norm(h) for h in r["gold_subjects"]] + [norm(h) for h in r["pred_subjects"]]
    uniq = sorted({t for t in texts if t})
    print(f"embedding {len(uniq)} unique headings ...", flush=True)
    mat = embed(list(uniq))
    mat = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    index = {t: i for i, t in enumerate(uniq)}

    def sim(a, b):
        if a not in index or b not in index:
            return 0.0
        return float(mat[index[a]] @ mat[index[b]])

    # ---- gold index across OTHER records ----
    gold_by_rec = {r["work_key"]: [norm(h) for h in r["gold_subjects"]] for r in usable}
    all_gold_norm = [g for gs in gold_by_rec.values() for g in gs]
    all_gold_main = {main_heading(g) for g in all_gold_norm}
    gold_elsewhere = {g for gs in gold_by_rec.values() for g in gs}

    authority = OfflineAuthority()
    buckets = {}
    unrelated = []  # (row_idx, pred_heading_norm, work_key, own_gold_norms)

    for i, r in enumerate(usable):
        preds = r["pred_subjects"]
        golds = [norm(h) for h in r["gold_subjects"]]
        for p in preds:
            pn = norm(p)
            if any(score_heading(g, [p], sim) in ("exact", "semantic") for g in golds):
                continue
            bucket = classify_pred_error(p, golds, authority)
            buckets[bucket] = buckets.get(bucket, 0) + 1
            if bucket in ("unrelated", "unrelated_unchecked"):
                unrelated.append((i, pn, r["work_key"], golds))

    print("replicated taxonomy:", json.dumps(buckets, sort_keys=True))
    # Shipped run reported 0 authority lookup failures, so a heading missing
    # from the replay cache was checked live and found valid (True) unless it
    # is one of the 20 False entries -- all of which ARE in the cache. Hence
    # 'unrelated' + 'unrelated_unchecked' == shipped 'unrelated'.
    n_unrel = buckets.get("unrelated", 0) + buckets.get("unrelated_unchecked", 0)
    checks = {"authority_violation": buckets.get("authority_violation", 0),
              "under_specific": buckets.get("under_specific", 0),
              "over_specific": buckets.get("over_specific", 0),
              "unrelated": n_unrel}
    for k, v in SHIPPED.items():
        got = checks[k]
        status = "OK" if got == v else f"MISMATCH (shipped {v})"
        print(f"  {k}: {got}  {status}")
        if got != v:
            print("  -> refusing to decompose on a non-reproducing taxonomy")
            raise SystemExit(1)
    assert authority.failures == 0, f"{authority.failures} headings missing from cache"
    # ---- decomposition ----
    n = len(unrelated)
    a_elsewhere = b_family = c_near = 0
    near_cos = []
    own_gold_max = []
    a_list, b_list = [], []
    for (i, pn, wk, own_golds) in unrelated:
        other_golds = [g for k, gs in gold_by_rec.items() if k != wk for g in gs]
        hit_a = pn in gold_elsewhere and pn in other_golds
        hit_b = main_heading(pn) in all_gold_main and any(
            main_heading(g) == main_heading(pn) for g in other_golds)
        own_cos = [sim(pn, g) for g in own_golds]
        max_own = max(own_cos) if own_cos else 0.0
        hit_c = NEAR_BAND <= max_own < SEMANTIC_TAU
        if hit_a:
            a_elsewhere += 1
            a_list.append(pn)
        if hit_b:
            b_family += 1
            b_list.append(pn)
        if hit_c:
            c_near += 1
        own_gold_max.append(max_own)
        near_cos.append(max_own)

    union = set()
    for (i, pn, wk, own_golds) in unrelated:
        other_golds = [g for k, gs in gold_by_rec.items() if k != wk for g in gs]
        if (pn in gold_elsewhere and pn in other_golds) or \
           (main_heading(pn) in all_gold_main and any(
                main_heading(g) == main_heading(pn) for g in other_golds)) or \
           (NEAR_BAND <= max(sim(pn, g) for g in own_golds or [""]) < SEMANTIC_TAU):
            union.add(pn)

    residual = n - len(union)
    dist = {f"[{0:.2f},{NEAR_BAND:.2f})": 0, f"[{NEAR_BAND:.2f},{SEMANTIC_TAU:.2f})": 0,
            f"[{SEMANTIC_TAU:.2f},1]": 0}
    for c in own_gold_max:
        if c < NEAR_BAND:
            dist[f"[{0:.2f},{NEAR_BAND:.2f})"] += 1
        elif c < SEMANTIC_TAU:
            dist[f"[{NEAR_BAND:.2f},{SEMANTIC_TAU:.2f})"] += 1
        else:
            dist[f"[{SEMANTIC_TAU:.2f},1]"] += 1

    result = {
        "n_unrelated": n,
        "validated_against_shipped": True,
        "evidence": {
            "gold_elsewhere": a_elsewhere,
            "family_elsewhere": b_family,
            "near_semantic_own_gold": c_near,
            "union_any_evidence": len(union),
            "residual_no_evidence": residual,
            "share_any_evidence": round(len(union) / n, 3) if n else None,
        },
        "max_cosine_to_own_gold_distribution": {k: v for k, v in sorted(dist.items())},
        "example_gold_elsewhere": a_list[:8],
        "example_family_elsewhere": b_list[:8],
    }
    out = ROOT / "reports"
    (out / "unmatched_decomposition.json").write_text(
        json.dumps(result, indent=1) + "\n")
    e = result["evidence"]
    md = [
        "# Unmatched-heading decomposition (valid LCSH, no gold match)",
        "",
        f"- Validated: taxonomy reproduced offline exactly against shipped "
        f"(n_unrelated={result['n_unrelated']}; 20 authority violations, "
        f"51 under-, 14 over-specific; 0 cache misses).",
        f"- n = {result['n_unrelated']} headings. Categories are non-exclusive; "
        "the union is a lower bound on plausible legitimate alternatives.",
        "",
        "| Evidence | Count | Share |",
        "|---|---|---|",
        f"| heading is gold LCSH of another record in LIBRA-CAT | {e['gold_elsewhere']} | "
        f"{e['gold_elsewhere']/result['n_unrelated']:.1%} |",
        f"| shares main-heading family with another record's gold | {e['family_elsewhere']} | "
        f"{e['family_elsewhere']/result['n_unrelated']:.1%} |",
        f"| near-semantic to own gold (cos 0.60-0.75) | {e['near_semantic_own_gold']} | "
        f"{e['near_semantic_own_gold']/result['n_unrelated']:.1%} |",
        f"| **any of the above** | **{e['union_any_evidence']}** | "
        f"**{e['share_any_evidence']:.1%}** |",
        f"| residual (no collection-internal evidence) | {e['residual_no_evidence']} | "
        f"{e['residual_no_evidence']/result['n_unrelated']:.1%} |",
        "",
        "Max cosine to own gold:", "",
    ]
    for k, v in result["max_cosine_to_own_gold_distribution"].items():
        md.append(f"- {k}: {v}")
    (out / "unmatched_decomposition.md").write_text("\n".join(md) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
