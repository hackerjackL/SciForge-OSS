# Ouroboros Data-Insight Integration (SciForge-OSS — v2.8 TDAL-aligned)

> **Status (v2.8 — basic integration, TDAL-aligned)**: Integration protocol between SciForge-OSS (theory verification) and Ouroboros Data-Insight (data availability & quality assessment). This bridges the gap between "theory that looks good" and "theory that can actually be verified with real data". **v2.8 change**: the joint confidence formula now lives in [`domain-adaptation-contract.md`](domain-adaptation-contract.md) as the locked TDAL schema — Ouroboros feeds **only the D dimension** (`data_availability`), not a separate triple-product. This file defines the wiring: data-requirements spec → Ouroboros call → data-availability report → TDAL D dimension.
>
> **Core principle**: OSS handles theory derivation; Ouroboros handles data verification. Together they feed the 4-dimensional TDAL joint confidence. OSS never re-derives data availability — it consumes Ouroboros' `overall_score`.

## Quick Reference

- **Purpose**: 连接 OSS 理论验证与 Ouroboros 数据验证，填充 TDAL 的 D 维
- **OSS side**: 输出理论推导 + 数据需求清单 (`data-requirements.json`)
- **Ouroboros side**: 输入数据需求 → 返回数据可用性/质量报告 (`data-availability-report.json`)
- **Output**: TDAL `data_availability` dimension value (consumed by `/result-to-claim`, Phase 10)
- **Key**: v2.8 起不另算 joint confidence；Ouroboros 只产 D 维原始数据，TDAL 公式在 contract 里锁定

## Phase Wiring (v2.8 — three integration points)

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: problem understanding (basic layer — NEW v2.8)       │
│    → OSS parses problem for "data-relevant" signals             │
│    → emits refine-logs/data-requirements-seed.json             │
│      (early hint: which variables/datasets the problem implies) │
│    → NOT a full requirement spec yet — just a seed             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2.5: adversarial-falsification                          │
│    → OSS finalizes data-requirements.json (full spec)          │
│      from the seed + falsification exposure of data gaps       │
│    → emits data-requirements.json to refine-logs/              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼  (call Ouroboros)
┌─────────────────────────────────────────────────────────────────┐
│  Ouroboros Data-Insight                                         │
│    → reads data-requirements.json                               │
│    → returns data-availability-report.json                      │
│      (overall_score 0-1 + per-dataset quality + gaps)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 10: result-to-claim                                      │
│    → reads data-availability-report.json                        │
│    → feeds overall_score into TDAL D dimension:                 │
│        D = 0.5×ouroboros_score                                  │
│          + 0.3×oss_data_check                                   │
│          + 0.2×theory_only_flag                                 │
│    → TDAL schema in domain-adaptation-contract.md               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 12: paper-writing                                        │
│    → TDAL verdict → Confidence & Limitations section            │
│    → D dimension reported explicitly                            │
│    → data gaps from Ouroboros → Limitations enumeration         │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Point 1: Data Requirement Seed (Phase 1 — basic layer, NEW v2.8)

**Producer**: OSS Phase 1 (problem understanding) — emits an early *seed* of data requirements, NOT a full spec. This lets Ouroboros warm-start before Phase 2.5 finalizes.

### `refine-logs/data-requirements-seed.json`

```json
{
  "format_version": "1.0",
  "generated_by": "SciForge-OSS Phase 1",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:00:00Z",
  "seed_type": "early_hint",
  "data_relevant": true,
  "implied_variables": [
    {
      "name": "wage",
      "evidence": "problem text mentions 'employment effect'",
      "confidence": 0.6
    },
    {
      "name": "min_wage_policy",
      "evidence": "problem text mentions 'policy intervention'",
      "confidence": 0.7
    }
  ],
  "implied_datasets": [
    {
      "name": "labor_panel",
      "type": "panel_data",
      "evidence": "causal-inference signal + longitudinal variables",
      "confidence": 0.5
    }
  ],
  "theory_only_candidate": false,
  "open_questions": [
    "Is the policy intervention real or hypothetical?",
    "Are longitudinal observations required or cross-sectional suffices?"
  ]
}
```

**Phase 1 contract**:
- Emit `data-requirements-seed.json` for EVERY problem (even theory-only — `theory_only_candidate: true` flags the no-data path early).
- Mark `data_relevant: false` if the problem is clearly theory-only (math/proof problem). Ouroboros will NOT be called in Phase 2.5; TDAL D dimension falls back to `theory_only_flag: 1.0` reward.
- Mark `data_relevant: true` if any variable evidence has confidence ≥ 0.5. Ouroboros WILL be called in Phase 2.5.
- `open_questions` MUST be surfaced to the human if blocking — but the seed is provisional, not blocking.

**Consumer**: Phase 2.5 (`/adversarial-falsification`) reads the seed and finalizes the full `data-requirements.json` after falsification exposes data gaps. Ouroboros does NOT consume the seed directly — only the finalized spec.

## Integration Point 2: Full Data Requirement Spec (Phase 2.5 → Ouroboros)

**Producer**: OSS Phase 2.5 — finalizes the full data requirement spec from the seed + falsification exposure.

### `refine-logs/data-requirements.json`

```json
{
  "format_version": "1.0",
  "generated_by": "SciForge-OSS Phase 2.5",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:02:00Z",
  "spec_type": "finalized",
  "data_requirements": {
    "theory_type": "causal_inference",
    "required_datasets": [
      {
        "name": "CPS_2023",
        "type": "panel_data",
        "variables": ["wage", "employment", "state", "year", "industry"],
        "min_observations": 10000,
        "expected_source": "Current Population Survey",
        "publicly_available": true
      },
      {
        "name": "MW_data",
        "type": "policy_data",
        "variables": ["min_wage", "state", "year"],
        "min_observations": 500,
        "expected_source": "Department of Labor",
        "publicly_available": true
      }
    ],
    "simulation_alternative": {
      "possible": true,
      "method": "synthetic_data_generation",
      "parameters": ["mean_wage", "variance", "treatment_effect_size"]
    },
    "falsification_exposed_gaps": [
      {
        "gap": "control_group_for_parallel_trends",
        "severity": "major",
        "falsification_round": 2
      }
    ]
  }
}
```

**Phase 2.5 contract**:
- If `seed.theory_only_candidate == true` AND falsification did NOT surface a data need → finalize as `theory_only: true`, do NOT call Ouroboros. Phase 10's TDAL D dimension: `theory_only_flag: 1.0`, `ouroboros_report: 0.0` (component absent, weight 0.5 → contributes 0), `oss_data_check: 1.0` (no data needed = ready). D = 0.5×0 + 0.3×1.0 + 0.2×1.0 = 0.5. **This is the intended floor for theory-only problems — D cannot exceed 0.5 without real data.**
- If `seed.data_relevant == true` AND falsification confirmed → finalize full spec, call Ouroboros.
- `falsification_exposed_gaps` MUST be forwarded to Ouroboros so it can flag them in its availability report.

## Integration Point 3: Data Availability Report (Ouroboros → OSS Phase 10)

**Producer**: Ouroboros Data-Insight — returns availability + quality assessment.

### `refine-logs/data-availability-report.json`

```json
{
  "format_version": "1.0",
  "generated_by": "Ouroboros-Data-Insight",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:05:00Z",
  "overall_score": 0.85,
  "datasets": [
    {
      "name": "CPS_2023",
      "status": "available",
      "quality_score": 0.92,
      "missing_variables": [],
      "sample_size": 85000,
      "coverage": "national_representative"
    },
    {
      "name": "MW_data",
      "status": "available",
      "quality_score": 0.78,
      "missing_variables": ["industry_detail"],
      "sample_size": 1200,
      "coverage": "state_level"
    }
  ],
  "data_gaps": [
    {
      "variable": "industry_detail",
      "severity": "minor",
      "alternative": "use industry_aggregate instead"
    },
    {
      "gap": "control_group_for_parallel_trends",
      "severity": "major",
      "alternative": "synthetic control method",
      "source": "forwarded from falsification_exposed_gaps"
    }
  ],
  "recommendation": "Proceed with available data. Minor gap in industry_detail acceptable; major gap in control_group needs synthetic control alternative."
}
```

**Phase 10 consumption contract** (TDAL D dimension — see [`domain-adaptation-contract.md`](domain-adaptation-contract.md)):
- Read `overall_score` from the report → feeds TDAL `data_availability.components.ouroboros_report.score` (weight 0.5).
- Read `data_gaps` → forward to Phase 12 paper Limitations section as enumerated data limitations.
- If report absent (Ouroboros unavailable): `ouroboros_report.score = 0.0`, append `"ouroboros_report"` to TDAL `missing_inputs`.

## TDAL D Dimension Wiring (v2.8 — replaces the old triple-product)

**OLD (v2.5–v2.7, DEPRECATED)**:
```
joint_confidence = theoretical × data_availability × data_quality
```

**NEW (v2.8, LOCKED in domain-adaptation-contract.md)**:
```
TDAL joint = T × D × A × L

where D (data_availability) =
    0.5 × ouroboros_report.score
  + 0.3 × oss_data_check.score
  + 0.2 × theory_only_flag.score
```

Ouroboros now feeds **only the D dimension's 0.5-weight component** — it does NOT compute a separate `data_quality_score` or its own joint. The `overall_score` already integrates per-dataset quality into a single 0-1 number; feeding both `availability` and `quality` separately would double-count. The TDAL schema in [`domain-adaptation-contract.md`](domain-adaptation-contract.md) is the single source of truth for the joint.

### Worked Example (v2.8)

```
Scenario: causal-inference problem, Ouroboros called, overall_score = 0.85, OSS data check = DATA_READY, theory-only = false

D dimension:
  ouroboros_report:  0.5 × 0.85 = 0.425
  oss_data_check:    0.3 × 1.0  = 0.300
  theory_only_flag:  0.2 × 0.0  = 0.000
  D = 0.425 + 0.300 + 0.000 = 0.725

Full TDAL (example):
  T = 0.85, D = 0.725, A = 0.80, L = 0.755
  joint = 0.85 × 0.725 × 0.80 × 0.755 = 0.37 → WEAK
```

### Theory-only Worked Example

```
Scenario: pure math problem, Ouroboros NOT called, theory-only = true

D dimension:
  ouroboros_report:  0.5 × 0.0  = 0.000  (no report, component absent)
  oss_data_check:    0.3 × 1.0  = 0.300  (no data needed = ready)
  theory_only_flag:  0.2 × 1.0  = 0.200  (reward for not needing data)
  D = 0.000 + 0.300 + 0.200 = 0.500

This is the intended D-floor for theory-only problems — no real data, D capped at 0.5.
TDAL joint with T=0.95, A=0.85, L=0.70: 0.95 × 0.50 × 0.85 × 0.70 = 0.28 → UNSUPPORTED
(Theory-only math papers need very strong T+A+L to clear STRONG; the D floor enforces honesty.)
```

## Fallback (Ouroboros Unavailable)

If Ouroboros is not available (network error, service down, not configured):

1. OSS Phase 2.5 still finalizes `data-requirements.json` (the spec is produced regardless).
2. Phase 10 sets `ouroboros_report.score = 0.0` and appends `"ouroboros_report"` to TDAL `missing_inputs`.
3. `missing_inputs` non-empty → TDAL verdict capped at MODERATE (per contract floor constraints) — even if T+A+L are all STRONG, the missing Ouroboros data inspection prevents a STRONG verdict.
4. Paper Limitations section MUST state: "Data availability was not externally verified (Ouroboros unavailable). Results are grounded on OSS internal data checks only."
5. The pipeline does NOT block on Ouroboros absence — it surfaces honestly via the verdict cap.

## File Inventory

| File | Producer | Consumer | Phase |
|------|----------|----------|-------|
| `refine-logs/data-requirements-seed.json` | OSS Phase 1 | OSS Phase 2.5 | 1 → 2.5 |
| `refine-logs/data-requirements.json` | OSS Phase 2.5 | Ouroboros | 2.5 → Ouroboros |
| `refine-logs/data-availability-report.json` | Ouroboros | OSS Phase 10 | Ouroboros → 10 |
| `CLAIMS_FROM_RESULTS.md` (TDAL block) | OSS Phase 10 | OSS Phase 12 | 10 → 12 |

## Boundaries

- **Ouroboros feeds only D dimension.** It does NOT compute the TDAL joint — that is `/result-to-claim`'s sole job per the producer contract.
- **The seed (Phase 1) is provisional.** Ouroboros MUST NOT consume the seed directly; only the finalized spec from Phase 2.5.
- **Theory-only is a first-class path.** D is capped at 0.5 for theory-only problems by design — this is not a failure, it's honesty about the lack of empirical data.
- **Missing Ouroboros caps the verdict at MODERATE.** The pipeline continues but the paper cannot claim STRONG without external data verification.
- **Never feed both `overall_score` and a separate `data_quality_score` into TDAL.** Ouroboros' `overall_score` already integrates quality; double-counting would inflate D.

## See Also

- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL 4-dim locked schema (D dimension definition)
- [`../support/adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — produces data-requirements.json (Phase 2.5)
- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — consumes data-availability-report.json into TDAL D (Phase 10)
- [`../orchestrator/125-problems-pipeline/SKILL.md`](../orchestrator/125-problems-pipeline/SKILL.md) — phase wiring
- [`fantasy-prevention.md`](fantasy-prevention.md) — Gate 5: Data Availability (complementary anti-hallucination gate)
