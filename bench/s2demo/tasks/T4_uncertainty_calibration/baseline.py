"""Baseline: logistic fit whose scores pass through the incumbent's fixed
deployment sharpening (T0 = 0.5) — tuned for ranking/display, NOT calibration.

This is the documented incumbent behavior the candidate must beat; the base
model itself is a plain logistic regression (same as the candidate's base)."""
from __future__ import annotations

import numpy as np

DEPLOY_T0 = 0.5


def fit_logits(X: np.ndarray, y: np.ndarray, epochs: int = 600):
    mu, sd = X.mean(0), X.std(0) + 1e-8
    Xs = np.concatenate([np.ones((len(X), 1)), (X - mu) / sd], axis=1)
    w = np.zeros(Xs.shape[1])
    for _ in range(epochs):
        z = np.clip(Xs @ w, -50, 50)
        p = 1.0 / (1.0 + np.exp(-z))
        w -= 0.5 * (Xs.T @ (p - y)) / len(X)
    return w, mu, sd


def raw_logits(w, mu, sd, X) -> np.ndarray:
    Xs = np.concatenate([np.ones((len(X), 1)), (X - mu) / sd], axis=1)
    return np.clip(Xs @ w, -50, 50)


def solve(train: dict, test: dict) -> np.ndarray:
    X, y = train["X"], train["y"].astype(float)
    w, mu, sd = fit_logits(X, y)
    z = raw_logits(w, mu, sd, test["X"])
    return 1.0 / (1.0 + np.exp(-z / DEPLOY_T0))  # sharpened scores
