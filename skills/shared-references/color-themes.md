# Color Themes (SciForge-OSS — Unified Dopamine Design System v3.0)

> **Core**: dopamine palette (Layer 1) + viridis/magma/plasma data heatmaps (Layer 2). Using jet/rainbow/hsv is forbidden.
>
> **Single source of truth**: the color tables in this file and in [`unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) both take the `TOKENS` dictionary in **`scripts/plotting/sciforge_style.py`** as the sole authoritative definition. Every series color has passed numerical validation: **CIELAB chroma C* ≥ 30** (vivid), **pairwise color-blindness distinguishability ΔE ≥ 15 under protanopia / deuteranopia / tritanopia** (the CVD net), and **canvas visibility ≥ 3.0** (readable line or fill on the white ground). If this document disagrees with the code, the code wins.
>
> **v3.0 change of character**: the morandi system (C* ≤ 25) is retired. The design language is now a **high-saturation dopamine rainbow** — but "dopamine" here is a *constraint-satisfied* vividness, not decoration: every token was chosen so that no two series colors collide for color-blind readers, and every series is also distinguished by an **independent marker shape** (`series_style`), which is what carries the distinction in a pure-grayscale print (9+ series extend by cycling markers + lightness).

## Quick reference

| Use | Palette | Notes |
|------|------|------|
| Categorical/semantic colors | dopamine (Layer 1) | High saturation, C* ≥ 30, CVD-verified pairwise |
| Continuous data heatmaps | viridis / magma / plasma (Layer 2) | Perceptually uniform, colorblind-safe |
| Emphasis/annotation | `gold` / `red` tokens | Arrows, highlights, borders |
| Text/axes/labels | **black `#000000`** | Every glyph, tick and axis spine is pure black; the dopamine palette is ONLY for series fills/lines, never for text |
| Grayscale-print safety | `series_style` markers | color carries hue, shape carries series identity — B/W print stays legible |

## Dopamine palette (Layer 1) — fully consistent with sciforge_style.py

### Inks and surfaces (text, axes, background) — unchanged by v3.0

| Token | HEX | C* | Use |
|-------|-----|-----|------|
| text/axes (INK_TEXT) | #000000 | 0.0 | **All** text, ticks, axis spines, arrows — pure black |
| ink-soft | #4D4D4D | 0.0 | Node strokes, grid lines (never for readable text) |
| canvas/ground | #FFFFFF | 0.0 | Figure background — pure white, no off-white/grey |
| surface | #F4F1EC | 2.1 | Default node fill / panel background (warm near-white) |
| surface-alt | #EAE5DC | 3.1 | Alternating container fill |

### Categorical series colors (ordered by visual priority; 8 series verified)

| Token | HEX | C* | L* | fill vs white | stroke vs white | Semantic role |
|-------|-----|-----|-----|-----------|---------|---------|
| blue | #00A6FB | 52 | 65 | 2.7 | 7.3 | Series 1 / hero (proposed method) |
| orange | #F3722C | 75 | 63 | 2.9 | 7.7 | Series 2 |
| green | #06A77D | 48 | 61 | 3.1 | 8.0 | positive (improvement) |
| red | #FF3B6B | 77 | 58 | 3.5 | 6.5 | Series 4 / annotation |
| teal | #118AB2 | 34 | 54 | 4.0 | 9.4 | baseline (comparison method) |
| violet | #8338EC | 102 | 44 | 5.6 | 7.5 | ablation-2 |
| gold | #FFBF00 | 84 | 81 | 1.7 | 5.1 | accent / highlight |
| crimson | #D90429 | 83 | 46 | 5.3 | 8.5 | negative (degradation) |

**Verified distinguishability**: all 28 pairwise combinations of the 8 series colors pass min ΔE = 15.0 under each of protanopia / deuteranopia / tritanopia (recompute with `sciforge_style.palette_distinguishability`). The palette is **not hand-picked by eye** — it was locked by constraint search over a vivid pool against the CVD net. A 9th vivid hue could not be added without breaking the ΔE ≥ 15 floor, which is why the series cycle stops at 8 colors and continues by **marker + lightness variation** (the `series_style` and `MARKER_CYCLE` contract).

**Line visibility**: a pure fill on white can have contrast as low as 1.7 (gold), which fails WCAG 3:1 for non-text — so **every series carries a darkened outline** (`stroke_for` = fill + 45% toward ink, column "stroke vs white", all ≥ 5.1). A line plot reads by its stroke, an area reads by fill+stroke; text never uses a series color. This is what lets a vivid, high-chroma palette stay print- and projector-safe where a naive "bright colors" palette would wash out.

### Semantic aliases (backward-compatible with the pre-v3.0 spec)

| Old role name | Maps-to token | Old slot name | Maps-to token |
|---------|-----------|-----------|-----------|
| hero | blue | warm-grey | surface |
| baseline | teal | dusty-blue | blue |
| positive | green | dusty-rose | red |
| negative | crimson | charcoal | ink |
| neutral | surface | muted-ochre | gold |
| ablation-1 | orange | | |
| ablation-2 | violet | | |
| accent | gold | | |

**Stroke rule**: node stroke = fill color mixed 45% toward ink (`sciforge_style.stroke_for(fill)`), automatically accepted by the audit; hand-written off-palette saturated strokes are forbidden.

## Data heatmaps (Layer 2)

- **Continuous data**: viridis (default) / magma / plasma
- **Categorical data**: dopamine Layer 1 series colors
- **Forbidden**: jet / rainbow / hsv / gist_* / coolwarm / bwr (perceptually non-uniform, create false boundaries)
- **Two-layer rule**: Layer 1 is for categorical/semantic colors; Layer 2 is for continuous scalar fields. Never mix them. Layer 2 stays the *scientific* colormaps — a "dopamine" gradient would sacrifice perceptual uniformity, so the emotion register applies only where categories, not quantities, are encoded.

## The three safety nets (v3.0 — what makes dopamine publishable)

1. **Color-blindness net** (`simulate_cvd` + `pair_distinguishable`): protan/deutan/tritan simulation, ΔE ≥ 15 hard floor. Enforced by `sciforge_style` self-check and by figure_audit A3 on the delivered palette.
2. **Grayscale-print net** (`series_style`): every series gets a distinct marker shape, so a B/W reproduction (the most common real-world reviewer failure) still separates the lines. Layer-1 colors additionally spread across the L* range so lightness partially double-encodes.
3. **Contrast net**: text is always pure black on pure white (never a series color); gold/teal (the low-contrast members) carry a stroke or black label where text must sit on them; canvas visibility ≥ 3.0 per series token.

## Figure format spec (Nature minimum bar)

| Property | Rule |
|------|------|
| Format | Dual output: PDF (embedded in LaTeX, the sole delivery format) + SVG (for viewing/editing) |
| Fonts | Data figures: TeX Gyre Termes (serif, matches LaTeX); d2 figures: Liberation Sans (injected via CLI font file) |
| Text color | **Pure black `#000000`** on pure white `#FFFFFF` — never grey/brown ink, never off-white grounds, never a series color for glyphs |
| Font sizes (AT FINAL EMBEDDED SCALE) | Axis labels ≥16pt, ticks ≥13pt, legend ≥13pt, title ≥18pt, annotations ≥12pt, diagram nodes ≥14pt |
| Line widths | Primary lines ≥1.8pt, secondary lines ≥1.0pt |
| Markers | ≥7pt, distinct shapes (circle/square/diamond) — one per series, the grayscale backbone |
| Captions | Self-contained: "Figure N. content + key conclusion" |
| References | `\cref{fig:label}` — no hard-coded "Figure 3" |

**Print-size contract (render at physical size)**: render every data plot at the physical width it will occupy in the paper (`sciforge_style.figsize_full()` / `figsize_single()` / `figsize_panel(cols)`), so the LaTeX embed scale is ~1:1 and the floors above are what the reader actually sees. Rendering an 8in plot and shrinking one panel of it to ~2in (3-across) is the failure this contract removes. Composite figures therefore default to **≤2 columns** for data panels; 3-across is reserved for simple schematics and must be requested explicitly in the `.composite.json` manifest.

## Forbidden colors (rejected by the audit)

Off-palette high-saturation colors that are *not* the house tokens — Tailwind blues (`#2563EB`), Material (`#1565C0`), matplotlib defaults (`tab10`/`Set2`), and the default theme colors of the d2/graphviz engines (deterministically remapped to dopamine tokens by `sanitize_palette()` before the renderer emits output). The engine's own nearest-token snap makes a stray vivid blue become `#00A6FB`. Note the v3.0 reversal: it is *off-palette* vivid colors that are rejected, not vividness itself.

## Quick checks

- dopamine Layer 1 (C* ≥ 30, CVD ΔE ≥ 15, marker-encoded) for categorical/semantic use
- viridis/magma/plasma for continuous data
- No jet/rainbow/hsv/coolwarm/bwr; no off-palette hex anywhere in the delivered figure
- Text/axes pure black on pure white
- Dual vector output: PDF + SVG (PDF goes into LaTeX, SVG for viewing/editing)
- Rendering script + input data retained
- Captions are self-contained
