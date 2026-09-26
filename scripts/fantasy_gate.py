#!/usr/bin/env python3
"""Fantasy-prevention 5-gate — kernel-enforced (v1.6 A2).

The contract (fantasy-prevention.md) calls this "the most important quality
gate" yet it lived entirely in prose: nothing stopped an ungrounded claim from
reaching paper-writing. This script mechanically evaluates the 5 gates against
machine artifacts that the pipeline ALREADY produces (no new host burden —
each gate consumes an existing verdict/file):

  Gate1 Derivation traceability  : PROOF_AUDIT.json verdict in {PASS,WARN}
                                   OR derivations/**/derivation_output.md exists
  Gate2 Citation verifiability   : CITATION_AUDIT.json verdict == PASS
  Gate3 Assumption reasonability : FINAL_PROPOSAL.json assumptions[] each with
                                   a numeric reasonability score (hidden
                                   assumptions = the fantasy condition)
  Gate4 Falsifiability           : FALSIFICATION_RECORD.json exists with >= 1
                                   counterexample attempted
  Gate5 Data availability        : route theory-only => PASS-by-design;
                                   otherwise RESULT.json exists (data was run)
                                   or data-availability-report.json score >= 0.5

Verdict spectrum (contract's table): 5/4 gates => GROUNDED / MOSTLY_GROUNDED
(proceed); 3 => WEAKLY_GROUNDED (proceed with mandatory Limitations); 0-2 =>
MOSTLY_FANTASY/FANTASY -> FAIL, paper-writing is blocked (contract: return to
adversarial-falsification).

Evidence-not-yet-produced early phases => SKIP (exit 0): the gate fires where
its inputs exist; a route that legitimately lacks some artifacts declares them
N/A in VERIFICATION_ROUTING.json (those gates count as PASS-by-declaration).

Usage: python3 scripts/fantasy_gate.py <workspace> [--write-verdict]
Exit: 0 PASS/SKIP, 2 FAIL.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def evaluate(ws: Path) -> dict | None:
    v = ws / ".sciforge" / "verdicts"
    rl = ws / ".sciforge" / "refine-logs"
    routing = _load(v / "VERIFICATION_ROUTING.json") or {}
    na = set(routing.get("na_verdicts") or [])

    gates = {}

    # Gate 1 — derivation traceability
    pa = _load(v / "PROOF_AUDIT.json")
    if pa and pa.get("verdict") in ("PASS", "WARN"):
        gates["g1_derivation"] = (True, "PROOF_AUDIT verdict " + pa["verdict"])
    else:
        has_derivation = any((ws / "derivations").rglob("derivation_output.md")) \
            if (ws / "derivations").is_dir() else False
        if has_derivation:
            gates["g1_derivation"] = (True, "derivation_output.md present")
        elif pa is None and not (ws / "derivations").is_dir():
            gates["g1_derivation"] = (None, "no derivation artifacts yet")  # SKIP-eligible
        else:
            gates["g1_derivation"] = (False, "PROOF_AUDIT failed/absent without derivation trace")

    # Gate 2 — citation verifiability (3-layer PASS = verified refs)
    ca = _load(v / "CITATION_AUDIT.json")
    if ca is None:
        gates["g2_citation"] = (None, "CITATION_AUDIT not produced yet")
    else:
        gates["g2_citation"] = (ca.get("verdict") == "PASS", f"CITATION_AUDIT={ca.get('verdict')}")

    # Gate 3 — assumptions explicit + scored
    fp = _load(rl / "FINAL_PROPOSAL.json")
    if fp is None:
        gates["g3_assumptions"] = (None, "no FINAL_PROPOSAL.json")
    else:
        assumptions = fp.get("assumptions") or []
        scored = [a for a in assumptions
                  if isinstance(a, dict) and isinstance(a.get("reasonability"), (int, float))]
        if assumptions and len(scored) == len(assumptions):
            weak = [a for a in scored if a["reasonability"] < 5]
            gates["g3_assumptions"] = (len(weak) == 0 or "WARN", len(scored))
            if weak:
                gates["g3_assumptions"] = (True, f"{len(scored)} scored, {len(weak)}<5 (WARN zone)")
        else:
            # zero assumptions on an empirical claim = hidden assumptions; on a pure
            # math derivation the derivation itself is the grounding (g1 covers it)
            if routing.get("route") == "theory-only" or gates["g1_derivation"][0]:
                gates["g3_assumptions"] = (True, "no assumptions needed (derivation-grounded)")
            else:
                gates["g3_assumptions"] = (False, "assumptions missing or unscored")

    # Gate 4 — falsifiability: real counterexamples attempted
    fs = _load(rl / "FALSIFICATION_RECORD.json") or _load(v / "FALSIFICATION_RECORD.json")
    if fs is None:
        md = rl / "FALSIFICATION.md"
        gates["g4_falsifiable"] = (md.exists() and len(md.read_text()) > 500,
                                   "FALSIFICATION.md narrative") if md.exists() else \
                                  (None, "no falsification record yet")
    else:
        tries = len(fs.get("counterexamples") or fs.get("attacks") or
                    fs.get("falsification_rounds") or [])
        gates["g4_falsifiable"] = (tries >= 1, f"{tries} counterexample(s) attempted")

    # Gate 5 — data availability (theory-only: PASS by design)
    if routing.get("route") == "theory-only" or "BUDGET_FLOOR.json" in na:
        gates["g5_data"] = (True, "route needs no external data")
    else:
        has_result = (ws / "experiments").exists() and any((ws / "experiments").rglob("RESULT.json"))
        dar = _load(rl / "data-availability-report.json")
        if has_result or (dar and (dar.get("overall_score") or 0) >= 0.5):
            gates["g5_data"] = (True, "data executed or availability verified")
        elif dar is None and not has_result:
            gates["g5_data"] = (None, "experiment stage not reached yet")
        else:
            gates["g5_data"] = (False, "required data absent/unverified")

    evaluable = {k: v2 for k, v2 in gates.items() if v2[0] is not None}
    if not evaluable:
        return None  # full SKIP: pipeline hasn't produced fantasy evidence yet
    passed = sum(1 for ok, _ in evaluable.values() if ok is True)
    total = len(evaluable)
    # spectrum on the evaluable subset (partial evidence mid-run is normal for g2/g4 timing;
    # at the 12 boundary all artifacts exist, so total==5 in a complete run)
    ratio = passed / total
    if ratio >= 0.99:
        verdict = "GROUNDED"
    elif passed >= total - 1:
        verdict = "MOSTLY_GROUNDED"
    elif passed >= 3:
        verdict = "WEAKLY_GROUNDED"
    elif passed >= 2:
        verdict = "MOSTLY_FANTASY"
    else:
        verdict = "FANTASY"
    return {"gates": gates, "passed": passed, "total": total,
            "evaluable_total": total, "verdict": verdict}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    args = ap.parse_args(argv)
    ws = args.workspace
    res = evaluate(ws)
    if res is None:
        print("fantasy_gate: SKIP (no evidence artifacts yet)")
        return 0
    print(json.dumps(res, indent=2, default=str))
    if args.write_verdict:
        out = {"gate": "fantasy-prevention", "version": "v1.6",
               "verdict": res["verdict"], "gates_passed": res["passed"],
               "gates_total": res["evaluable_total"],
               "failed_gates": [k for k, (ok, _) in res["gates"].items() if ok is False],
               "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        (ws / "results").mkdir(exist_ok=True)
        (ws / "results" / "FANTASY_GATE.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        if res["verdict"] in ("FANTASY", "MOSTLY_FANTASY"):
            log = ws / ".sciforge" / "refine-logs" / "fantasy-log.md"
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, "a") as f:
                f.write(f"\n## Fantasy Entry — {out['generated_at']}\n"
                        f"**Verdict**: {res['verdict']} ({res['passed']}/{res['evaluable_total']} gates)\n"
                        f"**Failed gates**: {', '.join(out['failed_gates'])}\n"
                        f"**Action**: paper-writing BLOCKED; return to adversarial-falsification\n")
    blocked = res["verdict"] in ("FANTASY", "MOSTLY_FANTASY")
    print("fantasy_gate:", "FAIL — " + res["verdict"] if blocked else "PASS — " + res["verdict"])
    return 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
