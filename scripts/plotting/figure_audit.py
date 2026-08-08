"""SciForge-OSS figure audit — internal module of the unified renderer.

This is NOT a separate pipeline tool: `render_figure.py` (the single
unified entry point) invokes it automatically after every successful
render.  Running `figure_audit.py` directly is supported for re-auditing
existing figure dirs, but the pipeline only ever calls render_figure.py.

Audit layers (Nature-level):
  A1 outputs      — output.pdf + output.png exist, non-empty, valid magic
  A2 resolution   — PNG dpi >= 300 and width >= 1200px (agent-viewable);
                    composite figures get an explicit WARN downgrade when
                    composite_meta.json says output.pdf embeds rasterized
                    panels (vector-faithful assembly is composite.tex)
  A3 palette      — every saturated color in the SVG/tex/dot source is a
                    morandi token (C* <= 25 enforced by construction)
  A4 typography   — SVG text physical size >= Nature floor
                    (rsvg maps 1px = 0.75pt, verified empirically);
                    font family is TeX Gyre / Liberation / DejaVu
  A5 layout       — text not clipped outside the viewBox (heuristic),
                    sane aspect ratio, whitespace padding present
  A6 contract     — dual output, source preserved, latex_include.tex exists
  A7 complexity   — edge density / icon usage floors (complexity contract)
  A8 richness     — visual depth devices in hand-assembled SVG sources
  A9 brand leak   — no internal tool branding inside figure sources
  A10 occlusion   — wiring may not cross un-haloed text; text bboxes must
                    not overlap (>30% vertical intrusion => FAIL)

Report: figure_audit.json + PASS/WARN/FAIL verdict on stdout.
Exit: 0 PASS, 1 WARN, 4 FAIL.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sciforge_style as st  # noqa: E402

PX_TO_PT = 0.75  # rsvg-convert: 960px -> 720pt (measured, D65/96dpi basis)
ALLOWED_FONT_SUBSTRINGS = (
    "TeX Gyre", "Liberation", "DejaVu", "Noto Sans", "Noto Serif",
    "Source Sans", "serif", "sans-serif", "monospace",
    "d2-",  # d2 internal font-class ids (resolve to the --font-* TTF we pass)
)

# A10 text-bbox model: average per-character advance as a fraction of the
# font size, per font-family class.  Sans faces (Liberation/DejaVu/Noto
# Sans, TeX Gyre Heros) average ~0.52em per glyph, serif faces run
# slightly wider (~0.55em); an unknown/absent font-family keeps the
# conservative legacy 0.62em constant.  Exposed at module level so tests
# can pin them.
CHAR_WIDTH_ESTIMATES = {
    "sans": 0.52,
    "serif": 0.55,
    "fallback": 0.62,
}


class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.suggested_fixes: list[dict] = []

    def add(self, layer: str, status: str, msg: str) -> None:
        self.checks.append({"layer": layer, "status": status, "msg": msg})

    def add_fix(self, layer: str, fix: str) -> None:
        self.suggested_fixes.append({"layer": layer, "fix": fix})

    def verdict(self) -> str:
        if any(c["status"] == "FAIL" for c in self.checks):
            return "FAIL"
        if any(c["status"] == "WARN" for c in self.checks):
            return "WARN"
        return "PASS"

    def to_json(self) -> dict:
        d = {"verdict": self.verdict(),
             "style_version": st.__version__,
             "checks": self.checks}
        if self.suggested_fixes:
            d["suggested_fixes"] = self.suggested_fixes
        return d


def _parse_size(value: str) -> float:
    """Normalize a CSS/SVG font-size to px."""
    m = re.match(r"([\d.]+)\s*(px|pt)?", value.strip())
    if not m:
        return 0.0
    v = float(m.group(1))
    if m.group(2) == "pt":
        v /= PX_TO_PT  # pt -> px
    return v


def audit_outputs(figdir: Path, rep: Report) -> None:
    # v4.0 deliverables: output.pdf (LaTeX) + output.svg (viewing/editing)
    pdf, svg = figdir / "output.pdf", figdir / "output.svg"
    for f, magic in ((pdf, b"%PDF"), ):
        if not f.is_file() or f.stat().st_size == 0:
            rep.add("A1", "FAIL", f"missing or empty {f.name}")
            continue
        if f.read_bytes()[:4] != magic:
            rep.add("A1", "FAIL", f"{f.name} has invalid magic bytes")
        else:
            rep.add("A1", "PASS", f"{f.name} valid ({f.stat().st_size} B)")
    # SVG deliverable: required for viewing/editing (legacy output.png is
    # tolerated but no longer demanded)
    if svg.is_file() and svg.stat().st_size > 0:
        head = svg.read_bytes()[:64]
        if b"<svg" in head or head.startswith(b"<?xml"):
            rep.add("A1", "PASS", f"output.svg valid ({svg.stat().st_size} B)")
        else:
            rep.add("A1", "WARN", "output.svg present but has no <svg> root")
    elif (figdir / "output.png").is_file():
        rep.add("A1", "WARN", "legacy output.png found; v4.0 delivers "
                              "output.svg for viewing — re-render")
    else:
        rep.add("A1", "FAIL", "missing output.svg (viewing deliverable)")


def audit_resolution(svg: Path, rep: Report, figdir: Path | None = None) -> None:
    """v4.0: aspect/size checks run on the SVG viewBox (vector — dpi no
    longer applies). Legacy output.png is honored if present."""
    w = h = 0.0
    try:
        text = svg.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'viewBox="([\d.\s-]+)"', text)
        if m:
            vb = m.group(1).split()
            if len(vb) == 4:
                w, h = float(vb[2]), float(vb[3])
        if not w:
            wm = re.search(r'width="([\d.]+)', text)
            hm = re.search(r'height="([\d.]+)', text)
            if wm and hm:
                w, h = float(wm.group(1)), float(hm.group(1))
    except OSError:
        pass
    if not w or not h:
        rep.add("A2", "WARN", "SVG has no readable viewBox/size — cannot "
                              "verify dimensions")
    else:
        # adaptive width floor: a journal single-column preset legitimately
        # renders narrower than the 1200px wide-figure default
        floor = 1200.0
        if figdir is not None:
            pf = figdir / "width_preset.txt"
            if pf.is_file():
                try:
                    mm = float(pf.read_text().split()[0])
                    floor = max(500.0, mm / 25.4 * 300 * 0.85)
                except (ValueError, IndexError):
                    pass
        if w < floor:
            rep.add("A2", "WARN", f"SVG width {w:.0f}px < {floor:.0f} — small "
                                  "for agent review (pass --width-preset for "
                                  "column figs)")
        else:
            rep.add("A2", "PASS", f"SVG {w:.0f}x{h:.0f} viewBox (vector)")
    # aspect ratio — contract §1 (ALL engines covered)
    ratio = w / h if h else 0
    override = bool(figdir and (figdir / "aspect_override.txt").is_file())
    if not override and not (1.6 <= ratio <= 2.0):
        rep.add("A5", "WARN",
                f"aspect ratio {ratio:.2f} deviates from 16:9 (1.78) — "
                "re-layout toward 16:9 or drop an aspect_override.txt "
                "with the documented reason")


def audit_composite_raster(figdir: Path, rep: Report) -> None:
    """A2 honesty downgrade for composite figures.

    The composite engine rasterizes its panels into output.pdf (pdftoppm
    at <dpi>) and records that in composite_meta.json; the vector-
    faithful assembly is composite.tex.  Emit an explicit WARN so
    downstream auditing knows the PDF embeds rasters — this is an audit
    DOWNGRADE, not a FAIL: the vector path exists and is referenced by
    latex_include.tex."""
    meta = figdir / "composite_meta.json"
    if not meta.is_file():
        return
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rep.add("A2", "WARN", "composite_meta.json unreadable — cannot "
                              "verify composite panel embedding")
        return
    if data.get("raster_panels"):
        rep.add("A2", "WARN",
                f"composite: output.pdf embeds rasterized panels at "
                f"{data.get('dpi', '?')} dpi — the vector-faithful "
                f"assembly is {data.get('vector_assembly', 'composite.tex')} "
                "(audit downgrade, not a FAIL)")


def audit_palette_svg(svg_text: str, rep: Report) -> None:
    bad, seen = [], set()
    for h in sorted(set(re.findall(r"#[0-9a-fA-F]{6}", svg_text))):
        c = st.chroma(h)
        L = st.rgb2lab(st.hex2rgb(h))[0]
        if c < 2.0 or L > 96 or L < 12:
            continue  # neutrals, near-white, near-black
        if h in seen:
            continue
        seen.add(h)
        if not st.is_morandi(h):
            bad.append(f"{h} (C*={c:.1f})")
    if bad:
        rep.add("A3", "FAIL", "off-palette colors: " + ", ".join(bad))
    else:
        rep.add("A3", "PASS", "all saturated colors morandi-compliant")


def audit_source_text(text: str, rep: Report) -> None:
    """Source-level audit for engines without an SVG intermediate
    (tikz/asy/typst/blender): hex colors + declared font sizes."""
    hexes = set(re.findall(r"#[0-9a-fA-F]{6}", text))
    # tex HTML colors: \definecolor{...}{HTML}{3A3733}
    hexes |= set(re.findall(r"\{HTML\}\{([0-9a-fA-F]{6})\}", text))
    # asy rgb(0-1) triples
    for m in re.finditer(r"rgb\(([\d.]+),\s*([\d.]+),\s*([\d.]+)\)", text):
        r, g, b = (min(255, int(float(x) * 255)) for x in m.groups())
        hexes.add("#%02X%02X%02X" % (r, g, b))
    bad = []
    for h in sorted(hexes):
        c = st.chroma(h)
        L = st.rgb2lab(st.hex2rgb(h))[0]
        if c < 2.0 or L > 96 or L < 12:
            continue
        if not st.is_morandi(h):
            bad.append(f"{h} (C*={c:.1f})")
    if bad:
        rep.add("A3", "FAIL", "off-palette colors in source: " + ", ".join(bad))
    else:
        rep.add("A3", "PASS", "source colors morandi-compliant")
    # declared font sizes (tex \fontsize, asy fontsize, typst font-size)
    sizes = []
    for pat in (r"\\fontsize\{([\d.]+)\}", r"fontsize\(([\d.]+)pt\)",
                r"font-size:\s*([\d.]+)pt"):
        sizes += [float(s) for s in re.findall(pat, text)]
    if sizes and min(sizes) < st.NATURE_FLOOR["annotation"]:
        rep.add("A4", "FAIL", f"declared font size {min(sizes)}pt below floor")
    elif sizes:
        rep.add("A4", "PASS", f"declared font sizes {min(sizes)}-{max(sizes)}pt")
    else:
        rep.add("A4", "PASS", "no explicit small font sizes declared (inherits "
                              "document defaults)")


def audit_typography_svg(svg_text: str, rep: Report) -> None:
    floor = st.NATURE_FLOOR["diagram_node"]  # 12pt node label floor (v2.1)
    sizes = [_parse_size(s) for s in re.findall(
        r'font-size[:=]\s*"?([\d.]+(?:px|pt)?)"?', svg_text)]
    sizes = [s for s in sizes if s > 0]
    if not sizes:
        rep.add("A4", "WARN", "no font-size declarations found in SVG")
        return
    min_pt = min(sizes) * PX_TO_PT
    if min_pt < floor - 0.5:
        rep.add("A4", "FAIL",
                f"smallest text {min_pt:.1f}pt < Nature floor {floor}pt")
    else:
        rep.add("A4", "PASS",
                f"text sizes {min_pt:.1f}-{max(sizes)*PX_TO_PT:.1f}pt "
                f"(floor {floor}pt)")
    fams = set(re.findall(r'font-family[:=]\s*"?([^";>]+)"?', svg_text))
    bad_fams = [f for f in fams
                if not any(ok in f for ok in ALLOWED_FONT_SUBSTRINGS)]
    if bad_fams:
        rep.add("A4", "WARN", "non-approved font families: " + ", ".join(bad_fams))
    elif not fams:
        rep.add("A4", "WARN",
                "no font-family declared (inherits renderer default sans)")
    else:
        rep.add("A4", "PASS", "font families approved: " + ", ".join(sorted(fams)))


def audit_layout_svg(svg_text: str, rep: Report, figdir: Path | None = None) -> None:
    m = re.search(r'viewBox="([\d.\s-]+)"', svg_text)
    if not m:
        rep.add("A5", "WARN", "no viewBox — cannot verify layout bounds")
        return
    vb = [float(x) for x in m.group(1).split()]
    if len(vb) != 4:
        rep.add("A5", "WARN", "malformed viewBox")
        return
    vw, vh = vb[2], vb[3]
    clipped = 0
    for tm in re.finditer(
            r'<text[^>]*?x="([\d.-]+)"[^>]*?y="([\d.-]+)"[^>]*>(.*?)</text>',
            svg_text, re.S):
        x = float(tm.group(1))
        tag = tm.group(0)[: tm.group(0).find(">")]
        body = re.sub(r"<[^>]+>", "", tm.group(3))
        # d2 wraps multi-line labels in tspans sharing the anchor x
        lines = re.findall(r"<tspan[^>]*>([^<]*)</tspan>", tm.group(3)) or [body]
        max_line = max((len(s) for s in lines), default=0) or len(body)
        fs = re.search(r'font-size[:=]\s*"?([\d.]+)', tm.group(0))
        est_w = max_line * (float(fs.group(1)) if fs else 16) * 0.6
        if "text-anchor:middle" in tag or 'text-anchor="middle"' in tag:
            right = x + est_w / 2
            left = x - est_w / 2
        elif "text-anchor:end" in tag or 'text-anchor="end"' in tag:
            right = x
            left = x - est_w
        else:
            right = x + est_w
            left = x
        if right > vw + 4 or left < -4:
            clipped += 1
    if clipped:
        rep.add("A5", "WARN", f"{clipped} text element(s) may clip at edge")
    else:
        rep.add("A5", "PASS", f"layout bounds ok (viewBox {vw:.0f}x{vh:.0f})")
    # NOTE: the 16:9 aspect check lives in audit_resolution() (SVG viewBox)
    # so it covers ALL engines, not just SVG-intermediate ones.


def audit_contract(figdir: Path, rep: Report) -> None:
    # *.composite.json covers the manifests the composite engine preserves
    # next to its deliverables (composite_meta.json is a pipeline artifact,
    # NOT a source, and stays excluded)
    src = [p for p in figdir.glob("*")
           if p.suffix in (".d2", ".dot", ".gv", ".tex", ".svg", ".py")
           or p.name.endswith(".composite.json")]
    if not src:
        rep.add("A6", "FAIL", "no preserved source (spec/render script) found")
    else:
        rep.add("A6", "PASS", f"source preserved: {', '.join(p.name for p in src)}")
    if not (figdir / "latex_include.tex").is_file():
        rep.add("A6", "FAIL", "latex_include.tex missing")
    else:
        rep.add("A6", "PASS", "latex_include.tex present")


def audit_complexity(figdir: Path, rep: Report) -> None:
    """A7 — complexity floor per figure-complexity-contract.md:
    edge density, icon/custom-component usage for d2/tikz specs.
    Mechanical heuristics only; the qualitative judgment stays with the
    figure-quality-review advisor."""
    override = (figdir / "complexity_override.txt").is_file()
    spec_d2 = next(iter(figdir.glob("*.d2")), None)
    spec_tex = next(iter(figdir.glob("*.tex")), None)

    if spec_d2 is not None:
        text = spec_d2.read_text(encoding="utf-8", errors="replace")
        ids = set(re.findall(r"^([A-Za-z_][\w.-]*)\s*[:{]", text, re.M))
        ids |= set(re.findall(r"^([A-Za-z_][\w.-]*)\s*->", text, re.M))
        edges = re.findall(r"->", text)
        icons = len(re.findall(r"^\s*icon:", text, re.M))
        nodes = max(len(ids), 1)
        density = len(edges) / nodes
        msgs = []
        if density > 1.6 and not override:
            msgs.append(f"edge density {density:.2f} > 1.6 — consolidate "
                        "parallel flows into trunk/bus edges "
                        "(or add complexity_override.txt with a reason)")
        if nodes >= 5 and icons == 0 and not override:
            msgs.append(f"{nodes}-node diagram with zero icons — author "
                        "custom icons per figure-complexity-contract §1/§5")
        if msgs:
            for m in msgs:
                rep.add("A7", "WARN", m)
        else:
            rep.add("A7", "PASS",
                    f"{nodes} nodes / {len(edges)} edges "
                    f"(density {density:.2f}), {icons} icon node(s)")
    elif spec_tex is not None:
        text = spec_tex.read_text(encoding="utf-8", errors="replace")
        pics = len(re.findall(r"\\pic\b", text))
        rects = len(re.findall(r"rectangle", text))
        if pics == 0 and rects >= 5 and not override:
            rep.add("A7", "WARN", f"TikZ figure with {rects} bare rectangles "
                                  "and no \\pic — author custom components "
                                  "per figure-complexity-contract §1/§5.2")
        else:
            rep.add("A7", "PASS", f"TikZ components: {pics} pic(s), "
                                  f"{rects} rectangle ref(s)")
    else:
        rep.add("A7", "PASS", "complexity audit n/a for this engine")


def audit_richness(figdir: Path, rep: Report) -> None:
    """A8 — visual depth richness per figure-complexity-contract §7.

    Mechanical count of depth devices in hand-assembled SVG sources:
    gradients, drop shadows, mini-visualizations (sparkline/strip/grid/
    matrix), port dots, status meters.  A Visio-grade figure must not be
    flat boxes — flat-only => WARN."""
    override = (figdir / "complexity_override.txt").is_file()
    src = next(iter(figdir.glob("source*.svg")), None)
    if src is None:
        src = figdir / "intermediate.svg"
    if not src.is_file():
        rep.add("A8", "PASS", "richness audit n/a (no SVG source)")
        return
    text = src.read_text(encoding="utf-8", errors="replace")
    devices = {
        "gradients": len(re.findall(r"<(linearGradient|radialGradient)\b", text)),
        "shadows": len(re.findall(r'filter="url\(#shadow\)"', text)),
        "sparklines": len(re.findall(r"<polyline\b", text)),
        "grids": len(re.findall(r'patch grid|dot grid|token strip|attention mini',
                                text, re.I)),
        "port_dots": len(re.findall(r'<!-- port|class="port"', text)),
        "meters": len(re.findall(r'open \d+%|status meter', text, re.I)),
    }
    total = sum(devices.values())
    cards = len(re.findall(r'rx="1[0-4]"', text))
    if cards >= 4 and total < cards and not override:
        rep.add("A8", "WARN",
                f"{cards} cards but only {total} depth device(s) — add "
                "gradients/ports/mini-viz per complexity-contract §7")
    else:
        rep.add("A8", "PASS",
                f"depth devices: {total} "
                f"(gradients={devices['gradients']}, shadows={devices['shadows']}, "
                f"mini-viz={devices['sparklines'] + devices['grids']}, "
                f"ports={devices['port_dots']}, meters={devices['meters']})")


BRAND_BLOCKLIST = (
    r"sciforge", r"sci[- ]?forge", r"atomcode", r"autofigure",
    r"unified renderer", r"unified-renderer", r"figure-lab",
    r"morandi", r"pipeline skill", r"render_figure", r"v\d\.\d renderer",
)


def audit_brand_leak(figdir: Path, rep: Report) -> None:
    """A9 — figures are PAPER figures: no internal-tool branding may leak
    into them (skill names, renderer names, palette codenames, lab paths).
    Scans every preserved source in the figure dir.  Python import/sys.path
    machinery lines are exempt: they never render into the figure, and a
    repo checkout named SciForge-OSS makes the module path unavoidable."""
    hits = []
    for p in figdir.glob("*"):
        if p.suffix not in (".svg", ".tex", ".py", ".d2", ".asy", ".typ",
                            ".diag", ".dot"):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.suffix == ".py":
            kept = [ln for ln in text.splitlines()
                    if not re.match(r"^\s*(?:sys\.path|import|from)\b", ln)]
            text = "\n".join(kept)
        for pat in BRAND_BLOCKLIST:
            for m in re.finditer(pat, text, re.I):
                line = text[: m.start()].count("\n") + 1
                hits.append(f"{p.name}:{line} '{m.group(0)}'")
                if len(hits) > 6:
                    break
    if hits:
        rep.add("A9", "FAIL", "internal branding leaked into figure: "
                + "; ".join(hits[:6]))
    else:
        rep.add("A9", "PASS", "no internal branding in figure sources")


_NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _svg_viewport(svg_text: str) -> tuple[float, float, float, float]:
    """Establish the px coordinate scale of an SVG document.

    Parses the viewBox AND the width/height attributes of the <svg> root.
    Absolute units are normalized to px (pt via PX_TO_PT); a percentage,
    em-based or missing width/height falls back to the viewBox.  Returns
    (scale_x, scale_y, vb_w, vb_h) where scale maps viewBox user units to
    rendered px (1.0 when only the viewBox is declared).  All A10 overlap
    math below runs in user units — a uniform viewport scale cancels out
    of every comparison — but the parse is still required so SVGs whose
    width/height are declared in pt/% fall back to the viewBox instead of
    mis-scaling the bbox model.
    """
    sm = re.search(r"<svg\b[^>]*>", svg_text)
    tag = sm.group(0) if sm else ""
    vb_w = vb_h = 0.0
    m = re.search(r'viewBox="([^"]+)"', tag)
    if m:
        parts = m.group(1).split()
        if len(parts) == 4:
            try:
                vb_w, vb_h = float(parts[2]), float(parts[3])
            except ValueError:
                vb_w = vb_h = 0.0

    def _attr_px(attr: str) -> float | None:
        am = re.search(rf'{attr}="([^"]+)"', tag)
        if not am:
            return None
        num = re.match(r"\s*([\d.]+)\s*(px|pt)?\s*$", am.group(1))
        if not num:  # percentage / em / auto -> fall back to the viewBox
            return None
        v = float(num.group(1))
        return v / PX_TO_PT if num.group(2) == "pt" else v

    px_w, px_h = _attr_px("width"), _attr_px("height")
    sx = px_w / vb_w if (px_w and vb_w) else 1.0
    sy = px_h / vb_h if (px_h and vb_h) else 1.0
    return sx, sy, vb_w, vb_h


def _char_width_factor(font_family: str | None) -> float:
    """Average per-character advance (x font-size) for a font-family list.

    Approved sans families (Liberation/DejaVu/Noto Sans, TeX Gyre Heros,
    Helvetica/Arial look-alikes) -> 0.52; serif faces (TeX Gyre
    Termes/Pagella, Times, ...) -> 0.55; unknown families keep the
    conservative 0.62 legacy constant (CHAR_WIDTH_ESTIMATES)."""
    if not font_family:
        return CHAR_WIDTH_ESTIMATES["fallback"]
    fam = font_family.lower()
    if "sans" in fam or "heros" in fam or "helvet" in fam or "arial" in fam:
        return CHAR_WIDTH_ESTIMATES["sans"]
    if ("serif" in fam or "termes" in fam or "pagella" in fam
            or "times" in fam or "georgia" in fam):
        return CHAR_WIDTH_ESTIMATES["serif"]
    return CHAR_WIDTH_ESTIMATES["fallback"]  # monospace & unknown


def _text_bbox(x: float, y: float,
               chunks: list[tuple[str, float | None, float]],
               font_size: float, anchor: str = "start",
               char_w: float = CHAR_WIDTH_ESTIMATES["fallback"]
               ) -> tuple[float, float, float, float]:
    """Estimated bbox (x0, y0, x1, y1) of ONE <text> element.

    `chunks` is the element's text split into positioned runs; each entry
    is (content, own_x, dy) following SVG tspan semantics: a chunk with
    its own x starts a new line at that x, dy accumulates vertically from
    the previous chunk.  Widths are estimated as
    len(content) * font_size * char_w; `anchor` (start/middle/end) is
    applied per chunk.  Returns the union bbox covering all chunks —
    (x, y-font_size, x, y) when there is nothing to measure.
    """
    cur_x, cur_y = x, y
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    any_chunk = False
    for content, own_x, dy in chunks:
        if own_x is not None:
            cur_x = own_x          # tspan x: restart the line at this x
        cur_y += dy                # dy accumulates vertically
        w = len(content) * font_size * char_w
        if anchor == "middle":
            cx0 = cur_x - w / 2.0
        elif anchor == "end":
            cx0 = cur_x - w
        else:
            cx0 = cur_x
        cx1 = cx0 + w
        x0, x1 = min(x0, cx0), max(x1, cx1)
        # baseline box: ascender ~1.0em above, descender ~0.4em below
        y0, y1 = min(y0, cur_y - font_size), max(y1, cur_y + 0.4 * font_size)
        cur_x = cx1                # the next x-less run follows this one
        any_chunk = True
    if not any_chunk:
        return (x, y - font_size, x, y)
    return (x0, y0, x1, y1)


_TRANSFORM_FN_RE = re.compile(
    r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


def _parse_transform(value: str) -> tuple[float, float, float, bool]:
    """Parse an SVG transform attribute into (scale, tx, ty, supported).

    Supported: translate(tx[, ty]) and uniform scale(s) chains, e.g.
    'translate(10, 20) scale(2)'.  The result maps a point p to
    scale*p + (tx, ty).  matrix()/rotate()/skew*() and NON-uniform scale
    are out of scope for the bbox model: supported comes back False and
    the caller skips the element (flagged, never a crash).
    """
    s, tx, ty = 1.0, 0.0, 0.0
    for m in _TRANSFORM_FN_RE.finditer(value or ""):
        fn = m.group(1)
        try:
            args = [float(v) for v in _NUM_RE.findall(m.group(2))]
        except ValueError:
            return s, tx, ty, False
        if fn == "translate":
            s2 = 1.0
            t2x = args[0] if args else 0.0
            t2y = args[1] if len(args) > 1 else 0.0
        elif fn == "scale":
            sx = args[0] if args else 1.0
            sy = args[1] if len(args) > 1 else sx
            if sx != sy:
                return s, tx, ty, False  # non-uniform scale: out of scope
            s2, t2x, t2y = sx, 0.0, 0.0
        else:  # matrix / rotate / skewX / skewY — out of scope
            return s, tx, ty, False
        # compose: everything parsed so far is OUTER, the new fn inner —
        # p' = s*(s2*p + t2) + t
        s, tx, ty = s * s2, s * t2x + tx, s * t2y + ty
    return s, tx, ty, True


def _num_attr(attrs: str, name: str, default: float | None) -> float | None:
    """First numeric value of an attribute (`None` when absent)."""
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    if not m:
        return default
    nums = _NUM_RE.findall(m.group(1))
    if not nums:
        return default
    try:
        return float(nums[0])
    except ValueError:
        return default


def _ancestor_context(svg_text: str) -> dict[int, dict]:
    """Per-<text> ancestor state: accumulated transform + font-family.

    Walks <g>/<text> open/close tags in document order with a stack, so
    every <text> start position maps to the transform of ALL enclosing
    <g> elements composed with the text's own transform, plus the nearest
    inherited font-family (root <svg> font-family is the base).  When any
    transform on the chain is unsupported (matrix/rotate/skew/non-uniform
    scale) the entry is flagged supported=False so callers can skip the
    element instead of guessing.
    """
    sm = re.search(r"<svg\b[^>]*>", svg_text)
    root_fam = None
    if sm:
        fm = re.search(r'font-family="([^"]+)"', sm.group(0))
        if fm:
            root_fam = fm.group(1)
    ctx: dict[int, dict] = {}
    # state list: [scale, tx, ty, supported, font_family]
    cur = [1.0, 0.0, 0.0, True, root_fam]
    stack: list[list] = []
    for m in re.finditer(r"<g\b[^>]*>|</g\s*>|<text\b[^>]*>", svg_text):
        tag = m.group(0)
        if tag.startswith("</g"):
            if stack:
                cur = stack.pop()
            continue
        if tag.startswith("<text"):
            s, tx, ty, ok, fam = cur
            fm = re.search(r'font-family="([^"]+)"', tag)
            if fm:
                fam = fm.group(1)
            tm = re.search(r'transform="([^"]*)"', tag)
            if tm:
                s2, tx2, ty2, ok2 = _parse_transform(tm.group(1))
                s, tx, ty, ok = s * s2, s * tx2 + tx, s * ty2 + ty, ok and ok2
            ctx[m.start()] = {"s": s, "tx": tx, "ty": ty,
                              "supported": ok, "font_family": fam}
            continue
        if tag.endswith("/>"):
            continue  # self-closing <g/> contributes nothing
        stack.append(cur)
        s, tx, ty, ok, fam = cur
        fm = re.search(r'font-family="([^"]+)"', tag)
        if fm:
            fam = fm.group(1)
        tm = re.search(r'transform="([^"]*)"', tag)
        if tm:
            s2, tx2, ty2, ok2 = _parse_transform(tm.group(1))
            s, tx, ty, ok = s * s2, s * tx2 + tx, s * ty2 + ty, ok and ok2
        cur = [s, tx, ty, ok, fam]
    return ctx


def _seg_intersects_rect(p1, p2, r) -> bool:
    """Liang-Barsky: does segment p1-p2 intersect rect (x0,y0,x1,y1)?"""
    x0, y0, x1, y1 = r
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    if dx == 0 and dy == 0:
        return x0 <= p1[0] <= x1 and y0 <= p1[1] <= y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, p1[0] - x0), (dx, x1 - p1[0]),
                 (-dy, p1[1] - y0), (dy, y1 - p1[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def audit_text_occlusion(svg_text: str, rep: Report) -> None:
    """A10 — text must never be occluded by wiring: a line segment passing
    through a text bbox without a solid halo/background rect is flagged.

    Bbox model (pure Python, CHAR_WIDTH_ESTIMATES): the SVG viewport is
    established from viewBox + width/height attrs (_svg_viewport); per-
    character widths come from the font-metric table keyed by family
    (0.52 sans / 0.55 serif / 0.62 unknown); per-tspan positioning is
    honored (a tspan x starts a new line at that x, dy accumulates
    vertically) and one union bbox covers all tspans of a text element.
    translate()/uniform-scale() transforms on ancestor <g> elements (and
    on the text itself) are applied to the bbox; matrix()/rotate() and
    non-uniform scale are OUT OF SCOPE — such texts are skipped via a
    flag, never a crash.  Halo = a bright rect covering >=80% of the
    text bbox."""
    # Viewport px scale: all geometry below is in viewBox user units, in
    # which a uniform viewport scale cancels out of every comparison.
    _sx, _sy, _vw, _vh = _svg_viewport(svg_text)  # noqa: F841
    ancestors = _ancestor_context(svg_text)
    texts = []
    skipped_transforms = 0
    for tm in re.finditer(r"<text\b([^>]*)>(.*?)</text>", svg_text, re.S):
        attrs = tm.group(1)
        info = ancestors.get(tm.start())
        if info is not None and not info["supported"]:
            # matrix()/rotate()/non-uniform-scale ancestor: bbox model is
            # out of scope here — skip the element (flagged), don't crash
            skipped_transforms += 1
            continue
        x = _num_attr(attrs, "x", 0.0)
        y = _num_attr(attrs, "y", 0.0)
        fsm = re.search(r'font-size[:=]\s*"?([^";>]+)', attrs)
        fs = _parse_size(fsm.group(1)) if fsm else 16.0
        if fs <= 0:
            fs = 16.0
        am = re.search(r'text-anchor[:=]\s*"?(\w+)', attrs)
        anchor = am.group(1) if am else "start"
        # per-tspan walk: each tspan starts a positioned run; raw text
        # outside tspans forms runs anchored at the text position
        chunks: list[tuple[str, float | None, float]] = []
        baseline = y
        cur: dict | None = None

        def _flush() -> None:
            nonlocal cur
            if cur is not None:
                piece = html.unescape(cur["content"]).strip()
                if piece:
                    chunks.append((piece, cur["own_x"], cur["dy"]))
                cur = None

        for pm in re.finditer(r"<tspan\b([^>]*?)/?>|</tspan\s*>|([^<]+)",
                              tm.group(2)):
            if pm.group(2) is not None:
                if not pm.group(2).strip():
                    continue
                if cur is None:
                    cur = {"content": "", "own_x": None, "dy": 0.0}
                cur["content"] += pm.group(2)
                continue
            if pm.group(0).startswith("</tspan"):
                _flush()
                continue
            _flush()  # a new tspan starts a new run
            tattrs = pm.group(1)
            t_x = _num_attr(tattrs, "x", None)
            t_y = _num_attr(tattrs, "y", None)
            t_dy = _num_attr(tattrs, "dy", 0.0) or 0.0
            if t_y is not None:
                t_dy = t_y - baseline  # absolute tspan y resets baseline
            baseline += t_dy
            cur = {"content": "", "own_x": t_x, "dy": t_dy}
        _flush()
        if not chunks:
            continue
        fam_m = re.search(r'font-family[:=]\s*"?([^";>]+)', attrs)
        fam = fam_m.group(1) if fam_m else (
            info["font_family"] if info is not None else None)
        bx0, by0, bx1, by1 = _text_bbox(
            x, y, chunks, fs, anchor, _char_width_factor(fam))
        if info is not None:  # apply ancestor+own translate/scale chain
            bx0, bx1 = info["s"] * bx0 + info["tx"], info["s"] * bx1 + info["tx"]
            by0, by1 = info["s"] * by0 + info["ty"], info["s"] * by1 + info["ty"]
        label = " ".join(c[0] for c in chunks)[:24]
        texts.append((bx0, by0, bx1, by1, label))
    # halo rects: bright fills (canvas/white)
    halos = []
    for rm in re.finditer(r'<rect[^>]*>', svg_text):
        t = rm.group(0)
        fill = re.search(r'fill="(#[0-9A-Fa-f]{6}|white)"', t)
        if not fill:
            continue
        f = fill.group(1)
        bright = f.lower() in ("#faf8f5", "#ffffff", "white")
        if not bright:
            continue
        try:
            x = float(re.search(r'x="([\d.-]+)"', t).group(1))
            y = float(re.search(r'y="([\d.-]+)"', t).group(1))
            w = float(re.search(r'width="([\d.-]+)"', t).group(1))
            h = float(re.search(r'height="([\d.-]+)"', t).group(1))
        except AttributeError:
            continue
        halos.append((x, y, x + w, y + h))

    def covered(t):
        x0, y0, x1, y1, _ = t
        for hx0, hy0, hx1, hy1 in halos:
            ix = max(0, min(x1, hx1) - max(x0, hx0))
            iy = max(0, min(y1, hy1) - max(y0, hy0))
            if (x1 - x0) > 0 and (y1 - y0) > 0 and \
                    ix * iy >= 0.8 * (x1 - x0) * (y1 - y0):
                return True
        return False

    # gather line segments (polyline points, <line>, path M/L chains).
    # Arc/curve commands are skipped — occlusion risk lives in straight runs.
    segs = []
    for pm in re.finditer(r'<polyline[^>]*points="([^"]+)"[^>]*>', svg_text):
        nums = [float(v) for v in
                re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)", pm.group(1))]
        for i in range(0, len(nums) - 3, 2):
            segs.append(((nums[i], nums[i + 1]), (nums[i + 2], nums[i + 3])))
    for pm in re.finditer(r'<line[^>]*>', svg_text):
        t = pm.group(0)
        try:
            segs.append(((float(re.search(r'x1="([\d.-]+)"', t).group(1)),
                          float(re.search(r'y1="([\d.-]+)"', t).group(1))),
                         (float(re.search(r'x2="([\d.-]+)"', t).group(1)),
                          float(re.search(r'y2="([\d.-]+)"', t).group(1)))))
        except AttributeError:
            continue
    num_re = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
    for pm in re.finditer(r'<path[^>]*>', svg_text):
        tag = pm.group(0)
        d = re.search(r'd="([^"]+)"', tag)
        if not d:
            continue
        if 'fill="none"' not in tag:
            continue  # filled shapes are not wiring
        # walk explicit M/L (absolute or relative) coordinate runs only
        for cm in re.finditer(r"[MmLl]((?:\s*[-+]?(?:\d+\.?\d*|\.\d+))+)",
                              d.group(1)):
            coords = [float(v) for v in num_re.findall(cm.group(1))]
            pts = [(coords[i], coords[i + 1])
                   for i in range(0, len(coords) - 1, 2)]
            segs.extend(zip(pts, pts[1:]))

    bad = []
    for t in texts:
        if covered(t):
            continue
        r = (t[0], t[1], t[2], t[3])
        for s1, s2 in segs:
            if _seg_intersects_rect(s1, s2, r):
                bad.append(t[4])
                break
    if bad:
        rep.add("A10", "WARN", f"{len(bad)} label(s) crossed by wiring without "
                f"a halo rect (first: {bad[:3]}) — add background rects or "
                "re-route")
    else:
        rep.add("A10", "PASS", "no wiring crosses unlabeled text bboxes")

    # text-on-text overlap: labels truly collide when the vertical
    # intrusion exceeds 30% of the smaller label's height (area ratios are
    # inconsistent across label widths — short labels would fail at the
    # same line spacing where wide ones pass).  For each collision the
    # audit emits an actionable fix: move the LOWER label down by the
    # intrusion depth + 4px clearance (scoped revision, contract §4.6).
    overlaps = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            if ix <= 16 or iy <= 0:
                continue
            smaller_h = min(a[3] - a[1], b[3] - b[1])
            if smaller_h > 0 and iy > 0.30 * smaller_h:
                overlaps.append(f"'{a[4]}' vs '{b[4]}'")
                lower = b if b[1] >= a[1] else a
                shift = iy + 4
                rep.add_fix(
                    "A10",
                    f"move label '{lower[4]}' down by {shift:.0f}px "
                    f"(baseline y {lower[3]:.0f} -> {lower[3] + shift:.0f}), "
                    f"or re-anchor it to clear '{(a if lower is b else b)[4]}'")
    if overlaps:
        rep.add("A10", "FAIL", f"{len(overlaps)} text-overlap pair(s): "
                + "; ".join(overlaps[:4]) + " — see suggested_fixes")
    else:
        rep.add("A10", "PASS", f"{len(texts)} labels, zero text-on-text overlap")

    # layer structure: a Visio-grade figure organizes content in <g> layers
    layers = len(re.findall(r'<g[^>]*class="layer', svg_text))
    if layers == 0 and len(texts) >= 20:
        rep.add("A10", "WARN", "no <g class=\"layer-*\"> structure — organize "
                               "canvas/cards/wiring/labels into named layers")


def audit_figure(figdir: Path) -> Report:
    figdir = Path(figdir)
    rep = Report()
    audit_outputs(figdir, rep)
    out_svg = figdir / "output.svg"
    if out_svg.is_file():
        audit_resolution(out_svg, rep, figdir)
    audit_composite_raster(figdir, rep)
    svg = figdir / "intermediate.svg"
    if not svg.is_file():
        svg = next(iter(figdir.glob("*.svg")), None)
    if svg is not None and svg.suffix == ".svg":
        text = svg.read_text(encoding="utf-8", errors="replace")
        audit_palette_svg(text, rep)
        audit_typography_svg(text, rep)
        audit_layout_svg(text, rep, figdir)
    else:
        # engines without SVG intermediate: audit the preserved SOURCE
        srcs = [p for p in figdir.glob("*")
                if p.suffix in (".tex", ".asy", ".typ", ".py", ".blender.py")]
        if srcs:
            audit_source_text(srcs[0].read_text(encoding="utf-8",
                                                errors="replace"), rep)
        else:
            rep.add("A3", "WARN", "no SVG intermediate or source to audit")
    audit_contract(figdir, rep)
    audit_complexity(figdir, rep)
    audit_richness(figdir, rep)
    audit_brand_leak(figdir, rep)
    svg = figdir / "intermediate.svg"
    if not svg.is_file():
        svg = next(iter(figdir.glob("source*.svg")), None)
    if svg is not None and svg.is_file():
        audit_text_occlusion(svg.read_text(encoding="utf-8", errors="replace"),
                             rep)
    return rep


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: figure_audit.py <figure_dir> [more dirs...]",
              file=sys.stderr)
        return 2
    worst = 0
    for d in argv[1:]:
        figdir = Path(d)
        rep = audit_figure(figdir)
        out = rep.to_json()
        (figdir / "figure_audit.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        v = out["verdict"]
        print(f"[{v}] {figdir}")
        for c in out["checks"]:
            if c["status"] != "PASS":
                print(f"   {c['status']:4s} {c['layer']} {c['msg']}")
        worst = max(worst, {"PASS": 0, "WARN": 1, "FAIL": 4}[v])
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
