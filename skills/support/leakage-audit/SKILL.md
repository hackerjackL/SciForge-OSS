---
name: leakage-audit
type: reference-skill
role: structural-leakage-auditor
---

# Leakage Audit (SciForge-OSS — Discipline-Agnostic)

## Quick Reference

- **Purpose**: 审计 Type I 逻辑漏洞 + Type IV 逃逸 (验证与前提矛盾)
- **Input**: METHOD_REGISTRY.md + METHOD_BINDING.md
- **Output**: LEAKAGE_AUDIT.json + LEAKAGE_AUDIT.md
- **Key**: 无学科 overlay；Type I + Type IV 通用；3 轮 callback 到 method-registry

> **Status**: Structural auditor for the canonical leakage types that cause desk rejects. **OSS is discipline-agnostic** — there are no discipline overlays (no economics 14-class, no cs-ml 14-class, no physics 10-class). Only the universal `Type I Logic Gap` + `Type IV Empirical Escape` (generalized beyond physics) are active. Copied from main SciForge and trimmed to OSS's discipline-agnostic design.

## Use When

Use this skill to audit the method registry for the canonical leakage types that cause desk rejects at top venues.

Typical prompts:
- "audit my method registry"
- "check for leakage before paper-write"
- "pre-submission leakage audit"
- "why would a reviewer desk-reject this?"

**MANDATORY** in these situations:
- After `/method-registry` produces `METHOD_REGISTRY.md` + `METHOD_BINDING.md`
- Before `/paper-writing` for any 125-problem output
- During code review in `/dynamic-sandbox` (faster pre-screen than full review)
- During rebuttal preparation — a clean audit is the most credible defense

## Job

Act as a **structural auditor** that catches the canonical leakage types *before* the paper is submitted. The single most common cause of desk rejection is **leakage**: the method looks fine in isolation, but it does not actually test what the theory claims under assumptions the author can defend.

This skill defines:
1. The 3-class leakage framework (Type I / Type II / Type III) + the universalized Type IV
2. The 6-state verdict computation
3. The callback protocol to `/method-registry` (bounded 3 rounds)

**OSS has no discipline overlays.** Main SciForge loads `overlays/{economics,cs-ml,physics,general}.md` for discipline-specific pitfall lists; OSS has none. The audit applies the universal Type I check to every problem, and the universalized Type IV check (any problem where verification escapes premise) when relevant.

What this skill DOES guarantee:
- No CRITICAL Type I logic gaps are silently present
- The method registry chain is at least structurally complete
- The pre-registration hash is locked
- Type IV escape (verification contradicts premise) is caught for any discipline

What this skill does NOT do:
- Assess whether the methodology is novel (that is `/novelty-check`'s job)
- Assess whether claims are supported (that is `/result-to-claim`'s job)
- Assess whether the paper is well-written (that is `/auto-review-loop`'s job)
- Replace subject-matter expertise on novel methodological flaws

## Required Workspace

The audit reads from and writes to the project root:

**Inputs** (must exist):
- `methods/METHOD_REGISTRY.md` — the method registry (from `/method-registry`)
- `methods/METHOD_BINDING.md` — derived from registry Section 3
- `DERIVATION_PLAN.md` — used for method choices (from `/theory-derivation`)
- `results/` — used to compare realized vs declared (if numerical checks have run)
- `src/` (or wherever the derivation/sandbox code lives)

**Outputs**:
- `audit_report/LEAKAGE_AUDIT.md` — human-readable audit report
- `audit_report/LEAKAGE_AUDIT.json` — machine-readable verdict (consumed by downstream skills)
- `audit_report/Type_I.md`, `audit_report/Type_IV.md` — per-lens detail

If `methods/METHOD_REGISTRY.md` does not exist, **ABORT and tell the user to run `/method-registry` first.** Audit without registry is meaningless.

## Configuration

- **Difficulty** — `medium` / `hard` / `nightmare`. Controls audit depth (medium = structural only, hard = + cross-model verification, nightmare = + reviewer memory + debate).

## The Four Leakage Types (OSS Universalized)

### Type I — Logic Gap (Universal, Active for ALL 125 Problems)

> The claimed implications do not mathematically or logically follow from the stated assumptions.

**OSS universal manifestation**: Method ⟹/ Outcome (the expected outcome does not follow from the method).

**Detection**:
- For each implication/outcome, does it follow from the assumptions?
- Are there hidden assumptions not stated that are doing the work?
- Is the implication stronger than what the model can deliver?

> **R5 收敛声明 (v2.3)**: Type I 与 `/logic-verification` 的 `LOGICAL_GAP`/`UNJUSTIFIED_ASSERTION` 关注同一逻辑正确性问题——本 audit **交叉引用** logic-verification 的裁决：若 `LOGIC_VERIFICATION.json` 已对该 claim 判定 FATAL/CRITICAL，则 Type I 直接继承（不重复判定），只追加"该方法/结果是否从假设推导"这一板块性视角；避免对同一缺口双重判罚。

### Type II — Hidden Violation (OSS: NOT APPLICABLE)

> The empirical methodology silently violates the paper's own theoretical assumptions.

**OSS status**: **NOT APPLICABLE**. Type II is discipline-specific (economics 14-class, cs-ml 14-class, physics 10-class). OSS has no discipline-specific assumptions to violate — the agent's runtime reasoning in `/theory-derivation` + `/dynamic-sandbox` handles domain-specific assumption tracking, not an overlay checklist. Return `NOT_APPLICABLE` for Type II in every OSS audit.

### Type III — Proxy Mismatch (OSS: NOT APPLICABLE)

> The metric/parameter delivered by the methodology does not actually measure or test the core theoretical implication.

**OSS status**: **NOT APPLICABLE**. Type III is discipline-specific (economics P≠M structural object, cs-ml Metric≠Contribution, physics Verification≠Physical). OSS has no structural-object concept that's discipline-agnostic — the agent's runtime reasoning handles whether the method tests the theory, not an overlay. Return `NOT_APPLICABLE` for Type III in every OSS audit.

### Type IV — Empirical Escape (OSS Universalized, Active When Verification Runs)

> The Verification step closes the loop back to the Premise, but the empirical/numerical result escapes the regime where the assumption holds.

**OSS universal manifestation**: any 125 problem where the numerical verification (from `/dynamic-sandbox`) contradicts the theoretical premise (from `/theory-derivation`). This is generalized beyond physics — main SciForge had it as physics-only PNV escape; OSS applies it to any discipline where V ≠ P.

**Detection**:
- For each verification outcome, does it confirm the premise within the regime where the assumption holds?
- If the numerical result diverges from the theoretical prediction, is it because the assumption breaks outside a regime?
- Flag escapes — the verification "works" numerically but outside the regime where the premise is valid.

## Audit Workflow

### Step 0: Load DISCIPLINE_CONTEXT

Read `AGENT_DOC.md` for `DISCIPLINE_CONTEXT` block. In OSS, this is **always** `general` (see [`discipline-context.md`](../../shared-references/discipline-context.md)). There is no overlay to load — the universal Type I + Type IV checks are inlined below.

### Step 1: Locate the Artifacts

Confirm the input files exist:
```
project_root/
├── methods/METHOD_REGISTRY.md    # must exist (from /method-registry)
├── methods/METHOD_BINDING.md     # must exist (derived from Section 3)
├── DERIVATION_PLAN.md            # used for method choices
├── results/                      # used to compare realized vs declared (if any)
├── src/                          # or wherever the derivation/sandbox code is
└── ...
```

If `methods/METHOD_REGISTRY.md` does not exist, **ABORT**.

### Step 2: Parse the Registry Chain

Extract from `methods/METHOD_REGISTRY.md`:
- Section 1: Problem Anchor (frozen — Q-id from `problems/125-SCIENCE-PROBLEMS.md`)
- Section 2: Assumptions (universal schema)
- Section 3: Method Selection (hash-locked)
- Section 4: Outcomes (primary/secondary)
- Section 5: Reproducibility

### Step 3: Run the Audit Lenses

#### 3.1 Type I Audit (Logic Gap) — ACTIVE for all 125 problems

For each implication/outcome:
- Read the assumptions that should logically imply it
- Use the LLM to evaluate: "Does this implication follow from these assumptions?"
- If "no" or "only with additional assumptions" → **Type I leakage**

Output: `audit_report/Type_I.md` with one entry per implication, classified as:
- `CLEAN` (follows)
- `WEAK` (follows with caveats; document)
- `LEAKY` (does not follow without additional assumptions)

#### 3.2 Type II Audit (Hidden Violation) — NOT APPLICABLE in OSS

Return `NOT_APPLICABLE`. No overlay, no pitfall checklist. The agent's runtime reasoning handles assumption tracking.

#### 3.3 Type III Audit (Proxy Mismatch) — NOT APPLICABLE in OSS

Return `NOT_APPLICABLE`. No overlay, no structural-object concept. The agent's runtime reasoning handles method-theory alignment.

#### 3.4 Type IV Audit (Empirical Escape) — ACTIVE when verification runs

For each verification outcome (from `/logic-verification` + `/dynamic-sandbox`):
- Does the numerical result confirm the theoretical premise within the regime where the assumption holds?
- If the result diverges, is it because the assumption breaks outside a regime?

Output: `audit_report/Type_IV.md` with one entry per verification, classified as:
- `CLOSED` (verification confirms premise in the valid regime)
- `ESCAPE` (verification "works" numerically but outside the regime where the premise is valid)
- `NO_VERIFICATION` (no numerical verification ran — advisory only)

### Step 4: Compute the Audit Verdict

```
verdict = PASS    if no CRITICAL Type I leakages AND no Type IV ESCAPE
verdict = WARN    if any Type I WEAK but no LEAKY, OR Type IV NO_VERIFICATION
verdict = FAIL    if any Type I LEAKY on a primary outcome, OR any Type IV ESCAPE
verdict = NOT_APPLICABLE  never (OSS always runs Type I; this state is reserved for future use)
```

The audit verdict is the gate for `/paper-writing`:
- `FAIL` → block `/paper-writing`; require fix
- `WARN` → `/paper-writing` proceeds, but the leakage caveat must be added to the Discussion section
- `PASS` → clean

### Step 5: Persist the Audit Report

Write to `audit_report/LEAKAGE_AUDIT.md`:
```markdown
# Leakage Audit Report

**Project**: [name]
**Date**: [date]
**DISCIPLINE_CONTEXT**: general (OSS universal)
**Auditor**: leakage-audit
**Verdict**: PASS / WARN / FAIL

## Summary
- Type I (Logic Gap): [N leaky / total]
- Type II (Hidden Violation): NOT APPLICABLE (OSS has no discipline overlay)
- Type III (Proxy Mismatch): NOT APPLICABLE (OSS has no discipline overlay)
- Type IV (Empirical Escape): [N escape / total, or NO_VERIFICATION]

## Critical Leakages (must fix)
1. ...

## Major Leakages (should fix or discuss in appendix)
1. ...

## Recommendations
- [Specific, actionable fix for each critical/major leakage]
```

### Step 6: Emit Machine-Readable Verdict

Write to `audit_report/LEAKAGE_AUDIT.json`:
```json
{
  "verdict": "FAIL",
  "discipline_context": "general",
  "type_i": {"n_leaky": 1, "n_total": 5, "items": []},
  "type_ii": "NOT_APPLICABLE",
  "type_iii": "NOT_APPLICABLE",
  "type_iv": {"n_escape": 0, "n_total": 3, "items": []},
  "callback": {
    "target": "/method-registry",
    "reason": "Type I LEAKY on primary outcome: implication does not follow from stated assumptions",
    "iteration": 1,
    "max_iterations": 3
  },
  "blockers": ["Type I: primary outcome O1 not implied by assumptions A1-A3 — add A4 or weaken O1"],
  "recommendations": ["State A4 (compactness of the operator) explicitly in Section 2, OR weaken O1 to a conditional form"]
}
```

This JSON is consumed by:
- `/result-to-claim` (rejects if FAIL)
- `/auto-review-loop` (rejects if FAIL)
- `/paper-writing` (requires WARN or PASS)
- `/invariant-check` (the pre-paper-writing gate checks verdict is PASS or WARN)

## 6-State Verdict Schema

This skill uses the 6-state machine defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md):

| State | Meaning | When this skill emits it |
|-------|---------|--------------------------|
| `PASS` | No CRITICAL Type I + no Type IV ESCAPE | Step 4, clean |
| `WARN` | Type I WEAK OR Type IV NO_VERIFICATION | Step 4, caveats but no critical |
| `FAIL` | Type I LEAKY on primary OR Type IV ESCAPE | Step 4, critical found |
| `NOT_APPLICABLE` | (reserved — OSS always runs Type I) | never emitted in OSS |
| `BLOCKED` | Prerequisite missing (no `methods/METHOD_REGISTRY.md`) | Step 1 inputs missing |
| `ERROR` | Skill itself failed | Internal error |

## Callback Protocol (to /method-registry)

When the audit finds a Type I LEAKY on a primary outcome, the finding triggers a **callback** to `/method-registry` to revise the method binding. This closes the loop: the audit identifies the structural flaw, the method registry suggests the fix, and the binding is updated for the next iteration.

### When the callback fires
The callback fires if and only if:
- `type_i.n_leaky > 0` on a primary outcome, AND
- The current method is identified in `methods/METHOD_BINDING.md`

If the current method cannot be identified, the audit emits `BLOCKED` instead of `FAIL`, and the callback field is omitted — the orchestrator must first run `/method-registry` to produce the binding.

### Callback lifecycle (bounded loop)
1. Audit finds Type I LEAKY → emits `callback` in LEAKAGE_AUDIT.json
2. Orchestrator reads `callback` → re-invokes `/method-registry --callback audit_report/LEAKAGE_AUDIT.json`
3. `/method-registry` revises METHOD_BINDING.md → emits `METHOD_BINDING_DIFF.md`
4. Orchestrator re-invokes `/leakage-audit` to confirm the fix
5. If the same logic gap persists → repeat (up to 3 iterations)
6. **If 3 iterations exhausted on the same logic gap → orchestrator halts with fallback**:
   - Downgrade `METHOD_BINDING.md` status to `DRAFT`
   - Append `LOGIC_GAP_FUNDAMENTAL_ISSUE` flag to `METHOD_BINDING.md`
   - Log halt event in `methods/APPROVAL_LOG.txt` with `action=CALLBACK_EXHAUSTED`
   - Report to user: "The logic gap is fundamental — the implication cannot be defended under the current assumptions. Recommend returning to `/idea-discovery` to select a different approach to the problem."
   - **Do NOT silently continue** — a logic gap surviving 3 method swaps indicates the approach itself is flawed, not a method selection problem.

## Quality Gates (Block Downstream)

The audit REJECTS the project (returns FAIL) if any of:

| Gate | Trigger | Why |
|------|---------|-----|
| G1 | Type I LEAKY on a primary implication/outcome | Implication not implied by theory |
| G2 | Type IV ESCAPE on any verification | Numerical result escapes the regime where the premise holds |
| G3 | Missing `methods/METHOD_REGISTRY.md` | No chain to audit |
| G4 | Section 3 (Method Selection) is post-hoc | Pre-registration violated |

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **Always require `methods/METHOD_REGISTRY.md` first.** Audit without registry is meaningless.
- **Be conservative.** Mark borderline Type I cases as WEAK rather than CLEAN; let the user downgrade with justification.
- **Cite the registry section for each finding.** "G1 in `methods/METHOD_REGISTRY.md` Section 3" is the right granularity.
- **Do not run the code.** The audit is structural; runtime issues are caught by `/dynamic-sandbox`.
- **3-round callback limit.** Do not exceed 3 method revisions for the same logic gap. If exhausted, halt and report.
- **No discipline overlays.** OSS has no `overlays/{economics,cs-ml,physics}.md`. Do not reintroduce discipline-specific Type II/III pitfall lists — they are discipline-specific and OSS is discipline-agnostic. If a problem seems to need a discipline-specific check, the agent's runtime reasoning handles it, NOT an overlay.
- **Type II/III are NOT APPLICABLE.** Always return `NOT_APPLICABLE` for these in OSS — do not attempt to audit them without an overlay.

## Output Shape

The audit produces:
1. `audit_report/Type_I.md` — per-implication logic-gap classification (CLEAN / WEAK / LEAKY)
2. `audit_report/Type_IV.md` — per-verification empirical-escape classification (CLOSED / ESCAPE / NO_VERIFICATION)
3. `audit_report/LEAKAGE_AUDIT.md` — consolidated human-readable report with verdict and recommendations
4. `audit_report/LEAKAGE_AUDIT.json` — machine-readable verdict consumed by downstream skills

## Composing With Other Skills

```
/method-registry                        ← upstream (produces METHOD_REGISTRY.md)
    → /leakage-audit                    ← you are here
        → /result-to-claim (consumes verdict)
        → /auto-review-loop (consumes verdict)
        → /paper-writing (blocked if FAIL)
        → /invariant-check (pre-paper-writing gate checks verdict is PASS or WARN)
```

This skill is the **quality gate** for the pre-writing boundary. It runs after the registry is in place and before the paper is written.

## See Also

- [`../method-registry/SKILL.md`](../method-registry/SKILL.md) — produces the registry this skill audits
- [`../invariant-check/SKILL.md`](../invariant-check/SKILL.md) — verifies verdict at the pre-paper-writing gate
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md) — 6-state verdict schema
