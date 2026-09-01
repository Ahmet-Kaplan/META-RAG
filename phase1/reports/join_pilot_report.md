# Join Pilot Report (Gutenberg -> OpenLibrary)

- Sample size: 288 Gutenberg books (English, public domain)
- Matched: 224 (77.8%)
- Unmatched: 64
- API failures: 0
- Matched books with DDC (OL, MARC-derived): 113 (50%)
- Matched books with LCSH-format subjects from Gutenberg: 194 (87%)
- Matched books with LCSH-format subjects from OL: 38 (17%)

## Interpretation

The match rate estimates how many Gutenberg works we can enrich with professional
catalog metadata. LIBRA-CAT ground truth = Gutenberg LCSH-format subjects
+ OL MARC-derived DDC; LIBRA-QA = the same matched corpus with full text from
Gutenberg. A match rate >= 40% means the corpus build is viable from Gutenberg +
OpenLibrary alone; below that, we expand the Gutenberg index (gutendex) and/or
add Internet Archive items.

## Sample of matches

| Gutenberg | OL work | DDC | #GutLCSH | #OLLCSH |
|---|---|---|---|---|
| 14818 The Daughter of Anderson Crow | /works/OL24242W | 813.52 | 3 | 0 |
| 560 Mr. Standfast | /works/OL76598W | 823.912 | 3 | 3 |
| 20546 The Hand in the Dark | /works/OL7547145W | 823.912 | 0 | 0 |
| 18857 A Journey to the Centre of the Earth | /works/OL17908357W | - | 2 | 0 |
| 75201 A farewell to arms | /works/OL63072W | 823.91,813.5,813.52 | 8 | 0 |
| 394 Cranford | /works/OL1103093W | 823,823.8,008 | 5 | 5 |
| 19476 A Honeymoon in Space | /works/OL20941812W | - | 0 | 0 |
| 31472 Cynthia's Chauffeur | /works/OL811070W | - | 2 | 0 |
| 10441 The Green Mouse | /works/OL8127244W | 813.52 | 3 | 0 |
| 26315 Shakespeare's family | /works/OL6923763W | - | 1 | 0 |
| 120 Treasure Island | /works/OL24034W | 653.424,823.89,813.52 | 3 | 1 |
| 393 The Blue Lagoon: A Romance | /works/OL43016143W | - | 4 | 0 |
