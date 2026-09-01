# Phase 1 — Data & Benchmark Curation (LIBRA-Eval)

Status: **pilot complete** — 224 Gutenberg↔OpenLibrary joins (77.8%), 170 LIBRA-CAT
records, 600 LIBRA-QA draft questions. See `reports/phase1_report.md`. Scale-out
to the full 600-record LIBRA-CAT is the immediate next step.

## Data architecture (decided after source vetting)

| Need | Source | Why | Status |
|---|---|---|---|
| Full text (LIBRA-QA corpus) | Project Gutenberg (plaintext URLs via gutendex) | Reliable, open, public domain | ✅ verified (Moby Dick 1.2 MB fetched) |
| LCSH-format subject gold | Project Gutenberg subjects (LCSH-format, LC-derived) | High yield of true LCSH headings | ✅ verified |
| Professional DDC gold | OpenLibrary `ddc` field (aggregated MARC 082s) | MARC-derived, numeric, stratified | ✅ verified (Moby Dick: 818, 813.36, ...) |
| LCSH authority validation (later: Component C1) | `id.loc.gov` (LOC Linked Data) | Open LCSH authority service | ✅ verified reachable |
| Backup cataloging source | DNB SRU (`services.dnb.de`, MARC21-xml) | National library, DDC + GND subjects | ✅ verified (ddc=330 → 9200 recs) |

**Rejected sources (blocked or too sparse):** LOC search API (Cloudflare bot challenge), HathiTrust API (403), OCLC Classify (blocked), Internet Archive `ddc` field (103 indexed items only), OL `subject` field as LCSH source (0–9% LCSH-format).

## LLM setup (DeepSeek)

The LLM-dependent tools (`polish_qa_questions.py`, `judge_pilot.py`) read the key
from either the environment or `phase1/.env`:

```bash
cd phase1
cp .env.example .env          # then edit: DEEPSEEK_API_KEY=sk-...
chmod 600 .env                # keep it private; .gitignore already excludes it
```

Then polish the 600 LIBRA-QA template questions (est. cost < $0.10 on deepseek-chat):

```bash
python3 scripts/polish_qa_questions.py          # all 600; --resume to continue after a break
python3 scripts/judge_pilot.py --answers answers.jsonl --human-labels labels.jsonl
```

## Pipeline

```
fetch_gutenberg_index.py  -> data/gutenberg_index.jsonl   (metadata only, ~2–3 MB)
join_pilot.py             -> data/join_pilot_matches.jsonl (Gutenberg <-> OL fuzzy join)
build_libra_cat.py        -> data/libra_cat_records.jsonl  (LIBRA-CAT: LCSH + DDC gold)
build_qa_drafts.py        -> data/libra_qa_drafts.jsonl    (LIBRA-QA template drafts)
judge_pilot.py            (run later, needs LLM API key)
```

Run from the `phase1/` directory (all paths are resolved relative to it):

```bash
cd phase1
python3 scripts/fetch_gutenberg_index.py --max-books 2500
python3 scripts/join_pilot.py --sample 250
python3 scripts/build_libra_cat.py --target 600
python3 scripts/build_qa_drafts.py
```

## LIBRA-CAT record schema

```json
{
  "gutenberg_id": 2701,
  "work_key": "OL2161394W",
  "title": "Moby Dick; Or, The Whale",
  "author_name": ["Melville, Herman"],
  "first_publish_year": 1851,
  "gold_subjects": ["Ahab, Captain (Fictitious character) -- Fiction", "Whales -- Fiction"],
  "ddc": ["818", "813.36"],
  "plaintext_url": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
  "tier": 1
}
```

- **tier 1** = subjects + DDC gold present (primary benchmark split)
- **tier 2** = subjects only (secondary; DDC absent)
- Gold subjects = Gutenberg LCSH-format headings (contain ` -- `); DDC = OL MARC-derived.

## LIBRA-QA draft schema

```json
{
  "qid": "QA-00042",
  "type": "topical | known_item | bib_fact",
  "question": "...",
  "gold": ["..."],
  "work_key": "OL2161394W",
  "gutenberg_id": 2701,
  "book_title": "Moby Dick; Or, The Whale",
  "verifiable": true
}
```

## Known limitations / honest caveats (for the paper)

1. OL `ddc` values are aggregated across editions/libraries (multiple assignments
   per work). We treat all numeric values as gold and record them; scoring
   uses "any gold match" plus a primary (first) value.
2. Gutenberg subjects are LCSH-format but not from a national bibliographic
   agency; the cataloger panel validation (Activity 1) is what upgrades a
   stratified sample to high-confidence gold.
3. Non-English Gutenberg works were excluded in the index (`languages=en`).
4. LLM judge correlation pilot (`judge_pilot.py`) requires an LLM API key —
   not available in this environment; run locally.

## Next steps

1. Expand the join: `--sample 1500` (≈20 min) to reach 600 Tier-1 LIBRA-CAT records.
2. Recruit the cataloger panel (see `outreach_catalogers.md`).
3. Set an LLM API key, then: polish QA questions via LLM, run `judge_pilot.py`.
4. Full-text spot downloads into `data/samples/` for sanity checks.
