# Domain Failure Mode Catalog (SciForge-OSS — Reference)

> **Status (v2.2 — reference catalog, v2.8 — query contract via domain-signature-consumer.md)**: Reference catalog of domain-specific failure modes. This is NOT a hard-coded classification — the agent uses the domain signature (from `/domain-signature` Phase 1a OPTIONAL hint, or `/domain-learner` Phase 1b MUST source) to query this catalog and select relevant failure modes.
>
> **Core principle**: Every domain knows how it fails. Economics knows about endogeneity, physics knows about unit mismatch, medicine knows about confounding. This catalog makes that knowledge available to the agent.

## How to Use

1. `/domain-signature` extracts the domain signature from the problem
2. The agent queries this catalog using the signature's `evidence_type` and `methodology_profile`
3. The selected failure modes are added to `/adversarial-falsification` and `/leakage-audit`
4. The agent checks each failure mode against the specific problem

## Failure Mode Catalog

### causal_inference (causal inference)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **endogeneity** | Explanatory variables are correlated with the error term, causing biased estimates | Economics, econometrics, social sciences | Hausman test, DWH test | fatal |
| **omitted_variable_bias** | An important variable is omitted, and the omitted variable is correlated with the explanatory variables | Economics, sociology, education | Control for known confounders, sensitivity analysis | fatal |
| **reverse_causality** | The causal direction is reversed — Y causes X instead of X causing Y | Economics, epidemiology | Granger causality, lag analysis, instrumental variables | fatal |
| **selection_bias** | Sample selection is non-random; the treatment and control groups are not comparable | Economics, medicine, education | Heckman correction, propensity score matching | fatal |
| **measurement_error** | Variables are measured imprecisely, causing attenuation bias | Economics, psychology, medicine | Instrumental variables, multiple measures | severe |
| **simultaneity** | X and Y are determined simultaneously; the causal effect cannot be isolated | Macroeconomics, finance | Simultaneous equations, VAR | fatal |
| **attrition_bias** | Sample attrition is non-random | Medical clinical trials, education | Attrition analysis, bounds | severe |
| **publication_bias** | Only positive results are published, biasing the meta-analysis | Medicine, psychology, economics | Funnel plot, Egger's test | severe |

### experimental (experimental)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **no_placebo** | No placebo control; the placebo effect cannot be ruled out | Medicine, psychology | Check for placebo control | fatal |
| **no_blinding** | Not blinded; the experimenter/subjects know the group assignment | Medicine, psychology | Check blinding status | fatal |
| **insufficient_power** | Sample size too small to detect the effect | Medicine, biology, psychology | Power analysis, sample size calculation | severe |
| **multiple_testing** | Multiple hypothesis tests not corrected; false positives inflate | Medicine, genomics, psychology | Bonferroni, FDR, Holm correction | severe |
| **regression_to_mean** | Extreme values naturally regress upon repeated measurement | Medicine, psychology, education | Control group, multiple measurements | severe |
| **confounding_by_indication** | The treatment indication itself is correlated with the outcome | Medicine, epidemiology | Propensity score, restriction | fatal |
| **lead_time_bias** | Early diagnosis causes an apparent lengthening of survival time | Medicine, cancer research | Landmark analysis, adjust for lead time | severe |

### correlational (correlational)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **spurious_correlation** | Two unrelated variables appear correlated due to a common trend | All domains | Differencing, detrending, randomization | fatal |
| **ecological_fallacy** | Group-level conclusions cannot be generalized to individuals | Sociology, economics, epidemiology | Multi-level analysis, individual-level data | fatal |
| **simpson_paradox** | The direction of a correlation reverses after stratification | Statistics, sociology, medicine | Stratification, interaction terms | fatal |
| **survivorship_bias** | Only survivors are analyzed; the failures are ignored | Finance, military, history | Include failures, survival analysis | fatal |
| **confirmation_bias** | Only evidence supporting one's own hypothesis is sought | All domains | Pre-registration, adversarial search | severe |

### derivational (derivational)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **hidden_assumption** | The proof uses an undeclared assumption | Mathematics, theoretical CS, theoretical physics | Assumption audit, step-by-step verification | fatal |
| **circular_reasoning** | The conclusion is already implicit in the assumptions | Mathematics, philosophy | Check assumption → conclusion independence | fatal |
| **quantifier_error** | Wrong ∀/∃ order; wrong quantifier scope | Mathematics, logic | Formal verification, counterexample | fatal |
| **division_by_zero** | The derivation divides by a quantity that may be zero | Mathematics, physics, engineering | Check denominator conditions | fatal |
| **limit_order_error** | The order of limits cannot be interchanged | Mathematics, physics | Check dominated convergence, uniform convergence | fatal |
| **dimensional_error** | The two sides of an equation are dimensionally inconsistent | Physics, engineering | Dimensional analysis | fatal |
| **boundary_condition_error** | Boundary conditions are unverified or wrong | Physics, engineering, differential equations | Check boundary conditions at all limits | severe |

### simulational (simulational)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **numerical_instability** | The algorithm is unstable; errors grow exponentially | Physics, engineering, climate | Stability analysis, adaptive step size | fatal |
| **convergence_failure** | The iterative algorithm does not converge to the true solution | Optimization, ML, physics | Convergence criteria, multiple starting points | fatal |
| **discretization_error** | Systematic error caused by discretization | Physics, engineering, climate | Grid refinement study, error estimation | severe |
| **parameter_tuning_bias** | Parameter tuning overfits to the validation set | ML, engineering | Cross-validation, separate test set | fatal |
| **seed_dependence** | The random seed affects the results | ML, physics simulation | Multiple seeds, statistical aggregation | severe |

### interpretive (interpretive)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **cherry_picking** | Only evidence supporting the argument is selected; counterexamples are ignored | Humanities, social sciences, law | Systematic literature review | fatal |
| **anecdotal_evidence** | Individual cases are used in place of systematic evidence | Education, psychology, management | Case study limitations, generalizability check | severe |
| **straw_man** | The opposing view is misrepresented so it can be refuted | Philosophy, law, political science | Check if opposing view is accurately represented | severe |
| **ad_hoc_hypothesis** | Unfounded assumptions are added to rescue the theory | Philosophy of science, theory | Occam's razor, independent testability | fatal |
| **equivocation** | The same term carries different meanings in different contexts | Philosophy, law, linguistics | Define all terms, check consistency | fatal |

## How to Extend

Add new failure modes following this template:

```markdown
| **failure_name** | description | domain_tags | detection_method | severity |
```

Keep the catalog focused on **known, well-documented** failure modes. Do not add speculative failure modes.

## Boundaries

- **This catalog is never complete.** New failure modes are discovered as science progresses.
- **The agent must check if a failure mode applies.** Not all failure modes apply to all problems.
- **Failure mode severity is domain-dependent.** What's "severe" in one domain may be "fatal" in another.
- **Do not treat this as a checklist.** Treat it as a reference — the agent uses domain knowledge to decide which modes apply.

## See Also

- [`../meta-skills/domain-signature/SKILL.md`](../meta-skills/domain-signature/SKILL.md) — extracts the domain signature that queries this catalog
- [`../support/adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — uses failure modes for stress testing
- [`../support/leakage-audit/SKILL.md`](../support/leakage-audit/SKILL.md) — uses failure modes for leakage audit
