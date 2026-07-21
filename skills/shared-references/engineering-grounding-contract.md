# Engineering Grounding Contract — 5-Dimension Real-World Feasibility Axis

> **Status (v2.9 — NEW)**: Contract for the **Engineering Grounding (EG)** axis, the 6th axis in the idea pre-screen. Defines how OSS evaluates real-world engineering feasibility of every idea — not whether OSS sandbox can run it, but whether a real engineering team can build it.
>
> **Core principle**: Innovation without engineering grounding is a gamble. This axis quantifies the gamble so humans can decide. It does NOT simplify ideas — it only labels, routes, and produces downside protection reports.

---

## 1. Why a Separate Axis from Tractability

| Existing axis | What it measures | EG axis | What it measures |
|--------------|-----------------|---------|-----------------|
| **Tractability** (5-axis pre-screen) | Can OSS sandbox (SymPy + numpy) close the loop? | **Engineering Grounding** (6th axis) | Can a real engineering team build this? How much? How long? What if it's wrong? |

**Key difference**: Tractability is OSS-internal (sandbox feasibility). EG is OSS-external (real-world feasibility). They are non-overlapping. An idea can be tractable in OSS sandbox (SymPy derivation works) but have EG score 2/10 (requires 1000 GPU-h + proprietary dataset + 3 custom instruments).

---

## 2. The 5 Sub-Dimensions (Domain-Agnostic)

Every idea candidate is scored on 5 sub-dimensions. Each sub-dimension is **domain-agnostic** — the scoring rubric is the same for all fields. For humanities/social-science domains where some sub-dimensions don't apply, those are marked `NOT_APPLICABLE` (automatic 10/10, no penalty).

| # | Sub-dimension | What it measures | 0 (BLOCKED) | 5 (CONSTRAINED) | 10 (READY) | N/A handling |
|---|---------------|-----------------|-------------|-----------------|------------|-------------|
| 1 | **Compute Footprint** | Total compute needed for one full reproduce | > 10× OSS sandbox budget (e.g., > 1000 GPU-h, > 500 CPU-h) | 1-10× sandbox budget | ≤ sandbox budget | Humanities: NOT_APPLICABLE (auto 10) |
| 2 | **Dependency Chain** | Number of external dependencies NOT yet ready (dataset, device, library, process, instrument) | ≥ 3 unready deps | 1-2 unready deps | 0 or all ready | All domains: always applicable |
| 3 | **Team-Year Estimate** | Estimated person-months from idea → reproducible prototype (not full product, just reproduce-able) | > 24 person-months | 6-24 person-months | ≤ 6 person-months | All domains: always applicable |
| 4 | **Reproducibility Risk** | Probability that the core trick is false → full rework | > 50% | 20-50% | < 20% | All domains: always applicable |
| 5 | **Capital Cost** | Non-compute capital investment (equipment, clinical trial, field survey, proprietary data purchase) | Requires new infrastructure or new procurement | Requires procurement but commercially available | Only existing infrastructure | Humanities: NOT_APPLICABLE (auto 10) |

### N/A Rule

If a sub-dimension is NOT_APPLICABLE for the domain, it scores **10/10** and does not penalize the average. The agent must explicitly state why it's N/A (e.g., "Compute Footprint: NOT_APPLICABLE — pure theoretical humanities problem, no compute needed"). This prevents "N/A as escape hatch" — every N/A must be justified.

---

## 3. EG Axis Tier Classification

After 5 sub-dimension scores are computed:

```
eg_average = average of all non-N/A sub-dimensions

eg_average ≥ 6.0  →  READY        idea enters MCTS normally
eg_average 3.0-5.9 →  CONSTRAINED  idea enters MCTS, tagged `engineering_constrained`
eg_average < 3.0   →  HEAVY        idea enters MCTS, tagged `engineering_heavy`
Any sub-dim = 0    →  BLOCKED      idea rejected at pre-screen (same as any other axis BLOCKED)
```

### BLOCKED Rule (the only elimination)

A sub-dimension score of **0** is BLOCKED — the idea is rejected at pre-screen, same as any other axis BLOCKED. This ensures that ideas with truly impossible engineering requirements (e.g., "requires a particle accelerator that doesn't exist") are eliminated early.

**Exception**: If the sub-dimension is NOT_APPLICABLE, it can never be 0.

### Non-Elimination Rule (HEAVY / CONSTRAINED)

HEAVY and CONSTRAINED ideas are **NOT eliminated**. They proceed through the full pipeline. The EG tier only affects:

1. The idea carries a visible `engineering_grounding` label in `IDEA_CANDIDATES.md` and `IDEA_DAG.json`
2. The novelty-check composite score includes EG as a small weight (see §5)
3. Every HEAVY/CONSTRAINED idea produces an `ENGINEERING_GROUNDING.md` report (see §4)
4. The human sees the EG score at the Phase 3→4 forced checkpoint

---

## 4. Engineering Grounding Report (ENGINEERING_GROUNDING.md)

Every idea with EG tier CONSTRAINED or HEAVY produces a report. READY ideas may produce a simplified version.

### Report Schema

```markdown
## IDEA-{id} Engineering Grounding Report

### Labels
| Sub-dimension | Score | Tier | Notes |
|---------------|-------|------|-------|
| Compute Footprint | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. GPU-h or CPU-h; N/A reason if N/A} |
| Dependency Chain | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {list of unready deps} |
| Team-Year Estimate | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. person-months} |
| Reproducibility Risk | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {risk % + key assumption} |
| Capital Cost | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. cost; N/A reason if N/A} |
| **EG Average** | **{avg}** | **{OVERALL TIER}** | |

### Engineering Path (分段落地路线)
- Stage 1 ({person-month range}): {cheapest falsification step} — 「如果 trick 假，在这里就死，损失最小」
- Stage 2 ({person-month range}): {scaled verification step} — 「投入更多资源前再验证一次」
- Stage 3 ({person-month range}): {full prototype} — 「仅当 Stage 1+2 都通过时才投入」

### Downside Protection (trick 假的下行保护)
- If trick falsified at Stage 1 → loss = {person-months} (bounded, minimal)
- If falsified at Stage 2 → loss = {person-months} + {compute cost}
- If falsified at Stage 3 → loss = {person-months} + {full cost}
- **Recommendation**: {e.g., "Allocate Stage 1 budget first. Do not commit Stage 2-3 until Stage 1 passes."}
```

### Engineering Path Design Principles

1. **Stage 1 is always the cheapest possible falsification** — reproduce the core trick on OSS sandbox regime, or on a tiny dataset, or on a simplified model. The goal is to kill the idea as early as possible if it's false.
2. **Stage 2 is a scaled gate** — 10% compute, limited data, partial implementation. If the idea survives Stage 1 but fails Stage 2, the engineering team has spent moderate resources.
3. **Stage 3 is the full prototype** — only invest if Stages 1 and 2 both passed.
4. The stages are **not** the same as OSS pipeline phases. OSS pipeline runs the full theory derivation. The engineering path is a separate, real-world implementation plan.

---

## 5. Integration with Novelty-Check Composite Score

The novelty-check composite score formula is **updated** to include EG as a minor weight:

```
old: score = novelty × 0.50 + feasibility × 0.30 + relevance × 0.20
new: score = novelty × 0.45 + feasibility × 0.25 + relevance × 0.15 + engineering_grounding × 0.15
```

**Rationale**: EG gets 0.15 weight — enough to cause a noticeable ranking difference between a "novel but impossible" idea and a "novel and buildable" idea, but not enough to eliminate a highly novel idea purely on engineering grounds. The 0.15 weight is calibrated so that:
- A max-novelty (10) + min-EG (0) idea scores 10×0.45 + 0×0.15 = 4.5
- A mid-novelty (6) + max-EG (10) idea scores 6×0.45 + 10×0.15 = 4.2
- → Novelty still dominates, but EG provides meaningful differentiation.

**EG normalization**: EG score fed into the composite formula is `eg_average / 10` (normalized to 0-1 scale). If all sub-dimensions are N/A (humanities), EG = 1.0 (no penalty).

---

## 6. Integration with Adversarial Falsification

The existing Phase 5 (Computational Feasibility) is **split** into two sub-phases:

| Phase | Name | What it evaluates |
|-------|------|-------------------|
| **Phase 5a** | OSS Sandbox Feasibility (unchanged) | Can the idea be run in OSS sandbox (SymPy + numpy)? |
| **Phase 5b** | Engineering Grounding Estimate (NEW) | Real-world engineering feasibility using the 5 sub-dimensions above |

Phase 5b produces the `ENGINEERING_GROUNDING.md` report. It runs AFTER Phase 5a. If Phase 5a BLOCKED the idea, Phase 5b is skipped (NOT_APPLICABLE).

---

## 7. Integration with Result-to-Claim

The existing `Grounding Confidence` in `result-to-claim` is **split**:

| Component | Source | What it reports |
|-----------|--------|-----------------|
| **OSS Sandbox Grounding** (unchanged) | Phase 5a result, re-computed in Phase 10 | Confidence that OSS derivation is correct |
| **Engineering Grounding** (NEW) | Inherited from Phase 5b; NOT re-computed | Real-world feasibility projection from idea stage |

The Phase 10 `Grounding Confidence` score becomes:
```
grounding_confidence = 0.6 × oss_sandbox_grounding + 0.4 × engineering_grounding
```

The EG component is **inherited** from the idea stage, not re-computed. This prevents the pipeline from wasting time re-evaluating something that hasn't changed.

---

## 8. Artifact Registration

| Artifact | Path | Producer | Consumers | Schema |
|----------|------|----------|-----------|--------|
| `ENGINEERING_GROUNDING.md` | refine-logs/ | Phase 5b (adversarial-falsification) | Phase 3→4 human checkpoint, novelty-check, result-to-claim, auto-review-loop | This contract |

---

## 9. Boundaries

- **EG does NOT replace Tractability.** Both axes exist in parallel. Tractability = OSS sandbox feasibility. EG = real-world feasibility.
- **EG does NOT simplify ideas.** A HEAVY idea proceeds to full theory derivation. The EG report only labels and routes, never modifies the idea content.
- **N/A must be justified.** Every NOT_APPLICABLE annotation requires an explicit reason. "N/A as escape hatch" is forbidden.
- **EG is domain-agnostic.** The 5 sub-dimensions and N/A rules apply to all domains uniformly.
- **EG is NOT a compute budget for OSS.** The `effort-contract` budget (cs-ml 30 GPU-h etc.) remains OSS's internal search budget. EG's Compute Footprint measures the idea's real-world build cost, which is 30-100× larger.

---

## 10. See Also

- [`idea-discovery/SKILL.md`](../meta-skills/idea-discovery/SKILL.md) — consumes EG axis at pre-screen
- [`idea-dag-schema.md`](idea-dag-schema.md) — node schema with EG fields
- [`novelty-check/SKILL.md`](../meta-skills/novelty-check/SKILL.md) — composite score with EG weight
- [`adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — Phase 5b EG estimate
- [`result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — inherits EG from Phase 5b
- [`auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — orchestrator quality gate
- [`competitive-analysis.md`](competitive-analysis.md) — marks EG as "已实施"