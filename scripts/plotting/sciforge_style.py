"""SciForge-OSS unified figure design system (single source of truth).

This module is the ONLY authoritative definition of the SciForge morandi
design tokens.  The skill documents (color-themes.md, unified-plotting
SKILL.md, figure-quality-contract.md) reference this file; any hex value
written in prose is illustrative — the numbers here govern rendering and
auditing.

Design system (v2.0, numerically validated):
- Layer 1 (categorical / semantic): morandi tones, every color C* <= 25
  (CIELAB chroma) and ink-on-fill WCAG-AA contrast >= 4.5.
- Layer 2 (continuous scalar fields): viridis / magma / plasma ONLY —
  never morandi, never jet/rainbow/hsv.
- Typography: TeX Gyre family (Termes=Times, Pagella=Palatino,
  Heros=Helvetica clones) so figures match LaTeX body text.
- Nature readability floor: axis >= 12pt, ticks/legend >= 10pt,
  title >= 13pt, annotations >= 9pt, primary linewidth >= 1.5pt.

No third-party dependency is required for the color math (pure sRGB→Lab).
matplotlib is imported lazily so this module also works in headless
render paths that only need the tokens.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

__version__ = "2.0.0"

# --------------------------------------------------------------------------
# Layer 1 — morandi design tokens (all C* <= 25, validated)
# --------------------------------------------------------------------------
TOKENS: dict[str, str] = {
    # ink & grounds (text, axes, backgrounds)
    "ink": "#3A3733",          # primary text / axes / arrows
    "ink-soft": "#6E675F",     # secondary text, strokes, gridlines
    "canvas": "#FAF8F5",       # figure background
    "surface": "#EDE9E2",      # default node fill / panel background
    "surface-alt": "#E3DDD3",  # alternating container fill
    # categorical series (ordered by visual priority)
    "blue": "#93A7BB",         # 1st series / hero method
    "sage": "#A4B294",         # 2nd series / positive improvement
    "mauve": "#BDA5A7",        # 3rd series
    "ochre": "#C4A880",        # accent / highlight (max C* in palette)
    "taupe": "#B0A292",        # 4th series / baseline
    "rose": "#D9BCBC",         # soft accent / annotations fill
    "slate": "#97A2B2",        # ablation-2
    "moss": "#A5AB91",         # ablation-1
    "clay": "#C2A193",         # negative / degradation
}

# Semantic roles consumed by paper figures (old role names preserved so
# existing specs keep working — each maps onto a validated token).
SEMANTIC: dict[str, str] = {
    "hero": TOKENS["blue"],        # proposed method
    "baseline": TOKENS["taupe"],   # comparison method
    "positive": TOKENS["sage"],    # improvement
    "negative": TOKENS["clay"],    # degradation
    "neutral": TOKENS["surface"],  # background / reference
    "ablation-1": TOKENS["moss"],
    "ablation-2": TOKENS["slate"],
    "accent": TOKENS["ochre"],
    # slot-style aliases used by older unified-plotting specs
    "warm-grey": TOKENS["surface"],
    "dusty-blue": TOKENS["blue"],
    "dusty-rose": TOKENS["rose"],
    "charcoal": TOKENS["ink"],
    "muted-ochre": TOKENS["ochre"],
}

SERIES_ORDER: list[str] = [
    "blue", "sage", "mauve", "ochre", "taupe", "rose", "slate", "moss", "clay",
]
SERIES_HEX: list[str] = [TOKENS[n] for n in SERIES_ORDER]

# Layer 2 — continuous-field colormaps (matplotlib names)
LAYER2_COLORMAPS = ("viridis", "magma", "plasma")
FORBIDDEN_COLORMAPS = ("jet", "rainbow", "hsv", "gist_rainbow", "coolwarm", "bwr")

# --------------------------------------------------------------------------
# Typography (Nature floor)
# --------------------------------------------------------------------------
FONT_FAMILY = "TeX Gyre Termes"          # serif — matches LaTeX \rmdefault
FONT_FAMILY_SANS = "TeX Gyre Heros"      # optional sans
FONT_STACK_SERIF = ["TeX Gyre Termes", "Liberation Serif", "DejaVu Serif"]
FONT_STACK_SANS = ["TeX Gyre Heros", "Liberation Sans", "DejaVu Sans"]

NATURE_FLOOR = {
    "axis_label": 12.0,
    "tick_label": 10.0,
    "legend": 10.0,
    "title": 13.0,
    "annotation": 9.0,
    "diagram_node": 10.0,   # physical pt equivalent for d2/graphviz text
    "diagram_edge": 9.0,
}
LINEWIDTH = {"primary": 1.5, "secondary": 0.8, "diagram_stroke": 1.5}
MARKER_SIZE_MIN = 6.0

# d2 font sizes are SVG px; at the default ~1000px render width embedded at
# 8in, 1px ≈ 0.58pt.  22px ≈ 12.7pt node labels — clears the Nature floor.
D2_FONT_PX = {"node": 22, "edge": 18, "title": 28, "container": 20}

# d2 accepts fonts ONLY as .ttf file paths via --font-* CLI flags (it
# validates `style.font` names against a tiny builtin list and rejects
# everything else).  Liberation Sans = metric-compatible Helvetica clone,
# matching the sans choice for diagrams.  Fonts are LOCATED dynamically
# per platform (fontconfig first, then per-OS directory scan) — no
# machine-specific absolute paths are assumed; when nothing is found d2
# falls back to its embedded Source Sans Pro.
D2_FONT_ROLES = {
    "regular": ("Liberation Sans", "LiberationSans-Regular.ttf"),
    "bold": ("Liberation Sans:style=Bold", "LiberationSans-Bold.ttf"),
    "italic": ("Liberation Sans:style=Italic", "LiberationSans-Italic.ttf"),
}


def fc_match_file(family_query: str) -> str | None:
    """Resolve a font family to a file via fontconfig (Linux/macOS/WSL)."""
    import shutil as _shutil
    import subprocess
    fc = _shutil.which("fc-match")
    if not fc:
        return None
    try:
        r = subprocess.run([fc, "-f", "%{file}", family_query],
                           capture_output=True, text=True, timeout=10)
        p = r.stdout.strip()
        if r.returncode == 0 and p and os.path.isfile(p):
            return p
    except Exception:
        pass
    return None


def _font_scan_dirs() -> list[str]:
    """Common font directories per platform (user-home-relative first, so
    multi-user machines work without root-owned paths)."""
    import platform as _platform
    home = Path.home()
    sysname = _platform.system()
    if sysname == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA",
                               str(home / "AppData" / "Local"))
        return [
            str(home / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"),
            str(home / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Fonts"),
            os.path.join(local, "Microsoft", "Windows", "Fonts"),
            os.path.join(windir, "Fonts"),
        ]
    if sysname == "Darwin":
        return [
            str(home / "Library" / "Fonts"),
            "/Library/Fonts",
            "/System/Library/Fonts",
            "/Library/TeX/texmf/fonts",
        ]
    return [  # Linux / other POSIX
        str(home / ".local" / "share" / "fonts"),
        str(home / ".fonts"),
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/usr/share/texmf/fonts",
        "/usr/share/texlive/texmf-dist/fonts",
    ]


def locate_font(family_query: str, filename: str) -> str | None:
    """Cross-platform font lookup: fontconfig -> recursive dir scan."""
    import glob as _glob
    p = fc_match_file(family_query)
    if p and p.lower().endswith(".ttf"):
        return p
    for d in _font_scan_dirs():
        hits = _glob.glob(os.path.join(d, "**", filename), recursive=True)
        if hits:
            return hits[0]
    return None


def d2_font_flags() -> list[str]:
    """CLI font flags for d2 (cross-platform).  Silently omitted when the
    fonts are absent — d2 then uses its embedded Source Sans Pro.  If the
    regular face resolves, missing bold/italic reuse the regular file so
    the family stays consistent."""
    regular = None
    resolved = {}
    for role, (family, pattern) in D2_FONT_ROLES.items():
        p = locate_font(family, pattern)
        if p:
            resolved[role] = p
            if role == "regular":
                regular = p
    if not regular:
        return []  # all-or-nothing: never mix Liberation with d2 builtins
    flags: list[str] = []
    for role in ("regular", "bold", "italic"):
        flags += [f"--font-{role}", resolved.get(role, regular)]
    return flags


# --------------------------------------------------------------------------
# Color math (pure python sRGB -> CIELAB)
# --------------------------------------------------------------------------
def hex2rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _srgb2lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb2lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_srgb2lin(c) for c in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def chroma(hexcolor: str) -> float:
    """CIELAB chroma C* (morandi contract: <= 25)."""
    _, a, b = rgb2lab(hex2rgb(hexcolor))
    return math.hypot(a, b)


def luminance(hexcolor: str) -> float:
    r, g, b = (_srgb2lin(c) for c in hex2rgb(hexcolor))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(hex1: str, hex2: str) -> float:
    """WCAG relative-luminance contrast ratio."""
    l1, l2 = luminance(hex1), luminance(hex2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def sanitize_palette(svg_text: str) -> tuple[str, int]:
    """Deterministically remap every off-palette hex color in an SVG to the
    nearest morandi token by CIELAB L* (preserving light/dark ordering).

    Engine-injected theme colors (d2's default blues, graphviz defaults)
    are remapped here so the DELIVERED figure is always palette-compliant,
    regardless of tool version drift.  Author spec colors never reach this
    function off-palette — render_figure.py rejects them at source level.
    Returns (sanitized_text, n_replacements).
    """
    import re as _re
    targets = sorted(set(_re.findall(r"#[0-9a-fA-F]{6}", svg_text)))
    remap: dict[str, str] = {}
    for h in targets:
        c = chroma(h)
        L = rgb2lab(hex2rgb(h))[0]
        if c < 2.0 or L > 96 or L < 12:
            continue  # neutrals / near-white / near-black stay untouched
        if is_morandi(h):
            continue
        best = min(TOKENS.values(), key=lambda t: abs(rgb2lab(hex2rgb(t))[0] - L))
        remap[h.lower()] = best
    if not remap:
        return svg_text, 0
    n = 0

    def _sub(m):
        nonlocal n
        h = m.group(0).lower()
        if h in remap:
            n += 1
            return remap[h]
        return m.group(0)

    return _re.sub(r"#[0-9a-fA-F]{6}", _sub, svg_text), n


# --------------------------------------------------------------------------
# Runtime icon vocabulary (contract §5.5): recolor third-party icons
# --------------------------------------------------------------------------
def recolor_icon(svg_text: str, mapping: dict | None = None) -> tuple[str, int]:
    """Recolor an arbitrary icon SVG onto the morandi palette.

    Protocol (figure-complexity-contract §5.5): agents may fetch CC0/MIT
    icons at runtime (bioicons.com, Tabler, Lucide, Feather, ...) but the
    icons MUST pass through this function before use, so every delivered
    figure stays palette-compliant without shipping an asset library in
    the repo.  Mapping rule:
      - near-white / near-black / neutral (C*<2, L*>96 or <12): keep
      - saturated colors: sorted by CIELAB L*, mapped to SERIES_HEX in
        lightness order (lightest first), duplicates merge onto the
        nearest series slot by L* distance
      - `mapping` overrides individual source hexes if given.
    Returns (recolor_svg, n_substitutions).
    """
    import re as _re
    found = sorted(set(_re.findall(r"#[0-9a-fA-F]{6}", svg_text)))
    if mapping is None:
        mapping = {}
    remap: dict[str, str] = {}
    candidates = []
    for h in found:
        if h.lower() in {k.lower() for k in mapping}:
            continue
        c = chroma(h)
        L = rgb2lab(hex2rgb(h))[0]
        if c < 2.0 or L > 96 or L < 12:
            continue  # neutrals stay untouched
        candidates.append((L, h))
    candidates.sort()
    for i, (L, h) in enumerate(candidates):
        slot = SERIES_HEX[min(i, len(SERIES_HEX) - 1)]
        # nearest-by-lightness refinement within the series
        best = min(SERIES_HEX,
                   key=lambda t: abs(rgb2lab(hex2rgb(t))[0] - L))
        remap[h.lower()] = best
    for k, v in mapping.items():
        remap[k.lower()] = v
    if not remap:
        return svg_text, 0
    n = 0

    def _sub(m):
        nonlocal n
        h = m.group(0).lower()
        if h in remap:
            n += 1
            return remap[h]
        return m.group(0)

    return _re.sub(r"#[0-9a-fA-F]{6}", _sub, svg_text), n


def mix(hex1: str, hex2: str, t: float) -> str:
    """Linear RGB mix of hex1 toward hex2 (t=1 fully hex2)."""
    out = []
    for c1, c2 in zip(hex2rgb(hex1), hex2rgb(hex2)):
        out.append(round(c1 + (c2 - c1) * t))
    return "#%02X%02X%02X" % tuple(out)


def stroke_for(fill: str) -> str:
    """Canonical border color for a fill: 45% mix toward ink.

    Auditors accept a stroke if it equals this mix (±channel tolerance) or
    is itself a palette token.
    """
    return mix(fill, TOKENS["ink"], 0.45)


def _rgb_dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def is_morandi(hexcolor: str, tol: float = 8.0) -> bool:
    """True if hexcolor is a palette token OR the canonical stroke mix of
    one (within Euclidean sRGB tolerance `tol` per channel)."""
    try:
        rgb = hex2rgb(hexcolor)
    except (ValueError, IndexError):
        return False
    pool = list(TOKENS.values()) + list(SEMANTIC.values())
    pool += [stroke_for(t) for t in TOKENS.values()]
    pool += [TOKENS["canvas"], "#FFFFFF", "#ffffff", "none"]
    for p in pool:
        if p == "none":
            continue
        if _rgb_dist(rgb, hex2rgb(p)) <= tol:
            return True
    return False


# --------------------------------------------------------------------------
# matplotlib theme (Layer 1 enforcement for data plots)
# --------------------------------------------------------------------------
def apply_matplotlib_style(style: str = "academic") -> None:
    """Configure matplotlib rcParams to the SciForge academic style.

    Call once at the top of every render.py:
        from scripts.plotting.sciforge_style import apply_matplotlib_style
        apply_matplotlib_style()

    If the SciencePlots package is installed, the journal-grade
    `science` base style is loaded FIRST, then SciForge tokens override
    fonts/colors/sizes on top (house style wins; science style supplies
    tick/grid/figure geometry conventions).
    """
    import matplotlib as mpl
    from matplotlib import font_manager as fm

    try:
        import scienceplots  # noqa: F401  (registers 'science' styles)
        mpl.style.use(["science", "no-latex"])
    except Exception:
        pass  # SciencePlots optional — house style alone is complete

    # register TeX Gyre OTFs if present (cross-platform discovery)
    for tg in ("texgyretermes-regular.otf", "texgyretermes-bold.otf",
               "texgyretermes-italic.otf", "texgyreheros-regular.otf"):
        path = locate_font("TeX Gyre Termes", tg)
        if path:
            try:
                fm.fontManager.addfont(path)
            except Exception:
                pass

    stack = FONT_STACK_SERIF if style != "sans" else FONT_STACK_SANS
    rc = {
        "font.family": "serif",
        "font.serif": stack,
        "mathtext.fontset": "stix",
        "axes.prop_cycle": "cycler('color', %r)" % SERIES_HEX,
        "figure.facecolor": TOKENS["canvas"],
        "axes.facecolor": TOKENS["canvas"],
        "axes.edgecolor": TOKENS["ink"],
        "axes.labelcolor": TOKENS["ink"],
        "axes.labelsize": NATURE_FLOOR["axis_label"],
        "axes.titlesize": NATURE_FLOOR["title"],
        "axes.titleweight": "bold",
        "axes.linewidth": 1.0,
        "axes.grid": False,
        "xtick.color": TOKENS["ink"],
        "ytick.color": TOKENS["ink"],
        "xtick.labelsize": NATURE_FLOOR["tick_label"],
        "ytick.labelsize": NATURE_FLOOR["tick_label"],
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.fontsize": NATURE_FLOOR["legend"],
        "legend.frameon": False,
        "lines.linewidth": LINEWIDTH["primary"],
        "lines.markersize": MARKER_SIZE_MIN,
        "patch.edgecolor": TOKENS["ink-soft"],
        "grid.color": TOKENS["surface-alt"],
        "grid.linewidth": 0.6,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.08,
        "pdf.fonttype": 42,   # TrueType embedding — editable in Illustrator
        "ps.fonttype": 42,
    }
    if style == "monochrome":
        rc["axes.prop_cycle"] = "cycler('color', %r)" % [
            "#3A3733", "#6E675F", "#A9A29A", "#C9C3BB"]
    mpl.rcParams.update(rc)


# --------------------------------------------------------------------------
# d2 morandi preamble (injected by render_figure.py)
# --------------------------------------------------------------------------
def d2_preamble(direction: str | None = None) -> str:
    """Canonical d2 header enforcing the morandi look & Nature typography.

    Uses d2 glob selectors (`*` for shapes, `* -> *` for edges) so every
    element inherits the design system even when the spec omits styles.
    """
    lines = [
        "# ---- SciForge-OSS morandi preamble (auto-injected; do not edit) ----",
    ]
    if direction:
        lines.append(f"direction: {direction}")
    lines += [
        "*.style: {",
        f"  fill: \"{TOKENS['surface']}\"",
        f"  stroke: \"{TOKENS['ink-soft']}\"",
        "  stroke-width: 2",
        f"  font-color: \"{TOKENS['ink']}\"",
        f"  font-size: {D2_FONT_PX['node']}",
        "  border-radius: 6",
        "  bold: false",
        "}",
        "(* -> *).style: {",
        f"  stroke: \"{TOKENS['ink']}\"",
        "  stroke-width: 2",
        f"  font-color: \"{TOKENS['ink']}\"",
        f"  font-size: {D2_FONT_PX['edge']}",
        "}",
        "# ---- end preamble; author spec follows ----",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    # self-check: validate every token against the contract
    bad = []
    for name, h in TOKENS.items():
        c = chroma(h)
        if name not in ("ink", "ink-soft", "canvas") and c > 25:
            bad.append(f"{name} {h} C*={c:.1f} > 25")
        if name not in ("ink", "ink-soft", "canvas", "surface", "surface-alt"):
            ct = contrast(TOKENS["ink"], h)
            if ct < 4.5:
                bad.append(f"{name} {h} contrast={ct:.2f} < 4.5")
    if bad:
        print("PALETTE CONTRACT FAILURES:")
        print("\n".join(bad))
        raise SystemExit(1)
    print(f"sciforge_style v{__version__}: {len(TOKENS)} tokens OK "
          "(C*<=25, ink contrast>=4.5)")
    print("d2 preamble preview:")
    print(d2_preamble("right")[:400])
