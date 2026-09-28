"""Tests for scripts/plotting/render_figure.py — the unified renderer CLI.

All tests stay offline and deterministic: external engines are never
required (guards, palette checks and CLI dispatch are all testable before
any tool invocation).  One optional end-to-end test runs the real SVG
converter only when rsvg-convert is installed (see conftest.requires_rsvg).
"""

from __future__ import annotations

import json
import sys
import types

import pytest

from pathlib import Path
import render_figure as rf
import sciforge_style as st

from conftest import requires_rsvg


# ---------------------------------------------------------------------------
# palette_check
# ---------------------------------------------------------------------------

def test_palette_check_flags_off_palette_hex():
    v = rf.palette_check('<rect fill="#FF0000"/>', "spec.svg")
    assert len(v) == 1
    assert "#FF0000" in v[0]
    assert "spec.svg" in v[0]


@pytest.mark.parametrize("text", [
    '<rect fill="#FFFFFF"/>',           # white
    '<rect fill="#000000"/>',           # black
    '<rect fill="#808080"/>',           # neutral grey (C* < 2)
    '<g fill="none"/>',                 # no hex at all
    f'<rect fill="{st.TOKENS["surface"]}"/>',  # neutral surface token
    f'<rect fill="{st.TOKENS["blue"]}"/><rect fill="{st.TOKENS["crimson"]}"/>',
])
def test_palette_check_accepts_neutrals_and_palette(text):
    assert rf.palette_check(text, "spec.svg") == []


def test_palette_error_carries_violations():
    e = rf.PaletteError(["v1", "v2"])
    assert isinstance(e, RuntimeError)
    assert e.violations == ["v1", "v2"]
    assert "v1" in str(e)


# ---------------------------------------------------------------------------
# composite guards (both fire before ANY panel file IO — see
# render_composite: the zero-panel check precedes outdir creation and the
# >9-panel cap precedes the panel loop that would touch the filesystem)
# ---------------------------------------------------------------------------

def test_composite_zero_panels_raises(tmp_path):
    m = tmp_path / "f.composite.json"
    m.write_text(json.dumps({"panels": []}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="no panels"):
        rf.render_composite(m, tmp_path / "out" / "output.pdf",
                            tmp_path / "out" / "output.svg", 300, [])


def test_composite_panel_cap_raises_before_file_io(tmp_path):
    panels = [{"file": f"does_not_exist_{i}.pdf"} for i in range(10)]
    m = tmp_path / "f.composite.json"
    m.write_text(json.dumps({"panels": panels}), encoding="utf-8")
    outdir = tmp_path / "out"
    with pytest.raises(RuntimeError) as excinfo:
        rf.render_composite(m, outdir / "output.pdf",
                            outdir / "output.svg", 300, [])
    msg = str(excinfo.value)
    assert "10" in msg and "9" in msg
    assert "panel cap" in msg
    # the cap fired before any panel was copied/rasterized
    assert not list(outdir.glob("panel_*")) if outdir.exists() else True


def test_composite_nine_panels_allowed_past_cap(tmp_path):
    """9 panels clear the cap check (then fail later on missing files —
    proof the cap itself accepted the count)."""
    panels = [{"file": f"missing_{i}.pdf"} for i in range(9)]
    m = tmp_path / "f.composite.json"
    m.write_text(json.dumps({"panels": panels}), encoding="utf-8")
    with pytest.raises(RuntimeError) as excinfo:
        rf.render_composite(m, tmp_path / "out" / "output.pdf",
                            tmp_path / "out" / "output.svg", 300, [])
    assert "panel cap" not in str(excinfo.value)
    assert "panel file missing" in str(excinfo.value)


# ---------------------------------------------------------------------------
# WIDTH_PRESETS
# ---------------------------------------------------------------------------

def test_width_presets_sane_mm_range_and_required_keys():
    assert rf.WIDTH_PRESETS
    for name, mm in rf.WIDTH_PRESETS.items():
        assert isinstance(mm, int)
        assert 60 <= mm <= 300, f"{name}: {mm}mm outside sane column range"
    for key in ("nature-single", "nature-double", "ieee-double", "wide"):
        assert key in rf.WIDTH_PRESETS


# ---------------------------------------------------------------------------
# doctor()
# ---------------------------------------------------------------------------

def _ensure_importable(*names):
    """Defensive: doctor() imports matplotlib/PIL to set core_ok.  They are
    installed in this environment; this only guards unusual test envs."""
    for n in names:
        if n not in sys.modules:
            try:
                __import__(n)
            except ImportError:
                sys.modules[n] = types.ModuleType(n)


def test_doctor_all_tools_present_exit_0(monkeypatch, capsys):
    _ensure_importable("matplotlib", "PIL")
    monkeypatch.setattr(rf, "which", lambda *names: names[0])
    assert rf.doctor() == 0
    out = capsys.readouterr().out
    assert "READY" in out
    assert "[MISS]" not in out


def test_doctor_d2_missing_exit_1(monkeypatch, capsys):
    _ensure_importable("matplotlib", "PIL")

    def fake_which(*names):
        if "d2" in names:
            return None
        return names[0]

    monkeypatch.setattr(rf, "which", fake_which)
    assert rf.doctor() == 1
    out = capsys.readouterr().out
    assert "DEGRADED" in out
    assert "[MISS] d2" in out


# ---------------------------------------------------------------------------
# CLI dispatch / engine auto-detection via main()
# ---------------------------------------------------------------------------

def test_main_missing_source_exit_3(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv",
                        ["render_figure.py", str(tmp_path / "nope.d2")])
    assert rf.main() == 3


def test_main_unknown_extension_exit_3(monkeypatch, tmp_path, capsys):
    f = tmp_path / "figure.xyz"
    f.write_text("whatever", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["render_figure.py", str(f)])
    assert rf.main() == 3
    assert "unknown source extension" in capsys.readouterr().err


def test_main_composite_json_suffix_detected(monkeypatch, tmp_path, capsys):
    """`.composite.json` routes to the composite engine (the failure mode
    is the composite guard, NOT the unknown-extension error)."""
    f = tmp_path / "fig.composite.json"
    f.write_text(json.dumps({"panels": []}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["render_figure.py", str(f)])
    assert rf.main() == 3
    err = capsys.readouterr().err
    assert "no panels" in err
    assert "unknown source extension" not in err


def test_main_palette_violation_exit_2(monkeypatch, tmp_path, capsys):
    """palette_check runs before any external tool — exit 2 offline."""
    f = tmp_path / "source.svg"
    f.write_text('<svg xmlns="http://www.w3.org/2000/svg" '
                 'viewBox="0 0 100 100"><rect fill="#FF0000"/></svg>',
                 encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["render_figure.py", str(f)])
    assert rf.main() == 2
    assert "PALETTE AUDIT FAIL" in capsys.readouterr().err


def test_main_d2_palette_violation_exit_2(monkeypatch, tmp_path):
    """Same guard at source level for d2 specs (before d2 is invoked)."""
    f = tmp_path / "spec.d2"
    f.write_text('a -> b\na.style.fill: "#FF0000"\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["render_figure.py", str(f)])
    assert rf.main() == 2


# ---------------------------------------------------------------------------
# run() / which()
# ---------------------------------------------------------------------------

def test_run_success_returns_stdout():
    out = rf.run([sys.executable, "-c", "print('ok')"])
    assert out.strip() == "ok"


def test_run_nonzero_exit_raises_with_rc():
    with pytest.raises(RuntimeError, match="failed"):
        rf.run([sys.executable, "-c", "import sys; sys.exit(3)"])


def test_run_missing_tool_raises_tool_not_found():
    with pytest.raises(RuntimeError, match="tool not found"):
        rf.run(["definitely-not-a-real-tool-xyz"])


def test_run_logs_commands():
    log = []
    rf.run([sys.executable, "-c", "print('ok')"], log=log)
    assert log and log[0].startswith("$ ")


def test_which_returns_first_available(monkeypatch):
    monkeypatch.setattr(rf.shutil, "which",
                        lambda n: "/fake/bin/" + n if n == "dot" else None)
    assert rf.which("d2", "dot") == "dot"
    assert rf.which("d2") is None


# ---------------------------------------------------------------------------
# optional end-to-end: real SVG render (only with rsvg-convert installed)
# ---------------------------------------------------------------------------

@requires_rsvg
def test_main_svg_engine_end_to_end(monkeypatch, tmp_path, make_svg):
    src = tmp_path / "source.svg"
    src.write_text(make_svg(), encoding="utf-8")
    out = tmp_path / "fig"
    monkeypatch.setattr(sys, "argv",
                        ["render_figure.py", str(src), "--out", str(out)])
    assert rf.main() == 0
    assert (out / "output.pdf").read_bytes()[:4] == b"%PDF"
    assert (out / "output.svg").is_file()
    assert (out / "latex_include.tex").is_file()
    audit = json.loads((out / "figure_audit.json").read_text(encoding="utf-8"))
    assert audit["verdict"] in ("PASS", "WARN")
    # the original source was kept beside the deliverables
    assert (out / "source.svg").is_file()


# ---------------- v1.6.1 declarative recipe engine (toolchain unity) ----------------

import json as _json

def _recipe_pdf(tmp_path, spec):
    import subprocess, sys
    tmp_path.mkdir(parents=True, exist_ok=True)
    sp = tmp_path / "f.recipe.json"
    sp.write_text(_json.dumps(spec))
    out = tmp_path / "out"
    p = subprocess.run([sys.executable, str(Path(rf.__file__)),
                        str(sp), "--out", str(out), "--name", "output"],
                       capture_output=True, text=True, timeout=180)
    return p, out

def test_recipe_line_comparison_renders(tmp_path):
    # semantic fixture — a real LLM pretraining-loss sweep, not toy [1,2,3]
    # series (style benchmark: ChenLiu-1996/figures4papers, Yuan1z0825 nature-figure)
    epochs = [0, 250, 500, 750, 1000, 1250, 1500]
    p, out = _recipe_pdf(tmp_path, {
        "recipe": "line-comparison", "size": "single",
        "x_label": "Training tokens (B)", "y_label": "Validation loss",
        "series": [
            {"name": "Dense-6.7B", "x": epochs,
             "y": [3.02, 2.41, 2.18, 2.05, 1.98, 1.94, 1.91],
             "err": [0.04] * 7, "stat": "ci95"},
            {"name": "SparseAttn-6.7B (ours)", "x": epochs,
             "y": [2.94, 2.22, 1.98, 1.86, 1.79, 1.75, 1.72],
             "err": [0.035] * 7, "stat": "ci95"}]})
    assert p.returncode == 0, p.stdout + p.stderr
    assert (out / "output.pdf").exists() and (out / "output.svg").exists()
    assert (out / "figure_audit.json").exists()  # unified entry audits recipes too

def test_recipe_bar_and_forest(tmp_path):
    # benchmark-accuracy bars + multi-centre trial forest (semantic, reviewable)
    p, out = _recipe_pdf(tmp_path, {
        "recipe": "bar-grouped", "x_label": "Benchmark", "y_label": "Accuracy (%)",
        "groups": ["MMLU", "HellaSwag", "GSM8K"],
        "series": [{"name": "Ours-7B", "values": [63.8, 83.2, 68.9],
                    "err": [0.6, 0.4, 1.0], "stat": "ci95"}]})
    assert p.returncode == 0, p.stderr
    p2, out2 = _recipe_pdf(tmp_path / "f", {
        "recipe": "forest-plot",
        "x_label": "Mean difference in HbA1c (mmol/mol), 95% CI",
        "rows": [{"label": "CENTER 01 (n=142)", "effect": -6.2, "lo": -9.1, "hi": -3.3},
                 {"label": "CENTER 02 (n=98)", "effect": -4.8, "lo": -8.0, "hi": -1.6}],
        "pooled": {"effect": -5.5, "lo": -7.2, "hi": -3.8}})
    assert p2.returncode == 0, p2.stderr
    assert (out2 / "output.pdf").exists()

def test_recipe_unknown_kind_fails(tmp_path):
    sp = tmp_path / "bad.recipe.json"
    sp.write_text(_json.dumps({"recipe": "pie-3d", "series": []}))
    import subprocess, sys
    p = subprocess.run([sys.executable, str(Path(rf.__file__)),
                        str(sp), "--out", str(tmp_path / "o")],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode != 0
    assert "unknown recipe" in (p.stdout + p.stderr)

def test_recipe_heatmap_enforces_layer2(tmp_path):
    p, _ = _recipe_pdf(tmp_path, {
        "recipe": "heatmap",
        "matrix": [[0.21, 0.34], [0.55, 0.62]],  # layer-wise attention sparsity
        "colormap": "jet"})
    assert p.returncode != 0  # jet is forbidden for continuous fields
    p2, out2 = _recipe_pdf(tmp_path / "ok", {
        "recipe": "heatmap",
        "matrix": [[0.21, 0.34], [0.55, 0.62]], "colormap": "cividis"})
    assert p2.returncode == 0 and (out2 / "output.pdf").exists()

def test_recipe_panel_grid_shared_legend(tmp_path):
    p, out = _recipe_pdf(tmp_path, {
        "recipe": "panel-grid", "cols": 2,
        "panels": [
            {"recipe": "line-comparison",
             "x_label": "Training tokens (B)", "y_label": "Validation loss",
             "series": [{"name": "Dense-1.3B", "x": [0, 250, 500],
                         "y": [3.40, 2.65, 2.31]}]},
            {"recipe": "bar-grouped",
             "x_label": "Benchmark", "y_label": "Accuracy (%)",
             "groups": ["MMLU", "GSM8K"],
             "series": [{"name": "Ours-7B", "values": [63.8, 68.9],
                         "err": [0.6, 1.0], "stat": "ci95"}]}]})
    assert p.returncode == 0, p.stderr
    # one shared figure-level legend (not per-panel): verify in-process
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import figure_recipes as fr
    spec = _json.loads((tmp_path / "f.recipe.json").read_text())
    fig = plt.figure()
    plt.close(fig)
    # render via the module and introspect the produced figure's legend count
    import unittest.mock as mock
    created = {}
    real_subplots = plt.subplots
    def spy(*a, **k):
        f, ax = real_subplots(*a, **k)
        created["fig"] = f
        return f, ax
    with mock.patch.object(plt, "subplots", spy):
        fr.render(spec, tmp_path / "out2")
    figs = created["fig"]
    assert len(figs.legends) == 1, f"expected ONE shared legend, got {len(figs.legends)}"
    plt.close(figs)

def test_recipe_bar_long_labels_do_not_overlap(tmp_path):
    """ARC-Bench v1.7 review finding, locked as a regression.

    Every recipe set categorical x-tick labels with a bare set_xticklabels
    (groups) — long names (friedman1 low noise / FBA pFBA loop) rendered as an
    unreadable horizontal smear in all five papers' main figures. The fix runs a
    post-layout collision fit (rotate/verticalize until adjacent labels clear
    XTICK_MIN_GAP_PX). This test renders the worst case and asserts the
    produced figure's x-tick labels no longer collide.
    """
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import unittest.mock as mock
    import figure_recipes as fr
    spec = {"recipe": "bar-grouped", "size": "single",
            "x_label": "dataset (regime)", "y_label": "test RMSE",
            "groups": ["friedman1 low noise", "friedman1 high noise", "diabetes"],
            "series": [{"name": "Tree", "values": [2.88, 31.30, 64.64]},
                       {"name": "Boosting", "values": [1.45, 30.35, 56.65]}]}
    created = {}
    real_subplots = plt.subplots
    def spy(*a, **k):
        f, ax = real_subplots(*a, **k)
        created["fig"], created["ax"] = f, ax
        return f, ax
    with mock.patch.object(plt, "subplots", spy), \
            mock.patch.object(plt, "close", lambda *a, **k: None):
        fr.render(spec, tmp_path / "out")
    fig, ax = created["fig"], created["ax"]
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bbs = [t.get_window_extent(renderer=r) for t in ax.get_xticklabels() if t.get_text()]
    gaps = [bbs[i + 1].x0 - bbs[i].x1 for i in range(len(bbs) - 1)]
    assert all(g >= fr.XTICK_MIN_GAP_PX for g in gaps), (
        f"x-tick labels still collide (gaps {gaps} < {fr.XTICK_MIN_GAP_PX}px): "
        "the collision fit regressed")
    plt.close(fig)


def test_recipe_bar_long_labels_fixture():
    """The fixture spec used by the overlap test must itself be a real
    collision case (long labels in a single-width axis) — guards the test
    from silently passing on a spec that never collided."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import figure_recipes as fr
    st.apply_matplotlib_style()
    fig, ax = plt.subplots(figsize=st.figsize_single())
    groups = ["friedman1 low noise", "friedman1 high noise", "diabetes"]
    ax.bar([0, 1, 2], [2.88, 31.30, 64.64])
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(groups)
    assert fr._xticks_overlap(fig, ax) is True  # pre-fit: must be a real collision
    plt.close(fig)


def test_cycle_order_single_source():
    """series_style(0) == prop_cycle[0] (the panel color-drift bug guard)."""
    import sciforge_style as st
    st.apply_matplotlib_style()
    import matplotlib as mpl
    cyc = [c["color"] for c in mpl.rcParams["axes.prop_cycle"]]
    assert cyc[0] == st.series_style(0)["color"]
    assert st.contrast(cyc[0], "#FFFFFF") >= 3.0  # first series is line-safe

# ---------------- v1.6.2 layout archetypes (figure-layout-contract §3) ----------------

def _layout_spec(layout, panels, cols=2):
    return {"recipe": "panel-grid", "layout": layout, "cols": cols, "panels": panels}


def _mini_panels():
    """Realistic mini-panels — research semantics, not toy [1,2,3]."""
    return [
        {"recipe": "line-comparison",
         "x_label": "Training tokens (B)", "y_label": "Validation loss",
         "series": [{"name": "Dense-6.7B", "x": [0, 250, 500],
                     "y": [3.02, 2.41, 2.18], "err": [0.04, 0.04, 0.04],
                     "stat": "ci95"}]},
        {"recipe": "bar-grouped",
         "x_label": "Benchmark", "y_label": "Accuracy (%)",
         "groups": ["MMLU", "GSM8K"],
         "series": [{"name": "Ours-7B", "values": [63.8, 68.9],
                     "err": [0.6, 1.0], "stat": "ci95"}]},
        {"recipe": "hist-dist",
         "x_label": "Per-token latency (ms)", "y_label": "Density",
         "series": [{"name": "SparseAttn (ours)",
                     "values": [18.2, 19.1, 19.8, 20.4, 21.0, 22.3, 24.1, 26.0]}]},
        {"recipe": "scatter-fit",
         "x_label": "log10 training FLOPs", "y_label": "Validation loss",
         "series": [{"name": "grid runs", "x": [18.2, 19.0, 19.8, 20.6, 21.4, 22.2],
                     "y": [3.10, 2.72, 2.48, 2.30, 2.17, 2.08]}]},
    ]


def test_layout_archetype_equal_grid_emits_panel_manifest(tmp_path):
    p, out = _recipe_pdf(tmp_path, _layout_spec("equal-grid", _mini_panels()))
    assert p.returncode == 0, p.stdout + p.stderr
    mf = out / "panel_layout.json"
    assert mf.exists(), "panel_layout.json must be emitted for the A11 gate"
    m = _json.loads(mf.read_text())
    assert m["schema_version"] == 1
    assert m["layout_preset"] == "equal-grid"
    assert len(m["panels"]) == 4
    # equal-grid: no hero exemptions — all four panels stay comparable
    assert not m.get("exemptions"), "equal-grid must not exempt any panel"


def test_layout_archetype_schematic_led_exempts_hero_only(tmp_path):
    panels = _mini_panels()
    panels[0]["hero"] = True
    p, out = _recipe_pdf(tmp_path, _layout_spec("schematic-led", panels, cols=4))
    assert p.returncode == 0, p.stdout + p.stderr
    m = _json.loads((out / "panel_layout.json").read_text())
    assert m["layout_preset"] == "schematic-led"
    ex = m.get("exemptions") or []
    assert len(ex) == 1 and ex[0]["panels"] == ["p0"], (
        "hero is exempt; every support panel stays comparable (contract §5)")


def test_layout_archetype_unknown_name_fails(tmp_path):
    sp = tmp_path / "bad.recipe.json"
    sp.write_text(_json.dumps(_layout_spec("dashboard-grid", _mini_panels())))
    import subprocess, sys
    p = subprocess.run([sys.executable, str(Path(rf.__file__)),
                        str(sp), "--out", str(tmp_path / "o")],
                       capture_output=True, text=True, timeout=90)
    assert p.returncode != 0
    assert "unknown layout" in (p.stdout + p.stderr)


def test_forest_plot_rejects_boolean_pooled(tmp_path):
    """pooled must be {effect, lo, hi} — a bare True is a type error (spec bug)."""
    import figure_recipes as fr
    spec = {"recipe": "forest-plot", "pooled": True,
            "rows": [{"label": "CENTER 01", "effect": -6.2, "lo": -9.1, "hi": -3.3}]}
    try:
        fr.render(spec, tmp_path / "f")
    except ValueError as e:
        assert "pooled" in str(e)
    else:
        raise AssertionError("boolean pooled must raise ValueError")


def test_demo_corpus_specs_are_publication_grade():
    """The shipped demo corpus must carry research semantics, not toy arrays
    (style benchmark: ChenLiu-1996/figures4papers, Yuan1z0825/nature-figure)."""
    root = Path(__file__).resolve().parents[1] / "demos" / "figures"
    specs = sorted(root.glob("*.recipe.json"))
    assert len(specs) >= 8, f"expected a demo corpus, found {len(specs)}"
    banned_labels = {"a", "b", "c", "x", "y", "m", "s", "t", "acc", "ours"}
    for spec in specs:
        data = _json.loads(spec.read_text())
        blob = spec.read_text()
        # every shipped demo names real research objects in its axes/series
        assert any(tok in blob for tok in (
            "Accuracy", "loss", "FLOPs", "HbA1c", "Latency", "Sparsity",
            "Benchmark", "latency", "weight", "Pipeline", "MEMORY", "mem",
            "Retrieval", "Participants", "AE grade", "Speedup", "Occupancy",
        )), f"{spec.name} lacks research-semantic labels"
        # no toy series names in shipped demos
        def walk(node):
            if isinstance(node, dict):
                if "name" in node and isinstance(node["name"], str):
                    assert node["name"].strip().lower() not in banned_labels, (
                        f"{spec.name}: toy series name {node['name']!r}")
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(data)
