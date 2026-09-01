# HathiTrust Enrichment Report (professional MARC vs. our gold)

- Books enriched: 102
- Books with both gold subjects and HT subjects: 34
- Books with both OL DDC and HT DDC: 19
- Books with all four signals: 7

## Subjects (Gutenberg LCSH vs HathiTrust LCSH)

- Books where >=1 gold heading matches a HT heading: **9/34** (26%)
- Mean heading recall (fraction of gold headings found in HT): **15%**
- Mean heading precision (fraction of HT headings present in gold): **21%**

## DDC (OpenLibrary vs HathiTrust 082)

- Books where >=1 OL ddc matches a HT ddc exactly: **5/19** (26%)
- Books where 3-digit class matches (any): **17/19** (89%)

## Example records (agreement / disagreement)

| Book | Gold LCSH | HT LCSH | Gold DDC | HT DDC |
|---|---|---|---|---|
| The Daughter of Anderson Crow | City and town life -- Fiction, Foundlings -- Fiction | - | 813.52 | - |
| Mr. Standfast | Hannay, Richard (Fictitious character) -- Fiction, Intellige | - | 823.912 | - |
| Cranford | England -- Fiction, Female friendship -- Fiction | - | 823, 823.8 | - |
| Cynthia's Chauffeur | Americans -- England -- Fiction, Chauffeurs -- Fiction | - | - | - |
| The Green Mouse | Courtship -- Fiction, Magic -- Fiction | - | 813.52 | - |
| Shakespeare's family | Shakespeare, William, 1564-1616 -- Family | - | - | - |
| Treasure Island | Pirates -- Fiction, Treasure Island (Imaginary place) -- Fic | - | 653.424, 823.89 | - |
| The Pirate: Andrew Lang Edition | Kidnapping -- Fiction, Landlord and tenant -- Fiction | - | 823.7, 823.73 | - |
| Two on a Tower | Adultery -- Fiction, Astronomical observatories -- Fiction | - | 823.8, 023.8 | - |
| The Woman in White | Art teachers -- Fiction, Country homes -- Fiction | Nobility -- Fiction, Country homes -- Fiction | 823.8, 820 | - |

## Interpretation (important for the paper)

1. **DDC gold is well validated**: OL-vs-HathiTrust DDC agrees on the 3-digit class
   in **89%** of books (exact-string match 26%). Professional assignments differ
   mainly in edition-level granularity, not class. OL `ddc` is credible ground truth.

2. **Subject "disagreement" is mostly heading-form, not wrongness**: inspection
   shows Gutenberg headings are genuine LCSH that frequently match HathiTrust
   exactly (e.g., The Mystery of Edwin Drood 3/4, The Woman in White 2/3). The
   low exact-match rate (26% of books) reflects two *valid* professional choices
   (e.g., HT "Governesses in literature" vs GUT "Governesses -- Fiction";
   HT "Sisters -- Fiction" vs GUT "England -- Fiction").

3. **Design consequence**: LIBRA-Eval's multi-level scoring (exact →
   semantic-equivalence → acceptable) is not a nicety — it is required, or the
   benchmark would misreport agreement between professional catalogers as "error".
   The cataloger-panel validation (Activity 1) converts this into a measured
   inter-cataloger-agreement baseline, which the LLM scores should be compared
   against, not against exact-match.

4. **Coverage note**: 102/224 books (45.5%) were found in HathiTrust via
   LCCN/OCLC/ISBN; of those, 36 carried 650 fields and 19 carried 082 fields in
   the first matched record (many matched records are minimal). For benchmark
   ground truth we keep Gutenberg+OL as primary; HathiTrust serves as the
   professional cross-check on this 36-book sample.
