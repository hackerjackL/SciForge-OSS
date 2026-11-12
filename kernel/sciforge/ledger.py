"""PRODUCTION_LEDGER — the cross-run record of what this installation produced.

Why this exists: the pipeline can run end to end, but "we produce papers
steadily" was unverifiable — runs/ is gitignored, so every run's evidence
evaporated and nothing accumulated. A ledger makes throughput, gate
interception and failure modes countable, which is also the macro-level
selection signal the RSI layer needs (a skill patch that raises the FAIL rate
across runs is visible here, not just inside one run).

Design rules, all learned from defects this project already paid for:

* **Rebuildable from disk, never self-reported.** Every field is derived from
  artifacts on disk (RUNSTATE, verdicts, events, the PDF bytes). A run cannot
  inflate its own record by writing a nicer summary — the same reason
  fairness_gate stopped trusting the agent's ledger.
* **Absence is recorded, not hidden.** A Mode A run driven by a host agent has
  no kernel event log; a run stopped early has no PDF. Those are recorded as
  `unverified` / missing with a reason, never as zero-cost success. The
  UNPROTECTED lesson from gate_all applies: a guarantee that did not run must
  not read as a guarantee that passed.
* **Append-only history, idempotent rebuild.** One JSON object per run per
  line in PRODUCTION_LEDGER.jsonl. Rebuilding replaces a run's row rather than
  duplicating it, so the ledger can be regenerated at any time without
  double-counting.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = "1.0"
LEDGER_NAME = "PRODUCTION_LEDGER.jsonl"

# Lifecycle states a run can be in, derived from RUNSTATE plus disk evidence.
STATUS_COMPLETED = "completed"
STATUS_RUNNING = "running"
STATUS_BLOCKED = "blocked"
STATUS_UNKNOWN = "unknown"


def _read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _runstate(ws: Path) -> dict:
    d = _read_json(ws / ".sciforge" / "RUNSTATE.json")
    if not isinstance(d, dict):
        return {}
    return d.get("data") if isinstance(d.get("data"), dict) else d


def _pdf_facts(ws: Path) -> dict:
    """PDF presence, page count and content hash — the paper's physical proof."""
    pdf = ws / "paper" / "main.pdf"
    if not pdf.is_file():
        return {"present": False}
    try:
        blob = pdf.read_bytes()
    except OSError:
        return {"present": False}
    if not blob.startswith(b"%PDF"):
        # completion_gate's lesson: a file named .pdf that is not a PDF must
        # not count as a produced paper.
        return {"present": False, "reason": "not_a_pdf"}
    pages = None
    import re
    counts = re.findall(rb"/Count\s+(\d+)", blob)
    if counts:
        pages = max(int(c) for c in counts)
    return {"present": True, "bytes": len(blob), "pages": pages,
            "sha256": hashlib.sha256(blob).hexdigest()}


def _verdict_summary(ws: Path) -> dict:
    """Counts over registered verdicts, plus the readiness tier if present.

    Not every registered artifact carries a verdict: EXPERIMENT_MATRIX,
    EVALUATION_PROTOCOL, VERIFICATION_ROUTING, RUN_BUDGET, FIGURE_AUDITS and
    BLINDSPOT_CHECK are declarations/measurements. Counting them as UNKNOWN
    would make the failure statistics lie, so they are tallied separately as
    `declarative`. INVARIANT_CHECK spells its field `overall_verdict`.
    """
    vd = ws / ".sciforge" / "verdicts"
    counts: dict[str, int] = {}
    names: list[str] = []
    declarative: list[str] = []
    if vd.is_dir():
        for p in sorted(vd.glob("*.json")):
            d = _read_json(p)
            if not isinstance(d, dict):
                continue
            names.append(p.stem)
            raw = (d.get("verdict") or d.get("overall_verdict")
                   or d.get("status"))
            if raw is None:
                declarative.append(p.stem)
                continue
            v = str(raw).upper()
            counts[v] = counts.get(v, 0) + 1
    tier = None
    for cand in (vd / "SUBMISSION_READY.json",
                 ws / ".sciforge" / "audits" / "SUBMISSION_READY.json"):
        d = _read_json(cand)
        if isinstance(d, dict) and d.get("tier"):
            tier = d["tier"]
            break
    return {"counts": counts, "n": len(names), "submission_tier": tier,
            "declarative": declarative}


def _event_facts(ws: Path) -> dict:
    """Kernel event-log evidence. A Mode A run legitimately has none."""
    p = ws / ".sciforge" / "events.ndjson"
    if not p.is_file():
        return {"present": False, "reason": "no_kernel_event_log"}
    kinds: dict[str, int] = {}
    total = 0
    first_ts = last_ts = None
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                total += 1
                k = str(ev.get("kind") or "?")
                kinds[k] = kinds.get(k, 0) + 1
                ts = ev.get("ts")
                if isinstance(ts, (int, float)):
                    first_ts = ts if first_ts is None else min(first_ts, ts)
                    last_ts = ts if last_ts is None else max(last_ts, ts)
    except OSError:
        return {"present": False, "reason": "unreadable"}
    chain = None
    try:
        import sys
        kernel = Path(__file__).resolve().parents[1]
        if str(kernel) not in sys.path:
            sys.path.insert(0, str(kernel))
        from sciforge.state import EventLog
        v = EventLog(ws).verify_chain()
        chain = {"ok": bool(v.get("ok")), "legacy": bool(v.get("legacy")),
                 "broken_seq": v.get("broken_seq")}
    except Exception:
        chain = None
    return {"present": True, "events": total,
            "boundaries_committed": kinds.get("boundary_committed", 0),
            "gates_rejected": kinds.get("gate_rejected", 0),
            "loopbacks": kinds.get("loopback", 0),
            "first_ts": first_ts, "last_ts": last_ts, "chain": chain}


def _budget_facts(ws: Path) -> dict:
    d = _read_json(ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json")
    if not isinstance(d, dict):
        return {"present": False}
    return {"present": True,
            "api_cost_usd": d.get("api_cost_usd"),
            "wall_clock_seconds": d.get("wall_clock_seconds"),
            "external_wait_seconds": d.get("external_wait_seconds"),
            "pivot_count": d.get("pivot_count")}


def _derived_status(rs: dict, pdf: dict, events: dict) -> str:
    raw = str(rs.get("status") or "").lower()
    if raw == "completed":
        return STATUS_COMPLETED
    if raw in ("paused_blocked", "killed"):
        return STATUS_BLOCKED
    if raw in ("running", "paused_checkpoint", "created"):
        return STATUS_RUNNING
    # No trustworthy RUNSTATE: fall back to what the disk proves, and say so.
    if pdf.get("present") and events.get("boundaries_committed"):
        return STATUS_COMPLETED
    return STATUS_UNKNOWN


def run_record(ws: Path) -> dict:
    """One ledger row for one run, entirely derived from disk."""
    ws = Path(ws)
    rs = _runstate(ws)
    pdf = _pdf_facts(ws)
    events = _event_facts(ws)
    verdicts = _verdict_summary(ws)
    budget = _budget_facts(ws)
    status = _derived_status(rs, pdf, events)
    # `produced` is deliberately strict: a completed run WITH a real PDF. A
    # completed RUNSTATE alone is exactly the false-completion class that
    # completion_gate was built to catch.
    produced = status == STATUS_COMPLETED and bool(pdf.get("present"))
    unverified: list[str] = []
    if not events.get("present"):
        unverified.append("no_kernel_event_log")
    if events.get("chain") and not events["chain"]["ok"]:
        unverified.append("event_chain_broken")
    if not budget.get("present"):
        unverified.append("no_budget_record")
    if not verdicts["n"]:
        unverified.append("no_registered_verdicts")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": rs.get("run_id") or ws.name,
        "workspace": str(ws),
        "problem_hash": rs.get("problem_hash"),
        "status": status,
        "runstate_status": rs.get("status"),
        "current_phase": rs.get("current_phase"),
        "produced_paper": produced,
        "pdf": pdf,
        "verdicts": verdicts,
        "events": events,
        "budget": budget,
        "unverified": unverified,
    }


def discover_runs(archive: Path) -> list[Path]:
    """Sibling directories that look like runs (have .sciforge/ or PROBLEM.md)."""
    archive = Path(archive)
    if not archive.is_dir():
        return []
    out = []
    for p in sorted(archive.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        if (p / ".sciforge").is_dir() or (p / "PROBLEM.md").is_file():
            out.append(p)
    return out


def build_ledger(archive: Path, out: Path | None = None) -> dict:
    """Rebuild the ledger from disk. Idempotent: one row per run_id."""
    archive = Path(archive)
    out = Path(out) if out else archive / LEDGER_NAME
    rows: dict[str, dict] = {}
    # Preserve rows for runs whose workspace has since been removed — the
    # ledger is the durable record, so deleting a workspace must not erase
    # history. Disk evidence always wins for runs still present.
    if out.is_file():
        with open(out, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    prev = json.loads(line)
                except ValueError:
                    continue
                rid = prev.get("run_id")
                if rid:
                    prev.setdefault("workspace_missing", False)
                    rows[str(rid)] = prev
    for ws in discover_runs(archive):
        rec = run_record(ws)
        rec["workspace_missing"] = False
        rows[rec["run_id"]] = rec
    for rid, rec in rows.items():
        if not Path(rec.get("workspace") or "").is_dir():
            rec["workspace_missing"] = True
    ordered = [rows[k] for k in sorted(rows)]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for rec in ordered:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"ledger": str(out), "runs": len(ordered), "summary": summarize(ordered)}


def summarize(rows: list[dict]) -> dict:
    """Aggregate view: throughput, gate interception, failure modes.

    These are the macro signals the RSI layer needs; per-run gates only see
    one run at a time.
    """
    n = len(rows)
    produced = sum(1 for r in rows if r.get("produced_paper"))
    by_status: dict[str, int] = {}
    tiers: dict[str, int] = {}
    unverified: dict[str, int] = {}
    cost = 0.0
    cost_known = 0
    boundaries = rejected = loopbacks = 0
    for r in rows:
        by_status[r.get("status", "unknown")] = by_status.get(r.get("status", "unknown"), 0) + 1
        t = (r.get("verdicts") or {}).get("submission_tier")
        if t:
            tiers[t] = tiers.get(t, 0) + 1
        for u in r.get("unverified") or []:
            unverified[u] = unverified.get(u, 0) + 1
        b = r.get("budget") or {}
        c = b.get("api_cost_usd")
        if isinstance(c, (int, float)):
            cost += float(c)
            cost_known += 1
        e = r.get("events") or {}
        boundaries += e.get("boundaries_committed") or 0
        rejected += e.get("gates_rejected") or 0
        loopbacks += e.get("loopbacks") or 0
    return {
        "runs": n,
        "papers_produced": produced,
        "production_rate": round(produced / n, 4) if n else None,
        "by_status": by_status,
        "submission_tiers": tiers,
        "unverified_counts": unverified,
        "api_cost_usd_total": round(cost, 6),
        "runs_with_cost": cost_known,
        "cost_per_paper_usd": round(cost / produced, 6) if produced and cost_known else None,
        "boundaries_committed": boundaries,
        "gates_rejected": rejected,
        "loopbacks": loopbacks,
        "gate_interception_rate": round(rejected / (boundaries + rejected), 4)
        if (boundaries + rejected) else None,
    }


def load_ledger(path: Path) -> list[dict]:
    rows = []
    p = Path(path)
    if not p.is_file():
        return rows
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows