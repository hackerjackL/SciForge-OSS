#!/usr/bin/env python3
"""Arb certified-interval verification gate (v1.6, python-flint).

Point-value claims ("slope 4.94") are unverifiable; interval arithmetic turns
them into certified statements ("slope ∈ [4.93, 4.95] with rigorous bounds").
This gate checks a workspace's experiment RESULT.json for `arb_claims`:

    "arb_claims": [
      {"name": "energy_decay_rate", "lo": "0.9999999998", "hi": "0.9999999999",
       "method": "arb", "script": "src/energy_study.py"},
      {"name": "fit_slope", "lo": "4.7", "hi": "5.3", "method": "arb",
       "recompute": "python: 3.1415926535897932384626433832795028841971 / 2"}
    ]

Two check levels:
  - containment: the claimed [lo,hi] must be a valid interval (lo <= hi, parseable
    as arb with a proven error bound); malformed => FAIL.
  - recompute (optional): if a `recompute` python expression is given, evaluate it
    under Arb precision and verify the claimed interval contains the computed ball
    — a mismatch means the claim was NOT certified against the computation.

`arb` is an OPTIONAL gate (like fairness): absent arb_claims => SKIP, so runs on
non-numeric (theory/qualitative) routes are unaffected; numeric runs that declare
claims are held to certification.

Exit: 0 PASS/SKIP, 2 FAIL. python-flint required for the arb path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_result(ws: Path) -> Path | None:
    for cand in (ws / "experiments" / "full" / "RESULT.json",
                 ws / "experiments" / "toy" / "RESULT.json",
                 ws / "results" / "RESULT.json"):
        if cand.exists():
            return cand
    hits = sorted((ws / "experiments").rglob("RESULT.json")) if (ws / "experiments").is_dir() else []
    return hits[0] if hits else None


def check(ws: Path) -> list[str]:
    problems: list[str] = []
    rj = _find_result(ws)
    if rj is None:
        return []  # SKIP: no experiment result yet
    try:
        data = json.loads(rj.read_text())
    except Exception as e:
        return [f"RESULT.json unreadable: {e}"]
    claims = data.get("arb_claims") or []
    if not claims:
        return []  # SKIP: no certified claims declared
    try:
        from flint import arb, ctx  # python-flint
    except ImportError:
        return ["arb_claims present but python-flint not installed "
                "(pip install python-flint into the kernel venv) — certification impossible"]
    ctx.prec = 128
    for c in claims:
        name = c.get("name", "?")
        try:
            lo = arb(str(c["lo"])); hi = arb(str(c["hi"]))
        except Exception as e:
            problems.append(f"{name}: unparsable interval bounds ({e})")
            continue
        if not (lo <= hi):
            problems.append(f"{name}: inverted interval [{lo} , {hi}]")
            continue
        expr = c.get("recompute")
        if expr:
            try:
                val = eval(expr, {"__builtins__": {}}, {"arb": arb, "ctx": ctx})
                ball = val if isinstance(val, arb) else arb(str(val))
            except Exception as e:
                problems.append(f"{name}: recompute failed ({e})")
                continue
            # arb comparisons are certified: lo <= ball holds only if EVERY
            # element of the claimed interval is <= every element of the ball
            if not (lo <= ball and ball <= hi):
                problems.append(f"{name}: recompute {ball} NOT contained in claimed "
                                f"{lo}..{hi} — claim uncertified")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args(argv)
    problems = check(args.workspace)
    if problems:
        for p in problems:
            print(f"arb_verify: FAIL — {p}")
        return 2
    print("arb_verify: PASS (or SKIP — no arb_claims)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
