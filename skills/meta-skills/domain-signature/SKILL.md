---
name: domain-signature
version: 1.7.2
description: "Fast-path rule-based domain signature hint — Phase 1a (OPTIONAL). Writes domain-signature-hint.json consumed only by domain-learner as a prior. Invoke for cold-start domain detection when literature is sparse."
type: meta-skill
role: domain-characteristic-extractor
---

# Domain Signature Extraction (SciForge-OSS — Automatic Domain Characteristic Discovery)

> **Status (v2.8 — downgraded to OPTIONAL hint)**: Automatically extracts domain characteristics from the problem statement via **rule-based** matching. Output is a **hint file** (`domain-signature-hint.json`) consumed ONLY by `/domain-learner` as a prior — NOT directly by downstream skills. The learner (`/domain-learner`, Phase 1b) is the sole source of truth writing `domain-signature.json`. This skill runs as an OPTIONAL fast-path to seed the learner; if the learner is unavailable or confidence is low, downstream skills use defaults (the hint is never a fallback signature).
>
> **Core philosophy**: Do NOT hard-code domain classification. Let the agent discover domain characteristics at runtime from the problem's own language, literature, and structure.

## Quick Reference

- **Purpose**: Auto-extract a domain hint (rule-based) → prior for the learner only
- **Input**: Problem description + seed literature + user prompt
- **Output**: refine-logs/domain-signature-hint.json (hint file, not consumed directly downstream)
- **Key**: v2.8 downgraded to OPTIONAL fast path; downstream skills never read the hint, only the learner-written domain-signature.json. v6.0: the hint MAY carry a coarse `evidence_norm_profile`, but it is advisory prior only — the learner re-derives evidence norms from literature and always wins

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
- **Domain keywords**: [time-series, trend, periodicity, anomaly, signal]
- **Methodology keywords**: [detrending, spectral analysis, thresholding, model fitting]
- **Evidence keywords**: [residual, uncertainty, confidence interval, goodness-of-fit]
- **Output keywords**: [trend decomposition, anomaly flag, parameter estimate]

### Inferred Signals
- **Reasoning style**: empirical / formal / interpretive / design
- **Formality level**: high / medium / low
- **Quantitative intensity**: high / medium / low
- **Proof standard**: statistical / derivational / argumentative

### Literature Signals
- **Seed paper venues**: [general scientific journals, measurement-notes, data-repository publications]
- **Seed paper methods**: [detrending, spectral analysis, threshold-based anomaly detection]
- **Citation style**: [author-year, Harvard]
```

### Step 2: Generate Domain Signature

```json
{
  "signature_id": "sig_20260720_001",
  "problem_id": "Q001",
  "domain_profile": {
    "primary_domain": "time_series_analysis",
    "secondary_domains": ["statistics", "physics_measurement"],
    "evidence_type": "empirical_measurement",
    "reasoning_paradigm": "empirical"
  },
  "methodology_profile": {
    "standard_methods": ["detrending", "spectral_analysis", "threshold_based_detection"],
    "verification_approach": "numerical_simulation",
    "requires_experiment": false,
    "can_be_theory_only": false
  },
  "writing_profile": {
    "style": "empirical_measurement",
    "citation_format": "author_year",
    "section_structure": "introduction → model → measurement → analysis → discussion",
    "typical_length": "12-20 pages",
    "abstract_style": "motivation → method → main_result → implication"
  },
  "failure_mode_profile": {
    "common_failures": ["sensor_noise", "non_stationarity", "edge_effects", "aliasing"],
    "critical_assumptions": ["stationarity", "error_whiteness", "adequate_sampling_rate"],
    "robustness_checks": ["residual_test", "cross_validation", "different_preprocessing"]
  },
  "data_profile": {
    "data_type": "time_series",
    "typical_sources": ["sensor arrays", "public measurement repositories", "instrument logs"],
    "data_availability": "high",
    "min_sample_size": "500 time points"
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
| `causal_inference` | Causal inference, requires an identification strategy | Economics, econometrics, epidemiology |
| `correlational` | Correlational analysis, no causality required | Sociology, psychology, education |
| `derivational` | Derivation proofs, no data required | Mathematics, theoretical physics, theoretical CS |
| `experimental` | Controlled experiments, randomized controls | Medicine, biology, psychology |
| `simulational` | Numerical simulation, no real data | Physics, climate, engineering |
| `interpretive` | Textual interpretation, argument analysis | Humanities, law, philosophy |

#### Methodology Pattern Detection

| Pattern | Detected From | Typical Domains |
|---------|--------------|-----------------|
| `difference_in_differences` | "treatment group", "control group", "pre-post" | Economics, policy evaluation |
| `instrumental_variables` | "instrument", "exogenous variation", "2SLS" | Economics, econometrics |
| `structural_equation` | "SEM", "path analysis", "latent variable" | Psychology, sociology |
| `machine_learning` | "neural network", "training", "test set" | CS, engineering, bioinformatics |
| `theorem_proof` | "theorem", "lemma", "proof", "proposition" | Mathematics, theoretical CS |
| `controlled_trial` | "RCT", "randomized", "placebo", "double-blind" | Medicine, clinical |

### Step 4: Consume Signature

The **hint** is written to `refine-logs/domain-signature-hint.json` and consumed ONLY by `/domain-learner` (Phase 1b) as a prior. It is **NOT** consumed directly by downstream skills — the learner is the sole source of truth that writes `refine-logs/domain-signature.json`. (v2.8 alignment: this skill is an OPTIONAL fast-path hint, never the final signature.)

| Downstream Skill | How It Uses the Learner Signature |
|-----------------|-----------------------------------|
| `/idea-discovery` | Adjusts perspective weights based on evidence type |
| `/adversarial-falsification` | Adds domain-specific failure modes to attack vectors |
| `/novelty-check` | Adjusts novelty thresholds based on domain norms |
| `/theory-derivation` | Selects verification approach (derivation vs simulation vs none) |
| `/paper-writing` | Selects writing style, citation format, section structure; applies domain-specific writing conventions per [`discipline-writing.md`](../../shared-references/discipline-writing.md) (a shared reference, not a standalone skill in OSS) |
| `/result-to-claim` | Calibrates confidence based on domain feasibility |

> **Note**: These consumers read `domain-signature.json` (learner output), NOT the hint file produced here.

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