# Phase 1 Report — Data & Benchmark Curation (LIBRA-Eval)

Date: session run · Status: **pilot complete; scale-out pending**

## What was built

| Artifact | File | Contents |
|---|---|---|
| Gutenberg index (metadata) | `data/gutenberg_index_all.jsonl` | 640 unique English public-domain books (deduped merge of two gutendex pulls) |
| Join matches | `data/join_pilot_matches.jsonl` | 224 Gutenberg↔OpenLibrary matches with professional fields |
| **LIBRA-CAT** | `data/libra_cat_records.jsonl` | 170 records (77 Tier-1, 93 Tier-2) with LCSH + DDC gold |
| **LIBRA-QA drafts (template)** | `data/libra_qa_drafts.jsonl` | 600 questions (186 known-item / 184 topical / 230 bib-fact), **0 with empty gold** |
| **LIBRA-QA drafts (polished)** | `data/libra_qa_drafts_polished.jsonl` | 600/600 LLM-rephrased via DeepSeek `deepseek-chat`, 0 fallbacks, 99% unique, gold intact |
| Samples | `data/samples/moby_dick_pg2701.txt` | Full-text sanity check (1.2 MB) |

**Polished examples (real output):**
```
[known_item] Could you help me locate a book called 'The Daughter of Anderson Crow' in your collection?
[topical]    Can you find a novel in this library that deals with city and town life as a fictional theme?
[bib_fact]   What subject headings can I find 'The Daughter of Anderson Crow' under?
```

## Key numbers

- **Join match rate: 77.8%** (224/288) — well above the 40% viability threshold.
- Of matched books: **87%** carry LCSH-format Gutenberg subjects; **50%** carry OL MARC-derived DDC.
- LIBRA-CAT Tier-1 yield from the pilot join: 77 records (subjects + DDC gold).
- QA draft yield: ~3.6 questions per matched book; all gold answers derived from the catalog record (verifiable by construction).

## Data-quality spot check (drawn from the artifacts)

LIBRA-CAT Tier-1 example:
```
Adventures of Huckleberry Finn | Twain, Mark | ddc=['059','813.403','817.44']
  subs=['Boys -- Fiction', 'Finn, Huckleberry (Fictitious character) -- Fiction']
Autobiography of a Yogi | Yogananda, Paramahansa | ddc=['181','294.5092','294.55']
  subs=['Yogis -- India -- Biography']
Eighty Years and More | Stanton, Elizabeth Cady | ddc=['324.623092']
  subs=['Feminism -- United States -- History -- 19th century', 'Suffragists -- United States -- Biography']
```

LIBRA-QA example:
```
[known_item] Find the book titled 'The Daughter of Anderson Crow' in this collection.
[topical]    Which book in this collection covers City and town life -- Fiction?
[bib_fact]   Under which subject headings is 'The Daughter of Anderson Crow' filed?
[bib_fact]   What Dewey Decimal class number is assigned to 'The Daughter of Anderson Crow'?
```

## Decisions made this session (and why)

1. **Gutenberg subjects = LCSH gold source** (not OL subjects, which are tag-dominated: only 0–9% LCSH-format).
2. **OL `ddc` = professional DDC gold** (MARC 082 aggregation, e.g. Moby Dick: 818, 813.36) — joined via title/author fuzzy matching.
3. **Rejected sources:** LOC search API & HathiTrust (Cloudflare-blocked from this network), OCLC Classify (blocked), IA `ddc` (103 items indexed), OL subjects as LCSH.
4. **`id.loc.gov` (LOC Linked Data) verified reachable** — will power Component C1 (authority-file RAG) and LCSH validation later.

## Known limitations (to disclose in the paper)

1. **DDC coverage skews to literature (800s)** — Gutenberg's most-downloaded books are classics. Fix: join more of the 640-book index (and expand it), accept DNB (German national library) records for non-fiction classes, or weight sampling.
2. **LIBRA-CAT is 170 records (pilot)** — target is 600; needs a ~2000-book join (≈30 min on a stable network).
3. Gutenberg LCSH is LC-derived but not national-agency MARC; **cataloger-panel validation** upgrades a stratified sample to high-confidence gold (Activity 1 in `outreach_catalogers.md`).
4. OL `ddc` aggregates multiple editions (multiple values per work) — scoring uses "any gold match" + primary value.
5. LLM-judge correlation pilot (`scripts/judge_pilot.py`) awaits an LLM API key (not available in this environment).

## Reproducibility

All scripts are deterministic (seeded RNGs), use open APIs only, and write JSONL.
Run: `cd phase1 && python3 scripts/fetch_gutenberg_index.py && python3 scripts/join_pilot.py --sample 2500 && python3 scripts/build_libra_cat.py --target 600 && python3 scripts/build_qa_drafts.py`

## Next steps

1. **Scale the join** to ~2000–2500 books → ~600 Tier-1 LIBRA-CAT records with wider DDC coverage.
2. **Catalogers:** send the `outreach_catalogers.md` email; run Activity-1 validation on 60 stratified records.
3. **LLM polish:** with an API key, rewrite QA questions via LLM (same gold constraints), run `judge_pilot.py`.
4. Full-text spot downloads for QA gold verification (chunk-level citation checks).
