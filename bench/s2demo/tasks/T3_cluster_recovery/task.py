"""T3 — Cluster recovery under anisotropy (CPU, synthetic, deterministic).

Briefing: three clusters with different covariances and imbalanced sizes.
Spherical k-means (the incumbent) cuts elliptical clusters badly; find the
simplest method that beats its purity without labels (unsupervised).

score = clustering purity (higher better). Labels are used ONLY for scoring,
never for fitting.
"""
from __future__ import annotations

import numpy as np

TITLE = "Anisotropic cluster recovery: GMM vs spherical k-means"
METRIC_NAME = "purity"
DIRECTION = "maximize"
RUBRIC = [
    {"axis": "main_experiment_logic", "weight": 0.30,
     "question": "Unsupervised fit (no test labels used for training) + baseline reproduced on subset?"},
    {"axis": "evidence_sufficiency", "weight": 0.20,
     "question": "Full-split purity strictly above baseline with the same k?"},
    {"axis": "novelty_positioning", "weight": 0.15,
     "question": "Delta vs k-means stated (covariance model? init? regularization)?"},
    {"axis": "soundness", "weight": 0.15,
     "question": "Any label leakage into fitting (labels passed to solve)?"},
    {"axis": "clarity_reproducibility", "weight": 0.10,
     "question": "Seeds fixed, convergence criterion stated, runtime reported?"},
    {"axis": "citation_integrity", "weight": 0.10,
     "question": "Purity claims traceable to report numbers?"},
]
HUMAN_ANCHOR = {"baseline_score": 6.2,
                "note": "anchor = human-accepted-paper mean under the same rubric"}

_MIX = [  # (size weight, center, covariance) — covariances are PSD by construction
    (0.5, (-2.0, 0.0), ((2.0, 1.2), (1.2, 0.8))),
    (0.3, (2.0, 1.5), ((0.6, -0.45), (-0.45, 1.8))),
    (0.2, (0.0, -3.0), ((1.2, 0.0), (0.0, 0.5))),
]


def make_data(split: str, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    n = {"subset": 300, "full": 1500}[split]
    counts = [max(10, int(n * w)) for w, _, _ in _MIX]
    X, y = [], []
    for i, ((w, mu, cov), cnt) in enumerate(zip(_MIX, counts)):
        X.append(rng.multivariate_normal(mu, cov, size=cnt))
        y.append(np.full(cnt, i))
    X = np.concatenate(X)
    y = np.concatenate(y)
    perm = rng.permutation(len(X))
    X, y = X[perm], y[perm]
    # unsupervised contract: solve() never sees y; scoring does
    return {"train": {"X": X, "y": y}, "test": {"X": X, "y": y}}


def score(y_true, labels) -> float:
    y_true = np.asarray(y_true)
    labels = np.asarray(labels).astype(int)
    purity = 0.0
    for c in np.unique(labels):
        mask = labels == c
        if not mask.any():
            continue
        counts = np.bincount(y_true[mask].astype(int))
        purity += counts.max()
    return float(purity / len(y_true))
