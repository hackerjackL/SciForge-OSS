# Ouroboros Deep Integration (SciForge-OSS — theory ↔ data validation loop, long-term L2)

> **Status (v2.8 — long-term L2)**: Defines the **closed-loop** integration between SciForge-OSS (theory derivation) and Ouroboros Data-Insight (data verification) — going beyond the basic integration ([`ouroboros-integration.md`](ouroboros-integration.md) S3, which only feeds the TDAL D dimension's availability score). L2 closes the loop: OSS emits a **theoretical prediction** (effect size, sign, functional form, regime), Ouroboros searches for matching real data and returns the **actual effect** + **fit quality**, OSS computes a **joint validation report** (theory vs data agreement). This is the "theory verification engine" positioning — not "do research for you" but "verify your research idea against real data".
>
> **Core principle**: The basic integration answers "is the data available?" (D dimension). The deep integration answers "does the data AGREE with the theory?" (validation loop). Two separate Ouroboros calls: basic (Phase 2.5, availability report) + deep (Phase 10, prediction-vs-actual fit report). Neither substitutes for the other.

## Quick Reference

- **Purpose**: 理论预测 ↔ 数据实际值自动对照，输出联合验证报告（theory vs data agreement）
- **OSS side**: 输出 theoretical_prediction (effect size, sign, functional form, regime) from Phase 6 derivation
- **Ouroboros side**: 按预测查匹配数据 → 返回 actual_effect + fit_quality + recommendation
- **Output**: `refine-logs/theory-data-validation-report.json` (joint validation, consumed by Phase 10 TDAL T dimension uplift + Phase 12 paper Validation section)
- **Key**: basic (availability) and deep (validation) are TWO separate Ouroboros calls; deep is OPTIONAL (only when basic returned availability ≥ 0.5)

## Two Ouroboros Calls — basic vs deep

```
┌────────────────────────────────────────────────────────────────────┐
│ BASIC call (S3, already exists)                                    │
│   trigger: Phase 2.5 finalizes data-requirements.json             │
│   OSS → Ouroboros: "is this data available?"                      │
│   Ouroboros → OSS: data-availability-report.json (overall_score)  │
│   feeds: TDAL D dimension (availability component, weight 0.5)   │
│   does NOT answer: "does the data agree with the theory?"         │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼  (pipeline continues Phase 5-10)
┌────────────────────────────────────────────────────────────────────┐
│ DEEP call (L2, NEW)                                                │
│   trigger: Phase 6 derivation completes + Phase 10 TDAL emits      │
│            AND basic call's overall_score ≥ 0.5 (data exists)      │
│   OSS → Ouroboros: "here is my theoretical prediction;             │
│                     does matching real data agree?"               │
│   Ouroboros → OSS: theory-data-validation-report.json             │
│     (actual_effect, fit_quality, recommendation)                   │
│   feeds: TDAL T dimension uplift (fit ≥ 0.7 → T component bonus)  │
│          + Phase 12 paper Validation section (joint report)        │
└────────────────────────────────────────────────────────────────────┘
```

**Deep call OPTIONAL rationale**: if basic call returned `overall_score < 0.5` (data largely unavailable), the deep call has nothing to verify against — skip deep, fall back to OSS-internal numerical sanity check (existing Phase 6 behavior). The deep call only runs when there IS data to verify against.

## OSS Output: theoretical-prediction.json (Phase 6 → deep call trigger)

After Phase 6 (`/theory-derivation`) completes successfully, OSS emits a structured theoretical prediction for Ouroboros to match:

```json
{
  "format_version": "1.0",
  "generated_by": "SciForge-OSS Phase 6",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:30:00Z",
  "derivation_summary": {
    "assumptions": ["compact operator", "contraction mapping"],
    "target_outcome": "convergence_rate",
    "method": "SymPy symbolic + numerical sweep",
    "fidelity": "symbolic"
  },
  "theoretical_prediction": {
    "predicted_effect_sign": "positive",
    "predicted_effect_size": 0.5,
    "predicted_effect_size_unit": " elasticity coefficient ",
    "confidence_interval": [0.3, 0.7],
    "functional_form": "Y = βX + ε where β ∈ [0.3, 0.7]",
    "regime_of_validity": "compact contraction operators on Banach spaces",
    "key_predictions": [
      {
        "prediction_id": "P1",
        "description": "convergence rate is linear in contraction constant",
        "type": "quantitative",
        "expected_value": "O(ρ) where ρ is contraction constant",
        "tolerance": "factor of 2"
      },
      {
        "prediction_id": "P2",
        "description": "convergence fails for non-compact operators",
        "type": "qualitative",
        "expected_value": "divergence or sub-linear convergence",
        "tolerance": "sign-only"
      }
    ],
    "required_data_for_validation": [
      {
        "prediction_id": "P1",
        "needed_variables": ["iteration_error", "contraction_constant"],
        "needed_regime": "compact contraction operators",
        "min_observations": 50
      }
    ]
  },
  "anti_inflation_flags": {
    "assumptions_are_restrictive": true,
    "scope_is_narrow": false,
    "falsification_resistant": true,
    "comment": "Prediction is grounded in symbolic proof; not inflated to general Banach operators"
  }
}
```

**Emission contract**:
- Phase 6 emits `theoretical-prediction.json` ONLY when derivation succeeds (SymPy PASS or PARTIAL with documented gap). FAIL → no prediction, no deep call.
- `key_predictions` MUST distinguish `quantitative` (numeric effect) from `qualitative` (sign or regime). Ouroboros validates each type differently.
- `anti_inflation_flags` MUST self-assess: if the prediction is grounded in restrictive assumptions, flag it — Ouroboros' fit report will respect the regime, not generalize.
- `required_data_for_validation` echoes the basic call's data requirements but refined per-prediction — Ouroboros searches for the variables needed to validate EACH key prediction.

## Ouroboros Input: actual-observation-report.json (deep call return)

Ouroboros searches for real data matching the prediction's regime and returns the actual observation:

```json
{
  "format_version": "1.0",
  "generated_by": "Ouroboros-Data-Insight (deep call)",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:35:00Z",
  "matched_datasets": [
    {
      "prediction_id": "P1",
      "dataset": "Fredholm_2024_benchmark",
      "source": "Numerische Mathematik benchmark archive",
      "sample_size": 120,
      "regime_match": "compact contraction operators on Banach spaces",
      "observations": [
        {"iteration_error": 0.45, "contraction_constant": 0.3},
        {"iteration_error": 0.21, "contraction_constant": 0.5},
        {"iteration_error": 0.09, "contraction_constant": 0.7}
      ]
    }
  ],
  "actual_effect": {
    "prediction_id": "P1",
    "observed_sign": "positive",
    "observed_effect_size": 0.48,
    "observed_ci": [0.25, 0.65],
    "observed_regime": "compact contraction operators; ρ ∈ [0.2, 0.8]"
  },
  "fit_quality": {
    "prediction_id": "P1",
    "sign_agreement": true,
    "size_agreement": 0.92,
    "ci_overlap": 0.78,
    "overall_fit": 0.85,
    "fit_method": "least-squares + CI overlap ratio"
  },
  "qualitative_predictions": [
    {
      "prediction_id": "P2",
      "observed": "3 cases of non-compact operators showed sub-linear convergence; 1 case divergence",
      "agreement": "consistent"
    }
  ],
  "recommendation": "Theory is consistent with data for P1 (fit 0.85, CI overlap 0.78). P2 qualitative agreement. Recommend: publish with regime caveat; generalization to non-compact operators remains conjectural."
}
```

**Ouroboros deep contract**:
- `matched_datasets` MUST match the prediction's `regime_of_validity` — Ouroboros does NOT pull data from outside the theory's stated regime (that would be unfair falsification).
- `fit_quality.size_agreement` = `1 - |predicted - observed| / max(|predicted|, |observed|)` — bounded 0-1.
- `fit_quality.ci_overlap` = overlap area of predicted vs observed CI / union area.
- `fit_quality.overall_fit` = `0.4 × sign_agreement + 0.4 × size_agreement + 0.2 × ci_overlap` — locked formula (sign agreement is the dominant component: wrong sign = theory falsified).
- `recommendation` is a STRING (human-readable) — OSS does NOT let it gate the pipeline; OSS reads the structured fields and applies its own verdict.

## OSS Joint Validation Report: theory-data-validation-report.json (Phase 10)

OSS combines its theoretical prediction with Ouroboros' actual observation into a joint validation report. This is the L2 output artifact:

```json
{
  "format_version": "1.0",
  "generated_by": "SciForge-OSS Phase 10 (deep integration)",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:40:00Z",
  "oss_output": {
    "theoretical_prediction": "Y = βX + ε, β ∈ [0.3, 0.7]",
    "predicted_effect_size": 0.5,
    "predicted_ci": [0.3, 0.7],
    "required_data": ["iteration_error", "contraction_constant"]
  },
  "ouroboros_output": {
    "data_found": true,
    "actual_effect": 0.48,
    "actual_ci": [0.25, 0.65],
    "fit_quality": 0.85,
    "recommendation": "Theory is consistent with data..."
  },
  "joint_validation": {
    "sign_agreement": true,
    "size_disagreement": 0.04,
    "ci_overlap": 0.78,
    "overall_fit": 0.85,
    "regime_caveat": "validated for compact contraction operators; non-compact remains conjectural",
    "verdict": "CONSISTENT",
    "verdict_score": 0.85
  },
  "tdal_t_uplift": {
    "applied": true,
    "fit_bonus": 0.10,
    "t_component": "theory_data_validation",
    "t_before": 0.85,
    "t_after": 0.95,
    "rationale": "external data confirms prediction within regime; T uplift bounded by fit_quality"
  },
  "paper_validation_section": {
    "headline": "Theoretical prediction validated against Fredholm_2024_benchmark (N=120)",
    "quantitative": "Predicted β = 0.5 [0.3, 0.7]; observed β = 0.48 [0.25, 0.65]; fit 0.85",
    "qualitative": "Non-compact operators: 3/4 cases showed sub-linear convergence (consistent with divergence conjecture)",
    "caveats": ["validated only for ρ ∈ [0.2, 0.8]; extrapolation beyond needs further data"]
  }
}
```

### Joint Validation Verdict (locked)

| overall_fit | verdict | meaning | T uplift |
|-------------|---------|---------|----------|
| ≥ 0.8 | CONSISTENT | theory strongly supported by data | +0.10 bonus |
| 0.6 - 0.8 | MOSTLY_CONSISTENT | theory supported with minor discrepancies | +0.05 bonus |
| 0.4 - 0.6 | PARTIAL | theory partially supported; discrepancies need explanation | 0 (no bonus, no penalty) |
| 0.2 - 0.4 | MOSTLY_INCONSISTENT | theory largely disagrees with data | -0.10 penalty |
| < 0.2 | FALSIFIED | data contradicts theory | -0.20 penalty + TDAL verdict capped at WEAK |
| sign disagreement | FALSIFIED_SIGN | data has opposite sign — theory is wrong on direction | FALSIFIED escalation → TDAL verdict capped at UNSUPPORTED for this claim |

**T uplift contract**:
- The T dimension bonus/penalty is applied to the `theory_data_validation` T component (a NEW component added in v2.8 L2), NOT to the existing SymPy/logic/falsification components.
- v2.8 T dimension weight redistribution (locked):

```
T = 0.3 × sympy_derivation + 0.25 × logic_verification + 0.25 × falsification_resistance + 0.2 × theory_data_validation
```

The new `theory_data_validation` component (weight 0.2) is fed by the deep integration verdict. When deep integration is NOT invoked (theory-only or data unavailable), this component defaults to 0.5 (neutral — neither confirmed nor contradicted) and `missing_inputs` lists `"theory_data_validation"`.

**Floor**: `theory_data_validation` component cannot push T above 1.0 — the bonus is bounded by the cap. FALSIFIED_SIGN escalates to TDAL UNSUPPORTED regardless of other components (a theory with wrong direction is not publishable).

## Phase Wiring (L2 integration into the 20-phase pipeline)

```
Phase 6: /theory-derivation
    ↓ emits derivations/* AND theoretical-prediction.json (NEW L2)
    ↓
Phase 7: /leakage-audit
    ↓ (unchanged)
Phase 8: /logic-verification
    ↓ (unchanged)
Phase 9: /invariant-check
    ↓ (unchanged)
Phase 10: /result-to-claim
    ↓ reads basic call's data-availability-report.json (S3)
    ↓ IF overall_score ≥ 0.5 AND theoretical-prediction.json exists:
    │     ↓ DEEP CALL → Ouroboros → actual-observation-report.json (NEW L2)
    │     ↓ compute theory-data-validation-report.json (NEW L2)
    │     ↓ apply T uplift bonus/penalty to TDAL
    ↓ ELSE: skip deep call, theory_data_validation component = 0.5 (neutral)
    ↓ emit final TDAL with T uplift applied
    ↓
Phase 12: /paper-writing
    ↓ reads theory-data-validation-report.json → paper Validation section (NEW L2)
    ↓ Validation section structure:
    │     - headline (theory vs data agreement verdict)
    │     - quantitative match (predicted vs observed effect size)
    │     - qualitative match (regime coverage)
    │     - caveats (regime limits, extrapolation warnings)
```

**Deep call OPTIONAL triggers** (all three must hold):
1. `data-availability-report.json` exists AND `overall_score ≥ 0.5` (basic call found data)
2. `theoretical-prediction.json` exists AND derivation succeeded (Phase 6 PASS or PARTIAL)
3. `theory_only = false` (theory-only problems have no data to verify against)

If any trigger fails → skip deep call, T component = 0.5 neutral, `missing_inputs: ["theory_data_validation"]` caps TDAL verdict at MODERATE (per contract floor).

## Fallback (Deep Call Fails)

If the deep call is triggered but Ouroboros returns an error or no matching dataset:

1. `theory_data_validation` component = 0.3 (slight penalty — deep call was expected but failed)
2. `missing_inputs` lists `"theory_data_validation"`
3. TDAL verdict capped at MODERATE per contract floor (missing inputs non-empty)
4. Paper Validation section states: "External data validation was attempted but no matching dataset found in Ouroboros. Results rest on OSS-internal numerical sanity checks."
5. Pipeline continues — deep call failure is NOT BLOCK; it is surfaced honestly via the verdict cap.

## Boundaries

- **Basic and deep are separate calls.** Basic (Phase 2.5, availability) feeds D dimension; deep (Phase 10, validation) feeds T dimension uplift. Two distinct contracts, two distinct Ouroboros endpoints, two distinct artifacts. Never combine them.
- **Deep call OPTIONAL.** It only runs when basic call found data AND theory produced a prediction AND theory-only flag is false. Theory-only problems never invoke deep call — their T dimension rests on SymPy + logic alone.
- **T uplift is bounded.** The bonus cannot push T past 1.0; the penalty cannot push the component below 0.0. FALSIFIED_SIGN escalates to TDAL UNSUPPORTED — the deep call can FALSIFY a claim, not just confirm it.
- **Ouroboros must match the prediction's regime.** Pulling data from outside the theory's stated regime to falsify it is unfair — Ouroboros' `matched_datasets.regime_match` MUST align with `theoretical_prediction.regime_of_validity`.
- **The recommendation field is informational, not gating.** OSS reads structured fields (`fit_quality`, `sign_agreement`) and applies its own verdict from the locked table. Ouroboros' string recommendation goes into the paper for human readability but does NOT gate the pipeline.
- **Deep call failure is NOT BLOCK.** It caps the verdict at MODERATE (missing inputs) but the pipeline continues. Only FALSIFIED_SIGN escalates to UNSUPPORTED/BLOCK.
- **Theory-only problems get neutral T component.** `theory_data_validation = 0.5` is the honest middle — neither confirmed nor contradicted, because there is no data to compare against. This is NOT a penalty; it is the intended floor for theory-only work.

## Why this is "theory verification engine" positioning

The deep integration operationalizes the v2.7 strategic positioning ("OSS is not 'do research for you', it is 'verify your research idea against real data'"):

1. OSS produces a **falsifiable prediction** (Phase 6) — not a vague claim, but a structured prediction with sign, size, CI, regime.
2. Ouroboros finds **matching real data** — not cherry-picked data, but data within the theory's stated regime.
3. OSS computes a **joint validation report** — theory vs data agreement, with bounded T uplift.
4. The paper's Validation section **transparently reports** the match — readers see exactly what was predicted, what was observed, and the fit quality.

This is distinct from "AutoML runs experiments for you" (competitor positioning) — OSS does NOT run experiments; it verifies predictions against existing data. Distinct from "paper generator" — OSS does NOT write claims without evidence; the Validation section is gated by the joint report.

## See Also

- [`ouroboros-integration.md`](ouroboros-integration.md) — basic integration (S3, Phase 2.5 + D dimension); this L2 file is the deep complement
- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL schema; L2 adds the `theory_data_validation` T component (weight 0.2, redistributed)
- [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) — Phase 6 producer of `theoretical-prediction.json`
- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — Phase 10 producer of `theory-data-validation-report.json` + T uplift application
- [`../support/paper-writing/SKILL.md`](../support/paper-writing/SKILL.md) — Phase 12 consumer of validation report → paper Validation section
- [`../orchestrator/125-problems-pipeline/SKILL.md`](../orchestrator/125-problems-pipeline/SKILL.md) — phase wiring integration
