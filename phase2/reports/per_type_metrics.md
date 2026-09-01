# Per-type metric breakdown (META-RAG pilot)

- Corpus: 30 books · Questions: 196 · Pool in corpus: 196

| type | dense | bm25 | hybrid | meta |
|---|---|---|---|---|
| known_item | 0.865 | 0.845 | 0.945 | 0.942 |
| topical | 0.417 | 0.217 | 0.377 | 0.697 |
| bib_fact | 0.836 | 0.901 | 0.962 | 0.990 |

**Paired permutation test (meta vs hybrid, nDCG@10):**

- known_item: p=0.914
- topical: p=0.000
- bib_fact: p=0.114
