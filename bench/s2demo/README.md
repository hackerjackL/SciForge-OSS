# S2-demo bench — ScientistTwo-style demo sub-bench (CPU-only)

> Part of SciForge-OSS v1.7.0 (ScientistTwo parity layer). We cannot run
> Google's 107 real-conference problems here (no GPU, closed harness), so this
> is a **demo sub-bench built in their mold** — same ladder, same critic, same
> relative-gain metric, scaled to four synthetic problems any laptop or Colab
> free-tier CPU can finish in seconds.

## What is copied from ScientistTwo (arXiv:2609.19644)

| Their mechanism | Here |
|---|---|
| Input = problem + incumbent baseline (their: accepted-paper codebase) | each task ships a real baseline (`baseline.py`) that must be reproduced first |
| Subset → Full-Set ladder with 3-state Critic {BAD\|GOOD\|Engineer} | `run.py` runs both splits and drives the **production** critic (`kernel/sciforge/s2/ladder.py` — the same code the 6c boundary gate runs) |
| Promote only on strict full-set improvement | `S2_LADDER.json` written per task, `ladder.validate()` must return zero problems |
| Relative gain over baseline ("+25.2% over human SOTA") | `relative_gain_pct` per task (direction-aware: maximize/minimize) |
| Rubric-scored review + human anchor (their: NeurIPS-accepted mean 6.2) | per-task `RUBRIC` (6 axes, weighted) + `HUMAN_ANCHOR.baseline_score = 6.2` for calibration |
| Cost transparency (their: $3765 / 2–3 days per paper) | `wall_s` + per-arm `baseline_s` / `candidate_s` in every report |

## Tasks (all numpy-only, seeded, offline)

| Task | Question | Metric | Baseline → Candidate |
|---|---|---|---|
| `T1_tabular_nonlinear` | separate concentric rings without leaking test data | accuracy ↑ | linear logistic → random Fourier features + logistic |
| `T2_seasonal_forecast` | beat seasonal-naive on a held-out horizon | RMSE ↓ | seasonal naive → harmonic regression (lstsq, train only) |
| `T3_cluster_recovery` | recover anisotropic clusters unsupervised | purity ↑ | spherical k-means → full-covariance GMM-EM |
| `T4_uncertainty_calibration` | lower ECE with a train-only calibrator | ECE ↓ | sharpened deployment scores (T0=0.5) → temperature scaling on val slice |

Every task file carries the briefing, the 6-axis rubric and the human anchor —
the ARC-Bench / ScientistTwo "structured briefing" pattern.

## Run

```bash
python3 bench/s2demo/run.py --list
python3 bench/s2demo/run.py --task all           # all 4 tasks, ~5s CPU
python3 bench/s2demo/run.py --task T1 --solution path/to/your_solve.py
```

Solution contract (any python file, numpy allowed):

```python
def solve(train: dict, test: dict) -> np.ndarray:
    # train/test: {"X": ndarray, "y": ndarray} — never touch test["y"]
    ...
    return predictions  # labels or positive-class probs or values
```

Exit code `0` = every task `PROMOTED` (candidate strictly beats baseline on the
full split AND the ladder validates); `2` = something `DISCARDED/TUNE/invalid`.

Reports land in `bench/s2demo/results/` (gitignored):
`<task>__<solution>.report.json` (full metrics + rubric + anchor) and
`<task>__<solution>.S2_LADDER.json` (the exact artifact shape the 6c gate
validates — copy it into a run workspace as `.sciforge/audits/S2_LADDER.json`).

## Colab / no-GPU notes

- only `numpy` is required (Colab ships it); no downloads, no network;
- seeds are fixed — results are bit-reproducible per numpy version;
- to add a task: new dir under `tasks/` with `task.py` (`make_data`,
  `score`, `TITLE`, `METRIC_NAME`, `DIRECTION`, `RUBRIC`, `HUMAN_ANCHOR`),
  plus `baseline.py` and `candidate.py`.

## Relation to the kernel gates

```
bench/s2demo/run.py  ──imports──►  kernel/sciforge/s2/ladder.py
                                        ▲
scripts/s2_ladder_gate.py  ──imports────┘   (phase 6c boundary)
```

One critic implementation, two consumers: the bench proves the contract on
known-answer tasks; the gate enforces the same contract on real runs.
