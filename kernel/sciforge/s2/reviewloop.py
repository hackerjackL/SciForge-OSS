"""Score-driven rebuttal loop + Meta-Review (ScientistTwo §3.5/§3.6).

Copied rules:

- dual-threshold discipline: the phase-14 boundary floor stays at **6**
  (our legacy contract), but the ScientistTwo acceptance bar is **8** —
  any calibrated panel score < 8 triggers a *rebuttal*: a plan of
  supplementary experiment tasks that are REALLY run, then backfilled into
  the manuscript, then re-reviewed (<= 2 rounds);
- Meta-Review {ACCEPT | REFINE}: ACCEPT only at score >= threshold with no
  surviving fatals; REFINE means the method changes, ablations rerun and the
  paper re-enters the loop (we do not paper over a REFINE with wording).

The LLM side (planning experiment supplements) stays host-side; the kernel
owns the threshold, the round cap, the plan skeleton derived from panel
fatals, and the ACCEPT/REFINE decision — so "score < 8 => rebuttal" cannot be
talked past.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

DEFAULT_THRESHOLD = 8.0
MAX_REBUTTAL_ROUNDS = 2
BOUNDARY_FLOOR = 6.0  # legacy phase-14 boundary gate (REVIEW_STATE.last_score >= 6)
PLAN_REL = Path(".sciforge") / "audits" / "REBUTTAL_PLAN.json"


def threshold() -> float:
    """Rebuttal/acceptance threshold. env SCIFORGE_REVIEW_THRESHOLD overrides
    (bench harnesses and lower-stakes runs may calibrate it down)."""
    try:
        return float(os.environ.get("SCIFORGE_REVIEW_THRESHOLD", DEFAULT_THRESHOLD))
    except ValueError:
        return DEFAULT_THRESHOLD


def needs_rebuttal(score: float | None, thr: float | None = None) -> bool:
    if score is None:
        return False
    return float(score) < (threshold() if thr is None else float(thr))


def seed_rebuttal_plan(panel: dict, score: float | None, round_no: int = 1,
                       thr: float | None = None) -> dict:
    """Mechanical seed plan: one supplementary task per panel concern.
    The host refines task descriptions into runnable experiment specs; the
    structure (round cap, score, provenance) is kernel-owned."""
    thr = threshold() if thr is None else float(thr)
    tasks = []
    for i, item in enumerate((panel.get("fatal") or [])[:8]):
        tasks.append({"id": f"R{round_no}T{i + 1}", "kind": "experiment_redesign",
                      "source": "fatal", "description": str(item)[:300],
                      "target_artifact": "experiments/ (supplementary run)"})
    for i, item in enumerate((panel.get("kill_arguments") or [])[:4]):
        tasks.append({"id": f"R{round_no}K{i + 1}", "kind": "experiment",
                      "source": "kill_argument", "description": str(item)[:300],
                      "target_artifact": "experiments/ (rebuttal experiment)"})
    if not tasks:
        tasks.append({"id": f"R{round_no}E1", "kind": "analysis",
                      "source": "score_gap",
                      "description": (f"panel score {score} below threshold {thr} "
                                      "with no fatal listed — strengthen the weakest "
                                      "rubric axis with a supplementary analysis"),
                      "target_artifact": "experiments/ or paper/ (evidence backfill)"})
    return {
        "schema_version": "1.0",
        "round": round_no,
        "max_rounds": MAX_REBUTTAL_ROUNDS,
        "score": score,
        "threshold": thr,
        "trigger": f"score {score} < threshold {thr}" if needs_rebuttal(score, thr)
                   else "seed (score at/above threshold)",
        "tasks": tasks,
        "rule": ("supplementary tasks MUST be executed and backfilled into the "
                 "manuscript before re-review; wording-only rebuttals are "
                 "round_invalid (anti-shrinkage)"),
        "ts": time.time(),
    }


def write_plan(ws: Path, plan: dict) -> Path:
    p = Path(ws) / PLAN_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    return p


def load_plan(ws: Path) -> dict | None:
    p = Path(ws) / PLAN_REL
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def meta_review(score: float | None, panel: dict | None,
                rebuttal_rounds: int = 0, thr: float | None = None) -> dict:
    """Meta-Review decision (ScientistTwo §3.6)."""
    thr = threshold() if thr is None else float(thr)
    panel = panel or {}
    fatals = panel.get("fatal") or []
    if score is None:
        decision = "REFINE"
        reason = "no usable panel score"
    elif needs_rebuttal(score, thr):
        decision = "REFINE" if rebuttal_rounds >= MAX_REBUTTAL_ROUNDS else "PENDING_REBUTTAL"
        reason = (f"score {score} < {thr} after {rebuttal_rounds}/{MAX_REBUTTAL_ROUNDS} "
                  f"rebuttal round(s)")
    elif fatals:
        decision = "REFINE"
        reason = f"{len(fatals)} surviving fatal concern(s) despite score {score}"
    else:
        decision = "ACCEPT"
        reason = f"score {score} >= threshold {thr}, no fatals"
    return {"decision": decision, "score": score, "threshold": thr,
            "rebuttal_rounds": rebuttal_rounds, "reason": reason,
            "fatals": fatals[:8]}


def load_meta(ws: Path) -> dict | None:
    """Meta-review as recorded on REVIEW_STATE.json (host or kernel wrote it)."""
    p = Path(ws) / ".sciforge" / "verdicts" / "REVIEW_STATE.json"
    try:
        return json.loads(p.read_text()).get("meta_review")
    except Exception:
        return None
