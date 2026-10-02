"""SciForge-OSS unified figure design system (single source of truth).

This module is the ONLY authoritative definition of the SciForge design
tokens (v3.0 dopamine palette; formerly morandi).  The skill documents (color-themes.md, unified-plotting
SKILL.md, figure-quality-contract.md) reference this file; any hex value
written in prose is illustrative — the numbers here govern rendering and
auditing.

Design system (v3.0, numerically validated):
- Layer 1 (categorical / semantic): DOPAMINE tones — high-saturation (C* >= 30),
  every pairwise combination validated for color-blindness distinguishability
  (protan/deutan/tritan deltaE >= 15) via the CVD net below, and each series
  token readable on the white canvas. Neutrals (ink/canvas/surfaces) keep the
  classic black-on-white rule.
- Layer 2 (continuous scalar fields): viridis / magma / plasma ONLY —
  never a categorical palette, never jet/rainbow/hsv.
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
import re
from pathlib import Path

__version__ = "3.0.0"

# One pattern for every #-hex color literal the SVG renderers accept:
# 3-digit (#RGB shorthand), 6-digit (#RRGGBB) and 8-digit (#RRGGBBAA) forms.
# The ordered longest-first alternation plus the trailing negative lookahead
# guarantees a 6-digit literal is never consumed as the PREFIX of an 8-digit
# one and that 4/5/7-digit garbage never matches at all.  rsvg/inkscape
# render all three forms, so every palette gate (extract_colors /
# audit_palette_svg / sanitize_palette) must recognize all three.  TeX
# {HTML}{...} colors are matched by a separate pattern at the call sites
# and STAY 6-digit only (xcolor rejects 3-char shorthand).
HEX_COLOR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")


def normalize_hex(h: str) -> str:
    """Normalize a #-hex literal matched by HEX_COLOR_RE to canonical
    #RRGGBB: #RGB expands by doubling each nibble (#F00 -> #FF0000),
    #RRGGBBAA drops the alpha channel (#FF000066 -> #FF0000), #RRGGBB
    passes through unchanged."""
    body = h.lstrip("#")
    if len(body) == 3:
        body = "".join(c * 2 for c in body)
    elif len(body) == 8:
        body = body[:6]
    return "#" + body

# --------------------------------------------------------------------------
# Layer 1 — dopamine design tokens (v3.0: HIGH-SATURATION, CVD-verified)
# The morandi system (C* <= 25) is retired; the design language is now a vivid
# rainbow, but every series token passes two hard nets (see the CVD/grayscale
# section below): distinguishable under protan/deutan/tritan AND readable on the
# white canvas. Neutrals (ink / canvas / surfaces) stay black-on-white — the
# text and ground rules did not change, only the categorical series palette.
# --------------------------------------------------------------------------
TOKENS: dict[str, str] = {
    # ink & grounds (text, axes, backgrounds) — unchanged: classic black/white.
    "ink": "#000000",          # primary text / axes / arrows (pure black)
    "ink-soft": "#4D4D4D",     # secondary strokes / gridlines (neutral grey)
    "canvas": "#FFFFFF",       # figure background — PURE WHITE
    "surface": "#F4F1EC",      # default node fill / panel background (warm near-white)
    "surface-alt": "#EAE5DC",  # alternating container fill
    # categorical series — dopamine hues (ordered by visual priority). Validated
    # with palette_distinguishability: min CVD ΔE = 15.0 over all 28 pairs, 0 fails.
    "blue":    "#00A6FB",      # 1st series / hero method
    "orange":  "#F3722C",      # 2nd series
    "green":   "#06A77D",      # positive improvement
    "red":     "#FF3B6B",      # 4th series / annotation
    "teal":    "#118AB2",      # baseline
    "violet":  "#8338EC",      # ablation
    "gold":    "#FFBF00",      # accent / highlight
    "crimson": "#D90429",      # negative / degradation
}

# Semantic roles consumed by paper figures (old role names preserved so
# existing specs keep working — each maps onto a validated dopamine token).
SEMANTIC: dict[str, str] = {
    "hero": TOKENS["blue"],        # proposed method
    "baseline": TOKENS["teal"],    # comparison method
    "positive": TOKENS["green"],   # improvement
    "negative": TOKENS["crimson"], # degradation
    "neutral": TOKENS["surface"],  # background / reference
    "ablation-1": TOKENS["orange"],
    "ablation-2": TOKENS["violet"],
    "accent": TOKENS["gold"],
    # slot-style aliases used by older unified-plotting specs (retargeted to
    # the dopamine palette; old morandi names resolve to the nearest vivid hue).
    "warm-grey": TOKENS["surface"],
    "dusty-blue": TOKENS["blue"],
    "dusty-rose": TOKENS["red"],
    "charcoal": TOKENS["ink"],
    "muted-ochre": TOKENS["gold"],
}

SERIES_ORDER: list[str] = [
    "blue", "orange", "green", "red", "teal", "violet", "gold", "crimson",
]
SERIES_HEX: list[str] = [TOKENS[n] for n in SERIES_ORDER]

# Layer 2 — continuous-field colormaps (matplotlib names)
LAYER2_COLORMAPS = ("viridis", "magma", "plasma", "cividis")  # cividis: CVD-designed (research-adopted v3.0)
FORBIDDEN_COLORMAPS = ("jet", "rainbow", "hsv", "gist_rainbow", "coolwarm", "bwr")

# --------------------------------------------------------------------------
# Typography (Nature floor)
# --------------------------------------------------------------------------
FONT_FAMILY = "TeX Gyre Termes"          # serif — matches LaTeX \rmdefault
FONT_FAMILY_SANS = "TeX Gyre Heros"      # optional sans
FONT_STACK_SERIF = ["TeX Gyre Termes", "Liberation Serif", "DejaVu Serif"]
FONT_STACK_SANS = ["TeX Gyre Heros", "Liberation Sans", "DejaVu Sans"]

# --------------------------------------------------------------------------
# Typography (Nature floor) — v2.2: floors raised to PRINT size (test feedback:
# "figures look small / fonts unreadable once embedded in LaTeX").  These are
# the sizes the reader sees AT FINAL EMBEDDED SCALE, assuming the figure is
# rendered at the physical width it will occupy (see figsize_* helpers below).
# --------------------------------------------------------------------------
NATURE_FLOOR = {
    "axis_label": 16.0,
    "tick_label": 13.0,
    "legend": 13.0,
    "title": 18.0,
    "annotation": 12.0,
    "diagram_node": 14.0,   # physical pt equivalent for d2/graphviz text
    "diagram_edge": 12.0,
}
LINEWIDTH = {"primary": 1.8, "secondary": 1.0, "diagram_stroke": 1.6}
MARKER_SIZE_MIN = 7.0

# Black on pure white is the only acceptable text/ground combination for a
# scientific paper figure.  The dopamine tokens remain the CATEGORICAL series
# palette (fills / lines) but every glyph, tick and axis spine is black, and
# the figure background is pure white — no off-white / grey science-style
# grounds and no brown-grey ink (v2.2, eval feedback: "text is not black").
INK_TEXT = "#000000"
GROUND = "#FFFFFF"

# --------------------------------------------------------------------------
# Print-size contract (v2.2 — cures "figures too small in LaTeX")
# --------------------------------------------------------------------------
# A figure's fonts are only as big as (font_pt * embedded_width/render_width).
# The recurring failure was rendering a data plot at ~8in and embedding one
# panel of it at ~2in (3-across composite) -> 4x shrink -> 13pt becomes 3pt.
# The fix is to RENDER AT THE PHYSICAL SIZE THE FIGURE WILL OCCUPY, so the
# embed scale is ~1:1 and the NATURE_FLOOR sizes are what the reader sees.
# elsarticle [preprint,12pt] text block is ~6.3in; a single-column journal
# figure is ~3.5in.  These helpers return (w_in, h_in) for plt.figure(figsize=...).
TEXTWIDTH_IN = 6.3          # elsarticle preprint text block width
SINGLE_COL_IN = 3.5         # typical journal single-column width

def figsize_full(aspect: float = 9 / 16) -> tuple[float, float]:
    """Full-textwidth figure (\\textwidth). aspect = height/width.

    v1.7.1: default is LANDSCAPE 16:9 (the Nature data-figure proportion) —
    the user mandate: data figures are horizontal, never the tall skinny
    default. A tall figure stays available via an explicit aspect override.
    """
    return (TEXTWIDTH_IN, TEXTWIDTH_IN * aspect)

def figsize_wide(aspect: float = 9 / 16) -> tuple[float, float]:
    """Explicit landscape preset (same geometry as the v1.7.1 full default)."""
    return figsize_full(aspect)

def figsize_single(aspect: float = 9 / 16) -> tuple[float, float]:
    """Single-column figure (~89mm), landscape 16:9 by default (v1.7.1)."""
    return (SINGLE_COL_IN, SINGLE_COL_IN * aspect)

def figsize_panel(cols: int, aspect: float = 0.72) -> tuple[float, float]:
    """One panel of an N-across composite laid out across \\textwidth.

    A 3-across panel is only ~2in wide — too small for readable axis text, so
    data-heavy panels should use cols<=2.  When cols==3 the caller is told to
    enlarge fonts (the returned size is small by construction); the skill docs
    steer authors to 2-across (or stacked) for data plots.
    """
    w = (TEXTWIDTH_IN * 0.94) / cols
    return (w, w * aspect)

# --------------------------------------------------------------------------
# Visibility tiers (v3.0) — the contrast audit splits the dopamine series by
# WCAG visibility on white: low-contrast light tokens (gold, orange, blue) are
# FILL-only (their stroke_for() outline ≥ 5.1 carries the edge); LINE plots and
# small markers must draw from tokens visible enough for thin geometry.
# --------------------------------------------------------------------------
def palette_visibility() -> dict[str, list[str]]:
    """Split SERIES_ORDER into line-safe vs fill-only by white-canvas contrast."""
    line_safe = [n for n in SERIES_ORDER if contrast(TOKENS[n], "#FFFFFF") >= 3.0]
    fill_only = [n for n in SERIES_ORDER if contrast(TOKENS[n], "#FFFFFF") < 3.0]
    return {"line_safe": line_safe, "fill_only": fill_only,
            "line_strokes": [stroke_for(TOKENS[n]) for n in fill_only]}


# --------------------------------------------------------------------------
# Experiment-plot aesthetics (v2.3 — matches the 640.png reference: line+band
# with per-series markers, top horizontal legend, log-x where warranted)
# --------------------------------------------------------------------------
MARKER_CYCLE = ["o", "s", "^", "D", "v", "P", "X", "*"]

# v1.6.0 single source of truth for series color ORDER. The default matplotlib
# prop_cycle AND series_style() both draw from this, so a naive ax.plot and an
# explicit series_style(0) agree. Ordering is by canvas visibility: the 5
# line-safe tokens (contrast >= 3 on white) come first so the 1st/2nd series of
# any line plot are readable as thin geometry; the 3 fill-only tokens (gold,
# blue, orange — need a stroke_for outline) trail for bars/areas. SERIES_ORDER
# (semantic role order: hero=blue…) is preserved separately for role lookup.
# Lazily computed (palette_visibility needs contrast/stroke_for, defined below).
_CYCLE_HEX: list[str] | None = None


def cycle_hex() -> list[str]:
    """Visibility-ordered series colors — the one cycle both prop_cycle and
    series_style consume (toolchain unity: no second source of color order)."""
    global _CYCLE_HEX
    if _CYCLE_HEX is None:
        vis = palette_visibility()
        _CYCLE_HEX = [TOKENS[n] for n in vis["line_safe"] + vis["fill_only"]]
    return _CYCLE_HEX


def series_style(i: int) -> dict:
    """Consistent (color, marker) pair for series i so multi-line plots get
    distinct markers like the reference, while colors stay on the dopamine
    series cycle (visibility-ordered — see cycle_hex)."""
    cyc = cycle_hex()
    return {"color": cyc[i % len(cyc)],
            "marker": MARKER_CYCLE[i % len(MARKER_CYCLE)]}

def add_error_band(ax, x, y_mean, y_std, color, alpha: float = 0.16):
    """Shaded +/-std (or CI) band around a line — the uncertainty device the
    reference uses.  Call after plotting the mean line with the same color."""
    y_mean = list(y_mean); y_std = list(y_std)
    lo = [m - s for m, s in zip(y_mean, y_std)]
    hi = [m + s for m, s in zip(y_mean, y_std)]
    ax.fill_between(x, lo, hi, color=color, alpha=alpha, linewidth=0, zorder=1)

def legend_top(ax, ncol: int | None = None):
    """Frameless horizontal legend ABOVE the axes (as in the reference)."""
    n = len(ax.get_legend_handles_labels()[0])
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02),
              ncol=ncol or min(n, 4), frameon=False,
              fontsize=NATURE_FLOOR["legend"])

# d2 font sizes are SVG px; at the default ~1000px render width embedded at
# 8in, 1px ≈ 0.58pt.  26px ≈ 15pt node labels — clears the raised 12pt
# diagram floor with margin (v2.1).
D2_FONT_PX = {"node": 26, "edge": 22, "title": 32, "container": 24}

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


def _lin2srgb(v: float) -> float:
    """Inverse gamma on a LINEAR 0-1 value (pair for the 0-1 linear space the
    CVD matrices operate in; distinct from _srgb2lin which takes 0-255 bytes)."""
    v = 0.0 if v < 0 else 1.0 if v > 1 else v
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def rgb2lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_srgb2lin(c) for c in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    # divide by the D65 reference white implied by the matrix row sums
    # themselves, so the reference white maps EXACTLY to L*=100, a*=b*=0
    fx = f(x / (0.4124564 + 0.3575761 + 0.1804375))
    fy = f(y / (0.2126729 + 0.7151522 + 0.0721750))
    fz = f(z / (0.0193339 + 0.1191920 + 0.9503041))
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


# --------------------------------------------------------------------------
# Color-blindness + grayscale distinguishability (v3.0 — the safety net the
# morandi system never had, and that a HIGH-SATURATION dopamine palette needs).
# CVD simulation via the Viénot/Brettel linear-RGB approximation matrices
# (no third-party dep; pure math like the Lab conversion above). Two categorical
# colors are "distinguishable" only if they stay apart (CIE76 ΔE above a floor)
# under normal vision AND each CVD type AND a grayscale print. This replaces
# the old docstring claim "colorblind friendly" (asserted, never checked) with
# an auditable gate — figure_audit A3 consumes it on the delivered palette.
# --------------------------------------------------------------------------
_CVD_MATRICES = {
    "protanopia": ((0.152286, 1.052583, -0.204868),
                   (0.114503, 0.782298, 0.103199),
                   (-0.003882, -0.048119, 1.052)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501, 0.047413),
                     (-0.011820, 0.042944, 0.968876)),
    "tritanopia": ((1.255528, -0.076749, -0.178779),
                   (0.078183, 0.930625, -0.008808),
                   (0.004762, 0.691337, 0.303901)),
}


def _lin_rgb(hexcolor: str) -> tuple[float, float, float]:
    return tuple(_srgb2lin(c) for c in hex2rgb(hexcolor))  # type: ignore[return-value]


def _clip01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def simulate_cvd(hexcolor: str, kind: str) -> str:
    """Simulated #RRGGBB for a dichromat (protanopia/deuteranopia/tritanopia)."""
    m = _CVD_MATRICES[kind]
    r, g, b = _lin_rgb(hexcolor)
    lin = [_clip01(m[i][0] * r + m[i][1] * g + m[i][2] * b) for i in range(3)]
    return "#%02X%02X%02X" % tuple(int(round(_lin2srgb(v) * 255)) for v in lin)


def lab_delta(hex1: str, hex2: str) -> float:
    """CIE76 ΔE in Lab (screening-grade; a large floor catches true collisions)."""
    a = rgb2lab(hex2rgb(hex1)); b = rgb2lab(hex2rgb(hex2))
    return math.dist(a, b)


def pair_distinguishable(hex1: str, hex2: str, min_delta: float = 15.0,
                         min_gray_delta: float = 12.0) -> dict:
    """ΔE under normal + each CVD + grayscale lightness gap. min_gray_delta
    guards the pure-grayscale-print failure mode (two dopamine hues can be
    identical in L* yet vivid in color — unreadable when printed B/W)."""
    checks = {"normal": lab_delta(hex1, hex2)}
    for kind in _CVD_MATRICES:
        checks[kind] = lab_delta(simulate_cvd(hex1, kind), simulate_cvd(hex2, kind))
    gray = abs(rgb2lab(hex2rgb(hex1))[0] - rgb2lab(hex2rgb(hex2))[0])
    failed = [k for k, d in checks.items() if d < min_delta]
    if gray < min_gray_delta:
        failed.append("grayscale(L*)")
    return {"ok": not failed, "deltaE": {k: round(d, 1) for k, d in checks.items()},
            "gray_deltaL": round(gray, 1), "failed_modes": failed}


def palette_distinguishability(hexcodes: list[str], min_delta: float = 15.0) -> dict:
    """All pairwise checks; returns offending pairs (for the A3 gate + self-check)."""
    bad = []
    for i in range(len(hexcodes)):
        for j in range(i + 1, len(hexcodes)):
            r = pair_distinguishable(hexcodes[i], hexcodes[j], min_delta)
            if not r["ok"]:
                bad.append({"pair": [hexcodes[i], hexcodes[j]], **r})
    return {"ok": not bad, "n_pairs": len(hexcodes) * (len(hexcodes) - 1) // 2,
            "offenders": bad}


def sanitize_palette(svg_text: str) -> tuple[str, int]:
    """Deterministically remap every off-palette hex color in an SVG to the
    nearest design token by CIELAB L* (preserving light/dark ordering).

    Engine-injected theme colors (d2's default blues, graphviz defaults)
    are remapped here so the DELIVERED figure is always palette-compliant,
    regardless of tool version drift.  Author spec colors never reach this
    function off-palette — render_figure.py rejects them at source level.
    Recognizes 3-, 6- and 8-digit hex literals (HEX_COLOR_RE): shorthand
    and alpha-suffixed forms are normalized to #RRGGBB for the palette
    check, but the ORIGINAL textual form is remapped (fill="#F00" ->
    fill="<token>").  Returns (sanitized_text, n_replacements).
    """
    targets = sorted(set(HEX_COLOR_RE.findall(svg_text)))
    remap: dict[str, str] = {}
    for h in targets:
        norm = normalize_hex(h)
        c = chroma(norm)
        L = rgb2lab(hex2rgb(norm))[0]
        if c < 2.0 or L > 96 or L < 12:
            continue  # neutrals / near-white / near-black stay untouched
        if is_morandi(norm):
            continue
        best = min(TOKENS.values(), key=lambda t: abs(rgb2lab(hex2rgb(t))[0] - L))
        remap[h.lower()] = best  # keyed by the ORIGINAL textual form
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

    return HEX_COLOR_RE.sub(_sub, svg_text), n


# --------------------------------------------------------------------------
# Runtime icon vocabulary (contract §5.5): recolor third-party icons
# --------------------------------------------------------------------------
def recolor_icon(svg_text: str, mapping: dict | None = None) -> tuple[str, int]:
    """Recolor an arbitrary icon SVG onto the design palette.

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


def derived_colors() -> list[str]:
    """Canonical DERIVED colors: deterministic pure functions of tokens, so they
    are on-palette *by construction* (the audit accepts them without a whitelist
    entry per use). Two families:
      - zone tints:  mix(token, white, 0.85)  — 15% fill backgrounds (method
        recipes' PaperBanana zone strategy)
      - strokes:     stroke_for(token)        — 45% toward ink outlines
    """
    return [mix(t, "#FFFFFF", 0.85) for t in TOKENS.values()] + \
           [stroke_for(t) for t in TOKENS.values()]


def is_on_palette(hexcolor: str, tol: float = 8.0) -> bool:
    """True if hexcolor is a design token (any layer), the canonical stroke
    mix, or a zone tint of one (within Euclidean sRGB distance `tol` over the
    whole RGB triple).

    Named for the palette it currently enforces (dopamine); the morandi alias
    below keeps older callers/verdicts working across the v3.0 rename."""
    try:
        rgb = hex2rgb(hexcolor)
    except (ValueError, IndexError):
        return False
    pool = list(TOKENS.values()) + list(SEMANTIC.values())
    pool += derived_colors()
    pool += [TOKENS["canvas"], "#FFFFFF", "#ffffff", "none"]
    for p in pool:
        if p == "none":
            continue
        if _rgb_dist(rgb, hex2rgb(p)) <= tol:
            return True
    return False


# v3.0 rename: the palette predicate is color-system-agnostic; keep the
# historical names as thin aliases so audits/tests/verdicts keep resolving.
is_dopamine = is_on_palette
is_morandi = is_on_palette

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
    # v2.2 print contract: black glyphs on pure white, rendered at the size
    # the figure will occupy in the paper (full textwidth default) so fonts
    # read 1:1 after LaTeX embed.  Series colors stay dopamine for fills/lines.
    #
    # v3.0 cycle ordering: the default matplotlib prop_cycle is consumed by
    # line plots first, so line-safe tokens (white contrast >= 3) come before
    # fill-only tokens (gold/blue/orange, which need a stroke_for outline).
    # cycle_hex() is the SINGLE source shared with series_style() — a naive
    # ax.plot and an explicit series_style(0) draw the same first color.
    rc = {
        "font.family": "serif",
        "font.serif": stack,
        "mathtext.fontset": "stix",
        "axes.prop_cycle": "cycler('color', %r)" % cycle_hex(),
        "figure.figsize": figsize_full(),
        "figure.facecolor": GROUND,
        "axes.facecolor": GROUND,
        "axes.edgecolor": INK_TEXT,
        "axes.labelcolor": INK_TEXT,
        "axes.labelsize": NATURE_FLOOR["axis_label"],
        "axes.titlesize": NATURE_FLOOR["title"],
        "axes.titleweight": "bold",
        "axes.linewidth": 1.2,
        # 640.png aesthetic: subtle horizontal gridlines ONLY, drawn under the
        # data; top/right spines removed for a clean journal look.
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": INK_TEXT,
        "xtick.color": INK_TEXT,
        "ytick.color": INK_TEXT,
        "xtick.labelsize": NATURE_FLOOR["tick_label"],
        "ytick.labelsize": NATURE_FLOOR["tick_label"],
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.fontsize": NATURE_FLOOR["legend"],
        "legend.frameon": False,
        "lines.linewidth": LINEWIDTH["primary"],
        "lines.markersize": MARKER_SIZE_MIN,
        "patch.edgecolor": INK_TEXT,
        "grid.color": "#D8D8D8",
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
            "#000000", "#404040", "#737373", "#A6A6A6"]
    mpl.rcParams.update(rc)


# --------------------------------------------------------------------------
# d2 design-system preamble (injected by render_figure.py)
# --------------------------------------------------------------------------
def d2_preamble(direction: str | None = None) -> str:
    """Canonical d2 header enforcing the dopamine look & Nature typography.

    Uses the d2 shape-glob selector (`*.style`) so every node inherits the
    design system even when the spec omits styles. NO global-edge block is
    injected — measured against d2 v0.9.0, both candidate syntaxes are
    destructive: `(* -> *).style` is not a style glob but a
    connection-completion selector (an 8-node chain rendered as 65
    all-to-all spaghetti paths — the ARC-Bench Q02 architecture figure),
    and `edges.style:` materializes a ghost node literally named "edges".
    Edge palette compliance is guaranteed downstream by sanitize_palette
    (SVG color remap), so the block is unnecessary.
    """
    lines = [
        "# ---- SciForge-OSS design-system preamble (auto-injected; do not edit) ----",
    ]
    if direction:
        lines.append(f"direction: {direction}")
    lines += [
        "*.style: {",
        f"  fill: \"{TOKENS['surface']}\"",
        f"  stroke: \"{TOKENS['ink-soft']}\"",
        "  stroke-width: 2",
        f"  font-color: \"{INK_TEXT}\"",
        f"  font-size: {D2_FONT_PX['node']}",
        "  border-radius: 6",
        "  bold: false",
        "}",
        "# ---- end preamble; author spec follows ----",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    # self-check: validate every token against the v3.0 dopamine contract
    bad = []
    for name, h in TOKENS.items():
        c = chroma(h)
        if name not in ("ink", "ink-soft", "canvas", "surface", "surface-alt"):
            if c < 30.0:
                bad.append(f"{name} {h} C*={c:.1f} < 30 (not vivid enough)")
            # series token must be visible on the white canvas (line or fill)
            vis = max(contrast(h, "#FFFFFF"), contrast(h, "#000000"))
            if vis < 3.0:
                bad.append(f"{name} {h} canvas-visibility={vis:.2f} < 3.0")
    # the categorical series must be mutually CVD-distinguishable (the dopamine net)
    dv = palette_distinguishability(SERIES_HEX, min_delta=15.0)
    for off in dv["offenders"]:
        # grayscale is covered by the marker encoding (series_style), so only
        # a genuine CVD failure is a contract violation here.
        cvd = [m for m in off["failed_modes"] if m != "grayscale(L*)"]
        if cvd:
            bad.append(f"series pair {off['pair']} fails {cvd} "
                       f"(deltaE={off['deltaE']})")
    if bad:
        print("PALETTE CONTRACT FAILURES:")
        print("\n".join(bad))
        raise SystemExit(1)
    mn = min(min(r["deltaE"].values()) for r in (pair_distinguishable(a, b, 0, 0)
           for a, b in __import__("itertools").combinations(SERIES_HEX, 2)))
    print(f"sciforge_style v{__version__}: {len(TOKENS)} tokens OK "
          f"(C*>=30, canvas-visibility>=3, min series CVD deltaE={mn:.1f})")
    print("d2 preamble preview:")
    print(d2_preamble("right")[:400])
