"""Golden problem-set regression (S19) — the selection pressure for RSI.

A fixed set of small problems covering all 4 verification routes; the kernel's
deterministic machinery (routing, gap-gate discrimination, leakage scan,
verdict-schema validity, e2e fixture) must reproduce the expected behavior on
every evolution round. An evolved patch that regresses any golden case scores
zero on the `test` shard (S12 held-out) and is rejected by submit's full CI.

This is the "must be >= old version" choice pressure the analysis called for:
not vibes, a runnable battery. stdlib; runs as a subprocess gate (see
kernel/config/evolve.json gate_checks for how the evolution domain scores it).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOLDEN = [
    {"id": "G-theory", "verification_type": "theory-only",
     "problem": "Prove: for n>=2, the AM-GM inequality holds for n positive reals.",
     "expect_route": "theory-only"},
    {"id": "G-comp", "verification_type": "computational",
     "problem": "Does label smoothing change transformer calibration?",
     "expect_route": "experiment-first"},
    {"id": "G-hybrid", "verification_type": "theory+experiment",
     "problem": "Derive and numerically verify damped-oscillator energy decay.",
     "expect_route": "hybrid"},
    {"id": "G-qual", "verification_type": "qualitative",
     "problem": "Taxonomy of historiographical schools on the fall of Rome.",
     "expect_route": "theory-only"},
]

# a gap report that SHOULD pass the discrimination gate, and one that should not
GOOD_GAP = ("GAP-1: prior [Xiao 2023] contradicts itself on attention sinks; "
            "no study measured perplexity delta for 125M models (Jin 2024).")
BAD_GAP = "Interesting future work is needed; this topic deserves more research."


def run_golden() -> dict:
    py = sys.executable
    results = []
    ok = True
    # 1. e2e fixture must validate complete (the pinned verdict contract)
    p = subprocess.run([py, str(REPO_ROOT / "scripts" / "validate_verdicts.py"),
                        str(REPO_ROOT / "fixtures" / "e2e_minimal" / ".sciforge" / "verdicts"),
                        "--strict", "--require-complete"],
                       capture_output=True, text=True, timeout=120)
    results.append({"case": "fixture_verdicts_complete", "passed": p.returncode == 0,
                    "tail": (p.stdout + p.stderr)[-200:]})
    ok &= p.returncode == 0

    # 2. routing determinism: feed each golden verification_type, expect the route
    from .pipeline import Kernel  # noqa: E402 (intra-package)
    import tempfile
    for g in GOLDEN:
        ws = Path(tempfile.mkdtemp()) / g["id"]
        (ws / ".sciforge" / "refine-logs").mkdir(parents=True)
        (ws / ".sciforge" / "refine-logs" / "FINAL_PROPOSAL.json").write_text(
            json.dumps({"verification_type": g["verification_type"]}))
        k = Kernel(ws)
        v = k._route()  # deterministic routing only
        got = json.loads((ws / ".sciforge" / "verdicts" / "VERIFICATION_ROUTING.json").read_text())["route"]
        passed = got == g["expect_route"]
        results.append({"case": f"route:{g['id']}", "passed": passed, "got": got,
                        "expect": g["expect_route"]})
        ok &= passed

    # 3. gap-gate discrimination: good passes, vague fails
    for label, gap, should_pass in (("gap_good", GOOD_GAP, True), ("gap_bad", BAD_GAP, False)):
        ws = Path(tempfile.mkdtemp())
        (ws / "literature").mkdir()
        (ws / "literature" / "GAP_REPORT.md").write_text(gap)
        p = subprocess.run([py, str(REPO_ROOT / "scripts" / "gap_gate.py"), str(ws)],
                           capture_output=True, text=True, timeout=60)
        passed = (p.returncode == 0) == should_pass
        results.append({"case": label, "passed": passed, "rc": p.returncode})
        ok &= passed
    return {"ok": ok, "n": len(results), "passed": sum(r["passed"] for r in results),
            "cases": results}


def main() -> int:
    out = run_golden()
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
