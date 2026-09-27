"""Candidate: temperature scaling fitted on a validation slice of train.

Delta vs baseline: drop the fixed deployment sharpening; refit the base
logistic on 80% of train, choose T by validation ECE on the held-out 20%
(never the eval labels), publish sigmoid(z / T)."""
from __future__ import annotations

import numpy as np


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


def _ece(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (p >= edges[i]) & (p < edges[i + 1]) if i < n_bins - 1 \
            else (p >= edges[i]) & (p <= edges[i + 1])
        if mask.any():
            ece += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return float(ece)


def solve(train: dict, test: dict) -> np.ndarray:
    X, y = train["X"], train["y"].astype(float)
    n = len(X)
    n_val = max(50, n // 5)
    n_fit = n - n_val
    Xf, yf = X[:n_fit], y[:n_fit]
    Xv, yv = X[n_fit:], y[n_fit:]

    w, mu, sd = fit_logits(Xf, yf)
    z_v = raw_logits(w, mu, sd, Xv)
    best_T, best_ece = 1.0, _ece(yv, 1.0 / (1.0 + np.exp(-z_v)))
    for T in np.linspace(0.2, 8.0, 160):
        p_t = 1.0 / (1.0 + np.exp(-z_v / T))
        e = _ece(yv, p_t)
        if e < best_ece - 1e-12:
            best_ece, best_T = e, float(T)

    z_te = raw_logits(w, mu, sd, test["X"])
    return 1.0 / (1.0 + np.exp(-z_te / best_T))
