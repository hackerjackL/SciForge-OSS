# Domain Adaptation Contract (SciForge-OSS — TDAL 4-Dimensional Joint Confidence Schema)

> **Status (v2.8 — locked schema, v1.0.0 — weights hierarchy clarified)**: The single authoritative schema for the 4-dimensional joint confidence score (TDAL) consumed by `/result-to-claim` (Phase 10), reported in `CLAIMS_FROM_RESULTS.md`, and surfaced to `/paper-writing` (Phase 12) for the paper's Confidence & Limitations section. This file is the **contract** — every producer/consumer of TDAL MUST conform to the schema, weights, and thresholds defined here.
>
> **Core principle**: Confidence is not a single number. It decomposes into 4 independent dimensions; the joint is their product. No single dimension may be silently inflated or dropped.

## Quick Reference

- **Purpose**: Locks the 4-dimensional joint confidence (TDAL) schema + weights + thresholds + invocation contract
- **Producer**: `/result-to-claim` (Phase 10) — computes and emits TDAL
- **Consumer**: `/paper-writing` (Phase 12, Confidence & Limitations section) + orchestrator (PIPELINE_STATUS verdict)
- **Output**: `CLAIMS_FROM_RESULTS.md` § Confidence Assessment (TDAL block, machine-readable JSON attached)
- **Key**: joint = T × D × A × L; 4-level verdict STRONG/MODERATE/WEAK/UNSUPPORTED; the weakest dimension must always be reported

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

## TDAL Weight Hierarchy Table (v1.0.0 clarification)

> **Why this section exists**: After v2.8 introduced L2 deep integration, CHANGELOG line 20 reads "T dimension adds a new `theory_data_validation` component with weight 0.2 (T weight redistribution 0.3/0.25/0.25/0.2)" — in that phrasing, `0.3/0.25/0.25/0.2` can be read either as "the T dimension's share among the four TDAL dimensions" or as "the distribution across the 4 sub-components inside the T dimension". Both readings are self-consistent but mean entirely different things. This section explicitly distinguishes the two levels to remove the ambiguity.

### Level 1 — TDAL four-dimension weights (the relative standing of the 4 dimensions in the joint)

TDAL's 4 dimensions **T / D / A / L** are locked in v2.8 as **equal-weight** — the joint is a product (`T × D × A × L`), not a weighted average. Therefore at this level **there is no weight distribution such as 0.3/0.25/0.25/0.2**; each dimension independently takes a value in 0-1, and the product yields the joint.

| Dimension | Standing in the joint | Value range | Notes |
|-----------|-----------------------|-------------|-------|
| T (theoretical) | Equal-weight product factor | 0-1 | Weighted sum of the 4 T sub-components (see Level 2) |
| D (data_availability) | Equal-weight product factor | 0-1 | Weighted sum of the 3 D sub-components |
| A (domain_adaptation) | Equal-weight product factor | 0-1 | Weighted sum of the 2 A sub-components |
| L (literature_support) | Equal-weight product factor | 0-1 | Weighted sum of the 3 L sub-components |

**Key point**: joint = `T × D × A × L`, and **if any single dimension is 0 then the joint is 0** (floor constraint). There is no such thing as an inter-dimension weight like "T dimension accounts for 30%, D dimension accounts for 25%" — this is the core strictness of the v2.8 product formula.

### Level 2 — Sub-component weights within each dimension (final distribution after v2.8 L2)

**Inside** each dimension there are several sub-components, combined by weighted sum (weight sum = 1.0). This is where the `0.3/0.25/0.25/0.2` numbers truly belong — they are the weights of the **4 sub-components inside the T dimension**, not the share of the T dimension itself within TDAL.

#### Inside the T dimension (v2.8 L2 redistribution)

| T sub-component | Weight | Value | Source |
|-----------------|--------|-------|--------|
| `sympy_derivation` | 0.3 | PASS=1.0 / PARTIAL=0.5 / FAIL=0.0 | `/theory-derivation` Phase 6 |
| `logic_verification` | 0.25 | PASS=1.0 / WARN=0.7 / FAIL=0.0 | `/logic-verification` Phase 8 |
| `falsification_resistance` | 0.25 | SURVIVE=1.0 / WEAKENED=0.5 / FALSIFIED=0.0 | `/adversarial-falsification` Phase 2.5 |
| `theory_data_validation` | 0.2 | CONSISTENT=1.0 → FALSIFIED_SIGN=0.0; default 0.5 neutral | [`ouroboros-integration.md`](ouroboros-integration.md) § B (L2 deep call) |
| **sum** | **1.0** | | |

**v2.7→v2.8 T dimension change**: In v2.7, T dimension = `sympy_derivation (0.4) + logic_verification (0.3) + falsification_resistance (0.3)`, with the three components summing to 1.0. After v2.8 L2 added the `theory_data_validation` component, the original three components' weights were scaled proportionally from (0.4/0.3/0.3) down to (0.3/0.25/0.25), freeing 0.2 for the new component while the sum remains 1.0. **This is the true meaning of CHANGELOG v2.8 line 20 "T weight redistribution 0.3/0.25/0.25/0.2" — the new weight distribution of the 4 sub-components inside the T dimension.**

#### Inside the D dimension

| D sub-component | Weight | Value | Source |
|----------|------|------|------|
| `ouroboros_report` | 0.5 | `overall_score` 0-1 | [`ouroboros-integration.md`](ouroboros-integration.md) § A (basic call) |
| `oss_data_check` | 0.3 | DATA_READY=1.0 / DATA_LIMITED=0.5 / DATA_BLOCKED=0.0 | `/adversarial-falsification` Phase 2.5 |
| `theory_only_flag` | 0.2 | theory_only=true → 1.0 / false → 0.0 | `data-requirements-seed.json` |
| **sum** | **1.0** | | |

#### Inside the A dimension (after v2.8 S1)

| A sub-component | Weight | Value | Source |
|-----------------|--------|-------|--------|
| `domain_learner` | 0.8 | `learning_confidence` 0-1 | `/domain-learner` Phase 1b → `domain-signature.json` |
| `seed_paper_match` | 0.2 | qualitative match 0-1 | comparison against seed paper expectations |
| **sum** | **1.0** | | |

**v2.7→v2.8 A dimension change**: In v2.7, A dimension = `domain_signature (0.4) + domain_learner (0.4) + seed_paper_match (0.2)`. After v2.8 S1 (learner-first), the Phase 1a signature was downgraded to an OPTIONAL hint and is no longer an independent confidence source — hence the A dimension collapses to `domain_learner (0.8) + seed_paper_match (0.2)`, and the sum remains 1.0.

#### Inside the L dimension

| L sub-component | Weight | Value | Source |
|-----------------|--------|-------|--------|
| `supporting_ratio` | 0.5 | supporting_papers / total_papers | `/universal-retrieval` Phase 4 |
| `non_contradicting_ratio` | 0.3 | 1 - contradicting_papers / total_papers | same as above |
| `non_gap_ratio` | 0.2 | 1 - gap_papers / total_papers | same as above |
| **sum** | **1.0** | | |

### Computation order across the two levels (locked)

```
Step 1: Within each dimension, compute that dimension's value with a weighted sum
  T = 0.3×sympy + 0.25×logic + 0.25×falsif + 0.2×theory_data_val
  D = 0.5×ouroboros + 0.3×oss_check + 0.2×theory_only_flag
  A = 0.8×domain_learner + 0.2×seed_paper_match
  L = 0.5×supporting + 0.3×non_contradicting + 0.2×non_gap

Step 2: Across the four dimensions, compute the joint with a product
  joint = T × D × A × L

Step 3: Apply floor constraints + verdict thresholds
  - any dim = 0 → verdict ≤ WEAK
  - missing_inputs non-empty → verdict ≤ MODERATE
  - joint ≥ 0.7 → STRONG; 0.5-0.7 → MODERATE; 0.3-0.5 → WEAK; <0.3 → UNSUPPORTED
```

**Why the hybrid of "weighted sum inside dimensions + product across dimensions"**: The sub-components inside a dimension are **complementary** (SymPy pass + logic pass + falsification pass = high theoretical credibility; every pass contributes), which suits a weighted sum; the dimensions themselves are **strictly gated** against each other (no matter how strong the theory, no data is no data and no literature is no literature), which suits a product to realize the floor "any dimension at 0 forces the joint to 0". This is the core design of the v2.8 strictness contract.

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
- Theory-only flag: 0.0 (not a theory-only problem; real data is required)
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
**Weakest dimension**: Data Availability (0.725) — the Ouroboros data score is on the low side and the problem is not theory-only; a more reliable data source is needed, or a theory-only qualification must be added
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
- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — orchestrator contract
- [`ouroboros-integration.md`](ouroboros-integration.md) — § A D dimension basic call source + § B T dimension `theory_data_validation` deep call source (consolidated v1.0.0)
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — A dimension source (learner-written signature)


## retrain_from_results (v1.5.0-w2, GNoME active-learning pattern)

Verified experiment results are not terminal — they are **training evidence** for the
next domain-learning pass. When `experiments/**/RESULT.json` carries `status=PASS`, the
domain-learner SHOULD append the verified regime/metric to
`refine-logs/domain-signature.json` under `retrain_from_results` (list of
{regime, metric, artifact}) so the next run's signature already knows where the method
holds. This mirrors GNoME's predict -> DFT-verify -> retrain loop: the evidence that
survives verification feeds the model that will propose the next structures. Unverified
results never enter this field (hallucinated results must not self-reinforce).
