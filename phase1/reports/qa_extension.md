# LIBRA-QA extended over the full join

## Why

The original LIBRA-QA capped generation at 1,200 questions, which exhausted the
book list after **188 books**. Once the corpus grew to 1,241 books, ~1,050 of
them could never be a gold answer — they were pure distractors. That is a
harder retrieval task, but the gold distribution covered 15% of the collection.

## What changed

| | before | after |
|---|---|---|
| Questions | 1,200 | **8,690** |
| Books covered | 188 | **1,316** |
| In-corpus questions | 1,076 | **8,046** |
| Corpus books with >=1 question | 188 / 1,241 | **1,220 / 1,220** |
| known-item / topical / bib-fact | 375 / 374 / 451 | **2,718 / 2,718 / 3,254** |

Every book in the corpus is now reachable as a gold answer.

## Generation

Templates from `build_qa_drafts.py` (unchanged: gold is derived from the
record, so it is verifiable by construction), then LLM-rephrased into patron
language by `polish_qa_questions.py` with gold frozen.

- 8,690 polished, **8,689 rephrased, 1 fell back to template**
- 5 of 2,718 topical questions still contain raw MARC `--` subdivision syntax
  (0.2%); the rest read as natural requests
- `polish_qa_questions.py` was parallelised (8 workers) — serially this was
  over three hours

## Files

- `phase1/data/libra_qa_full.jsonl` — templates
- `phase1/data/libra_qa_full_polished.jsonl` — polished set (the benchmark)

## What this does and does not fix

**Fixes:** the gold/distractor asymmetry, and 7x more evaluation data.

**Does not fix:** topical questions are still LLM paraphrases of each record's
own subject heading. The query distribution remains unrepresentative of real
patron search, and every topical number remains an upper bound. Pooled graded
judging (conference §V-G) corrects the *scoring*; only independently sourced
queries correct the *queries*. See §5 of `plan/extended_journal_paper.md`.

## Evaluation note

At 8,046 in-corpus questions the chunk-based baselines cost ~1-2.5 s/question,
so a full-pool run is ~5 h per configuration. Reported numbers use a fixed
seeded 2,500-question sample; the full set is released.
