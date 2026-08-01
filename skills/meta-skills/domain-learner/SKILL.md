---
name: domain-learner
description: "Learn a discipline's signature (evidence_type, methodology, writing style, failure modes) from literature — Phase 1b, sole writer of domain-signature.json. Invoke when the pipeline needs domain adaptation for a new problem."
type: meta-skill
role: domain-characteristic-learner
---

# Domain Learner (SciForge-OSS — Automatic Domain Characteristic Learning)

> **Status**: Automatically learns domain characteristics from literature, problem analysis, and seed papers. Unlike `/domain-signature` which uses hardcoded rules, this skill **learns** from scratch every time it runs.
>
> **Core principle**: Do NOT pre-define domain characteristics. Search the literature, analyze the problem, and LEARN what makes this domain unique.

## Quick Reference

- **Purpose**: 从文献中自动学习领域特性，替代硬编码签名
- **Input**: 问题描述 + 种子文献
- **Output**: refine-logs/domain-signature.json (覆盖规则签名，供下游统一消费)
- **Key**: 每次运行从零学习，不依赖预定义规则；输出路径与 /domain-signature 一致以保证下游无缝消费

## How It Works

```
Step 1: Search literature for domain characteristics
  → "What are the standard methods in [domain]?"
  → "What are the common failure modes in [domain]?"
  → "What is the standard paper structure for [domain]?"

Step 2: Analyze seed papers
  → Read 3-5 seed papers from the problem
  → Extract: methodology, writing style, citation format, failure modes

Step 3: Synthesize domain profile
  → Combine literature search + seed paper analysis
  → Output: structured domain profile

Step 4: All downstream skills consume the profile
  → Same as domain-signature consumer protocol
  → But the profile is LEARNED, not hardcoded
```

## Workflow

### Step 1: Literature Search for Domain Characteristics

Search the literature using `/universal-retrieval`:

```markdown
## Literature Search Results

### Search 1: "standard methodologies in [domain]"
- Query: "common signal-processing methods in time-series anomaly detection"
- Results: spectral methods (40%), statistical thresholding (35%), model-based filtering (25%) — from 50 papers surveyed
- Source: signal-processing / time-series analysis methodological reviews

### Search 2: "common failure modes in [domain]"
- Query: "common pitfalls in time-series periodicity and anomaly analysis"
- Results: sensor noise/aliasing (45%), non-stationarity (35%), edge effects (20%)
- Source: measurement-science and signal-analysis surveys

### Search 3: "standard paper structure in [domain]"
- Query: "typical structure of a physics/datalab measurement study"
- Results: Problem → Model/Hypothesis → Measurement → Analysis → Robustness → Conclusion
- Source: measurement-physics and applied-lab author guidelines
```

### Step 2: Seed Paper Analysis

If the user provided seed papers or the problem references known works:

```markdown
## Seed Paper Analysis

### Paper 1: "Damped Oscillator Parameter Estimation from Noisy Time Series"
- Title: "Recovering damping ratio and natural frequency from short, noisy records"
- Venue: Applied Physics Letters (measurement-notes style)
- Methodology: nonlinear least-squares fit of an analytical oscillator model
- Structure: Intro → Model → Acquisition → Fit → Uncertainty → Conclusion
- Citations: author-year (physical-sciences style)
- Key robustness checks: residual whiteness test, cross-validated fit, multiple trials

### Paper 2: "Material Degradation Modeling over Exposure Time"
- Type: Empirical methodology study
- Methods: exponential/logistic growth-curve fitting, uncertainty propagation, sensitivity analysis
- Common failures: measurement drift, instrument calibration bias, truncation of long-term trends
```

### Step 3: Synthesize Domain Profile

```json
{
  "learner_version": "2.0",
  "learning_method": "literature_search + seed_analysis",
  "sources_consulted": [
    "Signal-processing methodological review (50 papers)",
    "Measurement-physics study (oscillator parameter estimation)",
    "Material-science degradation modeling study"
  ],
  "learning_confidence": 0.85,
  "domain_profile": {
    "primary_domain": "physics_measurement",
    "evidence_type": "empirical_measurement",
    "reasoning_paradigm": "empirical"
  },
  "methodology_profile": {
    "standard_methods": ["model_based_fitting", "spectral_analysis", "statistical_thresholding"],
    "method_frequencies": {"model_based_fitting": 0.40, "spectral_analysis": 0.35, "statistical_thresholding": 0.25},
    "verification_approach": "numerical_simulation",
    "learning_basis": "literature survey of 50 papers"
  },
  "failure_mode_profile": {
    "common_failures": ["sensor_noise", "non_stationarity", "edge_effects"],
    "failure_frequencies": {"sensor_noise": 0.45, "non_stationarity": 0.35, "edge_effects": 0.20},
    "learning_basis": "signal-analysis common pitfalls"
  },
  "writing_profile": {
    "style": "empirical_measurement",
    "citation_format": "author_year",
    "section_structure": "introduction → model → measurement → analysis → robustness → conclusion",
    "learning_basis": "measurement-physics author guidelines + 50 paper survey"
  }
}
```

### Step 4: Handle Learning Failure

If literature search returns no results:

```markdown
## Learning Failure Report

### Searches Attempted
1. "standard methodologies in [domain]" → 0 results
2. "common failure modes in [domain]" → 0 results
3. "standard paper structure in [domain]" → 0 results

### Fallback
Using default domain profile (general academic).
Logging: "WARNING: Domain learner could not find specific characteristics for [domain].
Using general defaults. Consider adding seed papers for better results."

### Suggested Action
User may want to provide 2-3 seed papers from the target domain
for better domain adaptation.
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `learning_mode` | enum | `literature` | `literature` (search APIs), `seed_only` (papers only), `hybrid` (both) |
| `min_papers_for_learning` | int | `3` | Minimum number of papers to analyze for reliable learning |
| `confidence_threshold` | float | `0.7` | Minimum confidence to apply learned characteristics |
| `fallback_to_default` | bool | `true` | Whether to use default profile if learning fails |

## Output Shape

- `refine-logs/domain-signature.json` — learned domain profile (覆盖 /domain-signature 的低置信输出，被所有下游 skill 统一消费；schema 与 /domain-signature 兼容)
- `refine-logs/domain-learning-log.md` — detailed learning log (searches, analyses, synthesis)

## Boundaries

- **Never hardcode domain characteristics.** The learner starts from zero every time.
- **Learning confidence < 0.7** → Use defaults, do NOT apply learned characteristics.
- **Seed papers > literature search** when both are available. The most reliable signal.
- **The learner is the single source of truth (v2.8).** Phase 1a (`/domain-signature`) only writes a hint file (`domain-signature-hint.json`) consumed as a prior; the learner is the sole writer of `domain-signature.json` and the only signature downstream skills consume. If the learner fails entirely, downstream skills use default behavior — the hint is never consumed directly.

## See Also

- [`../shared-references/domain-signature-consumer.md`](../../shared-references/domain-signature-consumer.md) — how downstream skills consume the learned profile
- [`../shared-references/domain-failure-modes.md`](../../shared-references/domain-failure-modes.md) — pre-defined failure mode catalog (used when learner fails)
- [`../shared-references/domain-adaptation-guide.md`](../../shared-references/domain-adaptation-guide.md) — Section B worked examples + Section C acceptance tests for verification