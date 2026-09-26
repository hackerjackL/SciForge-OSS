"""Robustness tests for the plotting toolchain — fixes F8 / F9 / F10.

F8  (crash)     figure_audit must never raise on malformed SVG numerics
                (font-size="..", viewBox="0 0 .. 10", width=".."): the
                audit degrades to WARN/FAIL, it never kills the render.
F9  (escaping)  composite labels are TeX-escaped in composite.tex and
                XML-escaped in the assembled SVG; a user --caption is
                TeX-escaped in latex_include.tex.
F10 (palette)   #RGB shorthand and #RRGGBBAA 8-digit hex literals are
                visible to every color gate (palette_check /
                audit_palette_svg / sanitize_palette); 4/5/7-digit
                garbage never matches; {HTML}{...} TeX colors stay
                6-digit only (xcolor rejects shorthand).

stdlib + PIL only; pdflatex/pdftoppm end-to-end tests skip when the
binaries are absent (conftest style).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.dom.minidom

import pytest

import figure_audit as fa
import render_figure as rf
import sciforge_style as st

from conftest import PDF_BYTES, requires_pdflatex

requires_pdftoppm = pytest.mark.skipif(
    shutil.which("pdftoppm") is None, reason="pdftoppm is not installed")


# ---------------------------------------------------------------------------
# F8 — _parse_size is total
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("..", 0.0),          # the reported crash input
    (".", 0.0),           # the reported crash input
    ("", 0.0),
    ("   ", 0.0),
    ("garbage", 0.0),
    ("px", 0.0),
    ("12pt", 16.0),       # pt -> px via PX_TO_PT (12 / 0.75)
    ("13px", 13.0),
    ("10", 10.0),
    ("12.5", 12.5),
])
def test_parse_size_total(value, expected):
    """_parse_size returns a float for EVERY input — never raises."""
    assert fa._parse_size(value) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# F8 — audit layers degrade to WARN on malformed numerics, never crash
# ---------------------------------------------------------------------------

MALFORMED_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" '
                 'viewBox="0 0 .. 10" width=".." height=".">'
                 '<text x="10" y="10" font-size="..">hi</text>'
                 '<text x="10" y="50" font-size=".">yo</text></svg>')


def test_audit_figure_malformed_numerics_dir_never_raises(figure_dir):
    d = figure_dir(files={"output.pdf": PDF_BYTES,
                          "output.svg": MALFORMED_SVG})
    rep = fa.audit_figure(d)          # must NOT raise ValueError
    verdict = rep.verdict()
    assert isinstance(verdict, str)
    assert verdict in ("WARN", "FAIL")          # degraded, not crashed
    a2 = [c for c in rep.checks if c["layer"] == "A2"]
    assert any(c["status"] == "WARN" for c in a2)   # A2 promised a WARN
    assert rep.to_json()["verdict"] == verdict      # serializable report


def test_audit_resolution_malformed_viewbox_warns(tmp_path):
    svg = tmp_path / "output.svg"
    svg.write_text('<svg viewBox="0 0 .. 10"></svg>', encoding="utf-8")
    rep = fa.Report()
    fa.audit_resolution(svg, rep)     # float("..") must not escape
    assert [c["status"] for c in rep.checks if c["layer"] == "A2"] == ["WARN"]


def test_audit_layout_svg_malformed_viewbox_warns():
    rep = fa.Report()
    fa.audit_layout_svg('<svg viewBox="0 0 .. 10"></svg>', rep)
    a5 = [c for c in rep.checks if c["layer"] == "A5"]
    assert a5 and a5[0]["status"] == "WARN"
    assert "malformed" in a5[0]["msg"]


def test_svg_viewport_malformed_width_height_falls_back():
    """width=".."/height="." fall back to the viewBox instead of raising."""
    sx, sy, vw, vh = fa._svg_viewport(
        '<svg viewBox="0 0 100 50" width=".." height=".">')
    assert (sx, sy, vw, vh) == pytest.approx((1.0, 1.0, 100, 50))


# ---------------------------------------------------------------------------
# F9 — composite labels: TeX round-trip + XML well-formedness
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def panel_pdf_dir(tmp_path_factory):
    """Two tiny panel PDFs crafted via pdflatex standalone (module-cached)."""
    if shutil.which("pdflatex") is None:
        pytest.skip("pdflatex is not installed")
    base = tmp_path_factory.mktemp("composite_panels")
    (base / "panel.tex").write_text(
        r"\documentclass{standalone}\begin{document}"
        r"\rule{60pt}{30pt}\end{document}", encoding="utf-8")
    for name in ("raw1", "raw2"):
        r = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             "-jobname", name, "panel.tex"],
            cwd=base, capture_output=True, text=True, timeout=240)
        assert r.returncode == 0, r.stdout[-2000:]
        assert (base / f"{name}.pdf").is_file()
    return base


@requires_pdflatex
@requires_pdftoppm
def test_composite_labels_roundtrip_pdflatex_and_xml(panel_pdf_dir):
    """Labels 'a_b'/'x%y' used to break pdflatex (Missing $ inserted /
    Illegal parameter number).  Now composite.tex compiles and the
    assembled output.svg parses as XML."""
    base = panel_pdf_dir
    manifest = base / "fig.composite.json"
    manifest.write_text(json.dumps({
        "panels": [{"file": "raw1.pdf", "label": "a_b"},
                   {"file": "raw2.pdf", "label": "x%y"}],
        "cols": 2}), encoding="utf-8")
    outdir = base / "fig"
    rf.render_composite(manifest, outdir / "output.pdf",
                        outdir / "output.svg", 100, [])
    # panel copies land under TeX-safe file names
    assert (outdir / "panel_a_b.pdf").is_file()
    assert (outdir / "panel_x_y.pdf").is_file()
    tex = (outdir / "composite.tex").read_text(encoding="utf-8")
    assert r"label}{a\_b}" in tex          # typeset label escaped
    assert r"label}{x\%y}" in tex
    assert "panel_x_y.pdf" in tex          # file name safe/verbatim
    assert "panel_x%y.pdf" not in tex
    # the shipped composite.tex compiles under stock pdflatex
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
         "composite.tex"],
        cwd=outdir, capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, \
        (outdir / "composite.log").read_text(errors="replace")[-3000:]
    assert (outdir / "composite.pdf").read_bytes()[:4] == b"%PDF"
    # the assembled SVG is well-formed XML
    xml.dom.minidom.parseString(
        (outdir / "output.svg").read_text(encoding="utf-8"))


@requires_pdflatex
@requires_pdftoppm
def test_composite_svg_labels_xml_escaped(panel_pdf_dir):
    """'&'/'<' labels must not corrupt the assembled SVG."""
    base = panel_pdf_dir
    manifest = base / "hostile.composite.json"
    manifest.write_text(json.dumps({
        "panels": [{"file": "raw1.pdf", "label": "m&n"},
                   {"file": "raw2.pdf", "label": "a<b"}],
        "cols": 2}), encoding="utf-8")
    outdir = base / "hostile"
    rf.render_composite(manifest, outdir / "output.pdf",
                        outdir / "output.svg", 100, [])
    svg = (outdir / "output.svg").read_text(encoding="utf-8")
    xml.dom.minidom.parseString(svg)   # raises ParseError if malformed
    assert "(m&amp;n)" in svg
    assert "(a&lt;b)" in svg
    assert "(m&n)" not in svg and "(a<b)" not in svg


def test_write_composite_tex_escapes_labels(tmp_path):
    rf.write_composite_tex(
        tmp_path,
        [("a_b", "panel_a_b.pdf"), ("x%y", "panel_x_y.pdf"),
         ("m&n", "panel_m_n.pdf")],
        3, 1, {"canvas_w": 3600, "gap": 48, "margin": 60,
               "label_strip": 64}, 300)
    tex = (tmp_path / "composite.tex").read_text(encoding="utf-8")
    assert r"label}{a\_b}" in tex
    assert r"label}{x\%y}" in tex
    assert r"label}{m\&n}" in tex
    # raw specials never reach the typeset label definitions
    assert r"label}{a_b}" not in tex
    assert r"label}{x%y}" not in tex
    # file names stay verbatim (renderer supplies safe stems)
    assert r"file}{panel_a_b.pdf}" in tex


# ---------------------------------------------------------------------------
# F9 — user --caption is TeX-escaped in latex_include.tex
# ---------------------------------------------------------------------------

def test_write_latex_include_user_caption_escaped(tmp_path):
    rf.write_latex_include(tmp_path, "output",
                           "50% confidence & more_speed", "figx")
    tex = (tmp_path / "latex_include.tex").read_text(encoding="utf-8")
    assert r"\caption{50\% confidence \& more\_speed}" in tex
    assert "50% confidence & more_speed" not in tex


def test_write_latex_include_auto_caption_behavior_unchanged(tmp_path):
    rf.write_latex_include(tmp_path, "output", None, "fig_x")
    tex = (tmp_path / "latex_include.tex").read_text(encoding="utf-8")
    assert r"Figure: fig\_x" in tex
    assert "auto-caption --- replace" in tex


# ---------------------------------------------------------------------------
# F10 — palette gates see #RGB shorthand and #RRGGBBAA
# ---------------------------------------------------------------------------

def test_palette_check_flags_shorthand_and_8digit():
    v = rf.palette_check('<rect fill="#F00"/>', "s.svg")
    assert len(v) == 1
    assert "#FF0000" in v[0]                       # normalized form reported
    v = rf.palette_check('<rect fill="#FF000066"/>', "s.svg")
    assert len(v) == 1                             # alpha dropped, still red
    assert "#FF0000" in v[0]


def test_audit_palette_svg_shorthand_fails():
    rep = fa.Report()
    fa.audit_palette_svg('<svg><rect fill="#F00"/></svg>', rep)
    a3 = [c for c in rep.checks if c["layer"] == "A3"]
    assert [c["status"] for c in a3] == ["FAIL"]
    assert "#FF0000" in a3[0]["msg"]


def test_sanitize_palette_remaps_original_forms_and_is_idempotent():
    svg = '<svg><rect fill="#F00"/><rect fill="#00FF0080"/></svg>'
    out, n = st.sanitize_palette(svg)
    assert n == 2                                  # ORIGINAL forms remapped
    assert "#F00" not in out and "#f00" not in out
    assert "#00FF0080" not in out and "#00ff0080" not in out.lower()
    fills = re.findall(r'fill="([^"]+)"', out)
    assert len(fills) == 2
    assert all(f in st.TOKENS.values() for f in fills)
    again, n2 = st.sanitize_palette(out)
    assert again == out and n2 == 0                # idempotent


@pytest.mark.parametrize("raw,rgb", [
    ("#F00", (255, 0, 0)),
    ("#FF000066", (255, 0, 0)),                    # alpha dropped
    ("#ABC", (170, 187, 204)),
    ("#35322E", (53, 50, 46)),                     # 6-digit passthrough
])
def test_hex2rgb_roundtrips_normalized_forms(raw, rgb):
    norm = st.normalize_hex(raw)
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", norm)
    assert st.hex2rgb(norm) == rgb


# ---------------------------------------------------------------------------
# F10 controls — 6-digit behavior unchanged; garbage lengths never match
# ---------------------------------------------------------------------------

def test_controls_6digit_behavior_unchanged():
    v = rf.palette_check('<rect fill="#FF0000"/>', "s.svg")
    assert len(v) == 1 and "#FF0000" in v[0]
    assert rf.palette_check(f'<rect fill="{st.TOKENS["blue"]}"/>', "s.svg") == []
    assert rf.palette_check('<rect fill="#fff"/>', "s.svg") == []  # neutral
    out, n = st.sanitize_palette('<svg><rect fill="#3366FF"/></svg>')
    assert n == 1
    fill = re.search(r'fill="([^"]+)"', out).group(1)
    assert fill in st.TOKENS.values()


@pytest.mark.parametrize("garbage", ["#F000", "#FF000", "#FF00006", "#GGGGGG"])
def test_4_5_7_digit_hex_never_matches(garbage):
    assert rf.palette_check(f'<rect fill="{garbage}"/>', "s.svg") == []
    assert st.HEX_COLOR_RE.search(garbage) is None
    svg = f'<svg><rect fill="{garbage}"/></svg>'
    out, n = st.sanitize_palette(svg)
    assert out == svg and n == 0


def test_8digit_hex_not_split_into_6_plus_prefix():
    assert st.HEX_COLOR_RE.findall("#FF000066") == ["#FF000066"]
    assert st.HEX_COLOR_RE.findall('fill="#FF0000" x') == ["#FF0000"]
    # both forms normalize to the same canonical color
    assert rf.extract_colors('a="#FF0000" b="#FF000066"') == {"#FF0000"}


def test_html_tex_colors_stay_6digit_only():
    """xcolor rejects 3-char shorthand — the {HTML} gate must not widen."""
    assert rf.extract_colors(r"\definecolor{x}{HTML}{F00}") == set()
    assert rf.extract_colors(r"\definecolor{x}{HTML}{FF000066}") == set()
    assert rf.extract_colors(r"\definecolor{x}{HTML}{FF0000}") == {"FF0000"}
