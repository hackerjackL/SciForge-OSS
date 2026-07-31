---
name: unified-plotting
type: meta-skill
role: figure-renderer-and-spec-generator
---

# Unified Plotting (SciForge-OSS — Merged figure-spec + paper-figure, Morandi-Enforced)

## Quick Reference

- **Purpose**: 从结构化数据或 JSON spec 渲染出版级矢量图
- **Input**: 数据 (JSON/matrix) 或图表描述
- **Output**: **PDF + PNG 双产出** (PDF for LaTeX compile, PNG for AI/human viewing) + 渲染脚本
- **Key**: 11 种图表类型 (含 4 种理论图)；莫兰迪色系强制；数据图 Python 管线，理论图 LaTeX tikz，复杂架构图 d2；**16:9 横版默认**；**Nature 级可读性**；见 [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md)

> **Status**: Visual communication meta-skill — renders publication-quality figures from structured data OR deterministic JSON specs. **OSS merges main SciForge's `figure-spec`** (deterministic JSON → SVG for architecture/workflow/topology diagrams) **and `paper-figure`** (data plots: line/scatter/bar/heatmap/3D) **into this single skill**. **OSS is discipline-agnostic** — the morandi palette + Layer 2 data-encoding colormaps are universal contracts.
>
> **v2.2 upgrades (figure-quality-contract)**: (1) **dual output** — every figure produces both PDF (for LaTeX compile, the only format embedded in the paper) AND PNG (for AI/human viewing); default `format` is now `pdf+png` (was `svg`). (2) **16:9 horizontal default** — Nature/Science wide-figure standard. (3) **Nature-level readability floor** — axis labels ≥12pt, ticks ≥10pt, legend ≥10pt (was 10pt/8pt). (4) **d2 pipeline for complex diagrams** — AI-direct SVG demoted to ≤4-node trivial only; 5+ node architecture/flow diagrams use d2 (auto-layout, proper typography) → SVG → PDF+PNG. (5) **humanities/arts figures** use the same pipeline (d2 timelines, flowcharts) — no quality deviation. See [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md).
>
> **Key OSS relaxation**: main SciForge enforces Python pipeline (matplotlib/seaborn) for all figures. OSS **allows AI-direct SVG generation** when the figure is simple enough (≤ 4 nodes — architecture diagrams, flow charts, topology) — the morandi palette contract is still enforced, but the Python pipeline is not mandatory for non-data figures. For **data plots** (line/scatter/bar/heatmap/3D), the Python pipeline remains mandatory (reproducibility requires preserved render script + input data).

## Use When

Use this skill when the AI scientist needs to generate publication-quality academic figures from structured data or diagram specs.

Typical prompts:
- "画这个数据的图表" / "plot the simulation results"
- "generate a figure showing the relationship between X and Y"
- "create a system architecture diagram" / "render a 3D surface plot"
- "架构图" / "workflow 图" / "pipeline 图"
- "figure spec" / "draw architecture"

**Not for**: format conversion (use `/drawio-export` if available; otherwise inline the conversion in this skill's output).

## Job

Accept structured data (JSON coordinates / matrices / graph edges) OR a diagram description, then render publication-quality vector figures (SVG/PDF). The engine is discipline-agnostic: astrophysics scatter plots and education-results bar charts are processed identically.

The non-negotiable goals:
1. **Every DATA figure is reproducible** — render script + input data preserved (Python pipeline mandatory for data plots)
2. **Every figure is vector** — SVG or PDF, never raster PNG unless explicitly requested
3. **Every figure has a caption** — auto-generated from chart type + description
4. **Every figure follows the morandi palette** (Layer 1) or Layer 2 data-encoding colormaps (for continuous scalar fields)
5. **No manual editing needed** — output is directly usable in the paper

## Supported Chart Types

| Category | Chart types | Use | Pipeline |
|----------|-------------|-----|----------|
| **Relation** | line, scatter, area, step | X-Y relations, trends, time series | Python (data) |
| **Comparison** | bar, grouped-bar, stacked-bar, histogram | Cross-category value comparison | Python (data) |
| **Distribution** | box, violin, kde, ecdf | Statistical distributions, outliers | Python (data) |
| **Composition** | pie, donut, stacked-area | Parts of a whole | Python (data) |
| **Correlation** | heatmap, correlation-matrix, pairplot | Multivariate relations | Python (data) |
| **3D Surface** | surface, contour, wireframe, 3d-scatter | Math functions, spatial data | Python (data) |
| **Topology** | graph, network, tree, flow-chart | Relations, hierarchies, pipelines | **d2** (5+ nodes) OR AI-direct SVG (≤4 nodes) |
| **Architecture** | layered, hub-and-spoke, multi-plane | System architecture, workflow | **d2** (5+ nodes, `--layout=elk` for dense) OR AI-direct SVG (≤4 nodes) |
| **Scientific** | errorbar, filled-curve, quiver, streamplot | Error ranges, vector fields | Python (data) |
| **Theoretical** | commutative-diagram, derivation-tree, concept-map, dependency-graph, counterexample-plot | Proof structures, concept relations, theorem dependencies | LaTeX `tikz-cd` (commutative) OR **d2** (concept-map, dependency-graph, 5+ nodes) OR AI-direct SVG (≤4 nodes) |
| **Engineering Path** | ai-dev-path | AI 开发路线三段式时间轴（Stage 1/2/3 轮次+投资+风险节点+downside protection） | **d2** (sequence/timeline) OR LaTeX `tikz`/`pgfplots` → PDF |
| **Humanities/Arts** | timeline, argument-structure, textual-flow, comparison-map | Historical timelines, argument maps, hermeneutic diagrams | **d2** (all — same pipeline as STEM, see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §5) |

**Pipeline rule** (v2.2 — see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md)):
- **Data plots** (Relation/Comparison/Distribution/Composition/Correlation/3D Surface/Scientific) → Python pipeline mandatory (matplotlib/numpy), render script + input data preserved, **output BOTH `output.pdf` AND `output.png`** (PDF for LaTeX, PNG for viewing)
- **Diagram plots** (Topology + Architecture) → **d2** (`.d2` spec → SVG intermediate → `rsvg-convert`/`inkscape` → PDF+PNG). AI-direct SVG demoted to ≤4-node trivial only. For 5+ node diagrams, d2 (or graphviz fallback) is mandatory — AI-direct SVG produces small-text, poor-layout, non-Nature figures.
- **Theoretical plots** → LaTeX `tikz-cd` for commutative diagrams (PDF direct); **d2** for concept-maps/dependency-graphs (5+ nodes); AI-direct SVG for ≤4-node trivial. Reproducibility via the LaTeX source OR the `.d2` spec preserved.
- **Engineering Path / Humanities** → **d2** (timelines, argument maps, comparison structures → SVG → PDF+PNG). Same 16:9 default, dual output, Nature readability floor as STEM — no humanities quality deviation.
- **Dual output is non-negotiable** for ALL pipelines: every figure produces both PDF (LaTeX-embeddable) AND PNG (viewable). A figure with only one format is INCOMPLETE — re-render.
- **16:9 horizontal default** for ALL pipelines unless content demands otherwise (square matrix → 4:3; documented reason required for any deviation).

### Theoretical Chart Types Detail

| Type | Description | Rendering method | Use case |
|------|-------------|-----------------|----------|
| **commutative-diagram** | Category-theoretic or algebraic commutative diagrams | LaTeX `tikz-cd` | Morphism relations, exact sequences, functoriality |
| **derivation-tree** | Proof tree / derivation tree showing inference steps | LaTeX `tikz` or AI-direct SVG | Logical derivations, type inference, proof theory |
| **concept-map** | Node-link diagram showing concept relationships | AI-direct SVG | Domain knowledge structure, terminology mapping |
| **dependency-graph** | Directed graph showing theorem/lemma dependencies | AI-direct SVG | Structure of proofs, which results depend on which |
| **counterexample-plot** | Numerical counterexample visualization | Python (data) | Showing a counterexample to a claim |

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | enum | `svg` | `svg` / `pdf` / `png` / `all` |
| `theme` | enum | `academic` | `academic` (serif, restrained), `modern` (sans-serif, vivid — **NEVER use**, violates morandi), `monochrome` (grayscale, print-friendly) |
| `width` | string | `8in` | Figure width (inches or cm) — v2.2: default raised for 16:9 wide figures |
| `height` | string | `4.5in` | Figure height — v2.2: default set for 16:9 ratio (8:4.5 = 16:9) |
| `aspect_ratio` | enum | `16:9` | v2.2: default `16:9` (Nature wide); `4:3`/`3:2`/`1:1` only when content demands (see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §1) |
| `dpi` | int | `300` | Raster output resolution (PNG) |
| `color_scheme` | string | `morandi` | Palette — **default is `morandi`** (house default, chroma C* ≤ 25). See [`color-themes.md`](../../shared-references/color-themes.md). Switch to `colorblind-safe` only when the venue explicitly requires it OR the human user explicitly requests it. |
| `renderer` | enum | `auto` | `auto` (Python for data, d2 for diagrams, tikz-cd for commutative, AI-direct SVG ≤4 nodes only), `python`, `d2` (force d2 for diagrams), `graphviz` (force dot for graphs), `tikz` (LaTeX theoretical), `ai-direct` (force AI hand-written SVG — ≤4 nodes only, LAST resort) |
| `format` | enum | `pdf+png` | v2.2: default `pdf+png` (was `svg`). PDF for LaTeX compile (only format embedded), PNG for AI/human viewing. `svg` is intermediate-only. |

**Hard prohibition on `theme: modern`**: the modern theme uses high-saturation Tailwind colors that violate the morandi chroma C* ≤ 25 principle. If the user requests `theme: modern`, override to `theme: academic` and log a warning.

## Morandi Palette Contract (Layer 1 — Universal)

All categorical/semantic colors use the **morandi** house palette. See [`color-themes.md`](../../shared-references/color-themes.md) Layer 1 for the full contract. Summary:

| Slot | Color | Hex | Use |
|------|-------|-----|-----|
| 1 | warm grey | `#D4CFC9` | Group fills, backgrounds |
| 2 | dusty blue | `#8B9DAF` | Primary series |
| 3 | sage | `#9CAF88` | Secondary series |
| 4 | mauve | `#C7A8A8` | Tertiary series |
| 5 | muted ochre | `#D9A05B` | Accent / highlight |
| 6 | taupe | `#A89B8C` | Quaternary series |
| 7 | dusty rose | `#E8C4C4` | Soft accent |
| 8 | charcoal | `#5C5C5C` | Text, axes, final series |

**NEVER use**: Tailwind high-saturation (`#2563EB` / `#10B981` / `#7C3AED` / `#EA580C`), Material Design blue (`#1565C0` / `#0D47A1`), matplotlib defaults (`tab10` / `Set2`), jet / rainbow / hsv. These violate the morandi chroma C* ≤ 25 principle.

## Layer 2 — Data-Encoding Colormaps (Continuous Scalar Fields)

For **continuous scalar fields** (heatmaps, 3D surfaces, contour plots, correlation matrices), use perceptually-uniform colormaps — NOT morandi. See [`color-themes.md`](../../shared-references/color-themes.md) Layer 2 for the full contract.

| Discipline (OSS — always `general`) | Colormap | Why |
|--------------------------------------|----------|-----|
| `general` (default for all 125 problems) | `viridis` | Conservative, perceptually uniform, CB-safe |
| Physics-flavored problems (field plots, EM maps) | `viridis` or `magma` | Perceptually uniform; required by PRL/PRB-style figures |
| CS/ML-flavored problems (attention maps, loss surfaces) | `viridis` | Perceptually uniform, CB-safe |
| Math-flavored problems (function plots, convergence heatmaps) | `viridis` or `plasma` | Perceptually uniform |

**NEVER use**: `jet`, `rainbow`, `hsv`, `coolwarm`, `bwr` — they create artificial visual boundaries and are not perceptually uniform.

**The two-layer rule**: morandi (Layer 1) for categorical/semantic colors (series, groups, annotations); viridis/magma/plasma (Layer 2) for continuous scalar fields (heatmaps, surfaces). Never mix — a heatmap with morandi colors is wrong (morandi is not perceptually uniform); a line chart with viridis colors is wrong (viridis is for continuous fields, not categorical series).

## Workflow

### Step 1: Parse the Figure Spec

From the request, extract:
1. **Chart type** — from the supported list
2. **Data** — structured data (JSON coordinate arrays, matrices, graph edges) OR a diagram description (for architecture/workflow)
3. **Axis labels** — X, Y, Z (if 3D) labels with units
4. **Title** — figure title (optional)
5. **Legend** — series labels and grouping
6. **Annotations** — specific points, regions, or formulas to emphasize
7. **Q-id** — the frozen problem Q-id (from `refine-logs/FINAL_PROPOSAL.md`) — reference in the figure's preserved spec

Validate data shape matches chart type:
- Line plot → 2D coordinate array (x, y)
- Heatmap → 2D matrix
- Bar chart → categories + values
- Graph → nodes + edge list
- 3D surface → 2D matrix or 3D coordinate array

If data shape is wrong, reject with a clear error message and suggest the correct input format.

### Step 2: Choose the Renderer

Based on `renderer` config (default `auto`) — v2.2 routing per [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §4:
- **Data plot** (line/scatter/bar/heatmap/3D/etc.) → Python pipeline (matplotlib/numpy) → **output BOTH `output.pdf` AND `output.png`**
- **Diagram plot** (architecture/workflow/topology, 5+ nodes) → **d2** (`.d2` spec → SVG → `rsvg-convert`/`inkscape` → PDF+PNG). `--layout=elk` for dense (>20 node) graphs.
- **Diagram plot** (≤4 nodes, trivial) → AI-direct SVG (LAST resort) → `rsvg-convert` → PDF+PNG
- **Commutative/category diagram** → LaTeX `tikz-cd` (PDF direct, then render PNG via `pdftoppm`/`magick` for viewing)
- **Concept-map/dependency-graph** (5+ nodes) → d2 → SVG → PDF+PNG
- **Humanities** (timeline/argument-flow/comparison) → d2 → SVG → PDF+PNG (same as STEM diagrams)
- **Fallback chain** if d2 unavailable: `graphviz`/`dot` → SVG → PDF+PNG; if graphviz unavailable, AI-direct SVG for ≤4 nodes only; for 5+ node diagrams with no d2/graphviz, BLOCK (do not produce a small-text AI-direct figure).

### Step 3a: Python Pipeline (for Data Plots)

Write the complete Python render script (`render.py`):
1. Import matplotlib, numpy, and other required libraries
2. Set theme from config (fonts, colors, grid style) — **enforce morandi palette**
3. Read data from `input_data.json`
4. Render the specified chart type
5. Apply labels, title, legend, and annotations
6. **Save BOTH `output.pdf` AND `output.png`** (v2.2: dual output non-negotiable — PDF for LaTeX, PNG for viewing)
7. Set random seed for reproducibility
8. **Set `figsize` to a 16:9 ratio** (e.g., `(8, 4.5)`, `(10, 5.625)`) unless `aspect_ratio` overridden

**Code quality rules (v2.2 — Nature-level floor per [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §3)**:
- Every axis must carry unit annotation (e.g., "Time (s)", "Energy (eV)")
- **Font sizes meet Nature floor**: axis labels ≥ 12pt, tick labels ≥ 10pt, legend ≥ 10pt, title ≥ 13pt, annotations ≥ 9pt (was 10pt/8pt — too small)
- **Line widths**: primary ≥ 1.5pt, secondary ≥ 0.8pt
- **Marker size**: ≥ 6pt
- Legend must not overlap data
- `theme: academic` uses morandi palette (NEVER tab10/Set2/matplotlib defaults)
- For continuous scalar fields (heatmap/surface/contour), use viridis/magma/plasma (NEVER jet/rainbow/hsv)
- No interactive elements
- No text clipped at figure edges; ≥ 2pt gap between subpanels

### Step 3b: d2 Pipeline (for Complex Diagrams — v2.2)

For architecture/workflow/topology/concept-map/dependency-graph/humanities-timeline diagrams with 5+ nodes, use **d2** (replaces the old JSON-spec renderer):

1. Write `spec.d2` (d2's declarative DSL — see https://d2lang.com):
```d2
direction: right
Input: {shape: rectangle; style.fill: "#D4CFC9"; style.stroke: "#8B9DAF"}
Process: {shape: rounded; style.fill: "#9CAF88"}
Output: {shape: rectangle; style.fill: "#C7A8A8"}
Input -> Process: "feeds"
Process -> Output: "produces"
```
2. Render SVG: `d2 --layout=elk spec.d2 output.svg` (ELK engine for dense graphs; default TALA for normal)
3. Convert to **dual output** (v2.2): `rsvg-convert -f pdf -o output.pdf output.svg` AND `rsvg-convert -f png -d 300 -o output.png output.svg` (fallback: `inkscape output.svg --export-pdf=output.pdf` and `--export-png=output.png`)
4. **Morandi enforcement**: all `style.fill`/`style.stroke` in the `.d2` spec MUST be from the morandi palette. The renderer rejects specs with non-morandi colors.
5. Preserve `spec.d2` as the reproducible source (equivalent to `render.py` for data plots)

**d2 readability**: d2 auto-lays-out nodes with proper typography (no small-text problem). Verify the rendered SVG/PDF has readable labels (≥ 10pt equivalent) — if d2's default font is too small, set `style.font-size` in the `.d2` spec.

### Step 3c: AI-Direct SVG (≤4-node trivial ONLY — v2.2 demoted)

Draft the FigureSpec JSON (see main SciForge's `figure-spec` schema for the full spec):
```json
{
  "canvas": {"width": 900, "height": 520},
  "nodes": [
    {"id": "node_a", "label": "A", "x": 180, "y": 120, "shape": "rounded"},
    {"id": "node_b", "label": "B", "x": 350, "y": 120}
  ],
  "edges": [
    {"from": "node_a", "to": "node_b", "label": "uses"}
  ],
  "groups": [
    {"label": "Layer 1", "node_ids": ["node_a", "node_b"], "fill": "#D4CFC9", "stroke": "#8B9DAF"}
  ]
}
```

**Morandi enforcement**: all `fill` and `stroke` colors in the spec MUST be from the morandi palette (Layer 1). The renderer rejects specs with non-morandi colors.

### Step 3c: AI-Direct SVG (for Simple Diagrams)

For simple diagrams (≤ 8 nodes, no complex auto-layout needed), the agent can hand-write the SVG directly:
```svg
<svg width="500" height="350" xmlns="http://www.w3.org/2000/svg">
  <rect x="50" y="50" width="120" height="60" rx="8" fill="#D4CFC9" stroke="#8B9DAF" stroke-width="2"/>
  <text x="110" y="85" text-anchor="middle" font-family="serif" font-size="14" fill="#5C5C5C">Input</text>
  ...
</svg>
```

**Morandi enforcement**: all `fill` and `stroke` colors in the SVG MUST be from the morandi palette. The agent must NOT use Tailwind/Material/matplotlib-default colors.

**Preserved spec**: even for AI-direct SVG, save the source spec (a markdown description of what the diagram represents + the Q-id) alongside the SVG for reproducibility.

### Step 4: Render and Validate

Execute the render (Python subprocess with 60s timeout, OR JSON-spec renderer, OR AI-direct SVG write):
1. Create figure directory: `figures/{figure_name}/`
2. Write `input_data.json` (or `spec.md` for AI-direct) and `render.py` (or `spec.json` / `source.md`)
3. Execute the render
4. Validate output:
   - File exists and is non-empty
   - File is valid SVG (parseable XML) or PDF (valid magic bytes)
   - File size reasonable (SVG: < 5MB, PDF: < 10MB)
   - **Color audit**: parse the SVG/PDF for non-morandi colors (for categorical) or non-viridis/magma (for continuous); reject if prohibited colors found
5. Auto-generate caption from chart type + data description

### Step 5: Generate LaTeX Include Snippet

For each figure, generate the LaTeX-ready include snippet:
```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.8\textwidth]{figures/{figure_name}/output.pdf}
    \caption{{auto-generated caption}}
    \label{fig:{figure_name}}
\end{figure}
```

Write to `figures/{figure_name}/latex_include.tex`.

### Step 6: Update Figure Index

Append to `figures/FIGURE_INDEX.md`:
```markdown
## {figure_name}
- **Q-id**: [frozen problem Q-id]
- **Type**: {chart_type}
- **Path (PDF)**: `figures/{figure_name}/output.pdf` (LaTeX-embedded)
- **Path (PNG)**: `figures/{figure_name}/output.png` (viewing)
- **Aspect**: 16:9 (default) / [override + reason]
- **Caption**: {auto-generated caption}
- **Data/Source**: `figures/{figure_name}/input_data.json` (data) OR `spec.d2` (d2) OR `spec.md` (AI-direct)
- **Script**: `figures/{figure_name}/render.py` (Python) OR `figures/{figure_name}/spec.d2` (d2) OR `source.md` (AI-direct)
- **Palette**: morandi (Layer 1) / viridis (Layer 2)
- **Readability**: Nature floor verified (axis ≥12pt, ticks ≥10pt)
```

## Required Workspace

- `figures/` — output PDF + PNG files (dual output, v2.2)
- `figures/{figure_name}/` — per-figure directory with `output.pdf` + `output.png` + preserved source
- `figures/{figure_name}/render.py` (Python data) OR `spec.d2` (d2 diagrams) OR `source.md` (AI-direct ≤4 nodes) — preserved source for reproducibility
- `figures/{figure_name}/input_data.json` (Python data) — preserved input data
- `figures/FIGURE_INDEX.md` — all generated figures index

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../../shared-references/output-language.md)** — respect the project's language setting
> - **[Figure Quality Contract](../../shared-references/figure-quality-contract.md)** — dual output, 16:9 default, Nature readability floor, d2 pipeline

## Boundaries

- **Dual output (PDF + PNG) is non-negotiable.** A figure with only one format is INCOMPLETE — re-render. PDF is the only format embedded in LaTeX; PNG is for AI/human viewing.
- **16:9 horizontal is the default.** A non-16:9 figure requires an explicit `aspect_ratio` override + documented reason.
- **Nature readability floor is enforced.** The Step 4 audit rejects any figure with text below the floor (axis <12pt, ticks <10pt, legend <10pt). The old 10pt/8pt floor produced too-small text.
- **Morandi palette is non-negotiable for categorical/semantic colors.** NEVER use Tailwind/Material/matplotlib-default/tab10/Set2 colors. The color audit in Step 4 rejects prohibited colors.
- **Layer 2 colormaps (viridis/magma/plasma) are mandatory for continuous scalar fields.** NEVER use jet/rainbow/hsv/coolwarm/bwr.
- **Python pipeline is mandatory for data plots.** Reproducibility requires preserved render script + input data. Do NOT AI-direct-generate a data plot (the numbers must come from the actual data, not AI memory).
- **d2 is the preferred tool for complex diagrams (5+ nodes).** AI-direct SVG is demoted to ≤4-node trivial diagrams ONLY. For 5+ node architecture/flow/topology/humanities diagrams, d2 (or graphviz fallback) is mandatory — AI-direct SVG produces small-text, poor-layout, non-Nature figures. If d2 AND graphviz are both unavailable, BLOCK 5+ node diagrams (do not produce a low-quality AI-direct figure).
- **SVG is NEVER the final deliverable.** SVG is an intermediate format (d2/graphviz output) converted to PDF+PNG before delivery. `\includegraphics{output.pdf}` in LaTeX — never `.svg` (breaks pdflatex) and never `.png` for vector content (loses quality).
- **Every figure preserves its source** (`render.py` + `input_data.json` for data; `spec.d2` for d2; `source.md` for AI-direct). No figure is "just a PDF" — the source is part of the output.
- **Humanities/arts figures use the same pipeline and quality floor as STEM.** A history timeline, argument map, or hermeneutic diagram must meet the same Nature readability, 16:9 default, dual output, and morandi palette as a physics curve. No humanities quality deviation.
- **No discipline-specific enforcement.** Do not reintroduce physics SI-units enforcement or cs-ml benchmark-plot conventions. The universal morandi + Layer 2 + dual-output + 16:9 contract applies to every problem.
- **`theme: modern` is prohibited.** Override to `theme: academic` and log a warning if requested.

## Output Shape

The final output is (v2.2 — dual output):
1. `figures/{figure_name}/output.pdf` — vector PDF (LaTeX-embedded, the only format in the compiled paper)
2. `figures/{figure_name}/output.png` — raster PNG at 300 DPI (AI/human viewing)
3. `figures/{figure_name}/render.py` (Python data) OR `spec.d2` (d2 diagrams) OR `source.md` (AI-direct ≤4 nodes) — preserved source for reproducibility
4. `figures/{figure_name}/input_data.json` (Python pipeline) — preserved input data
5. `figures/{figure_name}/latex_include.tex` — LaTeX include snippet (`\includegraphics{output.pdf}`)
6. `figures/FIGURE_INDEX.md` — all generated figures index (appended)

(SVG is an INTERMEDIATE-only format for d2/graphviz output, converted to PDF+PNG before delivery — never a final deliverable.)

## Composing With Other Skills

```
/theory-derivation (produces results that need visualization)
    → /unified-plotting               ← you are here
        → /paper-writing (consumes the latex_include.tex snippets)
```

## See Also

- [`../shared-references/color-themes.md`](../../shared-references/color-themes.md) — morandi palette (Layer 1) + viridis/magma data colormaps (Layer 2)
- [`../shared-references/writing-principles.md`](../../shared-references/writing-principles.md) — figure caption style
- [`../shared-references/output-manifest.md`](../../shared-references/output-manifest.md) — product structure contract
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
