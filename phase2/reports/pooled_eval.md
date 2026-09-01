# Pooled graded relevance for topical questions

- 103 topical questions, pooled top-10 from 9 configurations
- Mean fully-relevant records per query: **2.38**
- Queries with more than one fully-relevant record: **39/103**

| Configuration | single-gold nDCG@10 | graded nDCG@10 | delta |
|---|---|---|---|
| dense | 0.519 | **0.521** | +0.002 |
| bm25 | 0.268 | **0.274** | +0.006 |
| hybrid | 0.451 | **0.424** | -0.027 |
| meta | 0.643 | **0.670** | +0.027 |
| loop_none | 0.283 | **0.314** | +0.031 |
| loop_llm | 0.625 | **0.649** | +0.024 |
| loop_gold | 0.643 | **0.670** | +0.027 |
| sparsity_base100 | 0.643 | **0.670** | +0.027 |
| sparsity_enr100 | 0.801 | **0.746** | -0.055 |

Judgments are LLM-derived and not yet human-validated; a human-judged
subsample is required before these are treated as gold.
