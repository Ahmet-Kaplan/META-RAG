# Extended benchmark: 1,241 books x 8,690 questions

Final state of the scale-up. Corpus and question set both extended; every
retrieval experiment re-run on the GPU server.

| | conference | scaled corpus | **+ extended questions** |
|---|---|---|---|
| Books | 227 | 1,241 | **1,241** |
| Chunks | 88,264 | 460,054 | **460,054** |
| Questions | 1,200 | 1,200 | **8,690** |
| Books reachable as gold | 188 | 188 | **1,220 (all)** |
| Evaluated on | 1,076 | 1,097 | **2,500** (seeded sample) |

Reported numbers use a fixed 2,500-question sample: at 8,046 in-corpus
questions the chunk-based baselines cost 1-2.5 s/question, so a full-pool run
is ~5 h per configuration. The complete 8,690-question set is released.

## Table I (n=2,500, 95% bootstrap CI)

| Config | known_item | topical | bib_fact | overall |
|---|---|---|---|---|
| dense | 0.680 [0.651, 0.709] | 0.343 [0.314, 0.372] | 0.883 [0.867, 0.899] | 0.651 [0.634, 0.667] |
| bm25 | 0.663 [0.635, 0.692] | 0.173 [0.150, 0.196] | 0.769 [0.745, 0.792] | 0.551 [0.533, 0.567] |
| hybrid | 0.794 [0.772, 0.816] | 0.299 [0.272, 0.327] | 0.926 [0.912, 0.939] | 0.690 [0.674, 0.706] |
| meta | 0.811 [0.791, 0.831] | 0.533 [0.504, 0.563] | 0.904 [0.890, 0.918] | 0.760 [0.746, 0.773] |

**Confidence intervals tightened by ~30%** (topical width 0.085 -> 0.059)
on 2.3x the questions.

### Significance (paired permutation, 20k iterations)

| Comparison | result |
|---|---|
| META-RAG vs hybrid, **topical** | 0.533 vs 0.299, **p<0.001** (n=771) |
| META-RAG vs hybrid, known_item | 0.811 vs 0.794, p=0.170 — no advantage |
| META-RAG vs hybrid, bib_fact | 0.904 vs 0.926, **p=0.007** — META-RAG is *worse* |

The topical result is now the strongest it has been: **+78% relative** over
hybrid, against +48% in the conference paper. Two secondary findings replicate
on independent questions:

- **No known-item advantage.** Held at 227 books (p=0.06), 1,241 books (p=0.87),
  and now on an independent question set (p=0.17). The conference paper's
  withdrawal of that claim was correct.
- **META-RAG loses to hybrid on bib_fact at scale** (p=0.007, replicating
  p=0.009). Full-text evidence disambiguates fact lookups over a large
  collection in a way record fields alone cannot. This is absent from the
  conference paper, where the two tied.

## Closing the loop (topical)

| Condition | value |
|---|---|
| no metadata | 0.227 |
| LLM, matched coverage | 0.393 |
| LLM, all records | 0.430 |
| gold | 0.533 |

LLM metadata recovers **66%** of the gap: **54% heading quality**, **12% coverage**.

The recovery figure has fallen at every step — 100% (227 books), 77% (1,241
books), **66%** (1,241 books, independent questions). Each correction of a
measurement artefact moved it down. The conference paper's 100% was an artefact
of a small collection and a question set covering 15% of it.

## Sparsity sweep (topical)

| Gold coverage | catalog as-is | + LLM gap-fill | gain |
|---|---|---|---|
| 0% | 0.227 | 0.430 | +0.203 |
| 25% | 0.301 | 0.466 | +0.165 |
| 50% | 0.400 | 0.512 | +0.112 |
| 75% | 0.471 | 0.546 | +0.075 |
| 100% | 0.533 | 0.586 | +0.053 |

**The central claim survives every correction**: gap-filling beats a fully
gold-cataloged collection, 0.533 [0.504, 0.562] -> 0.586 [0.557, 0.614], **p<0.001** (n=771). The gain
still declines monotonically with coverage and still never reaches zero.

- Enrichment **helps** bib_fact (0.915 vs 0.902, p=0.0003).
- Enrichment **hurts** known-item (0.794 vs 0.813, p=0.003). This
  was significant at 227 books, failed to replicate at 1,241 on the old question
  set, and is significant again on the extended set. Treat it as real: subject
  terms add noise to identity lookups.

## What this does not fix

Topical questions remain LLM paraphrases of each record's own subject heading.
More books and more questions make the task harder and better powered; they do
not make the query distribution representative of real patron search. Every
topical number here is still an upper bound. Only query logs or
authority-sourced queries change that (§5, `plan/extended_journal_paper.md`).

## Status

AIDL 2026 is frozen at 227 books and unaffected; `.results_227/` preserves those
artifacts. These results are E1 of the journal plan, complete.
Not re-run: LIBRA-CAT scoring (corpus-size independent), pooled graded relevance,
and the RQ2 generation pass.
