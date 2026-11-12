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
import re
import secrets
import time
from pathlib import Path

from .state import EventLog, RunState, open_checkpoint_requests

_CK_LINE = re.compile(r"checkpoint=(\S+)")


def _verified_marks(ws: Path) -> tuple[dict[str, str | None], set[tuple[str, str]]]:
    """Decision facts from the event ledger: {checkpoint: decision} for
    checkpoint_cleared epochs, and {(checkpoint, kind)} for skips.

    Fail-closed on a broken hash chain. The pipeline's checkpoint guard already
    refuses to advance on a broken ledger, but this function is the primitive
    every approval decision reads — trusting forged `checkpoint_cleared` events
    here would leave the defence depending on each caller remembering to check
    first. Legacy chainless logs stay readable (verify_chain reports ok=True).
    """
    cleared: dict[str, str | None] = {}
    skipped: set[tuple[str, str]] = set()
    try:
        log = EventLog(ws)
        if not log.verify_chain().get("ok", True):
            return cleared, skipped
        events = log.replay()
    except Exception:
        return cleared, skipped
    for ev in events:
        pl = ev.get("payload") or {}
        ck = pl.get("checkpoint")
        if not ck:
            continue
        ck = str(ck)
        if ev.get("kind") == "checkpoint_cleared":
            cleared[ck] = pl.get("decision")  # None for legacy epochs
        elif ev.get("kind") == "checkpoint_skipped":
            skipped.add((ck, str(pl.get("kind") or pl.get("skip_kind") or "")))
    return cleared, skipped


def _filter_verified_log(ws: Path, raw: str) -> str:
    """Drop approval-log lines that have no backing event. A hand-written
    'checkpoint=X decision=APPROVE' (or human_skip=True) line in
    APPROVAL_LOG.txt must never be able to clear a human checkpoint."""
    cleared, skipped = _verified_marks(ws)
    kept: list[str] = []
    for line in raw.splitlines():
        m = _CK_LINE.search(line)
        if not m:
            kept.append(line)
            continue
        ck = m.group(1)
        if "decision=" in line:
            dec = line.split("decision=", 1)[1].split()[0]
            mark = cleared.get(ck, "\x00")  # \x00 = never cleared
            if mark == dec or (mark is None and dec == "APPROVE"):
                kept.append(line)
            continue
        if "human_skip=True" in line:
            if (ck, "human_skip") in skipped:
                kept.append(line)
            continue
        if "test_mode_bypass=True" in line:
            if (ck, "test_mode_bypass") in skipped:
                kept.append(line)
            continue
        kept.append(line)
    return "\n".join(kept) + ("\n" if kept else "")


class _VerifiedLog:
    """Path-like view of APPROVAL_LOG.txt used by the kernel. Writes go to the
    real file; reads expose only decision lines backed by the event ledger.
    Path-like so existing callers (`appr.log.exists()`, `open(appr.log, "a")`)
    keep working unchanged."""

    def __init__(self, ws: Path):
        self._path = Path(ws) / ".sciforge" / "APPROVAL_LOG.txt"

    def __fspath__(self) -> str:
        return str(self._path)

    def __str__(self) -> str:
        return str(self._path)

    @property
    def parent(self) -> Path:
        return self._path.parent

    @property
    def name(self) -> str:
        return self._path.name

    def exists(self) -> bool:
        return self._path.exists()

    def read_text(self, encoding=None, errors=None) -> str:
        try:
            raw = self._path.read_text(encoding=encoding or "utf-8",
                                       errors=errors or "strict")
        except (OSError, UnicodeDecodeError):
            return ""
        ws = self._path.parent.parent  # .../.sciforge/APPROVAL_LOG.txt -> ws
        return _filter_verified_log(ws, raw)


class Approvals:
    """File-backed approval queue with event-ledger epochs (anti stale-approval
    replay + anti self-approval). A PENDING record only exists because the
    kernel emitted `checkpoint_requested` with an epoch nonce; a decision is
    accepted only for an open epoch with a matching nonce, and the approval
    log view hides any line the ledger does not back."""

    def __init__(self, ws: Path):
        self.ws = Path(ws)
        self.dir = self.ws / ".sciforge" / "approvals"
        self.log = _VerifiedLog(self.ws)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _emit_cleared(self, checkpoint: str, phase: str, decision: str | None = None,
                      by: str | None = None, nonce: str | None = None) -> None:
        """Close the external-wait timer for this checkpoint in the event log so
        the dual-timer does not keep counting a decision already made. The same
        event is the anti-forgery anchor for the approval log."""
        try:
            payload = {"checkpoint": checkpoint}
            if decision:
                payload["decision"] = decision
            if by:
                payload["by"] = by
            if nonce:
                payload["nonce"] = nonce
            EventLog(self.ws).emit(phase, "checkpoint_cleared", payload)
        except Exception:
            pass

    def request(self, checkpoint: str, phase: str, payload: dict, rs: RunState) -> dict:
        nonce = secrets.token_hex(16)
        rec = {"checkpoint": checkpoint, "phase": phase, "requested_at": time.time(),
               "status": "PENDING", "payload": payload, "nonce": nonce,
               "request_epoch": nonce}
        (self.dir / f"{phase.replace('.', '_')}.json").write_text(
            json.dumps(rec, indent=2, ensure_ascii=False))
        rs.status = "paused_checkpoint"
        rs.update(pending=[checkpoint])
        rs.write()
        # open the external-wait timer in the same transaction that blocks the run
        try:
            EventLog(self.ws).emit(phase, "checkpoint_requested",
                                   {"checkpoint": checkpoint, "phase": phase,
                                    "nonce": nonce})
        except Exception:
            pass
        return rec

    def _file_pending(self, checkpoint: str, req_nonce: str | None = None,
                      req_phase: str | None = None) -> tuple[dict | None, Path | None]:
        candidates: list[tuple[dict, Path]] = []
        for f in sorted(self.dir.glob("*.json")):
            try:
                rec = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if rec.get("checkpoint") == checkpoint and rec.get("status") == "PENDING":
                candidates.append((rec, f))
        if not candidates:
            return None, None
        if req_nonce:
            for rec, f in candidates:  # current epoch wins over stale siblings
                if rec.get("nonce") == req_nonce:
                    return rec, f
            for rec, f in candidates:
                if req_phase and rec.get("phase") == req_phase:
                    return rec, f  # same phase, wrong nonce => tampered
            return None, None  # only stale sibling epochs remain
        return candidates[0]

    def decide(self, checkpoint: str, approved: bool, decided_by: str,
               rs: RunState, note: str = "") -> dict:
        # The decision must answer a kernel-issued, still-open request epoch.
        open_req = open_checkpoint_requests(self.ws).get(checkpoint)
        if open_req is None:
            raise KeyError(f"no PENDING approval for checkpoint '{checkpoint}'")
        req_pl = open_req.get("payload") or {}
        req_nonce = req_pl.get("nonce")
        rec, path = self._file_pending(checkpoint, req_nonce=req_nonce,
                                       req_phase=req_pl.get("phase"))
        if rec is not None:
            if req_nonce and rec.get("nonce") != req_nonce:
                raise PermissionError(
                    f"approval record for '{checkpoint}' does not match the "
                    "kernel-issued request epoch (forged/tampered PENDING file)")
            phase = rec.get("phase") or req_pl.get("phase") or ""
        else:
            # file deleted or hand-marked APPROVED: rebuild from the ledger
            phase = req_pl.get("phase") or open_req.get("phase") or ""
            rec = {"checkpoint": checkpoint, "phase": phase,
                   "requested_at": open_req.get("ts"), "status": "PENDING",
                   "payload": {}, "nonce": req_nonce,
                   "recovered_from": "event_log"}
            path = self.dir / f"{str(phase).replace('.', '_')}.json"
        decision = "APPROVE" if approved else "DENY"
        rec["status"] = "APPROVED" if approved else "DENIED"
        rec["decided_at"] = time.time()
        rec["decided_by"] = decided_by or "unknown"
        rec["decision_epoch"] = req_nonce
        path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        self.log.parent.mkdir(exist_ok=True)
        with open(self.log, "a") as lf:
            lf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                     f"checkpoint={checkpoint} decision={decision} "
                     f"by={rec['decided_by']} phase={phase} note={note}\n")
        self._emit_cleared(checkpoint, phase, decision=decision,
                           by=rec["decided_by"], nonce=req_nonce)  # stop the wait timer
        pend = [r["checkpoint"] for r in self.pending_records()
                if r["checkpoint"] != checkpoint]
        rs.update(pending=pend)
        if not pend:
            rs.status = "running"
        rs.write()
        return rec

    def pending_records(self) -> list[dict]:
        """Pending checkpoints from BOTH sources, fail-closed:
        - event-ledger epochs that are still open (covers deleted/hand-edited
          approval files), and
        - PENDING files whose epoch nonce matches the kernel's request.
        A PENDING file with no kernel request is kept (blocks the run) but is
        marked unverified and cannot be decided through `decide()`."""
        open_reqs = open_checkpoint_requests(self.ws)
        records: dict[str, dict] = {}
        if self.dir.exists():
            for f in sorted(self.dir.glob("*.json")):
                try:
                    rec = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                ck = rec.get("checkpoint")
                if not ck or rec.get("status") != "PENDING":
                    continue
                req = open_reqs.get(ck)
                if req is not None:
                    req_nonce = (req.get("payload") or {}).get("nonce")
                    if req_nonce and rec.get("nonce") != req_nonce:
                        continue  # tampered epoch; ledger record below wins
                    records[ck] = rec
                else:
                    rec = dict(rec)
                    rec["source"] = "file_only"
                    rec["unverified"] = True
                    records[ck] = rec
        for ck, ev in open_reqs.items():
            if ck in records:
                continue
            pl = ev.get("payload") or {}
            records[ck] = {"checkpoint": ck,
                           "phase": pl.get("phase") or ev.get("phase") or "",
                           "requested_at": ev.get("ts"), "status": "PENDING",
                           "payload": {}, "nonce": pl.get("nonce"),
                           "source": "event_log"}
        return sorted(records.values(), key=lambda r: r.get("requested_at") or 0)

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
        try:
            EventLog(self.ws).emit(phase, "checkpoint_skipped",
                                   {"checkpoint": checkpoint, "kind": kind})
        except Exception:
            pass
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


def external_wait_seconds(ws: Path, now: float | None = None) -> float:
    """Dual-timer accounting (C-5 / v1.6): time spent waiting OUTSIDE the
    pipeline's own compute must not consume the run's wall-clock budget. Two
    wait classes, both derived from events.ndjson so a mid-wait crash can't
    leak an open timer (the interval is reconstructed from the log, not from
    mutable state):

      - human approval: checkpoint_requested -> checkpoint_cleared (by name)
      - host-agent execution: host_dispatched -> host_result|host_timeout (by phase)

    An open interval counts up to `now` (still legitimately waiting). Overlaps
    are merged (nested begins don't double-count)."""
    now = now or time.time()
    from .state import EventLog
    spans: list[tuple[float, float | None, str]] = []  # (open_ts, close_ts, key)
    open_by_key: dict[str, float] = {}
    for e in EventLog(ws).replay():
        k, ph, pl = e["kind"], e.get("phase", ""), e.get("payload", {})
        if k == "checkpoint_requested":
            open_by_key[f"ck:{pl.get('checkpoint')}"] = e["ts"]
        elif k == "checkpoint_cleared":
            key = f"ck:{pl.get('checkpoint')}"
            if key in open_by_key:
                spans.append((open_by_key.pop(key), e["ts"], key))
        elif k == "host_dispatched":
            open_by_key[f"h:{ph}"] = e["ts"]
        elif k in ("host_result", "host_timeout"):
            key = f"h:{ph}"
            if key in open_by_key:
                spans.append((open_by_key.pop(key), e["ts"], key))
    for key, t in open_by_key.items():  # still waiting now
        spans.append((t, None, key))
    if not spans:
        return 0.0
    # true merge of overlapping intervals (a checkpoint held open *while* a host
    # agent also runs is ONE wall-clock span, not two summed waits)
    ivs = sorted((s, e if e is not None else now) for s, e, _ in spans)
    total = 0.0
    cs, ce = ivs[0]
    for s, e in ivs[1:]:
        if s <= ce:                 # overlaps/abuts the current block
            ce = max(ce, e)
        else:
            total += max(0.0, ce - cs)
            cs, ce = s, e
    total += max(0.0, ce - cs)
    return total


def accrue(ws: Path, *, phase: str, cost_usd: float | None = None,
           duration_s: float | None = None, pivot: bool = False, ba: bool = False) -> dict:
    """Boundary accounting (anti-gaming: kernel writes from the clock, never self-report)."""
    p = ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    import calendar
    started = calendar.timegm(time.strptime(d["started_at"], "%Y-%m-%dT%H:%M:%SZ"))
    raw_wall = int(time.time() - started)
    wait = external_wait_seconds(ws)          # subtracted from the compute budget
    d["external_wait_seconds"] = int(wait)
    d["wall_clock_seconds"] = max(0, raw_wall - int(wait))
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
