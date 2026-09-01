# Corpus scale-up: 227 -> 1,241 books

Full text for every joined book was downloaded, chunked, and indexed; all
retrieval experiments re-run end to end on the GPU server (voximul).

| | 227 books | 1,241 books |
|---|---|---|
| Books | 227 | **1,241** (118 of 1,359 joined were skipped: missing or <20k chars) |
| Chunks | 88,264 | **460,054** |
| Records with gold subjects | 156 (69%) | **931 (75%)** |
| In-corpus questions | 1,076 | **1,097** |
| Distinct books the questions cover | 188 | 188 (unchanged) |

**The question set did not grow.** LIBRA-QA's 1,200 questions cover 188 books,
so the extra ~1,050 books act purely as distractors. That is a harder and more
realistic retrieval task, but it is not more evaluation data. Extending the
question set over the full 1,359-book join is the natural companion step.

## Table I — full pool (n=1,097), 95% bootstrap CIs

| Config | known_item | topical | bib_fact | overall |
|---|---|---|---|---|
| dense | 0.692 [0.648, 0.737] | 0.370 [0.327, 0.414] | 0.878 [0.853, 0.902] | 0.660 [0.635, 0.685] |
| bm25 | 0.664 [0.621, 0.708] | 0.163 [0.130, 0.197] | 0.753 [0.719, 0.787] | 0.540 [0.514, 0.566] |
| hybrid | 0.784 [0.750, 0.817] | 0.316 [0.276, 0.357] | 0.921 [0.902, 0.940] | 0.688 [0.665, 0.711] |
| meta | 0.786 [0.754, 0.817] | 0.545 [0.502, 0.587] | 0.890 [0.868, 0.911] | 0.749 [0.728, 0.769] |

### What moved, 227 -> 1,241

| Config | topical | overall |
|---|---|---|
| dense | 0.514 -> **0.370** | 0.751 -> 0.660 |
| bm25 | 0.271 -> **0.163** | 0.658 -> 0.540 |
| hybrid | 0.465 -> **0.316** | 0.781 -> 0.688 |
| meta | 0.686 -> **0.545** | 0.853 -> 0.749 |

Every score falls, as it must with 5.5x more distractors. The *ordering* and
the central claim survive intact:

- **topical**: META-RAG 0.545 vs hybrid 0.316, paired permutation **p<0.001** (n=344). The relative gain actually grows: +72% vs +48% at 227 books.
- **known_item**: 0.786 vs 0.784, p=0.870. No advantage, confirming the withdrawal made at 227 books.
- **bib_fact**: META-RAG is now significantly *worse* than hybrid (0.890 vs 0.921, p=0.009). At 227 books this was a tie (p=0.375). **New finding:** for fact lookups over a large collection, full-text evidence disambiguates in a way the record fields alone cannot.

## Loop conditions (n=1,097, topical)

| Condition | 227 | 1,241 |
|---|---|---|
| none | 0.313 | **0.234** |
| llm-matched | 0.568 | **0.392** |
| llm | 0.656 | **0.453** |
| gold | 0.686 | **0.545** |

LLM metadata recovers **70%** of the topical gap (was 100% at 227 books): **51%** heading quality, **20%** coverage. Generated headings substitute for professional ones *less* well once there are 1,000 more books to be confused with -- the honest direction for this number to move.

## Sparsity sweep (n=1,097, topical)

| Gold coverage | catalog as-is | + LLM gap-fill | gain |
|---|---|---|---|
| 0% | 0.199 | 0.476 | +0.277 |
| 25% | 0.325 | 0.523 | +0.198 |
| 50% | 0.415 | 0.593 | +0.178 |
| 75% | 0.435 | 0.602 | +0.166 |
| 100% | 0.561 | 0.669 | +0.108 |

Same monotone shape, same conclusion: **gap-filling beats a fully gold-cataloged collection** and the gain never reaches zero.

On the full pool the headline comparison is 0.548 [0.505, 0.590] -> 0.619 [0.577, 0.661], paired permutation **p<0.001** (n=344).

> Note on the CIs: the marginal 95% intervals overlap slightly, while the paired
> test is decisive. That is expected and not a contradiction -- both arms are
> scored on the *same* questions, so the paired test removes the between-question
> variance that dominates each marginal interval. The paired test is the correct
> one here.

- Enrichment now **helps** bib_fact (0.909 vs 0.890, p=0.004).
- The known-item *harm* seen at 227 books (p=0.017) **does not replicate**: 0.776 vs 0.787, p=0.284. That caveat should be dropped, not carried forward.

## Status

The AIDL 2026 paper is frozen at 227 books and is unaffected. These results are
the foundation for the journal extension (E1 in `plan/extended_journal_paper.md`).
227-book artifacts are preserved in `.results_227/`.

Not yet re-run at 1,241 books: LIBRA-CAT scoring (unchanged -- cataloging quality
does not depend on corpus size), the pooled graded-relevance check, and the
generation/RQ2 pass.
