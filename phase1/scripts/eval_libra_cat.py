#!/usr/bin/env python3
"""
eval_libra_cat.py — Run LLM cataloging over LIBRA-CAT records.

The model sees a minimal catalog record (title, author, year) and must propose
LCSH subject headings and a DDC number. This is the retrospective-conversion
setting: enriching minimal records, which is the case libraries actually ask
about.

Two conditions are supported (E3, plan/e3_model_comparison.md):
  sparse    (default) title/author/year only — the shipped LIBRA-CAT protocol
  fulltext  the same input plus a head-of-text excerpt from Gutenberg

Any provider in llm_client.PROVIDERS can run a cell (deepseek, gemini,
openai_compatible), so E3 can compare model tiers with one harness.

Gold answers are never shown to the model.

Outputs (one row per record, with model/condition recorded for provenance):
  --out  (default phase1/data/libra_cat_predictions.jsonl for sparse/deepseek)

Usage:
  # shipped behaviour (unchanged defaults)
  python3 eval_libra_cat.py --resume

  # an E3 cell
  python3 eval_libra_cat.py --provider gemini --model gemini-2.5-pro \
      --condition fulltext --out ../data/e3/preds_gemini_fulltext.jsonl --resume
"""

import argparse
import json
import logging
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

from llm_client import chat_json

ROOT = Path(__file__).resolve().parent.parent
# reuse the corpus downloader (stdlib-only)
sys.path.insert(0, str(ROOT.parent / "phase2" / "scripts"))
from corpus import download_text  # noqa: E402

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
{content}
Provide:
1. "subjects": 1-4 Library of Congress Subject Headings in standard LCSH form,
   using " -- " between subdivisions (e.g. "Governesses -- Fiction").
2. "ddc": a single Dewey Decimal Classification number appropriate for the work.

Respond ONLY with JSON:
{{"subjects": ["...", "..."], "ddc": "..."}}"""

CONTENT_BLOCK = """
Content excerpt (for cataloging context):
{excerpt}
"""

EXCERPT_CHARS = 1500

# Project Gutenberg front matter: the modern format delimits the work with
# *** START/END OF ... ***; older files only carry a metadata block. Note that
# corpus.clean_text removes the delimiters but leaves the license block ABOVE
# them, so an excerpt taken from its output is mostly licensing text — hence
# this explicit body extraction.
_START_RE = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.S | re.I)
_END_RE = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*", re.S | re.I)
_FM_RE = re.compile(
    r"^(Title|Author|Release date|Most recently updated|Language|"
    r"Other information and formats|Credits|Character set encoding|Encoding|"
    r"Produced by|Transcriber|Illustrator|Editor|Translator)\s*:", re.I)


def gutenberg_body(raw: str) -> str:
    """Return the work's own text, with the PG license/metadata block removed."""
    m = _START_RE.search(raw)
    if m:
        body = raw[m.end():]
    else:
        lines = raw.splitlines()
        last = None
        for i, ln in enumerate(lines[:120]):
            if _FM_RE.match(ln.strip()):
                last = i
        body = "\n".join(lines[last + 1:]) if last is not None else raw
    return _END_RE.sub("", body)


def build_prompt(rec: Dict, condition: str = "sparse",
                 excerpt: Optional[str] = None) -> str:
    authors = rec.get("author_name") or []
    content = ""
    if condition == "fulltext" and excerpt:
        content = CONTENT_BLOCK.format(excerpt=excerpt)
    return PROMPT.format(
        title=rec.get("title") or "(unknown)",
        author="; ".join(authors) if authors else "(unknown)",
        year=rec.get("first_publish_year") or "(unknown)",
        content=content,
    )


def get_excerpt(rec: Dict, cache_dir: Path,
                chars: int = EXCERPT_CHARS) -> Optional[str]:
    """Head-of-text excerpt for a work, cached per work_key.

    Returns None when the record has no plaintext URL or the download fails;
    the caller records that as a per-row error rather than silently running
    a sparse prompt under a full-text label.
    """
    wk = rec["work_key"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{wk.replace('/', '_')}.txt"
    if cache_file.exists():
        cached = cache_file.read_text(encoding="utf-8", errors="replace").strip()
        return cached or None
    url = rec.get("plaintext_url")
    if not url:
        return None
    raw = download_text(url)
    if not raw:
        return None
    excerpt = " ".join(gutenberg_body(raw).split())[:chars]
    if not excerpt:
        return None
    cache_file.write_text(excerpt, encoding="utf-8")
    return excerpt


def catalog_one(rec: Dict, condition: str, provider: str, model: Optional[str],
                excerpt: Optional[str]) -> Dict:
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
        "provider": provider,
        "model": model or "(provider default)",
        "condition": condition,
        "error": None,
    }
    if condition == "fulltext" and not excerpt:
        out["error"] = "no_text_available"
        return out
    try:
        resp = chat_json(build_prompt(rec, condition, excerpt),
                         system=SYSTEM, temperature=0.0, max_tokens=300,
                         provider=provider, model=model)
    except Exception as exc:  # network/API/parse failure
        out["error"] = f"{type(exc).__name__}: {exc}"
        logger.warning("cataloging failed for %s: %s", rec["work_key"], exc)
        return out

    subs = resp.get("subjects")
    if isinstance(subs, str):
        subs = [subs]
    out["pred_subjects"] = [s.strip() for s in (subs or [])
                            if isinstance(s, str) and s.strip()]
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
    ap.add_argument("--out", default="",
                    help="default: libra_cat_predictions.jsonl for "
                         "sparse/deepseek; otherwise preds_<provider>_<condition>.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--provider", default="deepseek",
                    help="llm_client provider: deepseek | gemini | openai_compatible")
    ap.add_argument("--model", default="", help="model name (default: provider default)")
    ap.add_argument("--condition", choices=["sparse", "fulltext"], default="sparse")
    ap.add_argument("--text-cache", default=str(ROOT / "data" / "text_cache"),
                    help="cache dir for Gutenberg excerpts (fulltext condition)")
    ap.add_argument("--excerpt-chars", type=int, default=EXCERPT_CHARS)
    args = ap.parse_args()

    model = args.model or None
    out_path = Path(args.out) if args.out else Path(
        str(ROOT / "data" / "libra_cat_predictions.jsonl")
        if (args.condition == "sparse" and args.provider == "deepseek")
        else str(ROOT / "data" / "e3" / f"preds_{args.provider}_{args.condition}.jsonl"))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.records, encoding="utf-8") as f:
        recs: List[Dict] = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        recs = recs[: args.limit]

    done = load_done(out_path) if args.resume else {}
    pending = [r for r in recs if r["work_key"] not in done]
    logger.info("Cataloging %d of %d records (%d already done), %d workers, "
                "provider=%s model=%s condition=%s",
                len(pending), len(recs), len(done), args.workers,
                args.provider, model or "(default)", args.condition)

    lock = threading.Lock()
    results: List[Dict] = list(done.values())
    completed = [0]

    def work(rec: Dict) -> None:
        excerpt = None
        if args.condition == "fulltext":
            excerpt = get_excerpt(rec, Path(args.text_cache), args.excerpt_chars)
        row = catalog_one(rec, args.condition, args.provider, model, excerpt)
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
    no_text = sum(1 for r in results if r.get("error") == "no_text_available")
    logger.info("Wrote %d predictions -> %s (%d failed, %d lacked text)",
                len(results), out_path, failed, no_text)


if __name__ == "__main__":
    main()
