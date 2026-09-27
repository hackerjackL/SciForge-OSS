"""Baseline: seasonal-naive forecast (repeat the last full period)."""
from __future__ import annotations

import numpy as np

PERIOD = 24


def solve(train: dict, test: dict) -> np.ndarray:
    y = np.asarray(train["y"], dtype=float)
    n_test = len(np.atleast_1d(test["X"]))
    tail = y[-PERIOD:]
    reps = int(np.ceil(n_test / PERIOD))
    return np.tile(tail, reps)[:n_test]
