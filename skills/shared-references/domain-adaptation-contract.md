# Domain Adaptation Contract (SciForge-OSS — TDAL 4-Dimensional Joint Confidence Schema)

> **Status (v2.8 — locked schema)**: The single authoritative schema for the 4-dimensional joint confidence score (TDAL) consumed by `/result-to-claim` (Phase 10), reported in `CLAIMS_FROM_RESULTS.md`, and surfaced to `/paper-writing` (Phase 12) for the paper's Confidence & Limitations section. This file is the **contract** — every producer/consumer of TDAL MUST conform to the schema, weights, and thresholds defined here.
>
> **Core principle**: Confidence is not a single number. It decomposes into 4 independent dimensions; the joint is their product. No single dimension may be silently inflated or dropped.

## Quick Reference

- **Purpose**: 锁定 4 维联合置信度 (TDAL) schema + 权重 + 阈值 + 调用契约
- **Producer**: `/result-to-claim` (Phase 10) — computes and emits TDAL
- **Consumer**: `/paper-writing` (Phase 12, Confidence & Limitations section) + orchestrator (PIPELINE_STATUS verdict)
- **Output**: `CLAIMS_FROM_RESULTS.md` § Confidence Assessment (TDAL block, machine-readable JSON attached)
- **Key**: joint = T × D × A × L; 4 级判定 STRONG/MODERATE/WEAK/UNSUPPORTED; 最弱维度必须报告

## TDAL Schema (Locked)

```json
{
  "tdal": {
    "schema_version": "1.0",
    "problem_id": "Q001",
    "theoretical": {
      "value": 0.0,
      "components": {
        "sympy_derivation": {"weight": 0.3, "score": 0.0, "status": "pass|partial|fail"},
        "logic_verification": {"weight": 0.25, "score": 0.0, "status": "pass|warn|fail"},
        "falsification_resistance": {"weight": 0.25, "score": 0.0, "status": "survive|weakened|falsified"},
        "theory_data_validation": {"weight": 0.2, "score": 0.5, "status": "consistent|mostly_consistent|partial|mostly_inconsistent|falsified|falsified_sign|neutral|missing", "source": "ouroboros-deep-integration.md verdict_score; default 0.5 neutral when deep call not invoked"}
      }
    },
    "data_availability": {
      "value": 0.0,
      "components": {
        "ouroboros_report": {"weight": 0.5, "score": 0.0, "source": "ouroboros overall_score 0-1"},
        "oss_data_check": {"weight": 0.3, "score": 0.0, "status": "data_ready|data_limited|data_blocked"},
        "theory_only_flag": {"weight": 0.2, "score": 0.0, "status": "theory_only=true → 1.0; false → 0.0"}
      }
    },
    "domain_adaptation": {
      "value": 0.0,
      "components": {
        "domain_learner": {"weight": 0.8, "score": 0.0, "source": "domain-signature.json learning_confidence"},
        "seed_paper_match": {"weight": 0.2, "score": 0.0, "source": "qualitative match to seed paper expectations"}
      }
    },
    "literature_support": {
      "value": 0.0,
      "components": {
        "supporting_ratio": {"weight": 0.5, "score": 0.0, "source": "supporting_papers / total_papers"},
        "non_contradicting_ratio": {"weight": 0.3, "score": 0.0, "source": "1 - contradicting_papers / total_papers"},
        "non_gap_ratio": {"weight": 0.2, "score": 0.0, "source": "1 - gap_papers / total_papers"}
      }
    },
    "joint": 0.0,
    "verdict": "STRONG|MODERATE|WEAK|UNSUPPORTED",
    "weakest_dimension": "theoretical|data_availability|domain_adaptation|literature_support",
    "missing_inputs": []
  }
}
```

**v2.8 schema change**: `domain_adaptation` previously split into `domain_signature` (0.4) + `domain_learner` (0.4) + `seed_paper_match` (0.2). After S1 (learner-first, Phase 1a downgraded to OPTIONAL hint), the signature is no longer an independent confidence source — only the learner writes the signature. So `domain_adaptation` now collapses to `domain_learner` (0.8) + `seed_paper_match` (0.2). This avoids double-counting the learner's output under two labels.

## Per-Dimension Weight Tables

### Dimension 1: Theoretical Confidence (T)

| Source | Weight | How to compute |
|--------|--------|---------------|
| SymPy derivation status | 0.3 | PASS=1.0, PARTIAL=0.5, FAIL=0.0 |
| Logic verification | 0.25 | PASS=1.0, WARN=0.7, FAIL=0.0 |
| Falsification resistance | 0.25 | SURVIVE=1.0, WEAKENED=0.5, FALSIFIED=0.0 |
| Theory-data validation (deep integration, L2) | 0.2 | From [`ouroboros-deep-integration.md`](ouroboros-deep-integration.md) `joint_validation.verdict_score`; default 0.5 neutral when deep call not invoked; FALSIFIED_SIGN → 0.0 + TDAL cap at UNSUPPORTED |

**v2.8 L2 weight redistribution**: the original v2.7 weights (0.4 / 0.3 / 0.3) redistributed to (0.3 / 0.25 / 0.25 / 0.2) to make room for the new `theory_data_validation` component without exceeding sum = 1.0. The new component is the **only** T source fed by external data (Ouroboros deep call); the other three are OSS-internal. When deep call is not invoked (theory-only / data unavailable / prediction absent), the component defaults to 0.5 (neutral) and `missing_inputs` lists `"theory_data_validation"` — this caps TDAL verdict at MODERATE per the floor constraint, ensuring a claim cannot reach STRONG without external data validation.

### Dimension 2: Data Availability Confidence (D)

| Source | Weight | How to compute |
|--------|--------|---------------|
| Ouroboros data report | 0.5 | overall_score from Ouroboros (0-1) |
| OSS data availability check | 0.3 | DATA_READY=1.0, DATA_LIMITED=0.5, DATA_BLOCKED=0.0 |
| Theory-only flag | 0.2 | theory_only=true → 1.0 (no data needed); false → 0.0 |

**Theory-only problems**: if `theory_only=true`, the 0.2 weight rewards the problem for not needing data; D reduces to `0.5×ouroboros + 0.3×oss_check + 0.2×1.0`. If Ouroboros is unavailable on a theory-only problem, `ouroboros` component scores 0 but the 0.2 reward still applies — D does NOT collapse to 0.

### Dimension 3: Domain Adaptation Confidence (A)

| Source | Weight | How to compute |
|--------|--------|---------------|
| Domain learner confidence | 0.8 | From `domain-signature.json` `learning_confidence` field (written by /domain-learner) |
| Seed paper match quality | 0.2 | Qualitative: how well output matches domain expectations from seed papers |

**Learner-unavailable fallback**: if the learner failed entirely (no `domain-signature.json`), A defaults to 0.3 (general-domain baseline) and `missing_inputs` MUST list `"domain_learner"`. Never use Phase 1a's hint as a substitute score — the hint is not a confidence-bearing artifact.

### Dimension 4: Literature Support Confidence (L)

| Source | Weight | How to compute |
|--------|--------|---------------|
| Supporting papers ratio | 0.5 | supporting_papers / total_papers (0-1) |
| Non-contradicting ratio | 0.3 | 1 - contradicting_papers / total_papers |
| Non-gap ratio | 0.2 | 1 - gap_papers / total_papers |

**No literature found**: if `total_papers = 0`, L = 0.0 and `missing_inputs` MUST list `"literature_search"`. This blocks STRONG/MODERATE verdict regardless of other dimensions — a theory with no literature context is UNSUPPORTED for publication purposes.

## Combined Formula

```
joint_confidence = T × D × A × L

where:
  T = theoretical_confidence (0-1)
  D = data_availability_confidence (0-1)
  A = domain_adaptation_confidence (0-1)
  L = literature_support_confidence (0-1)
```

**Why product not weighted average**: a weighted average lets a strong dimension compensate for a failed one (e.g., T=1.0, D=0.0, average=0.5 → MODERATE). The product correctly drives the joint to 0 when any single dimension is 0 — a theory with zero data availability, zero domain fit, or zero literature support is UNSUPPORTED, regardless of how strong the other dimensions are. This is the strictness contract.

## Verdict Thresholds (Locked)

| Joint Confidence | Verdict | Action | Paper framing |
|-----------------|---------|--------|---------------|
| ≥ 0.7 | STRONG | Publishable with high confidence | "We establish…" / "We demonstrate…" |
| 0.5 - 0.7 | MODERATE | Publishable with caveats | "We provide evidence for…" + explicit caveats section |
| 0.3 - 0.5 | WEAK | Needs strengthening before publication | Do NOT claim — reframe as "preliminary" / "suggests"; recommend Phase 6 re-derivation |
| < 0.3 | UNSUPPORTED | Not publishable | BLOCK paper-writing; surface to human with weakest dimension + missing_inputs |

**Floor constraints (override the threshold table)**:
- Any single dimension = 0 → verdict is at most WEAK (cannot be STRONG/MODERATE regardless of joint value)
- `missing_inputs` non-empty → verdict is at most MODERATE (flag missing sources transparently)
- `weakest_dimension` MUST always be reported; the paper's Limitations section MUST name it explicitly

## Worked Example

```markdown
## Confidence Assessment (TDAL)

### Theoretical Confidence: 0.85 (STRONG)
- SymPy derivation: PASS (1.0)
- Logic verification: PASS (1.0)
- Falsification: SURVIVE (1.0)
- Weighted: 0.4×1.0 + 0.3×1.0 + 0.3×1.0 = 0.85

### Data Availability Confidence: 0.725 (MODERATE)
- Ouroboros report: 0.85
- OSS data check: DATA_READY (1.0)
- Theory-only flag: 0.0 (非 theory-only 问题，需要真实数据)
- Weighted: 0.5×0.85 + 0.3×1.0 + 0.2×0.0 = 0.725

### Domain Adaptation Confidence: 0.80 (STRONG)
- Domain learner: 0.80
- Seed paper match: 0.80
- Weighted: 0.8×0.80 + 0.2×0.80 = 0.80

### Literature Support Confidence: 0.75 (MODERATE)
- Supporting: 10/15 papers (0.67)
- Non-contradicting: 13/15 papers (0.87)
- Non-gap: 12/15 papers (0.80)
- Weighted: 0.5×0.67 + 0.3×0.87 + 0.2×0.80 = 0.755

### Joint Confidence: 0.85 × 0.725 × 0.80 × 0.755 = 0.37
**Verdict**: WEAK — needs strengthening before publication
**Weakest dimension**: Data Availability (0.725) — Ouroboros 数据得分偏低且非 theory-only，需更可靠数据源或补充 theory-only 限定
```

## Producer Contract (/result-to-claim)

`/result-to-claim` (Phase 10) is the **sole producer** of TDAL. It MUST:

1. Compute all 4 dimensions; if any input is missing, set that component to 0.0 and append to `missing_inputs`.
2. Emit the full machine-readable `tdal` JSON block in `CLAIMS_FROM_RESULTS.md` (attached as a fenced ```json block).
3. Compute `joint = T × D × A × L` exactly — no rounding, no clamping.
4. Apply the verdict thresholds AND the floor constraints.
5. Report `weakest_dimension` as the dimension with the lowest `value`.
6. NEVER inflate a dimension to avoid a WEAK/UNSUPPORTED verdict — missing inputs are reported, not papered over.
7. Surface UNSUPPORTED verdicts as BLOCK to the orchestrator (paper-writing cannot proceed).

## Consumer Contract (/paper-writing)

`/paper-writing` (Phase 12) is the **sole consumer** for paper output. It MUST:

1. Read `CLAIMS_FROM_RESULTS.md` and parse the `tdal` JSON block.
2. Include a "Confidence Assessment" section reproducing the 4-dimension breakdown + joint + verdict.
3. Name `weakest_dimension` explicitly in the Limitations section, with the specific gap described.
4. Frame claims per the verdict's "Paper framing" column — never use STRONG language ("establish", "demonstrate") for MODERATE/WEAK verdicts.
5. If `verdict = UNSUPPORTED`: refuse to write the paper and surface BLOCK to the orchestrator.

## Orchestrator Contract

The orchestrator (Phase 10 boundary) MUST:

1. Parse `tdal.verdict` from `CLAIMS_FROM_RESULTS.md`.
2. If `UNSUPPORTED`: halt with `verdict: BLOCKED, reason_code: unsupported_claim_<weakest_dimension>` — do NOT advance to Phase 11.
3. If `WEAK`: WARN + continue, but flag in PIPELINE_STATUS that the paper will be "preliminary" framed.
4. Forward `tdal` to Phase 12 (`/paper-writing`) via the artifact; do not recompute.

## Boundaries

- **Never silently drop a dimension.** All 4 must appear in every TDAL emission, even if a component is 0 with `missing_inputs` flagging why.
- **Never substitute Phase 1a hint confidence for learner confidence.** After S1, the hint is not confidence-bearing.
- **Never round the joint to dodge a threshold.** 0.6999 is MODERATE, not STRONG — report exactly.
- **Never let a strong dimension compensate a zero dimension.** The product formula is non-negotiable; a weighted average is NOT acceptable.
- **The schema is versioned (`schema_version: "1.0"`).** Any change to weights, thresholds, or component structure MUST bump the version and update CHANGELOG.

## See Also

- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — producer (Phase 10)
- [`../support/paper-writing/SKILL.md`](../support/paper-writing/SKILL.md) — consumer (Phase 12)
- [`../orchestrator/125-problems-pipeline/SKILL.md`](../orchestrator/125-problems-pipeline/SKILL.md) — orchestrator contract
- [`ouroboros-integration.md`](ouroboros-integration.md) — D dimension data source (basic integration, S3)
- [`ouroboros-deep-integration.md`](ouroboros-deep-integration.md) — T dimension `theory_data_validation` component source (deep integration, L2)
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — A dimension source (learner-written signature)
