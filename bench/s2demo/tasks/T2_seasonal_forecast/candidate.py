"""Candidate: harmonic (Fourier) regression with trend — least squares on
train only, forecast the held-out horizon."""
from __future__ import annotations

import numpy as np

PERIOD = 24


def _design(t: np.ndarray) -> np.ndarray:
    cols = [np.ones_like(t), t]
    for k in (1, 2):
        cols.append(np.sin(2 * np.pi * k * t / PERIOD))
        cols.append(np.cos(2 * np.pi * k * t / PERIOD))
    return np.stack(cols, axis=1)


def solve(train: dict, test: dict) -> np.ndarray:
    ttr = np.asarray(train["X"], dtype=float)
    ytr = np.asarray(train["y"], dtype=float)
    tte = np.asarray(test["X"], dtype=float)
    A = _design(ttr)
    coef, *_ = np.linalg.lstsq(A, ytr, rcond=None)
    return _design(tte) @ coef
