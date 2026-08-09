#!/usr/bin/env python3
"""Minimal toy experiment for the Q001 e2e smoke fixture (Phase 6b toy gate).

Core claim tested (see ../PROBLEM.md): the sample mean (estimator X) has
lower sampling variance than the sample median (estimator Y) when estimating
the mean of N(0, 1) from n = 21 i.i.d. draws.

Ground truth (used as a sanity band, not as a substitute for the Monte
Carlo): Var(mean) = sigma^2 / n, and asymptotically
Var(median) = (pi / 2) * sigma^2 / n, so the variance ratio
Var(mean) / Var(median) should be about 2 / pi ~= 0.637 < 1.

Contract honored:
- auto-pipeline SKILL.md Phase 6b gate: RESULT.json with
  status == "PASS" and core_claim_validated == true.
- experiment-execution SKILL.md "Output schema (RESULT.json)":
  experiment_id / stage / status / core_claim_tested / success_criteria /
  result_summary / gate_logic / execution_time_seconds / scale_ratio /
  reasoning_chain_validated / kill_signal / recommendation.
- Fixture additions required by the e2e smoke test: core_claim_validated,
  metrics, seeds_used (= 3).

Stdlib only (random + statistics), deterministic (fixed seeds), and
seconds-scale. Usage:

    python3 run_toy.py <outdir>

writes <outdir>/RESULT.json and exits 0 on PASS, 1 on FAIL, 2 on usage
error.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys
import time

N_SEEDS = 3
SEEDS = (42, 43, 44)
N_SAMPLES = 21          # draws per trial
N_TRIALS = 400          # Monte Carlo repetitions per seed
MU = 0.0
SIGMA = 1.0
# Ground-truth ratio Var(mean)/Var(median) ~ 2/pi ~= 0.637; accept a wide
# sanity band so the known-answer check is robust at toy scale.
RATIO_BAND = (0.35, 0.95)


def run_seed(seed: int) -> tuple[float, float]:
    """Return (var_of_means, var_of_medians) for one seed."""
    rng = random.Random(seed)
    means: list[float] = []
    medians: list[float] = []
    for _ in range(N_TRIALS):
        sample = [rng.gauss(MU, SIGMA) for _ in range(N_SAMPLES)]
        means.append(statistics.fmean(sample))
        medians.append(statistics.median(sample))
    return statistics.variance(means), statistics.variance(medians)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: run_toy.py <outdir>", file=sys.stderr)
        return 2
    outdir = argv[1]
    os.makedirs(outdir, exist_ok=True)

    started = time.time()
    per_seed: list[dict] = []
    all_var_mean: list[float] = []
    all_var_median: list[float] = []
    for seed in SEEDS:
        var_mean, var_median = run_seed(seed)
        all_var_mean.append(var_mean)
        all_var_median.append(var_median)
        per_seed.append({
            "seed": seed,
            "var_mean": round(var_mean, 6),
            "var_median": round(var_median, 6),
            "mean_has_lower_variance": var_mean < var_median,
        })

    pooled_var_mean = statistics.fmean(all_var_mean)
    pooled_var_median = statistics.fmean(all_var_median)
    ratio = pooled_var_mean / pooled_var_median

    per_seed_ok = all(entry["mean_has_lower_variance"] for entry in per_seed)
    pooled_ok = pooled_var_mean < pooled_var_median
    band_ok = RATIO_BAND[0] <= ratio <= RATIO_BAND[1]

    passed = per_seed_ok and pooled_ok and band_ok
    status = "PASS" if passed else "FAIL"
    elapsed = time.time() - started

    result = {
        "experiment_id": "toy_q001_e2e_fixture",
        "stage": "toy",
        "status": status,
        "core_claim_tested": (
            "sample mean has lower sampling variance than sample median "
            "for the mean of N(0,1), n=%d" % N_SAMPLES
        ),
        "core_claim_validated": passed,
        "success_criteria": (
            "per-seed and pooled Var(mean) < Var(median); pooled ratio "
            "Var(mean)/Var(median) inside sanity band %s around 2/pi"
            % (RATIO_BAND,)
        ),
        "metrics": {
            "pooled_var_mean": round(pooled_var_mean, 6),
            "pooled_var_median": round(pooled_var_median, 6),
            "variance_ratio": round(ratio, 6),
            "expected_ratio_2_over_pi": round(2.0 / 3.141592653589793, 6),
            "n_samples": N_SAMPLES,
            "n_trials_per_seed": N_TRIALS,
            "per_seed": per_seed,
        },
        "result_summary": {
            "primary_metric": {
                "metric_name": "variance_ratio",
                "metric_value": round(ratio, 6),
                "threshold": "< 1.0",
                "passed": pooled_ok,
            },
            "secondary_metrics": [
                {
                    "metric_name": "per_seed_direction",
                    "metric_value": sum(
                        1 for e in per_seed if e["mean_has_lower_variance"]
                    ),
                    "threshold": "== %d" % N_SEEDS,
                    "passed": per_seed_ok,
                },
                {
                    "metric_name": "known_answer_band",
                    "metric_value": round(ratio, 6),
                    "threshold": "inside %s" % (RATIO_BAND,),
                    "passed": band_ok,
                },
            ],
        },
        "gate_logic": "all_metrics_pass",
        "execution_time_seconds": round(elapsed, 3),
        "scale_ratio": 1.0,
        "seeds_used": N_SEEDS,
        "reasoning_chain_validated": passed,
        "kill_signal": None,
        "recommendation": "PROCEED_TO_FULL" if passed else "BLOCK",
    }

    out_path = os.path.join(outdir, "RESULT.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("toy experiment %s (%.3fs) -> %s" % (status, elapsed, out_path))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
