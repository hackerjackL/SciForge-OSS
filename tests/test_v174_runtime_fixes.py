"""Regressions for defects found by the S01 real end-to-end run (v1.7.4).

Every test here corresponds to something that actually broke while running a
real ARC-Bench problem, not to a hypothetical. Each asserts the fixed behaviour
AND, where the old behaviour could hide, the negative direction too.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
KERNEL = REPO / "kernel"
sys.path.insert(0, str(KERNEL))
sys.path.insert(0, str(REPO / "scripts"))


# ---------------------------------------------------------------------------
# 1. sandbox: scientific stack must import under Seatbelt
# ---------------------------------------------------------------------------
def test_sandbox_allows_os_uname():
    """numpy calls os.uname() at import time; the profile must allow it.

    Measured failure: every smoke re-execution died with PermissionError inside
    numpy before the experiment script ran a line, while the same command
    passed unsandboxed. `sysctl-read` is the minimal allowance that fixes it.
    """
    from sciforge.execution import sandbox_cmd

    if not shutil.which("sandbox-exec"):
        pytest.skip("sandbox-exec not available on this platform")
    ws = Path(os.environ.get("TMPDIR", "/tmp"))
    cmd = sandbox_cmd(ws)
    assert cmd, "sandbox_cmd returned None despite sandbox-exec being present"
    p = subprocess.run(cmd + [sys.executable, "-c",
                              "import os; print(os.uname()[0])"],
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip()


@pytest.mark.skipif(shutil.which("sandbox-exec") is None,
                    reason="sandbox-exec not available")
def test_venv_interpreters_keep_their_site_packages_under_sandbox():
    """The venv shim is resolved away by sandbox-exec; site-packages must be
    recovered from the shim path so `import numpy` still resolves."""
    from sciforge.execution import venv_site_packages

    venv_py = REPO / ".venv" / "bin" / "python"
    if not venv_py.exists():
        pytest.skip("no .venv in this checkout")
    paths = venv_site_packages(str(venv_py))
    assert paths, "venv site-packages not recovered from the shim path"
    assert any(Path(p).is_dir() for p in paths)
    # a non-venv interpreter must yield nothing rather than a bogus path
    assert venv_site_packages("/usr/bin/python3") == []


# ---------------------------------------------------------------------------
# 2. dep_gate: sibling modules are local, not undeclared dependencies
# ---------------------------------------------------------------------------
def test_dep_gate_local_sibling_module_is_not_a_violation(tmp_path):
    """S01 had src/bootstrap_ci.py imported by three siblings; the gate called
    all three 'not in dependencies.json' and would have blocked 6b/6c."""
    import dep_gate

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "helper.py").write_text("VALUE = 1\n")
    (tmp_path / "src" / "main.py").write_text(
        "import helper\nimport numpy\n")
    manifest = {"python": {"core": ["numpy"]}, "always_forbidden": {"roots": []}}
    res = dep_gate.check(tmp_path, manifest)
    assert [v["import"] for v in res["violations"]] == []


def test_dep_gate_still_rejects_undeclared_third_party(tmp_path):
    """The local-root allowance must not become a hole: an undeclared genuine
    dependency still fails."""
    import dep_gate

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("import torch\n")
    manifest = {"python": {"core": ["numpy"]}, "always_forbidden": {"roots": []}}
    res = dep_gate.check(tmp_path, manifest)
    assert [v["import"] for v in res["violations"]] == ["torch"]


# ---------------------------------------------------------------------------
# 3. smoke_gate: the stage-level aggregate is not a group
# ---------------------------------------------------------------------------
def _smoke_group(base: Path, name: str, script_rel: str) -> None:
    g = base / "experiments" / "full" / name
    g.mkdir(parents=True)
    src = 'print("slice ok")\n'
    (g / "run.py").write_text(src)
    (g / "DISPATCH.json").write_text(json.dumps({"script": script_rel}))
    (g / "STATUS.json").write_text('{"state": "done"}')
    (g / f"{name}.SMOKE.json").write_text(json.dumps({
        "group": name, "smoke_result": "PASS", "status_row_written": True,
        "script": script_rel,
        "script_sha256": __import__("hashlib").sha256(src.encode()).hexdigest(),
        "smoke_cmd": f"{sys.executable} {script_rel}",
        "executed_at": "2026-01-01T00:00:00Z"}))


def test_smoke_stage_aggregate_status_is_not_a_group(tmp_path):
    """experiments/full/STATUS.json is the stage aggregate. With per-group
    markers present it must not spawn a phantom group demanding its own smoke
    (S01: all four groups had smokes, yet the gate asked for full.SMOKE.json)."""
    import smoke_gate as sg

    _smoke_group(tmp_path, "g1", "experiments/full/g1/run.py")
    _smoke_group(tmp_path, "g2", "experiments/full/g2/run.py")
    (tmp_path / "experiments" / "full" / "STATUS.json").write_text(
        '{"status": "completed"}')
    doc = sg.check(tmp_path, execute=False)   # record/freshness only
    groups = [g["group"] for g in doc["groups"]]
    assert "full" not in groups, groups
    assert set(groups) == {"g1", "g2"}
    assert "missing_smoke" not in doc["reason_codes"]


def test_smoke_root_only_layout_still_works(tmp_path):
    """With no per-group subdirectories the root marker IS the group — the
    single-group fallback must keep accepting it."""
    import smoke_gate as sg

    g = tmp_path / "experiments" / "full"
    g.mkdir(parents=True)
    src = 'print("ok")\n'
    (g / "run.py").write_text(src)
    (g / "DISPATCH.json").write_text(json.dumps({"script": "experiments/full/run.py"}))
    (g / "STATUS.json").write_text('{"state": "done"}')
    (g / "full.SMOKE.json").write_text(json.dumps({
        "smoke_result": "PASS", "status_row_written": True,
        "script": "experiments/full/run.py",
        "script_sha256": __import__("hashlib").sha256(src.encode()).hexdigest(),
        "executed_at": "2026-01-01T00:00:00Z"}))
    doc = sg.check(tmp_path, execute=False)   # record/freshness only
    assert [g["group"] for g in doc["groups"]] == ["full"]
    assert doc["groups"][0]["record"]["status"] == "PASS"
    assert "missing_smoke" not in doc["reason_codes"]


# ---------------------------------------------------------------------------
# 4. gate_all: on-disk evidence outranks a stale RUNSTATE cursor
# ---------------------------------------------------------------------------
def test_gate_all_uses_artifact_evidence_when_cursor_is_stale(tmp_path, capsys):
    """A Mode A workspace whose RUNSTATE still says phase 0 while experiments,
    figures and a manuscript exist made every gate report phase_not_reached —
    the whole battery silently skipped. Evidence must win, and the staleness
    must be reported rather than silently corrected."""
    import gate_all

    ws = tmp_path
    (ws / ".sciforge").mkdir()
    (ws / ".sciforge" / "RUNSTATE.json").write_text(json.dumps(
        {"status": "running", "current_phase": "0",
         "last_completed_boundary": "0"}))
    (ws / "experiments" / "full" / "group_main").mkdir(parents=True)
    (ws / "experiments" / "full" / "group_main" / "RESULT.json").write_text(
        json.dumps({"status": "PASS"}))
    (ws / "results").mkdir()
    (ws / "results.json").write_text("{}")

    assert gate_all._declared_rank(ws) == 0
    assert gate_all._evidence_rank(ws) is not None
    assert gate_all._evidence_rank(ws) > 0
    assert gate_all._cursor_stale(ws)
    assert gate_all._current_rank(ws) == gate_all._evidence_rank(ws)


def test_gate_all_reports_cursor_stale_as_a_row(tmp_path, capsys):
    import gate_all

    ws = tmp_path
    (ws / ".sciforge").mkdir()
    (ws / ".sciforge" / "RUNSTATE.json").write_text(json.dumps(
        {"status": "running", "current_phase": "0"}))
    (ws / "results").mkdir()
    (ws / "results.json").write_text("{}")
    opts = gate_all.argparse.Namespace(only=["inv_g1"], skip=[], offline=True,
                                       integrity_llm=False, timeout=60)
    doc = gate_all.run_all(ws, opts)
    row = next(r for r in doc["gates"] if r["gate"] == "runstate_cursor")
    assert row["status"] == "WARN"
    assert row["reason_code"] == "runstate_cursor_stale"


def test_gate_all_keeps_skip_semantics_without_evidence(tmp_path):
    """A genuinely new workspace has neither cursor nor artifacts: gates must
    still be able to SKIP rather than being force-run."""
    import gate_all

    assert gate_all._declared_rank(tmp_path) is None
    assert gate_all._evidence_rank(tmp_path) is None
    assert gate_all._current_rank(tmp_path) is None
    assert not gate_all._cursor_stale(tmp_path)

# ---------------------------------------------------------------------------
# 5. smoke re-execution must not mutate the evidence it audits
# ---------------------------------------------------------------------------
def _clobbering_smoke_ws(tmp_path: Path) -> Path:
    """A workspace whose smoke_cmd writes RESULT.json into the group dir —
    exactly the S01 layout that destroyed a 60-cell R=1000 result."""
    import hashlib

    g = tmp_path / "experiments" / "full" / "g1"
    g.mkdir(parents=True)
    real = {"stage": "full",
            "aggregate": {f"m{i}": {"coverage": 0.95} for i in range(60)}}
    (g / "RESULT.json").write_text(json.dumps(real))
    src = ('import json,sys,pathlib\n'
           'out=pathlib.Path(sys.argv[sys.argv.index("--out")+1])\n'
           'out.mkdir(parents=True, exist_ok=True)\n'
           '(out/"RESULT.json").write_text(json.dumps({"stage":"smoke","aggregate":{"m0":1}}))\n'
           'print("slice ok")\n')
    (g / "run.py").write_text(src)
    (g / "DISPATCH.json").write_text(json.dumps({"script": "experiments/full/g1/run.py"}))
    (g / "STATUS.json").write_text('{"state": "done"}')
    (g / "g1.SMOKE.json").write_text(json.dumps({
        "smoke_result": "PASS", "status_row_written": True,
        "script": "experiments/full/g1/run.py",
        "script_sha256": hashlib.sha256(src.encode()).hexdigest(),
        "smoke_cmd": f"{sys.executable} experiments/full/g1/run.py "
                     "--out experiments/full/g1",
        "executed_at": "2026-01-01T00:00:00Z"}))
    return tmp_path


def test_smoke_reexec_restores_clobbered_evidence_and_fails(tmp_path):
    """The audit must leave evidence byte-identical AND report the violation.

    Silently restoring would hide a broken smoke_cmd; silently keeping the
    slice would downgrade every downstream claim. Do both: restore, then FAIL.
    """
    import smoke_gate as sg

    ws = _clobbering_smoke_ws(tmp_path)
    doc = sg.check(ws, sandbox_wrap=lambda w: ["/usr/bin/env"])
    ex = doc["groups"][0]["execution"]
    assert doc["verdict"] == "FAIL", doc
    assert "smoke_reexec_mutated_evidence" in ex["reason_codes"]
    assert "experiments/full/g1/RESULT.json" in ex["mutated_evidence"]
    after = json.loads((ws / "experiments" / "full" / "g1" / "RESULT.json").read_text())
    assert after["stage"] == "full"
    assert len(after["aggregate"]) == 60


def test_smoke_reexec_with_isolated_output_passes(tmp_path):
    """The same script pointed at a scratch dir is a legitimate smoke: no
    evidence touched, so the gate must not invent a violation."""
    import hashlib
    import smoke_gate as sg

    ws = _clobbering_smoke_ws(tmp_path)
    g = ws / "experiments" / "full" / "g1"
    rec = json.loads((g / "g1.SMOKE.json").read_text())
    rec["smoke_cmd"] = (f"{sys.executable} experiments/full/g1/run.py "
                        "--out .smoke-out/g1")
    (g / "g1.SMOKE.json").write_text(json.dumps(rec))
    before = (g / "RESULT.json").read_bytes()
    doc = sg.check(ws, sandbox_wrap=lambda w: ["/usr/bin/env"])
    ex = doc["groups"][0]["execution"]
    assert "smoke_reexec_mutated_evidence" not in (ex.get("reason_codes") or [])
    assert (g / "RESULT.json").read_bytes() == before
    assert doc["verdict"] in ("PASS", "WARN"), doc
