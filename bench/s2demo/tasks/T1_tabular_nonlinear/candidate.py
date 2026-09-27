"""Candidate: random Fourier features + logistic (captures ring structure).

Delta vs baseline: explicit nonlinear feature map (RBF-kernel approximation)
so the same linear trainer separates concentric rings. Seeded — deterministic.
"""
from __future__ import annotations

import numpy as np


def solve(train: dict, test: dict) -> np.ndarray:
    X, y = train["X"], train["y"].astype(float)
    Xt = test["X"]
    mu, sd = X.mean(0), X.std(0) + 1e-8
    X = (X - mu) / sd
    Xt = (Xt - mu) / sd
    rng = np.random.default_rng(7)
    D, gamma = 256, 1.0
    W = rng.normal(0, np.sqrt(2 * gamma), size=(X.shape[1], D))
    b = rng.uniform(0, 2 * np.pi, size=D)
    fmap = lambda A: np.sqrt(2.0 / D) * np.cos(A @ W + b)
    Z, Zt = fmap(X), fmap(Xt)
    Zb = np.concatenate([np.ones((len(Z), 1)), Z], axis=1)
    w = np.zeros(Zb.shape[1])
    lr, epochs = 0.5, 400
    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-Zb @ w))
        w -= lr * (Zb.T @ (p - y)) / len(Z)
    Ztb = np.concatenate([np.ones((len(Zt), 1)), Zt], axis=1)
    return ((Ztb @ w) > 0).astype(int)
