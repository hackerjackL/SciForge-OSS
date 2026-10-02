"""SOTA hill-climbing driver (v1.7.1, mode/claim_mode=sota).

The missing loop: given a frozen problem + an incumbent (published SOTA
number or a reproduced baseline), iterate method variants against it with
the SAME anti-Goodhart machinery the rest of the kernel uses:

    reproduce incumbent (ladder baseline arm — no comparison against air)
      -> propose variant (memory-prior + exploration guarantee)
      -> host executes subset->full ladder + ablation for the variant
      -> record: closed fractions per scored leg -> s2.headline geomean
      -> hard gates (capability floor + regression CIs) invalidate a "win"
      -> promote only on strict headline improvement; plateau/budget stops

The kernel OWNS the bookkeeping (state file, promotion rule, stop rule);
the host owns the science (variant design + execution). Nothing here trains
models — the trainer backend is a seam (`experiments/sota/<variant>/`), so
CPU numpy arms and Linux-CUDA LoRA runs use the identical loop.

Machine artifacts:
  .sciforge/verdicts/SOTA_TARGET.json   (declared at phase 0/5, hash-bound)
  .sciforge/audits/SOTA_STATE.json      (iteration ledger, kernel-written)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import memory as memory_mod
from .s2 import headline as headline_mod
from .s2 import ideas as ideas_mod
from .s2 import ladder as ladder_mod

TARGET_REL = Path(".sciforge") / "verdicts" / "SOTA_TARGET.json"
STATE_REL = Path(".sciforge") / "audits" / "SOTA_STATE.json"
DEFAULT_MAX_ITER = 12
DEFAULT_PLATEAU = 3


# ---------------- target / state io ----------------

def load_target(ws: Path) -> dict | None:
    try:
        return json.loads((Path(ws) / TARGET_REL).read_text())
    except Exception:
        return None


def load_state(ws: Path) -> dict:
    try:
        return json.loads((Path(ws) / STATE_REL).read_text())
    except Exception:
        return {"schema_version": "1.0", "iterations": [],
                "best": None, "plateau": 0, "status": "open"}


def save_state(ws: Path, state: dict) -> Path:
    p = Path(ws) / STATE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    return p


# ---------------- loop ----------------

def next_variant(ws: Path, problem: str = "") -> dict:
    """Assemble the next variant proposal payload for the host bundle.

    Priors come from the cross-run failure memory (memory.query over the
    problem text) plus the exploration guarantee (an unexplored seed id when
    the run keeps an IDEA_EVOLUTION ledger). The kernel never invents science;
    it hands the host its own history so iteration N+1 cannot repeat N.
    """
    state = load_state(ws)
    target = load_target(ws) or {}
    tried = [it.get("variant") for it in state.get("iterations", [])]
    priors = []
    idx = memory_mod.default_index_path()
    if idx.exists():
        priors = memory_mod.query(idx, problem or target.get("problem", ""),
                                  k=6, min_sim=0.12)
    seed = ideas_mod.next_exploration_seed(ws)
    return {
        "iteration": len(state.get("iterations", [])) + 1,
        "tried_variants": tried,
        "incumbent": target.get("incumbent"),
        "benchmarks": target.get("benchmarks", []),
        "memory_priors": [{"text": p["text"][:300], "sim": p["sim"],
                           "run": p.get("run_id")} for p in priors],
        "exploration_seed": seed,
        "contract": ("execute subset->full ladder + 5-6 ablations for the new "
                     "variant; report per-leg scores WITH CIs; the kernel "
                     "decides promotion via s2.headline gates"),
    }


def record_iteration(ws: Path, variant: str, legs: dict[str, dict],
                     note: str = "") -> dict:
    """legs: {bench: {"score": x, "ci": [lo, hi]}}. Returns the decision record.

    closed fractions are computed against the declared incumbent/optimum per
    leg; the headline is the geomean (any leg at baseline zeroes it); the hard
    gates invalidate significant regressions and capability-floor breaches.
    """
    target = load_target(ws) or {}
    state = load_state(ws)
    benches = {b["name"]: b for b in target.get("benchmarks", [])}
    closed, per_leg_ci = {}, {}
    for name, leg in legs.items():
        b = benches.get(name) or {}
        base = float(b.get("baseline", leg.get("baseline", 0.0)))
        opt = float(b.get("optimum", b.get("incumbent", leg.get("score", 0.0))))
        direction = b.get("direction", target.get("direction", "maximize"))
        score = float(leg["score"])
        if direction == "minimize":
            score, base, opt = -score, -base, -opt
        closed[name] = headline_mod.closed_fraction(score, base, opt)
        ci = leg.get("ci")
        if ci:
            lo, hi = (-float(ci[1]), -float(ci[0])) if direction == "minimize" \
                else (float(ci[0]), float(ci[1]))
            per_leg_ci[name] = (lo, hi, base, base)
    gates = headline_mod.gates(closed, per_leg_ci=per_leg_ci)
    head = gates["headline"]
    best = state.get("best") or {"headline": -1.0}
    improved = gates["valid"] and head > best.get("headline", -1.0)
    rec = {"ts": time.time(), "variant": variant, "closed": closed,
           "headline": round(head, 6), "valid": gates["valid"],
           "invalid_reasons": gates["reasons"], "promoted": bool(improved),
           "note": note[:400]}
    state.setdefault("iterations", []).append(rec)
    if improved:
        state["best"] = {"variant": variant, "headline": round(head, 6),
                         "closed": closed}
        state["plateau"] = 0
    else:
        state["plateau"] = state.get("plateau", 0) + 1
    max_iter = int((target.get("budget") or {}).get("max_iterations",
                                                    DEFAULT_MAX_ITER))
    plateau_lim = int((target.get("budget") or {}).get("plateau_rounds",
                                                       DEFAULT_PLATEAU))
    if state["plateau"] >= plateau_lim or len(state["iterations"]) >= max_iter:
        state["status"] = "stopped"
        state["stop_reason"] = ("plateau" if state["plateau"] >= plateau_lim
                                else "iteration_budget")
    save_state(ws, state)
    return rec


def status(ws: Path) -> dict:
    state = load_state(ws)
    target = load_target(ws)
    return {"status": state.get("status", "open"),
            "iterations": len(state.get("iterations", [])),
            "plateau": state.get("plateau", 0),
            "best": state.get("best"),
            "stop_reason": state.get("stop_reason"),
            "target_declared": target is not None,
            "ladder_present": ladder_mod.load(ws) is not None}
