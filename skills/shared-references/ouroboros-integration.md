# Ouroboros Data-Insight Integration (SciForge-OSS)

> **Status**: Integration protocol between SciForge-OSS (theory verification) and Ouroboros Data-Insight (data availability & quality assessment). This bridges the gap between "theory that looks good" and "theory that can actually be verified with real data".
>
> **Core principle**: OSS handles theory derivation; Ouroboros handles data verification. Together they achieve 80-90% landing rate.

## Quick Reference

- **Purpose**: 连接 OSS 理论验证与 Ouroboros 数据验证，确保理论落地
- **OSS side**: 输出理论推导 + 数据需求清单
- **Ouroboros side**: 输入数据需求 → 返回数据可用性/质量报告
- **Output**: 联合置信度评分 (理论置信度 × 数据置信度)

## Integration Points

### Point 1: Data Requirement Specification (OSS → Ouroboros)

After Phase 2.5 (adversarial-falsification), OSS outputs a data requirement spec:

```json
{
  "data_requirements": {
    "problem_id": "Q001",
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
    }
  }
}
```

### Point 2: Data Availability Report (Ouroboros → OSS)

Ouroboros returns a data availability report:

```json
{
  "data_availability_report": {
    "problem_id": "Q001",
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
      }
    ],
    "recommendation": "Proceed with available data. Minor gap in industry_detail is acceptable."
  }
}
```

### Point 3: Joint Confidence Score

OSS combines its theoretical confidence with Ouroboros' data confidence:

```
joint_confidence = theoretical_confidence × data_availability_score × data_quality_score

Example:
  theoretical_confidence = 0.85 (from SymPy verification + logic audit)
  data_availability_score = 0.85 (from Ouroboros)
  data_quality_score = 0.85 (from Ouroboros)
  joint_confidence = 0.85 × 0.85 × 0.85 = 0.61

Interpretation:
  joint_confidence ≥ 0.7: STRONG — publishable with high confidence
  joint_confidence 0.5-0.7: MODERATE — publishable with caveats
  joint_confidence < 0.5: WEAK — needs more data or stronger theory
```

## Integration Workflow

```
Phase 2.5: /adversarial-falsification
    ↓
  Output: data_requirements.json
    ↓
  → Ouroboros Data-Insight
    ↓
  ← Ouroboros: data_availability_report.json
    ↓
Phase 10: /result-to-claim
    ↓
  Compute joint_confidence = theoretical × data_availability × data_quality
    ↓
Phase 12: /paper-writing
    ↓
  Include joint confidence in paper limitations section
```

## Fallback (No Ouroboros Available)

If Ouroboros is not available:
1. OSS uses its own data availability check (Phase 6 of adversarial-falsification)
2. Confidence is based on theory alone (theoretical_confidence only)
3. Paper MUST include "Data Limitations" section stating: "Data verification was not performed. Results are theoretical only."

## File Format

### OSS Output: `data-requirements.json`

```json
{
  "format_version": "1.0",
  "generated_by": "SciForge-OSS",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:00:00Z",
  "data_requirements": [...]
}
```

### Ouroboros Input: `data-availability-report.json`

```json
{
  "format_version": "1.0",
  "generated_by": "Ouroboros-Data-Insight",
  "problem_id": "Q001",
  "timestamp": "2026-07-21T10:05:00Z",
  "overall_score": 0.85,
  "datasets": [...]
}
```

## See Also

- [`../support/adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — produces data requirements
- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — computes joint confidence
- [`../shared-references/fantasy-prevention.md`](fantasy-prevention.md) — Gate 5: Data Availability