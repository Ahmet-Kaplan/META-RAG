#!/usr/bin/env python3
"""
score_libra_cat.py — Score LLM cataloging output against LIBRA-CAT gold.

Implements the scoring protocol the paper describes:

  Subject headings (LCSH), multi-level, best level per gold heading:
    exact       normalized string match
    semantic    cosine >= SEMANTIC_TAU over MiniLM embeddings
    acceptable  same main heading (text before the first " -- "), i.e. a
                correct broader heading with different subdivision
    miss        none of the above

  DDC, top-k over the gold set (OL aggregates editions -> any gold match):
    exact       full string match against any gold DDC
    class3      first three digits match any gold DDC
    class1      first digit (top-level class) matches any gold DDC

  Error taxonomy, applied to predicted headings that matched no gold:
    authority_violation   not found in LC subject authorities (id.loc.gov)
    over_specific         main heading matches gold but adds subdivisions
    under_specific        gold main heading is an extension of the prediction
    unrelated             valid LCSH, but unrelated to any gold heading

  DDC errors:
    wrong_branch          top-level class differs from every gold DDC

Authority validation calls id.loc.gov (cached on disk). With --no-authority
the authority_violation category is reported as "not checked" rather than
silently folded into another bucket.

Usage:
  python3 score_libra_cat.py [--no-authority]
"""

import argparse
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "phase2" / "scripts"))

logger = logging.getLogger(__name__)

SEMANTIC_TAU = 0.75          # cosine threshold for "semantically equivalent"
AUTHORITY_URL = "https://id.loc.gov/authorities/{f}/suggest2?q={q}&count=5"
AUTHORITY_FILES = ("subjects", "names")  # names: persons/corporate bodies used as subjects
CACHE_PATH = ROOT / "data" / "lcsh_authority_cache.json"


# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------

def norm(h: str) -> str:
    """Normalize a heading for comparison: case, punctuation, subdivision form."""
    h = h.lower().strip().rstrip(".")
    h = re.sub(r"\s*--\s*", " -- ", h)
    h = re.sub(r"[^\w\s\-]", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def main_heading(h: str) -> str:
    return norm(h).split(" -- ")[0].strip()


def raw_main_heading(h: str) -> str:
    """Main heading in its original form, for authority lookup.

    Only the main heading is looked up: LCSH subdivisions are free-floating and
    most valid main-heading + subdivision strings have no single pre-coordinated
    authority record, so querying the full string reports valid headings as
    invented.
    """
    return re.split(r"\s*--\s*", h.strip())[0].strip().rstrip(".")


def ddc_class3(d: str) -> str:
    digits = re.sub(r"[^\d]", "", d or "")
    return digits[:3]


# --------------------------------------------------------------------------
# semantic equivalence
# --------------------------------------------------------------------------

def build_semantic_matcher(all_texts: Sequence[str]):
    """Return fn(a, b) -> cosine similarity, or None if embeddings unavailable."""
    try:
        import numpy as np
        from embeddings import embed
    except Exception as exc:
        logger.warning("embeddings unavailable (%s); semantic level disabled", exc)
        return None
    uniq = sorted({t for t in all_texts if t})
    logger.info("Embedding %d unique headings for semantic scoring", len(uniq))
    mat = embed(list(uniq))
    mat = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    index = {t: i for i, t in enumerate(uniq)}

    def sim(a: str, b: str) -> float:
        if a not in index or b not in index:
            return 0.0
        return float(mat[index[a]] @ mat[index[b]])

    return sim


# --------------------------------------------------------------------------
# LC authority validation
# --------------------------------------------------------------------------

class AuthorityChecker:
    """Checks whether a heading exists in LC subject authorities. Disk-cached."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.cache: Dict[str, bool] = {}
        if CACHE_PATH.exists():
            try:
                self.cache = json.loads(CACHE_PATH.read_text())
            except json.JSONDecodeError:
                logger.warning("authority cache corrupt; starting fresh")
        self.checked = 0
        self.failures = 0

    def is_valid(self, heading: str) -> Optional[bool]:
        """True/False, or None if the check could not be performed."""
        if not self.enabled:
            return None
        term = raw_main_heading(heading)
        if not term:
            return None
        key = norm(term)
        if key in self.cache:
            return self.cache[key]
        for auth_file in AUTHORITY_FILES:
            hit = self._query(auth_file, term)
            if hit is None:
                return None            # lookup failed; do not guess
            if hit:
                self.cache[key] = True
                return True
        self.cache[key] = False
        return False

    def _query(self, auth_file: str, term: str) -> Optional[bool]:
        url = AUTHORITY_URL.format(f=auth_file, q=urllib.parse.quote(term))
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=20) as resp:
                    data = json.loads(resp.read())
                self.checked += 1
                return bool(data.get("hits"))
            except Exception as exc:
                if attempt == 2:
                    self.failures += 1
                    logger.warning("authority lookup failed for %r: %s", term, exc)
                    return None
                time.sleep(1.5 * (attempt + 1))
        return None

    def save(self) -> None:
        CACHE_PATH.write_text(json.dumps(self.cache, indent=0))


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def score_heading(gold: str, preds: Sequence[str], sim) -> str:
    """Best level at which `gold` is covered by any prediction."""
    g = norm(gold)
    if any(norm(p) == g for p in preds):
        return "exact"
    if sim is not None and any(sim(norm(p), g) >= SEMANTIC_TAU for p in preds):
        return "semantic"
    gm = main_heading(gold)
    if gm and any(main_heading(p) == gm for p in preds):
        return "acceptable"
    return "miss"


def classify_pred_error(pred: str, golds: Sequence[str], authority) -> str:
    """Taxonomy bucket for a predicted heading that matched no gold heading."""
    valid = authority.is_valid(pred)
    if valid is False:
        return "authority_violation"
    pm = main_heading(pred)
    for g in golds:
        gm = main_heading(g)
        if pm == gm:
            # same concept, different specificity
            if len(norm(pred).split(" -- ")) > len(norm(g).split(" -- ")):
                return "over_specific"
            return "under_specific"
    if valid is None:
        return "unrelated_unchecked"
    return "unrelated"


def score_ddc(pred: Optional[str], golds: Sequence[str]) -> str:
    if not pred or not golds:
        return "no_prediction" if not pred else "no_gold"
    if any(pred.strip() == g.strip() for g in golds):
        return "exact"
    p3 = ddc_class3(pred)
    if p3 and any(ddc_class3(g) == p3 for g in golds):
        return "class3"
    if p3 and any(ddc_class3(g)[:1] == p3[:1] for g in golds):
        return "class1"
    return "wrong_branch"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default=str(ROOT / "data" / "libra_cat_predictions.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "libra_cat_eval"))
    ap.add_argument("--no-authority", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.preds, encoding="utf-8") if l.strip()]
    usable = [r for r in rows if not r.get("error")]
    logger.info("Scoring %d predictions (%d generation failures excluded)",
                len(usable), len(rows) - len(usable))

    texts = []
    for r in usable:
        texts += [norm(h) for h in r["gold_subjects"]] + [norm(h) for h in r["pred_subjects"]]
    sim = build_semantic_matcher(texts)
    authority = AuthorityChecker(enabled=not args.no_authority)

    gold_levels = {"exact": 0, "semantic": 0, "acceptable": 0, "miss": 0}
    pred_errors: Dict[str, int] = {}
    ddc_levels: Dict[str, int] = {}
    n_gold = n_pred = 0
    recs_any_exact = 0

    for i, r in enumerate(usable):
        preds = r["pred_subjects"]
        golds = r["gold_subjects"]
        n_gold += len(golds)
        n_pred += len(preds)
        levels = [score_heading(g, preds, sim) for g in golds]
        for lv in levels:
            gold_levels[lv] += 1
        if "exact" in levels:
            recs_any_exact += 1
        for p in preds:
            if any(score_heading(g, [p], sim) in ("exact", "semantic") for g in golds):
                continue
            bucket = classify_pred_error(p, golds, authority)
            pred_errors[bucket] = pred_errors.get(bucket, 0) + 1
        if r["gold_ddc"]:
            lv = score_ddc(r.get("pred_ddc"), r["gold_ddc"])
            ddc_levels[lv] = ddc_levels.get(lv, 0) + 1
        if (i + 1) % 100 == 0:
            logger.info("  scored %d/%d", i + 1, len(usable))
            authority.save()

    authority.save()

    n_ddc = sum(ddc_levels.values())
    cum = {}
    running = 0
    for lv in ("exact", "semantic", "acceptable"):
        running += gold_levels[lv]
        cum[lv] = running

    result = {
        "n_records": len(usable),
        "n_generation_failures": len(rows) - len(usable),
        "n_gold_headings": n_gold,
        "n_pred_headings": n_pred,
        "semantic_tau": SEMANTIC_TAU,
        "authority_checked": authority.enabled,
        "authority_lookup_failures": authority.failures,
        "subject_recall_by_level": gold_levels,
        "subject_recall_cumulative": {
            "exact": round(cum["exact"] / n_gold, 3),
            "exact_or_semantic": round(cum["semantic"] / n_gold, 3),
            "exact_semantic_or_acceptable": round(cum["acceptable"] / n_gold, 3),
        },
        "records_with_any_exact_heading": round(recs_any_exact / len(usable), 3),
        "predicted_heading_errors": pred_errors,
        "ddc": {"n": n_ddc, "levels": ddc_levels,
                "exact": round(ddc_levels.get("exact", 0) / n_ddc, 3) if n_ddc else None,
                "class3": round((ddc_levels.get("exact", 0) + ddc_levels.get("class3", 0)) / n_ddc, 3) if n_ddc else None},
    }

    out_json = Path(args.out).with_suffix(".json")
    out_json.write_text(json.dumps(result, indent=2))
    logger.info("Wrote %s", out_json)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
