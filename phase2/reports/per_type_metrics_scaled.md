# Per-type metric breakdown (META-RAG pilot)

- Corpus: 227 books · Questions: 300 · Pool in corpus: 1076

| type | dense | bm25 | hybrid | meta |
|---|---|---|---|---|
| known_item | 0.747 | 0.816 | 0.866 | 0.886 |
| topical | 0.519 | 0.268 | 0.451 | 0.574 |
| bib_fact | 0.936 | 0.869 | 0.978 | 0.982 |

**Paired permutation test (meta vs hybrid, nDCG@10):**

- known_item: p=0.257
- topical: p=0.002
- bib_fact: p=0.797
