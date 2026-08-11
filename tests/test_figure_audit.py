"""Tests for scripts/plotting/figure_audit.py — audit layers A1..A10.

Figure dirs are constructed in tmp_path; all geometry for the A10 bbox
tests is deliberately generous (>= 60% vertical intrusion, wide
horizontal overlap) so the assertions are robust against small changes
in the CHAR_WIDTH_ESTIMATES width model.
"""

from __future__ import annotations

import pytest

import figure_audit as fa
import sciforge_style as st

SVG_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 1600 900" width="1600" height="900">')


def layer_checks(rep, layer):
    return [c for c in rep.checks if c["layer"] == layer]


def layer_statuses(rep, layer):
    return [c["status"] for c in layer_checks(rep, layer)]


def text_el(x, y, label, fs=20, extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{fs}" '
            f'fill="#000000"{extra}>{label}</text>')


# ---------------------------------------------------------------------------
# Report class
# ---------------------------------------------------------------------------

def test_report_verdict_precedence():
    rep = fa.Report()
    rep.add("A1", "PASS", "ok")
    assert rep.verdict() == "PASS"
    rep.add("A2", "WARN", "hmm")
    assert rep.verdict() == "WARN"
    rep.add("A3", "FAIL", "bad")
    assert rep.verdict() == "FAIL"


def test_report_to_json_shape():
    rep = fa.Report()
    rep.add("A1", "PASS", "ok")
    d = rep.to_json()
    assert d["verdict"] == "PASS"
    assert d["style_version"] == st.__version__
    assert d["checks"][0] == {"layer": "A1", "status": "PASS", "msg": "ok"}
    assert "suggested_fixes" not in d          # omitted when empty
    rep.add_fix("A10", "move it")
    assert d is not rep.to_json()              # fresh dict each call
    assert rep.to_json()["suggested_fixes"] == [{"layer": "A10", "fix": "move it"}]


# ---------------------------------------------------------------------------
# A1 — outputs
# ---------------------------------------------------------------------------

def test_a1_missing_outputs_fail(tmp_path):
    rep = fa.Report()
    fa.audit_outputs(tmp_path, rep)
    assert "FAIL" in layer_statuses(rep, "A1")
    msgs = " | ".join(c["msg"] for c in layer_checks(rep, "A1"))
    assert "output.pdf" in msgs
    assert "output.svg" in msgs


def test_a1_valid_magic_pass(figure_dir, make_svg):
    from conftest import PDF_BYTES
    d = figure_dir(files={"output.pdf": PDF_BYTES, "output.svg": make_svg()})
    rep = fa.Report()
    fa.audit_outputs(d, rep)
    assert set(layer_statuses(rep, "A1")) == {"PASS"}


def test_a1_bad_pdf_magic_fails(figure_dir, make_svg):
    d = figure_dir(files={"output.pdf": b"NOTPDF garbage",
                          "output.svg": make_svg()})
    rep = fa.Report()
    fa.audit_outputs(d, rep)
    assert "FAIL" in layer_statuses(rep, "A1")
    assert any("magic" in c["msg"] for c in layer_checks(rep, "A1"))


# ---------------------------------------------------------------------------
# A3 — palette
# ---------------------------------------------------------------------------

def test_a3_saturated_off_palette_hex_fails():
    rep = fa.Report()
    fa.audit_palette_svg('<svg><rect fill="#FF0000"/></svg>', rep)
    assert layer_statuses(rep, "A3") == ["FAIL"]
    assert "#FF0000" in layer_checks(rep, "A3")[0]["msg"]


def test_a3_morandi_only_svg_passes():
    svg = '<svg><rect fill="#8AA1BC"/><rect fill="#97A98D"/>' \
          '<rect fill="#FFFFFF"/><rect fill="#000000"/></svg>'
    rep = fa.Report()
    fa.audit_palette_svg(svg, rep)
    assert layer_statuses(rep, "A3") == ["PASS"]


def test_a3_neutrals_are_exempt():
    svg = '<svg><rect fill="#808080"/><rect fill="#FDFDFD"/>' \
          '<rect fill="#0A0A0A"/></svg>'
    rep = fa.Report()
    fa.audit_palette_svg(svg, rep)
    assert layer_statuses(rep, "A3") == ["PASS"]


# ---------------------------------------------------------------------------
# A4 — typography (Nature floor)
# ---------------------------------------------------------------------------

def test_a4_font_below_floor_fails():
    rep = fa.Report()
    fa.audit_typography_svg(
        '<svg>' + text_el(10, 10, "tiny", fs=10) + '</svg>', rep)
    # 10px * 0.75 = 7.5pt < 12pt diagram floor
    assert "FAIL" in layer_statuses(rep, "A4")


def test_a4_font_above_floor_passes():
    rep = fa.Report()
    fa.audit_typography_svg(
        '<svg>' + text_el(10, 10, "big", fs=24,
                          extra=' font-family="Liberation Sans"') + '</svg>',
        rep)
    assert set(layer_statuses(rep, "A4")) == {"PASS"}


def test_a4_pt_units_honored():
    rep = fa.Report()
    fa.audit_typography_svg(
        '<svg><text x="1" y="1" font-size="9pt">x</text></svg>', rep)
    assert "FAIL" in layer_statuses(rep, "A4")   # 9pt < 12pt floor


# ---------------------------------------------------------------------------
# A10 — text occlusion / overlap (bbox helpers + full layer)
# ---------------------------------------------------------------------------

def test_char_width_estimates_table_is_sane():
    for key in ("sans", "serif", "fallback"):
        assert key in fa.CHAR_WIDTH_ESTIMATES
        assert 0.0 < fa.CHAR_WIDTH_ESTIMATES[key] < 1.0


def test_a10_overlapping_texts_fail_with_fixes():
    """Same x, baselines 10px apart at fs=20 -> vertical intrusion ~64%
    (> 30% threshold) with full horizontal overlap."""
    svg = (SVG_HEAD
           + text_el(100, 100, "AAAAAAAAAA")
           + text_el(100, 110, "BBBBBBBBBB")
           + "</svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg, rep)
    assert "FAIL" in layer_statuses(rep, "A10")
    assert rep.suggested_fixes, "overlap must yield actionable fixes"
    assert all(f["layer"] == "A10" for f in rep.suggested_fixes)
    assert any("move label" in f["fix"] for f in rep.suggested_fixes)


def test_a10_well_separated_labels_pass():
    svg = (SVG_HEAD
           + text_el(100, 100, "AAAAAAAAAA")
           + text_el(100, 300, "BBBBBBBBBB")
           + "</svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg, rep)
    assert "FAIL" not in layer_statuses(rep, "A10")
    assert "PASS" in layer_statuses(rep, "A10")


def test_a10_detects_overlap_only_after_group_translate():
    """The second label sits at y=300 (no raw overlap with y=100); only
    the enclosing translate(0,-190) moves it onto the first label."""
    svg = (SVG_HEAD
           + text_el(100, 100, "AAAAAAAAAA")
           + '<g transform="translate(0,-190)">'
           + text_el(100, 300, "BBBBBBBBBB")
           + "</g></svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg, rep)
    assert "FAIL" in layer_statuses(rep, "A10")

    # control: without the transform the very same geometry is clean
    svg_raw = (SVG_HEAD
               + text_el(100, 100, "AAAAAAAAAA")
               + text_el(100, 300, "BBBBBBBBBB")
               + "</svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg_raw, rep)
    assert "FAIL" not in layer_statuses(rep, "A10")


@pytest.mark.parametrize("transform", [
    "rotate(45 100 100)",
    "matrix(1 0.5 0 1 0 0)",
    "scale(2 3)",           # non-uniform scale is out of scope too
])
def test_a10_unsupported_transforms_skipped_without_crash(transform):
    """A text that WOULD overlap is inside an unsupported transform and
    must be skipped (flagged), never crashing nor falsely failing."""
    svg = (SVG_HEAD
           + text_el(100, 100, "AAAAAAAAAA")
           + f'<g transform="{transform}">'
           + text_el(100, 100, "BBBBBBBBBB")
           + "</g></svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg, rep)          # must not raise
    assert "FAIL" not in layer_statuses(rep, "A10")


def test_a10_wiring_crossing_unhaloed_text_warns():
    svg = (SVG_HEAD
           + text_el(100, 100, "AAAAAAAAAA")
           + '<line x1="50" y1="95" x2="400" y2="95" '
             'stroke="#000000" stroke-width="2"/>'
           + "</svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg, rep)
    assert "WARN" in layer_statuses(rep, "A10")


def test_a10_halo_rect_suppresses_wiring_warn():
    svg = (SVG_HEAD
           + '<rect x="90" y="75" width="200" height="40" fill="#FFFFFF"/>'
           + text_el(100, 100, "AAAAAAAAAA")
           + '<line x1="50" y1="95" x2="400" y2="95" '
             'stroke="#000000" stroke-width="2"/>'
           + "</svg>")
    rep = fa.Report()
    fa.audit_text_occlusion(svg, rep)
    assert "WARN" not in layer_statuses(rep, "A10")


# ---- A10 low-level helpers ------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("translate(10, 20)", (1.0, 10.0, 20.0, True)),
    ("translate(10,20) scale(2)", (2.0, 10.0, 20.0, True)),
    ("scale(2)", (2.0, 0.0, 0.0, True)),
    ("", (1.0, 0.0, 0.0, True)),
])
def test_parse_transform_supported(value, expected):
    assert fa._parse_transform(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", [
    "rotate(30)", "matrix(1 0 0 1 5 5)", "scale(2, 3)", "skewX(10)",
])
def test_parse_transform_unsupported_flagged(value):
    _, _, _, ok = fa._parse_transform(value)
    assert ok is False


@pytest.mark.parametrize("tag,sx,sy,vw,vh", [
    ('<svg viewBox="0 0 100 50" width="200" height="100">', 2.0, 2.0, 100, 50),
    ('<svg viewBox="0 0 100 50" width="75pt" height="37.5pt">', 1.0, 1.0, 100, 50),
    ('<svg viewBox="0 0 100 50" width="100%">', 1.0, 1.0, 100, 50),
    ('<svg viewBox="0 0 100 50">', 1.0, 1.0, 100, 50),
])
def test_svg_viewport(tag, sx, sy, vw, vh):
    assert fa._svg_viewport(tag) == pytest.approx((sx, sy, vw, vh))


def test_text_bbox_anchors():
    cw = fa.CHAR_WIDTH_ESTIMATES["fallback"]
    fs = 10.0
    w = len("AB") * fs * cw
    x0, y0, x1, y1 = fa._text_bbox(100, 50, [("AB", None, 0.0)], fs, "start")
    assert (x0, x1) == pytest.approx((100, 100 + w))
    assert (y0, y1) == pytest.approx((40, 54))        # -1em .. +0.4em
    x0m, _, x1m, _ = fa._text_bbox(100, 50, [("AB", None, 0.0)], fs, "middle")
    assert (x0m, x1m) == pytest.approx((100 - w / 2, 100 + w / 2))
    x0e, _, x1e, _ = fa._text_bbox(100, 50, [("AB", None, 0.0)], fs, "end")
    assert (x0e, x1e) == pytest.approx((100 - w, 100))


def test_text_bbox_tspan_chunks_accumulate_dy():
    cw = fa.CHAR_WIDTH_ESTIMATES["fallback"]
    fs = 10.0
    x0, y0, x1, y1 = fa._text_bbox(
        100, 50, [("A", 100, 0.0), ("BB", None, 12.0)], fs, "start", cw)
    # second run starts where the first ended, 12 units lower
    assert x1 == pytest.approx(100 + 1 * fs * cw + 2 * fs * cw)
    assert y1 == pytest.approx(50 + 12 + 0.4 * fs)


def test_text_bbox_empty_chunks_degenerate():
    assert fa._text_bbox(7, 30, [], 10.0) == (7, 20, 7, 30)


# ---------------------------------------------------------------------------
# A9 — brand leak
# ---------------------------------------------------------------------------

def test_a9_brand_word_in_d2_spec_fails(figure_dir):
    d = figure_dir(files={"spec.d2": "title: sciforge pipeline\na -> b\n"})
    rep = fa.Report()
    fa.audit_brand_leak(d, rep)
    assert layer_statuses(rep, "A9") == ["FAIL"]
    assert "spec.d2" in layer_checks(rep, "A9")[0]["msg"]


def test_a9_brand_word_in_svg_fails(figure_dir):
    d = figure_dir(files={"output.svg": SVG_HEAD
                          + "<text>made with SciForge</text></svg>"})
    rep = fa.Report()
    fa.audit_brand_leak(d, rep)
    assert layer_statuses(rep, "A9") == ["FAIL"]


def test_a9_python_import_lines_exempt(figure_dir):
    """Only import/sys.path machinery lines in .py are exempt."""
    py = ("import sys\n"
          "sys.path.insert(0, 'scripts/plotting')\n"
          "import sciforge_style\n"
          "from figure_audit import audit_figure\n")
    d = figure_dir(files={"render.py": py})
    rep = fa.Report()
    fa.audit_brand_leak(d, rep)
    assert layer_statuses(rep, "A9") == ["PASS"]


def test_a9_python_non_import_line_still_caught(figure_dir):
    d = figure_dir(files={"render.py": "print('rendered by render_figure')\n"})
    rep = fa.Report()
    fa.audit_brand_leak(d, rep)
    assert layer_statuses(rep, "A9") == ["FAIL"]


def test_a9_clean_dir_passes(figure_dir):
    d = figure_dir(files={"spec.d2": "encoder -> decoder\n",
                          "output.svg": SVG_HEAD + "</svg>"})
    rep = fa.Report()
    fa.audit_brand_leak(d, rep)
    assert layer_statuses(rep, "A9") == ["PASS"]


# ---------------------------------------------------------------------------
# audit_figure — full pass over a valid minimal figure dir
# ---------------------------------------------------------------------------

def test_audit_figure_valid_dir_verdict_pass_or_warn(valid_figure_dir):
    rep = fa.audit_figure(valid_figure_dir)
    out = rep.to_json()
    assert out["verdict"] in ("PASS", "WARN")
    assert "FAIL" not in {c["status"] for c in out["checks"]}


def test_audit_figure_never_crashes_on_empty_dir(tmp_path):
    rep = fa.audit_figure(tmp_path)
    assert rep.verdict() == "FAIL"               # missing deliverables
    assert rep.to_json()["checks"]               # but checks were produced
