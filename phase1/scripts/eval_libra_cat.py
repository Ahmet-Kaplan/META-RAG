#!/usr/bin/env python3
"""
eval_libra_cat.py — Run LLM cataloging over LIBRA-CAT records.

The model sees only what a minimal catalog record carries (title, author,
year) and must propose LCSH subject headings and a DDC number. This is the
retrospective-conversion setting: enriching minimal records, which is the
case libraries actually ask about. Full-text conditioning is a separate
condition and is NOT run here (see --help note).

Gold answers are never shown to the model.

Outputs:
  phase1/data/libra_cat_predictions.jsonl   (one row per record)

Usage:
  python3 eval_libra_cat.py [--limit N] [--workers 8] [--resume]
"""

import argparse
import json
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

from llm_client import chat_json

ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)

SYSTEM = (
    "You are a professional cataloger assigning subject access to a library "
    "catalog record. You follow Library of Congress Subject Headings (LCSH) "
    "form and Dewey Decimal Classification practice. You never invent "
    "headings you are not confident are valid LCSH."
)

PROMPT = """Assign subject access for this catalog record.

Title: {title}
Author: {author}
Year: {year}

Provide:
1. "subjects": 1-4 Library of Congress Subject Headings in standard LCSH form,
   using " -- " between subdivisions (e.g. "Governesses -- Fiction").
2. "ddc": a single Dewey Decimal Classification number appropriate for the work.

Respond ONLY with JSON:
{{"subjects": ["...", "..."], "ddc": "..."}}"""


def build_prompt(rec: Dict) -> str:
    authors = rec.get("author_name") or []
    return PROMPT.format(
        title=rec.get("title") or "(unknown)",
        author="; ".join(authors) if authors else "(unknown)",
        year=rec.get("first_publish_year") or "(unknown)",
    )


def catalog_one(rec: Dict) -> Dict:
    """Ask the model to catalog one record. Never raises; records failures."""
    out = {
        "work_key": rec["work_key"],
        "gutenberg_id": rec.get("gutenberg_id"),
        "title": rec.get("title"),
        "tier": rec.get("tier"),
        "gold_subjects": rec.get("gold_subjects") or [],
        "gold_ddc": rec.get("ddc") or [],
        "pred_subjects": [],
        "pred_ddc": None,
        "error": None,
    }
    try:
        resp = chat_json(build_prompt(rec), system=SYSTEM,
                         temperature=0.0, max_tokens=300)
    except Exception as exc:  # network/API/parse failure
        out["error"] = f"{type(exc).__name__}: {exc}"
        logger.warning("cataloging failed for %s: %s", rec["work_key"], exc)
        return out

    subs = resp.get("subjects")
    if isinstance(subs, str):
        subs = [subs]
    out["pred_subjects"] = [s.strip() for s in (subs or []) if isinstance(s, str) and s.strip()]
    ddc = resp.get("ddc")
    out["pred_ddc"] = str(ddc).strip() if ddc not in (None, "") else None
    if not out["pred_subjects"] and out["pred_ddc"] is None:
        out["error"] = "empty response"
    return out


def load_done(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return {}
    done = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if not r.get("error"):          # retry previously failed rows
                done[r["work_key"]] = r
    return done


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=str(ROOT / "data" / "libra_cat_records_scaled.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "libra_cat_predictions.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    with open(args.records, encoding="utf-8") as f:
        recs: List[Dict] = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        recs = recs[: args.limit]

    out_path = Path(args.out)
    done = load_done(out_path) if args.resume else {}
    pending = [r for r in recs if r["work_key"] not in done]
    logger.info("Cataloging %d of %d records (%d already done), %d workers",
                len(pending), len(recs), len(done), args.workers)

    lock = threading.Lock()
    results: List[Dict] = list(done.values())
    completed = [0]

    def work(rec: Dict) -> None:
        row = catalog_one(rec)
        with lock:
            results.append(row)
            completed[0] += 1
            if completed[0] % 50 == 0:
                logger.info("  %d/%d", completed[0], len(pending))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, pending))

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    failed = sum(1 for r in results if r.get("error"))
    logger.info("Wrote %d predictions -> %s (%d failed)", len(results), out_path, failed)


if __name__ == "__main__":
    main()
