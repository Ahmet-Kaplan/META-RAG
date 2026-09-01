# Loop closing: does LLM-generated metadata improve discovery?

- 1241 books, 300 questions, META-RAG record index
- LLM metadata available for 1241/1241 records
- Identical index fields in all conditions; only field *content* changes

| Record metadata | overall | known_item | topical | bib_fact |
|---|---|---|---|---|
| none | 0.632 | 0.775 | 0.222 | 0.854 |
| llm_matched | 0.703 | 0.798 | 0.395 | 0.881 |
| llm | 0.699 | 0.759 | 0.406 | 0.895 |
| gold | 0.755 | 0.817 | 0.546 | 0.878 |

## Decomposition of the topical gap

The gap between no metadata (0.222) and gold metadata (0.546) is 0.324 nDCG@10. LLM cataloging closes 57% of it, in two parts:

- **Heading quality** (53% of the gap): at matched coverage, LLM headings on the 931 records that have gold reach 0.395 vs. gold's 0.546.
- **Coverage** (3% of the gap): the LLM also catalogs the 310 records that carry no gold heading at all, lifting topical nDCG@10 from 0.395 to 0.406.

So parity with gold is real but is not all heading quality: roughly
3% of it comes from enriching records the gold leaves empty.

## Interpretation limits

1. LIBRA-QA topical questions are paraphrases of each record's *gold*
   heading, so the gold condition is advantaged by construction and
   llm_matched is a lower bound on LLM heading utility.
2. The corpus is canonical public-domain literature; the model may have
   memorized real LCSH for these works, which would inflate both LLM
   conditions relative to a contemporary or obscure collection.
3. Known-item retrieval is *hurt* by both metadata sources relative to
   title-only (0.222... see table): subject terms add noise to
   identity lookups, and LLM subjects add slightly more than gold.
