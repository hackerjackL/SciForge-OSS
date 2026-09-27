"""Baseline: raw-feature logistic regression (linear boundary only)."""
from __future__ import annotations

import numpy as np


def solve(train: dict, test: dict) -> np.ndarray:
    X, y = train["X"], train["y"].astype(float)
    Xt = test["X"]
    # standardize from TRAIN stats only (no test leakage)
    mu, sd = X.mean(0), X.std(0) + 1e-8
    X = (X - mu) / sd
    Xt = (Xt - mu) / sd
    Xb = np.concatenate([np.ones((len(X), 1)), X], axis=1)
    w = np.zeros(Xb.shape[1])
    lr, epochs = 0.5, 300
    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-Xb @ w))
        w -= lr * (Xb.T @ (p - y)) / len(X)
    Xtb = np.concatenate([np.ones((len(Xt), 1)), Xt], axis=1)
    return ((Xtb @ w) > 0).astype(int)
