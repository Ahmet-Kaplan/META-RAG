# LIBRA-Eval & META-RAG

**Metadata Matters: Closing the Loop between LLM Cataloging and
Metadata-Aware Retrieval-Augmented Generation for Library Discovery**

A research release for the 2026 International Conference on Artificial
Intelligence and Digital Libraries (AIDL 2026). This repository contains:

- **META-RAG** — a metadata-aware retrieval-augmented generation system for
  library discovery: catalog records are first-class retrieval units
  (field-boosted BM25 + dense), fused with full-text chunks via reciprocal
  rank fusion, with citation-grounded generation and a verification module.
- **LIBRA-Eval** — a two-sided benchmark for library AI:
  - **LIBRA-QA** — 1,200 discovery questions (known-item / topical /
    bibliographic-fact) with record-linked gold answers, LLM-polished wording
  - **LIBRA-CAT** — 600 records with LCSH + DDC cataloging gold
  - A HathiTrust professional-MARC cross-check of the gold (89% DDC
    class-level agreement; subject headings differ mainly in form).

**Headline result (227 books, full in-corpus question pool n=1076):** META-RAG
improves retrieval nDCG@10 from 0.781 (best metadata-blind hybrid) to 0.851;
on topical discovery — where subject headings carry the signal — from 0.465
to 0.691 (paired permutation test, p < 0.001). Field ablation shows subjects
drive topical discovery (title-only 0.313 → title+subjects 0.691 topical); a
metadata corruption sweep confirms retrieval quality degrades monotonically
with metadata quality (topical 0.691 → 0.265 at 100% corruption).

## Quickstart (5-book demo, ~5 minutes)

Requires Python 3.11+, an embedding model download (~90 MB), and optionally
a DeepSeek API key (only for question polish and answer generation):

```bash
pip install transformers torch rank_bm25 numpy rapidfuzz python-dotenv openai matplotlib
cp phase1/.env.example phase1/.env      # add DEEPSEEK_API_KEY=... (optional)

# build a tiny corpus (5 books), index it, and evaluate all four modes
cd phase2
HF_HOME="$PWD/../.hf_cache" python3 scripts/corpus.py --limit 5 --out data/demo_corpus.jsonl
HF_HOME="$PWD/../.hf_cache" python3 scripts/index.py --corpus data/demo_corpus.jsonl --outdir data/demo_index
HF_HOME="$PWD/../.hf_cache" python3 scripts/evaluate.py --index data/demo_index \
    --qa ../phase1/data/libra_qa_drafts_scaled_polished.jsonl \
    --corpus data/demo_corpus.jsonl --all-modes --questions 10
```

## Reproduce the full pipeline (one command)

On a machine with a stable network and ≥ 15 GB free disk, the full benchmark
build and evaluation (~4–5 hours):

```bash
python3 run_scaled_pipeline.py --polish
python3 finalize_scaled_results.py     # regenerates paper tables/figures
```

The pipeline is checkpointed and resumable (`.scaled_state.json`); steps:
gutenberg index (4,000 books) → OpenLibrary join (2,000) → LIBRA-CAT (600) →
LIBRA-QA (1,200) → DeepSeek polish → corpus (250 books) → dual index →
evaluation (300 questions, 4 modes, permutation tests).

## Repository layout

```
paper/       paper (LaTeX, PDF, Word) + review & submission checklists
phase1/      benchmark curation: LIBRA-QA, LIBRA-CAT, HathiTrust cross-check,
             protocols, cataloger-panel materials, DeepSeek tooling
phase2/      META-RAG: corpus -> dual index -> hybrid retrieval ->
             citation-grounded generation -> evaluation
figures/     Figure 1 (architecture), Figure 2 (per-type), Figure 3 (robustness)
run_scaled_pipeline.py / finalize_scaled_results.py   one-command orchestration
DATA.md      full data inventory, licenses, regeneration instructions
```

## Data & licenses

All source data is open: Project Gutenberg (public domain), OpenLibrary
MARC-derived metadata, HathiTrust (public MARC API), Library of Congress
subject authorities (`id.loc.gov`). Benchmark annotations (LIBRA-QA questions,
LIBRA-CAT gold) are released under CC-BY-4.0; code under MIT. See `DATA.md`.

## Paper

- `paper/main.pdf` / `paper/main.docx` — *Metadata Matters: Closing the Loop
  between LLM Cataloging and Metadata-Aware Retrieval-Augmented Generation
  for Library Discovery*
- All numbers in the paper trace to JSON artifacts under `phase1/reports/`
  and `phase2/reports/`; all 18 citations were programmatically verified.

## Citing

See `CITATION.cff` (or cite the paper once published).

## Reproducibility notes

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (cached locally).
- LLM: DeepSeek `deepseek-chat` (OpenAI-compatible); used for question polish,
  answer generation, and the faithfulness judge (disclosed in the paper).
- No patron data is used anywhere; no IRB required.
