"""Tests for scripts/plotting/sciforge_style.py — the design system.

hypothesis is not available in this environment, so property-style checks
use pytest.parametrize plus seeded `random` sampling (no new deps).
"""

from __future__ import annotations

import colorsys
import random
import re

import pytest

import sciforge_style as st

TOKEN_ITEMS = sorted(st.TOKENS.items())
TOKEN_HEXES = sorted(st.TOKENS.values())


# ---------------------------------------------------------------------------
# Palette property (v3.0 dopamine contract): every series token is vivid
# (C* >= 30) and visible on the white canvas; neutrals stay neutral.
# ---------------------------------------------------------------------------

NEUTRAL_TOKENS = ("ink", "ink-soft", "canvas", "surface", "surface-alt")

@pytest.mark.parametrize("name,hexcolor", TOKEN_ITEMS)
def test_every_series_token_vivid_on_canvas(name, hexcolor):
    if name in NEUTRAL_TOKENS:
        return
    assert st.chroma(hexcolor) >= 30.0, f"{name} ({hexcolor}) not vivid (C*<30)"
    vis = max(st.contrast(hexcolor, "#FFFFFF"), st.contrast(hexcolor, "#000000"))
    assert vis >= 3.0, f"{name} ({hexcolor}) invisible on canvas"


@pytest.mark.parametrize("name,hexcolor", TOKEN_ITEMS)
def test_every_morandi_token_is_recognized(name, hexcolor):
    assert st.is_morandi(hexcolor), f"token {name} not accepted by is_morandi"


def test_semantic_roles_map_to_morandi_tokens():
    for role, hexcolor in st.SEMANTIC.items():
        assert st.is_morandi(hexcolor), f"semantic role {role} -> {hexcolor}"


def test_series_order_matches_tokens():
    assert st.SERIES_HEX == [st.TOKENS[n] for n in st.SERIES_ORDER]
    assert len(st.SERIES_HEX) == len(set(st.SERIES_HEX))


# ---------------------------------------------------------------------------
# hex2rgb <-> rgb roundtrip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hexstr,rgb", [
    ("#FFFFFF", (255, 255, 255)),
    ("#000000", (0, 0, 0)),
    ("#8AA1BC", (138, 161, 188)),
    ("8AA1BC", (138, 161, 188)),        # leading '#' optional
    ("#ABC", (170, 187, 204)),           # 3-digit shorthand
    ("#35322E", (53, 50, 46)),
])
def test_hex2rgb_known_values(hexstr, rgb):
    assert st.hex2rgb(hexstr) == rgb


def test_hex2rgb_rgb_roundtrip_seeded():
    """rgb -> formatted hex -> hex2rgb is the identity on all channels."""
    rng = random.Random(20260809)
    for _ in range(300):
        rgb = tuple(rng.randint(0, 255) for _ in range(3))
        h = "#%02X%02X%02X" % rgb
        assert st.hex2rgb(h) == rgb
        assert st.hex2rgb(h.lower()) == rgb


# ---------------------------------------------------------------------------
# rgb2lab sanity
# ---------------------------------------------------------------------------

def test_rgb2lab_white_is_L100():
    L, a, b = st.rgb2lab((255, 255, 255))
    assert L == pytest.approx(100.0, abs=0.5)
    assert abs(a) < 0.5 and abs(b) < 0.5


def test_rgb2lab_black_is_L0():
    L, a, b = st.rgb2lab((0, 0, 0))
    assert L == pytest.approx(0.0, abs=1e-9)
    assert a == pytest.approx(0.0, abs=1e-9)
    assert b == pytest.approx(0.0, abs=1e-9)


def test_rgb2lab_grey_lightness_monotonic():
    greys = [(v, v, v) for v in (0, 32, 96, 160, 224, 255)]
    lightness = [st.rgb2lab(g)[0] for g in greys]
    assert lightness == sorted(lightness)
    # tolerance: the sRGB->XYZ matrix rows are truncated to 7 digits, so
    # L*(white) overshoots 100 by ~4e-6 (see module-bugs note in report)
    assert -1e-3 <= lightness[0] and lightness[-1] <= 100.0 + 1e-3


def test_chroma_of_neutral_grey_is_near_zero():
    for h in ("#808080", "#35322E", "#FDFDFD"):
        assert st.chroma(h) < 5.0


# ---------------------------------------------------------------------------
# is_morandi
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hexcolor", TOKEN_HEXES)
def test_is_morandi_true_for_palette_members(hexcolor):
    assert st.is_morandi(hexcolor)


@pytest.mark.parametrize("hexcolor", ["#FF0000", "#0000FF"])
def test_is_morandi_false_for_unknown_primaries(hexcolor):
    assert not st.is_morandi(hexcolor)


def test_is_morandi_false_for_seeded_saturated_colors():
    """Fully saturated HSV colors (S=V=1) all sit far outside the morandi
    gamut: C* > 25 and rejected by is_morandi."""
    rng = random.Random(42)
    for _ in range(60):
        r, g, b = colorsys.hsv_to_rgb(rng.random(), 1.0, 1.0)
        hx = "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))
        assert st.chroma(hx) > 25.0, hx
        assert not st.is_morandi(hx), hx


def test_is_morandi_rejects_malformed_hex():
    assert not st.is_morandi("not-a-color")
    assert not st.is_morandi("#GGGGGG")


def test_is_morandi_accepts_stroke_mixes():
    """Canonical border mixes (45% toward ink) count as palette-compliant."""
    for t in TOKEN_HEXES:
        assert st.is_morandi(st.stroke_for(t)), t


# ---------------------------------------------------------------------------
# sanitize_palette
# ---------------------------------------------------------------------------

def test_sanitize_remaps_known_engine_color_to_token():
    svg = '<svg><rect fill="#3366FF"/></svg>'  # saturated engine-ish blue
    out, n = st.sanitize_palette(svg)
    assert n == 1
    fill = re.search(r'fill="([^"]+)"', out).group(1)
    assert fill in set(st.TOKENS.values())
    assert st.is_morandi(fill)


def test_sanitize_leaves_palette_colors_untouched():
    svg = "<svg>" + "".join(f'<rect fill="{h}"/>' for h in TOKEN_HEXES) + "</svg>"
    out, n = st.sanitize_palette(svg)
    assert n == 0
    assert out == svg


def test_sanitize_leaves_neutrals_untouched():
    svg = ('<svg><rect fill="#808080"/>'      # neutral grey (C* < 2)
           '<rect fill="#FDFDFD"/>'           # near-white (L > 96)
           '<rect fill="#101010"/></svg>')    # near-black (L < 12)
    out, n = st.sanitize_palette(svg)
    assert n == 0
    assert out == svg


def test_sanitize_is_idempotent_seeded():
    """sanitize(sanitize(x)) == sanitize(x), and the second pass is clean."""
    rng = random.Random(7)
    for _ in range(50):
        colors = ["#%06X" % rng.randrange(16 ** 6) for _ in range(6)]
        svg = "<svg>" + "".join(f'<path stroke="{c}"/>' for c in colors) + "</svg>"
        once, _ = st.sanitize_palette(svg)
        twice, n_second = st.sanitize_palette(once)
        assert twice == once
        assert n_second == 0


def test_sanitize_case_insensitive_match():
    out1, n1 = st.sanitize_palette('<svg><rect fill="#3366ff"/></svg>')
    out2, n2 = st.sanitize_palette('<svg><rect fill="#3366FF"/></svg>')
    assert n1 == n2 == 1
    assert out1 == out2


# ---------------------------------------------------------------------------
# NATURE_FLOOR
# ---------------------------------------------------------------------------

def test_nature_floor_positive_and_sensibly_ordered():
    f = st.NATURE_FLOOR
    assert f, "NATURE_FLOOR must not be empty"
    assert all(v > 0 for v in f.values())
    # titles are the largest text; axis labels outrank tick labels;
    # annotations are the smallest printable text; diagram nodes >= edges.
    assert f["title"] >= f["axis_label"] >= f["tick_label"]
    assert f["tick_label"] == f["legend"]
    assert f["annotation"] <= f["tick_label"]
    assert f["diagram_node"] >= f["diagram_edge"]
    assert max(f.values()) == f["title"]


# ---------------------------------------------------------------------------
# d2 preamble / version
# ---------------------------------------------------------------------------

def test_d2_preamble_contains_tokens_and_selectors():
    p = st.d2_preamble("right")
    assert "direction: right" in p
    assert "*.style:" in p
    assert "(* -> *).style:" in p
    assert st.TOKENS["surface"] in p      # shape fill
    assert st.INK_TEXT in p               # v2.2: black text (font-color)
    assert st.TOKENS["ink-soft"] in p     # edge stroke
    assert str(st.D2_FONT_PX["node"]) in p


def test_d2_preamble_without_direction_omits_it():
    assert "direction:" not in st.d2_preamble()


def test_version_is_semver():
    assert re.match(r"^\d+\.\d+\.\d+$", st.__version__)


# ---------------------------------------------------------------------------
# misc color helpers
# ---------------------------------------------------------------------------

def test_mix_endpoints():
    assert st.mix("#000000", "#FFFFFF", 0.0) == "#000000"
    assert st.mix("#000000", "#FFFFFF", 1.0) == "#FFFFFF"


def test_contrast_white_on_black_is_21():
    assert st.contrast("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.1)


# ---------------------------------------------------------------------------
# v3.0 dopamine infrastructure: CVD net + visibility tiers + self-check
# ---------------------------------------------------------------------------

def test_cvd_simulation_moves_red_toward_dark_yellow():
    # protanopia: pure red loses its L-cone signal -> dark yellow-ish
    sim = st.simulate_cvd("#FF0000", "protanopia")
    r, g, b = st.hex2rgb(sim)
    assert r > b and g > b and b < 60, sim


def test_red_green_pair_collides_under_protanopia():
    """Classic CVD failure mode: pure red vs pure green collapse for
    protanopes (ΔE ~10) — the net must catch it."""
    r = st.pair_distinguishable("#FF0000", "#008000")
    assert not r["ok"] and "protanopia" in r["failed_modes"]
    assert r["deltaE"]["protanopia"] < 15


def test_series_palette_passes_cvd_net():
    dv = st.palette_distinguishability(st.SERIES_HEX, min_delta=15.0)
    # grayscale collisions are expected (marker encoding covers them); only a
    # genuine CVD failure would be a contract violation
    cvd_fails = [o for o in dv["offenders"]
                 if any(m != "grayscale(L*)" for m in o["failed_modes"])]
    assert not cvd_fails, cvd_fails


def test_series_tokens_are_vivid_and_visible():
    for name in st.SERIES_ORDER:
        h = st.TOKENS[name]
        assert st.chroma(h) >= 30.0, f"{name} not vivid"
        vis = max(st.contrast(h, "#FFFFFF"), st.contrast(h, "#000000"))
        assert vis >= 3.0, f"{name} invisible"
        # fill-only tokens must have a line-safe stroke (the visibility contract)
        if st.contrast(h, "#FFFFFF") < 3.0:
            assert st.contrast(st.stroke_for(h), "#FFFFFF") >= 4.5, f"{name} stroke too light"


def test_palette_visibility_tiers():
    v = st.palette_visibility()
    assert set(v) == {"line_safe", "fill_only", "line_strokes"}
    assert not set(v["line_safe"]) & set(v["fill_only"])
    assert set(v["line_safe"]) | set(v["fill_only"]) == set(st.SERIES_ORDER)
    assert len(v["line_strokes"]) == len(v["fill_only"])


def test_style_self_check_passes():
    import subprocess, sys
    p = subprocess.run([sys.executable, str(st.__file__)], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "tokens OK" in p.stdout


def test_layer2_includes_cividis():
    assert "cividis" in st.LAYER2_COLORMAPS  # CVD-designed continuous map (research-adopted)
    assert "jet" in st.FORBIDDEN_COLORMAPS
