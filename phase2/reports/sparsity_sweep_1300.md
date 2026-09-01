# Sparsity sweep: when does LLM enrichment pay off?

- 1241 books, 300 questions, META-RAG record index
- Coverage = fraction of the 931 gold-bearing records that keep their headings
- `enriched` adds LLM headings to every record left without one (seed 23)

| Gold coverage | records w/ subjects (base -> enr) | topical base | topical enriched | gain |
|---|---|---|---|---|
| 0% | 0 -> 1241 | 0.199 | 0.476 | **+0.277** |
| 25% | 238 -> 1241 | 0.325 | 0.523 | **+0.198** |
| 50% | 476 -> 1241 | 0.415 | 0.593 | **+0.178** |
| 75% | 706 -> 1241 | 0.435 | 0.602 | **+0.166** |
| 100% | 931 -> 1241 | 0.561 | 0.669 | **+0.108** |
