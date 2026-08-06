#!/usr/bin/env python3
"""SciForge-OSS unified figure renderer — one CLI for all engines.

Renders a figure SOURCE to the mandatory DUAL OUTPUT (output.pdf +
output.png), enforcing the morandi design system
(`sciforge_style.py`).  Supported sources:

  d2        spec.d2        -> [preamble inject] -> d2 (dagre/elk) -> svg -> pdf+png
  graphviz  spec.dot       -> dot/neato/fdp     -> svg -> pdf+png
  tikz      spec.tex       -> pdflatex (standalone) -> pdfcrop -> pdf -> png
  asy       spec.asy       -> asy -f pdf        -> pdfcrop -> pdf -> png
  typst     spec.typ       -> typst compile     -> pdfcrop -> pdf -> png
  blender   spec.py        -> blender -b -P (Cycles CPU headless) -> png(+pdf)
  svg       source.svg     -> rsvg-convert      -> pdf+png  (AI-direct last resort)

Usage:
  python render_figure.py spec.d2  --out figures/arch/ --name output \
         [--layout elk] [--pad 80] [--dpi 300] [--no-preamble] [--caption "..."]

Outputs written next to --out (default: next to the source):
  output.pdf  output.png  latex_include.tex  render.log  figure_audit.json
The ORIGINAL source file is copied beside them (spec.d2 / spec.dot / ...)
so the figure directory is self-contained and reproducible.

Exit codes: 0 = success, 2 = palette/contract violation, 3 = tool error,
4 = audit FAIL under --strict.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sciforge_style as st  # noqa: E402
import figure_audit  # noqa: E402  (internal audit module — NOT a separate tool)

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
TOOL_TIMEOUT = 240


def run(cmd: list[str], cwd: str | None = None, log: list | None = None) -> str:
    """Run a tool; raise RuntimeError with stderr on failure."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=TOOL_TIMEOUT)
    except FileNotFoundError:
        raise RuntimeError(f"tool not found: {cmd[0]}")
    if log is not None:
        log.append("$ " + " ".join(cmd))
        if r.stdout.strip():
            log.append(r.stdout.strip()[:4000])
        if r.stderr.strip():
            log.append("[stderr] " + r.stderr.strip()[:4000])
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed (rc={r.returncode}):\n"
                           f"{r.stderr[:3000]}")
    return r.stdout


def which(*names: str) -> str | None:
    for n in names:
        if shutil.which(n):
            return n
    return None


def palette_check(text: str, src_name: str, svg: bool = False) -> list[str]:
    """Return violations: hex colors present that are not morandi-compliant.

    White-lists: pure white/black/none and near-neutrals are allowed (frame
    geometry).  Every SATURED off-palette color is a violation.
    """
    bad = []
    for h in sorted(set(HEX_RE.findall(text))):
        r, g, b = st.hex2rgb(h)
        L, _, _ = st.rgb2lab((r, g, b))
        c = st.chroma(h)
        # neutrals (C*<2) always ok; white/black always ok
        if c < 2.0 or L > 96 or L < 12:
            continue
        if not st.is_morandi(h):
            bad.append(f"{src_name}: off-palette color {h} (C*={c:.1f})")
    return bad


def render_d2(src: Path, out_pdf: Path, out_png: Path, layout: str,
              pad: int, dpi: int, inject: bool, log: list,
              keep_svg: Path | None = None) -> None:
    spec = src.read_text(encoding="utf-8")
    bad = palette_check(spec, src.name)
    if bad:
        raise PaletteError(bad)
    compiled = (st.d2_preamble() + "\n" + spec) if inject else spec
    with tempfile.TemporaryDirectory() as td:
        tmp_d2 = Path(td) / "render.d2"
        tmp_d2.write_text(compiled, encoding="utf-8")
        tmp_svg = Path(td) / "render.svg"
        cmd = ["d2", "--layout", layout, "--pad", str(pad)] + \
            st.d2_font_flags() + [str(tmp_d2), str(tmp_svg)]
        run(cmd, log=log)
        svg2dual(tmp_svg, out_pdf, out_png, dpi, log, keep_svg)


def render_graphviz(src: Path, out_pdf: Path, out_png: Path, layout: str,
                    dpi: int, log: list, keep_svg: Path | None = None) -> None:
    spec = src.read_text(encoding="utf-8")
    bad = palette_check(spec, src.name)
    if bad:
        raise PaletteError(bad)
    engine = layout if layout in ("dot", "neato", "fdp", "sfdp", "circo", "twopi") else "dot"
    with tempfile.TemporaryDirectory() as td:
        tmp_svg = Path(td) / "render.svg"
        run([engine, "-Tsvg", str(src), "-o", str(tmp_svg)], log=log)
        svg2dual(tmp_svg, out_pdf, out_png, dpi, log, keep_svg)


def render_tikz(src: Path, out_pdf: Path, out_png: Path, dpi: int,
                log: list) -> None:
    tex = src.read_text(encoding="utf-8")
    if r"\documentclass" not in tex:
        tex = ("\\documentclass[tikz,border=8pt]{standalone}\n"
               "\\usepackage{tikz,tikz-cd}\n\\begin{document}\n"
               + tex + "\n\\end{document}\n")
    # morandi palette for tikz
    inject = (
        "\\definecolor{sfink}{HTML}{3A3733}\n"
        "\\definecolor{sfsurface}{HTML}{EDE9E2}\n"
        "\\definecolor{sfblue}{HTML}{93A7BB}\n"
        "\\definecolor{sfsage}{HTML}{A4B294}\n"
        "\\definecolor{sfmauve}{HTML}{BDA5A7}\n"
        "\\definecolor{sfochre}{HTML}{C4A880}\n"
        "\\definecolor{sftaupe}{HTML}{B0A292}\n"
        "\\definecolor{sfrose}{HTML}{D9BCBC}\n"
    )
    tex = tex.replace("\\begin{document}", "\\begin{document}\n" + inject, 1)
    bad = palette_check(tex, src.name)
    if bad:
        raise PaletteError(bad)
    with tempfile.TemporaryDirectory() as td:
        texfile = Path(td) / "render.tex"
        texfile.write_text(tex, encoding="utf-8")
        run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             "render.tex"], cwd=td, log=log)
        shutil.copyfile(Path(td) / "render.pdf", out_pdf)
    run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile",
         str(out_pdf), str(out_png.with_suffix(""))], log=log)


def render_python(src: Path, outdir: Path, dpi: int, log: list) -> None:
    """Data-plot pipeline: run the figure's render.py inside outdir.

    The script MUST save `output.pdf` and `output.png` in its CWD (the
    figure dir) and call apply_matplotlib_style() first.  After running,
    the PNG dpi is stamped and both files are validated; the unified CLI
    then adds latex_include.tex + the embedded audit, keeping data plots
    on the same single-entry contract as diagrams.
    """
    if src.resolve() != (outdir / src.name).resolve():
        shutil.copyfile(src, outdir / src.name)
        src = outdir / src.name
    run([sys.executable, str(src)], cwd=str(outdir), log=log)
    png = outdir / "output.png"
    if png.is_file():
        stamp_png_dpi(png, dpi)


def render_asymptote(src: Path, out_pdf: Path, out_png: Path, dpi: int,
                     log: list) -> None:
    """Asymptote — publication vector engine for geometry/mechanism figures."""
    asy = src.read_text(encoding="utf-8")
    bad = palette_check(asy, src.name)
    if bad:
        raise PaletteError(bad)
    with tempfile.TemporaryDirectory() as td:
        run(["asy", "-f", "pdf", "-o", str(Path(td) / "render.pdf"), str(src)],
            cwd=td, log=log)
        cropped = Path(td) / "render_crop.pdf"
        if which("pdfcrop"):
            run(["pdfcrop", str(Path(td) / "render.pdf"), str(cropped)],
                cwd=td, log=log)
            shutil.copyfile(cropped, out_pdf)
        else:
            shutil.copyfile(Path(td) / "render.pdf", out_pdf)
    run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile",
         str(out_pdf), str(out_png.with_suffix(""))], log=log)
    stamp_png_dpi(out_png, dpi)


def render_typst(src: Path, out_pdf: Path, out_png: Path, dpi: int,
                 log: list) -> None:
    """Typst (fletcher/CeTZ) — fast declarative diagrams."""
    typ = src.read_text(encoding="utf-8")
    bad = palette_check(typ, src.name)
    if bad:
        raise PaletteError(bad)
    with tempfile.TemporaryDirectory() as td:
        run(["typst", "compile", str(src), str(Path(td) / "render.pdf")], log=log)
        cropped = Path(td) / "render_crop.pdf"
        if which("pdfcrop"):
            run(["pdfcrop", str(Path(td) / "render.pdf"), str(cropped)],
                cwd=td, log=log)
            shutil.copyfile(cropped, out_pdf)
        else:
            shutil.copyfile(Path(td) / "render.pdf", out_pdf)
    run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile",
         str(out_pdf), str(out_png.with_suffix(""))], log=log)
    stamp_png_dpi(out_png, dpi)


def render_blender(src: Path, out_pdf: Path, out_png: Path, dpi: int,
                   log: list) -> None:
    """Blender (Cycles, headless CPU) — cover-grade 3D mechanism render.

    The script MUST set bpy.context.scene.render.filepath to the literal
    token SCIFORGE_OUTPUT_PNG which is replaced with out_png's path.
    Produces PNG natively; PDF wraps it via img2pdf-style pdflatex.
    """
    script = src.read_text(encoding="utf-8")
    script = script.replace("SCIFORGE_OUTPUT_PNG", str(out_png))
    with tempfile.TemporaryDirectory() as td:
        tmp_py = Path(td) / "render.py"
        tmp_py.write_text(script, encoding="utf-8")
        run(["blender", "-b", "-P", str(tmp_py)], cwd=td, log=log)
    if not out_png.is_file():
        raise RuntimeError("blender script produced no PNG "
                           "(must render to SCIFORGE_OUTPUT_PNG)")
    stamp_png_dpi(out_png, dpi)
    # wrap PNG into a vector-safe PDF for LaTeX embedding
    _png_to_pdf(out_png, out_pdf, dpi, log)


def _png_to_pdf(png: Path, pdf: Path, dpi: int, log: list) -> None:
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        with Image.open(png) as im:
            w, h = im.size
        pts_w, pts_h = 72 * w / dpi, 72 * h / dpi
        tex = (
            "\\documentclass[varwidth]{standalone}\n"
            "\\usepackage{graphicx}\n"
            "\\begin{document}\n"
            f"\\includegraphics[width={pts_w:.1f}pt,height={pts_h:.1f}pt]"
            "{img.png}\n"
            "\\end{document}\n"
        )
        (Path(td) / "main.tex").write_text(tex, encoding="utf-8")
        shutil.copyfile(png, Path(td) / "img.png")
        run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             "main.tex"], cwd=td, log=log)
        shutil.copyfile(Path(td) / "main.pdf", pdf)


def render_svg(src: Path, out_pdf: Path, out_png: Path, dpi: int,
               log: list, keep_svg: Path | None = None) -> None:
    svg = src.read_text(encoding="utf-8")
    bad = palette_check(svg, src.name, svg=True)
    if bad:
        raise PaletteError(bad)
    svg2dual(src, out_pdf, out_png, dpi, log, keep_svg)


def svg2dual(svg: Path, out_pdf: Path, out_png: Path, dpi: int,
             log: list, keep_intermediate: Path | None = None) -> None:
    # Deterministic palette sanitization BEFORE delivery: engine-injected
    # theme colors (d2/graphviz defaults) are remapped to morandi tokens.
    text = svg.read_text(encoding="utf-8")
    text, n = st.sanitize_palette(text)
    if n:
        svg.write_text(text, encoding="utf-8")
        log.append(f"# palette sanitized: {n} engine-injected colors remapped")
    if keep_intermediate is not None:
        shutil.copyfile(svg, keep_intermediate)
    conv = which("rsvg-convert", "inkscape")
    if conv == "rsvg-convert":
        run(["rsvg-convert", "-f", "pdf", "-o", str(out_pdf), str(svg)], log=log)
        run(["rsvg-convert", "-f", "png", "-d", str(dpi), "-p", str(dpi),
             "-o", str(out_png), str(svg)], log=log)
    elif conv == "inkscape":
        run(["inkscape", str(svg), f"--export-filename={out_pdf}"], log=log)
        run(["inkscape", str(svg), f"--export-filename={out_png}",
             f"--export-dpi={dpi}"], log=log)
    else:
        raise RuntimeError("no SVG converter found (need rsvg-convert or inkscape)")
    stamp_png_dpi(out_png, dpi)


def stamp_png_dpi(png: Path, dpi: int) -> None:
    """Ensure the PNG carries pHYs dpi metadata (rsvg-convert omits it)."""
    try:
        from PIL import Image
        with Image.open(png) as im:
            im.save(png, dpi=(dpi, dpi))
    except Exception:
        pass  # metadata-only; never fail a render over it


class PaletteError(RuntimeError):
    def __init__(self, violations: list[str]):
        super().__init__("morandi palette violations:\n" + "\n".join(violations))
        self.violations = violations


def write_latex_include(outdir: Path, name: str, caption: str | None,
                        label: str | None) -> None:
    cap = caption or f"Figure: {label or name} (auto-caption — replace)."
    lab = label or name
    (outdir / "latex_include.tex").write_text(
        "\\begin{figure}[htbp]\n"
        "    \\centering\n"
        f"    \\includegraphics[width=0.9\\textwidth]{{figures/{lab}/output.pdf}}\n"
        f"    \\caption{{{cap}}}\n"
        f"    \\label{{fig:{lab}}}\n"
        "\\end{figure}\n", encoding="utf-8")


def doctor() -> int:
    """Environment self-check: report which engines are usable.

    Part of the single-entry contract — the pipeline asks ONE tool
    ("is my figure toolchain ready?") and gets a full answer.
    """
    checks = [
        ("d2", ["d2"], "complex architecture/flow diagrams (primary)"),
        ("graphviz/dot", ["dot"], "fallback graph layout"),
        ("pdflatex", ["pdflatex"], "tikz/tikz-cd theoretical diagrams"),
        ("asy", ["asy"], "Asymptote math/geometry mechanism figures"),
        ("typst", ["typst"], "Typst fletcher/CeTZ fast diagrams"),
        ("blender", ["blender"], "Blender Cycles headless 3D renders"),
        ("rsvg-convert", ["rsvg-convert"], "SVG -> PDF+PNG conversion"),
        ("inkscape", ["inkscape"], "SVG conversion fallback (optional)"),
        ("pdftoppm", ["pdftoppm"], "PDF -> PNG rasterization"),
        ("pdfcrop", ["pdfcrop"], "PDF whitespace crop"),
        ("svgo", ["svgo"], "SVG optimization (optional)"),
    ]
    core_ok = True
    print("SciForge unified figure toolchain doctor")
    print(f"  design system: sciforge_style v{st.__version__}")
    for name, cmds, role in checks:
        found = which(*cmds)
        if found:
            mark = "OK  "
        elif name in ("inkscape", "svgo", "blender", "typst", "asy"):
            mark = "opt "  # optional engines / fallbacks
        else:
            mark = "MISS"
            if name == "d2":
                core_ok = False
        print(f"  [{mark}] {name:14s} {role}")
    try:
        import PIL  # noqa: F401
        print("  [OK  ] Pillow         PNG dpi stamp + resolution audit")
    except ImportError:
        print("  [MISS] Pillow         pip install Pillow")
        core_ok = False
    try:
        import scienceplots  # noqa: F401
        print("  [OK  ] SciencePlots   journal-grade data-plot geometry")
    except ImportError:
        print("  [opt ] SciencePlots   pip install SciencePlots (optional)")
    try:
        import matplotlib  # noqa: F401
        print("  [OK  ] matplotlib     data-plot pipeline")
    except ImportError:
        core_ok = False
        print("  [MISS] matplotlib     pip install matplotlib (REQUIRED)")
    print(f"\n  verdict: {'READY — all core engines available' if core_ok else 'DEGRADED — install missing tools (see INSTALL.md)'}")
    return 0 if core_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="SciForge unified figure renderer")
    ap.add_argument("source", nargs="?", help="spec.d2 / spec.dot / spec.tex / "
                    "source.svg / spec.asy / spec.typ / render.py / *.blender.py")
    ap.add_argument("--doctor", action="store_true",
                    help="check the figure toolchain environment and exit")
    ap.add_argument("--out", default=None, help="output dir (default: beside source)")
    ap.add_argument("--name", default="output", help="output basename (no ext)")
    ap.add_argument("--engine",
                    choices=["d2", "graphviz", "tikz", "svg", "asy",
                             "typst", "blender", "python", "auto"],
                    default="auto")
    ap.add_argument("--layout", default=None,
                    help="d2: dagre|elk|tala  /  graphviz: dot|neato|fdp|...")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--pad", type=int, default=60)
    ap.add_argument("--no-preamble", action="store_true",
                    help="skip morandi preamble injection (d2)")
    ap.add_argument("--caption", default=None)
    ap.add_argument("--label", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 4 if the embedded audit verdict is FAIL")
    args = ap.parse_args()
    if args.doctor:
        return doctor()
    if not args.source:
        ap.error("source is required (or use --doctor)")

    src = Path(args.source).resolve()
    if not src.is_file():
        print(f"ERROR: source not found: {src}", file=sys.stderr)
        return 3
    outdir = Path(args.out) if args.out else src.parent
    outdir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix.lower()
    engine = args.engine
    if engine == "auto":
        engine = {".d2": "d2", ".dot": "graphviz", ".gv": "graphviz",
                  ".tex": "tikz", ".svg": "svg",
                  ".asy": "asy", ".typ": "typst", ".py": "python",
                  ".blender.py": "blender"}.get(ext)
        if src.name.endswith(".blender.py"):
            engine = "blender"
        if engine is None:
            print(f"ERROR: unknown source extension {ext} (supported: .d2 "
                  f".dot .tex .svg .asy .typ .py render scripts, "
                  f"*.blender.py)", file=sys.stderr)
            return 3

    out_pdf = outdir / f"{args.name}.pdf"
    out_png = outdir / f"{args.name}.png"
    keep_svg = outdir / "intermediate.svg" if engine in ("d2", "graphviz", "svg") else None
    log: list[str] = [f"# SciForge render_figure — engine={engine} src={src.name}"]
    try:
        if engine == "d2":
            layout = args.layout or ("elk" if _dense(src) else "dagre")
            inject = not args.no_preamble
            if inject and _too_many_elements(src):
                inject = False
                log.append("# dense spec: preamble skipped (layout-time guard; "
                           "palette compliance guaranteed by sanitize_palette)")
            render_d2(src, out_pdf, out_png, layout, args.pad, args.dpi,
                      inject, log, keep_svg)
        elif engine == "graphviz":
            render_graphviz(src, out_pdf, out_png, args.layout or "dot",
                            args.dpi, log, keep_svg)
        elif engine == "python":
            outdir.mkdir(parents=True, exist_ok=True)
            render_python(src, outdir, args.dpi, log)
        elif engine == "tikz":
            render_tikz(src, out_pdf, out_png, args.dpi, log)
        elif engine == "asy":
            render_asymptote(src, out_pdf, out_png, args.dpi, log)
        elif engine == "typst":
            render_typst(src, out_pdf, out_png, args.dpi, log)
        elif engine == "blender":
            render_blender(src, out_pdf, out_png, args.dpi, log)
        else:
            render_svg(src, out_pdf, out_png, args.dpi, log, keep_svg)
    except PaletteError as e:
        print("PALETTE AUDIT FAIL", file=sys.stderr)
        for v in e.violations:
            print("  " + v, file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"RENDER FAIL: {e}", file=sys.stderr)
        (outdir / "render.log").write_text("\n".join(log), encoding="utf-8")
        return 3

    # reproducibility: keep the source inside the figure dir
    kept = outdir / src.name
    if kept.resolve() != src.resolve():
        shutil.copyfile(src, kept)
    write_latex_include(outdir, args.name, args.caption,
                        args.label or outdir.name)
    (outdir / "render.log").write_text("\n".join(log), encoding="utf-8")
    for f in (out_pdf, out_png):
        if not f.is_file() or f.stat().st_size == 0:
            print(f"RENDER FAIL: missing/empty {f}", file=sys.stderr)
            return 3

    # embedded audit (single-entry pipeline: audit runs inside this tool)
    rep = figure_audit.audit_figure(outdir)
    report = rep.to_json()
    (outdir / "figure_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    verdict = report["verdict"]
    print(f"OK {out_pdf} ({out_pdf.stat().st_size} B) + "
          f"{out_png} ({out_png.stat().st_size} B)  [audit: {verdict}]")
    for c in report["checks"]:
        if c["status"] != "PASS":
            print(f"   {c['status']:4s} {c['layer']} {c['msg']}")
    if args.strict and verdict == "FAIL":
        return 4
    return 0


def _dense(src: Path) -> bool:
    """Heuristic: >20 top-level node definitions -> use elk."""
    try:
        text = src.read_text(encoding="utf-8")
        ids = set(re.findall(r"^([A-Za-z_][\w.-]*)\s*[:{]", text, re.M))
        ids |= set(re.findall(r"^([A-Za-z_][\w.-]*)\s*->", text, re.M))
        return len(ids) > 20
    except OSError:
        return False


def _too_many_elements(src: Path) -> bool:
    """Dense-spec detection for the preamble decision.

    The injected `*.style` glob forces d2 to style every element
    individually; on dense graphs (>14 nodes or >18 edges) layout time
    explodes from <1s to ~90s.  For such specs we skip the preamble and
    rely on (a) author explicit styles and (b) sanitize_palette() remapping
    any engine-injected colors, so delivery stays palette-compliant.
    """
    try:
        text = src.read_text(encoding="utf-8")
        nodes = set(re.findall(r"^([A-Za-z_][\w.-]*)\s*[:{]", text, re.M))
        edges = re.findall(r"^\s*([\w.\[\]]+)\s*->", text, re.M)
        return len(nodes) > 14 or len(edges) > 18
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
