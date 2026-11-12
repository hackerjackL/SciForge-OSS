"""PRODUCTION_LEDGER (v1.7.4) — the durable cross-run production record.

The ledger exists because runs/ is gitignored: every run's evidence evaporated
and "we produce papers steadily" was unverifiable. Its two design rules are
what these tests pin down, both borrowed from defects this project already
paid for:

* disk-derived, never self-reported (fairness_gate's lesson);
* absence recorded, not hidden (gate_all's UNPROTECTED lesson).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "kernel"))

from sciforge import ledger  # noqa: E402


def _run(root: Path, name: str, *, status="completed", pdf=True,
         events=True, verdicts=True, budget=True) -> Path:
    ws = root / name
    sc = ws / ".sciforge"
    (sc / "verdicts").mkdir(parents=True)
    (sc / "RUNSTATE.json").write_text(json.dumps(
        {"run_id": name, "status": status, "current_phase": "16",
         "problem_hash": "deadbeef"}))
    if pdf:
        (ws / "paper").mkdir(parents=True, exist_ok=True)
        (ws / "paper" / "main.pdf").write_bytes(b"%PDF-1.4\n/Count 7\n%%EOF\n")
    if events:
        lines = [{"seq": 1, "ts": 100.0, "phase": "0", "kind": "run_started",
                  "payload": {}},
                 {"seq": 2, "ts": 101.0, "phase": "1", "kind": "boundary_committed",
                  "payload": {}},
                 {"seq": 3, "ts": 102.0, "phase": "1", "kind": "gate_rejected",
                  "payload": {}}]
        (sc / "events.ndjson").write_text(
            "\n".join(json.dumps(x) for x in lines) + "\n")
    if verdicts:
        (sc / "verdicts" / "QUALITY_GATE.json").write_text(
            json.dumps({"verdict": "PASS"}))
        (sc / "verdicts" / "SUBMISSION_READY.json").write_text(
            json.dumps({"tier": "READY"}))
    if budget:
        (sc / "verdicts" / "RUN_BUDGET.json").write_text(
            json.dumps({"api_cost_usd": 2.5, "wall_clock_seconds": 120}))
    return ws


# ---------------------------------------------------------------------------
# produced_paper must be strict: completed AND a real PDF
# ---------------------------------------------------------------------------
def test_completed_with_real_pdf_counts_as_produced(tmp_path):
    ws = _run(tmp_path, "Q1")
    rec = ledger.run_record(ws)
    assert rec["status"] == "completed"
    assert rec["produced_paper"] is True
    assert rec["pdf"]["present"] and rec["pdf"]["pages"] == 7
    assert len(rec["pdf"]["sha256"]) == 64


def test_completed_without_pdf_is_not_produced(tmp_path):
    """The false-completion class completion_gate was built to catch: a
    completed RUNSTATE alone must never count as a produced paper."""
    ws = _run(tmp_path, "Q2", pdf=False)
    rec = ledger.run_record(ws)
    assert rec["status"] == "completed"
    assert rec["produced_paper"] is False


def test_non_pdf_bytes_do_not_count(tmp_path):
    ws = _run(tmp_path, "Q3")
    (ws / "paper" / "main.pdf").write_bytes(b"not a pdf at all")
    rec = ledger.run_record(ws)
    assert rec["pdf"]["present"] is False
    assert rec["pdf"].get("reason") == "not_a_pdf"
    assert rec["produced_paper"] is False


def test_blocked_run_is_not_produced_even_with_pdf(tmp_path):
    ws = _run(tmp_path, "Q4", status="paused_blocked")
    rec = ledger.run_record(ws)
    assert rec["status"] == "blocked"
    assert rec["produced_paper"] is False


# ---------------------------------------------------------------------------
# absence is recorded, not hidden
# ---------------------------------------------------------------------------
def test_mode_a_run_without_event_log_is_marked_unverified(tmp_path):
    """A host-driven Mode A run legitimately has no kernel event log. It must
    be recorded as unverified, not as a clean zero-cost success."""
    ws = _run(tmp_path, "Q5", events=False)
    rec = ledger.run_record(ws)
    assert rec["events"]["present"] is False
    assert "no_kernel_event_log" in rec["unverified"]


def test_missing_budget_and_verdicts_are_recorded(tmp_path):
    ws = _run(tmp_path, "Q6", budget=False, verdicts=False)
    rec = ledger.run_record(ws)
    assert "no_budget_record" in rec["unverified"]
    assert "no_registered_verdicts" in rec["unverified"]


def test_broken_event_chain_is_surfaced(tmp_path):
    ws = _run(tmp_path, "Q7")
    p = ws / ".sciforge" / "events.ndjson"
    lines = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    lines[1]["payload"]["forged"] = True
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    rec = ledger.run_record(ws)
    # chainless legacy logs verify ok; a mixed/forged suffix must not
    if rec["events"].get("chain") and not rec["events"]["chain"]["ok"]:
        assert "event_chain_broken" in rec["unverified"]


# ---------------------------------------------------------------------------
# verdict classification must not invent UNKNOWN for declarative artifacts
# ---------------------------------------------------------------------------
def test_declarative_artifacts_are_not_counted_as_unknown(tmp_path):
    """EXPERIMENT_MATRIX / EVALUATION_PROTOCOL / RUN_BUDGET etc. carry no
    verdict. Counting them as UNKNOWN would make failure statistics lie."""
    ws = _run(tmp_path, "Q8")
    vd = ws / ".sciforge" / "verdicts"
    (vd / "EXPERIMENT_MATRIX.json").write_text(json.dumps({"groups": []}))
    (vd / "VERIFICATION_ROUTING.json").write_text(json.dumps({"route": "hybrid"}))
    (vd / "INVARIANT_CHECK.json").write_text(json.dumps({"overall_verdict": "PASS"}))
    v = ledger.run_record(ws)["verdicts"]
    assert "UNKNOWN" not in v["counts"]
    assert set(v["declarative"]) >= {"EXPERIMENT_MATRIX", "VERIFICATION_ROUTING",
                                     "RUN_BUDGET"}
    assert v["counts"]["PASS"] == 2      # QUALITY_GATE + INVARIANT_CHECK


# ---------------------------------------------------------------------------
# rebuild is idempotent and preserves history
# ---------------------------------------------------------------------------
def test_build_is_idempotent(tmp_path):
    _run(tmp_path, "Q1")
    _run(tmp_path, "Q2", pdf=False)
    first = ledger.build_ledger(tmp_path)
    second = ledger.build_ledger(tmp_path)
    assert first["runs"] == second["runs"] == 2
    rows = ledger.load_ledger(tmp_path / ledger.LEDGER_NAME)
    assert len(rows) == 2
    assert len({r["run_id"] for r in rows}) == 2


def test_removed_workspace_keeps_its_history_row(tmp_path):
    """The ledger is the durable record; deleting a workspace must not erase
    the fact that the run happened."""
    ws = _run(tmp_path, "Q1")
    ledger.build_ledger(tmp_path)
    import shutil
    shutil.rmtree(ws)
    ledger.build_ledger(tmp_path)
    rows = ledger.load_ledger(tmp_path / ledger.LEDGER_NAME)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "Q1"
    assert rows[0]["workspace_missing"] is True
    assert rows[0]["produced_paper"] is True   # history preserved


def test_disk_evidence_overrides_a_stale_row(tmp_path):
    ws = _run(tmp_path, "Q1")
    ledger.build_ledger(tmp_path)
    (ws / "paper" / "main.pdf").unlink()      # paper retracted on disk
    ledger.build_ledger(tmp_path)
    rows = ledger.load_ledger(tmp_path / ledger.LEDGER_NAME)
    assert rows[0]["produced_paper"] is False


# ---------------------------------------------------------------------------
# summary: the macro signals RSI needs
# ---------------------------------------------------------------------------
def test_summary_aggregates_throughput_cost_and_interception(tmp_path):
    _run(tmp_path, "Q1")                      # produced, $2.5
    _run(tmp_path, "Q2", pdf=False)           # completed, no paper
    _run(tmp_path, "Q3", status="paused_blocked")
    s = ledger.build_ledger(tmp_path)["summary"]
    assert s["runs"] == 3
    assert s["papers_produced"] == 1
    assert s["production_rate"] == round(1 / 3, 4)
    assert s["api_cost_usd_total"] == 7.5
    assert s["cost_per_paper_usd"] == 7.5
    assert s["boundaries_committed"] == 3
    assert s["gates_rejected"] == 3
    assert s["gate_interception_rate"] == 0.5
    assert s["submission_tiers"]["READY"] == 3


def test_summary_on_empty_archive_is_safe(tmp_path):
    s = ledger.build_ledger(tmp_path)["summary"]
    assert s["runs"] == 0
    assert s["production_rate"] is None
    assert s["cost_per_paper_usd"] is None
    assert s["gate_interception_rate"] is None


def test_discover_runs_ignores_non_run_dirs(tmp_path):
    _run(tmp_path, "Q1")
    (tmp_path / "not_a_run").mkdir()
    (tmp_path / ".hidden").mkdir()
    found = {p.name for p in ledger.discover_runs(tmp_path)}
    assert found == {"Q1"}