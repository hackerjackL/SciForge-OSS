---
name: logic-verification
version: 1.1.2
description: "6-dimension logical consistency audit + 20-category issue taxonomy + acceptance gate (zero FATAL/CRITICAL). Phase 8. Invoke to rigorously verify a derivation/argument/proof."
type: support-skill
role: logical-consistency-auditor
---

# Logic Verification (SciForge-OSS — Structured Proof Checking, Discipline-Agnostic)

## Quick Reference

- **Purpose**: 6 维度逻辑一致性审计 + 20 分类问题体系
- **Input**: derivations/{problem_id}/derivation_output.md
- **Output**: LOGIC_VERIFICATION.md + LOGIC_VERIFICATION.json
- **Key**: 结构化证明检查 (非跨模型)；20 类问题；3 轮上限；验收门控 (零 FATAL/CRITICAL)

> **Status**: Rigorous logical verification of a derivation / argument / paper draft via structured proof checking. **OSS merges main SciForge's `proof-checker`** (20-category issue taxonomy, 2-axis severity, side-condition checklists, acceptance gate) **into this skill**. **OSS is discipline-agnostic** — no LaTeX `align*` environment-specific checks, no physics SI-units enforcement, no economics estimator-verification. The universal 6-dimension logical consistency audit applies to every problem.

## Use When

Use this skill when asked to rigorously verify a mathematical derivation, logical argument, or paper draft — identify gaps via structured proof checking with the 20-category issue taxonomy, fix each gap with full derivations, re-check until convergence, and generate a detailed audit report.

Typical prompts:
- "检查证明" / "verify proof" / "proof check"
- "审证明" / "check this derivation"
- "rigorously verify this theory paper's proofs"
- "verify the logical consistency of this argument"

## Job

Systematically verify a derivation / argument / paper draft via structured proof checking, fix identified gaps, re-check until convergence, and generate a detailed audit report with proof-obligation accounting. The non-negotiable goal: **correctness matters more than declaring success.** Never silently pass an argument with open gaps; never fabricate a fix.

## Required Workspace

The project directory containing:
- `derivations/{problem_id}/derivation_output.md` — the derivation to audit (from `/theory-derivation`)
- `paper/main.tex` + `paper/sections/*.tex` — if auditing a paper draft (from `/paper-writing`)
- `audit_report/LOGIC_VERIFICATION.md` — cumulative round-by-round audit log (created by this skill)
- `audit_report/LOGIC_VERIFICATION.json` — machine-readable verdict (always emitted)
- `audit_report/LOGIC_CHECK_STATE.json` — compact recovery state (written after each round)

## Configuration

- **MAX_REVIEW_ROUNDS = 3** — maximum review → fix → re-review iterations before falling through to the Unrecoverable Argument Protocol.
- **AUDIT_DOC = `audit_report/LOGIC_VERIFICATION.md`** — cumulative log.
- **STATE_FILE = `audit_report/LOGIC_CHECK_STATE.json`** — recovery state.
- **RENDER_HTML = true** — auto-render the audit log to HTML at workflow end.

## Acceptance Gate

The argument passes when ALL of the following hold:
1. Zero open FATAL or CRITICAL issues.
2. Every theorem/lemma/proposition has: (i) explicit hypotheses, (ii) a derivation with all interchanges justified, (iii) every application discharges its hypotheses in the ledger.
3. All big-O / Θ / o statements have declared parameter dependence and uniformity scope.
4. Counterexample pass executed on all key lemmas (log candidates even if none found).

This gate is objective and replaces subjective scoring.

## Issue Taxonomy (20 categories, 4 groups — universal, no discipline-specific categories)

### Group A: Logic & Proof Structure

| Category | Description |
|----------|-------------|
| **UNJUSTIFIED_ASSERTION** | Claim stated without proof or reference |
| **UNPROVEN_SUBCLAIM** | "Clearly" / "it follows" hides a nontrivial lemma |
| **QUANTIFIER_ERROR** | Wrong order ∀/∃, missing scope qualifier |
| **IMPLICATION_REVERSAL** | Uses (A⇒B) as (B⇒A), or claims equivalence with only one direction |
| **CASE_INCOMPLETE** | Misses boundary/degenerate cases |
| **CIRCULAR_DEPENDENCY** | Lemma uses theorem that depends on it |
| **LOGICAL_GAP** | A step is not justified by what precedes it |

### Group B: Analysis & Measure Theory

| Category | Description |
|----------|-------------|
| **ILLEGAL_INTERCHANGE** | Swaps limit/expectation/derivative/integral without DCT/MCT/Fubini |
| **NONUNIFORM_CONVERGENCE** | Pointwise convergence used as uniform |
| **MISSING_DOMINATION** | DCT cited but no dominating function given |
| **INTEGRABILITY_GAP** | Uses E|X|^p without proving/assuming finite moments |
| **REGULARITY_GAP** | Differentiability/Lipschitz/convexity used but not established |
| **STOCHASTIC_MODE_CONFUSION** | Mixes a.s./in prob./in L²/in expectation |

### Group C: Model & Parameter Tracking

| Category | Description |
|----------|-------------|
| **MISSING_DERIVATION** | A quantity is used but never derived from the model |
| **HIDDEN_ASSUMPTION** | Argument silently uses a condition not in the theorem |
| **INSUFFICIENT_ASSUMPTION** | Hypotheses too weak for argument (counterexample exists) |
| **DIMENSION_TRACKING** | Parameter dependence not explicit |
| **NORMALIZATION_MISMATCH** | Coordinate/scaling conventions inconsistent |
| **CONSTANT_DEPENDENCE_HIDDEN** | "C" depends on parameters but treated as universal |

### Group D: Scope & Claims

| Category | Description |
|----------|-------------|
| **SCOPE_OVERCLAIM** | Conclusion stated more broadly than argument supports |
| **REFERENCE_MISMATCH** | Cited theorem's hypotheses not verified at point of use |

**OSS has no Group E (discipline-specific)**. Main SciForge's physics SI-units / economics estimator / cs-ml benchmark categories are removed — OSS is discipline-agnostic.

## Two-Axis Severity System

### Axis A — Argument Status (what is wrong)

| Status | Meaning |
|--------|---------|
| **INVALID** | Statement false as written (counterexample exists or contradiction) |
| **UNJUSTIFIED** | Could be true, but current argument does not establish it |
| **UNDERSTATED** | True only after strengthening assumptions |
| **OVERSTATED** | True only after weakening conclusion / adding qualifiers |
| **UNCLEAR** | Ambiguous notation / definition drift |

### Axis B — Impact (how much breaks)

| Impact | Meaning |
|--------|---------|
| **GLOBAL** | Breaks main theorem or core dependency chain |
| **LOCAL** | Affects a side result but not the main theorem |
| **COSMETIC** | Exposition only |

### Severity Labels (derived)

| Label | Definition |
|-------|------------|
| **FATAL** | INVALID + GLOBAL |
| **CRITICAL** | (INVALID + LOCAL) or (UNJUSTIFIED + GLOBAL) |
| **MAJOR** | (UNJUSTIFIED + LOCAL) or (UNDERSTATED/OVERSTATED + GLOBAL) |
| **MINOR** | Clarity / notation / dimension bookkeeping that doesn't change claims |

## Side-Condition Checklists for Common Theorems

When the argument invokes any of the following, require explicit verification of ALL listed conditions:

| Theorem | Required Conditions |
|---------|---------------------|
| **DCT** (Dominated Convergence) | Pointwise a.e. convergence + integrable dominating function |
| **Fubini** | σ-finite measure + integrability of the iterated integral |
| **Jensen** | Convex function + integrable random variable + finite expectation |
| **Markov** | Finite expectation + positive threshold |
| **Rademacher** | Lipschitz function on open set |
| **Stone-Weierstrass** | Algebra separates points + contains constants + compact Hausdorff space |
| **Arzelà-Ascoli** | Equicontinuity + pointwise boundedness + compact domain |
| **Implicit Function** | C¹ function + nonsingular Jacobian at the point |
| **Contraction Mapping** | Contraction constant < 1 + complete metric space |

## Workflow

### Phase 0: Parse Argument

Read the argument / derivation / paper draft. Extract:
- Theorems / propositions / lemmas / definitions
- Assumptions / hypotheses / scope claims
- Notation / symbols
- The Q-id (from the document header — verify INV-G1 freeze)
- Step-by-step derivation chain

### Phase 0.5: Build Skeleton

Create `audit_report/ARGUMENT_SKELETON.md`:
- Dependency DAG (which claim depends on which)
- Assumption ledger (every assumption, where stated, where used)
- Micro-claim inventory (every assertion, its location, its justification)

### Phase 1: First Review (Fresh Context)

The agent switches to "proof auditor" role and applies the 20-category issue taxonomy systematically. Read the argument + mandatory checklist with maximum reasoning effort. The audit sees only the argument content; no prior context.

The audit flags each issue with:
- Category (from the 20-category taxonomy)
- Axis A status
- Axis B impact
- Derived severity (FATAL/CRITICAL/MAJOR/MINOR)
- Exact location (file + section + line)
- Minimal fix

### Phase 2: Fix Issues

For each FATAL/CRITICAL/MAJOR issue:
1. Read the issue + minimal fix recommendation
2. Apply the fix in the source document (derivation / paper draft)
3. Record the fix in `audit_report/LOGIC_VERIFICATION.md`
4. Re-verify the fix with SymPy (if mathematical) or with a structured re-check (if logical)

Never fabricate a fix. If a fix requires a new assumption, state it explicitly. If a fix requires weakening the claim, do so honestly.

### Phase 3: Re-Review (Carried Context)

Send the updated argument to the same reviewer thread (carried context — the reviewer remembers prior issues and can judge whether fixes closed the gaps). The reviewer re-flags any unresolved issues + any new issues introduced by the fixes.

### Phase 3.5: Blind Second Review (Fresh Context)

After Phase 3 convergence (all prior issues resolved), send the updated argument to a **fresh reviewer context** (no memory of prior rounds). This catches issues the original reviewer may have tacitly accepted.

If the blind review finds new FATAL/CRITICAL issues → return to Phase 2.

### Phase 3.6: Counterexample Pass

For every key lemma / proposition, run a counterexample search:
- Identify the minimal assumptions needed
- Construct test cases that probe the boundary (zero weight, singular case, degenerate distribution, non-unique argmin)
- Log candidates even if none found (audit trail)

If a counterexample is found → the lemma is INVALID → FATAL severity → fix or downgrade.

### Phase 4: Convergence or Escalation

If after MAX_REVIEW_ROUNDS the argument still has open FATAL/CRITICAL issues → **Unrecoverable Argument Protocol**:
1. Write `audit_report/UNRECOVERABLE_ARGUMENT.md` with the open issues + why each fix failed
2. Downgrade the argument status to `NOT YET COHERENT`
3. Recommend returning to `/theory-derivation` for a reframed derivation OR `/idea-discovery` for a different approach
4. **Do NOT silently pass** — a FATAL issue surviving 3 rounds indicates the argument is fundamentally flawed

### Phase 5: Emit Verdict

Write `audit_report/LOGIC_VERIFICATION.json`:
```json
{
  "verdict": "one of: PASS | WARN | FAIL | BLOCKED | ERROR",
  "q_id": "[frozen — from document header]",
  "n_fatal": 0,
  "n_critical": 0,
  "n_major": 2,
  "n_minor": 5,
  "issues": [],
  "counterexample_pass": "one of: executed | skipped",
  "review_rounds": 3,
  "argument_status": "one of: COHERENT AS STATED | COHERENT AFTER REFRAMING | NOT YET COHERENT"
}
```

Verdict mapping:
- `PASS`: zero FATAL/CRITICAL/MAJOR, all theorems discharge hypotheses, counterexample pass executed
- `WARN`: zero FATAL/CRITICAL, some MAJOR with explicit caveats documented
- `FAIL`: any FATAL/CRITICAL unresolved
- `BLOCKED`: prerequisite missing (no derivation / no Q-id)
- `ERROR`: skill itself failed

### Phase 6: Render HTML (if enabled)

Auto-render `audit_report/LOGIC_VERIFICATION.md` to HTML inline by the agent. Non-blocking: if rendering fails, log and continue.

## 6-State Verdict Schema

This skill uses the 6-state machine defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md):

| State | Meaning | When this skill emits it |
|-------|---------|--------------------------|
| `PASS` | All issues resolved, acceptance gate satisfied | Phase 4 convergence |
| `WARN` | Minor issues remain, documented as caveats | Phase 4 with minor residuals |
| `FAIL` | FATAL/CRITICAL unresolved after MAX_REVIEW_ROUNDS | Phase 4 escalation |
| `NOT_APPLICABLE` | (reserved — OSS always runs this for derivations) | never emitted |
| `BLOCKED` | Prerequisite missing (no derivation / no Q-id) | Phase 0 inputs missing |
| `ERROR` | Skill itself failed | Internal error |

## Output Protocols
> **v5.2 评判产物位置**：本 skill 产出的机读 verdict/hash/审计 JSON 一律写入 `verdicts/`（文件名见 [`output-protocol.md`](../../shared-references/output-protocol.md) 产物目录结构；叙述性报告留在原 stage 目录）。


> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **Never silently pass an argument with open gaps.** Correctness matters more than declaring success.
- **Never fabricate a fix.** If a fix requires a new assumption, state it. If a fix requires weakening the claim, do so honestly.
- **Structured proof checking is mandatory.** The agent audits its own work using the 20-category taxonomy — never skips the systematic checklist.
- **3-round limit.** Do not exceed MAX_REVIEW_ROUNDS. If exhausted, escalate to the Unrecoverable Argument Protocol — do NOT silently continue.
- **Counterexample pass is mandatory** for key lemmas. Log candidates even if none found.
- **No discipline-specific categories.** Do not reintroduce physics SI-units / economics estimator / cs-ml benchmark Group E categories. The universal 20-category taxonomy above is the complete set.
- **No LaTeX environment-specific checks.** Main SciForge's `proof-checker` has `align*` / `gather*` / `split` environment-specific checks; OSS removes these (the argument may be in markdown / plain text / SymPy output, not only LaTeX).

## Output Shape

The final output is:
1. `audit_report/ARGUMENT_SKELETON.md` — dependency DAG + assumption ledger + micro-claim inventory
2. `audit_report/LOGIC_VERIFICATION.md` — cumulative round-by-round audit log
3. `audit_report/LOGIC_VERIFICATION.json` — machine-readable verdict (consumed by `/leakage-audit`, `/result-to-claim`, `/quality-gate`)
4. `audit_report/LOGIC_CHECK_STATE.json` — compact recovery state
5. `audit_report/UNRECOVERABLE_ARGUMENT.md` (only if Phase 4 escalates)

## Composing With Other Skills

```
/theory-derivation (produces the derivation)
    → /logic-verification                ← you are here
        → /leakage-audit (consumes verdict — Type I logic gap + Type IV escape)
        → /result-to-claim (consumes verdict — claim gating)
        → /quality-gate (consumes verdict — QF-G2 quality floor check)
        → /paper-writing (consumes verdict — blocks if FAIL)
```

## See Also

- [`../shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md) — 6-state verdict schema
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../theory-derivation/SKILL.md`](../theory-derivation/SKILL.md) — produces the derivation this skill audits
- [`../leakage-audit/SKILL.md`](../leakage-audit/SKILL.md) — complementary audit (Type I logic gaps + Type IV escape)
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — 3-fidelity claim gate (downstream)
- [`../auto-review-loop/SKILL.md`](../auto-review-loop/SKILL.md) — downstream structured self-review loop
