# Figure Layout Contract (SciForge-OSS — Nature-grade 排版宪法)

> **Status (v1.0, 2026-09-27)**: This contract owns **composition and layout** — panel roles, page archetypes, geometry ratios, alignment tolerances, and sizing discipline. It is the missing layer between [`figure-quality-contract.md`](figure-quality-contract.md) (fonts/palette/formats) and [`figure-complexity-contract.md`](figure-complexity-contract.md) (richness/edges/anti-elementary). Audited mechanically by `figure_audit.py` (A11 panel-alignment layer) and enforced at spec time by `method_recipes.py` / `figure_recipes.py` layout presets.
>
> **Provenance (open-source, absorbed 2026-09)**: Yuan1z0825/nature-skills `nature-figure` (figure contract + multipanel evidence architecture + panel-alignment auditor, Apache-2.0 lineage), shuang-afk/research-figure-composer-skill (nature-skills-style-guide), Zhangyanbo/nature-style-skill (journal grid + point-scale type), 0xE1337/thesis-figure-skill (layout-by-construction + anti-AI-slop), ai4paper/apaper-plugin (block/tap-junction conventions), LawrenceRiver/FigFox-Gen-skill (human construction order), BAIKEMARK/happy-figure-skill (figure-type layout candidates), wbopan/paper-figure (shared-domain panel alignment).

## 0. Supreme rule

**The chart serves the scientific logic.** Aesthetic polish, template matching, and complex layout are subordinate to making the core conclusion clear, defensible, and reviewable. A figure is a **visual argument**, not a pretty plot. No figure starts from code or a favorite template — it starts from a claim.

---

## 1. The Five-Point Figure Contract (write BEFORE any code)

Every figure (single or composite) is specified with these five fields. `*.method.json` / `*.figure.json` / `*.composite.json` specs MUST carry them; the renderer rejects a spec missing `claim` and `archetype`:

1. **Core conclusion** — one sentence with a verb that the figure must defend. Not a topic ("BERT results"), a claim ("sparse attention matches dense accuracy at 40% of the FLOPs").
2. **Evidence chain** — map each panel to exactly one **inferential role** (table §2). Drop/merge/demote any panel that only redraws another panel's evidence under a secondary metric.
3. **Archetype** — one of: `quantitative-grid` | `schematic-led` | `image-plate` | `asymmetric-hero` (page archetypes §3).
4. **Backend/toolchain** — SciForge locks this: data plots = `figure_recipes.py` (matplotlib + `apply_matplotlib_style`); method diagrams = `method_recipes.py` (d2, L1–L5); composite = `render_figure.py` `.composite.json`. **No freestyle engines.** Single pipeline per figure.
5. **Export contract** — final physical width preset (`nature-single` 89mm / `nature-double` 183mm / …), 5pt glyph floor, editable text, source retained, alignment gate on, collision audit on.

**Necessity test for every panel** (run before drawing AND after final render):
1. What unique inference disappears if this panel is removed?
2. Does that inference establish, advance, qualify or bound the figure-level claim?
3. Is it a distinct evidence role, or the same result under another metric/estimator/seed/encoding?

Route: Main figure = decisive evidence / necessary control / central falsification / conclusion-changing boundary. Extended Data/SI = reassurance, provenance, secondary metrics. Another figure = a separate major claim. Delete = no independent inference gain.

---

## 2. Panel inferential roles (evidence hierarchy → visual hierarchy)

| Evidence role | Question it answers | Visual weight |
|---|---|---|
| Setup / schematic | What system/intervention/contrast is tested? | Hero if readers need it to interpret evidence; else quiet |
| Representative example | What does the phenomenon look like concretely? | Medium; must explain the aggregate, not decorate it |
| Primary quantitative evidence | Does the central effect exist? | **Hero position / largest area** |
| Baseline / control | Does it beat a credible alternative? | Quiet but judgeable |
| Decomposition | Which components account for the effect? | Medium |
| Stratification | Does it hold across meaningful conditions? | Medium |
| Orthogonal validation | Is it recovered with another assay/measure? | Quiet |
| Perturbation / stress test | Does it survive an attack? | Visible when it changes the claim |
| Boundary / failure case | Where does it weaken or stop? | **Never hide** — if it changes the claim it is main-figure material |
| Mechanistic evidence | What bounded explanation is supported? | Medium |

**Rules**:
- Panels are independently **necessary**, not independent stories. Covering one panel must remove a distinct inferential step the others cannot recover.
- Prefer **role diversity over metric diversity**. Weak mirror layout `a:R2 b:R2-pairwise c:MAPE d:MAPE-pairwise` = 2 roles, 4 panels → collapse. Stronger: `a:perturbation design → b:decisive comparison → c:full distribution/residual → d:decomposition/boundary`.
- Panel letters mark **reading order**, not function. `a` need not be a schematic; `d` need not be a stress test.
- One figure = one Results-level claim (strong default, not a rigid count). Subordinate findings allowed when all are needed for the same claim.
- Displaced material destination must be recorded: main | another figure | Extended Data/SI | delete.

### Evidence-chain archetypes (choose ONE per figure)

| Archetype | Chain | Use when |
|---|---|---|
| **Validation envelope** | define capability → establish → test failure modes → attack claim → bound | one system's credibility is under test |
| **Scale-to-instance** | global map/distribution → quantity → spatial relation → internal structure → representative exception | population pattern needs physical/biological interpretation |
| **Discovery sequence** | hypothesis → decisive experiment → analysis → refined hypothesis → next test | each result changes the next question |
| **Capability ladder** | what it is → what it learned → beats alternatives → survives harder conditions → broader ability | method paper with progressively stronger claims |
| **Reusable default** | establish → compare/control → stress-test/discriminate → broaden → bound | general fallback |

Across figures in a paper: each figure should ask a **deeper or different** question than the previous one. Two figures both summarizable as "X performs well" → merge, demote, or re-aim the later one.

---

## 3. Page archetypes (Nature 2026 corpus — LAYOUT LOCKED)

Classify the figure into exactly one archetype. The archetype fixes the **geometry ratios**; the model fills content only.

### 3.1 `schematic-led` (method/pipeline/architecture figures — THE default for Methods)

- Schematic occupies **45–60% of figure height** (hero band). Supporting quant panels below are smaller, cleaner, less saturated.
- **Same physical/material palette** in schematic and supporting plots — do not switch to generic method colors below the hero.
- Zoom callouts use ONE repeated accent family (e.g. a single dashed outline style) across the figure.
- Reserve ≥1 supporting panel for a real-world snapshot/photo when the story needs scale validation.
- Grid skeleton (locked): `gridspec(2, 4, height_ratios=[2.2, 1.0])`, hero spans `gs[0,:]`.

### 3.2 `asymmetric-hero` (mixed-modality / one central result)

- **Do not force equal panel sizes.** The scientifically central panel spans multiple rows/columns and dominates.
- Supporting plots answer narrower questions around the hero; keep them quieter.
- Tight, reused color mapping across all modalities (e.g. `wave1/wave2/wave3` or `baseline/highlight/neutral`).
- Grouping by whitespace and alignment — never decorative frames.
- Grid skeleton (locked): hero spans `gs[:, -1]` or `gs[0:2, 0:2]`; remaining cells filled by role priority.

### 3.3 `image-plate` (microscopy / volume / fluorescence)

- Black facecolor **only inside the plate cells**, never the whole page. White gutters, white scale bars.
- Grayscale context + 1–2 fluorescent channels (canonical: cyan `#22D7E6`, magenta `#FF2AD4`, grey context `#B8B8B8`).
- Crops, scale bars, view boxes geometrically consistent across rows/cols.
- Row/channel labels **directly on the plate** — no detached legends.

### 3.4 `clinical-triptych` (outcome-over-time)

- Top row: longitudinal lines, ONE shared legend strip above the row (outside data region).
- Middle row: forest-plot effects, dashed vertical reference line, pale category bands (never more salient than the CIs).
- Bottom row: compact summary/binary/stacked-percentage bars.
- Columns semantically parallel — if col1 is `ABR`, col2 reuses the same row logic.
- Baseline = black/dark grey; follow-up = restrained warm/cool sequence.

### 3.5 `quantitative-grid` (dense categorical / multi-metric)

- Equal grid spans **must** have equal final plot-area widths AND heights AND gutters (§5 alignment gate).
- Direct-label regions when categories are semantically intrinsic; hatch/texture when neighboring fills are close in luminance.
- Identical axis limits and panel geometry across the full grid.
- Repeated categorical structure → embedded labels, not a mega-legend.

### 3.6 Cross-cutting Nature page rules

- Panel labels: **small bold lowercase letters** near the top-left corner of each panel. Never large badges. `(a)` form acceptable for print; prefer `a`.
- Figure pages are **narrative, not dashboards**. A dominant panel is normal.
- Legends: omit when direct labeling works. Otherwise ONE shared legend strip, not per-panel legends.
- Background: white for charts; black only inside image-plate cells.
- Saturated colors are sparing and mean a true experimental channel or highlighted subgroup.
- When modalities coexist, axis-heavy plots are visually quieter than schematics/imaging.
- Gutters are slightly larger when dark panels touch light panels or modalities change.

---

## 4. Layout patterns (copy-ready skeletons — the "排版 vocabulary")

These 16 patterns are the layout vocabulary. `figure_recipes.py` / `method_recipes.py` expose the starred ones as first-class presets; the rest are documented gridspec recipes the agent may use **without changing locked geometry ratios**.

| # | Pattern | When | Locked geometry |
|---|---|---|---|
| P1 | Ultra-wide multi-metric bar | 3–4 metrics × many methods | width ≈ 3–4× height; x-ticks off if legend names methods |
| P2* | Dedicated legend panel | legend larger than 4 entries | last axes = legend-only, `set_axis_off()` |
| P3 | Categorical bars w/o x-ticks | methods named in legend | `ax.set_xticks([])` |
| P4 | Dynamic y-tighten | data occupies a sub-range | 10% margin; clean round ticks. **Never 0–100 when data is 80–95** |
| P5 | Alpha-graduated ablation | same method, stripped variants | one hue, `linspace(0.2, 1.0)` alphas |
| P6 | Hatch for grayscale | print / CVD risk | `hatches=['/','\\\\','.','x','o','+']` + black edge |
| P7 | Semantic/family color map | method families | coherent hue families; **green/red reserved for direction (gain/loss), never category identity** |
| P8 | In-bar text luminance-aware | value labels inside bars | `lum=0.299r+0.587g+0.114b`; white if <0.5 |
| P9 | Fill-between + hatch | cumulative/trend bands | hatch + white edge to erase border artifacts |
| P10 | Event annotations on trend | named events on a line | arrow + label at event x; stars encode significance |
| P11 | Grouped-within-grouped bars | metrics × datasets | 1-unit gap between dataset groups; dataset names as x-ticks |
| P12* | Schematic hero + quant row | mechanism leads, evidence follows | `height_ratios=[2.2, 1.0]`; hero = 45–60% height |
| P13* | Dark image plate grid | microscopy/volume | black only in cells; white gutters; consistent crop geometry |
| P14* | Clinical triptych | longitudinal + effect + summary | `height_ratios=[1.0, 1.35, 0.8]`; shared legend above |
| P15* | Asymmetric hero panel | one conceptually central result | hero spans full row or full column |
| P16 | Direct labels in filled regions | repeated stacked/phase structure | labels inside stable large regions; white/black stroke if fill varies |

---

## 5. Panel alignment gate (mechanical, A11 — 1.5 pt tolerance)

For every figure with ≥2 comparable panels, measure the **final rendered plot-area rectangles** before export and audit:

- **Shared edges, widths, heights, panel-label anchors, repeated gutters** must agree within **1.5 pt** (physical).
- A horizontal row of 3–4 equal-grid-span panels must have equal final plot-area **widths** as well as heights and gutters.
- Structured unequal-span grids (two stacked panels beside one panel spanning both rows) are checked via **shared grid start/stop boundaries**.
- Asymmetric hero panels, insets, colorbars are excluded only through an explicit `comparable_groups` entry or a recorded `exemption` with a reason. **Never weaken the global tolerance to hide one intentional exception.**
- Verdicts: `FIX BEFORE DELIVERY` / exit 1 blocks export. `NOT AUDITABLE` / exit 2 blocks any claim that alignment passed.

Implementation: `figure_audit.py` layer **A11** (matplotlib: collect `ax.get_window_extent()` after final layout draw; d2/SVG: parse panel-group rects). Manifest schema mirrors the nature-skills auditor (`schema_version`, `figure.{width_pt,height_pt}`, `panels[].bbox_pt`, `row_groups`, `column_groups`, `boundary_groups`).

---

## 6. Sizing discipline — final width FIRST (the step everyone gets wrong)

A point is 1/72 inch **of the saved file**. A 7pt label is 7pt to the reader only if the file is shown at the size it was saved.

```
on_page_font_pt = font_pt × W_doc / W_fig     # keep this ratio = 1
```

1. Find the **final width** first (where the figure will sit):
   - Nature/Science single column ≈ **89 mm / 3.54 in**
   - Nature/Science double column ≈ **183 mm / 7.24 in**
   - Height ceiling ≈ **240 mm**
   - One-column `article` ≈ 5.5 in
2. Set `figsize` to **exactly** that width. Height from aspect (0.5–0.8× width typical). Multi-panel rows: the whole figure gets the span width; panels divide it.
3. Keep point-scale fonts (6–8pt) — do NOT inflate fonts to compensate for a too-big figure; fix the width.
4. Insert at **100%**: `\includegraphics{fig.pdf}` with no `width=`, or `width=\columnwidth` **only if** figsize width already equals column width. **Never draw big and let the document shrink it.**
5. Prefer `constrained_layout=True` at a known `figsize`. `bbox_inches="tight"` changes the saved width and silently breaks the ratio.

**Point-scale type (locked, Zhangyanbo/nature-style-skill convergence)**:
- 6pt tick numbers · 7pt body · 8pt axis titles and panel labels · **5pt hard floor** (audit FAIL below)
- Regular + bold only; **bold carries emphasis, not size**
- Sentence case everywhere (`Tumour volume (mm³)`, not Title Case); SI units in parentheses
- Real Unicode glyphs (µ, α, ±, ×, ≤), never spelled out
- Panel labels: lowercase bold `a b c`

**Strokes (locked)**: floor 0.5pt · emphasized data line ≈1.6pt · regular ≈1.1pt · baseline/error bars ≈0.8pt · axis frame 0.8–1.2pt · no top/right spines on line/bar · frameless legends · no grid by default.

---

## 7. Human construction order (anti-AI-slop — method diagrams)

Model the figure as a human would build it in an editor. This order is a **hard planning sequence**, not post-hoc taste advice:

1. **Base** — main canvas, containers, simple geometry (rectangles / deliberately adjusted rounded rects). Flat fill; never a gradient to hide unplanned structure.
2. **Content on the base** — structures/modules with the simplest geometry that carries the meaning. Topologies/grids/model blocks reuse a real scholarly construction pattern, not an invented fake topology. Inputs are real or explicitly documented samples, not generic placeholder lines.
3. **Restrained arrows** — plain readable connectors AFTER objects are placed. Arrowheads/paths express direction and relation; never decorative, glossy, multi-colored, needlessly curved.
4. **Exact text** — concise block names/terms/relationship labels AFTER structure is stable. Never replace real labels with repeated horizontal filler lines.
5. **Visual next to its label** — each explanatory visual sits close to the text it explains.

**Forbidden defaults (AI-slop red list — hard FAIL at review)**:
- box + arrow only with zero embedded data visualization
- 3-color monotonous blue/orange/purple
- single-word labels with no formula/parameter
- hero containing only a box list, no embedded heatmap/curve/micro-plot
- no information panel (hyperparameters / loss curve / legend / metrics)
- flat layout with no visual hierarchy (core and aux at the same weight)
- default numbered `1/2/3/4` planning labels
- generic blue title-strip/content-box cards
- boxing off the upper portion of a module with a horizontal divider and centered title
- sticker-like cutouts, clip-art badges, medals, seals
- meaningless dots/tiles/floating symbols/purposeless boxes/decorative gradients/glow/fake shadows

**Visual hierarchy devices (use ≥2 stacked)**: size (hero ≥2× aux) · font weight · color saturation · whitespace · stroke width (hero container 1.4pt vs others 0.6pt). When the canvas size is fixed, prefer weight/color/stroke/whitespace over font size (font size is a globally coupled quantity).

**0.1s intuition test**: visual flow ≠ logical flow = wrong. Eye must travel the mainline without blockers. Deletion test: if it can be removed, remove it. Fixing one bug must not introduce a new aesthetic problem.

**Complexity budgets** (from diagram-design, already enforced in method_recipes): ≤9 nodes / ≤12 edges / focus modules ≤2 / ≤4 words per node.

---

## 8. Multi-panel composite rules (SCI Zone-1)

- Compose by **narrative unit** — only panels in the same argument/experiment chain share one figure.
- Panel count hard cap **9**; beyond → split or move to supplementary. Single-panel figures are equally legal.
- Every panel **independently** satisfies all audit and complexity rules — composite assembly cannot rescue low-quality panels.
- Coexisting schematic + data panels must unify style: same font family / color sequence / line width / marker vocabulary.
- Panel labels: reserved strip above each panel, never covering content. Numbering adapts continuously.
- Shared legend at figure level (not per-panel) whenever ≥2 panels share encodings.

---

## 9. QA checklist (run before delivery — mechanical + eyes)

**Contract**
- [ ] Core conclusion is one sentence with a verb
- [ ] Every panel has a distinct inferential role; necessity test passed
- [ ] Archetype declared and geometry ratios match §3
- [ ] Evidence-chain archetype declared

**Layout**
- [ ] Hero panel receives the dominant area; controls quieter but judgeable
- [ ] Panel labels: small bold lowercase, top-left, consistent anchor
- [ ] No per-panel legends when a shared legend/direct labels work
- [ ] Axis limits and geometry consistent across comparable panels
- [ ] A11 panel alignment PASS (1.5pt) or recorded exemption
- [ ] A10 text occlusion PASS (no label overlaps at final physical size)

**Sizing**
- [ ] figsize width == final print width preset
- [ ] `on_page_font_pt` ratio = 1 (no document-level rescale)
- [ ] All glyphs ≥5pt at final size
- [ ] Print-shrink test: readable at 50% zoom

**Encoding**
- [ ] Grayscale / CVD test survives (marker + line-style second cue, not color alone)
- [ ] Green/red only for direction/gain/loss/threshold — never sole category identity
- [ ] Error type named (`±1 SD` / `±1 SEM` / `95% CI`); zero baseline for bars unless justified
- [ ] Hatch/texture when neighboring fills are close in luminance

**Integrity**
- [ ] Source script + data retained beside the figure
- [ ] Negative results not packaged as contributions; failure boundaries visible when they change the claim
- [ ] Caption defines every symbol, color, `n`, and error type

---

## 10. Contract interaction

| Concern | Owner |
|---|---|
| Format, fonts, palette hexes, width presets | `figure-quality-contract.md` |
| Richness floor, edge governance, icons, layer model | `figure-complexity-contract.md` |
| **Composition, panel roles, page archetypes, alignment, sizing ratio** | **this file** |
| Visual review protocol | `figure-quality-review.md` |
| Rendering entry + audit wiring | `skills/meta-skills/unified-plotting/SKILL.md` |

Conflict priority: **scientific fact > user explicit request > this layout contract > aesthetic preference**. When the science demands unequal panels, record an A11 exemption — do not deform the science to satisfy equal grids.
