"""Research Execution Plan (v1.7.2, D4 — SCION REP concept, own implementation).

SCION's load-bearing idea: compile high-level intent into **staged objectives
with dependencies, verification checkpoints, expected artifacts and FALLBACK
CONDITIONS** — instead of letting an agent improvise recovery at failure time
(the observed failure class: mid-run agent deaths recovered by guessing from
disk). Our phasegraph is the static law; the REP is the per-run verdict:

  phase 1 compiles REP.json from: phasegraph (objectives + gates),
  domain-signature (route + intensity), intake manifest (inherited phases),
  effort limits (budgets), and the loopback registry (fallback conditions).

Boundaries then check two things mechanically:
  1. REP exists from phase 1 onward (a run without a plan is BLOCKED at 2);
  2. when a loopback fires, the REP's fallback condition for that phase was
     the one consumed (an off-plan recovery = contract violation, same
     spirit as the loopback registry's off-table rule).

Pure stdlib; the host still executes, the kernel still gates.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .pipeline import PhaseGraph

REP_REL = Path(".sciforge") / "audits" / "REP.json"


def compile_rep(ws: Path, graph: PhaseGraph | None = None) -> dict:
    ws = Path(ws)
    graph = graph or PhaseGraph()
    routing = None
    try:
        routing = json.loads((ws / ".sciforge" / "verdicts" /
                              "VERIFICATION_ROUTING.json").read_text())
    except Exception:
        pass
    intake = None
    try:
        intake = json.loads((ws / ".sciforge" / "verdicts" /
                             "INTAKE_MANIFEST.json").read_text())
    except Exception:
        pass
    sig = None
    try:
        sig = json.loads((ws / ".sciforge" / "refine-logs" /
                          "domain-signature.json").read_text())
    except Exception:
        pass

    objectives, fallbacks = [], {}
    for ph in graph.order:
        p = graph.phases[ph]
        objectives.append({
            "phase": ph, "name": p.get("name"),
            "mode": p.get("mode"),
            "verify": [g.get("cmd") or g.get("check")
                       for g in (p.get("gates") or ([p["gate"]] if p.get("gate") else []))],
            "artifacts": p.get("produces", []),
            "inherited": (intake or {}).get("phase_plan", {}).get(ph) in
                         ("inherit", "inherit-rewrite"),
        })
        lb = p.get("loopback")
        if lb:
            fallbacks[ph] = {
                "on": lb.get("on"), "target": lb.get("target"),
                "budget": lb.get("budget", -1),
                "condition": (f"verdict {lb.get('on')} at phase {ph} with "
                              f"budget left; consume prior failure evidence"),
            }
            if lb.get("ba"):
                fallbacks[ph]["ba"] = {"target": lb["ba"].get("target"),
                                       "budget": lb["ba"].get("budget", 2),
                                       "shared": "ba"}

    rep = {
        "schema_version": "1.0",
        "compiled_at": time.time(),
        "route": (routing or {}).get("route", "unknown"),
        "evidence_type": (routing or {}).get("evidence_type", "unknown"),
        "discipline": _flags(ws).get("discipline", "strict"),  # matches pipeline.start default
        "claim_mode": _flags(ws).get("claim_mode", "attribution"),
        "objectives": objectives,
        "fallbacks": fallbacks,
        "budgets": graph.limits,
        "intake": bool(intake),
        "signature": bool(sig),
    }
    p = ws / REP_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    return rep


def _flags(ws: Path) -> dict:
    try:
        d = json.loads((Path(ws) / ".sciforge" / "RUNSTATE.json").read_text())
        return (d.get("data") or d).get("flags", {}) or {}
    except Exception:
        return {}


def load(ws: Path) -> dict | None:
    try:
        return json.loads((Path(ws) / REP_REL).read_text())
    except Exception:
        return None


def check_plan(ws: Path) -> dict:
    """Boundary check: REP must exist from phase 2 onward.

    SKIP (not FAIL) when phase 1 was never actually entered (direct boundary
    calls in tests / hosts that drive phases out of order); FAIL when a real
    run passed phase 1 but carries no compiled plan — that is the improvising
    recovery class the REP exists to kill.
    """
    rep = load(ws)
    if rep is None:
        entered_1 = False
        try:
            from .state import EventLog
            entered_1 = any(e["kind"] == "phase_entered" and e["phase"] == "1"
                            for e in EventLog(Path(ws)).replay())
        except Exception:
            entered_1 = False
        if not entered_1:
            return {"status": "SKIP", "note": "phase 1 not entered yet"}
        return {"status": "FAIL",
                "note": "REP.json missing although phase 1 ran — phase 1 must "
                        "compile the run plan"}
    return {"status": "PASS", "objectives": len(rep.get("objectives", [])),
            "fallbacks": len(rep.get("fallbacks", {}))}


def fallback_consumed(ws: Path, phase: str, loopback_id: str) -> dict:
    """Did the fired loopback match a REP-declared fallback condition?"""
    rep = load(ws) or {}
    fb = (rep.get("fallbacks") or {}).get(phase)
    if fb is None:
        return {"status": "FAIL",
                "note": f"loopback {loopback_id} at phase {phase} is OFF-PLAN "
                        f"(not in REP fallbacks) — contract violation"}
    return {"status": "PASS", "condition": fb.get("condition")}
