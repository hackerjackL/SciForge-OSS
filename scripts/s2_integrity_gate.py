#!/usr/bin/env python3
"""Integrity monitor CLI (v1.7.1 AAR fusion), skill-mode entry point.

The kernel runs the same check at the 6b/6c boundary (gate `integrity_monitor`);
this CLI lets the host agent self-check before dispatch, mirroring the
security_scan/smoke_gate convention. Deterministic core (D2 path/download +
D3 frontier-teacher co-occurrence) always runs; the semantic D1 tier runs only
when a provider gateway is configured (fail-closed inside the kernel gate).

Usage: python3 scripts/s2_integrity_gate.py <workspace> [--strict-llm]
Exit: 0 = PASS/SKIP, 2 = FAIL (violations listed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge.s2 import monitor as mon_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--strict-llm", action="store_true",
                    help="also run the semantic D1 tier via configured providers")
    args = ap.parse_args()
    prov = None
    if args.strict_llm:
        try:
            from sciforge.providers import Providers
            prov = Providers()
        except Exception:
            prov = None
    status, doc = mon_mod.evaluate(args.workspace, providers=prov)
    if status == "SKIP":
        print(f"s2_integrity SKIP: {doc.get('note', 'not applicable')}")
        return 0
    if status == "PASS":
        print(f"s2_integrity PASS: {doc.get('scripts_scanned')} scripts, "
              f"suite={doc.get('suite_benchmarks')}, "
              f"llm_tier={'yes' if doc.get('llm_reviewed') else 'deterministic-only'}")
        return 0
    print(f"s2_integrity FAIL ({len(doc.get('violations', []))} violation(s)):")
    for v in doc.get("violations", [])[:10]:
        print(f"  - [{v.get('desiderata')}] {v.get('file', '?')}:{v.get('line', '?')} "
              f"{v.get('detail', '')}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
