---
name: unified-plotting
version: 1.7.1
description: "Render publication-quality vector figures (PDF+SVG) from data or JSON specs — 12 chart types incl. v3.4 Composite/Group (subfigure-grid, panel-2x2, inset-zoom), Dopamine palette (v3.0, CVD-verified high-saturation) + viridis/magma colormaps, 16:9 default, Nature readability floor. v3.5 UNIFIED SINGLE-ENTRY RENDERER: all diagram engines (d2/graphviz/tikz/SVG) consolidated behind one tool `scripts/plotting/render_figure.py` with embedded Nature-level audit. v3.4 Figure Budget Contract sets per-section minimums (Intro≥1, Methods≥1 architecture diagram MANDATORY, Results 2-4) consumed by paper-writing. Phase 11. Invoke when the paper needs figures."
type: meta-skill
role: figure-renderer-and-spec-generator
---

# Unified Plotting (SciForge-OSS — Merged figure-spec + paper-figure, Dopamine-Enforced v3.0)

## Quick Reference

- **Purpose**: Render publication-quality vector figures from structured data or JSON specs
- **Input**: Data (JSON/matrix) or a chart description
- **Output**: **PDF + SVG dual output** (PDF for LaTeX compile, SVG for agent viewing/editing) + render script + `figure_audit.json`
- **Key**: 15 engines incl. declarative recipe (data) + method-template (L1-L5) paths; dopamine palette enforced (single source of truth `scripts/plotting/sciforge_style.py`); data plots via the Python pipeline, complex diagrams via the **unified render tool**; **16:9 landscape default**; **Nature-level readability**; see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) (format), [`figure-complexity-contract.md`](../../shared-references/figure-complexity-contract.md) (complexity/aesthetics floor) and [`figure-layout-contract.md`](../../shared-references/figure-layout-contract.md) (**排版宪法**: figure contract, panel inferential roles, Nature page archetypes, 1.5pt panel-alignment gate, final-width sizing ratio)

> **v3.5 single entry point tool (UNIFIED SINGLE-ENTRY RENDERER)**: all declarative diagrams (d2 / graphviz / tikz / AI-direct SVG) are produced through **one** CLI only; parallel multi-tool runs or bypassing are forbidden:
>
> ```bash
> python scripts/plotting/render_figure.py <spec.d2|spec.dot|spec.tex|source.svg> \
>     --out figures/{figure_name}/ --label {figure_name} \
>     --caption "..." --strict
> ```
>
> The tool automatically completes internally: design-system preamble injection (d2) → engine render (d2 auto-selects dagre/elk) → deterministic sanitization of engine-leaked colors → SVG→PDF+SVG dual output → LaTeX include snippet → embedded Nature-level audit (`figure_audit.json`, verdict PASS/WARN/FAIL; under `--strict`, FAIL exits with code 4). Data plots still go through the Python pipeline (reproducibility requirement) but must call `apply_matplotlib_style()` at the top of the script to apply the unified theme. See [`scripts/plotting/INSTALL.md`](../../../scripts/plotting/INSTALL.md) for dependency installation; environment self-check: `python scripts/plotting/render_figure.py --doctor`.
>
> **v3.7 three enhancements**: (1) **Journal width presets** `--width-preset nature-single|nature-double|aaai-single|...` (14 layouts; the LaTeX include automatically uses the physical width in mm, and the audit's width floor adapts automatically; see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §1.5); (2) **Runtime icon vocabulary** — professional icons can be fetched at runtime from whitelisted open-source libraries (bioicons/Tabler/Lucide/Feather/Font Awesome Free), mandatorily recolored to the dopamine palette via `sciforge_style.recolor_icon()` before use, with the source license recorded in `revision_log.md` (contract §5.5; on fetch failure, fall back to hand-drawn icons — non-blocking); (3) **Audit auto-fix suggestions** — the `suggested_fixes` field of `figure_audit.json` outputs precise offset coordinates for text overlaps ("move label X down by Npx"); apply them one by one per contract §4.6 scoped revision.
>
> **v3.8 composite figure engine (Composite — SCI Zone-1 norm, contract §7)**: multi-panel composite figures (4/6/N panels) are assembled via the single entry point `render_figure.py xxx.composite.json`: panels (PDF/PNG) → grid layout → **(a)(b)(c)… bold panel labels** (reserved strip above each panel, never covering content) → dual output + audit. **Composition decisions follow Nature/Science/Cell logic**: compose by narrative unit (only panels belonging to the same argument/experiment chain share one figure), panel count **hard cap 9** (beyond it the renderer rejects outright — split the figure or move panels to supplementary material — the "everything-in-one-pot" anti-pattern), single-panel figures remain equally legal, numbering adapts continuously to the panel count. Every panel must **independently** satisfy all audit and complexity rules — composite assembly cannot rescue low-quality panels. Data plots (curves/ablations/heatmaps, etc.) join composite figures as panels; when coexisting in one figure with schematic panels, the style must be unified (same font family / color sequence / line width).
>
> **v3.9 two-tier visual review (Visual Review — zero external API, see [`figure-quality-review.md`](../../shared-references/figure-quality-review.md))**: the mechanical audit (A1–A10) verifies structure only, not aesthetics; visual quality is closed by a two-tier protocol: **Tier 1 = the agent's own native vision** — when the host agent can read images (a multimodal, vision-capable host), after every render it **must open `output.svg` and self-review item by item against the 9-item visual checklist** (message readability / visual hierarchy / whitespace balance / wiring legibility / typography scan / palette discipline / icon discriminability / composite-specific / print-shrink test), write the answers into `revision_log.md`, and fix at source + re-render when problems are found; **Tier 2 = external advisor** (optional — used only when the deployment already has a model endpoint; the skill stores no credentials and initiates no calls). **A text-only agent cannot read images → record `visual-review: skipped-text-only`, deliver per the mechanical audit, never block**. Capability detection is a host attribute: this skill never calls an external vision API on the host's behalf.

> **v3.10 layout constitution (Nature-grade 排版, 2026-09-27; absorbs Yuan1z0825/nature-skills nature-figure, Zhangyanbo/nature-style-skill, thesis-figure-skill, research-figure-composer, FigFox-Gen, apaper PRINCIPLES)**: composition is now LOCKED by [`figure-layout-contract.md`](../../shared-references/figure-layout-contract.md). Non-negotiables: (1) **Five-Point Figure Contract before any code** — core conclusion (one sentence with a verb) + evidence chain (each panel = one inferential role from the 10-role table) + archetype + locked toolchain + export contract; specs missing `claim`/`archetype` are rejected. (2) **Page archetypes fix geometry**: `schematic-led` (hero 45–60% height, `height_ratios=[2.2,1.0]`), `asymmetric-hero` (central panel spans rows/cols), `image-plate` (black only inside plate cells), `clinical-triptych` (`height_ratios=[1.0,1.35,0.8]`, shared legend above), `quantitative-grid` (equal spans) — select via `figure_recipes` `panel-grid` `layout` field; model fills content only. (3) **A11 panel-alignment gate** (1.5pt physical tolerance on shared edges/widths/heights/gutters; `panel_layout.json` manifest; FAIL blocks export; asymmetric heroes are recorded exemptions, never tolerance-weakening). (4) **Final-width-first sizing**: `on_page_font_pt = font_pt × W_doc / W_fig` must stay 1 — set `figsize` to the journal column width FIRST (nature-single 89mm / nature-double 183mm / height ceiling 240mm), never draw big and let LaTeX shrink. (5) **Human construction order** for method diagrams (base → content → restrained arrows → exact text → visual next to label) + AI-slop red list (no box+arrow-only, no 3-color blue/orange/purple defaults, no numbered 1/2/3/4 planning labels, no sticker badges). (6) **Necessity test** for every panel: if removing it loses no unique inference, it does not belong in the main figure.

> **Agent-driven staged design workflow (borrows AutoFigure-Edit's staged assembly idea, MIT licensed; this skill has zero external API — the "model" is the agent itself, and users get it out of the box with their own Claude/Codex/AtomCode)**:
> 1. **Skeleton**: extract the component list + data flow + grouping hierarchy from the methods-section text; write the layout skeleton first (containers/rows-columns/edges), do not rush to draw
> 2. **Fill**: pick the engine by content type — architecture/flow via d2 or diagrams/blockdiag (professional icon sets / swimlanes), mechanism detail via tikz, geometry/schematics via asy, fast iteration via typst, Visio-grade precision figures via hand-assembled SVG (orthogonal rounded-corner routing), data via matplotlib; fill every component with dopamine token styles
> 3. **Assemble**: render everything through the single entry point `render_figure.py` (preamble injection, palette sanitization, dual output, LaTeX snippet — all completed in one step)
> 4. **Review**: the mechanical layer reads the `figure_audit.json` verdict and `suggested_fixes`; on FAIL, apply local fixes item by item using the precise coordinates in suggested_fixes (contract §4.6 scoped revision, one issue class per pass), then re-render. **Visual layer** (v3.9): a host agent with native vision must open `output.svg`, self-review item by item against the 9-item checklist in figure-quality-review.md, and record into `revision_log.md`; a text-only host records skipped-text-only and delivers per the mechanical audit. Manual pixel patching of PNG/SVG is forbidden
>
> **Complexity hard constraint (v3.6 — anti-"elementary-school-level" figures, applies to all domains)**: every figure with 5+ nodes must satisfy [`figure-complexity-contract.md`](../../shared-references/figure-complexity-contract.md): ≥60% of components use **self-drawn icons** (d2 `icon:`; the agent writes the SVG on the fly and saves it alongside the figure into `figures/<name>/icons/`) or TikZ `\pic` self-drawn components; edges must consolidate into container-level buses (arrow rain forbidden, edge density ≤1.6); at least two grouping levels; text discipline (≤3 lines / ≤4 words). Below the floor = the figure is not finished yet — keep iterating. Audit layer A7 mechanically checks icon count and edge density. First judge the figure's **structural role** (structure/flow/mechanism/network/hierarchy/temporal/spatial/data) per contract §0.5 to pick the engine — the domain only determines component semantics, not the rules.

> **Status**: Visual communication meta-skill — renders publication-quality figures from structured data OR deterministic JSON specs. **OSS merges main SciForge's `figure-spec`** (deterministic JSON → SVG for architecture/workflow/topology diagrams) **and `paper-figure`** (data plots: line/scatter/bar/heatmap/3D) **into this single skill**. **OSS is discipline-agnostic** — the dopamine palette + Layer 2 data-encoding colormaps are universal contracts.
>
> **v2.2 upgrades (figure-quality-contract)**: (1) **dual output** — every figure produces both PDF (for LaTeX compile, the only format embedded in the paper) AND SVG (for agent viewing/editing); default `format` is now `pdf+svg` (was `svg`). (2) **16:9 horizontal default** — Nature/Science wide-figure standard. (3) **Nature-level readability floor (v2.2 print floors, at final embedded scale)** — axis labels ≥16pt, ticks ≥13pt, legend ≥13pt, title ≥18pt, annotations ≥12pt. (4) **d2 pipeline for complex diagrams** — AI-direct SVG demoted to ≤4-node trivial only; 5+ node architecture/flow diagrams use d2 (auto-layout, proper typography) → SVG → PDF+SVG. (5) **humanities/arts figures** use the same pipeline (d2 timelines, flowcharts) — no quality deviation. See [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md).
>
> **Key OSS relaxation**: main SciForge enforces Python pipeline (matplotlib/seaborn) for all figures. OSS **allows AI-direct SVG generation** when the figure is simple enough (≤ 4 nodes — architecture diagrams, flow charts, topology) — the dopamine palette contract is still enforced, but the Python pipeline is not mandatory for non-data figures. For **data plots** (line/scatter/bar/heatmap/3D), the Python pipeline remains mandatory (reproducibility requires preserved render script + input data).

## Use When

Use this skill when the AI scientist needs to generate publication-quality academic figures from structured data or diagram specs.

Typical prompts:
- "Plot a chart of this data" / "plot the simulation results"
- "generate a figure showing the relationship between X and Y"
- "create a system architecture diagram" / "render a 3D surface plot"
- "Architecture diagram" / "workflow diagram" / "pipeline diagram"
- "figure spec" / "draw architecture"

**Not for**: format conversion (format conversion is done inline within this skill in OSS; no `/drawio-export`).

## Job

Accept structured data (JSON coordinates / matrices / graph edges) OR a diagram description, then render publication-quality vector figures (SVG/PDF). The engine is discipline-agnostic: astrophysics scatter plots and education-results bar charts are processed identically.

The non-negotiable goals:
1. **Every DATA figure is reproducible** — render script + input data preserved (Python pipeline mandatory for data plots)
2. **Every figure is vector** — SVG or PDF, never raster PNG unless explicitly requested
3. **Every figure has a caption** — auto-generated from chart type + description
4. **Every figure follows the dopamine palette** (Layer 1) or Layer 2 data-encoding colormaps (for continuous scalar fields)
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
| **Engineering Path** | ai-dev-path | AI development roadmap three-stage timeline (Stage 1/2/3 rounds + investment + risk nodes + downside protection) | **d2** (sequence/timeline) OR LaTeX `tikz`/`pgfplots` → PDF |
| **Humanities/Arts** | timeline, argument-structure, textual-flow, comparison-map | Historical timelines, argument maps, hermeneutic diagrams | **d2** (all — same pipeline as STEM, see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §5) |
| **Composite / Group** (v3.4 — NEW) | subfigure-grid, panel-2x2, panel-1x3, panel-2x3, inset-zoom, dual-axis | Multi-panel figures (a/b/c/d panels sharing one caption), grouped result comparisons, inset detail + overview | Python (`matplotlib` `subplots`/`gridspec`) for data panels OR d2 multi-graph for diagram panels → **single composite PDF+SVG**; LaTeX side: `\usepackage{subcaption}` + `\begin{figure}\subfloat{...}\subfloat{...}\end{figure}` OR single rendered PDF embedded with panel labels (a/b/c) baked into the image |

**Pipeline rule** (v2.2 — see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md)):
- **Data plots** (Relation/Comparison/Distribution/Composition/Correlation/3D Surface/Scientific) → Python pipeline mandatory (matplotlib/numpy), render script + input data preserved, **output BOTH `output.pdf` AND `output.svg`** (PDF for LaTeX, SVG for viewing/editing)
- **Diagram plots** (Topology + Architecture) → **d2** (`.d2` spec → SVG intermediate → `rsvg-convert`/`inkscape` → PDF+SVG). AI-direct SVG demoted to ≤4-node trivial only. For 5+ node diagrams, d2 (or graphviz fallback) is mandatory — AI-direct SVG produces small-text, poor-layout, non-Nature figures.
- **Theoretical plots** → LaTeX `tikz-cd` for commutative diagrams (PDF direct); **d2** for concept-maps/dependency-graphs (5+ nodes); AI-direct SVG for ≤4-node trivial. Reproducibility via the LaTeX source OR the `.d2` spec preserved.
- **Engineering Path / Humanities** → **d2** (timelines, argument maps, comparison structures → SVG → PDF+SVG). Same 16:9 default, dual output, Nature readability floor as STEM — no humanities quality deviation.
- **Composite / Group plots (v3.4 — NEW)** → two valid modes:
  1. **Pre-rendered composite** (preferred for data panels): Python `matplotlib.subplots`/`gridspec` renders all panels into ONE PDF+SVG with (a)/(b)/(c) labels baked in. LaTeX embeds the single PDF via `\includegraphics`. Caption uses Nature style: "Figure N. **a**, Description. **b**, Description. ...". Preserves ONE render.py + ONE input_data.json for the whole composite.
  2. **LaTeX `subcaption` composite** (preferred when panels are heterogeneous — e.g. a d2 architecture diagram + a data plot + a table): each panel is a separate PDF; LaTeX assembles via `\usepackage{subcaption}` + `\begin{figure}\subfloat[...]{\includegraphics{panel_a.pdf}}\subfloat[...]{\includegraphics{panel_b.pdf}}\end{figure}`. The `subcaption` package MUST be loaded in the unified skeleton's preamble (add to `math_commands.tex` or `main.tex` preamble: `\usepackage{subcaption}`).
  - **Panel label rule**: every subpanel gets a bold lowercase letter label **(a)**, **(b)**, **(c)**... — either baked into the image (mode 1) or via `\subfloat`'s caption (mode 2). Never unlabeled panels.
  - **Gap rule** (from figure-quality-contract): ≥ 2pt gap between subpanels; no cramped layouts.
  - **Caption self-contained**: the composite caption explains ALL panels — a reader should understand the figure without reading the body text.
  - **Dual output for composites**: the composite produces `output.pdf` (LaTeX-embeddable) AND `output.svg` (viewable) regardless of mode. For mode 2 (LaTeX subcaption), the composite PNG is a rendered preview of the assembled figure (the agent renders it once for review).
- **Dual output is non-negotiable** for ALL pipelines: every figure produces both PDF (LaTeX-embeddable) AND SVG (viewable/editable). A figure missing either is INCOMPLETE — re-render.
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
| `format` | enum | `pdf+svg` | v2.2: default `pdf+svg` (was `svg`). PDF for LaTeX compile (only format embedded), SVG for agent viewing/editing. `svg` is intermediate-only. |
| `theme` | enum | `academic` | `academic` (serif, restrained palette-first), `modern` (sans-serif, high-impact — permitted since v3.0 as it aligns with the dopamine palette), `monochrome` (grayscale, print-friendly) |
| `width` | string | `8in` | Figure width (inches or cm) — v2.2: default raised for 16:9 wide figures |
| `height` | string | `4.5in` | Figure height — v2.2: default set for 16:9 ratio (8:4.5 = 16:9) |
| `aspect_ratio` | enum | `16:9` | v2.2: default `16:9` (Nature wide); `4:3`/`3:2`/`1:1` only when content demands (see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §1) |
| `dpi` | int | `300` | PNG rasterization resolution (composite panels / pdftoppm steps only) |
| `color_scheme` | string | `dopamine` | Palette — **default is `dopamine`** (v3.0 house default, C* ≥ 30, CVD-verified ΔE ≥ 15, marker-encoded for grayscale). See [`color-themes.md`](../../shared-references/color-themes.md). The palette itself IS the colorblind-safe one (constraint-verified), so no venue-specific switch is needed; `monochrome` stays for print-only venues. |
| `renderer` | enum | `auto` | `auto` (Python for data, d2 for diagrams, tikz-cd for commutative, AI-direct SVG ≤4 nodes only), `python`, `d2` (force d2 for diagrams), `graphviz` (force dot for graphs), `tikz` (LaTeX theoretical), `ai-direct` (force AI hand-written SVG — ≤4 nodes only, LAST resort) |

**`theme: modern` is permitted since v3.0** (reverses the pre-v3.0 morandi-era ban): the dopamine design system is itself high-saturation, so a sans-serif vivid theme no longer conflicts — it just must still draw its series colors from the design tokens (`is_on_palette`), not arbitrary Tailwind hexes. Off-palette vivid colors are still rejected/remapped at source. Text stays pure black regardless of theme.

## Dopamine Palette Contract (Layer 1 — Universal)

All categorical/semantic colors use the **dopamine** house palette (v3.0; CVD-verified, high-saturation). The single source of truth is `scripts/plotting/sciforge_style.py` (`TOKENS`); the table below mirrors it. See [`color-themes.md`](../../shared-references/color-themes.md) for semantic-role mappings and legacy aliases.

| Token | Hex | C* | Use |
|-------|-----|----|-----|
| ink | `#3A3733` | 3.0 | Text, axes, arrows |
| ink-soft | `#6E675F` | 5.6 | Secondary text, strokes, gridlines |
| canvas | `#FAF8F5` | 1.7 | Figure background |
| surface | `#EDE9E2` | 3.9 | Default node fill / panel background |
| surface-alt | `#E3DDD3` | 5.6 | Alternating container fill |
| blue | `#93A7BB` | 12.9 | 1st series / hero |
| sage | `#A4B294` | 17.2 | 2nd series / positive |
| mauve | `#BDA5A7` | 9.3 | 3rd series |
| ochre | `#C4A880` | 24.9 | Accent / highlight |
| taupe | `#B0A292` | 10.4 | 4th series / baseline |
| rose | `#D9BCBC` | 11.0 | Soft accent / annotations |
| slate | `#97A2B2` | 9.6 | ablation-2 |
| moss | `#A5AB91` | 14.4 | ablation-1 |
| clay | `#C2A193` | 15.5 | negative / degradation |

**NEVER use**: off-palette hexes — Tailwind blues (`#2563EB`), Material (`#1565C0` / `#0D47A1`), matplotlib defaults (`tab10` / `Set2`), jet / rainbow / hsv. The v3.0 rule is NOT a saturation cap (that was the retired morandi C* ≤ 25): it is an **on-palette** rule — every categorical color must be a design token that passed the CVD + contrast nets. Arbitrary vivid colors are rejected at source; engine-injected theme colors in SVG output are deterministically remapped to tokens (`sanitize_palette`) before delivery.

**Usage constraint (v3.0, from the dopamine contrast audit)**: the lightest tokens (`gold` #FFBF00 contrast 1.7, `blue` 2.7, `orange` 2.9 on white) are **fill-only** — they carry a `stroke_for()` dark outline (all outlines ≥ 5.1 contrast) and must not be used as thin lines or small markers alone. Line plots and point series draw in tokens with L* ≤ 62 (`violet`, `teal`, `red`, `crimson`) or rely on their outline. `palette_visibility()` in sciforge_style encodes this split.

## Layer 2 — Data-Encoding Colormaps (Continuous Scalar Fields)

For **continuous scalar fields** (heatmaps, 3D surfaces, contour plots, correlation matrices), use perceptually-uniform colormaps — NEVER the categorical dopamine palette. See [`color-themes.md`](../../shared-references/color-themes.md) Layer 2 for the full contract.

| Discipline (OSS — always `general`) | Colormap | Why |
|--------------------------------------|----------|-----|
| `general` (universal default) | `viridis` | Conservative, perceptually uniform, CB-safe |
| Physics-flavored problems (field plots, EM maps) | `viridis` or `magma` | Perceptually uniform; required by PRL/PRB-style figures |
| CS/ML-flavored problems (attention maps, loss surfaces) | `viridis` | Perceptually uniform, CB-safe |
| Math-flavored problems (function plots, convergence heatmaps) | `viridis` or `plasma` | Perceptually uniform |

**NEVER use**: `jet`, `rainbow`, `hsv`, `coolwarm`, `bwr` — they create artificial visual boundaries and are not perceptually uniform.

**The two-layer rule**: dopamine (Layer 1) for categorical/semantic colors (series, groups, annotations); viridis/magma/cividis (Layer 2) for continuous scalar fields (heatmaps, surfaces). Never mix — a heatmap with categorical colors is wrong (they are not perceptually uniform); a line chart with viridis colors is wrong (viridis is for continuous fields, not categorical series).

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

Based on `renderer` config (default `auto`) — v3.5 routing per [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §4. **Every diagram goes through the single unified CLI `scripts/plotting/render_figure.py`** (one entry point — never invoke raw `d2`/`dot`/`rsvg-convert` in parallel):
- **Data plot** (line/scatter/bar/heatmap/3D/etc.) → Python pipeline (matplotlib/numpy, `apply_matplotlib_style()` at top) → **output BOTH `output.pdf` AND `output.svg`**
- **Diagram plot** (architecture/workflow/topology, 5+ nodes) → write `spec.d2` → `render_figure.py spec.d2` (auto-selects dagre; elk for >20 nodes) → dual PDF+SVG + audit
- **Diagram plot** (≤4 nodes, trivial) → AI-direct `source.svg` → `render_figure.py source.svg --engine svg` → dual output + audit (LAST resort)
- **Commutative/category diagram** → `spec.tex` (tikz/tikz-cd) → `render_figure.py spec.tex` (pdflatex → PDF → PNG)
- **Concept-map/dependency-graph** (5+ nodes) → d2 via unified CLI
- **Composite multi-panel** (4/6/N panels, Nature-style (a)(b)(c) labels) → `render_figure.py xxx.composite.json` (contract §7; panel cap 9, narrative-unit grouping)
- **Humanities** (timeline/argument-flow/comparison) → d2 via unified CLI (same as STEM diagrams)
- **Fallback chain** if d2 unavailable: `render_figure.py spec.dot` (graphviz engine); if graphviz unavailable, AI-direct SVG for ≤4 nodes only; for 5+ node diagrams with no d2/graphviz, BLOCK (do not produce a small-text AI-direct figure).

### Step 3a: Python Pipeline (for Data Plots)

Write the complete Python render script (`render.py`):
1. Import matplotlib, numpy, and other required libraries
2. Set theme from config (fonts, colors, grid style) — **enforce the dopamine palette**
3. Read data from `input_data.json`
4. Render the specified chart type
5. Apply labels, title, legend, and annotations
6. **Save BOTH `output.pdf` AND `output.svg`** (v2.2: dual output non-negotiable — PDF for LaTeX, SVG for viewing/editing)
7. Set random seed for reproducibility
8. **Set `figsize` to the physical width the figure will occupy in the paper** (print-size contract, v2.2): use `sciforge_style.figsize_full()` for a full-textwidth figure, `figsize_single()` for a single column, `figsize_panel(cols)` for one panel of a composite. Do NOT render a large figure (e.g. `(8,4.5)`) and then shrink one panel of it to ~2in — that is exactly the "tiny unreadable fonts" failure. Aspect stays ~16:9 for full-width, taller for single-column.

**Code quality rules (v2.2 print contract — Nature-level floor per [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §3)**:
- Every axis must carry unit annotation (e.g., "Time (s)", "Energy (eV)")
- **All text is pure black `#000000` on a pure white `#FFFFFF` ground** (no grey/brown ink, no off-white science-style background)
- **Font sizes meet the print floor AT FINAL EMBEDDED SCALE**: axis labels ≥ 16pt, tick labels ≥ 13pt, legend ≥ 13pt, title ≥ 18pt, annotations ≥ 12pt
- **Line widths**: primary ≥ 1.8pt, secondary ≥ 1.0pt
- **Marker size**: ≥ 7pt
- **Experiment-plot aesthetic (v2.3, mirrors the 640.png reference)**: use the `sciforge_style` helpers — `series_style(i)` for distinct (color,marker) per series; `add_error_band(ax,x,mean,std,color)` to shade ±std/CI whenever ≥2 seeds exist (a single line with no band looks cheap); `legend_top(ax)` for a frameless horizontal legend ABOVE the axes; `set_xscale("log")` when the x variable spans orders of magnitude; keep only subtle horizontal gridlines (the style default) and drop top/right spines. Prefer line+band over a bare 2-bar chart.
- Legend must not overlap data
- every theme uses the dopamine design tokens (NEVER tab10/Set2/arbitrary Tailwind hexes)
- For continuous scalar fields (heatmap/surface/contour), use viridis/magma/plasma (NEVER jet/rainbow/hsv)
- No interactive elements
- No text clipped at figure edges; ≥ 2pt gap between subpanels

### Step 3b: d2 Pipeline via the Unified Renderer (for Complex Diagrams — v3.5)

For architecture/workflow/topology/concept-map/dependency-graph/humanities-timeline diagrams with 5+ nodes, use **d2** through the single unified CLI:

1. Write `spec.d2` (d2's declarative DSL — see https://d2lang.com). Use dopamine tokens for any explicit fills (the renderer injects a design-system preamble for everything you leave unstyled):
```d2
direction: right
Input: {shape: rectangle; style.fill: "#EDE9E2"; style.stroke: "#6E675F"}
Process: {shape: oval; style.fill: "#A4B294"}
Output: {shape: rectangle; style.fill: "#BDA5A7"}
Input -> Process: "feeds"
Process -> Output: "produces"
```
2. Render via the **single entry point** (preamble injection → d2 layout → palette sanitization → PDF+SVG dual output → embedded Nature-level audit all happen inside):
```bash
python scripts/plotting/render_figure.py spec.d2 \
    --out figures/{figure_name}/ --label {figure_name} \
    --caption "..." --strict
```
3. Check the printed `[audit: PASS|WARN|FAIL]` verdict (also written to `figure_audit.json`). FAIL means re-fix the spec and re-render — do not deliver.
4. **Palette enforcement**: all `style.fill`/`style.stroke` in the `.d2` spec MUST be design tokens — the renderer rejects off-palette specs (exit 2). Engine-injected theme colors are deterministically remapped to tokens before delivery.
5. The CLI preserves `spec.d2` + `intermediate.svg` + `render.log` in the figure dir as the reproducible source (equivalent to `render.py` for data plots).

**d2 readability**: the injected preamble sets node font-size 22px / edge 18px (≈12.7pt/10.4pt physical at 16:9 embed width — above the Nature floor) and Liberation Sans (Helvetica-metric) via d2's `--font-*` flags. The audit verifies physical text size ≥ the diagram-node floor (14pt).

### Step 3c: AI-Direct SVG (≤4-node trivial ONLY — v3.5 demoted)

Hand-write a minimal SVG only when the diagram has ≤ 4 nodes and no auto-layout is needed. Deliver it through the unified CLI (`--engine svg`) so dual output + audit still apply:
```svg
<svg width="800" height="450" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect x="0" y="0" width="800" height="450" fill="#FFFFFF"/>
  <rect x="80" y="160" width="200" height="90" rx="8" fill="#EDE9E2" stroke="#6E675F" stroke-width="1.5"/>
  <text x="180" y="212" text-anchor="middle" font-family="TeX Gyre Heros, sans-serif" font-size="22" fill="#000000">Input</text>
  <line x1="280" y1="205" x2="520" y2="205" stroke="#665F57" stroke-width="2"/>
  <rect x="520" y="160" width="200" height="90" rx="8" fill="#8AA1BC" stroke="#6E675F" stroke-width="1.5"/>
  <text x="620" y="212" text-anchor="middle" font-family="TeX Gyre Heros, sans-serif" font-size="22" fill="#000000">Output</text>
</svg>
```

**Palette enforcement**: all `fill` and `stroke` colors in the SVG MUST be design tokens (Layer 1). The agent must NOT use arbitrary Tailwind/Material/matplotlib-default colors; the unified CLI audits the SVG and rejects off-palette hexes (exit 2).

**Preserved spec**: run the SVG through `render_figure.py source.svg --engine svg` so the source, `intermediate.svg`, and audit report are preserved beside `output.pdf`/`output.svg`.

### Step 3d: Premium Overview / Figure-1 Recipe (v2.3 — the "not cheap" bar)

Method/architecture overview figures must reach the quality of a top-venue
Figure 1 (reference: numbered-stage, icon-rich, nested-container overview). A
two-box diagram is a FAIL of the richness bar. Compose with:
1. **3-4 numbered stages** left→right: circular number badge (dopamine fill, black
   numeral) + bold stage title.
2. **Semantic color-block containers** per stage; use **nested rounded rectangles**
   to show hierarchy/ladders (e.g. T0⊂T1…); each block a surface design token.
3. **Icon vocabulary** (table / scatter-cloud / network / document / robot / gauge /
   clock / target): pull CC0 icons at runtime (bioicons/Tabler/Lucide) and recolor via
   `sciforge_style.recolor_icon()`, or hand-draw simple glyphs in the palette.
4. **Metric glyphs panel** (gauge/clock/target rows) for build/query cost & accuracy.
5. **Dashed callout box** for the headline numbers; **single-trunk flow arrows** with
   ≤1 crossing (dense → `--layout elk`).
6. Black text on pure white; all fills on-palette; deliver via `--engine svg` (or
   `diagrams`) so dual output + audit apply. The A7/A8 audits then verify icon/depth
   richness; a flat boxes-only overview WARNs and must be upgraded.

### Step 4: Render and Validate

Execute the render (Python subprocess for data plots; unified CLI for diagrams):
1. Create figure directory: `figures/{figure_name}/`
2. Write `input_data.json` + `render.py` (data) or `spec.d2` / `spec.tex` / `source.svg` (diagram)
3. Execute: `python render.py` OR `python scripts/plotting/render_figure.py <spec> --out figures/{figure_name}/ --label {figure_name} --strict`
4. Validate output (the unified CLI does this internally; data plots must be checked the same way):
   - `output.pdf` + `output.svg` exist, non-empty, valid magic bytes
   - SVG viewBox width ≥ 1200px (or the --width-preset floor) — vector, dpi-free
   - **Color audit**: every saturated color is a design token (dopamine v3.0: C* ≥ 30, CVD ΔE ≥ 15 pairwise, contrast-net) or a Layer-2 colormap — the CLI's embedded audit writes `figure_audit.json` with verdict PASS/WARN/FAIL
   - **Typography audit**: physical text size ≥ Nature floor (10pt diagram labels)
5. Auto-generate caption from chart type + data description (the CLI writes `latex_include.tex` with the caption)
5b. **Caption discipline (v1.7.1 — PaperOrchestra plotting contract, [`paper-voice-contract.md`](../../shared-references/paper-voice-contract.md) §4)**: the caption is written AFTER the final render, never before (a caption describing a figure that since changed is a visual lie); it must match what the image ACTUALLY shows — re-open the rendered figure and delete any interpretive clause the pixels do not support; it must define every error bar/band (±1 SD? 95% CI? over seeds?); it must not contain the literal word "Figure"/"Table" (LaTeX supplies the number) nor markdown; and it describes the SCIENCE, never the pipeline (no palette/renderer/aspect mentions). Figures and tables sit before the Conclusion.

### Step 4.5: Visual Self-Review (v3.9 — mandatory for vision-capable agents)

Per [`figure-quality-review.md`](../../shared-references/figure-quality-review.md):
1. **Detect capability**: can the host agent read an image file? Vision-native (class V) ⇒ Tier 1 mandatory; text-only (class T) ⇒ record `visual-review: skipped-text-only` in `revision_log.md` and proceed on the mechanical audit.
2. **Inspect the SVG** (it exists exactly for this; PDF is for LaTeX): open `figures/{figure_name}/output.svg` and walk the 9-item visual checklist (message / hierarchy / balance / wiring legibility / typography scan / color discipline / icon quality / composite-specific / print-shrink test). Write one-line answers per item into `revision_log.md` — "looks fine" is not an answer.
3. **Fix at source**: every concern becomes a concrete edit to the spec/render script, re-render, re-inspect — one issue class per pass (contract §4.6 scoped revision); 3 failed passes on one concern ⇒ re-layout from skeleton.
4. **Deliver** only when the checklist is satisfied AND the mechanical audit is not FAIL. Optional Tier 2 external advisor: one minimal-prompt call per version max, advisory only, never a gate.

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
- **Path (SVG)**: `figures/{figure_name}/output.svg` (viewing / later manual editing)
- **Aspect**: 16:9 (default) / [override + reason]
- **Caption**: {auto-generated caption}
- **Data/Source**: `figures/{figure_name}/input_data.json` (data) OR `spec.d2` (d2) OR `spec.md` (AI-direct)
- **Script**: `figures/{figure_name}/render.py` (Python) OR `figures/{figure_name}/spec.d2` (d2) OR `source.md` (AI-direct)
- **Palette**: dopamine (Layer 1, CVD-verified) / viridis·magma·cividis (Layer 2)
- **Readability**: Nature print floor verified (axis ≥16pt, ticks ≥13pt)
```

### Step 6.5: Update the verdict mirror (v5.3 — FIGURE_AUDITS.json)

After every figure render/re-render, update the machine-readable mirror `.sciforge/verdicts/FIGURE_AUDITS.json` so downstream skills can check all figure audits with one flat read (the per-figure detail stays in `figures/{figure_name}/figure_audit.json`):

```json
{
  "schema_version": "1.0",
  "generated_at": "<UTC ISO-8601, time of this update>",
  "figures": {
    "{figure_name}": {
      "verdict": "PASS | WARN | FAIL (from figure_audit.json)",
      "audit_file": "figures/{figure_name}/figure_audit.json"
    }
  }
}
```

Semantics: read the existing mirror (if present), upsert this figure's entry, rewrite the file. A figure re-rendered after fixes overwrites its own entry. Consumers (`/paper-writing`, `/paper-compile`) gate on it: any entry at FAIL blocks figure inclusion until fixed. Contract: [`artifact-registry.md`](../../shared-references/artifact-registry.md) row `.sciforge/verdicts/FIGURE_AUDITS.json`; schema: [`schemas/FIGURE_AUDITS.schema.json`](../../shared-references/schemas/FIGURE_AUDITS.schema.json).

## Required Workspace

- `figures/` — output PDF + SVG files (dual output, v4.0)
- `figures/{figure_name}/` — per-figure directory with `output.pdf` + `output.svg` + preserved source
- `figures/{figure_name}/render.py` (Python data) OR `spec.d2` (d2 diagrams) OR `source.md` (AI-direct ≤4 nodes) — preserved source for reproducibility
- `figures/{figure_name}/input_data.json` (Python data) — preserved input data
- `figures/FIGURE_INDEX.md` — all generated figures index

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)
> - **[Figure Layout Contract](../../shared-references/figure-layout-contract.md)** — 排版宪法: figure contract, evidence roles, page archetypes, panel alignment (A11), sizing ratio, construction order
> - **[Figure Quality Contract](../../shared-references/figure-quality-contract.md)** — dual output, 16:9 default, Nature readability floor, d2 pipeline
> - **[Unified Plot Theme (v3.1)](../../shared-references/figure-quality-contract.md)** — unified enforcement: data plots follow the academic theme (TeX Gyre academic fonts, Nature palette, font-size floors title≥13/axis≥12/tick≥10, 16:9 default), figures saved with vector PDF + SVG dual output; architecture/flow diagrams are mandatorily rendered via d2 / graphviz declarative rendering (d2→SVG→PDF+SVG); freehand SVG is forbidden (>4 nodes). Data plots must not be hand-written with scattered ad-hoc styles — they must follow the unified theme contract.
> - **[Figure Quality Review](../../shared-references/figure-quality-review.md)** — two-tier visual review protocol (Tier 1: agent-native visual self-review, MANDATORY for vision-capable hosts — read `output.svg` against the 9-item checklist; Tier 2: optional external advisor; text-only hosts degrade to the mechanical audit and record `skipped-text-only`)

## Boundaries

- **Dual output (PDF + SVG) is non-negotiable.** A figure with only one format is INCOMPLETE — re-render. PDF is the only format embedded in LaTeX; PNG is for AI/human viewing.
- **16:9 horizontal is the default.** A non-16:9 figure requires an explicit `aspect_ratio` override + documented reason.
- **Nature readability floor is enforced.** The Step 4 audit rejects any figure with text below the floor (axis <12pt, ticks <10pt, legend <10pt). The old 10pt/8pt floor produced too-small text.
- **The dopamine palette is non-negotiable for categorical/semantic colors** (v3.0). NEVER use off-palette Tailwind/Material/matplotlib-default/tab10/Set2 colors — vividness alone is not the test; membership in the CVD-verified design tokens is. The color audit in Step 4 rejects off-palette colors.
- **Layer 2 colormaps (viridis/magma/plasma) are mandatory for continuous scalar fields.** NEVER use jet/rainbow/hsv/coolwarm/bwr.
- **Python pipeline is mandatory for data plots.** Reproducibility requires preserved render script + input data. Do NOT AI-direct-generate a data plot (the numbers must come from the actual data, not AI memory).
- **d2 is the preferred tool for complex diagrams (5+ nodes).** AI-direct SVG is demoted to ≤4-node trivial diagrams ONLY. For 5+ node architecture/flow/topology/humanities diagrams, d2 (or graphviz fallback) is mandatory — AI-direct SVG produces small-text, poor-layout, non-Nature figures. If d2 AND graphviz are both unavailable, BLOCK 5+ node diagrams (do not produce a low-quality AI-direct figure).
- **SVG is the viewing/editing deliverable but is NEVER embedded in LaTeX.** Engines produce SVG; the unified CLI derives the PDF for `\includegraphics` and keeps the SVG for agent review and later manual editing.
- **Every figure preserves its source** (`render.py` + `input_data.json` for data; `spec.d2` for d2; `source.md` for AI-direct). No figure is "just a PDF" — the source is part of the output.

## Figure Budget Contract (v3.4 — per-section minimums, consumed by `/paper-writing`)

> **Why this exists (honest gap)**: two real test runs produced **2 figures** (Q-HARM-001) and **5 figures** (Q-SGD-BS-GAP), ALL crammed into the Results section. A Zone-1 SCI paper has **4-8 figures distributed across sections** — an Introduction problem/motivation figure, a Methods/architecture diagram, 2-4 Results panels, often a Discussion/limitations figure. The "1-2 figures is enough" failure made the papers look thin and broke the "figures aid understanding at every section" SCI norm. This contract sets per-section minimums that `/paper-writing` Step 1 (Plan Structure) consumes when planning the figure budget.

**Per-section figure budget (minimum — a paper may exceed)**:

| Section | Min figures | Typical figure type | Rationale |
|---------|-------------|---------------------|-----------|
| **Introduction** | 0-1 | Problem illustration / motivation figure / frontier-gap map (d2 concept-map or 1-panel data teaser) | Optional (v1.7.1): the mandated set is Related-Work map + Methods diagram + 5-8 experiment figures; an Intro teaser adds orientation when the problem is visual |
| **Related Work** | 1 | **Challenge-vs-ours map (v1.7.1 mandate)**: prior-work landscape × the challenge each line leaves open × where our method sits (taxonomy tree / method-comparison matrix / challenge map) | A Related Work with a visual challenge map reads as a positioned contribution, not a literature dump |
| **Problem Formalization** | 0-1 | Formal setup illustration (variable-dependency graph, problem-schema diagram) | Optional but valuable for complex formalizations |
| **Methods / Architecture** | 1 | **Pipeline / architecture diagram (MANDATORY)** — d2 layered/hub-and-spoke/flow showing the method's components + data flow | A Methods section with zero architecture diagram is the single strongest "thin paper" signal; every Zone-1 paper has one |
| **Theory / Derivation** | 0-1 | Commutative diagram / derivation tree / dependency graph (tikz-cd or d2) | Optional for theory-heavy papers; valuable when proof structure is non-trivial |
| **Results** | 5-8 | Experimental evidence: primary curves + comparisons + ablation + sensitivity/robustness + mechanism probes (data plots, composites count as 1) | v1.7.1 (user mandate): the experiment-figure band is 5-8; **type diversity is hard** — ≥3 distinct visual grammars across the paper (bars AND lines AND scatter/heatmap/forest/…); a run of identical bar charts is the basic-figure failure class, enforced by `scripts/figure_style_gate.py` |
| **Discussion** | 0-1 | Limitations illustration / future-work roadmap / robustness summary | Optional; a robustness/sensitivity summary figure strengthens the Discussion |
| **Appendix** | 0+ | Extended tables, full grid results, supplementary plots | Unlimited; appendix figures are not counted in the body budget |

**Total body minimum (excl. appendix)**: **7 figures** (1 Related-Work challenge map + 1 Methods/architecture + 5 experiment figures; an Intro motivation figure is optional and adds to the band, upper end 5-8 experiment figures ⇒ 7-10 body figures). Fewer than 7 body figures is `WARN` (`figure_budget: below_minimum`); fewer than 5 is `FAIL` — it cannot support a Zone-1 submission regardless of text quality. **All data figures are landscape 16:9 vector (PDF) by default; raster embeds in the body are a gate FAIL; every figure's first citation precedes its float** (`scripts/figure_style_gate.py` enforces all three).

**Composite counting**: a single composite figure with 4 panels (a/b/c/d) counts as **1 figure** for budget purposes but provides 4 visual units — this is the preferred way to pack rich content without inflating the figure count past the page budget. The Results section's "2-4 figures" minimum is best met as 2 composites × 2-3 panels each.

**Architecture-diagram mandate (v3.4)**: every paper's Methods/Architecture section MUST contain at least one d2 (or graphviz) pipeline/architecture diagram showing the method's components and data flow. A Methods section with only equations and text — no architecture diagram — is the strongest "thin paper / desk-reject-risk" signal. This is a HARD requirement: `figure_budget.architecture_diagram_present` must be `true` in `FIGURE_INDEX.md`, or `/paper-writing` Step 5 self-review emits `FAIL, reason_code: missing_architecture_diagram`.

**How `/paper-writing` consumes this**: at Step 1 (Plan Structure), the agent reads this budget, plans which figures go in which section, writes the plan to `PAPER_PLAN.md`'s figure-budget row, then at Step 2 (Write Each Section) requests each planned figure from `/unified-plotting`. A section that ends up with fewer figures than its minimum is `WARN` unless the mode (e.g. `theory` with no Methods section) makes it not-applicable — in which case the minimum is recalculated per the mode's section set (see [`paper-modes.md`](../../shared-references/paper-modes.md) §3).
- **Humanities/arts figures use the same pipeline and quality floor as STEM.** A history timeline, argument map, or hermeneutic diagram must meet the same Nature readability, 16:9 default, dual output, and dopamine palette as a physics curve. No humanities quality deviation.
- **No discipline-specific enforcement.** Do not reintroduce physics SI-units enforcement or cs-ml benchmark-plot conventions. The universal dopamine + Layer 2 + dual-output + 16:9 contract applies to every problem.
- **`theme: modern` is prohibited.** Override to `theme: academic` and log a warning if requested.

## Output Shape

The final output is (v2.2 — dual output):
1. `figures/{figure_name}/output.pdf` — vector PDF (LaTeX-embedded, the only format in the compiled paper)
2. `figures/{figure_name}/output.svg` — vector SVG (agent viewing + later manual editing; NEVER embedded in LaTeX)
3. `figures/{figure_name}/render.py` (Python data) OR `spec.d2` (d2 diagrams) OR `source.md` (AI-direct ≤4 nodes) — preserved source for reproducibility
4. `figures/{figure_name}/input_data.json` (Python pipeline) — preserved input data
5. `figures/{figure_name}/latex_include.tex` — LaTeX include snippet (`\includegraphics{output.pdf}`)
6. `figures/FIGURE_INDEX.md` — all generated figures index (appended)

(SVG is the viewing/editing deliverable and the PDF source; LaTeX embeds the PDF only — `\includegraphics{output.pdf}`, never the SVG.)

## Composing With Other Skills

```
/theory-derivation (produces results that need visualization)
    → /unified-plotting               ← you are here
        → /paper-writing (consumes the latex_include.tex snippets)
```

## See Also

- [`../shared-references/color-themes.md`](../../shared-references/color-themes.md) — dopamine palette (Layer 1, CVD-verified) + viridis/magma/cividis data colormaps (Layer 2)
- [`../shared-references/writing-principles.md`](../../shared-references/writing-principles.md) — figure caption style
- [`../shared-references/output-manifest.md`](../../shared-references/output-manifest.md) — product structure contract
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
