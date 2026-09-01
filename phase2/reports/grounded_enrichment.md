# Grounded enrichment: does prediction quality find the headroom?

- 227 records, 227 enrichable, 693 predicted headings, 1076 questions
- Stripped catalog topical 0.313; enrich-all 0.656 (gain +0.343)
- Groundedness = IDF-weighted share of a heading's tokens found in the book's own full text (label-free)

## Per-record triage (budget = share of cataloging calls spent)

| Policy | 10% | 25% | 50% | 75% |
|---|---|---|---|---|
| random | 0.340 (8%) | 0.401 (25%) | 0.483 (49%) | 0.564 (73%) |
| grounded | 0.339 (8%) | 0.367 (16%) | 0.470 (46%) | 0.585 (79%) |
| ungrounded | 0.334 (6%) | 0.394 (23%) | 0.513 (58%) | 0.612 (87%) |
| oracle | 0.429 (34%) | 0.597 (83%) | 0.678 (106%) | 0.671 (104%) |

| Policy | budget | delta vs random | 95% CI | p |
|---|---|---|---|---|
| grounded | 10% | -0.0005 | [-0.0309, +0.0293] | 0.9759 |
| grounded | 25% | -0.0238 | [-0.0618, +0.0144] | 0.2331 |
| grounded | 50% | -0.0134 | [-0.0562, +0.0301] | 0.5432 |
| grounded | 75% | +0.0030 | [-0.0341, +0.0393] | 0.8741 |
| ungrounded | 10% | -0.0059 | [-0.0327, +0.0195] | 0.6667 |
| ungrounded | 25% | +0.0029 | [-0.0372, +0.0420] | 0.8871 |
| ungrounded | 50% | +0.0293 | [-0.0202, +0.0798] | 0.2568 |
| ungrounded | 75% | +0.0293 | [-0.0083, +0.0670] | 0.1287 |

## Per-heading filtering (full budget; drop headings below threshold)

| Threshold | headings kept | topical | delta vs unfiltered | 95% CI | p |
|---|---|---|---|---|---|
| 0.25 | 619/693 | 0.641 | -0.0153 | [-0.0329, +0.0004] | 0.0653 |
| 0.50 | 504/693 | 0.623 | -0.0329 | [-0.0584, -0.0088] | 0.0085 |
| 0.75 | 307/693 | 0.517 | -0.1395 | [-0.1764, -0.1033] | 0.0001 |
