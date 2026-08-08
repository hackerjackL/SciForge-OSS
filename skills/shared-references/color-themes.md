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
| Text/axes | `ink` (#3A3733) | All body text, axis lines |

## Morandi palette (Layer 1) — fully consistent with sciforge_style.py

### Inks and surfaces (text, axes, background)

| Token | HEX | C* | Use |
|-------|-----|-----|------|
| ink | #3A3733 | 3.0 | Primary text, axes, arrows |
| ink-soft | #6E675F | 5.6 | Secondary text, node strokes, grid lines |
| canvas | #FAF8F5 | 1.7 | Canvas background |
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
| Font sizes | Axis labels ≥12pt, ticks ≥10pt, legend ≥10pt, title ≥13pt, annotations ≥9pt |
| Line widths | Primary lines ≥1.5pt, secondary lines ≥0.8pt |
| Markers | ≥6pt, distinct shapes (circle/square/diamond) |
| Captions | Self-contained: "Figure N. content + key conclusion" |
| References | `\cref{fig:label}` — no hard-coded "Figure 3" |

## Forbidden colors (rejected by numerical validation)

Tailwind high-saturation (`#2563EB`/`#10B981`/`#7C3AED`/`#EA580C`), Material blues (`#1565C0`/`#0D47A1`), matplotlib defaults (tab10/Set2), and the default theme colors of the d2/graphviz engines (deterministically remapped back to morandi by `sanitize_palette()` before the renderer emits output).

## Quick checks

- morandi Layer 1 (C* ≤ 25) for categorical/semantic use
- viridis/magma/plasma for continuous data
- No jet/rainbow/hsv/coolwarm/bwr
- Dual vector output: PDF + SVG (PDF goes into LaTeX, SVG for viewing/editing)
- Rendering script + input data retained
- Captions are self-contained
