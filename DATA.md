# DATA.md — Data inventory, licenses, and regeneration

All source data is open and license-compatible with a public release. The
benchmark **annotations** (LIBRA-QA questions, LIBRA-CAT gold records) are our
own creation and are released under **CC-BY-4.0**; all **code** is MIT.

## Sources (external)

| Source | What we use | License / terms |
|---|---|---|
| Project Gutenberg | full text (public domain) + LCSH-format subjects | Public domain (US) |
| OpenLibrary | MARC-derived metadata: title/author/DDC (`ddc` field) | Open Library license / CC0 contributions |
| HathiTrust | professional MARC (650/082) via public bibliographic API | Public API; MARC records from contributing libraries |
| Library of Congress | subject authorities via `id.loc.gov` | Public domain |
| The British Library `blbooks` (HF) | referenced as open book-catalog metadata | CC0 |
| DNB SRU | backup national-library MARC21 source | Open (Deutsche Nationalbibliothek) |

## Benchmark artifacts in this repo (`phase1/data/`)

| File | Contents | Notes |
|---|---|---|
| `gutenberg_index_scaled.jsonl` | 4,000 Gutenberg books (gutendex metadata) | English, public domain |
| `join_matches_scaled.jsonl` | 1,359 Gutenberg↔OpenLibrary joins (68%) | fuzzy title/author |
| `libra_cat_records_scaled.jsonl` | **LIBRA-CAT**: 600 records (204 Tier-1: LCSH+DDC gold) | CC-BY-4.0 |
| `libra_qa_drafts_scaled.jsonl` | **LIBRA-QA**: 1,200 template questions | CC-BY-4.0 |
| `libra_qa_drafts_scaled_polished.jsonl` | LLM-polished wording (gold frozen) | CC-BY-4.0 |
| `hathi_enrichment.jsonl` | HathiTrust MARC cross-check (102 books) | see source terms |
| `join_pilot_matches.jsonl` | 224-book pilot joins | — |

## Derived artifacts NOT in the repo (regenerate or request)

These are large or network-derived; the pipeline rebuilds them:

| Artifact | Size (approx) | How to regenerate |
|---|---|---|
| Full-text corpus (250 books, chunks) | ~150 MB | `phase2/scripts/corpus.py --limit 250` |
| Dual index (dense + BM25, 88k chunks) | ~320 MB | `phase2/scripts/index.py` |
| Embedding model cache | ~90 MB | auto-downloaded to `.hf_cache/` |
| Ablation / noise index variants | ~2 MB each | `index.py --fields ... --records-only` |

Full pipeline: `python3 run_scaled_pipeline.py --polish` (~4–5 h on a normal
laptop; network-dependent). Evaluation results are in `phase1/reports/` and
`phase2/reports/` (all JSON, committed).

## Research ethics

- No patron/circulation data is used anywhere; no IRB required.
- LLM use (DeepSeek `deepseek-chat`) is disclosed in the paper and limited to
  question polishing, experimental answer generation, and the faithfulness
  judge; all outputs are programmatically validated.
- AI-generated metadata is used for research evaluation only, never written
  back to real catalogs.

## Reproducing the paper numbers

```bash
python3 run_scaled_pipeline.py --polish          # rebuild everything
python3 finalize_scaled_results.py               # regenerates paper tables/figures
cd paper && latexmk -pdf main.tex                # rebuild the PDF
```

See `README.md` and `paper/submission_checklist.md` for details.
