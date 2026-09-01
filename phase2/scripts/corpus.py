#!/usr/bin/env python3
"""
corpus.py — Build the META-RAG retrieval corpus from matched books.

Input : phase1/data/join_pilot_matches.jsonl (or a subset)
Output: phase2/data/corpus.jsonl
  each record:
    {
      "work_key", "gutenberg_id", "title", "authors", "year",
      "subjects" (LCSH-format), "ddc",
      "chunks": [ {"chunk_id", "text"} ],        # full-text chunks (on demand)
      "plaintext_url"
    }

Full text is downloaded on demand from Gutenberg and chunked (~300 words,
50-word overlap). Use --limit to keep it small for demos; use --max-books to
cap corpus size. Chunks are NOT persisted by default (only metadata + counts)
unless --keep-text is set, to save disk.
"""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "LIBRA-Eval/0.1 (research; contact: research)"}
CHUNK_WORDS = 300
CHUNK_OVERLAP = 50


def download_text(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [warn] download failed: {url} :: {e}", file=__import__('sys').stderr)
                return None
            time.sleep(2 * (attempt + 1))
    return None


def clean_text(raw):
    # strip Gutenberg header/footer boilerplate
    raw = re.sub(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", "", raw, flags=re.S | re.I)
    raw = re.sub(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*", "", raw, flags=re.S | re.I)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def chunk_text(text, words=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
    toks = text.split(" ")
    out = []
    i = 0
    while i < len(toks):
        out.append(" ".join(toks[i:i + words]))
        i += words - overlap
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", default=str(ROOT.parent / "phase1" / "data" / "join_pilot_matches.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "corpus.jsonl"))
    ap.add_argument("--limit", type=int, default=40, help="max books (0 = all)")
    ap.add_argument("--resume", action="store_true", help="skip books already in --out")
    ap.add_argument("--workers", type=int, default=5, help="concurrent downloads")
    ap.add_argument("--delay", type=float, default=0.5, help="per-worker politeness delay")
    ap.add_argument("--min-chars", type=int, default=20000, help="skip texts shorter than this")
    ap.add_argument("--keep-text", action="store_true", default=True,
                    help="persist full text per record (needed by index & generation)")
    args = ap.parse_args()

    with open(args.matches, encoding="utf-8") as f:
        matches = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        matches = matches[: args.limit]

    records, skipped = [], 0
    n_written, total_chunks = 0, 0
    done_ids = set()
    if args.resume and Path(args.out).exists():
        for line in open(args.out, encoding="utf-8"):
            if line.strip():
                done_ids.add(json.loads(line)["gutenberg_id"])
        print(f"resuming: {len(done_ids)} books already written", flush=True)
    out_fh = open(args.out, "a" if args.resume else "w", encoding="utf-8")
    n_written = len(done_ids)
    # Downloads dominate wall time and are pure I/O, so fetch concurrently.
    # Writes are serialised behind a lock; each record is flushed as it lands so
    # an interrupted run resumes rather than restarts.
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock()
    counters = {"written": n_written, "skipped": 0, "chunks": 0}

    def fetch_one(m):
        if m.get("gutenberg_id") in done_ids:
            return
        url = m.get("plaintext_url")
        if not url:
            with lock:
                counters["skipped"] += 1
            return
        raw = download_text(url)
        if not raw:
            with lock:
                counters["skipped"] += 1
            return
        text = clean_text(raw)
        if len(text) < args.min_chars:
            with lock:
                counters["skipped"] += 1
            return
        chunks = chunk_text(text)
        rec = {
            "work_key": m["work_key"],
            "gutenberg_id": m["gutenberg_id"],
            "title": m.get("gutenberg_title") or m.get("ol_title"),
            "authors": m.get("gutenberg_authors") or m.get("ol_authors") or [],
            "year": m.get("first_publish_year"),
            "subjects": [s2 for s2 in (m.get("gutenberg_subjects") or []) if " -- " in s2],
            "ddc": m.get("ddc") or [],
            "plaintext_url": url,
            "n_chunks": len(chunks),
            "n_chars": len(text),
            "chunks": [{"chunk_id": f"{m['gutenberg_id']}-{j}", "text": c} for j, c in enumerate(chunks)]
                     if args.keep_text else [{"chunk_id": f"{m['gutenberg_id']}-{j}"} for j in range(len(chunks))],
        }
        with lock:
            out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fh.flush()
            counters["written"] += 1
            counters["chunks"] += rec["n_chunks"]
            if counters["written"] % 50 == 0:
                print(f"  corpus: {counters['written']} books ({counters['skipped']} skipped)", flush=True)
        time.sleep(args.delay)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(fetch_one, matches))
    skipped = counters["skipped"]
    total_chunks = counters["chunks"]
    n_written = counters["written"]

    out_fh.close()
    records = [None] * n_written
    print(f"\nCorpus: {len(records)} books, {total_chunks} chunks -> {args.out}")
    print(f"Skipped (no text/too short): {skipped}")


if __name__ == "__main__":
    main()
