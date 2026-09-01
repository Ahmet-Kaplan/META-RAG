#!/usr/bin/env python3
"""
join_pilot.py — Pilot: how well do Gutenberg books join to professional
OpenLibrary catalog records by title/author fuzzy matching?

Pipeline per sampled Gutenberg book:
  1. Query OL search API (title + first-author surname).
  2. Confirm candidate with rapidfuzz: title similarity >= threshold AND
     author token overlap >= threshold.
  3. Record match + the OL professional fields (ddc, LCSH subjects, ia ids).

Outputs:
  data/join_pilot_matches.jsonl  — matched books w/ OL fields
  reports/join_pilot_report.md   — match rate + diagnostics

Usage:
  python3 join_pilot.py [--sample 250] [--title-threshold 88] [--author-threshold 60]
"""

import argparse
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
OL_SEARCH = "https://openlibrary.org/search.json"
UA = {"User-Agent": "LIBRA-Eval/0.1 (research; contact: research)"}


def http_get_json(url, retries=3, backoff=2.0):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [warn] GET failed: {url} :: {e}", file=sys.stderr)
                return None
            time.sleep(backoff * (attempt + 1))
    return None


def norm_title(t):
    t = re.sub(r"\s*[:(].*$", "", t)          # drop subtitle
    t = re.sub(r"[^a-z0-9 ]", "", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def surname(name):
    parts = name.replace(",", " ").split()
    return parts[0] if parts else ""


def ol_search(title, author):
    q = urllib.parse.quote(title)
    a = urllib.parse.quote(author)
    url = f"{OL_SEARCH}?title={q}&author={a}&fields=key,title,author_name,first_publish_year,ddc,subject,ia,isbn&limit=5"
    return http_get_json(url)


def author_overlap(gut_authors, ol_authors):
    """Token-level overlap ratio between Gutenberg and OL author strings."""
    g = {w for a in gut_authors for w in a.lower().replace(",", " ").split() if len(w) > 2}
    o = {w for a in ol_authors for w in a.lower().replace(",", " ").split() if len(w) > 2}
    if not g or not o:
        return 0.0
    return len(g & o) / min(len(g), len(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=str(ROOT / "data" / "gutenberg_index.jsonl"))
    ap.add_argument("--sample", type=int, default=250)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--title-threshold", type=int, default=88)
    ap.add_argument("--author-threshold", type=float, default=0.6)
    ap.add_argument("--out", default=str(ROOT / "data" / "join_pilot_matches.jsonl"))
    ap.add_argument("--report", default=str(ROOT / "reports" / "join_pilot_report.md"))
    args = ap.parse_args()

    with open(args.index, encoding="utf-8") as f:
        books = [json.loads(l) for l in f if l.strip()]
    # prefer books that have a plaintext URL and were downloaded often
    books.sort(key=lambda b: (b.get("plaintext_url") is not None, b.get("download_count") or 0), reverse=True)
    sample = random.Random(args.seed).sample(books, min(args.sample, len(books)))

    matches, misses, api_failures = [], [], 0
    for i, b in enumerate(sample):
        title = b.get("title") or ""
        authors = b.get("authors") or []
        if not title or not authors:
            misses.append({"gutenberg_id": b.get("gutenberg_id"), "reason": "no title/author"})
            continue
        data = ol_search(norm_title(title)[:40], surname(authors[0]))
        if not data:
            api_failures += 1
            continue
        best = None
        for cand in data.get("docs", []):
            cand_title = cand.get("title") or ""
            cand_authors = cand.get("author_name") or []
            t_ratio = fuzz.ratio(norm_title(title), norm_title(cand_title))
            a_ov = author_overlap(authors, cand_authors)
            if t_ratio >= args.title_threshold and a_ov >= args.author_threshold:
                best = cand
                break
        if best:
            ddcs = [d for d in (best.get("ddc") or []) if re.match(r"^\d{3}(\.\d+)?$", str(d))]
            ol_subs = best.get("subject") or []
            matches.append({
                "gutenberg_id": b["gutenberg_id"],
                "gutenberg_title": title,
                "gutenberg_authors": authors,
                "gutenberg_subjects": b.get("subjects") or [],   # LCSH-format (Gutenberg)
                "work_key": best.get("key"),
                "ol_title": best.get("title"),
                "ol_authors": best.get("author_name"),
                "ol_subjects": ol_subs,
                "ol_lcsh": [s for s in ol_subs if " -- " in s],  # LCSH-format (OL)
                "first_publish_year": best.get("first_publish_year"),
                "ddc": ddcs,
                "ia_ids": best.get("ia") or [],
                "isbn": (best.get("isbn") or [])[:3],
                "title_ratio": t_ratio,
                "author_overlap": round(a_ov, 2),
                "plaintext_url": b.get("plaintext_url"),
                "download_count": b.get("download_count"),
            })
        else:
            misses.append({"gutenberg_id": b.get("gutenberg_id"), "title": title, "reason": "no candidate above thresholds"})
        if (i + 1) % 50 == 0:
            print(f"  processed {i+1}/{len(sample)} (matches={len(matches)})")
        time.sleep(0.4)

    with open(args.out, "w", encoding="utf-8") as f:
        for m in matches:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    n = len(sample)
    match_rate = 100 * len(matches) / max(1, n)
    with_ddc = sum(1 for m in matches if m["ddc"])
    with_gut_lcsh = sum(1 for m in matches if any(" -- " in s for s in m["gutenberg_subjects"]))
    with_ol_lcsh = sum(1 for m in matches if m["ol_lcsh"])
    report = f"""# Join Pilot Report (Gutenberg -> OpenLibrary)

- Sample size: {n} Gutenberg books (English, public domain)
- Matched: {len(matches)} ({match_rate:.1f}%)
- Unmatched: {len(misses)}
- API failures: {api_failures}
- Matched books with DDC (OL, MARC-derived): {with_ddc} ({100*with_ddc/max(1,len(matches)):.0f}%)
- Matched books with LCSH-format subjects from Gutenberg: {with_gut_lcsh} ({100*with_gut_lcsh/max(1,len(matches)):.0f}%)
- Matched books with LCSH-format subjects from OL: {with_ol_lcsh} ({100*with_ol_lcsh/max(1,len(matches)):.0f}%)

## Interpretation

The match rate estimates how many Gutenberg works we can enrich with professional
catalog metadata. LIBRA-CAT ground truth = Gutenberg LCSH-format subjects
+ OL MARC-derived DDC; LIBRA-QA = the same matched corpus with full text from
Gutenberg. A match rate >= 40% means the corpus build is viable from Gutenberg +
OpenLibrary alone; below that, we expand the Gutenberg index (gutendex) and/or
add Internet Archive items.

## Sample of matches

| Gutenberg | OL work | DDC | #GutLCSH | #OLLCSH |
|---|---|---|---|---|
"""
    for m in matches[:12]:
        report += (f"| {m['gutenberg_id']} {str(m['gutenberg_title'])[:40]} | {m['work_key']} | "
                   f"{','.join(m['ddc'][:3]) or '-'} | "
                   f"{sum(1 for s in m['gutenberg_subjects'] if ' -- ' in s)} | {len(m['ol_lcsh'])} |\n")

    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nMatches: {len(matches)}/{n} ({match_rate:.1f}%)")
    print(f"Report -> {args.report}")


if __name__ == "__main__":
    main()
