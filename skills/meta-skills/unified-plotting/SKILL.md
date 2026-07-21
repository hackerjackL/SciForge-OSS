---
name: unified-plotting
type: meta-skill
role: figure-renderer-and-spec-generator
---

# Unified Plotting (SciForge-OSS — Merged figure-spec + paper-figure, Morandi-Enforced)

## Quick Reference

- **Purpose**: 从结构化数据或 JSON spec 渲染出版级矢量图
- **Input**: 数据 (JSON/matrix) 或图表描述
- **Output**: SVG/PDF 矢量图 + 渲染脚本
- **Key**: 11 种图表类型 (含 4 种理论图)；莫兰迪色系强制；数据图 Python 管线，理论图 LaTeX tikz/AI-direct SVG

> **Status**: Visual communication meta-skill — renders publication-quality figures from structured data OR deterministic JSON specs. **OSS merges main SciForge's `figure-spec`** (deterministic JSON → SVG for architecture/workflow/topology diagrams) **and `paper-figure`** (data plots: line/scatter/bar/heatmap/3D) **into this single skill**. **OSS is discipline-agnostic** — the morandi palette + Layer 2 data-encoding colormaps are universal contracts.
>
> **Key OSS relaxation**: main SciForge enforces Python pipeline (matplotlib/seaborn) for all figures. OSS **allows AI-direct SVG generation** when the figure is simple enough (architecture diagrams, flow charts, topology) — the morandi palette contract is still enforced, but the Python pipeline is not mandatory for non-data figures. For **data plots** (line/scatter/bar/heatmap/3D), the Python pipeline remains mandatory (reproducibility requires preserved render script + input data).

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
| **Topology** | graph, network, tree, flow-chart | Relations, hierarchies, pipelines | JSON-spec OR AI-direct SVG |
| **Architecture** | layered, hub-and-spoke, multi-plane | System architecture, workflow | JSON-spec OR AI-direct SVG |
| **Scientific** | errorbar, filled-curve, quiver, streamplot | Error ranges, vector fields | Python (data) |
| **Theoretical** | commutative-diagram, derivation-tree, concept-map, dependency-graph, counterexample-plot | Proof structures, concept relations, theorem dependencies | LaTeX tikz OR AI-direct SVG |

**Pipeline rule**:
- **Data plots** (the first 7 categories + Scientific) → Python pipeline mandatory (matplotlib/seaborn/numpy), render script + input data preserved
- **Diagram plots** (Topology + Architecture) → JSON-spec deterministic renderer OR AI-direct SVG generation (when the diagram is simple enough that AI can hand-write the SVG); either way, the spec/source is preserved for reproducibility
- **Theoretical plots** (Theoretical category) → LaTeX `tikz-cd` for commutative diagrams, or AI-direct SVG for concept maps and dependency graphs. No Python pipeline required — reproducibility is via the LaTeX source or SVG spec preserved.

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
| `width` | string | `6in` | Figure width (inches or cm) |
| `height` | string | `4in` | Figure height (inches or cm) |
| `dpi` | int | `300` | Raster output resolution |
| `color_scheme` | string | `morandi` | Palette — **default is `morandi`** (house default, chroma C* ≤ 25). See [`color-themes.md`](../../shared-references/color-themes.md). Switch to `colorblind-safe` only when the venue explicitly requires it OR the human user explicitly requests it. |
| `renderer` | enum | `auto` | `auto` (pick based on chart type — Python for data, JSON-spec for diagrams), `python` (force Python pipeline), `json-spec` (force deterministic JSON → SVG), `ai-direct` (force AI hand-written SVG — only for simple diagrams) |

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

Based on `renderer` config (default `auto`):
- **Data plot** (line/scatter/bar/heatmap/3D/etc.) → Python pipeline (matplotlib/seaborn/numpy)
- **Diagram plot** (architecture/workflow/topology) → JSON-spec deterministic renderer OR AI-direct SVG (pick based on complexity: ≤ 8 nodes → AI-direct SVG is fine; > 8 nodes → JSON-spec for determinism)

### Step 3a: Python Pipeline (for Data Plots)

Write the complete Python render script (`render.py`):
1. Import matplotlib, seaborn, numpy, and other required libraries
2. Set theme from config (fonts, colors, grid style) — **enforce morandi palette**
3. Read data from `input_data.json`
4. Render the specified chart type
5. Apply labels, title, legend, and annotations
6. Save to `output.svg` and/or `output.pdf`
7. Set random seed for reproducibility

**Code quality rules**:
- Every axis must carry unit annotation (e.g., "Time (s)", "Energy (eV)")
- Font sizes readable at publication scale (axis labels ≥ 10pt, tick labels ≥ 8pt)
- Legend must not overlap data
- `theme: academic` uses morandi palette (NEVER tab10/Set2/matplotlib defaults)
- For continuous scalar fields (heatmap/surface/contour), use viridis/magma/plasma (NEVER jet/rainbow/hsv)
- No interactive elements

### Step 3b: JSON-Spec Renderer (for Complex Diagrams)

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
- **Path**: `figures/{figure_name}/output.pdf`
- **Caption**: {auto-generated caption}
- **Data**: `figures/{figure_name}/input_data.json` (or `spec.md` for AI-direct)
- **Script**: `figures/{figure_name}/render.py` (or `spec.json` / `source.md`)
- **Palette**: morandi (Layer 1) / viridis (Layer 2)
```

## Required Workspace

- `figures/` — output SVG and PDF files
- `figures/{figure_name}/` — per-figure directory with output + preserved source
- `figures/specs/` — source FigureSpec JSON for reproducibility (JSON-spec renderer)
- `figures/FIGURE_INDEX.md` — all generated figures index

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../../shared-references/output-language.md)** — respect the project's language setting

## Boundaries

- **Morandi palette is non-negotiable for categorical/semantic colors.** NEVER use Tailwind/Material/matplotlib-default/tab10/Set2 colors. The color audit in Step 4 rejects prohibited colors.
- **Layer 2 colormaps (viridis/magma/plasma) are mandatory for continuous scalar fields.** NEVER use jet/rainbow/hsv/coolwarm/bwr.
- **Python pipeline is mandatory for data plots.** Reproducibility requires preserved render script + input data. Do NOT AI-direct-generate a data plot (the numbers must come from the actual data, not AI memory).
- **AI-direct SVG is allowed for simple diagrams only** (≤ 8 nodes, no complex auto-layout). For complex diagrams, use the JSON-spec deterministic renderer.
- **Every figure preserves its source** (render.py + input_data.json for data; spec.json for JSON-spec; source.md for AI-direct). No figure is "just an SVG" — the source is part of the output.
- **No discipline-specific enforcement.** Do not reintroduce physics SI-units enforcement or cs-ml benchmark-plot conventions. The universal morandi + Layer 2 contract applies to every problem.
- **`theme: modern` is prohibited.** Override to `theme: academic` and log a warning if requested.

## Output Shape

The final output is:
1. `figures/{figure_name}/output.svg` — vector output (editable)
2. `figures/{figure_name}/output.pdf` — publication-grade output
3. `figures/{figure_name}/render.py` (Python pipeline) OR `spec.json` (JSON-spec) OR `source.md` (AI-direct) — preserved source for reproducibility
4. `figures/{figure_name}/input_data.json` (Python pipeline) — preserved input data
5. `figures/{figure_name}/latex_include.tex` — LaTeX include snippet
6. `figures/FIGURE_INDEX.md` — all generated figures index (appended)

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
