# Domain Adaptation Execution Guide (SciForge-OSS)

> **Status**: Step-by-step execution guide for AI agents. Follow these steps exactly to ensure domain adaptation works correctly. This is the **concrete mechanism** that bridges protocol design and actual execution.
>
> **Core principle**: The agent MUST follow these steps in order. Skipping any step breaks domain adaptation.

## Step 0: Prerequisites

Before starting, verify:
- [ ] `refine-logs/` directory exists
- [ ] `shared-references/domain-signature-consumer.md` exists
- [ ] `shared-references/domain-failure-modes.md` exists
- [ ] `shared-references/startup-protocol.md` exists

## Step 1: Receive Problem Input

The user provides a problem. Example:
```
/125-problems-pipeline "Does minimum wage increase unemployment? Use DiD"
```

**Agent action**: Read the problem statement and identify:
- Domain keywords (e.g., "minimum wage", "DiD" → economics)
- Methodology keywords (e.g., "difference-in-differences", "treatment")
- Evidence type (e.g., "causal_inference", "derivational", "experimental")

## Step 2: Extract Domain Signature (Phase 1a)

**Agent action**: Execute the domain signature extraction protocol:

```
1. Read the problem statement
2. Extract domain keywords → map to evidence_type
3. Extract methodology keywords → map to methodology_profile
4. Extract writing style signals → map to writing_profile
5. Write refine-logs/domain-signature.json
```

**Concrete prompt for agent**:
```text
I am executing Phase 1a: Domain Signature Extraction.

Problem: "Does minimum wage increase unemployment? Use DiD"

Analysis:
- Domain keywords: minimum wage, unemployment, DiD → economics
- Methodology keywords: difference-in-differences, treatment, control → causal_inference
- Evidence type: causal_inference (causal claim with identification strategy)
- Writing style: empirical economics → AER-style, author-year citations
- Failure modes: endogeneity, omitted variable bias, selection bias

Writing domain-signature.json to refine-logs/...
```

## Step 3: Execute Startup Protocol (Every Skill)

**Agent action**: Before executing ANY skill, follow the Mandatory Startup Protocol:

```
For each skill (idea-discovery, adversarial-falsification, paper-writing, etc.):
  1. Check if refine-logs/domain-signature.json exists
  2. If YES: Read it → Apply consumption rules → Log adaptation
  3. If NO: Log warning → Use defaults
```

**Concrete example for idea-discovery**:
```text
I am executing Mandatory Startup Protocol for /idea-discovery.

1. Check refine-logs/domain-signature.json → EXISTS
2. Read signature → evidence_type = "causal_inference"
3. Look up consumption rules in domain-signature-consumer.md
4. Found: causal_inference → perspective_weights = {theoretical: 0.3, computational: 0.5, qualitative: 0.2}
5. Apply weights: generating ideas with emphasis on identification strategy
6. Log: "Domain adaptation applied: idea-discovery → evidence_type=causal_inference → weights adjusted"
```

## Step 4: Execute Phase with Adapted Behavior

**Agent action**: Execute each phase's main workflow with the adapted parameters.

### Phase 2: idea-discovery (adapted)

```text
Generating ideas with domain-adapted weights:
- theoretical (0.3): "DiD framework with parallel trends assumption"
- computational (0.5): "Panel data regression with state/year fixed effects"
- qualitative (0.2): "Labor market adjustment channels"

Logging: "Phase 2 complete. 3 ideas generated. Domain adaptation: ACTIVE."
```

### Phase 2.5: adversarial-falsification (adapted)

```text
Loading domain-specific failure modes from domain-failure-modes.md:
- evidence_type = "causal_inference"
- Loading: [endogeneity, omitted_variable_bias, reverse_causality, selection_bias]

Checking each idea against domain failure modes:
- Idea 1: endogeneity check → PASS (IV available)
- Idea 1: omitted_variable_bias → PASS (controls included)
- Idea 1: selection_bias → PASS (panel data, no attrition)

Data availability check (Phase 6):
- Required: CPS panel data, MW policy data
- Publicly available: YES (CPS, DOL)
- Data availability score: 85% → DATA_READY

Verdict: SURVIVE (all domain-specific attacks resisted)
```

### Phase 12: paper-writing (adapted)

```text
Domain signature consumed:
- writing_style = "empirical_economics" → AER-style section structure
- citation_format = "author_year" → \citep{} / \citet{} (elsarticle-harv)

Writing paper with structure:
1. Introduction
2. Theoretical Framework
3. Empirical Strategy (with DiD identification)
4. Results
5. Robustness Checks
6. Conclusion

Logging: "Domain adaptation applied: paper-writing → style=AER, citation=author_year"
```

## Step 5: Verify Domain Adaptation

**Agent action**: After each phase, verify that domain adaptation was applied:

```text
Check: Was the domain signature consumed?
  - refine-logs/startup-log.md must contain "Domain adaptation applied" entries
  - Each entry must specify which skill, which field, and which value

Check: Did the output reflect domain adaptation?
  - Economics paper should have "identification strategy" section
  - Economics paper should use author-year citations
  - Economics paper should discuss endogeneity

If any check fails: Log WARNING and apply manual override
```

## Step 6: Handle Missing Signature

If `refine-logs/domain-signature.json` does not exist:

```text
1. Log: "WARNING: No domain signature found. Using default behavior."
2. Use default perspective weights (equal: 0.33, 0.33, 0.33)
3. Use default failure modes (universal only)
4. Use default writing style (academic, numeric citations)
5. Pipeline continues without interruption
6. After pipeline completes, suggest: "Consider running /domain-signature manually for domain adaptation"
```

## Step 7: Cross-Domain Verification

**Agent action**: Verify that the same pipeline works for different domains:

```text
Test 1: Economics
  Input: "Does minimum wage increase unemployment? Use DiD"
  Expected: causal_inference signature, AER-style paper
  Verify: [ ] signature.correct [ ] style.correct [ ] citations.correct

Test 2: Mathematics
  Input: "Prove the Riemann zeta function converges for Re(s) > 1"
  Expected: derivational signature, theorem-proof paper
  Verify: [ ] signature.correct [ ] style.correct [ ] citations.correct

Test 3: Medicine
  Input: "Design a clinical trial for drug X efficacy"
  Expected: experimental signature, IMRaD paper
  Verify: [ ] signature.correct [ ] style.correct [ ] citations.correct
```

## Error Recovery

| Error | Cause | Recovery |
|-------|-------|----------|
| Signature not found | Phase 1a skipped | Run Phase 1a manually, or use defaults |
| Signature malformed | JSON parsing error | Fix JSON, re-run Phase 1a |
| Consumption rules not found | Missing domain-signature-consumer.md | Use defaults, log warning |
| Failure modes not found | Missing domain-failure-modes.md | Use universal failure modes only |
| Writing style not recognized | Unknown evidence_type | Use default academic style |

## Quick Reference Card

```text
DOMAIN ADAPTATION EXECUTION
============================
1. RECEIVE problem → extract domain signals
2. EXTRACT signature → write to refine-logs/domain-signature.json
3. STARTUP each skill → read signature → apply rules → log
4. EXECUTE phase → with adapted behavior
5. VERIFY adaptation → check logs and output
6. HANDLE missing → use defaults, continue
7. CROSS-VERIFY → test with different domains
```

## See Also

- [`domain-signature-consumer.md`](domain-signature-consumer.md) — consumption rules
- [`startup-protocol.md`](startup-protocol.md) — mandatory startup steps
- [`domain-adaptation-test.md`](domain-adaptation-test.md) — acceptance tests
- [`domain-adaptation-examples.md`](domain-adaptation-examples.md) — concrete examples