# Per-type metric breakdown (META-RAG pilot)

- Corpus: 227 books · Questions: 120 · Pool in corpus: 1076

| type | dense | bm25 | hybrid | meta |
|---|---|---|---|---|
| known_item | 0.761 | 0.793 | 0.886 | 0.914 |
| topical | 0.507 | 0.269 | 0.440 | 0.736 |
| bib_fact | 0.940 | 0.796 | 0.983 | 0.914 |

**Paired permutation test (meta vs hybrid, nDCG@10):**

- known_item: p=0.551
- topical: p=0.003
- bib_fact: p=0.064
