"""Component Ablation planner + AblCritic (ScientistTwo §3.4).

Copied rules:

- the Ablation Planner emits **5–6 plans** (component removed/replaced, one
  metric each) — mechanical floor/cap here (env-overridable for tiny runs);
- AblCritic decides {Good | Refine} per plan under the STRICT rule
  "the new result must strictly beat the old state" — a tie keeps the old
  state (REFINE), it never silently replaces it;
- the ledger is monotone: `current_best` can only move in the improving
  direction, and every GOOD decision must be backed by numbers.

Machine artifact: `.sciforge/audits/ABLATION_LEDGER.json`, demanded by the
phase-10 gate (`scripts/s2_ablation_gate.py`) whenever experiment results
exist — claims without ablation support cannot cross the result-to-claim
boundary.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .ladder import is_improvement

SCHEMA_VERSION = "1.0"
AUDIT_REL = Path(".sciforge") / "audits" / "ABLATION_LEDGER.json"
DECISIONS = ("GOOD", "REFINE")


def plan_bounds() -> tuple[int, int]:
    """(min, max) plans per round — ScientistTwo: 5–6."""
    lo = int(os.environ.get("SCIFORGE_ABLATION_MIN", "5"))
    hi = int(os.environ.get("SCIFORGE_ABLATION_MAX", "6"))
    return max(1, lo), max(lo, hi)


def ablcritic(prev: float | None, new: float, direction: str = "maximize") -> str:
    """AblCritic: GOOD iff the new state strictly beats the old; else REFINE
    (old state kept). Missing prev (first measurement) -> GOOD."""
    if prev is None:
        return "GOOD"
    return "GOOD" if is_improvement(prev, new, direction) else "REFINE"


def validate(doc: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(doc, dict):
        return ["ablation ledger is not a JSON object"]
    if doc.get("schema_version") not in (None, SCHEMA_VERSION):
        problems.append(f"unknown schema_version {doc.get('schema_version')!r}")

    lo, hi = plan_bounds()
    plans = doc.get("plans") or []
    if not plans:
        problems.append("plans missing (Ablation Planner produced nothing)")
    elif not (lo <= len(plans) <= hi):
        problems.append(
            f"{len(plans)} plans out of range [{lo},{hi}] (ScientistTwo: 5–6 plans)")

    seen_ids: set[str] = set()
    for i, p in enumerate(plans):
        pid = str(p.get("id") or f"#{i}")
        if pid in seen_ids:
            problems.append(f"duplicate plan id {pid}")
        seen_ids.add(pid)
        for field in ("component", "hypothesis", "metric"):
            if not p.get(field):
                problems.append(f"plan {pid}: missing '{field}'")

    direction = (doc.get("metric") or {}).get("direction", "maximize")
    results = doc.get("results") or []
    by_plan = {str(r.get("plan")): r for r in results}
    for r in results:
        pid = str(r.get("plan"))
        decision = r.get("decision")
        if decision not in DECISIONS:
            problems.append(f"result {pid}: decision must be one of {DECISIONS}, "
                            f"got {decision!r}")
            continue
        new = r.get("new_value")
        prev = r.get("prev_value")
        if new is None:
            problems.append(f"result {pid}: new_value missing")
            continue
        expected = ablcritic(prev, new, direction)
        if decision != expected:
            problems.append(
                f"result {pid}: decision {decision} violates the strict rule "
                f"(mechanical AblCritic says {expected} for prev={prev} new={new})")
        if decision == "GOOD" and prev is not None and not is_improvement(prev, new, direction):
            problems.append(f"result {pid}: GOOD declared without strict improvement")

    executed = [p for p in plans if str(p.get("id")) in by_plan]
    for p in executed:
        if p.get("status") not in (None, "executed", "refined", "planned"):
            problems.append(f"plan {p.get('id')}: unknown status {p.get('status')!r}")

    # monotone ledger: current_best must equal the best GOOD outcome seen
    current = doc.get("current_best")
    if current is not None and results:
        vals = [r.get("new_value") for r in results
                if r.get("decision") == "GOOD" and r.get("new_value") is not None]
        if vals:
            best = max(vals) if direction == "maximize" else min(vals)
            try:
                if abs(float(current) - float(best)) > 1e-9:
                    problems.append(
                        f"current_best {current} != best GOOD outcome {best} "
                        f"(ledger not monotone — state regressed or was hand-edited)")
            except (TypeError, ValueError):
                problems.append("current_best is not numeric")
    if not (doc.get("problem_id") or doc.get("run_id")):
        problems.append("problem_id/run_id missing (INV-G1 anchor required)")
    return problems


def load(ws: Path) -> dict | None:
    for base in (Path(ws) / ".sciforge" / "audits",
                 Path(ws) / "experiments",
                 Path(ws) / "results"):
        p = base / "ABLATION_LEDGER.json"
        if p.exists():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError:
                return {"_unreadable": str(p)}
    return None


def evaluate(ws: Path) -> tuple[str, dict | None, list[str]]:
    """Gate entry: -> (status, doc, problems). status in PASS|FAIL|SKIP."""
    from .ladder import experiment_markers
    markers = experiment_markers(ws)
    doc = load(ws)
    if doc is None:
        if markers["any"]:
            return "FAIL", None, [
                "experiment results exist but ABLATION_LEDGER.json is absent — "
                "claims would advance without component ablation "
                "(ScientistTwo §3.4 requires 5–6 plans)"]
        return "SKIP", None, ["no experiment stage reached (ablation not applicable)"]
    if doc.pop("_unreadable", None):
        return "FAIL", None, ["ABLATION_LEDGER.json is not valid JSON"]
    problems = validate(doc)
    return ("FAIL" if problems else "PASS"), doc, problems
