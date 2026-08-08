# METHOD_REGISTRY_SNIPPET.md — Section 3 (Method Selection) of METHOD_REGISTRY.md

Fixture stand-in for the hash-locked Section 3 of `methods/METHOD_REGISTRY.md`
(Q001 e2e minimal run). `verdicts/REGISTRY_HASH.txt` holds the SHA256 of this
file's exact bytes; any edit here is an INV-G1-adjacent drift that
`/invariant-check` must catch by recomputing the hash (artifact-registry.md,
schema invariant 4: Section 3 immutability).

## Section 3 — Method Selection (hash-locked)

- Problem anchor: Q001 (frozen, see PROBLEM.md)
- Verification route: hybrid (analytic ground truth + Monte Carlo)
- Estimator X (main): sample mean of n = 21 i.i.d. N(0, 1) draws
- Estimator Y (comparison): sample median of the same draws
- Metric: sampling variance of each estimator over Monte Carlo trials;
  decision rule = Var(mean) < Var(median) per seed and pooled, plus
  Var(mean)/Var(median) inside the known-answer band around 2/pi
- Seeds: 3 fixed seeds (42, 43, 44); toy scale 400 trials per seed
- Budget scale: lite (effort-contract.md)
- Experiment groups: main (mean vs median Monte Carlo),
  baseline_analytic (closed-form 2/pi ratio check)

**LOCKED** — post-approval, this section is immutable. Drift => FAIL from
/invariant-check; KILL/PIVOT decisions must go through the bounded
loop-back registry, never a silent edit.
