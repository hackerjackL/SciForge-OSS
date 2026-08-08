---
name: result-to-claim
version: 1.2.1
description: "3-fidelity claim gate (symbolic/numerical/qualitative) mapping results to claims, blocking unsupported 'supported'/'proven' language. Phase 10. Invoke to gate which claims the paper may make."
type: reference-skill
role: result-to-claim-gate
---

# Result-to-Claim Gate (SciForge-OSS — Discipline-Agnostic, 3-Fidelity)

## Quick Reference

- **Purpose**: 3-fidelity claim gate (symbolic/numerical/qualitative) + confidence assessment
- **Input**: derivations/{problem_id}/ + audit_report/LOGIC_VERIFICATION.json
- **Output**: CLAIMS_FROM_RESULTS.md (with confidence assessment)
- **Key**: theoretical confidence vs grounding confidence emitted separately; primary outcomes require ≥ numerical fidelity

> **Status**: Gate that decides what claims the derivation/verification results support. **OSS is discipline-agnostic** — there is no economics p-value significance gate, no cs-ml SOTA gate. The gate uses a universal **3-fidelity claim ladder** (symbolic / numerical / qualitative) adapted from main SciForge's 5-fidelity filter. Copied from main SciForge and trimmed to OSS's no-experiment, no-benchmark design.

## Use When

Use this skill when derivation/verification completes and you need to judge what claims the results support, what they don't, and what evidence is still missing.

Typical prompts:
- "What do these results actually show"
- "Can I claim X from these numbers"
- "What claims do the results support"
- "Result-to-claim gate"
- "Are my claims supported by the derivation"
- "Before paper writing: check claim support"

## Job

Derivations and numerical sanity checks produce results; this gate decides what those results *mean*. Collect evidence from available sources, get an external reviewer judgment against intended claims, then auto-route based on the verdict (pivot, supplement, or confirm). The non-negotiable goal: **never inflate a claim beyond what the evidence supports — the external reviewer is the judge, the host agent only collects evidence and routes.**

## When to Use

- **MANDATORY**: After `/theory-derivation` + `/logic-verification` + `/dynamic-sandbox` complete (the OSS "results" phase).
- **MANDATORY**: Before committing to claims in a paper or review response.
- **MANDATORY**: Before invoking `/paper-writing`. If not invoked, `/paper-writing` will refuse to proceed.
- When results are ambiguous and you need an objective second opinion.

## Mandatory Invocation Check

Before allowing `/paper-writing` to proceed, verify:
1. `results/` directory exists with derivation/verification output files (symbolic proofs, numerical sanity checks).
2. `result-to-claim` has been invoked (check for `CLAIMS_FROM_RESULTS.md`).
3. If not invoked: **BLOCK paper writing** and require `/result-to-claim` first.
4. If invoked but verdict is `no` or `partial`: **BLOCK paper writing** until claim is revised.
5. **Problem anchor integrity**: `refine-logs/FINAL_PROPOSAL.md` exists with the frozen Q-id (verified at Step 0). This is the same check performed by `/invariant-check` INV-G1 at the phase boundary.

This check is mandatory and cannot be skipped for any OSS output.

## Required Workspace

- `derivations/{problem_id}/` — derivation/verification output files (SymPy proof logs, numerical sanity check results)
- `refine-logs/FINAL_PROPOSAL.md` — intended claims and derivation design (primary source for pre-specified claims)
- `docs/research_contract.md` — optional project-level research contract (read if present; not produced by any skill)
- `findings.md` — append postmortem / confirmed claims here
- `audit_report/LOGIC_VERIFICATION.md` — analysis report from `/logic-verification` (read if present)
- `CLAIMS_FROM_RESULTS.md` — output: the structured verdict

## Configuration

- **External reviewer model** — the cross-model reviewer used for objective claim evaluation. Should be a different model family from the host agent.
- **Fidelity threshold** — the minimum fidelity level required to support a **primary** claim. Default: `numerical` (a primary claim must have at least numerical sanity-check support; symbolic-only is "partial", qualitative-only is "no"). Configurable to `symbolic` (stricter — requires full proof) or `qualitative` (lenient — qualitative reasoning suffices).
- **Outcome classification** — outcomes are classified as **primary** (pre-specified in `refine-logs/FINAL_PROPOSAL.md`, directly testable predictions of the theoretical model) or **secondary** (mechanism tests, robustness checks, additional analyses). The fidelity gate operates on primary outcomes only.

## The 3-Fidelity Claim Ladder (OSS Universal)

OSS adapts main SciForge's 5-fidelity filter (text / symbolic / minimal / empirical / full) to a **3-fidelity ladder** suited to no-experiment, no-benchmark problems:

| Fidelity | What it means | Claim strength it supports | Label |
|----------|---------------|----------------------------|-------|
| **Symbolic** | Full SymPy derivation chain from assumptions to outcome, every step machine-verified | STRONG | "proven" / "established" |
| **Numerical** | Numerical sanity check in `/dynamic-sandbox` (parameter sweeps, counterexample search, regime verification) confirms the symbolic result behaves as predicted | MODERATE | "supported" / "confirmed numerically" |
| **Qualitative** | Only qualitative reasoning (the outcome "looks right", matches intuition, consistent with known results) — no symbolic proof, no numerical check | WEAK | "suggests" / "consistent with" |

**Claim strength rule**:
- A **primary** claim requires at least `numerical` fidelity (default; configurable). Symbolic-only → `partial`. Qualitative-only → `no`.
- A **secondary** claim (mechanism/robustness) can be supported by `qualitative` fidelity — secondary claims do not gate the pipeline.
- **Never** label a claim "proven" without `symbolic` fidelity. **Never** label a claim "supported" without at least `numerical` fidelity.

### Evidence Sufficiency Gate (v5.1 — from CRUX shadow-evaluation failure mode #1)

**Background** (arXiv:2607.27191): an AI agent got negative results on small-scale synthetic data, then packaged a severely underpowered experiment as a "discovery" — its own self-review scored it a weak reject, yet it proceeded as usual. "It knew its writing was bad, but not how to make it better." Our fidelity ladder governs evidence *type*; this section adds evidence **weight** — the common death of an experiment-based paper is not the absence of numbers, but numbers that weigh nothing.

**Mandatory checks** (under `experiment-first` / `hybrid` routing; run per PRIMARY claim; results written to the `evidence_sufficiency` field in `CLAIMS_FROM_RESULTS.md`):

| Check | Floor | Fail verdict |
|-------|-------|--------------|
| **Statistical power** | The experiment scale can detect the effect: report sample size / training scale + the minimum detectable effect at that scale (or a power analysis) | `underpowered` |
| **Effect size** | The main result reports the effect size itself (difference / improvement magnitude), not just a p-value; the effect must be comparable to the noise level (>1× between-seed std, or an explicit confidence interval) | `effect_within_noise` |
| **Replication** | Mean±std over ≥3 seeds (lite tier ≥2); single-point results must not support a PRIMARY claim | `single_seed` |
| **Data-scale match** | Toy/synthetic-data results can **only** support "in the tested regime"-level statements; primary claims must be supported by full experiments | `toy_overreach` |
| **Baseline comparison** | Primary claims require a same-conditions comparison against ≥1 baseline (the baseline group of the mandatory experiment matrix) | `no_baseline` |

**Handling** (any check fails):
1. The claim's fidelity is **force-downgraded** to at most `qualitative` → it must not enter the paper body as a PRIMARY claim
2. If the claim is the core hypothesis (the main thesis of FINAL_PROPOSAL) → trigger `/experiment-execution`'s **KILL-or-PIVOT** (insufficient evidence = core hypothesis unsupported, same as the negative-results discipline) — rewriting wording to turn an "underpowered experiment" into an "exploratory finding" is **forbidden**
3. `CLAIMS_FROM_RESULTS.md` records the five `evidence_sufficiency: {power, effect_size, replication, scale, baseline}` fields for every claim — on `/paper-writing` self-check, any PRIMARY claim missing this field or containing a failed item → FAIL (`reason_code: insufficient_evidence_as_finding`)

**Anti-packaging red line** (audit hook): if the body contains a strong statement of the "we are the first to find / we reveal" type while any sufficiency item of the corresponding claim fails → FAIL. Stronger wording cannot bypass evidence weight — this is exactly the typical agent death in the CRUX experiments.

**Evaluation-fairness check (v5.2 — consumes the method-registry §3.6 pre-registration protocol)**: every claim involving a comparison gets three extra field checks (written to `CLAIMS_FROM_RESULTS.md`):

| Field | Check | Failure handling |
|-------|-------|------------------|
| `parity_check` | The compared sides' conditions are aligned item by item (same split / same preprocessing / same compute budget / same tuning effort), sourced from RESULT.json condition records | Not aligned → the comparison cannot serve as claim evidence (`reason_code: unfair_comparison`) |
| `all_seeds_reported` | The main result contains all-seed mean±std, not a single best point | Single-point reporting → claim fidelity drops one level (`reason_code: cherry_picked_seed`) |
| `full_grid_reported` | The full hyperparameter-sweep grid is inspectable (body or appendix), not only the best point | Reporting only the best point → claim fidelity drops one level (`reason_code: cherry_picked_config`) |

Also check the `protocol_violation` flag in RESULT.json — results from a violation-flagged experiment group **as a whole** must not support any claim (the group may only be disclosed honestly in an "evaluation process notes" section, not in the main comparison of the results table). If a baseline is labeled `reproduced_by_us`, the paper must state the reproduction method (Limitations or Experimental Setup) and must not pass it off as an official result.

## 4-Dimensional Joint Confidence (TDAL — locked schema)

The overall confidence is computed from 4 dimensions (T × D × A × L), not just theory fidelity. **The full schema, weights, thresholds, producer/consumer contracts, and floor constraints are locked in [`../shared-references/domain-adaptation-contract.md`](../../shared-references/domain-adaptation-contract.md).** This section is the **producer contract** — what `/result-to-claim` MUST emit.

```json
{
  "tdal": {
    "schema_version": "1.0",
    "theoretical": {"value": 0.0, "components": {"sympy_derivation": {}, "logic_verification": {}, "falsification_resistance": {}}},
    "data_availability": {"value": 0.0, "components": {"ouroboros_report": {}, "oss_data_check": {}, "theory_only_flag": {}}},
    "domain_adaptation": {"value": 0.0, "components": {"domain_learner": {}, "seed_paper_match": {}}},
    "literature_support": {"value": 0.0, "components": {"supporting_ratio": {}, "non_contradicting_ratio": {}, "non_gap_ratio": {}}},
    "joint": 0.0,
    "verdict": "one of: STRONG | MODERATE | WEAK | UNSUPPORTED",
    "weakest_dimension": "one of: theoretical | data_availability | domain_adaptation | literature_support",
    "missing_inputs": []
  }
}
```

### Producer Contract (/result-to-claim MUST)

1. **Compute all 4 dimensions**; if any input is missing, set that component to 0.0 and append the dimension to `missing_inputs`. Never silently drop a dimension.
2. **Emit the full machine-readable `tdal` JSON** as a fenced ```json block in `CLAIMS_FROM_RESULTS.md` (in addition to the human-readable per-dimension breakdown).
3. **Compute `joint = T × D × A × L` exactly** — no rounding, no clamping, no weighted-average substitution. The product formula is the strictness contract: a zero in any dimension drives the joint to 0.
4. **Apply verdict thresholds AND floor constraints** (any dimension = 0 → verdict at most WEAK; `missing_inputs` non-empty → verdict at most MODERATE). See [`domain-adaptation-contract.md`](../../shared-references/domain-adaptation-contract.md) § Verdict Thresholds.
5. **Report `weakest_dimension`** as the dimension with the lowest `value` — this MUST be named explicitly in the paper's Limitations section (forwarded to `/paper-writing`).
6. **Never inflate** a dimension to dodge a WEAK/UNSUPPORTED verdict. Missing inputs are reported transparently, not papered over.
7. **UNSUPPORTED verdict → BLOCK** the orchestrator: emit `verdict: BLOCKED, reason_code: unsupported_claim_<weakest_dimension>`, do NOT advance to Phase 11. Paper-writing cannot proceed on an UNSUPPORTED claim.

### Per-Dimension Quick Reference (full weights in contract)

| Dim | Components | Joint role |
|-----|-----------|-----------|
| **T** (Theoretical) | SymPy derivation (0.4) + Logic verification (0.3) + Falsification resistance (0.3) | Multiplier |
| **D** (Data Availability) | Ouroboros report (0.5) + OSS data check (0.3) + Theory-only flag (0.2) | Multiplier |
| **A** (Domain Adaptation) | Domain learner (0.8) + Seed paper match (0.2) — **v2.8**: signature sub-source removed after S1 learner-first | Multiplier |
| **L** (Literature Support) | Supporting ratio (0.5) + Non-contradicting (0.3) + Non-gap (0.2) | Multiplier |

### Per-Dimension Breakdown (MUST emit in CLAIMS_FROM_RESULTS.md)

The confidence assessment MUST include a per-dimension breakdown. Example (full worked example in [`domain-adaptation-contract.md`](../../shared-references/domain-adaptation-contract.md) § Worked Example):

```markdown
## Confidence Assessment

### Theoretical Confidence: 0.85 (STRONG)
- SymPy derivation: PASS (1.0)
- Logic verification: PASS (1.0)
- Falsification: SURVIVE (1.0)
- Weighted: 0.4×1.0 + 0.3×1.0 + 0.3×1.0 = 0.85

### Data Availability Confidence: 0.725 (MODERATE)
- Ouroboros report: 0.85
- OSS data check: DATA_READY (1.0)
- Theory-only flag: 0.0 (not a theory-only problem; real data required)
- Weighted: 0.5×0.85 + 0.3×1.0 + 0.2×0.0 = 0.725

### Domain Adaptation Confidence: 0.80 (STRONG)
- Domain learner: 0.80
- Seed paper match: 0.80
- Weighted: 0.8×0.80 + 0.2×0.80 = 0.80

### Literature Support Confidence: 0.755 (MODERATE)
- Supporting: 10/15 papers (0.67)
- Non-contradicting: 13/15 papers (0.87)
- Non-gap: 12/15 papers (0.80)
- Weighted: 0.5×0.67 + 0.3×0.87 + 0.2×0.80 = 0.755

### Joint Confidence: 0.85 × 0.725 × 0.80 × 0.755 = 0.37
**Verdict**: WEAK — needs strengthening before publication
**Weakest dimension**: Data Availability (0.725) — Ouroboros data score low and not theory-only; need a more reliable data source or an explicit theory-only qualification
```

## Workflow

### Step 0: Load DISCIPLINE_CONTEXT

Read `AGENT_DOC.md` for `DISCIPLINE_CONTEXT` block. In OSS, this is **always** `general` (see [`discipline-context.md`](../../shared-references/discipline-context.md)). There is no economics/cs-ml/physics branch — the universal 3-fidelity ladder below applies to every run.

### Step 1: Collect Results

Gather derivation/verification evidence from whatever sources are available in the project:

1. **Symbolic derivation logs** (`code/derivations/{problem_id}/derivation.py` + `derivations/{problem_id}/derivation_output.md`): the SymPy proof chain from `/theory-derivation`.
2. **Numerical sanity checks** (`derivations/{problem_id}/verification_report.md`): parameter sweeps, counterexample searches from `/dynamic-sandbox`.
3. **Logic verification audit** (`audit_report/LOGIC_VERIFICATION.json`): the 6-dim audit from `/logic-verification`.
4. **refine-logs/FINAL_PROPOSAL.md**: intended claims and derivation design (primary source).
5. **docs/research_contract.md**: optional project-level contract (read if present).

Assemble the key information:
- What derivations were run (assumptions, target outcome, method).
- What the symbolic chain produced (proof complete? gap? contradiction?).
- What the numerical sanity check showed (consistent? divergent? counterexample found?).
- The intended claim these derivations were designed to test.
- Any known caveats or scope limits.

### Step 2: External Reviewer Judgment

Send the prompt to the external reviewer for objective evaluation:

```text
RESULT-TO-CLAIM EVALUATION (OSS — 3-fidelity ladder)

I need you to judge whether derivation/verification results support the intended claim.

Intended claim: [the claim these derivations test]

Derivation run:
[list: assumptions, target outcome, SymPy method]

Symbolic result:
[proof complete / gap / contradiction — paste key steps]

Numerical sanity check:
[parameter sweeps, counterexample search — paste key numbers]

Known caveats:
[any confounding factors, limited regimes, missing comparisons]

Please evaluate:
1. claim_supported: yes | partial | no
2. fidelity_level: symbolic | numerical | qualitative (the highest fidelity the evidence reaches)
3. what_results_support: what the evidence actually shows
4. what_results_dont_support: where the evidence falls short of the claim
5. missing_evidence: specific evidence gaps
6. suggested_claim_revision: if the claim should be strengthened, weakened, or reframed
7. next_analyses_needed: specific additional derivations/checks to fill gaps (if any)
8. confidence: high | medium | low

Be honest. Do not inflate claims beyond what the evidence supports.
A qualitative "looks right" judgment does not support a "proven" claim.
```

### Negative Results Discipline (v5.0)

**Field feedback**: agents package negative results as "honest findings" and offer them as contributions — in real submissions this is fatal (reviewers do not buy "we honestly failed"). The discipline:

1. **Negative results are never contributions**: the claims list in `CLAIMS_FROM_RESULTS.md` only includes results that **positively support the main thesis**; no "we honestly report that X failed / fell short of expectation" may appear in claims, the contribution list, or the Abstract
2. **Two legitimate destinations for negative results**:
   - **Main-experiment-level negative** (core hypothesis unsupported) → not a writing problem, a direction problem: route back to `/experiment-execution`'s **KILL-or-PIVOT stop protocol** (toy level) or trigger a method re-examination (full level); the paper pipeline pauses pending new evidence — **continuing to write the paper on a falsified core hypothesis is forbidden**
   - **Local/boundary negative** (a sub-scenario, baseline, or ablation group falls short) → write into **Limitations/Discussion** as a boundary statement ("our method shows no advantage under condition X, indicating the applicability boundary is Y") — this is the correct form of academic honesty
3. **Ablation/hyperparameter negatives are information, not failure**: an ablation shows a component adds no gain → report honestly that the component's contribution is not significant (valid scientific information in itself), but do not elevate it to a contribution claim such as "we found removal is better" without main-experiment-level evidence
4. **Audit hook**: every claim in `CLAIMS_FROM_RESULTS.md` carries a `polarity: positive|boundary` field; an entry with `polarity: negative` appearing in the claims list → `/paper-writing` self-check FAIL (`reason_code: negative_result_as_contribution`)

### Step 3: Parse and Normalize

Extract structured fields from the external reviewer's response:

```markdown
- claim_supported: yes | partial | no
- fidelity_level: symbolic | numerical | qualitative
- what_results_support: "..."
- what_results_dont_support: "..."
- missing_evidence: "..."
- suggested_claim_revision: "..."
- next_analyses_needed: "..."
- confidence: high | medium | low
```

### Step 3.2: Fidelity Gate (Universal — replaces economics p-value gate and cs-ml SOTA gate)

Apply the 3-fidelity gate to **primary** outcomes only:

1. Parse the external reviewer's `fidelity_level` verdict.
2. **Classify outcomes** (read `refine-logs/FINAL_PROPOSAL.md` to determine pre-specification):
   - **Primary outcomes**: pre-specified, directly testable predictions of the theoretical model.
   - **Secondary outcomes**: mechanism tests, robustness checks, additional analyses (NOT pre-specified).
3. **Apply fidelity gate (on PRIMARY outcomes only)**:
   - `qualitative` only → **REJECT claim** — cannot label "supported"; reframe as "suggests" or "consistent with"
   - `numerical` (default threshold) → **SUPPORT claim** — "supported" or "confirmed numerically" acceptable
   - `symbolic` → **STRONG support** — "proven" or "established" acceptable
4. **Handle secondary outcomes (NOT used in gate)**:
   - Secondary outcomes at `qualitative` fidelity: report in mechanism/robustness section, explain why theory may not predict secondary outcomes directly.
   - Secondary outcomes at `numerical`+ fidelity: report as supportive evidence.
   - **NEVER** use secondary outcomes to reject a claim supported by primary outcomes.
5. **Enforce scope transparency**:
   - If the derivation only holds in a limited regime: MUST qualify the claim with the regime.
   - If the numerical check used synthetic/example parameters: MUST NOT claim "general" — use "for the tested parameters" or "in the tested regime".
   - If a counterexample was found: MUST flag — the claim is falsified for that regime, report honestly.

**Example fidelity gate output:**
```text
FIDELITY GATE:
- Classification of outcomes:
  Primary (pre-specified in FINAL_PROPOSAL.md):
    - convergence_rate: symbolic (full SymPy proof) → STRONG
    - stability_bound:   numerical (sweep confirms, no symbolic proof) → MODERATE
    - general_formula:   qualitative (matches intuition, no proof) → WEAK
  Secondary (mechanism tests):
    - special_case_check: numerical (spot checks pass)
    - limit_behavior:     qualitative (consistent with known result)

- Primary outcomes: 3 (convergence_rate, stability_bound, general_formula)
- Primary outcomes at ≥ numerical fidelity: 2/3
- Fidelity gate: PARTIAL (general_formula is qualitative-only — must reframe or drop)
- Claim strength: MODERATE EVIDENCE (for convergence_rate + stability_bound)
- Scope: convergence_rate proven for compact operators; stability_bound confirmed for |λ|<1
- Required claim framing: "We establish the convergence rate for compact operators (Theorem 1) and confirm the stability bound numerically for |λ|<1. The general formula remains a conjecture supported by qualitative consistency."
```

### Step 3.5: Check Logic Verification Audit

Read `audit_report/LOGIC_VERIFICATION.json` (from `/logic-verification`):
- `logic_status` from the file.
- Attach to verdict output:
  - `logic_status: pass | warn | fail`
- If `fail`: append to verdict "[LOGIC CONCERN] — 6-dim audit found issues, see LOGIC_VERIFICATION.md" and downgrade confidence to `low` regardless of the external reviewer's judgment.
- If `warn`: append to verdict "[LOGIC: WARN] — audit flagged potential issues".
- If the file does not exist: `logic_status = "unavailable"`, verdict is labeled "provisional — no logic verification run". This does NOT block — the pipeline continues, but the claim is framed as "provisional".

### Step 4: Route Based on Verdict

#### `no` — Claim not supported
1. Record postmortem in `findings.md` (Research Findings section):
   - What was tested, what failed, hypotheses for why.
   - Constraints for future attempts (what NOT to try again).
2. Update `AGENT_DOC.md` Pipeline Status.
3. Decide whether to pivot to next idea from `IDEA_CANDIDATES.md` or try an alternative approach.

#### `partial` — Claim partially supported
1. Update the working claim to reflect what IS supported (drop the qualitative-only primary outcomes, or reframe them as conjectures).
2. Record the gap in `findings.md`.
3. Design and run supplementary derivations/checks to fill evidence gaps (e.g., attempt the symbolic proof for the `general_formula` outcome).
4. Re-run result-to-claim after supplementary derivations complete.
5. **Multiple rounds of `partial` on the same claim** → record analysis in `findings.md`, consider whether to narrow the claim scope or switch ideas.

#### `yes` — Claim supported
1. Record confirmed claim in project notes.
2. If secondary outcomes are incomplete → flag in Discussion section.
3. If all evidence is in → ready for paper writing.

### Step 5: Update Research Wiki (if active)

Skip this step entirely if `research-wiki/` does not exist. (OSS does not provision a research wiki by default — this step is reserved for future use.)

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

**Never**:
- Round `partial` up to `yes`. If the external reviewer says `partial`, do not inflate.
- Let the host agent be the judge. The external reviewer evaluates; the host agent collects evidence and routes. This prevents post-hoc rationalization.
- Generalize from a single numerical sanity check on one parameter set. Be honest about scope.
- Label a claim "proven" without `symbolic` fidelity. Label a claim "supported" without at least `numerical` fidelity.
- Block the pipeline if the external reviewer is unavailable. Make a host-agent judgment and mark it `[pending external review]`.

**Always**:
- Record the verdict and reasoning in `findings.md`, regardless of outcome.
- If `confidence` is low, treat the judgment as inconclusive and add derivations/checks rather than committing to a claim.
- Bind every claim to specific evidence (which derivation step, which numerical check, which regime).
- Qualify claims with their regime of validity — never claim "general" when the derivation only holds in a limited regime.

## Output Shape

The final `CLAIMS_FROM_RESULTS.md` contains:
1. **Intended claim** — what the derivations were designed to test
2. **Derivations run** — assumptions, target outcome, SymPy method, numerical checks
3. **External reviewer verdict** — `claim_supported`, `fidelity_level`, `what_results_support`, `what_results_dont_support`, `missing_evidence`, `suggested_claim_revision`, `next_analyses_needed`, `confidence`
4. **Fidelity gate** — primary vs secondary outcome classification, fidelity levels, gate verdict, scope transparency
5. **Logic status** — `pass | warn | fail | unavailable`
6. **Confidence Assessment** — theoretical confidence vs grounding confidence (separated)
7. **Routing decision** — pivot / supplement / confirm with next-step actions

### Confidence Assessment (TDAL — emitted per Phase 10 producer contract)

```markdown
## Confidence Assessment

### Theoretical Confidence
- **Score**: [0-10]
- **Basis**: SymPy derivation status, logic verification results, proof completeness
- **Risks**: [remaining theoretical gaps]

### OSS Sandbox Grounding (from Phase 5a, recomputed)
- **Score**: [0-10]
- **Basis**: OSS sandbox feasibility, adversarial falsification results, analogy mapping, prior probability
- **Risks**: [assumptions that may not hold in OSS sandbox]

### Engineering Grounding (from Phase 5b, inherited, not recomputed)
- **Score**: [0-10] (inherited from `refine-logs/ENGINEERING_GROUNDING.md` eg_average)
- **Report**: See `refine-logs/ENGINEERING_GROUNDING.md` for full 8-dim breakdown + downside protection
- **Risks**: [engineering risks from Phase 5b — compute, deps, ai_dev_cycle, reproducibility, capital, code_complexity, temporal_maturity, regulatory]

### Combined Assessment
- **Grounding confidence**: 0.6 × OSS_sandbox_grounding + 0.4 × engineering_grounding
- **Overall confidence**: [0-10]
- **Recommendation**: 
  - If theoretical ≥ 7 AND grounding ≥ 7: "Strong — suitable for publication"
  - If theoretical ≥ 7 AND grounding 4-6: "Theoretically sound, needs empirical validation"
  - If theoretical ≥ 7 AND grounding < 4: "Interesting theory, high risk of non-transferability"
  - If theoretical < 7: "Insufficient theoretical foundation — revisit derivation"
```

## Reviewer Routing

External reviewer routing, backend selection, and per-CLI registration examples are documented in [`shared-references/reviewer-routing.md`](../../shared-references/reviewer-routing.md).

## Review Tracing

After each external reviewer call, save the trace following [`shared-references/review-tracing.md`](../../shared-references/review-tracing.md) (forensic policy; never silently skip). Respect the `trace` parameter (default: `full`).

## See Also

- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md) — 6-state verdict schema
- [`../shared-references/reviewer-routing.md`](../../shared-references/reviewer-routing.md) — cross-model reviewer routing
- [`../theory-derivation/SKILL.md`](../theory-derivation/SKILL.md) — produces the symbolic derivation chain
- [`../logic-verification/SKILL.md`](../logic-verification/SKILL.md) — produces the 6-dim logic audit
- [`../invariant-check/SKILL.md`](../invariant-check/SKILL.md) — verifies INV-G1 problem anchor freeze
