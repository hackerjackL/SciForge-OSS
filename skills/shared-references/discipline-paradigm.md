# Discipline Paradigm Configuration (SciForge-OSS — Universal Domain Coverage)

> **Status**: Defines 4 universal research paradigms that cover ALL scientific domains — from formal sciences to humanities. OSS selects the paradigm based on the problem's nature, NOT by hard-coded discipline mapping.
>
> Each paradigm has its own truth standard, verification method, and output format. The agent's runtime reasoning applies the appropriate paradigm.

## The 4 Paradigms

| Paradigm | Truth Standard | Verification Method | Output Format | Example Domains |
|----------|---------------|---------------------|---------------|-----------------|
| **formal** | Proof | Theorem proving, model checking, logical derivation | Theorem-Proof structure | Mathematics, logic, theoretical CS |
| **empirical** | Reproducible experiment | Statistical test, controlled experiment, numerical validation | Hypothesis-Method-Results-Discussion | Physics, chemistry, biology, medicine |
| **interpretive** | Explanatory power, coherence | Text analysis, argument reconstruction, hermeneutic analysis | Claim-Evidence-Counterargument-Conclusion | Humanities, social sciences, law, education |
| **design** | Functional implementation | Prototype validation, benchmark evaluation, ablation study | Design-Implementation-Evaluation-Discussion | Engineering, CS, materials, sensors |

## Paradigm Selection

The paradigm is auto-detected in Phase 1 (problem understanding) based on:

1. **Problem type**: Is the expected answer a proof, a measurement, an interpretation, or a design?
2. **Verification method**: Can the result be verified by derivation, experiment, analysis, or prototype?
3. **Output format**: What structure does the expected paper follow?

### Explicit override

The user can override paradigm selection:

```
/125-problems-pipeline "Q042: 教育公平性研究" — paradigm: interpretive
/125-problems-pipeline "Prove the Riemann Hypothesis" — paradigm: formal
```

## Paradigm-Specific Configurations

### Formal Paradigm

| Setting | Value |
|---------|-------|
| Truth standard | Proof (derivation chain with no gaps) |
| Fidelity gate | symbolic ≥ numerical (proof required) |
| Theory derivation | SymPy symbolic verification |
| Figures | commutative-diagram, derivation-tree |
| Paper structure | Main Results → Proofs (no experiments) |
| Fallback | If no proof found, emit conjecture + evidence |

### Empirical Paradigm

| Setting | Value |
|---------|-------|
| Truth standard | Reproducible experiment (statistical significance) |
| Fidelity gate | numerical ≥ qualitative (data required) |
| Theory derivation | SymPy + numerical sanity check |
| Figures | line, scatter, bar, heatmap, box |
| Paper structure | Problem → Method → Results → Discussion |
| Fallback | If no data, reframe as theoretical prediction |

### Interpretive Paradigm

| Setting | Value |
|---------|-------|
| Truth standard | Explanatory power (coherence, consistency, coverage) |
| Fidelity gate | qualitative (analysis quality, argument strength) |
| Theory derivation | Argument reconstruction, textual analysis |
| Figures | concept-map, dependency-graph |
| Paper structure | Claim → Evidence → Counterargument → Conclusion |
| Fallback | If no evidence, reframe as hypothesis |

### Design Paradigm

| Setting | Value |
|---------|-------|
| Truth standard | Functional implementation (prototype works) |
| Fidelity gate | numerical (benchmark results) |
| Theory derivation | Design reasoning + complexity analysis |
| Figures | architecture, flow-chart, ablation, comparison |
| Paper structure | Design → Implementation → Evaluation → Discussion |
| Fallback | If no prototype, reframe as design proposal |

## Boundaries

- **Never hard-code discipline-to-paradigm mapping.** The paradigm is selected by problem nature, not by domain label.
- **Paradigm affects verification method, not idea quality.** All paradigms are equally valid.
- **The agent can switch paradigms** if the problem's nature becomes clearer during research.
- **No paradigm is "better"** — they are different standards of evidence for different types of inquiry.

## See Also

- [`../discipline-context.md`](discipline-context.md) — OSS single-row discipline contract
- [`../discipline-writing.md`](discipline-writing.md) — section-by-section writing guide per paradigm
- [`../venue-profiles.md`](venue-profiles.md) — universal elsarticle template