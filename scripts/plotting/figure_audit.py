"""SciForge-OSS figure audit — internal module of the unified renderer.

This is NOT a separate pipeline tool: `render_figure.py` (the single
unified entry point) invokes it automatically after every successful
render.  Running `figure_audit.py` directly is supported for re-auditing
existing figure dirs, but the pipeline only ever calls render_figure.py.

Audit layers (Nature-level):
  A1 outputs      — output.pdf + output.png exist, non-empty, valid magic
  A2 resolution   — PNG dpi >= 300 and width >= 1200px (agent-viewable)
  A3 palette      — every saturated color in the SVG/tex/dot source is a
                    morandi token (C* <= 25 enforced by construction)
  A4 typography   — SVG text physical size >= Nature floor
                    (rsvg maps 1px = 0.75pt, verified empirically);
                    font family is TeX Gyre / Liberation / DejaVu
  A5 layout       — text not clipped outside the viewBox (heuristic),
                    sane aspect ratio, whitespace padding present
  A6 contract     — dual output, source preserved, latex_include.tex exists

Report: figure_audit.json + PASS/WARN/FAIL verdict on stdout.
Exit: 0 PASS, 1 WARN, 4 FAIL.
"""

from __future__ import annotations

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


class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, layer: str, status: str, msg: str) -> None:
        self.checks.append({"layer": layer, "status": status, "msg": msg})

    def verdict(self) -> str:
        if any(c["status"] == "FAIL" for c in self.checks):
            return "FAIL"
        if any(c["status"] == "WARN" for c in self.checks):
            return "WARN"
        return "PASS"

    def to_json(self) -> dict:
        return {"verdict": self.verdict(),
                "style_version": st.__version__,
                "checks": self.checks}


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
    pdf, png = figdir / "output.pdf", figdir / "output.png"
    for f, magic in ((pdf, b"%PDF"), (png, b"\x89PNG")):
        if not f.is_file() or f.stat().st_size == 0:
            rep.add("A1", "FAIL", f"missing or empty {f.name}")
            continue
        if f.read_bytes()[:4] != magic:
            rep.add("A1", "FAIL", f"{f.name} has invalid magic bytes")
        else:
            rep.add("A1", "PASS", f"{f.name} valid ({f.stat().st_size} B)")


def audit_resolution(png: Path, rep: Report, figdir: Path | None = None) -> None:
    try:
        from PIL import Image
        with Image.open(png) as im:
            w, h = im.size
            dpi = im.info.get("dpi", (0, 0))[0]
    except Exception as e:  # pragma: no cover
        rep.add("A2", "WARN", f"PNG unreadable: {e}")
        return
    if dpi and dpi < 290:
        rep.add("A2", "FAIL", f"PNG dpi {dpi:.0f} < 300")
    elif w < 1200:
        rep.add("A2", "WARN", f"PNG width {w}px < 1200 — small for agent review")
    else:
        rep.add("A2", "PASS", f"PNG {w}x{h} @ {dpi:.0f}dpi")
    # aspect ratio — contract §1 (PNG-based so ALL engines are covered)
    ratio = w / h if h else 0
    override = bool(figdir and (figdir / "aspect_override.txt").is_file())
    if not override and not (1.6 <= ratio <= 2.0):
        rep.add("A5", "WARN",
                f"aspect ratio {ratio:.2f} deviates from 16:9 (1.78) — "
                "re-layout toward 16:9 or drop an aspect_override.txt "
                "with the documented reason")


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
    floor = st.NATURE_FLOOR["diagram_node"]  # 10pt node label floor
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
        centered = "text-anchor:middle" in tag or 'text-anchor="middle"' in tag
        right = x + (est_w / 2 if centered else est_w)
        left = x - est_w / 2 if centered else x
        if right > vw + 4 or left < -4:
            clipped += 1
    if clipped:
        rep.add("A5", "WARN", f"{clipped} text element(s) may clip at edge")
    else:
        rep.add("A5", "PASS", f"layout bounds ok (viewBox {vw:.0f}x{vh:.0f})")
    # NOTE: the 16:9 aspect check lives in audit_resolution() (PNG-based)
    # so it covers ALL engines, not just SVG-intermediate ones.


def audit_contract(figdir: Path, rep: Report) -> None:
    src = [p for p in figdir.glob("*")
           if p.suffix in (".d2", ".dot", ".gv", ".tex", ".svg", ".py")]
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


def audit_figure(figdir: Path) -> Report:
    figdir = Path(figdir)
    rep = Report()
    audit_outputs(figdir, rep)
    png = figdir / "output.png"
    if png.is_file():
        audit_resolution(png, rep, figdir)
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
