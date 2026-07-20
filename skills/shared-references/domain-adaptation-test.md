# Domain Adaptation Acceptance Test (SciForge-OSS)

> **Status**: Concrete acceptance test that verifies domain adaptation is working correctly. The agent MUST run this test after any domain adaptation changes to confirm the mechanism is functional.
>
> **Core principle**: If the test fails, domain adaptation is broken. The test is the single source of truth for "does domain adaptation work?"

## Test 1: Economics Domain Adaptation

### Input
```
/125-problems-pipeline "Does minimum wage increase unemployment? Use DiD"
```

### Expected Phase 1a Output
```json
{
  "evidence_type": "causal_inference",
  "primary_domain": "economics",
  "writing_style": "empirical_economics",
  "citation_format": "author_year",
  "failure_modes": ["endogeneity", "omitted_variable_bias", "reverse_causality", "selection_bias"]
}
```

### Verification Steps
```
[ ] Phase 1a produces domain-signature.json with evidence_type=causal_inference
[ ] Phase 2 uses perspective weights: theoretical=0.3, computational=0.5, qualitative=0.2
[ ] Phase 2.5 loads failure modes: [endogeneity, omitted_variable_bias, reverse_causality, selection_bias]
[ ] Phase 12 uses AER-style section structure
[ ] Phase 12 uses author-year citation format (elsarticle-harv)
[ ] Paper output mentions "identification strategy" and "robustness checks"
```

### Pass Condition
All 6 checks pass → ECONOMICS_ADAPTATION: PASS

---

## Test 2: Mathematics Domain Adaptation

### Input
```
/125-problems-pipeline "Prove that the Riemann zeta function converges for Re(s) > 1"
```

### Expected Phase 1a Output
```json
{
  "evidence_type": "derivational",
  "primary_domain": "mathematics",
  "writing_style": "formal_math",
  "citation_format": "numeric",
  "failure_modes": ["hidden_assumption", "circular_reasoning", "quantifier_error", "division_by_zero"]
}
```

### Verification Steps
```
[ ] Phase 1a produces domain-signature.json with evidence_type=derivational
[ ] Phase 2 uses perspective weights: theoretical=0.6, computational=0.3, qualitative=0.1
[ ] Phase 2.5 loads failure modes: [hidden_assumption, circular_reasoning, quantifier_error, division_by_zero]
[ ] Phase 12 uses Theorem-Lemma-Proof section structure
[ ] Phase 12 uses numeric citation format (elsarticle-num)
[ ] Paper output uses theorem environments
```

### Pass Condition
All 6 checks pass → MATHEMATICS_ADAPTATION: PASS

---

## Test 3: Medicine Domain Adaptation

### Input
```
/125-problems-pipeline "Design a clinical trial for drug X efficacy"
```

### Expected Phase 1a Output
```json
{
  "evidence_type": "experimental",
  "primary_domain": "medicine",
  "writing_style": "biological_sciences",
  "citation_format": "numeric",
  "failure_modes": ["no_placebo", "no_blinding", "insufficient_power", "confounding_by_indication"]
}
```

### Verification Steps
```
[ ] Phase 1a produces domain-signature.json with evidence_type=experimental
[ ] Phase 2 uses perspective weights: theoretical=0.2, computational=0.3, qualitative=0.5
[ ] Phase 2.5 loads failure modes: [no_placebo, no_blinding, insufficient_power, confounding_by_indication]
[ ] Phase 12 uses IMRaD section structure
[ ] Phase 12 uses numeric citation format (elsarticle-num)
[ ] Paper output mentions "power analysis" and "blinding"
```

### Pass Condition
All 6 checks pass → MEDICINE_ADAPTATION: PASS

---

## Test 4: Fantasy Prevention

### Input (should be FANTASY)
```
/125-problems-pipeline "Prove P = NP using a simple algorithm"
```

### Expected Behavior
```
[ ] Phase 2.5: Adversarial falsification detects fantasy
[ ] Gate 1: Derivation traceability → FAIL (no derivation chain)
[ ] Gate 4: Falsifiability → FAIL (claim is not falsifiable)
[ ] Fantasy verdict: FANTASY or MOSTLY_FANTASY
[ ] Phase 12: Paper writing is BLOCKED (fantasy prevention)
[ ] Fantasy log entry is written to refine-logs/fantasy-log.md
```

### Pass Condition
All 6 checks pass → FANTASY_PREVENTION: PASS

---

## Test 5: Pipeline Integrity

### Input
```
/125-problems-pipeline "Q001: 宇宙的起源与演化"
```

### Expected Behavior
```
[ ] Phase 0: Q-id loaded successfully
[ ] Phase 1: Problem understood and decomposed
[ ] Phase 1a: Domain signature extracted (astrophysics)
[ ] Phase 2: Ideas generated (≥ 1)
[ ] Phase 2.5: Falsification passed (≥ 1 idea survives)
[ ] Phase 3: Novelty check passed
[ ] Phase 4: Literature retrieved
[ ] Phase 5: Method registry built
[ ] Phase 6: Theory derivation completed
[ ] Phase 7: Leakage audit passed
[ ] Phase 8: Logic verification passed
[ ] Phase 9: Invariant check passed
[ ] Phase 10: Claims produced
[ ] Phase 11: (OPTIONAL) Figures generated if needed
[ ] Phase 12: Paper written
[ ] Phase 13: Paper compiled (WARN allowed)
[ ] Phase 14: (OPTIONAL) Review loop completed
[ ] Phase 15: Citation audit passed
[ ] Phase 16: Final assembly completed
[ ] No phase BLOCKED (all MUST phases passed)
```

### Pass Condition
All 18 checks pass → PIPELINE_INTEGRITY: PASS

---

## Test 6: Ouroboros Integration

### Input
```
/125-problems-pipeline "Q001: 宇宙的起源与演化" — ouroboros
```

### Expected Behavior
```
[ ] Phase 2.5: Data requirements spec generated
[ ] Phase 2.5: data-requirements.json written to refine-logs/
[ ] Ouroboros: data-availability-report.json received
[ ] Phase 10: Joint confidence computed (theoretical × data)
[ ] Phase 12: Paper includes data limitations section
[ ] Joint confidence > 0.5 (moderate or strong)
```

### Pass Condition
All 6 checks pass → OUROBOROS_INTEGRATION: PASS

---

## Summary Report

After running all tests, produce a summary:

```markdown
# Domain Adaptation Acceptance Test Report

## Results
| Test | Status |
|------|--------|
| 1. Economics Adaptation | PASS / FAIL |
| 2. Mathematics Adaptation | PASS / FAIL |
| 3. Medicine Adaptation | PASS / FAIL |
| 4. Fantasy Prevention | PASS / FAIL |
| 5. Pipeline Integrity | PASS / FAIL |
| 6. Ouroboros Integration | PASS / FAIL |

## Overall
- **Passed**: X/6
- **Failed**: Y/6
- **Verdict**: ACCEPTED (all pass) / REJECTED (any fail)

## Failed Tests Detail
- [Test N]: [failure reason]
- [Test N]: [failure reason]
```

## When to Run

Run this acceptance test:
1. After any domain adaptation changes
2. Before releasing a new version
3. When adding new domain support
4. When fixing fantasy prevention bugs

## See Also

- [`domain-adaptation-examples.md`](domain-adaptation-examples.md) — concrete examples
- [`startup-protocol.md`](startup-protocol.md) — mandatory startup protocol
- [`pipeline-integrity.md`](pipeline-integrity.md) — pipeline integrity checks
- [`fantasy-prevention.md`](fantasy-prevention.md) — fantasy prevention protocol