#!/usr/bin/env python3
"""Component-ablation gate (ScientistTwo §3.4), kernel-enforced at phase 10.

No claim crosses result-to-claim without component ablation support: the
Ablation Planner emits 5–6 plans, AblCritic decides {GOOD|REFINE} under the
strict "new must strictly beat old" rule, and the ledger stays monotone
(current_best only moves in the improving direction).

Check (against the workspace):
  1. experiment evidence exists but `.sciforge/audits/ABLATION_LEDGER.json`
     is absent  => FAIL (claims without ablation — ScientistTwo would not
     have counted the paper)
  2. no experiment evidence            => SKIP (theory-only / no run yet)
  3. ledger present                    => full validation, any problem => FAIL

Usage: python3 scripts/s2_ablation_gate.py <workspace>
Exit:  0 = PASS/SKIP, 2 = FAIL.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge.s2 import ablation as ablation_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args()
    status, doc, problems = ablation_mod.evaluate(args.workspace)
    if status == "SKIP":
        print(f"s2_ablation SKIP: {problems[0] if problems else 'not applicable'}")
        return 0
    if status == "PASS":
        lo, hi = ablation_mod.plan_bounds()
        print(f"s2_ablation PASS: {len(doc.get('plans', []))} plans "
              f"(range {lo}-{hi}), current_best={doc.get('current_best')}")
        return 0
    print(f"s2_ablation FAIL ({len(problems)} problem(s)):")
    for p in problems:
        print(f"  - {p}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
