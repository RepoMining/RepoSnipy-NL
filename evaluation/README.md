# Retrieval evaluation

This directory contains the single frozen benchmark used for the
natural-language retrieval feature. The benchmark combines Chinese and English
queries with AI-assisted prelabels that the team reviewed and accepted as the
current human standard.

## Scope

The evaluation is a **closed-pool reranking experiment**. Each query is scored
inside the union of the top-10 candidates returned by five retrieval methods:

- metadata BM25;
- README BM25;
- dense README retrieval;
- dense docstring retrieval;
- the original 0.80/0.20 proposal blend.

The reported results therefore measure candidate reranking. They are not a
measurement of full-index recall.

## Frozen data

```text
benchmark/ai_labeled_intent_benchmark.json
```

SHA-256:

```text
f1f2c11371210b07d7a15c1c72896d76efb73fefed263418d36f53d5879dad0b
```

| Item | Count |
| --- | ---: |
| Functional intents | 40 |
| Queries | 80 |
| Query-repository candidate judgments | 2,706 |
| Repositories with a public README in the candidate corpus | 1,182 |
| Queries: train / validation / test | 40 / 20 / 20 |
| Candidate judgments: train / validation / test | 1,369 / 678 / 659 |
| Candidate judgments: Chinese / English | 1,410 / 1,296 |

Labels use three levels:

- `0`: not relevant to the requested function;
- `1`: partially relevant or a useful alternative;
- `2`: directly satisfies the requested function.

The benchmark is marked `HUMAN_VERIFIED_AI_LABELS` and
`valid_as_human_gold = true`.

## Weight-selection protocol

README weight is searched from `0.00` to `1.00` in increments of `0.01`, with
docstring weight set to `1 - README weight`. The selected weight maximizes the
frozen validation-set 1,000-query bootstrap lower bound for nDCG@10. Ties are
resolved by validation nDCG@10, strict MRR@10, strict Hit@10, and weight
balance. The test split is not used to choose the production weight.

The validation-selected production weights are:

```text
README     0.33
docstring  0.67
```

| Metric | Validation (20 queries) | Test (20 queries) |
| --- | ---: | ---: |
| nDCG@10 | 0.604229 | 0.659644 |
| MRR@10 strict | 0.458532 | 0.629444 |
| Hit@10 strict | 0.700000 | 0.900000 |
| P@10 strict | 0.150000 | 0.205000 |
| Recall@10 strict, frozen pooled field | 0.641111 | 0.901389 |

The validation nDCG@10 bootstrap 95% lower bound is `0.523919`. A separate
test-only diagnostic optimum occurs at README `0.71` / docstring `0.29`, with
test nDCG@10 `0.665190`. It is recorded as a diagnostic and is not used to
change production weights.

## Reproduce

From the repository root:

```bash
python evaluation/audit_benchmark.py
```

The audit:

- verifies the SHA-256, status, labels, counts, splits, and uniqueness;
- reconstructs all 101 weight points from candidate channel scores and labels;
- independently recomputes nDCG@10, strict MRR@10, strict Hit@10, and strict
  P@10 for train, validation, and test;
- verifies the validation-selected weight and the test-only diagnostic;
- verifies that `DEFAULT_REQUIREMENT_WEIGHTS["blend"]` matches the frozen
  selection.

The historical pooled `Recall@10_strict` values are checked against the frozen
selected row but are not recomputed by this audit and are not used for weight
selection.

Use `--output path/to/audit.json` to save the machine-readable audit result.
The default command writes only to standard output and does not duplicate the
benchmark.
