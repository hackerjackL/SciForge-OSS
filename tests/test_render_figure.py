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
