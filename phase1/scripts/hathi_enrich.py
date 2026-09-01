#!/usr/bin/env python3
"""
hathi_enrich.py — Enrich the 224 joined books with HathiTrust professional MARC.

For each match (up to 3 ISBNs), query the HathiTrust /full/ bibliographic API
and parse the returned MARC21 XML (stdlib ElementTree):
  - 650  -> LCSH subject headings (subfields a x y z v)
  - 082/092 -> DDC numbers
  - 050 -> LCC
  - 100/110/245 -> author/title sanity fields
Merge subjects/DDC across all records returned for that ISBN.

Outputs:
  data/hathi_enrichment.jsonl  (one line per matched book with HT data)
  reports/hathi_enrichment_stats.json

Usage:
  python3 hathi_enrich.py [--matches ../data/join_pilot_matches.jsonl]
"""

import argparse
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
NS = {"m": "http://www.loc.gov/MARC21/slim"}
API = "https://catalog.hathitrust.org/api/volumes/full/{idtype}/{id}.json"
OL_KEY = "https://openlibrary.org/search.json?q=key%3A{key}&fields=key,lccn,oclc&limit=1"


def ol_identifiers(work_key):
    """Fetch LCCN + OCLC identifiers for an OL work key (for HT lookup)."""
    try:
        raw = http_get(OL_KEY.format(key=urllib.parse.quote(work_key)))
        if not raw:
            return [], []
        docs = (json.loads(raw) or {}).get("docs") or []
        if not docs:
            return [], []
        d = docs[0]
        return (d.get("lccn") or [])[:3], (d.get("oclc") or [])[:3]
    except Exception:
        return [], []


def http_get(url, retries=2, backoff=1.5):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [warn] GET failed: {url} :: {e}", file=sys.stderr)
                return None
            time.sleep(backoff * (attempt + 1))
    return None


def marc_fields(marc_xml, tag):
    """Return list of {code: subfield-text} dicts for a datafield tag."""
    out = []
    try:
        root = ET.fromstring(marc_xml)
    except ET.ParseError:
        return out
    for df in root.findall(f".//m:datafield[@tag='{tag}']", NS):
        subs = {}
        for sf in df.findall("m:subfield", NS):
            code = sf.get("code")
            subs[code] = (subs.get(code, "") + " " + (sf.text or "")).strip()
        if subs:
            out.append(subs)
    return out


def join_subfields(subs, codes, sep=" -- "):
    return sep.join(subs[c] for c in codes if c in subs).strip()


def parse_record(marc_xml):
    """Extract LCSH (650), DDC (082/092), LCC (050), author, title from MARC."""
    lcsh = []
    for s in marc_fields(marc_xml, "650"):
        h = join_subfields(s, ["a", "x", "y", "z", "v"])
        if h:
            lcsh.append(h)
    ddc = [s.get("a") for s in marc_fields(marc_xml, "082") if s.get("a")]
    ddc += [s.get("a") for s in marc_fields(marc_xml, "092") if s.get("a")]
    lcc = [s.get("a") for s in marc_fields(marc_xml, "050") if s.get("a")]
    authors = [s.get("a") for s in marc_fields(marc_xml, "100") + marc_fields(marc_xml, "110") if s.get("a")]
    titles = [s.get("a") for s in marc_fields(marc_xml, "245") if s.get("a")]
    return {"lcsh": lcsh, "ddc": ddc, "lcc": lcc, "authors": authors, "titles": titles}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", default=str(ROOT / "data" / "join_pilot_matches.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "hathi_enrichment.jsonl"))
    ap.add_argument("--max-isbns", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    with open(args.matches, encoding="utf-8") as f:
        matches = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        matches = matches[: args.limit]

    enriched, empty = [], 0
    out_fh = open(args.out, "w", encoding="utf-8")
    try:
        for i, m in enumerate(matches):
            isbns = [b for b in (m.get("isbn") or []) if b][:2]
            lccns, oclcs = ol_identifiers(m.get("work_key"))
            merged = {"lcsh": [], "ddc": [], "lcc": [], "authors": [], "titles": [], "oclcs": [], "record_urls": []}
            found = False
            for idtype, ids in (("lccn", lccns), ("oclc", oclcs), ("isbn", isbns)):
                for ident in ids:
                    raw = http_get(API.format(idtype=idtype, id=ident))
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    recs = data.get("records") or {}
                    for oclc, rec in recs.items():
                        marc = rec.get("marc-xml")
                        if not marc:
                            continue
                        found = True
                        merged["oclcs"].append(oclc)
                        merged["record_urls"].append(rec.get("recordURL"))
                        parsed = parse_record(marc)
                        for k in ("lcsh", "ddc", "lcc", "authors", "titles"):
                            merged[k].extend(parsed[k])
                    if found:
                        break  # first identifier with records
                if found:
                    break
            if not found:
                empty += 1
                continue
            rec = {
                "gutenberg_id": m["gutenberg_id"],
                "work_key": m["work_key"],
                "gutenberg_title": m.get("gutenberg_title"),
                "isbns_used": isbns,
                "lccns_used": lccns,
                "oclcs_used": oclcs,
                "ht_subjects": list(dict.fromkeys(merged["lcsh"])),
                "ht_ddc": list(dict.fromkeys(merged["ddc"])),
                "ht_lcc": list(dict.fromkeys(merged["lcc"])),
                "ht_authors": list(dict.fromkeys(merged["authors"])),
                "ht_titles": list(dict.fromkeys(merged["titles"])),
                "oclcs": list(dict.fromkeys(merged["oclcs"])),
                "record_urls": list(dict.fromkeys(merged["record_urls"])),
            }
            enriched.append(rec)
            out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fh.flush()
            if (i + 1) % 40 == 0:
                print(f"  processed {i+1}/{len(matches)} (enriched={len(enriched)})")
            time.sleep(0.25)
    finally:
        out_fh.close()

    with open(args.out, "w", encoding="utf-8") as f:
        for r in enriched:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "matches_with_isbn": sum(1 for m in matches if m.get("isbn")),
        "enriched": len(enriched),
        "no_record": empty,
        "with_ht_subjects": sum(1 for r in enriched if r["ht_subjects"]),
        "with_ht_ddc": sum(1 for r in enriched if r["ht_ddc"]),
        "with_ht_lcc": sum(1 for r in enriched if r["ht_lcc"]),
        "avg_ht_subjects": round(sum(len(r["ht_subjects"]) for r in enriched) / max(1, len(enriched)), 2),
    }
    with open(ROOT / "reports" / "hathi_enrichment_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"\nEnriched {len(enriched)} books -> {args.out}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
