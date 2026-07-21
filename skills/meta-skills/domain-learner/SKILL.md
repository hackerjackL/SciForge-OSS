---
name: domain-learner
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
- Query: "common research methods in economics causal inference"
- Results: DiD (50%), IV (30%), RDD (20%) — from 50 papers surveyed
- Source: Journal of Economic Literature surveys

### Search 2: "common failure modes in [domain]"
- Query: "common pitfalls in economics causal inference"
- Results: endogeneity (60%), omitted variable bias (25%), selection bias (15%)
- Source: Angrist & Pischke "Mostly Harmless Econometrics"

### Search 3: "standard paper structure in [domain]"
- Query: "AER paper structure format"
- Results: Introduction → Theory → Empirical Strategy → Results → Robustness → Conclusion
- Source: American Economic Review author guidelines
```

### Step 2: Seed Paper Analysis

If the user provided seed papers or the problem references known works:

```markdown
## Seed Paper Analysis

### Paper 1: Card & Krueger (1994)
- Title: "Minimum Wages and Employment: A Case Study..."
- Journal: American Economic Review
- Methodology: Difference-in-Differences
- Structure: Introduction → Background → Empirical Strategy → Results → Conclusion
- Citations: author-year (AER style)
- Key robustness checks: placebo test, specification checks

### Paper 2: Angrist & Pischke (2009)
- Type: Methodology textbook
- Methods: IV, DiD, RDD, panel data
- Common failures: endogeneity, weak instruments, measurement error
```

### Step 3: Synthesize Domain Profile

```json
{
  "learner_version": "2.0",
  "learning_method": "literature_search + seed_analysis",
  "sources_consulted": [
    "Journal of Economic Literature",
    "Angrist & Pischke (2009)",
    "Card & Krueger (1994)"
  ],
  "learning_confidence": 0.85,
  "domain_profile": {
    "primary_domain": "economics",
    "evidence_type": "causal_inference",
    "reasoning_paradigm": "empirical"
  },
  "methodology_profile": {
    "standard_methods": ["difference_in_differences", "instrumental_variables", "regression_discontinuity"],
    "method_frequencies": {"DiD": 0.50, "IV": 0.30, "RDD": 0.20},
    "verification_approach": "numerical_simulation",
    "learning_basis": "literature survey of 50 papers"
  },
  "failure_mode_profile": {
    "common_failures": ["endogeneity", "omitted_variable_bias", "selection_bias"],
    "failure_frequencies": {"endogeneity": 0.60, "OVB": 0.25, "selection": 0.15},
    "learning_basis": "Angrist & Pischke common pitfalls"
  },
  "writing_profile": {
    "style": "empirical_economics",
    "citation_format": "author_year",
    "section_structure": "introduction → theory → empirical_strategy → results → robustness → conclusion",
    "learning_basis": "AER author guidelines + 50 paper survey"
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