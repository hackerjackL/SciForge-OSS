# Domain Adaptation Guide (SciForge-OSS — Execution + Examples + Acceptance Tests)

> **Status (v2.9 — consolidated)**: Single-entry guide merging three v2.2-v2.6 documents:
> - v2.6 `domain-adaptation-execution.md` (7-step execution) → **Section A**
> - v2.4 `domain-adaptation-examples.md` (5 domain examples) → **Section B**
> - v2.5 `domain-adaptation-test.md` (6 acceptance tests) → **Section C**
>
> The three originals were deleted in v2.9; their content is preserved here in three clearly-delineated sections. The previous cross-references between the three files (each cited the other two in "See Also") are collapsed into the unified guide below.
>
> **Core principle**: Domain adaptation is a wiring layer, not a discipline branch. Every skill reads `refine-logs/domain-signature.json` at startup and adapts its behavior accordingly. This guide is the **concrete mechanism** — follow the steps exactly to ensure domain adaptation works correctly.

---

## Section A — Execution Guide (7 Steps)

> Merged from v2.6 `domain-adaptation-execution.md`. The agent MUST follow these steps in order. Skipping any step breaks domain adaptation.

### Step 0: Prerequisites

Before starting, verify:
- [ ] `refine-logs/` directory exists
- [ ] `shared-references/domain-signature-consumer.md` exists
- [ ] `shared-references/domain-failure-modes.md` exists
- [ ] `shared-references/startup-protocol.md` exists

### Step 1: Receive Problem Input

The user provides a problem. Example:
```
/125-problems-pipeline "Does minimum wage increase unemployment? Use DiD"
```

**Agent action**: Read the problem statement and identify:
- Domain keywords (e.g., "minimum wage", "DiD" → economics)
- Methodology keywords (e.g., "difference-in-differences", "treatment")
- Evidence type (e.g., "causal_inference", "derivational", "experimental")

### Step 2: Extract Domain Signature (Phase 1a)

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

### Step 3: Execute Startup Protocol (Every Skill)

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

### Step 4: Execute Phase with Adapted Behavior

**Agent action**: Execute each phase's main workflow with the adapted parameters.

#### Phase 2: idea-discovery (adapted)

```text
Generating ideas with domain-adapted weights:
- theoretical (0.3): "DiD framework with parallel trends assumption"
- computational (0.5): "Panel data regression with state/year fixed effects"
- qualitative (0.2): "Labor market adjustment channels"

Logging: "Phase 2 complete. 3 ideas generated. Domain adaptation: ACTIVE."
```

#### Phase 2.5: adversarial-falsification (adapted)

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

#### Phase 12: paper-writing (adapted)

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

### Step 5: Verify Domain Adaptation

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

### Step 6: Handle Missing Signature

If `refine-logs/domain-signature.json` does not exist:

```text
1. Log: "WARNING: No domain signature found. Using default behavior."
2. Use default perspective weights (equal: 0.33, 0.33, 0.33)
3. Use default failure modes (universal only)
4. Use default writing style (academic, numeric citations)
5. Pipeline continues without interruption
6. After pipeline completes, suggest: "Consider running /domain-signature manually for domain adaptation"
```

### Step 7: Cross-Domain Verification

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

### Error Recovery (Section A)

| Error | Cause | Recovery |
|-------|-------|----------|
| Signature not found | Phase 1a skipped | Run Phase 1a manually, or use defaults |
| Signature malformed | JSON parsing error | Fix JSON, re-run Phase 1a |
| Consumption rules not found | Missing domain-signature-consumer.md | Use defaults, log warning |
| Failure modes not found | Missing domain-failure-modes.md | Use universal failure modes only |
| Writing style not recognized | Unknown evidence_type | Use default academic style |

### Quick Reference Card (Section A)

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

---

## Section B — Five Domain Examples

> Merged from v2.4 `domain-adaptation-examples.md`. Each example traces the full flow from problem input to paper output, showing how the domain signature automatically adapts Phase 2 (idea discovery), Phase 2.5 (adversarial falsification), and Phase 12 (paper writing) for different domains.

### Example 1: Economics — Causal Inference

**Input**:
```
/125-problems-pipeline "Does minimum wage increase unemployment? Use DiD"
```

**Phase 1a — Domain Signature Extraction**:
```
Problem analysis:
  - Keywords: "minimum wage", "unemployment", "DiD" → causal_inference
  - Methodology: "difference-in-differences" → panel data, treatment/control
  - Writing style: empirical economics → AER-style

Domain signature output:
{
  "evidence_type": "causal_inference",
  "primary_domain": "economics",
  "verification_approach": "numerical_simulation",
  "writing_style": "empirical_economics",
  "citation_format": "author_year",
  "failure_modes": ["endogeneity", "omitted_variable_bias", "reverse_causality", "selection_bias"],
  "data_availability": "high"
}
```

**Phase 2 — Idea Discovery (Adapted)**:
```
Domain signature consumed:
  - evidence_type=causal_inference → weights: theoretical=0.3, computational=0.5, qualitative=0.2
  - Emphasis: identification strategy, robustness checks

Generated ideas:
  1. [theoretical] DiD framework with parallel trends assumption
  2. [computational] Panel data regression with state/year FE
  3. [qualitative] Mechanism: labor market adjustment channels
```

**Phase 2.5 — Adversarial Falsification (Adapted)**:
```
Domain signature consumed:
  - failure_modes loaded from catalog: [endogeneity, omitted_variable_bias, reverse_causality, selection_bias]
  - Data availability checked: panel data from CPS (public) → DATA_READY

Falsification report:
  - endogeneity: Checked → Instrumental variable available (neighboring state policy)
  - omitted_variable_bias: Checked → State GDP and population are controlled
  - parallel_trends: Checked → Pre-treatment trends are parallel (p=0.34)
  - Verdict: SURVIVE (all attacks resisted)
```

**Phase 12 — Paper Writing (Adapted)**:
```
Domain signature consumed:
  - writing_style=empirical_economics → AER-style: theory → empirical strategy → results → robustness
  - citation_format=author_year → \citep{} / \citet{} (elsarticle-harv)
  - Section structure: 1.Introduction → 2.Theoretical Framework → 3.Empirical Strategy → 4.Results → 5.Robustness → 6.Conclusion

Output: Economics-style paper with DiD identification strategy
```

### Example 2: Mathematics — Formal Proof

**Input**:
```
/125-problems-pipeline "Prove that the Riemann zeta function has no zeros for Re(s) > 1"
```

**Phase 1a — Domain Signature Extraction**:
```
Domain signature output:
{
  "evidence_type": "derivational",
  "primary_domain": "mathematics",
  "verification_approach": "symbolic_derivation",
  "writing_style": "formal_math",
  "citation_format": "numeric",
  "failure_modes": ["hidden_assumption", "circular_reasoning", "quantifier_error", "division_by_zero"],
  "data_availability": "not_applicable"
}
```

**Phase 2 — Idea Discovery (Adapted)**:
```
Domain signature consumed:
  - evidence_type=derivational → weights: theoretical=0.6, computational=0.3, qualitative=0.1
  - Emphasis: proof structure, theorem chain

Generated ideas:
  1. [theoretical] Euler product representation → absolute convergence for Re(s) > 1
  2. [computational] Numerical verification for sample points
  3. [qualitative] Comparison with Dirichlet series convergence
```

**Phase 2.5 — Adversarial Falsification (Adapted)**:
```
Domain signature consumed:
  - failure_modes loaded: [hidden_assumption, circular_reasoning, quantifier_error, division_by_zero]
  - Data availability: NOT_APPLICABLE (theory-only)

Falsification report:
  - hidden_assumption: Checked → All assumptions are explicit (s is complex, Re(s) > 1)
  - circular_reasoning: Checked → No circularity detected
  - quantifier_error: Checked → ∀s with Re(s) > 1, not ∃s with Re(s) > 1
  - division_by_zero: Checked → No division by zero in the derivation
  - Verdict: SURVIVE
```

**Phase 12 — Paper Writing (Adapted)**:
```
Domain signature consumed:
  - writing_style=formal_math → Theorem → Lemma → Proof → Corollary chain
  - citation_format=numeric → \cite{} (elsarticle-num)
  - Section structure: 1.Introduction → 2.Preliminaries → 3.Main Theorem → 4.Proofs → 5.Discussion

Output: Formal mathematics paper with theorem-proof structure
```

### Example 3: Medicine — Clinical Trial

**Input**:
```
/125-problems-pipeline "Does drug X reduce blood pressure? Design a clinical trial"
```

**Phase 1a — Domain Signature Extraction**:
```
Domain signature output:
{
  "evidence_type": "experimental",
  "primary_domain": "medicine",
  "verification_approach": "statistical_analysis",
  "writing_style": "biological_sciences",
  "citation_format": "numeric",
  "failure_modes": ["no_placebo", "no_blinding", "insufficient_power", "confounding_by_indication"],
  "data_availability": "partial"
}
```

**Phase 2 — Idea Discovery (Adapted)**:
```
Domain signature consumed:
  - evidence_type=experimental → weights: theoretical=0.2, computational=0.3, qualitative=0.5
  - Emphasis: protocol design, statistical power

Generated ideas:
  1. [theoretical] RCT design with parallel groups
  2. [computational] Sample size calculation (power=0.8, α=0.05)
  3. [qualitative] Mechanism: drug X → ACE inhibition → vasodilation
```

**Phase 2.5 — Adversarial Falsification (Adapted)**:
```
Domain signature consumed:
  - failure_modes loaded: [no_placebo, no_blinding, insufficient_power, confounding_by_indication]
  - Data availability: PARTIAL → trial data needs IRB approval

Falsification report:
  - no_placebo: Checked → Placebo control included
  - no_blinding: Checked → Double-blind design
  - insufficient_power: Checked → n=200 per group (power=0.85)
  - confounding_by_indication: Checked → Randomization ensures balance
  - Data availability: DATA_LIMITED → needs IRB approval
  - Verdict: SURVIVE (with DATA_LIMITED caveat)
```

**Phase 12 — Paper Writing (Adapted)**:
```
Domain signature consumed:
  - writing_style=biological_sciences → IMRaD: Introduction → Methods → Results → Discussion
  - citation_format=numeric → \cite{} (elsarticle-num)
  - Section structure: 1.Introduction → 2.Methods (with protocol) → 3.Results → 4.Discussion → 5.Conclusion

Output: Clinical trial paper with IMRaD structure
```

### Example 4: Physics — Numerical Simulation

**Input**:
```
/125-problems-pipeline "Simulate the heat equation on a 2D domain"
```

**Phase 1a — Domain Signature Extraction**:
```
Domain signature output:
{
  "evidence_type": "simulational",
  "primary_domain": "physics",
  "verification_approach": "numerical_simulation",
  "writing_style": "physical_sciences",
  "citation_format": "numeric",
  "failure_modes": ["numerical_instability", "convergence_failure", "discretization_error"],
  "data_availability": "not_applicable"
}
```

**Phase 2 — Idea Discovery (Adapted)**:
```
Domain signature consumed:
  - evidence_type=simulational → weights: theoretical=0.3, computational=0.5, qualitative=0.2
  - Emphasis: model equations, numerical methods

Generated ideas:
  1. [theoretical] Finite difference discretization of heat equation
  2. [computational] Crank-Nicolson scheme implementation
  3. [qualitative] Stability analysis via von Neumann method
```

**Phase 2.5 — Adversarial Falsification (Adapted)**:
```
Domain signature consumed:
  - failure_modes loaded: [numerical_instability, convergence_failure, discretization_error]
  - Data availability: NOT_APPLICABLE (simulation generates its own data)

Falsification report:
  - numerical_instability: Checked → Crank-Nicolson is unconditionally stable
  - convergence_failure: Checked → Grid refinement study shows O(h²) convergence
  - discretization_error: Checked → Error < 1% at h=0.01
  - Verdict: SURVIVE
```

**Phase 12 — Paper Writing (Adapted)**:
```
Domain signature consumed:
  - writing_style=physical_sciences → PRL-style: concise, results-first, methods at end
  - citation_format=numeric → \cite{} (elsarticle-num)
  - Section structure: 1.Introduction → 2.Model (governing equations) → 3.Numerical Method → 4.Results → 5.Conclusion

Output: Physics-style paper with model equations and numerical results
```

### Example 5: Humanities — Interpretive Analysis

**Input**:
```
/125-problems-pipeline "Analyze the concept of justice in Plato's Republic"
```

**Phase 1a — Domain Signature Extraction**:
```
Domain signature output:
{
  "evidence_type": "interpretive",
  "primary_domain": "philosophy",
  "verification_approach": "textual_analysis",
  "writing_style": "interpretive",
  "citation_format": "author_year",
  "failure_modes": ["cherry_picking", "anecdotal_evidence", "straw_man", "equivocation"],
  "data_availability": "high"
}
```

**Phase 2 — Idea Discovery (Adapted)**:
```
Domain signature consumed:
  - evidence_type=interpretive → weights: theoretical=0.2, computational=0.1, qualitative=0.7
  - Emphasis: argument structure, counter-evidence

Generated ideas:
  1. [theoretical] Justice as harmony of the soul (Plato's main argument)
  2. [qualitative] Thrasymachus' challenge: justice as advantage of the stronger
  3. [qualitative] Glaucon's challenge: justice as social contract
```

**Phase 2.5 — Adversarial Falsification (Adapted)**:
```
Domain signature consumed:
  - failure_modes loaded: [cherry_picking, anecdotal_evidence, straw_man, equivocation]
  - Data availability: HIGH (text is publicly available)

Falsification report:
  - cherry_picking: Checked → All three challenges to justice are addressed
  - straw_man: Checked → Thrasymachus' position is accurately represented
  - equivocation: Checked → "Justice" is consistently defined
  - Verdict: SURVIVE
```

**Phase 12 — Paper Writing (Adapted)**:
```
Domain signature consumed:
  - writing_style=interpretive → Claim → Evidence → Counterargument → Conclusion
  - citation_format=author_year → \citep{} / \citet{} (elsarticle-harv)
  - Section structure: 1.Introduction → 2.Main Argument → 3.Counterarguments → 4.Analysis → 5.Conclusion

Output: Humanities-style paper with argument-counterargument structure
```

### Summary Table (Section B)

| Domain | evidence_type | Perspective Weights | Failure Modes | Writing Style | Citation |
|--------|--------------|-------------------|---------------|---------------|----------|
| Economics | causal_inference | T:0.3, C:0.5, Q:0.2 | endogeneity, OVB, selection | AER-style | author-year |
| Mathematics | derivational | T:0.6, C:0.3, Q:0.1 | hidden_assumption, circular | Theorem-Proof | numeric |
| Medicine | experimental | T:0.2, C:0.3, Q:0.5 | no_placebo, low_power | IMRaD | numeric |
| Physics | simulational | T:0.3, C:0.5, Q:0.2 | numerical_instability | PRL-style | numeric |
| Philosophy | interpretive | T:0.2, C:0.1, Q:0.7 | cherry_picking, straw_man | Argument-Counterargument | author-year |

---

## Section C — Acceptance Tests (6 Cases)

> Merged from v2.5 `domain-adaptation-test.md`. The agent MUST run these tests after any domain adaptation changes to confirm the mechanism is functional. If the test fails, domain adaptation is broken.

### Test 1: Economics Domain Adaptation

**Input**:
```
/125-problems-pipeline "Does minimum wage increase unemployment? Use DiD"
```

**Expected Phase 1a Output**:
```json
{
  "evidence_type": "causal_inference",
  "primary_domain": "economics",
  "writing_style": "empirical_economics",
  "citation_format": "author_year",
  "failure_modes": ["endogeneity", "omitted_variable_bias", "reverse_causality", "selection_bias"]
}
```

**Verification Steps**:
```
[ ] Phase 1a produces domain-signature.json with evidence_type=causal_inference
[ ] Phase 2 uses perspective weights: theoretical=0.3, computational=0.5, qualitative=0.2
[ ] Phase 2.5 loads failure modes: [endogeneity, omitted_variable_bias, reverse_causality, selection_bias]
[ ] Phase 12 uses AER-style section structure
[ ] Phase 12 uses author-year citation format (elsarticle-harv)
[ ] Paper output mentions "identification strategy" and "robustness checks"
```

**Pass Condition**: All 6 checks pass → ECONOMICS_ADAPTATION: PASS

### Test 2: Mathematics Domain Adaptation

**Input**:
```
/125-problems-pipeline "Prove that the Riemann zeta function converges for Re(s) > 1"
```

**Expected Phase 1a Output**:
```json
{
  "evidence_type": "derivational",
  "primary_domain": "mathematics",
  "writing_style": "formal_math",
  "citation_format": "numeric",
  "failure_modes": ["hidden_assumption", "circular_reasoning", "quantifier_error", "division_by_zero"]
}
```

**Verification Steps**:
```
[ ] Phase 1a produces domain-signature.json with evidence_type=derivational
[ ] Phase 2 uses perspective weights: theoretical=0.6, computational=0.3, qualitative=0.1
[ ] Phase 2.5 loads failure modes: [hidden_assumption, circular_reasoning, quantifier_error, division_by_zero]
[ ] Phase 12 uses Theorem-Lemma-Proof section structure
[ ] Phase 12 uses numeric citation format (elsarticle-num)
[ ] Paper output uses theorem environments
```

**Pass Condition**: All 6 checks pass → MATHEMATICS_ADAPTATION: PASS

### Test 3: Medicine Domain Adaptation

**Input**:
```
/125-problems-pipeline "Design a clinical trial for drug X efficacy"
```

**Expected Phase 1a Output**:
```json
{
  "evidence_type": "experimental",
  "primary_domain": "medicine",
  "writing_style": "biological_sciences",
  "citation_format": "numeric",
  "failure_modes": ["no_placebo", "no_blinding", "insufficient_power", "confounding_by_indication"]
}
```

**Verification Steps**:
```
[ ] Phase 1a produces domain-signature.json with evidence_type=experimental
[ ] Phase 2 uses perspective weights: theoretical=0.2, computational=0.3, qualitative=0.5
[ ] Phase 2.5 loads failure modes: [no_placebo, no_blinding, insufficient_power, confounding_by_indication]
[ ] Phase 12 uses IMRaD section structure
[ ] Phase 12 uses numeric citation format (elsarticle-num)
[ ] Paper output mentions "power analysis" and "blinding"
```

**Pass Condition**: All 6 checks pass → MEDICINE_ADAPTATION: PASS

### Test 4: Fantasy Prevention

**Input (should be FANTASY)**:
```
/125-problems-pipeline "Prove P = NP using a simple algorithm"
```

**Expected Behavior**:
```
[ ] Phase 2.5: Adversarial falsification detects fantasy
[ ] Gate 1: Derivation traceability → FAIL (no derivation chain)
[ ] Gate 4: Falsifiability → FAIL (claim is not falsifiable)
[ ] Fantasy verdict: FANTASY or MOSTLY_FANTASY
[ ] Phase 12: Paper writing is BLOCKED (fantasy prevention)
[ ] Fantasy log entry is written to refine-logs/fantasy-log.md
```

**Pass Condition**: All 6 checks pass → FANTASY_PREVENTION: PASS

### Test 5: Pipeline Integrity

**Input**:
```
/125-problems-pipeline "Q001: 宇宙的起源与演化"
```

**Expected Behavior**:
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

**Pass Condition**: All 18 checks pass → PIPELINE_INTEGRITY: PASS

### Test 6: Ouroboros Integration

**Input**:
```
/125-problems-pipeline "Q001: 宇宙的起源与演化" — ouroboros
```

**Expected Behavior**:
```
[ ] Phase 2.5: Data requirements spec generated
[ ] Phase 2.5: data-requirements.json written to refine-logs/
[ ] Ouroboros: data-availability-report.json received
[ ] Phase 10: Joint confidence computed (theoretical × data)
[ ] Phase 12: Paper includes data limitations section
[ ] Joint confidence > 0.5 (moderate or strong)
```

**Pass Condition**: All 6 checks pass → OUROBOROS_INTEGRATION: PASS

### Summary Report (Section C)

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

### When to Run (Section C)

Run this acceptance test:
1. After any domain adaptation changes
2. Before releasing a new version
3. When adding new domain support
4. When fixing fantasy prevention bugs

---

## See Also

- [`domain-signature-consumer.md`](domain-signature-consumer.md) — consumption rules (wiring layer)
- [`startup-protocol.md`](startup-protocol.md) — mandatory startup steps
- [`pipeline-integrity.md`](pipeline-integrity.md) — pipeline integrity checks
- [`fantasy-prevention.md`](fantasy-prevention.md) — fantasy prevention protocol
- [`domain-failure-modes.md`](domain-failure-modes.md) — reference catalog of domain failure modes
- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL 4-dim joint confidence schema (v2.8)
- [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) — M1 Phase 5/6/11 intensity adaptation (v2.8)
- [`pipeline-adaptive-degradation.md`](pipeline-adaptive-degradation.md) — M3 phase mode adaptation (v2.8)
