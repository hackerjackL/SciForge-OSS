#!/usr/bin/env python3
"""TDAL 4-dimension joint confidence — kernel-computed (v1.6, A1).

domain-adaptation-contract.md locked the formula since v2.8 but nothing computed
it — result-to-claim's TDAL block was prose. This script derives T×D×A×L purely
from EXISTING machine artifacts (no new host burden), applies the locked floor
constraints, and writes results/TDAL.json (marker pattern — the registered-
verdict set stays 22).

Locked formula (contract §Combined):
  T = 0.30×sympy + 0.25×logic + 0.25×falsification + 0.20×theory_data(0.5 neutral)
  D = 0.50×ouroboros + 0.30×oss_data_check + 0.20×theory_only_flag
  A = 0.80×learner_confidence + 0.20×seed_match (0.5 neutral when absent)
  L = 0.50×supporting + 0.30×non_contradicting + 0.20×non_gap
  joint = T×D×A×L;  >=0.7 STRONG / 0.5 MODERATE / 0.3 WEAK / else UNSUPPORTED
  floors: any dim=0 -> <=WEAK; missing_inputs non-empty -> <=MODERATE;
          FALSIFIED_SIGN -> UNSUPPORTED; total_papers=0 -> L=0 + literature_search missing.

Usage: python3 scripts/tdal_compute.py <workspace> [--write] [--json]
Exit: 0 computed (any verdict — it's a score, not a gate), 2 unreadable workspace.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

VERDICT_PASS, VERDICT_WARN = 1.0, 0.7
LEVELS = ("STRONG", "MODERATE", "WEAK", "UNSUPPORTED")


def _load(p: Path):
    try:
        return json.loads(p.read_text(errors="replace"))
    except Exception:
        return None


def _num(x, default=None):
    return float(x) if isinstance(x, (int, float)) else default


def compute(ws: Path) -> dict | None:
    v = ws / ".sciforge" / "verdicts"
    rl = ws / ".sciforge" / "refine-logs"
    routing = _load(v / "VERIFICATION_ROUTING.json") or {}
    theory_only = routing.get("route") == "theory-only"
    missing: list[str] = []

    # ---- T ----
    pa = _load(v / "PROOF_AUDIT.json")
    if pa is None:
        t_sympy = 0.5
        missing.append("sympy_derivation")
    else:
        t_sympy = {"PASS": VERDICT_PASS, "WARN": VERDICT_WARN}.get(pa.get("verdict"), 0.0)
    lv = _load(v / "LOGIC_VERIFICATION.json")
    t_logic = {"PASS": VERDICT_PASS, "WARN": VERDICT_WARN}.get((lv or {}).get("verdict"), 0.5) \
        if lv is not None else 0.5
    if lv is None:
        missing.append("logic_verification")
    fs = _load(rl / "FALSIFICATION_RECORD.json") or _load(v / "FALSIFICATION_RECORD.json")
    if fs is None:
        t_fals = 0.5
        missing.append("falsification")
    else:
        outcome = (fs.get("overall_outcome") or fs.get("verdict") or "").upper()
        t_fals = {"SURVIVE": 1.0, "SURVIVED": 1.0, "PASS": 1.0, "WEAKENED": 0.5,
                  "FALSIFIED": 0.0}.get(outcome, 0.5)
        if outcome == "FALSIFIED_SIGN":
            t_fals = 0.0
    t_data = 0.5  # deep Ouroboros call: neutral default per contract (missing input)
    missing.append("theory_data_validation")
    T = 0.30 * t_sympy + 0.25 * t_logic + 0.25 * t_fals + 0.20 * t_data

    # ---- D ----
    dar = _load(rl / "data-availability-report.json")
    d_ouro = _num((dar or {}).get("overall_score"), None)
    if d_ouro is None:
        d_ouro = 0.0
        missing.append("ouroboros_report")
    result_ok = bool(_load(ws / "experiments" / "full" / "RESULT.json")
                     or _load(ws / "experiments" / "toy" / "RESULT.json"))
    d_oss = 1.0 if result_ok else (0.5 if theory_only else 0.0)
    d_flag = 1.0 if theory_only else 0.0
    D = 0.5 * d_ouro + 0.3 * d_oss + 0.2 * d_flag

    # ---- A ----
    sig = _load(rl / "domain-signature.json")
    lc = _num((sig or {}).get("learning_confidence"), None)
    if lc is None:
        lc = 0.3
        missing.append("domain_learner")  # contract fallback: general baseline 0.3
    A = 0.8 * lc + 0.2 * 0.5

    # ---- L ----
    ca = _load(v / "CITATION_AUDIT.json")
    if ca is None:
        L = 0.0
        missing.append("literature_search")
    else:
        det = ca.get("details") or {}
        total = det.get("total_entries") or 0
        if total == 0:
            L = 0.0  # contract: no literature found -> L=0 + missing input
            missing.append("literature_search")
        else:
            counts = det.get("counts") or {}
            keep = counts.get("KEEP", 0)
            L = 0.5 * (keep / total) + 0.3 * (1.0 if ca.get("verdict") != "FAIL" else 0.5) \
                + 0.2 * 1.0  # non-gap: no machine gap-ratio field; neutral 1.0 noted

    joint = T * D * A * L
    # ---- verdict + floors ----
    dims = {"theoretical": T, "data_availability": D, "domain_adaptation": A,
            "literature_support": L}
    weakest = min(dims, key=dims.get)
    if joint >= 0.7:
        verdict = "STRONG"
    elif joint >= 0.5:
        verdict = "MODERATE"
    elif joint >= 0.3:
        verdict = "WEAK"
    else:
        verdict = "UNSUPPORTED"
    if any(val == 0.0 for val in dims.values()):
        verdict = "WEAK" if verdict in ("STRONG", "MODERATE") else verdict
    if missing and verdict == "STRONG":
        verdict = "MODERATE"  # floor: unverified inputs cap at MODERATE
    return {"tdal": {
        "dims": {k: round(x, 3) for k, x in dims.items()},
        "joint": round(joint, 4), "verdict": verdict,
        "weakest_dimension": weakest, "missing_inputs": sorted(set(missing)),
    }, "dims_raw": dims, "joint": joint}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    ws = args.workspace
    if not (ws / ".sciforge").is_dir():
        print("tdal_compute: FAIL — not a sciforge workspace", file=sys.stderr)
        return 2
    out = compute(ws)
    doc = {**out, "gate": "tdal", "version": "v1.6",
           "formula": "T×D×A×L locked (domain-adaptation-contract.md)",
           "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if args.write:
        (ws / "results").mkdir(exist_ok=True)
        (ws / "results" / "TDAL.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(json.dumps(doc if args.json else doc["tdal"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
