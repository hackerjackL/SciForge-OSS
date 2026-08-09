# Figure Complexity Contract (SciForge-OSS — Anti-Elementary-Figure Rules)

> **Status (v1.1)**: This contract specifically targets "elementary-school-level" figures — figures made of plain basic shapes plus large blocks of text, arrows flying everywhere, with no visual hierarchy. It complements [`figure-quality-contract.md`](figure-quality-contract.md) (format/palette/font sizes): that file governs "conventions", this file governs "complexity and visual appeal". Enforced by `/unified-plotting`, with mechanical checks embedded in the audit inside `render_figure.py` (A7 complexity layer).

## 0. Discipline Neutrality — Supreme Principle

SciForge-OSS serves **all disciplines**: science, engineering, agriculture, medicine, social sciences, humanities, economics, management, law — all of them. Every rule in this contract is stated in terms of the **structural role** of figures, not in terms of specific figure content or discipline:

- **Test figures ≠ skill boundary**: The example figures used during development are merely carriers for pipeline validation; they do not constitute a list of figure types the skill supports. The same set of rules applies to figures of any discipline, any content.
- **Discipline determines only semantics, not rules**: medical pathway diagrams, material lattice diagrams, statute hierarchy diagrams, historical timelines, ecological network diagrams... Component semantics vary by discipline, but this contract's richness floor, edge governance, layer model, depth devices, white-background and branding discipline never change.
- **The audit is discipline-agnostic**: The A4–A10 audit layers check only structural properties (font size, chroma, overlap, icon ratio, brand leakage) and contain no discipline assumptions whatsoever — adding a new discipline requires no audit changes.

## 0.5 Cross-Discipline Figure Role Typology (Role Typology × Engine Mapping)

Any paper figure is first classified into one structural role, then the engine and techniques are chosen from the table (all engines are rendered through the unified entry point `render_figure.py`, single pipeline):

| Structural role | Examples per discipline (illustrative only) | Preferred engine | Key techniques |
|---------|---------------------|---------|---------|
| **Structure/composition** | System architecture, device structure, anatomical hierarchy, unit cell/molecular structure, organizational framework | Hand-assembled SVG (Visio level) / tikz / isometric SVG | Layered containers, icon components, number badges, gradient card faces |
| **Process/flow** | Methodology, reaction pathways, clinical pathways, legal procedures, manufacturing processes | d2 / blockdiag(actdiag) / mermaid / pikchr / hand-crafted SVG | Swimlanes, check gates/decision points, milestone spine, deliverable annotations |
| **Mechanism/causality** | Molecular mechanisms, physiological feedback loops, economic causal chains, proof sketches, attention mechanisms | tikz (`\pic` custom-drawn) / isometric SVG / asy / pikchr | Custom-drawn components, bundle width ∝ intensity, dashed feedback, formula annotations |
| **Relation/network** | Citation networks, knowledge graphs, food webs, social networks, theorem dependencies | d2 (elk dense) / graphviz | Container-level bundling, edge density control, legend |
| **Hierarchy/classification** | Taxonomy trees, phylogeny, statute hierarchy, ontology structure | d2 / blockdiag tree | Tree layout, branch labels, progressive depth shading |
| **Time/evolution** | Historical timelines, evolutionary sequences, clinical courses, policy evolution | Hand-assembled SVG / d2 timeline | Axis + event anchors, period color bands, callouts |
| **Space/geography** | Maps, cross-sections, crystal structures, 3D devices | Isometric SVG / asy / diagrams | Isometric projection, grid baseplate, orientation annotations |
| **Evidence/data** | Experimental curves, clinical statistics, survey results, simulation outputs | matplotlib (white background + apply_matplotlib_style) | Composite panels, inset zoom, significance annotations, uncertainty bands |

**Usage**: When the agent receives a drawing task, it first determines the role (may be composite, e.g. "mechanism+data" uses composite panels); the role determines the engine and techniques, while the discipline only determines what the components depict. Composite-role figures prefer hand-assembled SVG on a unified canvas; splicing together multi-engine outputs is prohibited (keep a single pipeline).

---

## 1. Component Richness Floor

**For figures with ≥5 nodes, it is forbidden that all components are plain rectangles/plain ellipses.** At least 60% of the main components must have a custom visual identity, via one of three options (the agent writes them on the fly, without relying on any repo asset library):

| Technique | Engine | Approach |
|------|------|------|
| **Icon component** | d2 | Node declares `icon: ./icons/<name>.svg`; icons are written on the fly by the agent (§5 methodology) |
| **Custom pic** | TikZ | Multi-layer drawing via `\pic` macros (shadow layer + body + symbolic detail); no bare `rectangle` boxes |
| **Composite shape** | Asymptote/SVG | Combine ≥3 primitives + two tones (body fill + accent detail), e.g. a test tube with a liquid level, a chip with a grid |

**Audit**: A figure with 5+ nodes and zero icons/zero custom-drawn components → `A7 WARN plain_shapes_only`.

## 2. Visual Hierarchy

- **At least two levels of grouping**: container nesting (further grouping inside containers) or horizontal band partitioning; containers carry a title and a one-step-lighter fill color (`surface` → `surface-alt` progression).
- **Each container ≤6 direct children**; if exceeded, nest one more level of grouping.
- **Protagonist stands out**: The figure's core component (the protagonist of that figure's narrative — which may be a method, organ, device, or event) uses `ochre` (the sole accent slot) or a `diamond`/`hexagon` special shape; all other components are uniformly low-saturation.

## 3. Edge Governance — governing "too many, too messy edges"

1. **Container-level bundling**: When there are ≥3 parallel flows between the same pair of groups, they must be merged into a single labeled trunk edge or bus; N×M fully-connected arrow rain is prohibited. Example: 3 input sources each connecting to the same processing module → change to one trunk with symbol labels from the input container.
2. **Edge density cap**: `edges / nodes ≤ 1.6` (audit WARNs when exceeded). Genuinely needed dense graphs (theorem dependency DAGs, etc.) place a `complexity_override.txt` in the figure directory explaining the reason (e.g. "the dependency relations are themselves the content").
3. **Arrow style family ≤3 kinds**: solid = main data flow; dashed = feedback/auxiliary; thick = trunk. Four or more line styles in one figure are prohibited.
4. **Feedback edges detour**: Feedback/update edges run along the outer perimeter of the figure (d2: separate direction declaration; TikZ: `to[out=,in=]` detour); crossing through other components is prohibited.
5. **Label concision**: Edge labels ≤3 words; if a symbol ($z_v$, $\alpha$) can be used, do not use a sentence.
6. **Hand-crafted SVG dedicated wiring corridors (Visio level)**: When hand-assembling SVG, cross-swimlane connections must run through **pre-allocated vertical corridors** (column bands such as x=460–520, 940–1000); only vertical wiring is allowed inside a corridor, and horizontal segments join at 90° at the corridor's two ends — i.e. "orthogonal rounded-corner wiring". Diagonal lines are prohibited, and connections crossing through cards are prohibited. After buses merge inside a corridor, they branch out to each target via short horizontal segments on the far side of the corridor, forming comb-like distribution.

## 4. Text Discipline

- Node labels ≤3 lines, ≤4 words/line; long explanations go into the caption or side notes.
- A full explanatory sentence appearing inside the figure (>8 words) → refactor: split into components or move into the caption.
- Mathematical symbols use the engine's native math typesetting (TikZ `$...$` / d2 LaTeX `$$..$$`).

## 4.5 Layer Model — the organizational discipline of zero text overlap

Hand-assembled SVG must be organized by layer; audit layer A10 checks mechanically (text-text bbox intersection >12% → FAIL; wiring passing through text without a halo → WARN; ≥20 labels without layer structure → WARN):

```
<g class="layer-0-bg">       background and ground (white background rect, swimlane baseplates, grid)
<g class="layer-1-cards">    cards/containers and their embedded icons, mini visualizations (text inside cards belongs to this layer)
<g class="layer-2-wiring">   all connections, buses, arrows (drawn above cards, below labels)
<g class="layer-3-labels">   edge labels, callouts, legend (topmost layer; every label must sit in an unobstructed empty spot)
```

**Hard rules**:
1. The bboxes of any two texts must not intersect (an edge label sitting on text, or a title sitting on card text, both count as violations) — check for empty space before placing labels (A10 will scan them out)
2. Edge labels sit **beside** the segment (vertical offset ≥1.2× font size) or carry a halo rect; riding on the line without a background is prohibited
3. Card text stays ≥12px from the card edge; text columns of adjacent cards must not intrude into each other
4. Wiring is in layer-2, text is in layer-3 — wiring never covers text

## 4.6 Review & Revision Discipline (Scoped Revision — drawing on Memslides local revision, Apache-2.0)

After the audit reports problems, revisions must be **localized**; rewriting the whole figure is prohibited:

1. Modify only the specific elements named by A4/A5/A8/A9/A10 (that label/that card/that connection); re-render the whole figure but confine the change to that spot
2. Fix only one class of problem at a time (fix FAILs first, then WARNs); after fixing, run the audit to confirm, then move on to the next class
3. Revisions preserve the iteration trail: the figure directory's `revision_log.md` records "audit finding → change made" item by item (reproducible, traceable)
4. If the same problem persists for 3 consecutive rounds → go back to skeleton level and re-lay out that region, instead of continuing to nudge coordinates

(Memslides' hierarchical-memory/tool-memory ideas have been comparatively evaluated: its rendering pipeline is slide export, which differs from this pipeline's vector-illustration positioning, so it is not integrated as an engine; only its scoped revision methodology is adopted, keeping a single pipeline.)

## 5. Icon Hand-Drawing Methodology (written on the fly by the agent, not checked into the repo)

> **Principle**: Icons are the agent's creative output, saved together with each figure in that figure's directory (`figures/<name>/icons/*.svg`), reproducible and auditable. SciForge-OSS provides only the methodology, not an icon library.

### 5.1 d2 icon conventions

- Size: `viewBox="0 0 64 64"` (square icons); node `width/height` left automatic in d2; `style.font-size` ≥20px next to the icon
- Coloring: Morandi tokens only (`sciforge_style.TOKENS`); stroke `#6E675F`(ink-soft) 1.5–2px, body fill `#EDE9E2`/token, accent details use the component's semantic color
- Structure: 5–15 primitives, ≥2 tones, must have one "recognizable detail" (the database's elliptical top, the neuron's synapse dots, the gear's teeth)
- Reference: `icon: ./icons/db.svg` (relative to the spec's directory)

**Reference template** (the agent custom-draws in this style; it must not be reused directly as an icon library):
```svg
<!-- database: elliptical top + cylindrical body + tier lines (recognizable detail = tiers) -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <path d="M12 16v28c0 4 9 7 20 7s20-3 20-7V16" fill="#EDE9E2" stroke="#6E675F" stroke-width="2"/>
  <ellipse cx="32" cy="16" rx="20" ry="7" fill="#93A7BB" stroke="#6E675F" stroke-width="2"/>
  <path d="M12 28c0 4 9 7 20 7s20-3 20-7" fill="none" stroke="#6E675F" stroke-width="1.5"/>
</svg>
```
```svg
<!-- neural layer: stacked discs + connection points (recognizable detail = stacking and nodes) -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="14" y="40" width="36" height="8" rx="4" fill="#BDA5A7" stroke="#6E675F" stroke-width="1.5"/>
  <rect x="14" y="28" width="36" height="8" rx="4" fill="#A4B294" stroke="#6E675F" stroke-width="1.5"/>
  <rect x="14" y="16" width="36" height="8" rx="4" fill="#93A7BB" stroke="#6E675F" stroke-width="1.5"/>
  <circle cx="22" cy="20" r="2" fill="#FAF8F5"/><circle cx="32" cy="20" r="2" fill="#FAF8F5"/><circle cx="42" cy="20" r="2" fill="#FAF8F5"/>
</svg>
```

### 5.2 TikZ custom component conventions

- Define the pic with `\tikzset{pics/<name>/.style={...}}`, with ≥3 drawing layers inside: `shadow (soft fill)` → `body (token fill + ink-soft stroke)` → `detail (ochre/rose accent)`
- Component shadows are unified: `fill=sfinksoft!12, transform canvas={shift={(0.35mm,-0.35mm)}}`
- Data tensors are drawn as stacked discs (`foreach` loop); do not write "[h1,h2,...]" as text

### 5.3 Asymptote / isometric SVG

- Asy: component = ≥3 primitives + ≥2 tones; mechanical parts add hatch lines (`hatch`), fluids add gradients (`axialshade`)
- **Isometric 3D style figures (lightweight alternative to Blender/renderers)**: use pure SVG for 2:1 isometric projection (iso(x,y,z) = ((x−y)·cos30°, (x+y)/2 − z)), drawing in depth-sorted order via the painter's algorithm; solid = top face + two visible side faces; side faces overlay translucent ink (10%/20%) on the token color to create light and shade, and the SVG source remains 100% Morandi-compliant (audit passes); paired with callout leader annotations (dashed leader + dot anchor + label), a ground grid plate, and particle-flow accents. Suited to mechanism schematics and system structure diagrams — achieving a "3D feel" without introducing 3D rendering dependencies.

### 5.4 Background and branding discipline

- **The background of all figure types is pure white `#FFFFFF`** (data plots, architecture diagrams, methodology diagrams, mechanism diagrams — all of them), blending seamlessly with the white paper of the paper; Morandi is used only for component/series/fill colors. For data plots, override `figure.facecolor`/`axes.facecolor` after `apply_matplotlib_style()`; SVG figures place `<rect fill="#FFFFFF">` underneath.
- **The figure is a paper illustration, not a tool poster**: internal brands/tool names/palette codenames (SciForge, unified renderer, morandi, figure-lab paths, renderer version numbers, etc.) are prohibited anywhere inside the figure. Audit layer A9 scans figure sources and forcibly blocks them; the title bar carries only the figure's academic content, and tool information stays in the caption and body text.

### 5.5 Runtime Icon Vocabulary Protocol (Runtime Icon Vocabulary — raising the visual ceiling, not checked into the repo)

> **Background**: There is a natural ceiling on the artistry of icons hand-drawn by the agent. This protocol permits borrowing professional open-source icon vocabulary at **runtime**, while not violating the principle of "not writing an icon asset library into the repo" — icons are saved with the figure in `figures/<name>/icons/`, with sources and licenses recorded in the figure's `revision_log.md`.

**License whitelist (fetch only from these sources; others prohibited)**:

| Source | License | Domain |
|------|------|------|
| bioicons.com | icons individually annotated (mostly CC0/CC-BY) | biomedical/molecular/cellular |
| Tabler Icons | MIT | general technology |
| Lucide | ISC | general technology |
| Feather Icons | MIT | general technology |
| Font Awesome Free (solid/regular) | CC-BY-4.0 | general (attribution required) |
| d2 bundled icons (icons.terrastruct.com) | distributed with d2 | infrastructure/cloud |

**Mandatory workflow (four steps, none may be skipped)**:
1. **Fetch**: download the SVG from a whitelisted source to `figures/<name>/icons/<icon>.svg`, accessing it via proxy (mihomo 8099); **a failed fetch does not block** — fall back to agent hand-drawing (§5.1 methodology)
2. **Recolor**: the icon must pass through `sciforge_style.recolor_icon()` (`python -c "from sciforge_style import recolor_icon; ..."`) — mapped to Morandi series colors by L* lightness order, neutrals preserved; original-color icons that were not recolored will be blocked by the A3 audit if they enter a figure
3. **Reference**: d2 uses `icon: ./icons/<icon>.svg`; hand-crafted SVG embeds via `<image>` or inline `<g>` (inline preferred, keeping a single auditable file)
4. **Record**: append a line `icon: <name> ← <source URL> (<license>)` to the figure's `revision_log.md`; attribution for CC-BY/Font Awesome icons is written into the LaTeX acknowledgments or supplementary materials as the license requires

**Prohibited**: using original colors directly after fetching, fetching from sources outside the whitelist, batch-writing the icon library into the repo, using icons to bypass the A7 complexity audit (icons are component vocabulary; they do not replace in-card mini visualizations).

### 5.6 Icon Synthesis Techniques (Icon Synthesis — Nature-level icon construction methods the agent must master)

> **Measured feedback (v4.0)**: When the agent directly draws "box + text", that is not an icon; figures that only use a single primitive + single-color fill cannot reach Nature level. This section gives **executable icon synthesis recipes** — each icon = a multi-primitive synthesis, and the agent writes the SVG on the fly per the recipe, without relying on any asset library.

**Icon anatomy (four elements, none may be skipped)**:
1. **Silhouette**: one recognizable main shape — thumbnail test: still recognizable when shrunk to 16px (database = cylinder with elliptical top, camera = rounded rectangle with a lens, funnel = trapezoid, chip = square with pins)
2. **Semantic detail**: 1–3 internal elements that say "what it is" (the database's tier lines, the chip's circuit traces, the document's text lines, the funnel's convergence lines) — this is the key to distinguishing a "box" from an "icon"
3. **Material hint**: a top highlight bar (white 20% opacity rectangle) or a bottom shadow (ink 8% opacity) — creating volume; all-flat fill is prohibited
4. **Anchoring stroke**: unified ink-soft 1.5–2px stroke, unified corner radius (r=4–8) — icon stroke widths across the whole figure must be consistent

**Icon synthesis recipes (take by category; viewBox is always 0 0 64 64)**:

| Icon class | Recipe (primitive composition order) |
|--------|---------------------|
| Storage/data source | elliptical top (token fill) → cylinder body path (surface fill) → 2 tier arcs (ink-soft 1.5px) → top highlight bar |
| Processing module | rounded rectangle (token gradient fill) → internal symbol (gear pattern/arrow ring/matrix dot grid) → status dot at top right (ochre r=3) |
| Document/text | folded-corner rectangle path → 3–4 text lines (alternating lengths, ink-soft) → 1 accent line (token) |
| Device/hardware | body rectangle → circle embedded in screen/lens (two layers: outer ring ink-soft + inner core canvas) → 2–3 small rectangles as side-interface bumps |
| Decision/gate | rhombus (ochre) → pass-through arrow inside (canvas 2.5px) → status dots at top and bottom vertices |
| Convergence/funnel | trapezoid path → 3 dashed lines converging inward → small exit circle |
| Network/relation | 3–5 circles of varying sizes (main node token, secondary nodes surface) → connections drawn first, under the circles (lines first, circles after) |
| Timeline/sequence | vertical timeline axis → event anchor circles (alternating token) → short label lines on the right |

**Synthesis discipline**:
- Each icon has ≥3 primitives and ≥2 tones (body token + detail ink-soft/canvas)
- Icons within the same figure belong to the **same style family**: stroke width, corner radius, highlight position all consistent
- **No text inside icons** (text belongs to the card layer); when annotation is needed, use the card title
- Complex icons may use `<g>` grouping + `<defs>` reuse (if icons of the same kind appear multiple times in a figure, define one `<symbol>` and `<use>` it in multiple places)

### 5.7 Advanced Architecture Diagram Techniques (Nature/Visio level — complex architecture diagrams no longer "simple")

Measured feedback: an architecture diagram with only nodes and arrows is at "flowchart level" and cannot reach Nature level. The following techniques are **stacked as figure complexity increases**:

1. **Layered containers**: swimlanes/zones use two-level containers (large zone with title bar + cards inside); container fill is surface-alt translucent, cards are pure white + shadow — hierarchy is expressed through "progressive depth of base color"
2. **Ports and junctions**: wiring anchor points on card edges (r=3–4 ink-soft solid circles); at bus merge/branch points draw solid junction circles (r=5) — circuit-diagram convention; connections directly "passing through" cards are prohibited
3. **Bus wiring**: ≥3 parallel flows joined into one labeled trunk (3px thick + label halo), comb-distributed to each target — eliminating arrow rain
4. **Gradient cards**: cards of key components use a token linear gradient (white 20% → token 45%) — gradient cards make up 30–50% of the figure, the rest pure white, forming visual rhythm
5. **Number badges**: circular numbers ①②③ in white on ink background at the top-left corner of main-flow components; the caption echoes by number — the standard practice of Nature Figure 1
6. **Callout leaders**: annotations outside the figure use "dot anchor + 45° thin leader + halo label"; stuffing long text into components is prohibited
7. **Legend discipline**: the legend explains only **line-style/symbol semantics** (what solid/dashed/junction/rhombus each represents), not repeating component names; placed as one horizontal band at the bottom
8. **Whitespace budget**: margins around ≥48px, spacing between cards ≥24px, container inner padding ≥20px — crowding is the first source of "not premium"

## 6. Complexity Floor (quantified)

| Figure type | Component count | Icon/custom-drawn ratio | Grouping levels | Additional elements (at least 1) |
|--------|--------|--------------|----------|----------------------|
| Intro problem figure | ≥8 | ≥50% | ≥2 | legend / callout annotation |
| Methods structure/mechanism figure | ≥12 | ≥60% | ≥2 | legend + zone titles (a/b/c) |
| Mechanism figure | ≥8 | ≥60% | ≥2 | formula annotation / attention weights |
| Composite panel | ≥3 panels | data plots exempt from icons | — | (a)(b)(c) panel labels |

**Failing to meet the floor = the figure is not finished yet**; keep iterating (add components, draw icons, tidy connections) rather than lowering the bar to deliver.

## 6.5 Visual Depth Techniques (Visio/Illustrator level — "flat boxes" prohibited)

> To reach Visio/AI-level texture, hand-assembled SVG must stack depth language; audit layer A8 counts mechanically (`figure_audit.py audit_richness`): card count ≥4 with a total number of depth elements less than the card count → WARN.

| Technique | Approach | Quantity recommendation |
|------|------|---------|
| **Gradient card face** | `<linearGradient>` white→token lightening (opacity overlay; source remains palette-compliant), card header or whole card | ≥30% of cards |
| **Shadow layering** | `filter feDropShadow` (validated template), floating cards/gate rhombuses | all floating cards |
| **Port dots** | wiring anchor points on card edges: r=3–4 solid circles (ink-soft); add r=5 junction circles at bus junctions | ≥1 on every card with outgoing lines |
| **Bus junctions** | at trunk merge/branch points draw solid junction circles (circuit-bus convention); lines directly "passing through" cards are prohibited | every merge point |
| **Mini visualization** | sparkline / token bar / patch grid / attention matrix / progress bar embedded inside a card | ≥40% of cards |
| **Numbered annotation** | card corner mark ①②③ or (1)(2)(3) small circular badges; the caption echoes by number | main-flow components |
| **Status badge** | small rounded badge at top right (pretrained ✓ / running / frozen) | where applicable |
| **Scale/gauge** | numeric values rendered as mini gauge bars (fill percentage), no bare text | ≥1 |

**Depth coloring discipline**: gradients use only "token ↔ canvas/white" or "token ↔ low-opacity ink overlay"; introducing new hues is prohibited; audit A3 still verifies via source hex values (opacity overlays do not produce new hex values, naturally compliant).

## 7. Composite Figure (Composite / Multi-panel) SCI Q1 Standard (v3.8)

Multi-panel composite figures must reach the SCI Q1 layout standard. The unified entry point supports `.composite.json` manifest assembly: panels (PDF/PNG) converted to raster → grid layout → **(a)(b)(c)… number labels** → dual outputs + audit.

### 7.0 Composition Decision (Nature/Science/Cell logic — decided up front; not every figure should be composited)

A paper's figures are a **reasonable mix of composite figures and single figures**; composition decisions follow CNS conventions:

1. **Compose by narrative unit, not by figure count**: only multiple panels of the same argument/same experiment chain go into one composite figure; independent arguments use independent single figures or independent composites; "stuffing unrelated panels into one figure to save space" is prohibited
2. **Panel count hard cap = 9**: `render_figure.py` **directly refuses** manifests with >9 panels (RENDER FAIL); they must be split into multiple composites or moved to supplementary materials — exceeding it produces "a hodgepodge", and Q1 review will invariably demand splitting the figure. Enforced at the tool layer; no override
3. **Layout budget**: the total number of composites in the main text is subject to the journal's layout (long-form Nature-style 3–6 main figures, double-column templates 5–8 figures); when composites squeeze the layout, prefer splitting figures or moving to supplementary materials over compressing panel readability
4. **Single figures are equally legitimate**: an independent core architecture/mechanism diagram needs no numbering — but if numbered, it still uses the **(a)** single label to keep the style consistent
5. **Numbering adapts to panel count**: (a)(b)(c)… assigned one by one; after panels are added or removed, numbering **must be renumbered consecutively** (caption synced); skipped numbers or leftover stale numbers are prohibited

### 7.1 Panel labels (mandatory)

1. Each panel gets one **bold lowercase letter label** `(a)` `(b)` `(c)` … (aa/ab used only with ≥27 panels, which the 9-panel cap makes impossible)
2. Labels sit in the **reserved strip above the panel** (label_strip), never covering panel content
3. Label font size ≥14pt, bold, ink color; order = reading order (left before right, top before bottom), corresponding one-to-one with **a** **b** **c** in the caption

### 7.2 Grid and layout (mandatory)

1. Panel count → default grid: 2 panels 1×2, 3–4 panels 2×2, 5–6 panels 2×3 or 3×2, 7–9 panels 3×3
2. Panels in the same row align to equal height (row height is that of the tallest panel in the row; short panels are vertically centered); uniform spacing (gap), margins on all four sides
3. Background pure white; no divider lines between panels (Nature convention); separation by spacing alone
4. Panel style unified: same font family/font size/line width/Morandi series color order; panels each doing their own thing is prohibited

### 7.3 Caption (mandatory)

1. The composite's caption is self-contained and explains panel by panel: `Fig. N. **a**, description. **b**, description. …` (Nature sentence style)
2. At least one sentence per panel; a single figure's caption is a complete self-contained description

### 7.4 Panel quality floor (mandatory)

Each panel inside a composite must **independently** satisfy all other rules of this contract (A1–A10 audit, complexity floor, depth devices); composite assembly cannot rescue low-quality panels — one panel failing = the whole figure failing.

**Manifest format** (`.composite.json`):
```json
{"panels": [{"file": "../fig1/output.pdf", "label": "a"},
            {"file": "../fig2/output.svg", "label": "b"}],
 "cols": 2, "gap": 48, "margin": 60, "label_strip": 64, "width_px": 3600}
```

## 8. See Also

- [`figure-quality-contract.md`](figure-quality-contract.md) — format/palette/font sizes/ratios
- [`figure-quality-review.md`](figure-quality-review.md) — two-level visual review protocol (level 1 = mandatory agent native-vision self-review; level 2 = optional external consultant; pure-text hosts fall back to mechanical audit)
- [`../meta-skills/unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) — consumer
