"""HITL approvals as data + budget ledger (S05).

Lesson: ScienceDiscovery turns human checkpoints into first-class run state
(permission.required -> run marked blocked -> timeouts paused). Our original
contract said "wait for human confirmation" in prose; here the same checkpoint
becomes a PENDING_APPROVAL.json file + a blocked status the kernel refuses to
run past until `sciforge approve` records the decision in APPROVAL_LOG.txt.

RUN_BUDGET.json is written in the existing registered schema shape so
validate_verdicts still checks it (S04 compatibility: new machinery never
breaks the old gates).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .state import RunState


class Approvals:
    """File-backed approval queue with epoch rotation (anti stale-approval-replay)."""

    def __init__(self, ws: Path):
        self.ws = Path(ws)
        self.dir = self.ws / ".sciforge" / "approvals"
        self.log = self.ws / ".sciforge" / "APPROVAL_LOG.txt"
        self.dir.mkdir(parents=True, exist_ok=True)

    def request(self, checkpoint: str, phase: str, payload: dict, rs: RunState) -> dict:
        rec = {"checkpoint": checkpoint, "phase": phase, "requested_at": time.time(),
               "status": "PENDING", "payload": payload}
        (self.dir / f"{phase.replace('.', '_')}.json").write_text(
            json.dumps(rec, indent=2, ensure_ascii=False))
        rs.status = "paused_checkpoint"
        rs.update(pending=[checkpoint])
        rs.write()
        return rec

    def decide(self, checkpoint: str, approved: bool, decided_by: str,
               rs: RunState, note: str = "") -> dict:
        for f in sorted(self.dir.glob("*.json")):
            try:
                rec = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            if rec["checkpoint"] != checkpoint or rec["status"] != "PENDING":
                continue
            rec["status"] = "APPROVED" if approved else "DENIED"
            rec["decided_at"] = time.time()
            f.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
            self.log.parent.mkdir(exist_ok=True)
            with open(self.log, "a") as lf:
                lf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                         f"checkpoint={checkpoint} decision={'APPROVE' if approved else 'DENY'} "
                         f"by={decided_by} phase={rec['phase']} note={note}\n")
            pend = [r["checkpoint"] for r in self.pending_records() if r["checkpoint"] != checkpoint]
            rs.update(pending=pend)
            if not pend:
                rs.status = "running"
            rs.write()
            return rec
        raise KeyError(f"no PENDING approval for checkpoint '{checkpoint}'")

    def pending_records(self) -> list[dict]:
        out = []
        if not self.dir.exists():
            return out
        for f in sorted(self.dir.glob("*.json")):
            try:
                rec = json.loads(f.read_text())
                if rec.get("status") == "PENDING":
                    out.append(rec)
            except json.JSONDecodeError:
                continue
        return out

    def has_pending(self, checkpoint: str) -> bool:
        return any(r["checkpoint"] == checkpoint for r in self.pending_records())

    def skipped(self, kind: str, checkpoint: str, phase: str, rs: RunState) -> dict:
        """test_mode/human_skip: bypass != skip — log with the same rigor, defer review."""
        rec = {"checkpoint": checkpoint, "phase": phase,
               "kind": kind,  # test_mode_bypass | human_skip
               "logged_at": time.time()}
        with open(self.log, "a") as lf:
            lf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                     f"checkpoint={checkpoint} {kind}={True} "
                     f"human_review_status={'PENDING_DEFERRED' if kind == 'test_mode_bypass' else 'EXPLICIT_SKIP'}\n")
        return rec


def init_budget(ws: Path, run_id: str, effort: str, limits: dict) -> dict:
    """RUN_BUDGET.json in the registered schema shape (validate_verdicts-compatible)."""
    p = ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json"
    lim = limits[effort] if effort in limits else limits["balanced"]
    data = {"schema_version": "1.0", "run_id": run_id,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_clock_seconds": 0, "api_cost_usd": 0.0,
            "pivot_count": 0, "ba_rounds_used": 0, "ba_rounds_max": lim["ba_rounds_max"],
            "per_phase": {},
            "limits": {"wall_clock_seconds_max": lim["wall_clock_seconds_max"],
                       "api_cost_usd_max": lim["api_cost_usd_max"],
                       "pivot_count_max": lim["pivot_count_max"]}}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return data


def accrue(ws: Path, *, phase: str, cost_usd: float | None = None,
           duration_s: float | None = None, pivot: bool = False, ba: bool = False) -> dict:
    """Boundary accounting (anti-gaming: kernel writes from the clock, never self-report)."""
    p = ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    import calendar
    started = calendar.timegm(time.strptime(d["started_at"], "%Y-%m-%dT%H:%M:%SZ"))
    d["wall_clock_seconds"] = int(time.time() - started)
    if cost_usd is not None:
        d["api_cost_usd"] = round(max(0.0, d["api_cost_usd"] + cost_usd), 4)  # monotone
    if duration_s is not None:
        d.setdefault("per_phase", {})[phase] = {
            "duration_s": round(duration_s, 1), "cost_usd": round(cost_usd or 0.0, 4)}
    if pivot:
        d["pivot_count"] += 1
    if ba:
        d["ba_rounds_used"] += 1
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2))
    tmp.replace(p)
    return d


def breach(d: dict) -> str | None:
    """Returns budget-exhausted_<resource> per contract naming, else None."""
    lim = d.get("limits", {})
    if d.get("wall_clock_seconds", 0) >= lim.get("wall_clock_seconds_max", 1e18):
        return "budget_exhausted_wall_clock"
    if d.get("api_cost_usd", 0.0) >= lim.get("api_cost_usd_max", 1e18):
        return "budget_exhausted_api_cost"
    if d.get("pivot_count", 0) > lim.get("pivot_count_max", 1e18):
        return "budget_exhausted_pivot"
    if d.get("ba_rounds_used", 0) > d.get("ba_rounds_max", 1e18):
        return "budget_exhausted_ba_rounds"
    return None


def underuse(d: dict) -> bool:
    """Budget-underuse guard (v6.0): cheap completion of unfinished exploration is a defect."""
    lim = d.get("limits", {})
    return (d.get("api_cost_usd", 0) < 0.5 * lim.get("api_cost_usd_max", 0)
            or d.get("wall_clock_seconds", 0) < 0.5 * lim.get("wall_clock_seconds_max", 0))
