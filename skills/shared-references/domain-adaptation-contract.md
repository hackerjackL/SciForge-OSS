# Domain Adaptation Contract (SciForge-OSS — TDAL 4-Dimensional Joint Confidence Schema)

> **Status (v2.8 — locked schema, v1.0.0 — weights hierarchy clarified)**: The single authoritative schema for the 4-dimensional joint confidence score (TDAL) consumed by `/result-to-claim` (Phase 10), reported in `CLAIMS_FROM_RESULTS.md`, and surfaced to `/paper-writing` (Phase 12) for the paper's Confidence & Limitations section. This file is the **contract** — every producer/consumer of TDAL MUST conform to the schema, weights, and thresholds defined here.
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

## TDAL 权重层级表（v1.0.0 澄清）

> **为什么要这一节**: v2.8 引入 L2 deep integration 后，CHANGELOG 第 20 行写 "T 维新增 0.2 权重 `theory_data_validation` 组件（T 权重重分布 0.3/0.25/0.25/0.2）"——这一表述里 `0.3/0.25/0.25/0.2` 既可被读作 "T 维在 TDAL 四维中的占比"，也可被读作 "T 维内部 4 子组件的分布"。两种读法都自洽但意义完全不同。本节显式区分两个层级，消除歧义。

### 层级 1 — TDAL 四维权重（4 维在 joint 中的相对地位）

TDAL 的 4 个维度 **T / D / A / L** 在 v2.8 锁定为**等权**——joint 是 product（`T × D × A × L`），不是 weighted average。因此这一层级**没有 0.3/0.25/0.25/0.2 这样的权重分布**；每一维独立取值 0-1，乘积得 joint。

| 维度 | 在 joint 中的地位 | 取值范围 | 备注 |
|------|------------------|---------|------|
| T (theoretical) | 等权乘积因子 | 0-1 | 由 4 个 T 子组件加权求得（见层级 2） |
| D (data_availability) | 等权乘积因子 | 0-1 | 由 3 个 D 子组件加权求得 |
| A (domain_adaptation) | 等权乘积因子 | 0-1 | 由 2 个 A 子组件加权求得 |
| L (literature_support) | 等权乘积因子 | 0-1 | 由 3 个 L 子组件加权求得 |

**关键**: joint = `T × D × A × L`，**任何一维为 0 则 joint 为 0**（floor constraint）。不存在 "T 维占 30%、D 维占 25%" 这样的维度间权重——这是 v2.8 product formula 的核心严格性。

### 层级 2 — 各维内部子组件权重（v2.8 L2 后的最终分布）

每一维**内部**有若干子组件，子组件之间是 weighted sum（权重和 = 1.0）。这才是 `0.3/0.25/0.25/0.2` 数字的真正归属——它们是 **T 维内部 4 子组件**的权重，不是 T 维本身在 TDAL 中的占比。

#### T 维内部（v2.8 L2 重分布）

| T 子组件 | 权重 | 取值 | 来源 |
|----------|------|------|------|
| `sympy_derivation` | 0.3 | PASS=1.0 / PARTIAL=0.5 / FAIL=0.0 | `/theory-derivation` Phase 6 |
| `logic_verification` | 0.25 | PASS=1.0 / WARN=0.7 / FAIL=0.0 | `/logic-verification` Phase 8 |
| `falsification_resistance` | 0.25 | SURVIVE=1.0 / WEAKENED=0.5 / FALSIFIED=0.0 | `/adversarial-falsification` Phase 2.5 |
| `theory_data_validation` | 0.2 | CONSISTENT=1.0 → FALSIFIED_SIGN=0.0；默认 0.5 neutral | [`ouroboros-integration.md`](ouroboros-integration.md) § B (L2 deep call) |
| **sum** | **1.0** | | |

**v2.7→v2.8 T 维变化**: v2.7 T 维 = `sympy_derivation (0.4) + logic_verification (0.3) + falsification_resistance (0.3)`，三组件 sum=1.0。v2.8 L2 新增 `theory_data_validation` 组件后，原三组件权重从 (0.4/0.3/0.3) 按比例收缩到 (0.3/0.25/0.25)，腾出 0.2 给新组件，sum 仍为 1.0。**这就是 CHANGELOG v2.8 第 20 行 "T 权重重分布 0.3/0.25/0.25/0.2" 的真正含义——T 维内部 4 子组件的新权重分布。**

#### D 维内部

| D 子组件 | 权重 | 取值 | 来源 |
|----------|------|------|------|
| `ouroboros_report` | 0.5 | `overall_score` 0-1 | [`ouroboros-integration.md`](ouroboros-integration.md) § A (basic call) |
| `oss_data_check` | 0.3 | DATA_READY=1.0 / DATA_LIMITED=0.5 / DATA_BLOCKED=0.0 | `/adversarial-falsification` Phase 2.5 |
| `theory_only_flag` | 0.2 | theory_only=true → 1.0 / false → 0.0 | `data-requirements-seed.json` |
| **sum** | **1.0** | | |

#### A 维内部（v2.8 S1 后）

| A 子组件 | 权重 | 取值 | 来源 |
|----------|------|------|------|
| `domain_learner` | 0.8 | `learning_confidence` 0-1 | `/domain-learner` Phase 1b → `domain-signature.json` |
| `seed_paper_match` | 0.2 | 定性匹配 0-1 | seed paper 期望对比 |
| **sum** | **1.0** | | |

**v2.7→v2.8 A 维变化**: v2.7 A 维 = `domain_signature (0.4) + domain_learner (0.4) + seed_paper_match (0.2)`。v2.8 S1 (learner-first) 后，Phase 1a signature 降为 OPTIONAL hint，不再是独立置信源——故 A 维 collapse 为 `domain_learner (0.8) + seed_paper_match (0.2)`，sum 仍为 1.0。

#### L 维内部

| L 子组件 | 权重 | 取值 | 来源 |
|----------|------|------|------|
| `supporting_ratio` | 0.5 | supporting_papers / total_papers | `/universal-retrieval` Phase 4 |
| `non_contradicting_ratio` | 0.3 | 1 - contradicting_papers / total_papers | 同上 |
| `non_gap_ratio` | 0.2 | 1 - gap_papers / total_papers | 同上 |
| **sum** | **1.0** | | |

### 两层级的计算顺序（locked）

```
Step 1: 每一维内部用 weighted sum 算出该维 value
  T = 0.3×sympy + 0.25×logic + 0.25×falsif + 0.2×theory_data_val
  D = 0.5×ouroboros + 0.3×oss_check + 0.2×theory_only_flag
  A = 0.8×domain_learner + 0.2×seed_paper_match
  L = 0.5×supporting + 0.3×non_contradicting + 0.2×non_gap

Step 2: 四维之间用 product 算 joint
  joint = T × D × A × L

Step 3: 应用 floor constraints + verdict thresholds
  - any dim = 0 → verdict ≤ WEAK
  - missing_inputs non-empty → verdict ≤ MODERATE
  - joint ≥ 0.7 → STRONG; 0.5-0.7 → MODERATE; 0.3-0.5 → WEAK; <0.3 → UNSUPPORTED
```

**为什么是 "内部 weighted sum + 维度间 product" 的混合**: 维度内部各子组件是**互补**的（SymPy 通过 + 逻辑通过 + 证伪通过 = 理论可信度高，任一通过都贡献），适合加权求和；维度之间是**严格卡控**的（理论再强，没数据就是没数据，没文献就是没文献），适合乘积以实现 "任一为 0 则 joint 为 0" 的 floor。这是 v2.8 严格性契约的核心设计。

## Per-Dimension Weight Tables

### Dimension 1: Theoretical Confidence (T)

| Source | Weight | How to compute |
|--------|--------|---------------|
| SymPy derivation status | 0.3 | PASS=1.0, PARTIAL=0.5, FAIL=0.0 |
| Logic verification | 0.25 | PASS=1.0, WARN=0.7, FAIL=0.0 |
| Falsification resistance | 0.25 | SURVIVE=1.0, WEAKENED=0.5, FALSIFIED=0.0 |
| Theory-data validation (deep integration, L2) | 0.2 | From [`ouroboros-integration.md`](ouroboros-integration.md) § B `joint_validation.verdict_score`; default 0.5 neutral when deep call not invoked; FALSIFIED_SIGN → 0.0 + TDAL cap at UNSUPPORTED |

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
- [`ouroboros-integration.md`](ouroboros-integration.md) — § A D dimension basic call source + § B T dimension `theory_data_validation` deep call source (consolidated v1.0.0)
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — A dimension source (learner-written signature)
