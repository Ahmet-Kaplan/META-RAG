# Relevance pilot — human vs LLM judge

- items: 120
- labeler A judged: 120
- labeler B judged: 120

## Human-human agreement
- n = 120 (items both judged)
- Cohen's kappa (3-way 0/1/2): **0.755**
- Cohen's kappa (relevant(2) vs not): **0.821**
- exact agreement: 85.8%

## Labeler A vs LLM judge
- n = 120
- Cohen's kappa (3-way): **0.638**
- Cohen's kappa (relevant vs not): **0.767**
- exact agreement: 78.3%
- confusion (LLM->human): {(0, 0): 56, (0, 1): 1, (1, 0): 13, (1, 1): 7, (1, 2): 1, (2, 0): 3, (2, 1): 8, (2, 2): 31}

## Labeler B vs LLM judge
- n = 120
- Cohen's kappa (3-way): **0.795**
- Cohen's kappa (relevant vs not): **0.870**
- exact agreement: 87.5%
- confusion (LLM->human): {(0, 0): 55, (0, 1): 1, (0, 2): 1, (1, 0): 7, (1, 1): 13, (1, 2): 1, (2, 0): 1, (2, 1): 4, (2, 2): 37}

