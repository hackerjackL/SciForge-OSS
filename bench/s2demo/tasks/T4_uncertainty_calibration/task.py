"""T4 — Probability calibration of a sharpened deployment score (CPU, synthetic).

Briefing: the incumbent pipeline trains a logistic model but publishes its
scores through a fixed deployment sharpening (T0 = 0.5, documented in
baseline.py — the classic "scores tuned for ranking/display, not for
calibration" situation). Research question: can a post-hoc calibrator,
fitted ONLY on a validation slice of train, recover well-calibrated
probabilities (lower ECE) on the held-out set?

score = ECE (10 equal-width bins), lower better => DIRECTION=minimize.
"""
from __future__ import annotations

import numpy as np

TITLE = "Post-hoc calibration: temperature scaling vs sharpened deployment scores"
METRIC_NAME = "ece"
DIRECTION = "minimize"
RUBRIC = [
    {"axis": "main_experiment_logic", "weight": 0.30,
     "question": "Calibrator fitted on a train-held-out validation slice only? Baseline reproduced on subset?"},
    {"axis": "evidence_sufficiency", "weight": 0.20,
     "question": "Full-split ECE strictly below baseline (same test set, same base model)?"},
    {"axis": "novelty_positioning", "weight": 0.15,
     "question": "Delta vs the incumbent sharpening stated (temperature? Platt? isotonic?)?"},
    {"axis": "soundness", "weight": 0.15,
     "question": "Any eval-label leakage into the calibrator fit?"},
    {"axis": "clarity_reproducibility", "weight": 0.10,
     "question": "Seeds, bin count, T-search grid and runtime reported?"},
    {"axis": "citation_integrity", "weight": 0.10,
     "question": "ECE claims traceable to report numbers?"},
]
HUMAN_ANCHOR = {"baseline_score": 6.2,
                "note": "anchor = human-accepted-paper mean under the same rubric"}
N_BINS = 10
DEPLOY_T0 = 0.5   # incumbent's fixed sharpening (documented in baseline.py)
LABEL_NOISE = 0.05


def make_data(split: str, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    n_train, n_test = {"subset": (600, 400), "full": (2000, 1000)}[split]
    d = 8
    w_true = rng.normal(0, 1, size=d)  # ONE truth shared by train and test

    def gen(n):
        X = rng.normal(0, 1, size=(n, d))
        p = 1.0 / (1.0 + np.exp(-(X @ w_true)))
        y = (rng.uniform(0, 1, n) < p).astype(int)
        flip = rng.uniform(0, 1, n) < LABEL_NOISE
        y = np.where(flip, 1 - y, y)
        return X, y

    Xtr, ytr = gen(n_train)
    Xte, yte = gen(n_test)
    return {"train": {"X": Xtr, "y": ytr}, "test": {"X": Xte, "y": yte}}


def score(y_true, y_prob) -> float:
    """ECE over N_BINS from positive-class probabilities."""
    y_true = np.asarray(y_true).astype(int)
    p = np.clip(np.asarray(y_prob, dtype=float), 0.0, 1.0)
    edges = np.linspace(0, 1, N_BINS + 1)
    ece = 0.0
    for i in range(N_BINS):
        mask = (p >= edges[i]) & (p < edges[i + 1]) if i < N_BINS - 1 \
            else (p >= edges[i]) & (p <= edges[i + 1])
        if mask.any():
            ece += mask.mean() * abs(p[mask].mean() - y_true[mask].mean())
    return float(ece)
