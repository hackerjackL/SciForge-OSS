---
name: method-registry
version: 0.1.0
description: "Build the 8-section method registry + hash-lock Section 3 + human approval gate. Phase 5. Invoke after idea selection to pre-register the methodology before derivation."
type: reference-skill
role: method-registry-builder
---

# Method Registry (SciForge-OSS — Discipline-Agnostic)

## Quick Reference

- **Purpose**: 方法预注册 + hash 锁 + 强制人类审批，防止事后方法选择
- **Input**: refine-logs/FINAL_PROPOSAL.md
- **Output**: METHOD_REGISTRY.md + REGISTRY_HASH.txt + APPROVAL_LOG.txt
- **Key**: 8 节 schema；Section 3 (Method Selection) 锁定；假设质量评分 (新增)；强制人类审批

> **Status**: Builds a structured `METHOD_REGISTRY.md` that locks the method selection BEFORE derivations are run, preventing post-hoc method shopping and scope creep. **OSS is discipline-agnostic** — there are no discipline overlays (no economics AIM schema, no cs-ml SOTA schema, no physics PNV schema). Only the universal 8-section schema with a Type I Logic Gap self-audit is active. Copied from main SciForge and trimmed to OSS's single-row design.

## Use When

Use this skill to build and maintain a structured `METHOD_REGISTRY.md` that locks the method selection BEFORE derivations are run, preventing post-hoc method shopping, scope creep, and problem drift.

Typical prompts:
- "register methods"
- "pre-register method selection"
- "build method registry"
- "锁定方法选择"

**MANDATORY** at the start of the OSS pre-writing phase (Phase 5 of `/auto-pipeline`, between `/universal-retrieval` and `/theory-derivation`).

**Do NOT invoke for**:
- After derivations are run (post-hoc registration is research fraud)

## Job

Turn the vague reviewer question — "did you decide your method BEFORE seeing results, or after?" — into a **machine-readable, auditable, structured artifact** (`METHOD_REGISTRY.md`) with a cryptographic hash lock.

The non-negotiable goal: **the registry is the entry point for the pre-writing boundary.** Without it, no downstream skill (`/leakage-audit`, `/result-to-claim`) can be trusted. Section 3 (Method Selection) is locked the moment the user approves the registry — the agent can never modify it after seeing results.

This skill defines:
1. The 8-section schema template (universal — no discipline-specific fields)
2. The hash lock mechanism (cryptographic pre-registration)
3. The 6-state verdict schema (shared with `/invariant-check`)
4. The bounded 3-round callback protocol (shared with `/leakage-audit`)

**OSS has no discipline overlay.** Main SciForge loads `overlays/{economics,cs-ml,physics,general}.md` for discipline-specific Section 2 schema, Section 6 pitfall checklist, persona, venue standards; OSS has none. The universal schema below applies to every 125-problem run.

## Required Workspace

The registry lives at `methods/METHOD_REGISTRY.md`. The structure is rigid; each section is required. Related artifacts:
- `methods/REGISTRY_HASH.txt` — SHA256 of the registry Section 3, cited to prove pre-registration.
- `methods/APPROVAL_LOG.txt` — structured human-checkpoint log (timestamp / approver / approved_section_3_hash / signature).
- `methods/METHOD_BINDING.md` — derived from Section 3, consumed by `/theory-derivation` and `/leakage-audit`.
- `methods/OUTCOME_CLASSIFICATION.md` — extracted from Section 4, consumed by `/result-to-claim` and `/invariant-check`.
- `AGENT_DOC.md` — gets a "Method Registry: METHOD_REGISTRY.md" pointer.

## Configuration

- **Target venue** — OSS outputs to the unified `elsarticle` preprint (see [`venue-profiles.md`](../../shared-references/venue-profiles.md)). No venue-specific robustness checks; the universal checks below apply.
- **Fidelity threshold** — the minimum fidelity level required to support a primary claim (default: `numerical`). Drives the gate in `/result-to-claim`. Configurable to `symbolic` (stricter) or `qualitative` (lenient).

## METHOD_REGISTRY.md Structure (Universal — no discipline overlay)

```markdown
# METHOD_REGISTRY.md — [Project Title]

**Generated**: [date]
**DISCIPLINE_CONTEXT**: general (OSS — discipline-agnostic)
**Target Venue**: unified elsarticle preprint (see venue-profiles.md)
**Last Updated**: [date]
**Problem Q-id**: [from problems/125-SCIENCE-PROBLEMS.md, frozen by INV-G1]

---

## 1. Problem Anchor

The frozen research question + boundary. Inherited from the orchestrator's Phase 1 (problem understanding). Cannot be modified after this point.

| Field | Value |
|-------|-------|
| Q-id | [from problems/125-SCIENCE-PROBLEMS.md] |
| Problem statement | [verbatim from FINAL_PROPOSAL.md Problem Anchor] |
| Scope boundary | [what is in scope, what is out] |
| Frozen hash | [SHA256 of Problem Anchor text] |

## 2. Assumptions (Universal schema with quality scoring)

Every assumption is scored for reasonability. This is the **assumption registry** — used by `/adversarial-falsification` for stress testing and by `/result-to-claim` for confidence calibration.

| Field | Value |
|-------|-------|
| A1 | [assumption 1, formal statement + plain-language] |
| A1_reasonability | [0-10] — how realistic is this assumption? 10 = universally true, 0 = never true in practice |
| A1_impact_if_violated | fatal / severe / minor |
| A1_evidence | [literature or reasoning supporting this score] |
| A2 | [assumption 2, ...] |
| A2_reasonability | [0-10] |
| A2_impact_if_violated | fatal / severe / minor |
| A2_evidence | [literature or reasoning supporting this score] |

**Assumption Health Score**: [average of all reasonability scores]
**Fatal assumptions with reasonability < 5**: [count] — if > 0, flag as HIGH RISK
**Assumption quality verdict**: HEALTHY / MODERATE / WEAK
| ... | ... |
| Falsification signal | [what would invalidate the assumption set] |

## 3. Method Selection (LOCKED — hash target)

**This section is the pre-registration lock.** Once the user approves the registry, this section's SHA256 is recorded in `REGISTRY_HASH.txt` and can NEVER be modified without explicit re-approval.

| ID | Method | Derivation approach | Data/Parameters required | Invalidation Signal |
|----|--------|---------------------|--------------------------|---------------------|
| M1 | [method name] | [SymPy derivation chain / numerical sanity check / qualitative reasoning] | [parameters, regimes] | [what would invalidate] |

**Method Binding**: `methods/METHOD_BINDING.md` is derived from this section. Any change here MUST propagate to METHOD_BINDING.md and trigger re-audit via `/leakage-audit`.

## 4. Outcomes (Primary vs Secondary)

Pre-registered outcome classification. **Cannot be changed post-hoc.**

| Outcome | Classification | Pre-specified In | Fidelity target | Rationale |
|---------|----------------|------------------|-----------------|-----------|
| [outcome_1] | PRIMARY | [DERIVATION_PLAN.md source] | symbolic | [why primary] |
| [outcome_2] | SECONDARY | [source] | numerical | [why secondary] |

**Fidelity gate** (universal): claim supported if ≥ 1 primary outcome reaches the configured fidelity threshold (default: numerical). See `/result-to-claim` for the 3-fidelity ladder.

## 5. Reproducibility

| Field | Value |
|-------|-------|
| Seed strategy | [fixed / grid_search / bootstrap — for numerical sanity checks] |
| Parameter availability | [values, ranges, access conditions] |
| Code availability | [URL or access conditions for SymPy scripts / sandbox code] |
| Compute resources | [CPU type, hours, memory — sandbox is lightweight by OSS design] |
| Software stack | [name+version for each dependency: sympy, numpy, matplotlib, etc.] |

## 6. Self-Audit (Universal — Type I Logic Gap only)

| ID | Check | Verdict | Notes |
|----|-------|---------|-------|
| SA-G1 | Does each primary outcome follow from the assumptions + method? | PASS / WEAK / LEAKY | [evidence] |
| SA-G2 | Are there hidden assumptions not stated that are doing the work? | PASS / FAIL | [evidence] |
| SA-G3 | Is any outcome stronger than what the method can deliver? | PASS / FAIL | [evidence] |

**OSS has no Type II pitfall checklist** (main SciForge has 14-class economics / 14-class cs-ml / 10-class physics). Type II is discipline-specific and OSS is discipline-agnostic — the agent's runtime reasoning in `/theory-derivation` handles assumption tracking, not an overlay checklist.

## 7. Approval (Human Checkpoint)

| Field | Value |
|-------|-------|
| Approval timestamp | [ISO 8601] |
| Approver | [user name / role] |
| Approved Section 3 hash | [SHA256] |
| Approval signature | [user-provided] |

**Approval Log**: `methods/APPROVAL_LOG.txt` appends an entry on each approval/re-approval event. Schema:
```
[timestamp] | [approver] | [action: INITIAL_APPROVAL | RE_APPROVAL | DRIFT_DETECTED] | [section_3_hash] | [signature]
```

This is a **forced human checkpoint**. The agent cannot self-approve. The agent cannot proceed to `/theory-derivation` until `APPROVAL_LOG.txt` contains an `INITIAL_APPROVAL` entry matching the current Section 3 hash.

## 8. Update Log

| Date | Change | Reviewer | Hash Drift? |
|------|--------|----------|-------------|
| [date] | Initial registry | [orchestrator] | N/A (initial) |

**Hash drift monitoring**: any Update Log entry that modifies Section 3 MUST:
1. Compute new SHA256 of Section 3
2. Compare against `REGISTRY_HASH.txt`
3. If different → require re-approval (Step 7) before downstream skills can proceed
4. Log drift event in `APPROVAL_LOG.txt` with action `DRIFT_DETECTED`
```

## Workflow

### Step 0: Load DISCIPLINE_CONTEXT

Read `AGENT_DOC.md` for `DISCIPLINE_CONTEXT` block. In OSS, this is **always** `general` (see [`discipline-context.md`](../../shared-references/discipline-context.md)). There is no overlay to load — the universal schema above is the complete template.

### Step 1: Locate Existing Artifacts

Derive sections from existing artifacts:
- `refine-logs/FINAL_PROPOSAL.md` Problem Anchor + Q-id → Section 1
- `refine-logs/IDEA_DAG.json` + `refine-logs/FINAL_PROPOSAL.md` → Section 2 (assumptions), Section 3 (method), Section 4 (outcomes)

If none exist, this is the **first** pre-writing step. Initialize an empty registry with the schema above and ask the user to fill in Sections 2-4, or — if there is enough context — propose a draft for user approval.

### Step 2: Validate Section 2 (Assumptions)

Universal validation:
- Each assumption is formally stated + plain-language
- The falsification signal is concrete (what would invalidate the assumption set)
- No hidden assumptions doing the work that aren't listed

### Step 3: Validate Section 3 (Method Selection) — CRITICAL

This is the pre-registration lock target. Universal validation:
- Apply the Type I Logic Gap self-check (Section 6): does each primary outcome follow from the assumptions + method?
- If any CRITICAL logic gap (LEAKY on a primary outcome) → BLOCK and require method revision before proceeding.

### Step 4: Validate Section 4 (Outcomes)

Universal validation:
- Primary outcomes must be pre-specified (not post-hoc); ≥ 1 primary, ≥ 1 secondary or explicit "none"
- Each outcome has a fidelity target (symbolic / numerical / qualitative)
- The fidelity gate threshold is set (default: numerical)

### Step 5: Validate Section 5 (Reproducibility)

Universal validation:
- `software_stack` is MANDATORY (sympy + numpy + matplotlib versions, at minimum)
- `parameter_availability` is MANDATORY (values, ranges, access conditions)
- `seed_strategy` is MANDATORY if numerical sanity checks are planned

### Step 6: Self-Audit (Section 6)

Run the universal Type I Logic Gap self-check (SA-G1 / SA-G2 / SA-G3). Record findings in Section 6 with severity (CRITICAL/MAJOR/MINOR).

### Step 7: Approval Checkpoint (FORCED HUMAN)

**This step cannot be skipped or self-approved by the agent.**
1. Present the completed registry to the user
2. Compute `SHA256(Section 3 text)` → write to `methods/REGISTRY_HASH.txt`
3. Ask user to explicitly approve: "Do you approve this method registry? Section 3 will be locked."
4. On approval: append entry to `methods/APPROVAL_LOG.txt` with `action=INITIAL_APPROVAL`
5. Without approval: registry is `DRAFT`, downstream skills MUST reject

### Step 8: Derive METHOD_BINDING.md

Extract Section 3 into `methods/METHOD_BINDING.md`:
```markdown
# METHOD_BINDING.md

**Source**: METHOD_REGISTRY.md Section 3
**Hash**: [SHA256 of Section 3]
**Status**: LOCKED

## Binding
[Section 3 content verbatim]

## Callback Protocol
If `/leakage-audit` finds CRITICAL Type I leakage AND this binding is identifiable,
the orchestrator re-invokes `/method-registry --callback audit_report/LEAKAGE_AUDIT.json`
to revise Section 3. Bounded to 3 iterations.
```

### Step 9: Extract OUTCOME_CLASSIFICATION.md

Extract Section 4 into `methods/OUTCOME_CLASSIFICATION.md`:
```markdown
# OUTCOME_CLASSIFICATION.md

**Source**: METHOD_REGISTRY.md Section 4
**Extracted**: [date]

## Primary Outcomes
[list, with fidelity targets]

## Secondary Outcomes
[list, with fidelity targets]

## Fidelity Gate (universal)
claim supported if ≥ 1 primary outcome reaches the configured fidelity threshold (default: numerical).
```

### Step 10: Persist & Link

Write `methods/METHOD_REGISTRY.md`. Update `AGENT_DOC.md` with registry pointer. Write `methods/REGISTRY_HASH.txt`, `methods/APPROVAL_LOG.txt`, `methods/METHOD_BINDING.md`, `methods/OUTCOME_CLASSIFICATION.md`.

### Step 11: Notify Downstream

- `/theory-derivation` → must read `METHOD_REGISTRY.md` + `METHOD_BINDING.md` to execute the derivation
- `/leakage-audit` → must read `METHOD_REGISTRY.md` + `METHOD_BINDING.md` to audit
- `/result-to-claim` → must read `OUTCOME_CLASSIFICATION.md` to gate claims
- `/invariant-check` → verifies `REGISTRY_HASH.txt` matches Section 3 (the pre-paper-writing gate)

## Hash Lock Mechanism

The hash lock is the cryptographic pre-registration. Once `REGISTRY_HASH.txt` is written:
1. Any modification to Section 3 changes its SHA256
2. `/invariant-check` (the pre-paper-writing gate) detects the mismatch
3. Downstream skills BLOCK until re-approval

**Re-approval flow** (when Section 3 must change):
1. Agent detects need for method revision (e.g., `/leakage-audit` callback)
2. Agent modifies Section 3
3. Agent computes new SHA256
4. Agent detects drift vs `REGISTRY_HASH.txt`
5. Agent logs `DRIFT_DETECTED` in `APPROVAL_LOG.txt`
6. Agent presents drift to user: "Section 3 changed from [old hash] to [new hash]. Reason: [leakage callback]. Re-approve?"
7. On re-approval: append `RE_APPROVAL` entry to `APPROVAL_LOG.txt`, update `REGISTRY_HASH.txt`

## 6-State Verdict Schema

This skill uses the 6-state machine defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md):

| State | Meaning | When this skill emits it |
|-------|---------|--------------------------|
| `PASS` | Registry valid, approved, hash locked | Step 7 approval complete |
| `WARN` | Registry valid but with minor logic gap findings | Section 6 has WEAK (not LEAKY) findings |
| `FAIL` | Registry has CRITICAL logic gap | Section 3 validation found LEAKY on a primary outcome |
| `NOT_APPLICABLE` | (reserved — OSS always requires this skill) | never emitted in OSS |
| `BLOCKED` | Prerequisite missing (no Problem Anchor, no FINAL_PROPOSAL) | Step 1 inputs missing |
| `ERROR` | Skill itself failed | Internal error |

## Bounded 3-Round Callback Protocol

When `/leakage-audit` finds CRITICAL Type I leakage (LEAKY on a primary outcome) and `METHOD_BINDING.md` is identifiable, the callback fires:
1. `/leakage-audit` emits `callback` field in `LEAKAGE_AUDIT.json`
2. Orchestrator re-invokes `/method-registry --callback audit_report/LEAKAGE_AUDIT.json`
3. `/method-registry` revises Section 3 → emits `METHOD_BINDING_DIFF.md`
4. Orchestrator re-invokes `/leakage-audit` to confirm the fix
5. If same logic gap persists → repeat (up to 3 iterations)
6. **If 3 iterations exhausted on the same logic gap → orchestrator halts with fallback**:
   - Downgrade `METHOD_BINDING.md` status to `DRAFT`
   - Append `LOGIC_GAP_FUNDAMENTAL_ISSUE` flag to `METHOD_BINDING.md`
   - Log halt event in `APPROVAL_LOG.txt` with `action=CALLBACK_EXHAUSTED`
   - Report to user: "The logic gap is fundamental — the implication cannot be defended under the current assumptions. Recommend returning to `/idea-discovery` to select a different approach to the problem."
   - **Do NOT silently continue** — a logic gap surviving 3 method swaps indicates the approach itself is flawed, not a method selection problem.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **No silent edits after approval.** Section 3 is hash-locked. Any change requires re-approval.
- **Forced human checkpoint.** The agent cannot self-approve. `APPROVAL_LOG.txt` must contain a user `INITIAL_APPROVAL` entry before downstream skills proceed.
- **3-round callback limit.** Do not exceed 3 method revisions for the same logic gap. If exhausted, halt and report.
- **No discipline overlays.** OSS has no `overlays/{economics,cs-ml,physics}.md`. Do not reintroduce discipline-specific Section 2 schema (AIM T/I/P, SOTA baseline/target, PNV Physical assumptions) or Section 6 pitfall checklists (14-class econ, 14-class cs-ml, 10-class physics). The universal schema above is the complete template. If a problem seems to need a discipline-specific check, the agent's runtime reasoning in `/theory-derivation` handles it, NOT an overlay.
- **This skill is structural, not substantive.** It cannot replace subject-matter expertise. The Type I self-check catches canonical logic gaps, not novel methodological flaws.

## Output Shape

The final output is:
1. `methods/METHOD_REGISTRY.md` — the 8-section universal registry
2. `methods/REGISTRY_HASH.txt` — SHA256 of Section 3
3. `methods/APPROVAL_LOG.txt` — human-checkpoint log
4. `methods/METHOD_BINDING.md` — derived from Section 3, consumed by `/theory-derivation` and `/leakage-audit`
5. `methods/OUTCOME_CLASSIFICATION.md` — extracted from Section 4, consumed by `/result-to-claim` and `/invariant-check`

## Composing With Other Skills

```
/auto-pipeline (Phase 1: Problem understanding, Q-id freeze)
    → /method-registry                   ← you are here (Phase 5)
        → /theory-derivation (executes METHOD_BINDING)
        → /leakage-audit (audits the registry)
        → /result-to-claim (gates on OUTCOME_CLASSIFICATION + 3-fidelity ladder)
        → /auto-review-loop (cross-model review)
        → /paper-writing (unified elsarticle template)
```

This skill is the **entry point** for the pre-writing boundary. Without it, no downstream skill can be trusted.

## See Also

- [`../leakage-audit/SKILL.md`](../leakage-audit/SKILL.md) — audits the registry this skill produces (Type I + Type IV universal)
- [`../invariant-check/SKILL.md`](../invariant-check/SKILL.md) — verifies hash lock + INV-G1 problem anchor freeze
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — 3-fidelity claim gate
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md) — 6-state verdict schema
- [`../shared-references/venue-profiles.md`](../../shared-references/venue-profiles.md) — OSS unified elsarticle template spec
