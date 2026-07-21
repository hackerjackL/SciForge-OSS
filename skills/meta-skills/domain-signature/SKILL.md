---
name: domain-signature
type: meta-skill
role: domain-characteristic-extractor
---

# Domain Signature Extraction (SciForge-OSS — Automatic Domain Characteristic Discovery)

> **Status (v2.8 — downgraded to OPTIONAL hint)**: Automatically extracts domain characteristics from the problem statement via **rule-based** matching. Output is a **hint file** (`domain-signature-hint.json`) consumed ONLY by `/domain-learner` as a prior — NOT directly by downstream skills. The learner (`/domain-learner`, Phase 1b) is the sole source of truth writing `domain-signature.json`. This skill runs as an OPTIONAL fast-path to seed the learner; if the learner is unavailable or confidence is low, downstream skills use defaults (the hint is never a fallback signature).
>
> **Core philosophy**: Do NOT hard-code domain classification. Let the agent discover domain characteristics at runtime from the problem's own language, literature, and structure.

## Quick Reference

- **Purpose**: 自动提取领域 hint (rule-based) → 仅供 learner 作 prior
- **Input**: 问题描述 + 种子文献 + 用户提示词
- **Output**: refine-logs/domain-signature-hint.json (hint 文件，非下游消费源)
- **Key**: v2.8 降级为 OPTIONAL 快路径；下游 skill 不直接读 hint，只读 learner 输出的 domain-signature.json

## Use When

Use this skill automatically in Phase 1 (problem understanding) of the orchestrator. It runs before any other downstream skill.

## Job

Analyze the problem statement and extract a structured domain signature. The signature captures:

1. **Evidence type**: What kind of evidence does this domain typically accept?
2. **Methodology patterns**: What research methods are standard in this domain?
3. **Writing conventions**: What writing style does this domain expect?
4. **Citation norms**: How are citations formatted in this domain?
5. **Failure modes**: What are the typical failure modes in this domain?
6. **Data availability**: Can the required data be obtained?

## Workflow

### Step 1: Analyze Problem Statement

Read the problem statement and extract domain signals:

```markdown
## Domain Signal Analysis

### Direct Signals
- **Domain keywords**: [economics, regression, causal, treatment, effect]
- **Methodology keywords**: [DiD, IV, RDD, panel data]
- **Evidence keywords**: [estimate, significance, confidence interval]
- **Output keywords**: [policy recommendation, causal claim]

### Inferred Signals
- **Reasoning style**: empirical / formal / interpretive / design
- **Formality level**: high / medium / low
- **Quantitative intensity**: high / medium / low
- **Proof standard**: statistical / derivational / argumentative

### Literature Signals
- **Seed paper venues**: [AER, QJE, Econometrica]
- **Seed paper methods**: [difference-in-differences, instrumental variables]
- **Citation style**: [author-year, Harvard]
```

### Step 2: Generate Domain Signature

```json
{
  "signature_id": "sig_20260720_001",
  "problem_id": "Q001",
  "domain_profile": {
    "primary_domain": "economics",
    "secondary_domains": ["statistics", "social_science"],
    "evidence_type": "causal_inference",
    "reasoning_paradigm": "empirical"
  },
  "methodology_profile": {
    "standard_methods": ["difference_in_differences", "instrumental_variables", "regression_discontinuity"],
    "verification_approach": "numerical_simulation",
    "requires_experiment": false,
    "can_be_theory_only": true
  },
  "writing_profile": {
    "style": "empirical_economics",
    "citation_format": "author_year",
    "section_structure": "introduction → theory → empirical_strategy → results → discussion",
    "typical_length": "25-35 pages",
    "abstract_style": "motivation → method → main_result → implication"
  },
  "failure_mode_profile": {
    "common_failures": ["endogeneity", "omitted_variable_bias", "reverse_causality", "measurement_error"],
    "critical_assumptions": ["exclusion_restriction", "parallel_trends", "no_spillover"],
    "robustness_checks": ["placebo_test", "different_specifications", "subsample_analysis"]
  },
  "data_profile": {
    "data_type": "panel_data",
    "typical_sources": ["World Bank", "PSID", "CPS", "Compustat"],
    "data_availability": "high",
    "min_sample_size": "1000 observations"
  },
  "confidence": {
    "domain_confidence": 0.85,
    "methodology_confidence": 0.75,
    "writing_confidence": 0.80
  }
}
```

### Step 3: Signature Dimension Details

#### Evidence Type Classification

| Evidence Type | Description | Example Domains |
|--------------|-------------|-----------------|
| `causal_inference` | 因果推断，需要识别策略 | 经济学、计量、流行病学 |
| `correlational` | 相关性分析，无需因果 | 社会学、心理学、教育学 |
| `derivational` | 推导证明，无需数据 | 数学、理论物理、理论 CS |
| `experimental` | 控制实验，随机对照 | 医学、生物学、心理学 |
| `simulational` | 数值模拟，无真实数据 | 物理、气候、工程 |
| `interpretive` | 文本解释，论证分析 | 人文、法学、哲学 |

#### Methodology Pattern Detection

| Pattern | Detected From | Typical Domains |
|---------|--------------|-----------------|
| `difference_in_differences` | "treatment group", "control group", "pre-post" | 经济学、政策评估 |
| `instrumental_variables` | "instrument", "exogenous variation", "2SLS" | 经济学、计量 |
| `structural_equation` | "SEM", "path analysis", "latent variable" | 心理学、社会学 |
| `machine_learning` | "neural network", "training", "test set" | CS、工程、生物信息 |
| `theorem_proof` | "theorem", "lemma", "proof", "proposition" | 数学、理论 CS |
| `controlled_trial` | "RCT", "randomized", "placebo", "double-blind" | 医学、临床 |

### Step 4: Consume Signature

The domain signature is written to `refine-logs/domain-signature.json` and consumed by all downstream skills:

| Downstream Skill | How It Uses the Signature |
|-----------------|--------------------------|
| `/idea-discovery` | Adjusts perspective weights based on evidence type |
| `/adversarial-falsification` | Adds domain-specific failure modes to attack vectors |
| `/novelty-check` | Adjusts novelty thresholds based on domain norms |
| `/theory-derivation` | Selects verification approach (derivation vs simulation vs none) |
| `/paper-writing` | Selects writing style, citation format, section structure |
| `/discipline-writing` | Applies domain-specific writing conventions |
| `/result-to-claim` | Calibrates confidence based on domain feasibility |

## Boundaries

- **Never hard-code domain-to-signature mapping.** The signature is extracted from the problem text, not from a classification table.
- **Domain signature is not a label.** It's a set of probabilistic signals. A problem can have mixed signatures (e.g., computational biology = CS + biology).
- **If confidence < 0.5**, use the default `general` signature — no domain-specific adaptation.
- **The signature is always provisional.** Downstream skills can refine it if they detect better signals.

## Output Shape

- `refine-logs/domain-signature.json` — the domain signature JSON
- `refine-logs/domain-signature-report.md` — human-readable explanation of the signature

## See Also

- [`../shared-references/domain-failure-modes.md`](../../shared-references/domain-failure-modes.md) — domain-specific failure mode catalog
- [`../shared-references/discipline-paradigm.md`](../../shared-references/discipline-paradigm.md) — 4 research paradigms
- [`../shared-references/discipline-writing.md`](../../shared-references/discipline-writing.md) — writing guide consumed by signature