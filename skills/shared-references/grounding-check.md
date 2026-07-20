# Grounding Checklist (SciForge-OSS — Practicality Assurance)

> **Status**: Mandatory pre-publication checklist that ensures every theoretical result has been assessed for **practical landing probability**. This is the bridge between "theoretically sound" and "likely to work in practice."
>
> The core insight: **a mathematically perfect derivation on unrealistic assumptions produces zero real-world value.** This checklist catches that gap.

## When to Use

- **MANDATORY**: After `/result-to-claim` produces `CLAIMS_FROM_RESULTS.md`, before `/paper-writing` begins
- **MANDATORY**: When confidence assessment shows grounding confidence < theoretical confidence
- **RECOMMENDED**: During `/auto-review-loop` for any paper with theory-only claims

## The Grounding Checklist

### 1. Assumption Realism

| Check | Description | Verdict |
|-------|-------------|---------|
| A1 | All assumptions explicitly listed and scored (reasonability 0-10) | PASS / WARN / FAIL |
| A2 | No fatal assumption has reasonability < 5 | PASS / WARN / FAIL |
| A3 | If any assumption has reasonability < 5, is there a workaround? | PASS / FAIL / NA |
| A4 | Are assumptions domain-standard? (i.e., used by other papers in the field) | PASS / WARN / FAIL |

### 2. Counterfactual Resilience

| Check | Description | Verdict |
|-------|-------------|---------|
| B1 | At least 3 possible failure modes have been identified | PASS / FAIL |
| B2 | Each failure mode has been searched in the literature | PASS / WARN / FAIL |
| B3 | No failure mode is confirmed by existing literature | PASS / WARN / FAIL |
| B4 | If a key assumption is violated, the result degrades gracefully (not catastrophically) | PASS / FAIL / NA |

### 3. Analogy Validation

| Check | Description | Verdict |
|-------|-------------|---------|
| C1 | At least one analogous problem in a related domain has been identified | PASS / FAIL |
| C2 | The analogous problem's success/failure rate is known | PASS / WARN / FAIL |
| C3 | The differences between this problem and the analogous one are explicitly listed | PASS / FAIL |
| C4 | The differences do not introduce new failure modes | PASS / WARN / FAIL |

### 4. Computational Feasibility

| Check | Description | Verdict |
|-------|-------------|---------|
| D1 | The minimum compute resources required are estimated | PASS / FAIL |
| D2 | The required resources are within OSS sandbox capabilities | PASS / FAIL / NA |
| D3 | If resources are insufficient, a scoped-down version is feasible | PASS / FAIL / NA |
| D4 | The derivation is reproducible (SymPy script preserved, random seed set) | PASS / FAIL |

### 5. Claim Scope Calibration

| Check | Description | Verdict |
|-------|-------------|---------|
| E1 | Every claim is qualified by its regime of validity | PASS / WARN / FAIL |
| E2 | No claim uses "proven" without symbolic fidelity | PASS / FAIL |
| E3 | No claim uses "supported" without at least numerical fidelity | PASS / FAIL |
| E4 | Limitations are explicitly stated in the Discussion section | PASS / WARN / FAIL |
| E5 | The confidence gap (theoretical vs grounding) is disclosed | PASS / FAIL |

## Overall Verdict

| Condition | Verdict |
|-----------|---------|
| All checks PASS | GROUNDED — ready for publication |
| 1-3 WARN, no FAIL | MOSTLY GROUNDED — proceed with caveats |
| Any FAIL | UNGROUNDED — must fix before paper writing |

## Quick Reference

- **Purpose**: Ensure theoretical ideas are practically realizable
- **When**: After result-to-claim, before paper-writing
- **Core question**: "If someone tried to implement this, would it work?"
- **Output**: GROUNDED / MOSTLY GROUNDED / UNGROUNDED

## See Also

- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — produces the claims this checklist validates
- [`../adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — upstream falsification stress test
- [`../method-registry/SKILL.md`](../support/method-registry/SKILL.md) — assumption registry with quality scores