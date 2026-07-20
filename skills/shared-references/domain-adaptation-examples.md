# Domain Adaptation Examples (SciForge-OSS — Concrete Working Examples)

> **Status**: Concrete examples showing how the domain signature automatically adapts the pipeline for different domains. Each example traces the full flow from problem input to paper output.

## Example 1: Economics — Causal Inference

### Input
```
/125-problems-pipeline "Does minimum wage increase unemployment? Use DiD"
```

### Phase 1a: Domain Signature Extraction

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

### Phase 2: Idea Discovery (Adapted)

```
Domain signature consumed:
  - evidence_type=causal_inference → weights: theoretical=0.3, computational=0.5, qualitative=0.2
  - Emphasis: identification strategy, robustness checks

Generated ideas:
  1. [theoretical] DiD framework with parallel trends assumption
  2. [computational] Panel data regression with state/year FE
  3. [qualitative] Mechanism: labor market adjustment channels
```

### Phase 2.5: Adversarial Falsification (Adapted)

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

### Phase 12: Paper Writing (Adapted)

```
Domain signature consumed:
  - writing_style=empirical_economics → AER-style: theory → empirical strategy → results → robustness
  - citation_format=author_year → \citep{} / \citet{} (elsarticle-harv)
  - Section structure: 1.Introduction → 2.Theoretical Framework → 3.Empirical Strategy → 4.Results → 5.Robustness → 6.Conclusion

Output: Economics-style paper with DiD identification strategy
```

---

## Example 2: Mathematics — Formal Proof

### Input
```
/125-problems-pipeline "Prove that the Riemann zeta function has no zeros for Re(s) > 1"
```

### Phase 1a: Domain Signature Extraction

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

### Phase 2: Idea Discovery (Adapted)

```
Domain signature consumed:
  - evidence_type=derivational → weights: theoretical=0.6, computational=0.3, qualitative=0.1
  - Emphasis: proof structure, theorem chain

Generated ideas:
  1. [theoretical] Euler product representation → absolute convergence for Re(s) > 1
  2. [computational] Numerical verification for sample points
  3. [qualitative] Comparison with Dirichlet series convergence
```

### Phase 2.5: Adversarial Falsification (Adapted)

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

### Phase 12: Paper Writing (Adapted)

```
Domain signature consumed:
  - writing_style=formal_math → Theorem → Lemma → Proof → Corollary chain
  - citation_format=numeric → \cite{} (elsarticle-num)
  - Section structure: 1.Introduction → 2.Preliminaries → 3.Main Theorem → 4.Proofs → 5.Discussion

Output: Formal mathematics paper with theorem-proof structure
```

---

## Example 3: Medicine — Clinical Trial

### Input
```
/125-problems-pipeline "Does drug X reduce blood pressure? Design a clinical trial"
```

### Phase 1a: Domain Signature Extraction

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

### Phase 2: Idea Discovery (Adapted)

```
Domain signature consumed:
  - evidence_type=experimental → weights: theoretical=0.2, computational=0.3, qualitative=0.5
  - Emphasis: protocol design, statistical power

Generated ideas:
  1. [theoretical] RCT design with parallel groups
  2. [computational] Sample size calculation (power=0.8, α=0.05)
  3. [qualitative] Mechanism: drug X → ACE inhibition → vasodilation
```

### Phase 2.5: Adversarial Falsification (Adapted)

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

### Phase 12: Paper Writing (Adapted)

```
Domain signature consumed:
  - writing_style=biological_sciences → IMRaD: Introduction → Methods → Results → Discussion
  - citation_format=numeric → \cite{} (elsarticle-num)
  - Section structure: 1.Introduction → 2.Methods (with protocol) → 3.Results → 4.Discussion → 5.Conclusion

Output: Clinical trial paper with IMRaD structure
```

---

## Example 4: Physics — Numerical Simulation

### Input
```
/125-problems-pipeline "Simulate the heat equation on a 2D domain"
```

### Phase 1a: Domain Signature Extraction

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

### Phase 2: Idea Discovery (Adapted)

```
Domain signature consumed:
  - evidence_type=simulational → weights: theoretical=0.3, computational=0.5, qualitative=0.2
  - Emphasis: model equations, numerical methods

Generated ideas:
  1. [theoretical] Finite difference discretization of heat equation
  2. [computational] Crank-Nicolson scheme implementation
  3. [qualitative] Stability analysis via von Neumann method
```

### Phase 2.5: Adversarial Falsification (Adapted)

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

### Phase 12: Paper Writing (Adapted)

```
Domain signature consumed:
  - writing_style=physical_sciences → PRL-style: concise, results-first, methods at end
  - citation_format=numeric → \cite{} (elsarticle-num)
  - Section structure: 1.Introduction → 2.Model (governing equations) → 3.Numerical Method → 4.Results → 5.Conclusion

Output: Physics-style paper with model equations and numerical results
```

---

## Example 5: Humanities — Interpretive Analysis

### Input
```
/125-problems-pipeline "Analyze the concept of justice in Plato's Republic"
```

### Phase 1a: Domain Signature Extraction

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

### Phase 2: Idea Discovery (Adapted)

```
Domain signature consumed:
  - evidence_type=interpretive → weights: theoretical=0.2, computational=0.1, qualitative=0.7
  - Emphasis: argument structure, counter-evidence

Generated ideas:
  1. [theoretical] Justice as harmony of the soul (Plato's main argument)
  2. [qualitative] Thrasymachus' challenge: justice as advantage of the stronger
  3. [qualitative] Glaucon's challenge: justice as social contract
```

### Phase 2.5: Adversarial Falsification (Adapted)

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

### Phase 12: Paper Writing (Adapted)

```
Domain signature consumed:
  - writing_style=interpretive → Claim → Evidence → Counterargument → Conclusion
  - citation_format=author_year → \citep{} / \citet{} (elsarticle-harv)
  - Section structure: 1.Introduction → 2.Main Argument → 3.Counterarguments → 4.Analysis → 5.Conclusion

Output: Humanities-style paper with argument-counterargument structure
```

## Summary Table

| Domain | evidence_type | Perspective Weights | Failure Modes | Writing Style | Citation |
|--------|--------------|-------------------|---------------|---------------|----------|
| Economics | causal_inference | T:0.3, C:0.5, Q:0.2 | endogeneity, OVB, selection | AER-style | author-year |
| Mathematics | derivational | T:0.6, C:0.3, Q:0.1 | hidden_assumption, circular | Theorem-Proof | numeric |
| Medicine | experimental | T:0.2, C:0.3, Q:0.5 | no_placebo, low_power | IMRaD | numeric |
| Physics | simulational | T:0.3, C:0.5, Q:0.2 | numerical_instability | PRL-style | numeric |
| Philosophy | interpretive | T:0.2, C:0.1, Q:0.7 | cherry_picking, straw_man | Argument-Counterargument | author-year |