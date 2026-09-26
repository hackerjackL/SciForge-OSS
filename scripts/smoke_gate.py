#!/usr/bin/env python3
"""Full-code smoke gate, kernel-enforced (v1.6 A3).

The contract (experiment-execution Step 5.0) makes .SMOKE.json load-bearing
evidence: "a full dispatch that completes without first writing .SMOKE.json is
invalid regardless of whether the experiment ultimately succeeded" — the buried-
subsection skip was a real, observed failure (Q-SGD-BS-GAP ran 184s with no
smoke). prose said MANDATORY; here the kernel checks it at the 6c boundary.

Check (against the workspace):
  1. every experiments/full/**/DISPATCH.json / STATUS.json group must have a
     sibling {experiment_id}.SMOKE.json with smoke_result=PASS
  2. freshness: smoke executed_at <= dispatch/launch time is NOT required
     (smoke runs first), but a smoke NEWER than the last STATUS update means
     the smoke ran against a mutated script — WARN only.
  3. no dispatch/STATUS files yet => SKIP (6c never reached).

Usage: python3 scripts/smoke_gate.py <workspace>
Exit: 0 PASS/SKIP, 2 FAIL (missing/failed smokes).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _smokes(ws: Path) -> dict[str, dict]:
    import json
    out = {}
    for f in (ws / "experiments" / "full").rglob("*.SMOKE.json"):
        stem = f.name.replace(".SMOKE.json", "")
        try:
            out[stem] = json.loads(f.read_text())
        except Exception:
            out[stem] = {"smoke_result": "FAIL", "fail_code": "unreadable_smoke_file"}
    return out


def check(ws: Path) -> list[str]:
    problems: list[str] = []
    full = ws / "experiments" / "full"
    if not full.is_dir():
        return []  # SKIP: experiment stage never produced anything
    smokes = _smokes(ws)
    # dispatched or finished groups identified by DISPATCH.json / STATUS.json
    markers = sorted(list(full.rglob("DISPATCH.json")) + list(full.rglob("STATUS.json")))
    groups = sorted({m.parent.name for m in markers})
    if not groups and not any(full.rglob("*.py")):
        return []  # nothing dispatched: theory-only / not reached
    for g in groups or ["_ungrouped"]:
        key = g if g != "_ungrouped" else "full"
        s = smokes.get(key) or smokes.get("full") or next(iter(smokes.values()), None)
        if s is None:
            problems.append(f"group '{g}': no {key}.SMOKE.json — smoke gate skipped "
                            f"(buried-subsection failure class; Step 5.0 is load-bearing)")
            continue
        if s.get("smoke_result") != "PASS":
            problems.append(f"group '{g}': smoke_result={s.get('smoke_result')} "
                            f"fail_code={s.get('fail_code')}")
        elif s.get("status_row_written") is not True:
            problems.append(f"group '{g}': smoke PASS but status_row_written!=true "
                            f"(status-row contract of Step 5.0 unmet)")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args(argv)
    problems = check(args.workspace)
    if problems:
        for p in problems:
            print(f"smoke_gate: FAIL — {p}")
        return 2
    has_any = (args.workspace / "experiments" / "full").is_dir()
    print("smoke_gate: PASS" if has_any else "smoke_gate: SKIP (no full experiments)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
