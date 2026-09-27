"""T1 — Tabular nonlinear separation (CPU, synthetic, deterministic).

Briefing (research question): the classes are concentric rings — no linear
boundary separates them. Reproduce the linear baseline, then find the
simplest method that materially beats it without leaking test data.

Contract: make_data(split) -> {"train": {X, y}, "test": {X, y}};
score(y_true, y_pred) -> accuracy (higher is better).
"""
from __future__ import annotations

import numpy as np

TITLE = "Nonlinear (concentric-ring) tabular classification: beat linear logistic"
METRIC_NAME = "accuracy"
DIRECTION = "maximize"
RUBRIC = [
    {"axis": "main_experiment_logic", "weight": 0.30,
     "question": "Is the baseline reproduced on the subset before the candidate claims a win?"},
    {"axis": "evidence_sufficiency", "weight": 0.20,
     "question": "Does the candidate strictly beat the baseline on the FULL split (not just subset)?"},
    {"axis": "novelty_positioning", "weight": 0.15,
     "question": "Is the method delta vs linear logistic stated (features? kernel? depth?)?"},
    {"axis": "soundness", "weight": 0.15,
     "question": "Any test-set leakage (fitting on test X/y, re-tuning on eval)?"},
    {"axis": "clarity_reproducibility", "weight": 0.10,
     "question": "Seeds fixed, data generator documented, runtime reported?"},
    {"axis": "citation_integrity", "weight": 0.10,
     "question": "Claims about linear/nonlinear separability traceable to the run?"},
]
HUMAN_ANCHOR = {"baseline_score": 6.2,
                "note": "anchor = human-accepted-paper mean under the same rubric "
                        "(ScientistTwo calibration design)"}


def make_data(split: str, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    n_train, n_test = {"subset": (240, 160), "full": (1200, 600)}[split]
    def rings(n):
        y = rng.integers(0, 2, size=n)
        r = np.where(y == 1, rng.uniform(1.5, 2.5, n), rng.uniform(0.2, 1.1, n))
        th = rng.uniform(0, 2 * np.pi, n)
        X = np.stack([r * np.cos(th), r * np.sin(th)], axis=1)
        X += rng.normal(0, 0.08, X.shape)
        return X, y
    Xtr, ytr = rings(n_train)
    Xte, yte = rings(n_test)
    return {"train": {"X": Xtr, "y": ytr}, "test": {"X": Xte, "y": yte}}


def score(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred).astype(int)
    return float((y_true == y_pred).mean())
