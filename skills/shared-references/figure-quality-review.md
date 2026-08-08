---
name: figure-quality-review
type: shared-reference
role: visual-figure-review-protocol
---

# Figure Quality Review Contract — Two-Tier Visual Review

> **Purpose**: mechanical audits (A1–A10 in `figure_audit.py`) verify
> STRUCTURE (sizes, palette, overlaps, branding) but cannot judge visual
> QUALITY (balance, elegance, whether the figure actually communicates).
> This contract closes that gap with a two-tier review protocol. **Tier 1
> requires NO external API — the host agent's own native vision is the
> reviewer.** Text-only agents degrade gracefully to the mechanical audit.

## Capability detection (first, once per run)

Determine the host agent's capability class and record it in the figure's
`revision_log.md`:

| Class | Detection | Review path |
|-------|-----------|-------------|
| **V (vision-native)** | The agent can read the figure file (SVG) and describe it | Tier 1 MANDATORY + Tier 2 optional |
| **T (text-only)** | The agent cannot ingest images | Mechanical audit + structure checklist only; Tier 1 recorded as `skipped-text-only` |

**Rule**: capability is a property of the HOST agent (Claude with vision,
GPT-4o, Gemini, a vision-enabled Codex/AtomCode build...), not of this
skill. The skill never calls an external vision API itself — if the host
has no vision, the run continues with the mechanical gate; it never blocks
and never fabricates a visual review.

## Tier 1 — Agent-native visual self-review (MANDATORY for class V)

After every render whose audit verdict is not FAIL, the agent MUST open
`figures/<name>/output.svg` (the SVG exists exactly for this — PDF is for
LaTeX) and answer the checklist below HONESTLY before delivering. This is
a structured inspection, not a glance: write the answers (one line each)
into `revision_log.md`.

**Visual checklist (answer every item; "looks fine" is not an answer)**:

1. **Message**: can a reader state the figure's single core message in one
   sentence without the caption? If not, the figure fails regardless of
   how pretty it is.
2. **Hierarchy**: does the eye land on the protagonist (ochre accent /
   diamond / largest element) first? Are secondary elements visibly
   quieter?
3. **Balance**: whitespace distribution — any corner crowded while another
   is empty? Panels in a composite visually equal-weighted?
4. **Wiring legibility**: follow each edge with the eye — any crossing
   that could be removed by re-routing? Any arrow entering a node from a
   confusing direction? Any label riding a line without a halo?
5. **Typography scan**: any text touching a border, clipped, or sitting on
   a dark fill with dark ink? All sizes perceptibly ≥ Nature floor at the
   PNG's native resolution?
6. **Color discipline**: does any element look MORE saturated than the
   rest (a smuggled non-morandi color the sanitizer can't catch, e.g. a
   named color or rgb() triple)? Any two elements that should be
   distinguished but look identical?
7. **Icon quality**: do icons read at thumbnail size, or are any
   unrecognizable blobs (→ redraw or replace via §5.5 runtime icons)?
8. **Composite-specific**: panel labels (a)(b)(c) present, bold, in
   reading order; no panel dwarfing its neighbors; style uniformity
   across panels (same font/color-order/line-weight family)?
9. **Print test**: shrink the PNG to single-column width in your head —
   does anything become illegible?

**Outcome handling** (scoped revision, complexity-contract §4.6):
- Every "no/concern" becomes a concrete fix applied to the SOURCE (spec /
  render.py), then re-render, then re-inspect. One issue class per pass.
- After 3 passes on the same concern without progress → re-layout that
  region from the skeleton (contract §4.6 rule 4), or record an explicit
  accepted-risk note with the reason.
- Deliver only when the checklist is fully satisfied AND the mechanical
  audit is not FAIL.

## Tier 2 — External optimization advisor (OPTIONAL, both classes)

An OPTIONAL second opinion from an external LLM advisor (any reachable
model endpoint the deployment already has — the skill itself stores no
credentials and makes no calls). Discipline unchanged from v1:

1. Keep the prompt minimal: short instruction + the figure's source or
   structure summary — the advisor does the analysis.
2. At most ONE call per figure version; its output is advisory, never a
   gate verdict, never blocks a run; unreachable ⇒ `deferred-external`.
3. Adopt suggestions only where they genuinely improve the figure; every
   adopted change goes through the normal source-edit → re-render → audit
   cycle.

**Prompt template (keep it minimal)**:

```
请对以下科研图的表达提出最有用的改进建议(每条一句话),并指出图形的
逻辑是否完整(有无缺失的输入/反馈边/数据节点)。
图源(结构概要): <nodes>, <edges>, <intent>。请严谨而克制。
```

## Figure criteria (mechanical + structural baseline)

| Aspect | Good threshold |
|--------|----------------|
| Logical completeness | all required inputs present; feedback loops shown; no dangling node |
| Narrative clarity | single core message; caption states it |
| Typography (Nature floor) | axis ≥ 12pt, ticks ≥ 10pt, legend ≥ 10pt |
| Palette | low-chroma house tokens (C* ≤ 25); Layer-2 colormaps for continuous fields |
| Layout | corridors/orthogonal wiring for hand SVG; no overlapping labels (A10) |
| Export | PDF + SVG dual output; source preserved; audit verdict not FAIL |

---
Tier 1 uses only the host agent's native vision (zero external calls);
Tier 2 is an optional advisory aid — neither tier produces a pipeline
gate verdict, stores credentials, or blocks a run. A text-only host
records `visual-review: skipped-text-only` and ships on the mechanical
audit alone.
