---
name: figure-quality-review
type: shared-reference
role: external-figure-qa-loop (mimo-v2.5)
---

# Figure Quality Review Contract (mimo-v2.5 external QA loop)

> **Purpose**: The figure quality cannot be judged reliably by the drawing agent alone (self-confirmation bias). For top-tier **architecture diagrams, DAGs, workflow/pipeline figures and academic charts**, pipe the figure description + spec to the **mimo-v2.5** reviewer for a score and concrete fixes, then implement and re-render. Moved from "self-check" to "external strict review".

> **Access (single strict pass)**: `https://token-plan-cn.xiaomimimo.com/v1/chat/completions`, model `mimo-v2.5`, auth `Authorization: Bearer <key>`. Keep the prompt **minimal** (a short instruction, the figure's d2/tikz/matplotlib source or its semantic content) — the reviewer must do the rigorous analysis, not be spoon-fed a recommendation. 单次调用.

## Protocol

1. **Produce**: render the first version of the diagram (d2 → SVG → PDF+PNG), per [`unified-plotting`](../../meta-skills/unified-plotting/SKILL.md) and [`figure-quality-contract.md`](figure-quality-contract.md).
2. **Review** (one call): send a *brief* reviewer instruction + the figure's structure (nodes, edges, layout intent, palette) to mimo-v2.5. Ask for: score `/10`, the **3 most important fixes**, and whether the narrative/architecture is logically complete (any missing input/feedback edge?).
3. **Deploy fixes**: implement the top-3 (e.g. add a missing literature→theory edge, add an experiment→idea feedback loop, add data/method input nodes, fix typography/caption, add a legend for data plots).
4. **Re-render + close**: render v2, and confirm each of the 3 fixes is present. Figures needing >3 rounds of external review should be flagged for human decision (bounded — 3 rounds max, mirroring the 3-round rollback ceiling elsewhere).

## Prompt template (keep it minimal)

```
评审以下科研图是否达到可发表水准,给1-10分和最重要的3条改进(每条一句话),
并指出图形的逻辑是否完整(有无缺失的输入/反馈边/数据节点)。
图源(结构概要): <nodes>, <edges>, <intent>。请严格且克制地审查。
```

## Quality criteria the reviewer scores against

| Aspect | Good threshold |
|--------|----------------|
| Logical completeness | all required inputs present; feedback loops shown; no dangling node |
| Narrative clarity | single core message; caption states it |
| Typography (Nature floor) | axis ≥ 12pt, ticks ≥ 10pt, legend ≥ 10pt |
| Palette | morandi (chroma C* ≤ 25), or colorblind-safe if venue requires |
| Layout | auto-layout (d2 `--layout=elk` for dense); no overlapping labels |
| Export | PDF + PNG dual output; spec preserved for reproducibility |

---
Single source of truth for external figure QA. When mimo is unreachable, mark the QA as `deferred-external` and self-review against the criteria table above instead of silently skipping.