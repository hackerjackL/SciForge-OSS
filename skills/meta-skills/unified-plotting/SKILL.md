---
name: unified-plotting
version: 1.2.0
description: "Render publication-quality vector figures (PDF+PNG) from data or JSON specs — 12 chart types incl. v3.4 Composite/Group (subfigure-grid, panel-2x2, inset-zoom), Morandi palette + viridis/magma colormaps, 16:9 default, Nature readability floor. v3.5 UNIFIED SINGLE-ENTRY RENDERER: all diagram engines (d2/graphviz/tikz/SVG) consolidated behind one tool `scripts/plotting/render_figure.py` with embedded Nature-level audit. v3.4 Figure Budget Contract sets per-section minimums (Intro≥1, Methods≥1 architecture diagram MANDATORY, Results 2-4) consumed by paper-writing. Phase 11. Invoke when the paper needs figures."
type: meta-skill
role: figure-renderer-and-spec-generator
---

# Unified Plotting (SciForge-OSS — Merged figure-spec + paper-figure, Morandi-Enforced)

## Quick Reference

- **Purpose**: 从结构化数据或 JSON spec 渲染出版级矢量图
- **Input**: 数据 (JSON/matrix) 或图表描述
- **Output**: **PDF + PNG 双产出** (PDF for LaTeX compile, PNG for AI/human viewing) + 渲染脚本 + `figure_audit.json`
- **Key**: 12 种图表类型 (含 4 种理论图)；莫兰迪色系强制（单一事实源 `scripts/plotting/sciforge_style.py`）；数据图 Python 管线，复杂图**统一渲染工具**；**16:9 横版默认**；**Nature 级可读性**；见 [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md)（格式）与 [`figure-complexity-contract.md`](../../shared-references/figure-complexity-contract.md)（复杂与美观下限）

> **v3.5 单一入口工具（UNIFIED SINGLE-ENTRY RENDERER）**: 所有声明式图（d2 / graphviz / tikz / AI-direct SVG）只通过**一个** CLI 产出，禁止多工具并行或绕过：
>
> ```bash
> python scripts/plotting/render_figure.py <spec.d2|spec.dot|spec.tex|source.svg> \
>     --out figures/{figure_name}/ --label {figure_name} \
>     --caption "..." --strict
> ```
>
> 该工具内部自动完成：莫兰迪前导注入（d2）→ 引擎渲染（d2 自动选 dagre/elk）→ 引擎泄漏色确定性净化 → SVG→PDF+PNG 双产出（300 DPI）→ LaTeX include 片段 → 内嵌 Nature 级审计（`figure_audit.json`，verdict PASS/WARN/FAIL；`--strict` 时 FAIL 退出码 4）。数据图仍走 Python 管线（可复现性要求），但必须在脚本顶部调用 `apply_matplotlib_style()` 统一主题。依赖安装见 [`scripts/plotting/INSTALL.md`](../../../scripts/plotting/INSTALL.md)，环境自检：`python scripts/plotting/render_figure.py --doctor`。
>
> **v3.7 三项增强**: (1) **期刊宽度预设** `--width-preset nature-single|nature-double|aaai-single|...`（14 种版面，LaTeX include 自动用 mm 物理宽度，审计宽度下限自适应，见 [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §1.5）；(2) **运行时图标词汇**——可从白名单开源库（bioicons/Tabler/Lucide/Feather/Font Awesome Free）运行时抓取专业图标，强制经 `sciforge_style.recolor_icon()` 重着色为莫兰迪后使用，来源许可记入 `revision_log.md`（契约 §5.5；抓取失败回退手绘，不阻塞）；(3) **审计自动修正建议**——`figure_audit.json` 的 `suggested_fixes` 字段对文字重叠输出精确偏移坐标（"move label X down by Npx"），按契约 §4.6 scoped revision 逐条应用。
>
> **v3.8 组图引擎（Composite — SCI 一区规范，契约 §7）**: 多面板组图（4/6/N 面板）经 `render_figure.py xxx.composite.json` 单一入口装配：面板（PDF/PNG）→ 网格排布 → **(a)(b)(c)… 加粗编号标签**（面板上方预留条，绝不覆盖内容）→ 双产出 + 审计。**组版决策遵循 Nature/Science/Cell 逻辑**：按叙事单元组版（同一论点/实验链才组一张）、面板数**硬上限 9**（超出渲染器直接拒绝，必须拆图或移补充材料——"一锅粥"反模式）、单图同样合法、编号随面板数连续自适应。每个面板必须**独立**满足全部审计与复杂度规则——组图装配不能拯救低质量面板。数据图（曲线/消融/热图等）作为面板融入组图，与示意图面板同图共存时风格统一（同系字体/色序/线宽）。

> **Agent 驱动分阶段设计工作流（借鉴 AutoFigure-Edit 的分阶段装配思想，MIT 许可；本 skill 零外部 API——"模型"就是 agent 自身，用户用自己的 Claude/Codex/AtomCode 开箱即用）**:
> 1. **骨架（skeleton）**: 从方法段落文本抽取组件清单 + 数据流 + 分组层级，先写布局骨架（容器/行列/边），不急着画
> 2. **填充（fill）**: 按内容类型选引擎——架构/流程用 d2 或 diagrams/blockdiag（专业图标集/泳道），机制细节用 tikz，几何/示意用 asy，快速迭代用 typst，Visio 级精密图用手工装配 SVG（正交圆角布线），数据用 matplotlib；每个组件填莫兰迪 token 样式
> 3. **装配（assemble）**: 全部经单一入口 `render_figure.py` 渲染（前导注入、调色板净化、双产出、LaTeX 片段一步完成）
> 4. **审阅（review）**: 看 `figure_audit.json` verdict 与 `suggested_fixes`；FAIL 时按 suggested_fixes 的精确坐标逐条局部修正（契约 §4.6 scoped revision，一次一类问题）再重渲染——禁止手工修补 PNG/SVG 像素
>
> **复杂度硬约束（v3.6 — 防"小学生级别"图，全领域适用）**: 每张 5+ 节点的图必须满足 [`figure-complexity-contract.md`](../../shared-references/figure-complexity-contract.md)：≥60% 组件用**自绘图标**（d2 `icon:`，agent 现写 SVG，随图保存到 `figures/<name>/icons/`）或 TikZ `\pic` 自绘组件；连线必须容器级汇流（禁止箭头雨，边密度 ≤1.6）；至少两级分组；文字纪律（≤3 行/≤4 词）。达不到下限 = 图还没画完，继续迭代。审计 A7 层机械检查图标计数与边密度。先按契约 §0.5 判定图的**结构角色**（结构/流程/机制/网络/层级/时间/空间/数据）选引擎——领域只决定组件语义，不改变规则。

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

**Not for**: format conversion (format conversion is done inline within this skill in OSS; no `/drawio-export`).

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
| **Composite / Group** (v3.4 — NEW) | subfigure-grid, panel-2x2, panel-1x3, panel-2x3, inset-zoom, dual-axis | Multi-panel figures (a/b/c/d panels sharing one caption), grouped result comparisons, inset detail + overview | Python (`matplotlib` `subplots`/`gridspec`) for data panels OR d2 multi-graph for diagram panels → **single composite PDF+PNG**; LaTeX side: `\usepackage{subcaption}` + `\begin{figure}\subfloat{...}\subfloat{...}\end{figure}` OR single rendered PDF embedded with panel labels (a/b/c) baked into the image |

**Pipeline rule** (v2.2 — see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md)):
- **Data plots** (Relation/Comparison/Distribution/Composition/Correlation/3D Surface/Scientific) → Python pipeline mandatory (matplotlib/numpy), render script + input data preserved, **output BOTH `output.pdf` AND `output.png`** (PDF for LaTeX, PNG for viewing)
- **Diagram plots** (Topology + Architecture) → **d2** (`.d2` spec → SVG intermediate → `rsvg-convert`/`inkscape` → PDF+PNG). AI-direct SVG demoted to ≤4-node trivial only. For 5+ node diagrams, d2 (or graphviz fallback) is mandatory — AI-direct SVG produces small-text, poor-layout, non-Nature figures.
- **Theoretical plots** → LaTeX `tikz-cd` for commutative diagrams (PDF direct); **d2** for concept-maps/dependency-graphs (5+ nodes); AI-direct SVG for ≤4-node trivial. Reproducibility via the LaTeX source OR the `.d2` spec preserved.
- **Engineering Path / Humanities** → **d2** (timelines, argument maps, comparison structures → SVG → PDF+PNG). Same 16:9 default, dual output, Nature readability floor as STEM — no humanities quality deviation.
- **Composite / Group plots (v3.4 — NEW)** → two valid modes:
  1. **Pre-rendered composite** (preferred for data panels): Python `matplotlib.subplots`/`gridspec` renders all panels into ONE PDF+PNG with (a)/(b)/(c) labels baked in. LaTeX embeds the single PDF via `\includegraphics`. Caption uses Nature style: "Figure N. **a**, Description. **b**, Description. ...". Preserves ONE render.py + ONE input_data.json for the whole composite.
  2. **LaTeX `subcaption` composite** (preferred when panels are heterogeneous — e.g. a d2 architecture diagram + a data plot + a table): each panel is a separate PDF; LaTeX assembles via `\usepackage{subcaption}` + `\begin{figure}\subfloat[...]{\includegraphics{panel_a.pdf}}\subfloat[...]{\includegraphics{panel_b.pdf}}\end{figure}`. The `subcaption` package MUST be loaded in the unified skeleton's preamble (add to `math_commands.tex` or `main.tex` preamble: `\usepackage{subcaption}`).
  - **Panel label rule**: every subpanel gets a bold lowercase letter label **(a)**, **(b)**, **(c)**... — either baked into the image (mode 1) or via `\subfloat`'s caption (mode 2). Never unlabeled panels.
  - **Gap rule** (from figure-quality-contract): ≥ 2pt gap between subpanels; no cramped layouts.
  - **Caption self-contained**: the composite caption explains ALL panels — a reader should understand the figure without reading the body text.
  - **Dual output for composites**: the composite produces `output.pdf` (LaTeX-embeddable) AND `output.png` (viewable) regardless of mode. For mode 2 (LaTeX subcaption), the composite PNG is a rendered preview of the assembled figure (the agent renders it once for review).
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
| `format` | enum | `pdf+png` | v2.2: default `pdf+png` (was `svg`). PDF for LaTeX compile (only format embedded), PNG for AI/human viewing. `svg` is intermediate-only. |
| `theme` | enum | `academic` | `academic` (serif, restrained), `modern` (sans-serif, vivid — **NEVER use**, violates morandi), `monochrome` (grayscale, print-friendly) |
| `width` | string | `8in` | Figure width (inches or cm) — v2.2: default raised for 16:9 wide figures |
| `height` | string | `4.5in` | Figure height — v2.2: default set for 16:9 ratio (8:4.5 = 16:9) |
| `aspect_ratio` | enum | `16:9` | v2.2: default `16:9` (Nature wide); `4:3`/`3:2`/`1:1` only when content demands (see [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §1) |
| `dpi` | int | `300` | Raster output resolution (PNG) |
| `color_scheme` | string | `morandi` | Palette — **default is `morandi`** (house default, chroma C* ≤ 25). See [`color-themes.md`](../../shared-references/color-themes.md). Switch to `colorblind-safe` only when the venue explicitly requires it OR the human user explicitly requests it. |
| `renderer` | enum | `auto` | `auto` (Python for data, d2 for diagrams, tikz-cd for commutative, AI-direct SVG ≤4 nodes only), `python`, `d2` (force d2 for diagrams), `graphviz` (force dot for graphs), `tikz` (LaTeX theoretical), `ai-direct` (force AI hand-written SVG — ≤4 nodes only, LAST resort) |

**Hard prohibition on `theme: modern`**: the modern theme uses high-saturation Tailwind colors that violate the morandi chroma C* ≤ 25 principle. If the user requests `theme: modern`, override to `theme: academic` and log a warning.

## Morandi Palette Contract (Layer 1 — Universal)

All categorical/semantic colors use the **morandi** house palette. The single source of truth is `scripts/plotting/sciforge_style.py` (`TOKENS`); the table below mirrors it. See [`color-themes.md`](../../shared-references/color-themes.md) for semantic-role mappings and legacy aliases.

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

**NEVER use**: Tailwind high-saturation (`#2563EB` / `#10B981` / `#7C3AED` / `#EA580C`), Material Design blue (`#1565C0` / `#0D47A1`), matplotlib defaults (`tab10` / `Set2`), jet / rainbow / hsv. These violate the morandi chroma C* ≤ 25 principle. The renderer rejects them at source level; engine-injected theme colors in SVG output are deterministically remapped to tokens (`sanitize_palette`) before delivery.

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

Based on `renderer` config (default `auto`) — v3.5 routing per [`figure-quality-contract.md`](../../shared-references/figure-quality-contract.md) §4. **Every diagram goes through the single unified CLI `scripts/plotting/render_figure.py`** (one entry point — never invoke raw `d2`/`dot`/`rsvg-convert` in parallel):
- **Data plot** (line/scatter/bar/heatmap/3D/etc.) → Python pipeline (matplotlib/numpy, `apply_matplotlib_style()` at top) → **output BOTH `output.pdf` AND `output.png`**
- **Diagram plot** (architecture/workflow/topology, 5+ nodes) → write `spec.d2` → `render_figure.py spec.d2` (auto-selects dagre; elk for >20 nodes) → dual PDF+PNG + audit
- **Diagram plot** (≤4 nodes, trivial) → AI-direct `source.svg` → `render_figure.py source.svg --engine svg` → dual output + audit (LAST resort)
- **Commutative/category diagram** → `spec.tex` (tikz/tikz-cd) → `render_figure.py spec.tex` (pdflatex → PDF → PNG)
- **Concept-map/dependency-graph** (5+ nodes) → d2 via unified CLI
- **Composite multi-panel** (4/6/N panels, Nature-style (a)(b)(c) labels) → `render_figure.py xxx.composite.json` (contract §7; panel cap 9, narrative-unit grouping)
- **Humanities** (timeline/argument-flow/comparison) → d2 via unified CLI (same as STEM diagrams)
- **Fallback chain** if d2 unavailable: `render_figure.py spec.dot` (graphviz engine); if graphviz unavailable, AI-direct SVG for ≤4 nodes only; for 5+ node diagrams with no d2/graphviz, BLOCK (do not produce a small-text AI-direct figure).

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

### Step 3b: d2 Pipeline via the Unified Renderer (for Complex Diagrams — v3.5)

For architecture/workflow/topology/concept-map/dependency-graph/humanities-timeline diagrams with 5+ nodes, use **d2** through the single unified CLI:

1. Write `spec.d2` (d2's declarative DSL — see https://d2lang.com). Use morandi tokens for any explicit fills (the renderer injects a morandi preamble for everything you leave unstyled):
```d2
direction: right
Input: {shape: rectangle; style.fill: "#EDE9E2"; style.stroke: "#6E675F"}
Process: {shape: oval; style.fill: "#A4B294"}
Output: {shape: rectangle; style.fill: "#BDA5A7"}
Input -> Process: "feeds"
Process -> Output: "produces"
```
2. Render via the **single entry point** (preamble injection → d2 layout → palette sanitization → PDF+PNG dual output → embedded Nature-level audit all happen inside):
```bash
python scripts/plotting/render_figure.py spec.d2 \
    --out figures/{figure_name}/ --label {figure_name} \
    --caption "..." --strict
```
3. Check the printed `[audit: PASS|WARN|FAIL]` verdict (also written to `figure_audit.json`). FAIL means re-fix the spec and re-render — do not deliver.
4. **Morandi enforcement**: all `style.fill`/`style.stroke` in the `.d2` spec MUST be morandi tokens — the renderer rejects off-palette specs (exit 2). Engine-injected theme colors are deterministically remapped to tokens before delivery.
5. The CLI preserves `spec.d2` + `intermediate.svg` + `render.log` in the figure dir as the reproducible source (equivalent to `render.py` for data plots).

**d2 readability**: the injected preamble sets node font-size 22px / edge 18px (≈12.7pt/10.4pt physical at 16:9 embed width — above the Nature floor) and Liberation Sans (Helvetica-metric) via d2's `--font-*` flags. The audit verifies physical text size ≥ 10pt.

### Step 3c: AI-Direct SVG (≤4-node trivial ONLY — v3.5 demoted)

Hand-write a minimal SVG only when the diagram has ≤ 4 nodes and no auto-layout is needed. Deliver it through the unified CLI (`--engine svg`) so dual output + audit still apply:
```svg
<svg width="800" height="450" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
  <rect x="0" y="0" width="800" height="450" fill="#FAF8F5"/>
  <rect x="80" y="160" width="200" height="90" rx="8" fill="#EDE9E2" stroke="#6E675F" stroke-width="1.5"/>
  <text x="180" y="212" text-anchor="middle" font-family="TeX Gyre Heros, sans-serif" font-size="22" fill="#3A3733">Input</text>
  <line x1="280" y1="205" x2="520" y2="205" stroke="#3A3733" stroke-width="2"/>
  <rect x="520" y="160" width="200" height="90" rx="8" fill="#93A7BB" stroke="#6E675F" stroke-width="1.5"/>
  <text x="620" y="212" text-anchor="middle" font-family="TeX Gyre Heros, sans-serif" font-size="22" fill="#3A3733">Output</text>
</svg>
```

**Morandi enforcement**: all `fill` and `stroke` colors in the SVG MUST be morandi tokens (Layer 1). The agent must NOT use Tailwind/Material/matplotlib-default colors; the unified CLI audits the SVG and rejects off-palette hexes (exit 2).

**Preserved spec**: run the SVG through `render_figure.py source.svg --engine svg` so the source, `intermediate.svg`, and audit report are preserved beside `output.pdf`/`output.png`.

### Step 4: Render and Validate

Execute the render (Python subprocess for data plots; unified CLI for diagrams):
1. Create figure directory: `figures/{figure_name}/`
2. Write `input_data.json` + `render.py` (data) or `spec.d2` / `spec.tex` / `source.svg` (diagram)
3. Execute: `python render.py` OR `python scripts/plotting/render_figure.py <spec> --out figures/{figure_name}/ --label {figure_name} --strict`
4. Validate output (the unified CLI does this internally; data plots must be checked the same way):
   - `output.pdf` + `output.png` exist, non-empty, valid magic bytes
   - PNG ≥ 300 DPI and ≥ 1200px wide (agent-reviewable)
   - **Color audit**: every saturated color is a morandi token (C* ≤ 25) or a Layer-2 colormap — the CLI's embedded audit writes `figure_audit.json` with verdict PASS/WARN/FAIL
   - **Typography audit**: physical text size ≥ Nature floor (10pt diagram labels)
5. Auto-generate caption from chart type + data description (the CLI writes `latex_include.tex` with the caption)

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
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)
> - **[Figure Quality Contract](../../shared-references/figure-quality-contract.md)** — dual output, 16:9 default, Nature readability floor, d2 pipeline
> - **[Unified Plot Theme (v3.1)](../../shared-references/figure-quality-contract.md)** — 统一强制：数据图按学术主题（DPI=300、Arial 或系统回退字体、Nature 调色板、字号下限 title≥13/axis≥12/tick≥10、16:9 默认）、图保存矢量 PDF + PNG 双产出；架构图/流程图强制 d2 / graphviz 声明式渲染（d2→SVG→PDF+PNG），禁用徒手 SVG（>4 节点）。数据图禁止直接手写散乱样式——必须遵循统一主题契约。
> - **[Figure Quality Review](../../shared-references/figure-quality-review.md)** — external LLM optimization advisor (optional) for top-tier architecture/DAG/academic diagrams: concrete improvement suggestions → re-render; advisory only, never a gate

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

## Figure Budget Contract (v3.4 — per-section minimums, consumed by `/paper-writing`)

> **Why this exists (honest gap)**: two real test runs produced **2 figures** (Q-HARM-001) and **5 figures** (Q-SGD-BS-GAP), ALL crammed into the Results section. A Zone-1 SCI paper has **4-8 figures distributed across sections** — an Introduction problem/motivation figure, a Methods/architecture diagram, 2-4 Results panels, often a Discussion/limitations figure. The "1-2 figures is enough" failure made the papers look thin and broke the "figures aid understanding at every section" SCI norm. This contract sets per-section minimums that `/paper-writing` Step 1 (Plan Structure) consumes when planning the figure budget.

**Per-section figure budget (minimum — a paper may exceed)**:

| Section | Min figures | Typical figure type | Rationale |
|---------|-------------|---------------------|-----------|
| **Introduction** | 1 | Problem illustration / motivation figure / frontier-gap map (d2 concept-map or 1-panel data teaser) | A Zone-1 Intro often opens with "Figure 1: the problem" — it orients the reader before any text |
| **Related Work** | 0-1 | Comparison table/diagram (taxonomy tree, method-comparison matrix) | Optional; a taxonomy diagram dramatically improves a survey-flavored Related Work |
| **Problem Formalization** | 0-1 | Formal setup illustration (variable-dependency graph, problem-schema diagram) | Optional but valuable for complex formalizations |
| **Methods / Architecture** | 1 | **Pipeline / architecture diagram (MANDATORY)** — d2 layered/hub-and-spoke/flow showing the method's components + data flow | A Methods section with zero architecture diagram is the single strongest "thin paper" signal; every Zone-1 paper has one |
| **Theory / Derivation** | 0-1 | Commutative diagram / derivation tree / dependency graph (tikz-cd or d2) | Optional for theory-heavy papers; valuable when proof structure is non-trivial |
| **Results** | 2-4 | Primary result curves + comparison/bar + ablation + sensitivity (data plots, may be composites) | The core evidence; 2-4 panels is the Zone-1 norm (1 is thin, 5+ risks overcrowding without composites) |
| **Discussion** | 0-1 | Limitations illustration / future-work roadmap / robustness summary | Optional; a robustness/sensitivity summary figure strengthens the Discussion |
| **Appendix** | 0+ | Extended tables, full grid results, supplementary plots | Unlimited; appendix figures are not counted in the body budget |

**Total body minimum (excl. appendix)**: **4 figures** (1 Intro + 1 Methods/architecture + 2 Results). A paper with fewer than 4 body figures is `WARN` (`figure_budget: below_minimum`). A paper with **only 1-2 figures total** is `FAIL` — it cannot support a Zone-1 submission regardless of text quality.

**Composite counting**: a single composite figure with 4 panels (a/b/c/d) counts as **1 figure** for budget purposes but provides 4 visual units — this is the preferred way to pack rich content without inflating the figure count past the page budget. The Results section's "2-4 figures" minimum is best met as 2 composites × 2-3 panels each.

**Architecture-diagram mandate (v3.4)**: every paper's Methods/Architecture section MUST contain at least one d2 (or graphviz) pipeline/architecture diagram showing the method's components and data flow. A Methods section with only equations and text — no architecture diagram — is the strongest "thin paper / desk-reject-risk" signal. This is a HARD requirement: `figure_budget.architecture_diagram_present` must be `true` in `FIGURE_INDEX.md`, or `/paper-writing` Step 5 self-review emits `FAIL, reason_code: missing_architecture_diagram`.

**How `/paper-writing` consumes this**: at Step 1 (Plan Structure), the agent reads this budget, plans which figures go in which section, writes the plan to `PAPER_PLAN.md`'s figure-budget row, then at Step 2 (Write Each Section) requests each planned figure from `/unified-plotting`. A section that ends up with fewer figures than its minimum is `WARN` unless the mode (e.g. `theory` with no Methods section) makes it not-applicable — in which case the minimum is recalculated per the mode's section set (see [`paper-modes.md`](../../shared-references/paper-modes.md) §3).
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
