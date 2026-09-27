#!/usr/bin/env python3
"""Subset→Full-Set ladder gate (ScientistTwo §3.2), kernel-enforced at phase 6c.

The ladder is the mechanism that separates "a subset looked better" from
"a candidate actually beats the reproduced baseline": baseline reproduction
(subset) -> Critic three-state {BAD|GOOD|ENGINEER} -> full-set re-verification
-> promote only on strict full-set improvement, engineer rounds capped at 2.

Check (against the workspace):
  1. experiment evidence exists but `.sciforge/audits/S2_LADDER.json` is
     absent  => FAIL (the ladder was skipped — the exact failure class the
     ladder exists to prevent)
  2. no experiment evidence at all               => SKIP (theory-only / 6c
     not reached; matches smoke_gate semantics)
  3. ladder present                              => full structural validation
     (state machine, engineer cap, strict full-set improvement, gain
     arithmetic) — any problem => FAIL

Usage: python3 scripts/s2_ladder_gate.py <workspace>
Exit:  0 = PASS/SKIP, 2 = FAIL.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge.s2 import ladder as ladder_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args()
    status, doc, problems = ladder_mod.evaluate(args.workspace)
    if status == "SKIP":
        print(f"s2_ladder SKIP: {problems[0] if problems else 'not applicable'}")
        return 0
    if status == "PASS":
        critic = (doc or {}).get("critic", {})
        print(f"s2_ladder PASS: state={critic.get('state')} "
              f"engineer_rounds={critic.get('engineer_rounds')} "
              f"gain={ (doc or {}).get('relative_gain_pct') }%")
        return 0
    print(f"s2_ladder FAIL ({len(problems)} problem(s)):")
    for p in problems:
        print(f"  - {p}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
