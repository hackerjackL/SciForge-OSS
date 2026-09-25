"""Run state + event-sourcing for the SciForge kernel (S01/S02).

The event log (.sciforge/events.ndjson) is the durable truth; RUNSTATE.json is
a derived snapshot rewritten at every boundary. A crashed run recovers by
replaying events: status interrupted -> resume from next_action. This mirrors
ScienceDiscovery's events.ndjson + `interrupted` lifecycle and DeepScientist's
replayable quest state, but for our 21-phase DAG.

Stdlib only. Every event carries: seq, ts, phase, kind, payload.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class EventLog:
    """Append-only NDJSON event stream; replay = authoritative state rebuild."""

    def __init__(self, ws: Path):
        self.ws = Path(ws)
        self.path = self.ws / ".sciforge" / "events.ndjson"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        if self.path.exists():
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self._seq = max(self._seq, int(json.loads(line)["seq"]))
                        except Exception:
                            pass

    def emit(self, phase: str, kind: str, payload: dict | None = None) -> dict:
        self._seq += 1
        ev = {"seq": self._seq, "ts": time.time(), "phase": phase, "kind": kind,
              "payload": payload or {}}
        with open(self.path, "a") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def replay(self):
        if not self.path.exists():
            return []
        out = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # torn write during crash; skip, keep replaying
        return out


class RunState:
    """RUNSTATE.json v2 — derived snapshot + resume contract (output-protocol compatible)."""

    FILENAME = "RUNSTATE.json"

    def __init__(self, ws: Path):
        self.ws = Path(ws)
        self.path = self.ws / ".sciforge" / self.FILENAME
        self.data = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.data = {}

    # ---- lifecycle status: exactly the registered RUNSTATE.schema.json enum ----
    STATUS = ("running", "paused_checkpoint", "paused_blocked", "completed", "killed")

    @property
    def status(self) -> str:
        return self.data.get("status", "created")

    @status.setter
    def status(self, v: str):
        assert v in self.STATUS, v
        self.data["status"] = v

    def update(self, *, phase: str | None = None, next_action: str | None = None,
               last_boundary: str | None = None, pending: list | None = None,
               budget_snapshot: dict | None = None, verdict: str | None = None,
               reason_code: str | None = None):
        d = self.data
        if phase is not None:
            d["current_phase"] = phase
        if next_action is not None:
            d["next_action"] = next_action
        if last_boundary is not None:
            d["last_completed_boundary"] = last_boundary
        if pending is not None:
            d["pending_approvals"] = pending
        if budget_snapshot is not None:
            d["budget_snapshot"] = budget_snapshot
        if verdict is not None:
            d["phase_verdicts"] = d.get("phase_verdicts", {})
            d["phase_verdicts"][d.get("current_phase", "")] = verdict
        if reason_code is not None:
            d["reason_code"] = reason_code
        d["schema_version"] = "2.0"
        d["updated_at"] = time.time()

    def write(self):
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
        os.replace(tmp, self.path)  # atomic: torn RUNSTATE can never strand a run

    @classmethod
    def open_workspace(cls, ws: Path, run_id: str, problem: str) -> "RunState":
        ws = Path(ws)
        (ws / ".sciforge" / "verdicts").mkdir(parents=True, exist_ok=True)
        (ws / ".sciforge" / "logs").mkdir(parents=True, exist_ok=True)
        (ws / ".sciforge" / "refine-logs").mkdir(parents=True, exist_ok=True)
        rs = cls(ws)
        if rs.data and rs.status not in ("completed", "failed", "cancelled"):
            raise FileExistsError(
                f"workspace {ws} has live run {rs.data.get('run_id')} ({rs.status}); "
                "use `sciforge resume` or a fresh dir")
        rs.data = {"run_id": run_id, "problem": problem,
                   "problem_hash": None, "phase_order_source": "kernel/config/phasegraph.json",
                   "created_at": time.time()}
        return rs


def holder_alive(ws: Path) -> bool:
    """Kernel lockfile = crash detector (schema-safe: no new RUNSTATE status values)."""
    lock = ws / ".sciforge" / "kernel.lock"
    if not lock.exists():
        return False
    try:
        pid = int(lock.read_text().strip())
        os.kill(pid, 0)  # 0 = liveness probe, sends nothing
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def take_lock(ws: Path):
    (ws / ".sciforge" / "kernel.lock").write_text(str(os.getpid()))


def release_lock(ws: Path):
    try:
        (ws / ".sciforge" / "kernel.lock").unlink()
    except FileNotFoundError:
        pass


def recover(log: EventLog, rs: RunState, ws: Path) -> str:
    """Startup recovery protocol. Returns: fresh | resume | completed | wait.

    Process death mid-run => lockfile orphaned => `running` status is stale,
    replay decides the resume point (dangling boundaries are redone). Mirrors
    SciDis: `interrupted` runs recover after process failure; DeepScientist:
    events are replayable, so the log outranks any snapshot.
    """
    if not rs.data:
        return "fresh"
    if rs.status in ("completed", "killed"):
        return "completed"
    if rs.status == "paused_checkpoint" and not Approvals_pending(ws):
        # human decided elsewhere (approve wrote the log); resume into running
        rs.status = "running"
        rs.write()
    if rs.status == "running" and not holder_alive(ws):
        last = log.replay()
        uncommitted = [e for e in last if e["kind"] == "phase_done"]
        committed = {e["payload"].get("phase") for e in last if e["kind"] == "boundary_committed"}
        dangling = [e["payload"]["phase"] for e in uncommitted
                    if e["payload"].get("phase") not in committed]
        rs.update(next_action=f"redo boundaries: {dangling}" if dangling else rs.data.get("next_action", ""))
        log.emit(rs.data.get("current_phase", "?"), "recovered",
                 {"from": "crash", "dangling_boundaries": dangling})
        return "resume"
    if holder_alive(ws) and rs.status == "running":
        return "wait"  # another kernel owns this workspace
    return "resume"


def Approvals_pending(ws: Path) -> bool:
    d = Path(ws) / ".sciforge" / "approvals"
    if not d.exists():
        return False
    for f in d.glob("*.json"):
        try:
            if json.loads(f.read_text()).get("status") == "PENDING":
                return True
        except Exception:
            continue
    return False
