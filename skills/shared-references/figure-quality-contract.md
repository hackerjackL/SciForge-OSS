# Figure Quality Contract (SciForge-OSS — Nature-Level, Dual Output, 16:9)

> **Status (v2.2)**: The single source of truth for figure QUALITY at Nature/Science publication level. Consumed by `/unified-plotting` to enforce: (1) 16:9 horizontal aspect ratio default, (2) dual PDF+PNG output (PDF for LaTeX compile, PNG for AI/agent viewing), (3) Nature-level readability standards (font sizes, line widths, layout), (4) complex architecture-diagram pipeline via d2, (5) humanities/arts figure support.
>
> **Why this exists**: the old unified-plotting defaulted to SVG-only output, had no aspect-ratio contract, no Nature-level readability floor, and no tool pipeline for complex architecture/flow diagrams (only AI-direct SVG which produces small-text, poor-layout, non-Nature figures). This contract fixes all four.

---

## 1. Aspect Ratio (16:9 Horizontal Default)

All figures default to **16:9 horizontal** (横版) aspect ratio. This is the Nature/Science figure standard for wide multi-panel layouts.

| Ratio | When | Aspect (w:h) |
|-------|------|-------------|
| **16:9 (default)** | Single wide figure, multi-panel landscape, architecture diagrams, result curves | 16:9 |
| 4:3 | Square-ish data (correlation matrices, small heatmaps, proof sketches) | 4:3 |
| 3:2 | Traditional academic (fallback if 16:9 clips content) | 3:2 |
| 1:1 | Standalone square (rare — icon, single matrix) | 1:1 |

**Hard rule**: unless the figure content DEMANDS a non-16:9 ratio (e.g., a square correlation matrix), use 16:9. A figure that looks "tall" or "narrow" at 16:9 is a signal the content needs re-layout (split panels, restructure), NOT a signal to change the ratio.

**Enforcement**: the render script MUST set `figsize` to a 16:9 ratio (e.g., `(8, 4.5)`, `(10, 5.625)`, `(12, 6.75)`). The skill rejects a render whose figsize ratio deviates from 16:9 by >10% without an explicit `aspect_ratio` override + documented reason.

---

## 2. Dual Output (PDF + PNG) — Non-Negotiable

Every figure produces **BOTH** a PDF and a PNG:

| Format | Purpose | Used by |
|--------|---------|---------|
| **PDF** (vector) | LaTeX `\includegraphics` compile — the ONLY format embedded in the compiled paper | `/paper-compile` (Phase 13) |
| **PNG** (raster, 300+ DPI) | Human/AI viewing — quick visual check without a PDF reader; other models (that can't read PDF) can view it | `/paper-writing` visual review, `/auto-review-loop`, the human user |

**Why both**: LaTeX compiles cleanly only with PDF (SVG requires `inkscape` conversion which adds a fragile dependency; PNG in LaTeX loses vector quality). But the pipeline's self-review and the human user need to VIEW figures quickly — PNG is universally viewable. Producing only PDF means no agent-side visual review; producing only PNG means non-vector figures in the paper. Dual output closes both gaps.

**Enforcement**: the render script MUST save both `output.pdf` AND `output.png`. The `format` config default is now `pdf+png` (was `svg`). A figure with only one format is INCOMPLETE — the skill re-runs the render to produce the missing format.

**SVG role**: SVG is an INTERMEDIATE format only (for d2/graphviz/tikz → PDF conversion, or for AI-direct diagram editing). The final deliverable is always PDF+PNG, never SVG-alone. If SVG is produced as an intermediate, it is converted to PDF (via `inkscape`/`rsvg-convert`/`d2 --layout=elk`) and to PNG (via the same) before delivery.

---

## 3. Nature-Level Readability Standards

Figures must meet Nature/Science readability floors. The old standards (axis labels ≥ 10pt, tick labels ≥ 8pt) are insufficient — they produce figures where text is too small at print scale.

| Element | Minimum (Nature floor) | Old OSS floor | Rationale |
|---------|------------------------|---------------|-----------|
| **Axis label** | ≥ 12pt | 10pt | Readable at 1-column print (88mm width) |
| **Tick label** | ≥ 10pt | 8pt | Readable at print scale |
| **Legend text** | ≥ 10pt | (none) | Legend must be as readable as ticks |
| **Title** | ≥ 13pt | (none) | Title anchors the figure |
| **Annotation text** | ≥ 9pt | (none) | Inline annotations readable |
| **Line width** | ≥ 1.5pt (primary), ≥ 0.8pt (secondary) | 1.5-2pt / 0.5-1pt | Visible at print |
| **Marker size** | ≥ 6pt | (none) | Distinguishable |
| **Font family** | serif (Nature default) OR sans-serif (Science default) — pick one, state once | serif | Consistent within paper |

**Enforcement**: the render script sets `fontsize` on every text element to meet these floors. The skill's color-audit step (Step 4) now ALSO audits font sizes — rejecting a figure with any text below the Nature floor.

**Layout quality (Nature-level)**:
- No overlapping elements (legend, labels, data)
- No orphaned axis labels (cut off at the figure edge)
- No cramped subpanels (≥ 2pt gap between subpanels)
- Whitespace around the figure (no content touching the frame)
- Captions are BELOW the figure, self-contained (Nature style: "Figure N. **a**, Description of panel a. **b**, ...")

---

## 4. Complex Architecture-Diagram Pipeline (d2)

The old unified-plotting handled architecture/workflow diagrams via "JSON-spec deterministic renderer OR AI-direct SVG." This produces poor figures: AI-direct SVG has small text, no auto-layout, no Nature-level typography; the JSON-spec renderer doesn't exist as a real tool.

**New pipeline**: use **d2** (Declarative Diagramming) for ALL complex architecture/workflow/pipeline/topology diagrams. d2 produces auto-laid-out, properly-typographed, vector diagrams.

| Diagram complexity | Tool | Why |
|--------------------|------|-----|
| ≤ 4 nodes, trivial | AI-direct SVG | Fast, no tool needed |
| 5-20 nodes, architecture/flow/pipeline | **d2** (`.d2` spec → SVG → PDF+PNG) | Auto-layout, proper typography, readable text |
| 20+ nodes, dense graph | **d2** with `--layout=elk` (ELK engine for large graphs) | ELK handles dense layouts better |
| Commutative/category diagrams | LaTeX `tikz-cd` (unchanged) | Math typography |
| Concept maps, dependency graphs | d2 OR AI-direct SVG (d2 preferred for >5 nodes) | d2 auto-layout beats hand-placement |

**d2 pipeline steps**:
1. Write `spec.d2` (d2's declarative DSL — see https://d2lang.com)
2. Render: `d2 --layout=elk spec.d2 output.svg` (produces SVG intermediate)
3. Convert: `rsvg-convert -f pdf -o output.pdf output.svg` AND `rsvg-convert -f png -d 300 -o output.png output.svg` (produces PDF+PNG)
4. Preserve `spec.d2` as the reproducible source (equivalent to `render.py` for data plots)

**d2 styling**: apply the morandi palette via d2's style blocks. d2 accepts custom colors — pass the morandi hex codes. The color audit (Step 4) checks d2 output the same as Python output.

**Fallback if d2 unavailable**: graphviz/dot (also auto-layout, also vector → PDF+PNG via rsvg-convert). AI-direct SVG is the LAST resort, only for ≤ 4 node trivial diagrams.

---

## 5. Humanities/Arts Figure Support

Figures in humanities/arts papers (history timelines, textual-analysis flow, hermeneutic-circle diagrams, comparative-literature structure maps) use the SAME pipeline:

| Humanities figure type | Tool | Pipeline |
|------------------------|------|----------|
| Timeline (historical events) | d2 (sequence diagram) OR matplotlib (horizontal timeline) | d2 → PDF+PNG |
| Argument structure (premise→conclusion) | d2 (flowchart) | d2 → PDF+PNG |
| Textual analysis flow | d2 (workflow) | d2 → PDF+PNG |
| Comparative structure map | d2 (graph) | d2 → PDF+PNG |
| Concept relation map | d2 OR AI-direct SVG (≤4 nodes) | d2 → PDF+PNG |

**No humanities-specific deviation**: the 16:9 default, dual output, Nature-level readability, and morandi palette apply identically. A humanities figure is NOT an excuse for lower quality — a timeline diagram in a history paper must meet the same readability floor as a physics result curve.

---

## 6. Conversion Toolchain (SVG → PDF + PNG)

When a tool produces SVG (d2, graphviz, AI-direct, inkscape), the conversion to PDF+PNG uses:

| Tool | PDF conversion | PNG conversion | Availability |
|------|---------------|----------------|-------------|
| `rsvg-convert` (librsvg) | `rsvg-convert -f pdf -o out.pdf in.svg` | `rsvg-convert -f png -d 300 -o out.png in.svg` | apt: `librsvg2-bin` |
| `inkscape` | `inkscape in.svg --export-pdf=out.pdf` | `inkscape in.svg --export-png=out.png --export-dpi=300` | apt: `inkscape` |
| `d2` (native) | `d2 in.d2 out.pdf` (direct) | (use rsvg/inkscape for PNG from the SVG intermediate) | d2 install script |

**Selection**: `rsvg-convert` preferred (fastest, headless, no GUI). Fallback to `inkscape`. If neither available, BLOCK the figure (do NOT deliver SVG-alone to LaTeX — it breaks compile).

---

## 7. Toolchain Summary (what gets installed)

| Tool | Role | Install |
|------|------|---------|
| `matplotlib` | Data plots (line/scatter/bar/heatmap/3D) — PDF+PNG direct | already present |
| `d2` | Complex architecture/flow/topology diagrams — SVG intermediate | d2 install script |
| `graphviz` (`dot`) | Fallback graph layout — SVG intermediate | apt: `graphviz` |
| `rsvg-convert` | SVG → PDF + PNG conversion | apt: `librsvg2-bin` |
| `inkscape` | Fallback SVG → PDF + PNG | apt: `inkscape` |
| `svgo` | SVG optimization (smaller intermediate files) | npm: `svgo` |
| LaTeX `tikz`/`tikz-cd` | Theoretical diagrams (commutative, derivation trees) — PDF direct | texlive |

The skill auto-detects which are installed and routes accordingly (d2 preferred → graphviz fallback → AI-direct SVG last resort for ≤4 nodes).

---

## 8. Boundaries

- **Dual output is non-negotiable.** A figure with only PDF or only PNG is INCOMPLETE. Re-render to produce both.
- **16:9 is the default.** A non-16:9 figure requires an explicit `aspect_ratio` override + documented reason.
- **Nature readability floor is enforced.** Text below the floor is rejected at the color/quality audit (Step 4).
- **d2 is the preferred diagram tool.** AI-direct SVG is only for ≤ 4 node trivial diagrams. For 5+ node diagrams, d2 (or graphviz fallback) is mandatory.
- **SVG is never the final deliverable.** SVG is intermediate only; the final is PDF+PNG.
- **PDF is the only format embedded in LaTeX.** `\includegraphics{output.pdf}` — never `.png` (loses vector), never `.svg` (breaks pdflatex without conversion).
- **No humanities deviation.** The same quality floor, palette, and pipeline apply to all domains.

---

## 9. See Also

- [`color-themes.md`](color-themes.md) — morandi palette (Layer 1) + viridis/magma (Layer 2)
- [`../meta-skills/unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) — consumer of this contract
- [`../support/paper-compile/SKILL.md`](../support/paper-compile/SKILL.md) — consumes the PDF figures
- [`writing-principles.md`](writing-principles.md) — figure caption style
