# Pooled graded relevance for topical questions

- 338 topical questions, pooled top-10 from 9 configurations
- Mean fully-relevant records per query: **2.25**
- Queries with more than one fully-relevant record: **125/338**

| Configuration | single-gold nDCG@10 | graded nDCG@10 | delta |
|---|---|---|---|
| dense | 0.514 | **0.502** | -0.012 |
| bm25 | 0.271 | **0.272** | +0.001 |
| hybrid | 0.465 | **0.437** | -0.028 |
| meta | 0.691 | **0.711** | +0.020 |
| loop_none | 0.313 | **0.326** | +0.013 |
| loop_llm | 0.656 | **0.680** | +0.024 |
| loop_gold | 0.691 | **0.711** | +0.020 |
| sparsity_base100 | 0.691 | **0.711** | +0.020 |
| sparsity_enr100 | 0.797 | **0.768** | -0.029 |

Judgments are LLM-derived and not yet human-validated; a human-judged
subsample is required before these are treated as gold.
