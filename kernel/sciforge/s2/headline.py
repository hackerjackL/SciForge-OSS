"""Geometric-mean headline + regression gates (AAR fusion, v1.7.1).

Ported measurement design from the AAR harness: the objective a research agent
hill-climbs is the GEOMETRIC MEAN of per-benchmark closed fractions
    closed(b) = (score - baseline) / (optimum - baseline),  clamped [0, 1]
so ANY benchmark left at or below baseline drives the whole headline to zero —
balanced improvement beats spiking one leg (anti-Goodhart by construction).
Plus two hard gates that make a "win" invalid regardless of headline:
  - capability floor: a don't-regress benchmark whose CI falls entirely below
    the base model's CI disqualifies the method;
  - regression gate: any scored dimension significantly WORSE than baseline
    (non-overlapping CIs) invalidates the method (no trading legs).

Pure stdlib, device-agnostic (identical on Mac test box / Linux CUDA / Windows).
"""
from __future__ import annotations

import math


def closed_fraction(score: float, baseline: float, optimum: float,
                    clamp: bool = True) -> float:
    """Fraction of the baseline->optimum gap closed (0 at baseline, 1 at optimum)."""
    denom = optimum - baseline
    if denom == 0:
        return 0.0
    f = (score - baseline) / denom
    return min(1.0, max(0.0, f)) if clamp else f


def geomean(values: list[float]) -> float:
    """Geometric mean; ANY zero (or empty) -> 0.0 (the balanced-gain property)."""
    vals = [float(v) for v in values]
    if not vals or any(v <= 0 for v in vals):
        return 0.0
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def headline(closed: dict[str, float]) -> float:
    """Headline = geomean of closed fractions over all scored legs."""
    return geomean(list(closed.values()))


def coverage_weighted_headline(closed: dict[str, float],
                               saturated: set[str] | None = None) -> float:
    """AAR's 'aab' variant: (n_improved/n_scored) * geomean(positive closed),
    saturated legs (no headroom) dropped from both terms."""
    saturated = saturated or set()
    scored = {k: v for k, v in closed.items() if k not in saturated}
    if not scored:
        return 0.0
    improved = [v for v in scored.values() if v > 0]
    if not improved:
        return 0.0
    return (len(improved) / len(scored)) * geomean(improved)


def ci_disjoint_below(ci_low_a: float, ci_high_a: float,
                      ci_low_b: float, ci_high_b: float) -> bool:
    """True when A's CI lies entirely below B's (significant regression)."""
    return ci_high_a < ci_low_b


def gates(closed: dict[str, float],
          capability: dict[str, tuple[float, float, float, float]] | None = None,
          per_leg_ci: dict[str, tuple[float, float, float, float]] | None = None) -> dict:
    """Hard-gate battery. capability/leg CIs: {name: (mean_lo, mean_hi, base_lo, base_hi)}.
    Returns {valid, reasons[]} — a method is invalid if any capability floor or
    scored-leg regression is significant, no matter the headline."""
    reasons: list[str] = []
    for name, (lo, hi, blo, bhi) in (capability or {}).items():
        if ci_disjoint_below(lo, hi, blo, bhi):
            reasons.append(f"capability_floor:{name}")
    for name, (lo, hi, blo, bhi) in (per_leg_ci or {}).items():
        if ci_disjoint_below(lo, hi, blo, bhi):
            reasons.append(f"regression_gate:{name}")
    return {"valid": not reasons, "reasons": reasons,
            "headline": headline(closed)}
