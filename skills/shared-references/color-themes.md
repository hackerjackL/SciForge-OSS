# Color Themes for Publication Figures

A curated set of color palettes designed for academic paper figures.
Every theme provides:

- **categorical** (8 colors) — line plots, bar charts, scatter groups
- **semantic** — hero (proposed method), baseline (comparison methods), positive (improvement), negative (degradation), neutral (background/reference)
- **ablation** — single hue + alpha ramp for ablation studies
- **sequential** + **diverging** colormap names for heatmaps
- **accent** (3 colors) — callout arrows, highlights, panel borders

---

## Table of Contents

| Theme ID | Style | Best for |
|----------|-------|----------|
| `morandi` | Low-saturation, muted, dusty elegance (house default) | All disciplines, unified elegant look |
| `signature-macaron` | Pastel soft, warm-pink hero/mint-teal baseline (house style) | General AI/ML papers, distinctive look |
| `scientific-modern` | High-saturation controlled, journal standard | ML conferences (NeurIPS/ICML/ICLR/CVPR) |
| `nature-premium` | Low-saturation, muted earth tones, Nature-style | Nature/Science family journals |
| `nmi-pastel` | Unified-family pastel, lilac/rose hero | Nature Machine Intelligence, unified-family figures |
| `colorblind-safe` | Okabe-Ito + Wong double-safe | Universal default, submission requirement |
| `physical-science` | Single-hue gradients, minimalist | PRL/PRB/APS, physics journals |
| `earth-observation` | Green-brown-blue, vegetation/urban/water intuitive | Remote Sensing, TGRS, IGARSS |

---

## Theme: `morandi` (House Default)

**Low-saturation, muted, dusty elegance.** Inspired by Giorgio Morandi's still-life paintings — every color is desaturated with a grey veil, creating a restrained, sophisticated, and harmonious palette. Best for all disciplines when a unified elegant look is desired. This is the **default theme** for `/paper-figure`.

```python
CATEGORICAL = [
    "#B5A8A0",  # 0: dusty rose    — hero method (warm)
    "#8B9DAF",  # 1: dusty blue    — primary baseline (cool)
    "#A3B5A0",  # 2: sage green    — second method (cool)
    "#A89BB5",  # 3: mauve         — third method (cool)
    "#C4B59A",  # 4: muted ochre   — fourth method (warm)
    "#B0A090",  # 5: taupe         — auxiliary (warm)
    "#D4CFC9",  # 6: warm grey     — reference / ablation
    "#6B6B6B",  # 7: charcoal      — axis / text
]

SEMANTIC = {
    "hero":      "#B5A8A0",   # dusty rose — proposed method
    "baseline":  "#8B9DAF",   # dusty blue — strongest baseline
    "positive":  "#A3B5A0",   # sage green — improvement / gain
    "negative":  "#B59B9B",   # dusty mauve-red — degradation / loss
    "neutral":   "#A8A8A8",   # medium grey — background / reference
}

ABLATION_BASE = "#8B9DAF"     # dusty blue; alpha 0.2 → 1.0

SEQUENTIAL = "Greys"          # grey gradient, Morandi-consistent
DIVERGING  = "BrBG"           # brown → white → blue-green for deviation
```

**Design rationale:**

| Principle | How Morandi satisfies it |
|-----------|--------------------------|
| Low saturation | All colors have chroma C* ≤ 25 (vs. scientific-modern's up to 80). Every hue is "greyed down" |
| Dusty veil | RGB values are pulled toward grey (R≈G≈B offset) — no pure primary colors |
| Warm/cool split | Hero = warm dusty rose (#B5A8A0, hue ~20°); Baselines = cool dusty blue/sage/mauve (hue 200°–280°) |
| High lightness | All data-series colors have L* ≥ 60, ensuring print readability |
| Semantic discipline | Green (sage) = improvement only; Red (dusty mauve) = degradation only; Data series use rose/blue/sage/mauve |
| Grayscale robustness | Luminance ranges from #B5A8A0 (L*≈70) → #8B9DAF (L*≈62) → #6B6B6B (L*≈44) — 3+ distinguishable steps |
| Unified elegance | All colors share the same low-chroma "veil" — the palette looks curated, not random |

**When to override:**
- Venue requires colorblind-safe → switch to `colorblind-safe`
- Nature/Science family → switch to `nature-premium`
- User explicitly requests a different theme → honor the request

**Auto-inference fallback:** When the venue has no specific recommendation and the user has not requested a theme, the system defaults to `morandi`.

---

## Theme: `scientific-modern`

Modern conference-journal standard.

```python
CATEGORICAL = [
    "#0F4D92",  # 0: deep blue — hero method
    "#B64342",  # 1: muted red — primary baseline
    "#42949E",  # 2: teal — second method
    "#D97C2B",  # 3: amber — third method
    "#7C6CCF",  # 4: violet — fourth method
    "#4DAF7A",  # 5: green — positive variant
    "#CFCECE",  # 6: light grey — reference/ablation
    "#272727",  # 7: near-black — special baseline
]

SEMANTIC = {
    "hero":      "#0F4D92",   # proposed method
    "baseline":  "#B64342",   # strongest baseline
    "positive":  "#4DAF7A",   # improvement/gain
    "negative":  "#E53935",   # degradation/loss
    "neutral":   "#767676",   # background/reference
}

ABLATION_BASE = "#3775BA"     # medium blue; alpha range 0.2 → 1.0

SEQUENTIAL = "Blues"          # cool sequential for heatmaps
DIVERGING  = "RdBu_r"         # red→white→blue for deviation
```

**Derivation:** Adapted from Nature Figure `PALETTE` (blue-main `#0F4D92`, red-strong `#B64342`, teal `#42949E`, green `#4DAF7A`). Replaces pure green with a controlled sage tone for print safety.

---

## Theme: `signature-macaron`

**House style — soft pastel/macaron palette.** Baselines form a cool mint/blue family; proposed method forms a warm pink/peach family. Best for general AI/ML papers that want a distinctive, soft, high-quality look.

> ⚠️ **Example recipe, not a fixed palette.** The values below are ONE valid instantiation of the macaron style. Agents should generate macaron-style colors following the **[Macaron Style Rules](#macaron-style-rules)** below, not copy these exact hex codes. Different projects call for different variants — as long as the principles are satisfied, the palette is valid.

```python
CATEGORICAL = [
    "#F4C2C2",  # 0: pastel pink      — hero method (warm)
    "#7EC8C4",  # 1: mint teal        — primary baseline (cool)
    "#A8D8EA",  # 2: baby blue        — second method (cool)
    "#FFDAB9",  # 3: peach            — third method (warm)
    "#E6E6FA",  # 4: lavender         — fourth method (cool)
    "#B8E6B8",  # 5: pale green       — positive variant
    "#D8D8D8",  # 6: light grey       — reference / ablation
    "#888888",  # 7: medium grey      — neutral baseline
]

SEMANTIC = {
    "hero":      "#F4C2C2",   # pastel pink — proposed method
    "baseline":  "#7EC8C4",   # mint teal — baseline family
    "positive":  "#B8E6B8",   # pale green — gain / improvement
    "negative":  "#D4A0A0",   # muted rose — degradation / loss
    "neutral":   "#D8D8D8",   # light grey
}

ABLATION_BASE = "#7EC8C4"     # mint teal; alpha 0.2 → 1.0

SEQUENTIAL = "PuRd"           # pink-purple-red, macaron-consistent
DIVERGING  = "PiYG"           # pink→white→green for signed deviation
```

**Design rationale:**

| Principle | How this example satisfies it |
|-----------|-------------------------------|
| Unified-family rule | Baselines = cool mint/blue (#7EC8C4 → #A8D8EA → #E6E6FA); Hero = warm pink/peach (#F4C2C2 → #FFDAB9) |
| Same hue family = same role | Never maps hero to a blue or baseline to pink |
| Reserve green/red for delta | `positive` = pale green (#B8E6B8), `negative` = muted rose (#D4A0A0) — data series use mint/pink instead |
| Reduce saturation before adding categories | All colors are pastel-level (high L\*, low chroma vs. scientific-modern) |
| Ablation = alpha encoding | `ABLATION_BASE` = mint teal; alpha 0.2→1.0 for minimal→full method |
| Grayscale robustness | Luminance ranges from #F4C2C2 (L\*≈75) → #7EC8C4 (L\*≈68) → #888888 (L\*≈54) — 3+ distinguishable steps |

**Auto-inference fallback:** When the venue has no specific recommendation, the system defaults to signature-macaron style (generate a valid macaron palette using the rules below).

---

## Macaron Style Rules

The macaron style is a **principle-driven family, not a fixed hex palette.** Any palette satisfying ALL rules below qualifies as macaron-style. Generate new colors per project so each paper has a coherent but unique look.

### 1. Warm/Cool Family Split

| Role | Family | Typical hues | Chroma (C\*) | Lightness (L\*) |
|------|--------|-------------|-------------|----------------|
| **Hero** (proposed) | Warm pastel | Pink → Peach → Coral → Rose | 25–40 | 65–80 |
| **Baselines** | Cool pastel | Mint → Teal → Baby Blue → Lavender → Soft Aqua | 20–35 | 60–75 |
| **Positive delta** | Pale green | Mint-green → Sage | 20–30 | 65–80 |
| **Negative delta** | Muted rose | Dusty pink → Mauve → Soft red | 20–30 | 60–70 |
| **Neutral** | Grey | Light→medium grey | <10 | 50–80 |

Rule: Hero's family and Baseline's family must be **visually separable by hue** (Δhue > 30° on HSL wheel). Typical: hero at 0°–30° (pink/peach), baselines at 160°–210° (mint/blue).

### 2. Pastel Constraint (Low Chroma)

All data-series colors must have:
- **Chromatically soft:** C\* (CIELCh) ≤ 40 (vs. scientific-modern's up to 80)
- **High lightness:** L\* ≥ 55 for all colors except annotation grey (#888888 ≈ L\*54)
- **No pure primary colors:** No hex with full saturation (e.g. #FF0000, #00FF00, #0000FF)

### 3. Unified-Family Grouping

- All baselines must belong to the **same cool hue family** (e.g., all within mint→teal→blue→lavender range, hue 160°–270°)
- Hero and its variants belong to a **single warm family** (e.g., pink→peach→coral, hue 0°–30°)
- Maximum 2 families across all data series (warm hero + cool baselines) — **this is what makes it look curated, not random**

### 4. Semantic Color Discipline

- Green (pale) = improvement / gain only — never used for a data series
- Red/pink (muted) = degradation / loss only — never used for a data series
- Heroes and baselines use **family colors** (pink, mint, blue, peach, lavender), not green/red
- Neutral grey = reference line, background annotation, ablation name

### 5. Ablation = Single Hue + Alpha

Pick one color from the baseline family (typically the primary baseline), use it as `ABLATION_BASE`. Vary alpha 0.2→1.0. Do NOT use multiple hues for ablation — that's the most common reviewer complaint.

### 6. Sequential + Diverging Colormap

- Sequential: pick one that goes from the baseline family to hero family (e.g., mint→pink = PiYG is a symmetric example; PuRd, RdPu, BuPu all work)
- Diverging: symmetric divergent centered at white/light (e.g., PiYG, PRGn, PuOr)

### 7. Grayscale Check

Desaturate the palette: if any two colors become indistinguishable (ΔL* < 15), adjust lightness. Minimum 3 distinguishable grey levels across the full set.

---

### Quick Generation Template

When you need a macaron default and there's no `paper-theme.json`, generate colors following this recipe:

```python
# Macaron style: warm hero, cool baselines, pastel constraints
# 1 warm family, 1 cool family, 2 delta colors, 1 neutral
import colorsys

def gen_macaron_categorical():
    warm_hues = [0, 10, 20, 350]         # pink → peach range
    cool_hues = [170, 190, 210, 250]      # mint → blue → lavender
    s, l = 0.40, 0.80                     # pastel: low sat, high light
    warm = [colorsys.hls_to_rgb(h/360, l, s) for h in warm_hues]
    cool = [colorsys.hls_to_rgb(h/360, l, s) for h in cool_hues]
    rgb_to_hex = lambda rgb: '#{:02X}{:02X}{:02X}'.format(
        int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
    return [rgb_to_hex(c) for c in warm[:1] + cool[:3] + warm[1:2] + cool[3:4]]
```

Result: always a macaron-compliant 8-color palette. Fine-tune s, l, and hues per project for a unique look.

---

## Theme: `nature-premium`

Low-saturation muted palette for high-impact journals. Inspired by Nature Biomedical Engineering and Nature Communications visual style.

```python
CATEGORICAL = [
    "#3B6999",  # 0: muted navy — hero
    "#A34E4E",  # 1: muted rust — baseline
    "#5B8A72",  # 2: sage green — positive variant
    "#8B7BAA",  # 3: muted lavender — comparison
    "#C4884A",  # 4: ochre — third method
    "#6899A8",  # 5: muted teal — auxiliary
    "#D4CFC7",  # 6: warm grey — reference
    "#3D3D3D",  # 7: dark charcoal — axis/text
]

SEMANTIC = {
    "hero":      "#3B6999",   # muted navy
    "baseline":  "#A34E4E",   # muted rust
    "positive":  "#5B8A72",   # sage green
    "negative":  "#C44D4D",   # desaturated red
    "neutral":   "#8C8C8C",   # grey
}

ABLATION_BASE = "#4A7BA8"     # muted blue; alpha 0.2 → 1.0

SEQUENTIAL = "YlOrBr"         # warm sequential for abundance/composition
DIVERGING  = "BrBG"            # brown→white→blue-green for deviation
```

**Design note:** All colors desaturated by ~20% vs `scientific-modern`. Avoids pure primary colors. Reads elegantly both in print and on screen.

---

## Theme: `nmi-pastel`

Unified-family palette for Nature Machine Intelligence–style composite figures.
Baselines form a coherent cool family (indigo scale); proposed method variants form a lilac/rose family.

```python
CATEGORICAL = [
    "#484878",  # 0: baseline dark (indigo)
    "#7884B4",  # 1: baseline mid  (steel blue)
    "#B4C0E4",  # 2: baseline soft (periwinkle)
    "#E4E4F0",  # 3: ours tiny    (lilac tint)
    "#E4CCD8",  # 4: ours base    (rose)
    "#F0C0CC",  # 5: ours large   (blush)
    "#D8D8D8",  # 6: neutral light (grey)
    "#606060",  # 7: neutral dark  (charcoal)
]

SEMANTIC = {
    "hero":      "#E4CCD8",   # rose — proposed method
    "baseline":  "#484878",   # indigo — baseline family
    "positive":  "#2E9E44",   # green — delta up
    "negative":  "#E53935",   # red — delta down
    "neutral":   "#A8A8A8",   # grey
}

ABLATION_BASE = "#7884B4"     # steel blue; alpha 0.2 → 1.0

SEQUENTIAL = "Purples"        # purple sequential for heatmaps
DIVERGING  = "PuOr"           # purple→white→orange
```

**Design note:** Reserve green `#2E9E44` and red `#E53935` exclusively for directional delta indicators (arrows, gain/loss labels), NOT for data series. This follows Nature MI's color policy: "reserve green/red mainly for gains, drops, and other directional cues."

---

## Theme: `colorblind-safe`

Double-safe for deuteranopia (red-green) and full grayscale. Based on Okabe-Ito (2008) + Wong (2011) recommendations.

```python
CATEGORICAL = [
    "#0072B2",  # 0: blue          — hero (safe for all)
    "#D55E00",  # 1: vermilion     — baseline (CB-safe)
    "#009E73",  # 2: bluish green  — positive (CB-safe)
    "#CC79A7",  # 3: reddish purple— comparison
    "#F0E442",  # 4: yellow        — accent (light bg OK)
    "#56B4E9",  # 5: sky blue      — auxiliary
    "#999999",  # 6: grey          — reference
    "#000000",  # 7: black         — special
]

SEMANTIC = {
    "hero":      "#0072B2",   # blue
    "baseline":  "#D55E00",   # vermilion
    "positive":  "#009E73",   # bluish green
    "negative":  "#CC79A7",   # reddish purple (instead of red-green)
    "neutral":   "#999999",   # grey
}

ABLATION_BASE = "#0072B2"     # blue; alpha 0.2 → 1.0

SEQUENTIAL = "viridis"        # perceptually uniform, CB-safe
DIVERGING  = "vik"            # Fabio Crameri's vik (CB-safe diverging)
```

**Verification:** Passes Coblis and Color Oracle for deuteranopia/protanopia/tritanopia. Also passes grayscale conversion.

---

## Theme: `physical-science`

Minimalist single-hue palette for physics journals (PRL, PRB, PRA, PRE). Uses one primary hue with controlled luminance steps.

```python
CATEGORICAL = [
    "#1F3D5A",  # 0: dark navy    — primary result
    "#4A6B8A",  # 1: steel blue   — comparison
    "#7B9CBA",  # 2: light blue   — second comparison
    "#A8C4DA",  # 3: pale blue    — auxiliary
    "#D4E3ED",  # 4: very pale    — reference
    "#5A5A5A",  # 5: dark grey    — baseline
    "#8C8C8C",  # 6: mid grey     — neutral
    "#C8C8C8",  # 7: light grey   — background
]

SEMANTIC = {
    "hero":      "#1F3D5A",   # dark navy
    "baseline":  "#5A5A5A",   # dark grey
    "positive":  "#4A6B8A",   # steel blue (variant)
    "negative":  "#8C8C8C",   # mid grey (subtle)
    "neutral":   "#C8C8C8",   # light grey
}

ABLATION_BASE = "#1F3D5A"     # same navy; alpha 0.15 → 1.0

SEQUENTIAL = "Blues"          # single-hue sequential
DIVERGING  = "RdBu_r"         # red-blue for signed deviations
```

**Design note:** Avoids hue-based distinctions for categories. Uses luminance steps instead. Reads well in B&W print without hatching. Best for papers with ≤4 method comparisons.

---

## Theme: `earth-observation`

Green-brown-blue palette optimized for remote sensing, geoscience, and TGRS figures.
Vegetation-friendly greens, urban-friendly browns, water-friendly blues.

```python
CATEGORICAL = [
    "#2E6B4A",  # 0: forest green  — proposed method (vegetation)
    "#8B5E3C",  # 1: earth brown   — baseline (soil/urban)
    "#3A7B9E",  # 2: water blue    — water/hydrology
    "#B8864E",  # 3: desert tan    — arid/barren
    "#6B8E5A",  # 4: olive green   — vegetation variant
    "#A07050",  # 5: warm brown    — urban variant
    "#88B0C8",  # 6: sky blue      — atmospheric
    "#D4C4A8",  # 7: sand          — background
]

SEMANTIC = {
    "hero":      "#2E6B4A",   # forest green
    "baseline":  "#8B5E3C",   # earth brown
    "positive":  "#3A7B9E",   # water blue
    "negative":  "#C44D3C",   # brick red for degradation
    "neutral":   "#A0A090",   # warm grey
}

ABLATION_BASE = "#2E6B4A"     # forest green; alpha 0.2 → 1.0

SEQUENTIAL = "YlGn"           # yellow-green for vegetation indices
DIVERGING  = "PiYG"           # pink→white→green for change detection
```

---

## Theme Selection Guide

| When the paper contains... | Use theme |
|----------------------------|-----------|
| **House default** (no venue match, or general AI/ML) | `signature-macaron` |
| Transformer, Attention, LLM, diffusion, ranking, recommender | `scientific-modern` |
| Biology, medicine, clinical trial, public health | `nature-premium` |
| Model architecture comparison, ablation families, scaling | `nmi-pastel` |
| Any venue that REQUIRES colorblind accessibility | `colorblind-safe` |
| Condensed matter, quantum, statistical physics, PRL/PRB | `physical-science` |
| Remote sensing, satellite imagery, environmental monitoring | `earth-observation` |
| Uncertainty quantification, interpretability, fairness | `colorblind-safe` |
| Materials science, chemistry, battery, catalysis | `nature-premium` |

### Auto-inference from venue

| Venue | Recommended Theme |
|-------|-------------------|
| No match / generic venue | `signature-macaron` (house default) |
| `NeurIPS`, `ICML`, `ICLR`, `CVPR`, `ICCV`, `ECCV`, `AAAI`, `ACL`, `EMNLP` | `scientific-modern` |
| `Nature`, `Science`, `Cell`, `Nature Communications` | `nature-premium` |
| `Nature Machine Intelligence` | `nmi-pastel` |
| `Nature Biomedical Engineering` | `nature-premium` |
| `PRL`, `PRB`, `PRA`, `PRE` | `physical-science` |
| `TGRS`, `IEEE Geoscience and Remote Sensing` | `earth-observation` |
| `JACM`, `TOMS` | `scientific-modern` |
| Generic `IEEE_JOURNAL` | `scientific-modern` |

---

## `figures/paper-theme.json` Format

This JSON file is written by `paper-writing` Phase 0 (or `paper-figure` Step 2 as fallback)
and consumed by all figure-generation skills.

```json
{
  "theme": "scientific-modern",
  "venue": "NeurIPS",
  "categorical": ["#0F4D92", "#B64342", "#42949E", "#D97C2B", "#7C6CCF", "#4DAF7A", "#CFCECE", "#272727"],
  "semantic": {
    "hero": "#0F4D92",
    "baseline": "#B64342",
    "positive": "#4DAF7A",
    "negative": "#E53935",
    "neutral": "#767676"
  },
  "ablation_base": "#3775BA",
  "sequential": "Blues",
  "diverging": "RdBu_r",
  "accents": ["#FFD700", "#42949E", "#EA84DD"]
}
```

### How each skill uses it

| Skill | Field(s) used | How |
|-------|--------------|-----|
| **paper-figure** | `categorical`, `semantic`, `ablation_base`, `sequential`, `diverging` | `COLORS = paper_theme["categorical"]` |
| **figure-spec** | `categorical`, `semantic`, `accents` | Auto-assign node fill/stroke from theme; color scheme via JSON spec fill/stroke |
| **d2-diagram** | `categorical` (first 3) | Theme selection via D2 theme directive |

---

## Quick Reference Card

```
Paper figure color checklist:
□ All figures share ONE theme (same paper-theme.json)
□ Hero method is consistently colored across all panels
□ Ablation uses single-hue alpha ramp, not different colors
□ Green/red reserved for delta cues (improvement/degradation)
□ Category count ≤ palette size (do not cycle)
□ Grayscale test: each category distinguishable when desaturated
```
