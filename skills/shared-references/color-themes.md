# Color Themes (SciForge-OSS — Unified Morandi Design System v2.0)

> **Core**: morandi palette (Layer 1) + viridis/magma/plasma data heatmaps (Layer 2). Using jet/rainbow/hsv is forbidden.
>
> **Single source of truth**: the color tables in this file and in [`unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) both take the `TOKENS` dictionary in **`scripts/plotting/sciforge_style.py`** as the sole authoritative definition (every color has passed numerical validation: CIELAB chroma C* ≤ 25 and ink text contrast ≥ 4.5). If this document disagrees with the code, the code wins.

## Quick reference

| Use | Palette | Notes |
|------|------|------|
| Categorical/semantic colors | morandi (Layer 1) | Low saturation, soft, elegant. C* ≤ 25 (numerically validated) |
| Continuous data heatmaps | viridis / magma / plasma (Layer 2) | Perceptually uniform, color-blind friendly |
| Emphasis/annotation | `ochre` / `rose` tokens | Arrows, highlights, borders |
| Text/axes/labels | **black `#000000`** (v2.2) | Every glyph, tick and axis spine is pure black; the morandi palette is ONLY for series fills/lines, never for text |

## Morandi palette (Layer 1) — fully consistent with sciforge_style.py

### Inks and surfaces (text, axes, background)

| Token | HEX | C* | Use |
|-------|-----|-----|------|
| text/axes (INK_TEXT) | #000000 | 0.0 | **All** text, ticks, axis spines, arrows — pure black (v2.2) |
| ink-soft | #665F57 | ~5 | Node strokes, grid lines (never for readable text) |
| canvas/ground | #FFFFFF | 0.0 | Figure background — pure white, no off-white/grey |
| surface | #EDE9E2 | 3.9 | Default node fill / panel background |
| surface-alt | #E3DDD3 | 5.6 | Alternating container fill |

### Categorical series colors (ordered by visual priority)

| Token | HEX | C* | ink contrast | Semantic role |
|-------|-----|-----|-----------|---------|
| blue | #93A7BB | 12.9 | 4.78 | Series 1 / hero (proposed method) |
| sage | #A4B294 | 17.2 | 5.28 | Series 2 / positive (improvement) |
| mauve | #BDA5A7 | 9.3 | 5.13 | Series 3 |
| ochre | #C4A880 | 24.9 | 5.22 | accent / highlight |
| taupe | #B0A292 | 10.4 | 4.75 | Series 4 / baseline (comparison method) |
| rose | #D9BCBC | 11.0 | 6.69 | Soft emphasis / annotation fill |
| slate | #97A2B2 | 9.6 | 4.58 | ablation-2 |
| moss | #A5AB91 | 14.4 | 4.98 | ablation-1 |
| clay | #C2A193 | 15.5 | 4.97 | negative (degradation) |

### Semantic aliases (backward-compatible with the old spec)

| Old role name | Maps-to token | Old slot name | Maps-to token |
|---------|-----------|-----------|-----------|
| hero | blue | warm-grey | surface |
| baseline | taupe | dusty-blue | blue |
| positive | sage | dusty-rose | rose |
| negative | clay | charcoal | ink |
| neutral | surface | muted-ochre | ochre |
| ablation-1 | moss | | |
| ablation-2 | slate | | |
| accent | ochre | | |

**Stroke rule**: node stroke = fill color mixed 45% toward ink (`sciforge_style.stroke_for(fill)`), automatically accepted by the audit; hand-written high-saturation strokes are forbidden.

## Data heatmaps (Layer 2)

- **Continuous data**: viridis (default) / magma / plasma
- **Categorical data**: morandi Layer 1 series colors
- **Forbidden**: jet / rainbow / hsv / gist_* / coolwarm / bwr (perceptually non-uniform, create false boundaries)
- **Two-layer rule**: Layer 1 is for categorical/semantic colors; Layer 2 is for continuous scalar fields. Never mix them.

## Figure format spec (Nature minimum bar)

| Property | Rule |
|------|------|
| Format | Dual output: PDF (embedded in LaTeX, the sole delivery format) + SVG (for viewing/editing) |
| Fonts | Data figures: TeX Gyre Termes (serif, matches LaTeX); d2 figures: Liberation Sans (injected via CLI font file) |
| Text color | **Pure black `#000000`** on pure white `#FFFFFF` — never grey/brown ink, never off-white grounds (v2.2) |
| Font sizes (AT FINAL EMBEDDED SCALE) | Axis labels ≥16pt, ticks ≥13pt, legend ≥13pt, title ≥18pt, annotations ≥12pt, diagram nodes ≥14pt |
| Line widths | Primary lines ≥1.8pt, secondary lines ≥1.0pt |
| Markers | ≥7pt, distinct shapes (circle/square/diamond) |
| Captions | Self-contained: "Figure N. content + key conclusion" |
| References | `\cref{fig:label}` — no hard-coded "Figure 3" |

**Print-size contract (v2.2 — cures "figures too small in LaTeX")**: render every data plot at the physical width it will occupy in the paper (`sciforge_style.figsize_full()` / `figsize_single()` / `figsize_panel(cols)`), so the LaTeX embed scale is ~1:1 and the floors above are what the reader actually sees. Rendering an 8in plot and shrinking one panel of it to ~2in (3-across) is the failure this contract removes. Composite figures therefore default to **≤2 columns** for data panels; 3-across is reserved for simple schematics and must be requested explicitly in the `.composite.json` manifest.

## Forbidden colors (rejected by numerical validation)

Tailwind high-saturation (`#2563EB`/`#10B981`/`#7C3AED`/`#EA580C`), Material blues (`#1565C0`/`#0D47A1`), matplotlib defaults (tab10/Set2), and the default theme colors of the d2/graphviz engines (deterministically remapped back to morandi by `sanitize_palette()` before the renderer emits output).

## Quick checks

- morandi Layer 1 (C* ≤ 25) for categorical/semantic use
- viridis/magma/plasma for continuous data
- No jet/rainbow/hsv/coolwarm/bwr
- Dual vector output: PDF + SVG (PDF goes into LaTeX, SVG for viewing/editing)
- Rendering script + input data retained
- Captions are self-contained
