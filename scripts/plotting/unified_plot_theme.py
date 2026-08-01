#!/usr/bin/env python3
"""SciForge-OSS unified plotting enforcement — Phase 6.

Single source of truth for academic figure style:
  - Data figures  : matplotlib/seaborn with Nature/Science academic theme
                    (DPI=300, Arial font, restrained colorblind-safe palette)
  - Diagrams      : d2 / graphviz declarative rendering -> vector SVG/PDF

Exposes:
  apply_academic_theme()   — configure matplotlib rcParams (call before plotting)
  nature_palette()         — restrained academic categorical colors
  save_figure(fig, path)   — enforce DPI=300 + vector-first (PDF/SVG) + PNG fallback
  render_d2(spec, out)     — run `d2 --layout=elk` -> SVG (declarative diagrams)
  render_dot(spec, out)    — run `dot -Tsvg` (graphviz fallback)

CLI:
    python3 scripts/plotting/unified_plot_theme.py sample   # render a demo data figure
    python3 scripts/plotting/unified_plot_theme.py diagram  # render a demo d2 diagram
"""
import argparse
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------------------------------- #
# academic style constants
# --------------------------------------------------------------------------- #
DPI = 300
FONT = "Arial"                       # Nature/Science standard; falls back if absent
PALETTE = [                          # restrained, colorblind-safe academic colors
    "#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE",
    "#AA3377", "#BBBBBB", "#332288",
]
SIZE_FLOOR = {                       # Nature readability floor (from figure-quality-contract)
    "title": 13, "axis_label": 12, "tick": 10, "legend": 10, "annotation": 9,
    "line": 1.5,
}
_FALLBACK_FONTS = ["DejaVu Sans", "Liberation Sans", "Helvetica", "sans-serif"]


def _available_fonts() -> set:
    from matplotlib import font_manager
    return {f.name for f in font_manager.fontManager.ttflist}


def _resolve_font(preferred: str = FONT) -> str:
    """Return `preferred` if installed, else the first available fallback."""
    avail = _available_fonts()
    if preferred in avail:
        return preferred
    for cand in _FALLBACK_FONTS:
        if cand in avail:
            return cand
    return "sans-serif"


def apply_academic_theme(dpi: int = DPI, font: str | None = None) -> str:
    """Configure matplotlib rcParams to the house academic theme.

    Returns the font actually resolved (Arial when present, else a fallback),
    so callers can log whether the Nature-standard font was honored.
    """
    resolved = _resolve_font(font or FONT)
    plt.rcParams.update({
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
        "font.family": resolved,
        "font.size": SIZE_FLOOR["axis_label"],
        "axes.titlesize": SIZE_FLOOR["title"],
        "axes.labelsize": SIZE_FLOOR["axis_label"],
        "xtick.labelsize": SIZE_FLOOR["tick"],
        "ytick.labelsize": SIZE_FLOOR["tick"],
        "legend.fontsize": SIZE_FLOOR["legend"],
        "axes.linewidth": 0.8,
        "lines.linewidth": SIZE_FLOOR["line"],
        "figure.figsize": (8, 4.5),   # 16:9 Nature wide
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    return resolved


def nature_palette() -> list[str]:
    return list(PALETTE)


def save_figure(fig, path: str, formats=("pdf", "png")) -> None:
    """Save figure enforcing DPI=300 and vector-first (pdf/svg) + png view copy."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    for fmt in formats:
        out = f"{os.path.splitext(path)[0]}.{fmt}"
        fig.savefig(out, dpi=DPI, bbox_inches="tight", transparent=False)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# declarative diagram renderers
# --------------------------------------------------------------------------- #
def render_d2(spec_path: str, out_svg: str, layout: str = "elk") -> bool:
    """Render a .d2 spec -> SVG via d2 (headless-native, auto-layout)."""
    os.makedirs(os.path.dirname(os.path.abspath(out_svg)) or ".", exist_ok=True)
    r = subprocess.run(["d2", f"--layout={layout}", spec_path, out_svg],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"[unified-plotting] d2 failed: {r.stderr[:300]}\n")
        return False
    return os.path.exists(out_svg)


def render_dot(spec_path: str, out_svg: str) -> bool:
    """Render a graphviz dot spec -> SVG (fallback for d2-unavailable cases)."""
    os.makedirs(os.path.dirname(os.path.abspath(out_svg)) or ".", exist_ok=True)
    with open(out_svg, "w") as f:
        r = subprocess.run(["dot", "-Tsvg", spec_path], stdout=f, stderr=subprocess.PIPE)
    if r.returncode != 0:
        sys.stderr.write(f"[unified-plotting] dot failed: {r.stderr[:300]}\n")
        return False
    return os.path.exists(out_svg)


# --------------------------------------------------------------------------- #
# demos (used for verification)
# --------------------------------------------------------------------------- #
def _sample_data_figure(out_dir: str) -> str:
    apply_academic_theme()
    fig, ax = plt.subplots()
    x = np.linspace(0, 2 * np.pi, 200)
    for i, c in enumerate(PALETTE[:3]):
        ax.plot(x, np.sin(x + i), color=c, label=f"series {i+1}")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude (a.u.)")
    ax.legend(frameon=False)
    out = os.path.join(out_dir, "sample_figure")
    save_figure(fig, out)
    return out


def _sample_diagram(out_dir: str) -> str:
    spec = os.path.join(out_dir, "sample_pipeline.d2")
    with open(spec, "w") as f:
        f.write("title: SciForge sample pipeline\n"
                "idea -> verify -> claim -> paper\n")
    out_svg = os.path.join(out_dir, "sample_pipeline.svg")
    ok = render_d2(spec, out_svg)
    return out_svg if ok else "RENDER_FAILED"


def main(argv: list[str]) -> int:
    out_dir = os.path.join(os.getcwd(), "artifacts", "plotting_demo")
    os.makedirs(out_dir, exist_ok=True)
    if len(argv) >= 2 and argv[1] == "diagram":
        print(_sample_diagram(out_dir))
        return 0
    print(_sample_data_figure(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
