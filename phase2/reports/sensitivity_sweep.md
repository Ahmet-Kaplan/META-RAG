# Sensitivity sweep: subject boost ×w and RRF k

- Pool: all 1076 in-corpus questions · same record index construction as shipped (title+subj, DDC excluded)
- Validation: w=2, k=60 reproduces shipped topical 0.691 / overall 0.851

| config | topical | overall | known_item | bib_fact |
|---|---|---|---|---|
| w1k100 | 0.675 | 0.855 | 0.919 | 0.953 |
| w1k200 | 0.675 | 0.855 | 0.919 | 0.953 |
| w1k30 | 0.677 | 0.857 | 0.922 | 0.953 |
| w1k60 | 0.676 | 0.856 | 0.920 | 0.953 |
| w2k100 | 0.691 | 0.850 | 0.896 | 0.947 |
| w2k200 | 0.691 | 0.850 | 0.896 | 0.946 |
| w2k30 | 0.692 | 0.852 | 0.898 | 0.948 |
| w2k60 | 0.691 | 0.851 | 0.897 | 0.948 |
| w4k100 | 0.701 | 0.840 | 0.865 | 0.937 |
| w4k200 | 0.700 | 0.840 | 0.864 | 0.937 |
| w4k30 | 0.700 | 0.841 | 0.868 | 0.938 |
| w4k60 | 0.701 | 0.840 | 0.865 | 0.937 |
| w8k100 | 0.689 | 0.798 | 0.788 | 0.899 |
| w8k200 | 0.689 | 0.798 | 0.787 | 0.899 |
| w8k30 | 0.694 | 0.802 | 0.794 | 0.901 |
| w8k60 | 0.690 | 0.799 | 0.790 | 0.899 |

Subject boost rows (k=60 fixed):

- ×1: topical 0.676 (0.630–0.721) vs shipped ×2 0.691
- ×2: topical 0.691 (0.645–0.737) vs shipped ×2 0.691
- ×4: topical 0.701 (0.654–0.745) vs shipped ×2 0.691
- ×8: topical 0.690 (0.643–0.735) vs shipped ×2 0.691

RRF k rows (×2 fixed):

- k=30: topical 0.692 overall 0.852
- k=60: topical 0.691 overall 0.851
- k=100: topical 0.691 overall 0.850
- k=200: topical 0.691 overall 0.850
