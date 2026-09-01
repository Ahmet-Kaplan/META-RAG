# LIBRA-CAT by book popularity (memorization probe)

Project Gutenberg download count as a popularity proxy. If the headline
cataloging numbers were driven by memorization of famous works, quality
should fall off sharply in the low-popularity buckets.

- 687 predictions with a download count, 3 equal-size buckets

| Bucket (downloads) | n | LCSH exact | +semantic | any level | DDC class3 | authority viol. |
|---|---|---|---|---|---|---|
| 1877-2804 downloads | 229 | 0.332 | 0.585 | 0.649 | 0.829 (n=82) | 1.0% |
| 2805-5135 downloads | 229 | 0.298 | 0.542 | 0.586 | 0.827 (n=81) | 1.3% |
| 5139-142569 downloads | 229 | 0.413 | 0.653 | 0.679 | 0.866 (n=82) | 0.7% |

## Reading

- LCSH exact: 0.332 (least popular) vs 0.413 (most popular), delta +0.081
- Any-level:  0.649 vs 0.679, delta +0.030
- DDC class3: 0.829 vs 0.866, delta +0.037
