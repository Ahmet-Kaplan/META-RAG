# Loop closing: does LLM-generated metadata improve discovery?

- 1241 books, 300 questions, META-RAG record index
- LLM metadata available for 1241/1241 records
- Identical index fields in all conditions; only field *content* changes

| Record metadata | overall | known_item | topical | bib_fact |
|---|---|---|---|---|
| none | 0.615 | 0.790 | 0.199 | 0.827 |
| llm_matched | 0.688 | 0.773 | 0.380 | 0.878 |
| llm | 0.719 | 0.754 | 0.476 | 0.896 |
| gold | 0.751 | 0.786 | 0.557 | 0.885 |

## Decomposition of the topical gap

The gap between no metadata (0.199) and gold metadata (0.557) is 0.359 nDCG@10. LLM cataloging closes 77% of it, in two parts:

- **Heading quality** (51% of the gap): at matched coverage, LLM headings on the 931 records that have gold reach 0.380 vs. gold's 0.557.
- **Coverage** (27% of the gap): the LLM also catalogs the 310 records that carry no gold heading at all, lifting topical nDCG@10 from 0.380 to 0.476.

So parity with gold is real but is not all heading quality: roughly
27% of it comes from enriching records the gold leaves empty.

## Interpretation limits

1. LIBRA-QA topical questions are paraphrases of each record's *gold*
   heading, so the gold condition is advantaged by construction and
   llm_matched is a lower bound on LLM heading utility.
2. The corpus is canonical public-domain literature; the model may have
   memorized real LCSH for these works, which would inflate both LLM
   conditions relative to a contemporary or obscure collection.
3. Known-item retrieval is *hurt* by both metadata sources relative to
   title-only (0.199... see table): subject terms add noise to
   identity lookups, and LLM subjects add slightly more than gold.
