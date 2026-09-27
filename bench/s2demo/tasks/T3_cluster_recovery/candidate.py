"""Candidate: Gaussian mixture (full-covariance EM) — handles anisotropy.

Delta vs baseline: per-component covariance instead of spherical assumption.
Labels are never consulted (unsupervised contract)."""
from __future__ import annotations

import numpy as np

K = 3


def solve(train: dict, test: dict) -> np.ndarray:
    X = np.asarray(train["X"], dtype=float)
    Xt = np.asarray(test["X"], dtype=float)
    rng = np.random.default_rng(0)
    n, d = X.shape
    means = X[rng.choice(n, size=K, replace=False)].copy()
    covs = np.array([np.cov(X.T) + 1e-6 * np.eye(d) for _ in range(K)])
    weights = np.full(K, 1.0 / K)
    resp = np.zeros((n, K))
    for _ in range(60):
        # E-step
        for k in range(K):
            inv = np.linalg.inv(covs[k])
            det = max(np.linalg.det(covs[k]), 1e-12)
            diff = X - means[k]
            quad = np.einsum("ni,ij,nj->n", diff, inv, diff)
            resp[:, k] = weights[k] * np.exp(-0.5 * quad) / np.sqrt((2 * np.pi) ** d * det)
        resp_sum = resp.sum(1, keepdims=True) + 1e-300
        resp /= resp_sum
        # M-step
        Nk = resp.sum(0) + 1e-10
        weights = Nk / n
        means = (resp.T @ X) / Nk[:, None]
        for k in range(K):
            diff = X - means[k]
            covs[k] = (resp[:, k][:, None] * diff).T @ diff / Nk[k] + 1e-6 * np.eye(d)
    # responsibilities for test points
    ll = np.zeros((len(Xt), K))
    for k in range(K):
        inv = np.linalg.inv(covs[k])
        det = max(np.linalg.det(covs[k]), 1e-12)
        diff = Xt - means[k]
        quad = np.einsum("ni,ij,nj->n", diff, inv, diff)
        ll[:, k] = np.log(weights[k] + 1e-300) - 0.5 * quad - 0.5 * np.log((2 * np.pi) ** d * det)
    return ll.argmax(1)
