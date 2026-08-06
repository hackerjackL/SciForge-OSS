---
name: figure-quality-review
type: shared-reference
role: external-figure-optimization-advisor
---

# Figure Quality Review Contract (external LLM optimization advisor)

> **Purpose**: The figure quality cannot be judged reliably by the drawing agent alone (self-confirmation bias). For top-tier **architecture diagrams, DAGs, workflow/pipeline figures and academic charts**, the drawing agent may optionally pipe the figure's structure (nodes, edges, layout intent, palette) to an **external LLM optimization advisor** to get concrete improvement suggestions, then implement and re-render. The advisor is an **assist for optimizing the drawing** — it is NOT a scoring gate, NOT part of the pipeline verdict, and never blocks a run. If the advisor is unreachable, the run continues normally (self-review against the criteria table below).

> **Discipline**: keep the prompt **minimal** (a short instruction + the figure's d2/tikz/matplotlib source or its semantic content) — the advisor should do the rigorous analysis, not be spoon-fed a recommendation. Use at most one call per figure version; never treat its output as a pass/fail gate.

## Protocol

1. **Produce**: render the first version of the diagram through the SINGLE unified entry point — `python scripts/plotting/render_figure.py spec.d2 --out figures/<name>/ --label <name> --caption "..." --strict` (internally: d2 → SVG → palette sanitize → PDF+PNG → embedded audit), per [`unified-plotting`](../meta-skills/unified-plotting/SKILL.md) and [`figure-quality-contract.md`](figure-quality-contract.md). The embedded audit (`figure_audit.json`) is the mechanical gate; this advisory pass is the qualitative complement.
2. **Advisory pass** (optional, one call): send a *brief* instruction + the figure's structure (nodes, edges, layout intent, palette) to the external advisor. Ask for the **most useful improvements** (e.g. missing input/feedback edge? better layout? typography/caption fixes?) and whether the architecture narrative is logically complete.
3. **Deploy improvements**: implement the suggested fixes where they genuinely improve the figure (e.g. add a missing literature→theory edge, add an experiment→idea feedback loop, add data/method input nodes, fix typography/caption, add a legend for data plots).
4. **Re-render**: re-run the same unified CLI (v2), confirm the audit verdict is PASS and each adopted improvement is present. If the advisor is unreachable, mark the advisory pass as `deferred-external` and rely on the criteria table below — never block the pipeline on it.

## Prompt template (keep it minimal)

```
请对以下科研图的表达提出最有用的改进建议(每条一句话),并指出图形的
逻辑是否完整(有无缺失的输入/反馈边/数据节点)。
图源(结构概要): <nodes>, <edges>, <intent>。请严谨而克制。
```

## Figure criteria (self-review fallback when advisor is unreachable)

| Aspect | Good threshold |
|--------|----------------|
| Logical completeness | all required inputs present; feedback loops shown; no dangling node |
| Narrative clarity | single core message; caption states it |
| Typography (Nature floor) | axis ≥ 12pt, ticks ≥ 10pt, legend ≥ 10pt |
| Palette | morandi (chroma C* ≤ 25), or colorblind-safe if venue requires |
| Layout | auto-layout (d2 `--layout=elk` for dense); no overlapping labels |
| Export | PDF + PNG dual output; spec preserved for reproducibility |

---
The external advisor is an optimization aid only — it never produces a gate verdict, never stores credentials in the repo, and its suggestions are adopted at the drawing agent's judgment.