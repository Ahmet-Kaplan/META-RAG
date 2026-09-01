# Join Pilot Report (Gutenberg -> OpenLibrary)

- Sample size: 2000 Gutenberg books (English, public domain)
- Matched: 1359 (68.0%)
- Unmatched: 641
- API failures: 0
- Matched books with DDC (OL, MARC-derived): 536 (39%)
- Matched books with LCSH-format subjects from Gutenberg: 1029 (76%)
- Matched books with LCSH-format subjects from OL: 110 (8%)

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
| 43548 The Illustrated Key to the Tarot: The Ve | /works/OL8516557W | - | 0 | 0 |
| 52734 The Scourge of God: A Romance of Religio | /works/OL24895273W | - | 4 | 0 |
| 50290 Space Station 1 | /works/OL37766011W | - | 2 | 0 |
| 22748 Explanation of Terms Used in Entomology | /works/OL24470796W | - | 1 | 0 |
| 57628 The Principles of Psychology, Volume 1 ( | /works/OL24353531W | - | 0 | 0 |
| 78107 Body-build and its inheritance | /works/OL1462095W | - | 0 | 0 |
| 60479 1900; or, The last President | /works/OL11449061W | - | 1 | 0 |
| 32101 The Crimson Gardenia and Other Tales of  | /works/OL5959561W | - | 0 | 0 |
| 55264 On Growth and Form | /works/OL1549602W | 574.4,574.31,591.134 | 0 | 0 |
| 16927 Tacitus: The Histories, Volumes I and II | /works/OL284406W | 937.07 | 2 | 0 |
| 28799 The Spinster Book | /works/OL2345588W | - | 0 | 0 |
| 21630 Bibliomania in the Middle Ages | /works/OL22014713W | - | 7 | 0 |
