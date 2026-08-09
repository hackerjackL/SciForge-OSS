"""Regression tests for the external verifiers' workspace path resolution.

v6.0 moved the verdict home from ``{ws}/verdicts/`` to
``{ws}/.sciforge/verdicts/``. The shell verifiers originally only looked at
the v5.2 / pre-v5.2 locations, which made them report "not found" on every
v6.0 workspace (bug fixed in 1.3.1). These tests pin the resolution order:

    .sciforge/verdicts/   (v6.0 canonical)
    verdicts/             (v5.2 fallback)
    review-stage/ paper/  (pre-v5.2 fallbacks)

Runtime target: well under 5 s (bash + python3 JSON checks only).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_VERIFIER = REPO_ROOT / "scripts" / "verifiers" / "verify_review_ledger.sh"
AUDITS_VERIFIER = REPO_ROOT / "scripts" / "verifiers" / "verify_paper_audits.sh"

VALID_LEDGER = {
    "schema_version": "1.0",
    "details": {
        "rounds": [
            {"round": 1, "score": 7, "verdict": "PASS", "action_items": [], "phase": "14"}
        ]
    },
}


def run_verifier(script: Path, workspace: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(script), str(workspace)],
        capture_output=True, text=True, timeout=60,
    )


def write_ledger(workspace: Path, rel_dir: str) -> None:
    target = workspace / rel_dir
    target.mkdir(parents=True, exist_ok=True)
    (target / "REVIEW_LEDGER.json").write_text(
        json.dumps(VALID_LEDGER, indent=2) + "\n", encoding="utf-8"
    )


def test_ledger_verifier_finds_v6_sciforge_path(tmp_path):
    ws = tmp_path / "Q001"
    write_ledger(ws, ".sciforge/verdicts")
    proc = run_verifier(LEDGER_VERIFIER, ws)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ".sciforge/verdicts/REVIEW_LEDGER.json" in proc.stdout


def test_ledger_verifier_still_reads_v52_fallback(tmp_path):
    ws = tmp_path / "Q001"
    write_ledger(ws, "verdicts")
    proc = run_verifier(LEDGER_VERIFIER, ws)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ledger_verifier_still_reads_pre_v52_fallback(tmp_path):
    ws = tmp_path / "Q001"
    write_ledger(ws, "review-stage")
    proc = run_verifier(LEDGER_VERIFIER, ws)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ledger_verifier_prefers_v6_over_legacy(tmp_path):
    """When both exist, the v6.0 canonical copy wins (writes never go to the
    legacy paths, so a stale legacy copy must not shadow the live one)."""
    ws = tmp_path / "Q001"
    write_ledger(ws, ".sciforge/verdicts")
    stale = dict(VALID_LEDGER)
    stale["details"] = {"rounds": []}  # invalid: empty rounds
    legacy = ws / "review-stage"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "REVIEW_LEDGER.json").write_text(json.dumps(stale), encoding="utf-8")
    proc = run_verifier(LEDGER_VERIFIER, ws)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ".sciforge/verdicts/REVIEW_LEDGER.json" in proc.stdout


def test_ledger_verifier_fails_when_absent_everywhere(tmp_path):
    ws = tmp_path / "Q001"
    ws.mkdir()
    proc = run_verifier(LEDGER_VERIFIER, ws)
    assert proc.returncode == 1
    assert "not found" in proc.stderr


def test_paper_audits_verifier_finds_v6_sciforge_path(tmp_path):
    ws = tmp_path / "Q001"
    verdicts = ws / ".sciforge" / "verdicts"
    verdicts.mkdir(parents=True)
    audit = {
        "verdict": "PASS",
        "thread_id": "t1",
        "audited_input_hashes": {},
    }
    (verdicts / "CITATION_AUDIT.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    proc = run_verifier(AUDITS_VERIFIER, ws)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS: CITATION_AUDIT" in proc.stdout
