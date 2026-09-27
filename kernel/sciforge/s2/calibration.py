"""Anchor calibration for review scores (ScientistTwo §evaluation design).

Their most credible trick: before scoring generated papers, they score
**known-quality papers** (human-accepted NeurIPS papers, mean 6.2 under the
same reviewer) and anchor the scale on that. A raw LLM panel score with no
anchor is a number, not a measurement.

We copy the design mechanically:

    anchors = [{id, reference_score, panel_score}, ...]   (>= 2)
    fit     reference = a + b * panel_score                (OLS, stdlib)
    apply   calibrated = clamp(a + b * raw, 0, 10)

Degenerate fits (b <= 0 — panel anti-correlated with the anchors) fall back
to identity and flag `usable: false`: an unusable calibration must never
silently rescale scores.

Machine artifact: `.sciforge/audits/CALIBRATION.json`. When present,
`pipeline._native_review` reports `overall_calibrated` alongside the raw
panel score and drives rebuttal/meta-review off the calibrated value.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

SCHEMA_VERSION = "1.0"
AUDIT_REL = Path(".sciforge") / "audits" / "CALIBRATION.json"


def fit(anchors: list[dict]) -> dict:
    """Ordinary least squares reference = a + b*panel over >=2 anchors."""
    pts = []
    for an in anchors or []:
        try:
            pts.append((float(an["panel_score"]), float(an["reference_score"]),
                        str(an.get("id", ""))))
        except (KeyError, TypeError, ValueError):
            continue
    doc: dict = {"schema_version": SCHEMA_VERSION, "n": len(pts),
                 "anchors": [{"id": i, "panel_score": x, "reference_score": y}
                             for x, y, i in pts],
                 "fitted_at": time.time(), "method": "ordinary_least_squares"}
    if len(pts) < 2:
        doc.update({"a": 0.0, "b": 1.0, "usable": False,
                    "note": "fewer than 2 valid anchors — identity mapping"})
        return doc
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(pts)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 1e-12:
        doc.update({"a": 0.0, "b": 1.0, "usable": False,
                    "note": "degenerate anchors (zero panel variance) — identity"})
        return doc
    b = sxy / sxx
    a = my - b * mx
    # residual quality (cheap R^2) — reported, not gating
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
    usable = b > 0
    doc.update({"a": round(a, 6), "b": round(b, 6), "r2": round(r2, 4),
                "usable": usable,
                "note": None if usable else
                        "non-positive slope (panel anti-correlated with anchors) — "
                        "identity fallback, fix the rubric before trusting scores"})
    return doc


def apply(doc: dict | None, score: float) -> float:
    """Map a raw panel score onto the anchor scale; clamp to [0, 10]."""
    if not doc or not doc.get("usable", False):
        return float(score)
    try:
        cal = float(doc.get("a", 0.0)) + float(doc.get("b", 1.0)) * float(score)
    except (TypeError, ValueError):
        return float(score)
    return round(min(10.0, max(0.0, cal)), 2)


def load(ws: Path) -> dict | None:
    p = Path(ws) / AUDIT_REL
    try:
        doc = json.loads(p.read_text())
        return doc if isinstance(doc, dict) else None
    except Exception:
        return None


def save(ws: Path, doc: dict) -> Path:
    p = Path(ws) / AUDIT_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return p


def calibrate(ws: Path, raw_score: float | None) -> tuple[float | None, dict | None]:
    """Convenience: -> (calibrated_or_raw, calibration_doc|None)."""
    doc = load(ws)
    if raw_score is None:
        return None, doc
    return apply(doc, raw_score), doc
