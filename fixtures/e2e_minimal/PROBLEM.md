# Q001 — Frozen Problem Statement (e2e minimal fixture)

**Q-id**: Q001
**Problem**: Does estimator X (sample mean) have lower sampling variance than
estimator Y (sample median) when estimating the population mean of a Gaussian
distribution from i.i.d. samples?

## Formal statement

Let X_1, ..., X_n be i.i.d. N(mu, sigma^2) with n = 21, mu = 0, sigma = 1.
Define the two estimators of mu:

- T_mean = (1/n) * sum_i X_i — estimator X (sample mean)
- T_med  = median(X_1, ..., X_n) — estimator Y (sample median)

Core claim (H): Var(T_mean) < Var(T_med) under repeated sampling, where the
variances are measured over independent Monte Carlo trials.

## Why this is a minimal problem

- Answerable by a seconds-scale Monte Carlo toy experiment: no datasets, no
  GPU, no third-party packages (stdlib `random` + `statistics` only).
- Analytic ground truth exists for cross-checking: Var(T_mean) = sigma^2 / n
  and, asymptotically, Var(T_med) = (pi / 2) * sigma^2 / n, so the expected
  variance ratio is 2 / pi (~0.637) < 1 and H is expected to be TRUE.
- Small enough to exercise every pipeline verdict artifact (routing, matrix,
  budget floor, audits, review, scoring) without any real research content.

## Freeze notice (INV-G1 PROBLEM_ANCHOR_FREEZE)

This statement is the problem anchor. At Phase 0 its SHA256 content hash is
written to `verdicts/PROBLEM_HASH.txt` and recomputed at every phase
boundary; any rewrite of this text is a pipeline violation
(`problem_content_rewritten`) and fails `/invariant-check`.
