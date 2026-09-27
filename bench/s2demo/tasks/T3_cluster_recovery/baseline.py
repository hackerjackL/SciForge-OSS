"""Baseline: spherical k-means (isotropic clusters assumption)."""
from __future__ import annotations

import numpy as np

K = 3


def solve(train: dict, test: dict) -> np.ndarray:
    X = np.asarray(train["X"], dtype=float)
    Xt = np.asarray(test["X"], dtype=float)
    rng = np.random.default_rng(0)
    centers = X[rng.choice(len(X), size=K, replace=False)].copy()
    labels = np.zeros(len(X), dtype=int)
    for _ in range(50):
        d2 = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        new = d2.argmin(1)
        if (new == labels).all():
            labels = new
            break
        labels = new
        for k in range(K):
            if (labels == k).any():
                centers[k] = X[labels == k].mean(0)
    d2t = ((Xt[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
    return d2t.argmin(1)
