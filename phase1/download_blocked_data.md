# How to Download the Blocked / Large Files

Short answer: **I cannot open a GUI browser**, but I have headless-Chrome automation
(`phase1/scripts/browser_downloader.py`) that solves Cloudflare challenges. From
this sandbox it works for **HathiTrust** but **not for www.loc.gov** (their
firewall blocks this datacenter IP even from real Chrome). Everything below that
says "run on your machine" will work from your network/browser.

---

## Quick decision table

| # | Data | Blocked here? | Do we need it? | Get it via |
|---|---|---|---|---|
| 1 | LOC search API (JSON) | ✅ blocked (CF) | Nice-to-have (extra professional metadata) | `browser_downloader.py` on **your machine** (or just open the URL in your browser) |
| 2 | LOC bulk MARC (cds/downloads) | blocked | Optional (large) | Browser on your machine; weekly files ~100 MB |
| 3 | HathiTrust bib API | **works from here** | Useful (professional MARC 650/082) | `browser_downloader.py` (needs valid OCLC/LCCN/ISBN) |
| 4 | OCLC Classify API | blocked | Optional (DDC cross-check) | `browser_downloader.py` on your machine |
| 5 | IA full text (`_djvu.txt`) | 503 (rate limit) | Fallback full text | Use archive.org item page → "Full Text" download, or retry later |
| 6 | Gutenberg index (gutendex) | flaky DNS | **Yes — for 600-record LIBRA-CAT** | `fetch_gutenberg_index.py --max-books 4000` on your machine |
| 7 | PG-19 (11 GB Gutenberg texts) | not attempted (disk) | Only if we want local full-text corpus | HF download on a machine with ≥15 GB free |
| 8 | HathiTrust Extracted Features 2.5 | not attempted | Optional (scale/robustness checks) | HTRC portal (account) |

---

## Instructions per item

### 1. LOC search API (JSON)
From your machine:
```bash
cd phase1
python3 scripts/browser_downloader.py --url "https://www.loc.gov/books/?fo=json&c=5&q=subject:railways+history"
```
Or in any browser, open that URL and save the page. Example useful query:
`https://www.loc.gov/books/?fo=json&c=20&q=ddc:330*` (20 records with subjects).

### 2. LOC bulk MARC
- Web page: https://www.loc.gov/cds/products/marcDist.php (free MARC distribution info)
- Weekly records: https://www.loc.gov/cds/downloads/MDSConnect/ (login sometimes required)
- Full catalog is ~30 GB; weekly files ~100 MB. Save under `phase1/data/loc_marc/`.

### 3. HathiTrust bibliographic API (works from this sandbox too!)
```bash
cd phase1
python3 scripts/browser_downloader.py --url "https://catalog.hathitrust.org/api/volumes/brief/isbn/9780141036144.json"
```
Identifiers: `isbn/…`, `lccn/…`, `oclc/…`, `htid/…`. Returns JSON with
`records[].recordURL` (full catalog page) and `items[]` (htids, rights).
This is the most authoritative MARC source we can reach — good for upgrading
LIBRA-CAT ground truth later.

### 4. OCLC Classify (DDC cross-check)
```bash
python3 scripts/browser_downloader.py --url "https://classify.oclc.org/classify2/Classify?stdnbr=ISBN:9780141036144&summary=true"
```
Run on your machine; from this sandbox OCLC serves a block page.

### 5. Internet Archive full text
503s here are IA rate-limiting, not a firewall. Options:
- Item page → "Full Text" → download (works in browser).
- Or `curl -L --retry 3 "https://archive.org/download/{id}/{id}_djvu.txt"` from your machine.
- Or use the IA search-inside API later.

### 6. Gutenberg index expansion (the one we actually need next)
From your machine (this sandbox had transient DNS failures):
```bash
cd phase1
python3 scripts/fetch_gutenberg_index.py --max-books 4000 --out data/gutenberg_index_full.jsonl
python3 scripts/join_pilot.py --index data/gutenberg_index_full.jsonl --sample 2000
python3 scripts/build_libra_cat.py --target 600
```
Target: ~600 Tier-1 LIBRA-CAT records (subjects + DDC gold).

### 7. PG-19 (11 GB)
On a machine with ≥15 GB free:
```bash
pip install -U "huggingface_hub[cli]"
huggingface-cli download pg19 --repo-type dataset
# or stream without saving: from datasets import load_dataset; load_dataset("pg19", split="train", streaming=True)
```

### 8. HathiTrust Extracted Features 2.5
- Portal: https://analytics.hathitrust.org/ (free HTRC account required)
- ~2 TB total; per-volume files available. Only needed for large-scale robustness runs.

---

## Where files should land

| Artifact | Path |
|---|---|
| LOC API JSON / MARC | `phase1/data/loc_*/` |
| HathiTrust JSON | `phase1/data/hathitrust_*/` |
| IA full texts | `phase1/data/ia_texts/` |
| Gutenberg index (expanded) | `phase1/data/gutenberg_index_full.jsonl` |
| LIBRA-CAT (built) | `phase1/data/libra_cat_records.jsonl` |

## What's already done (no download needed)

- LIBRA-CAT pilot: 170 records (`data/libra_cat_records.jsonl`)
- LIBRA-QA: 600 polished questions (`data/libra_qa_drafts_polished.jsonl`)
- Gutenberg index: 640 books (`data/gutenberg_index_all.jsonl`)
- Full-text on demand from `gutenberg.org` (works) — no bulk download needed.
