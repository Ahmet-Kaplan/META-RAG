# Sparsity sweep: when does LLM enrichment pay off?

- 1241 books, 300 questions, META-RAG record index
- Coverage = fraction of the 931 gold-bearing records that keep their headings
- `enriched` adds LLM headings to every record left without one (seed 23)

| Gold coverage | records w/ subjects (base -> enr) | topical base | topical enriched | gain |
|---|---|---|---|---|
| 0% | 0 -> 1241 | 0.222 | 0.406 | **+0.184** |
| 25% | 238 -> 1241 | 0.318 | 0.476 | **+0.158** |
| 50% | 476 -> 1241 | 0.439 | 0.546 | **+0.107** |
| 75% | 706 -> 1241 | 0.513 | 0.581 | **+0.068** |
| 100% | 931 -> 1241 | 0.546 | 0.558 | **+0.012** |
