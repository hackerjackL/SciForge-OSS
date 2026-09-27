#!/usr/bin/env python3
"""Completeness audit (ScientistTwo §3.7), kernel-enforced at wrap-up (phase 16).

Two mechanical halves of their audit that we did not have:
  1. reward-hacking scan — stated gains must equal recomputed gains; the
     evaluation protocol must declare split/held-out discipline;
  2. method↔code parity — every machine token the method section claims
     (`backticked` / snake_case / camelCase) must appear in the released
     code; <80% match = the method describes machinery that does not exist.

Writes `.sciforge/audits/AUDIT_TRAIL.json`.

Exit semantics: 0 = PASS or SKIP (no experiment claims to audit),
2 = FAIL. SKIP is only legitimate when no experiment evidence exists.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge.s2 import audit as audit_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    doc = audit_mod.run_full_audit(args.workspace)
    overall = doc["overall"]
    print(f"s2_audit {overall}")  # gate dispatchers parse this line — always emit
    if not args.quiet:
        print(f"  reward_hacking: {doc['reward_hacking']['overall']} "
              f"({list(doc['reward_hacking']['checks'])})")
        parity = doc["method_code_parity"]
        print(f"  method_code_parity: {parity.get('status')} "
              f"ratio={parity.get('ratio', '-')} unmatched={parity.get('unmatched', [])[:5]}")
    return 2 if overall == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
