#!/usr/bin/env python3
"""
fetch_gutenberg_index.py — Build a lightweight Gutenberg metadata index for the
LIBRA-QA corpus. Uses the gutendex JSON API (https://gutendex.com) so we never
download the multi-GB RDF feed: metadata only (~few MB), full text fetched
on demand from gutenberg.org later.

Pulls English, public-domain books (largest download counts first, then
continues through the catalog) and writes phase1/data/gutenberg_index.jsonl.

Usage:
  python3 fetch_gutenberg_index.py [--max-books 2500] [--out ../data/gutenberg_index.jsonl]
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # phase1/
GUTENDEX = "https://gutendex.com/books"
UA = {"User-Agent": "LIBRA-Eval/0.1 (research; contact: research)"}


def http_get_json(url, retries=5, backoff=2.0):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [warn] GET failed after {retries} tries: {url} :: {e}", file=sys.stderr)
                return None
            time.sleep(backoff * (attempt + 1))
    return None


def plaintext_url(formats):
    """Prefer UTF-8 plain text over HTML/other formats."""
    if not formats:
        return None
    for key in ("text/plain; charset=utf-8", "text/plain; charset=us-ascii", "text/plain"):
        if key in formats:
            return formats[key]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-books", type=int, default=2500)
    ap.add_argument("--out", default=str(ROOT / "data" / "gutenberg_index.jsonl"))
    args = ap.parse_args()

    records, url, guard = [], GUTENDEX + "?languages=en&copyright=false", 0
    seen_ids = set()
    while url and len(records) < args.max_books and guard < 500:
        guard += 1
        data = http_get_json(url)
        if not data:
            # transient failure: pause and retry the same page
            time.sleep(10)
            data = http_get_json(url)
            if not data:
                print(f"  [stop] giving up at page {guard} after retries", file=sys.stderr)
                break
        for b in data.get("results", []):
            if b.get("id") in seen_ids:
                continue
            seen_ids.add(b.get("id"))
            txt = plaintext_url(b.get("formats") or {})
            records.append({
                "gutenberg_id": b.get("id"),
                "title": b.get("title"),
                "authors": [a.get("name") for a in (b.get("authors") or [])],
                "subjects": b.get("subjects") or [],
                "bookshelves": b.get("bookshelves") or [],
                "download_count": b.get("download_count"),
                "languages": b.get("languages") or [],
                "copyright": b.get("copyright"),
                "plaintext_url": txt,
            })
            if len(records) >= args.max_books:
                break
        url = data.get("next")
        time.sleep(0.3)
        # checkpoint so a crash keeps earlier pages
        if guard % 20 == 0:
            with open(args.out, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  checkpoint: {len(records)} books at page {guard}")

    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_txt = sum(1 for r in records if r["plaintext_url"])
    print(f"Wrote {len(records)} books -> {args.out}")
    print(f"  with plaintext URL: {n_txt} ({100*n_txt/max(1,len(records)):.0f}%)")
    print(f"  languages: {sorted({l for r in records for l in r['languages']})}")


if __name__ == "__main__":
    main()
