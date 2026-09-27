"""T2 — Seasonal forecasting (CPU, synthetic, deterministic).

Briefing: a series with trend + two harmonics + noise. The seasonal-naive
baseline is the incumbent; find the simplest model that beats its forecast
RMSE on a held-out horizon without fitting the eval window.

score = RMSE (lower better => DIRECTION=minimize).
"""
from __future__ import annotations

import numpy as np

TITLE = "Seasonal forecast: harmonic regression vs seasonal-naive"
METRIC_NAME = "rmse"
DIRECTION = "minimize"
RUBRIC = [
    {"axis": "main_experiment_logic", "weight": 0.30,
     "question": "Forecast horizon held out? Baseline reproduced on the subset first?"},
    {"axis": "evidence_sufficiency", "weight": 0.20,
     "question": "Full-split RMSE strictly lower than baseline (not a subset fluke)?"},
    {"axis": "novelty_positioning", "weight": 0.15,
     "question": "Delta vs seasonal-naive stated (harmonics? trend? learned period?)?"},
    {"axis": "soundness", "weight": 0.15,
     "question": "Eval-window leakage (any fit using y beyond train)?"},
    {"axis": "clarity_reproducibility", "weight": 0.10,
     "question": "Seed, generator params and runtime reported?"},
    {"axis": "citation_integrity", "weight": 0.10,
     "question": "RMSE claims traceable to the report numbers?"},
]
HUMAN_ANCHOR = {"baseline_score": 6.2,
                "note": "anchor = human-accepted-paper mean under the same rubric"}

PERIOD = 24
HORIZON = 96


def make_data(split: str, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    n_train = {"subset": 120, "full": 600}[split]
    n = n_train + HORIZON
    t = np.arange(n, dtype=float)
    trend = 0.02 * t
    seasonal = (2.0 * np.sin(2 * np.pi * t / PERIOD)
                + 1.0 * np.sin(4 * np.pi * t / PERIOD + 0.7))
    y = trend + seasonal + rng.normal(0, 0.4, n)
    # "test" = forecast horizon; X is the time index (models may use train y only)
    return {"train": {"X": t[:n_train], "y": y[:n_train]},
            "test": {"X": t[n_train:], "y": y[n_train:]}}


def score(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
