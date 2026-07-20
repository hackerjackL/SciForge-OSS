---
name: quality-gate
type: reference-skill
role: pre-writing-quality-gate
---

# Quality Gate (SciForge-OSS — Discipline-Agnostic)

> **Status**: Hard gate at the **final pre-writing boundary** — the last checkpoint before paper writing begins. **OSS is discipline-agnostic** — there are no discipline overlays (no economics QF-E*, no cs-ml QF-C*, no physics QF-P*). Only the universal QF-G* quality floor + SD-G* self-deception guard checks are active. Copied from main SciForge and trimmed to OSS's single-row design.

## Use When

Called by the OSS orchestrator (`/125-problems-pipeline`) at the **final pre-writing boundary** — the last checkpoint before `/paper-writing` begins. This is the gate that prevents the pipeline from entering the writing phase when the underlying research is not ready.

This skill is NOT called during earlier phases (those are handled by `/invariant-check`). It is exclusively the pre-writing quality gate.

## Job

Verify three things before paper writing can begin:
1. **Stagnation Gate** — Has the pipeline been stuck in a retry loop? If any phase has been retried beyond its maximum allowed rounds, the pipeline must stop and produce a stagnation report.
2. **Quality Floor Gate** — Does the research meet the universal minimum quality bar? Objective, verifiable criteria only.
3. **Self-Deception Guard** — Is the agent's own quality assessment reliable? Structured self-consistency check of key claims.

This skill is a **hard gate** — if it fails, paper writing is blocked. The agent must either fix the underlying issues or explicitly acknowledge the quality limitations in the paper.

## Core Principle

> The agent's own assessment of its work is the least reliable signal. The quality gate replaces self-assessment with objective, verifiable criteria that the agent cannot fudge.

The invariants checked by `/invariant-check` verify structural integrity (files exist, Q-id anchor frozen, verdicts are valid). The quality gate verifies **research quality** (is this actually good enough to write up?).

## Validation Types

Quality gate checks are classified into two types. The agent must apply the correct type for each check — deterministic where possible, semantic only where necessary.

### Type D: Deterministic (programmable, no LLM discretion)

These checks have clear yes/no answers based on file content, field existence, or numeric thresholds. The agent MUST resolve them deterministically before invoking any LLM reasoning.

| Pattern | Example | Rule |
|---------|---------|------|
| Field existence | "Does `METHOD_REGISTRY.md` Section 3 have a `method` entry?" | Parse file, check field presence |
| File presence | "Does `audit_report/LEAKAGE_AUDIT.json` exist with `verdict: PASS`?" | Check file existence + parse JSON |
| Count comparison | "Are there ≥ 2 primary outcomes with fidelity ≥ numerical?" | Count from CLAIMS_FROM_RESULTS.md |
| Hash match | "Does `REGISTRY_HASH.txt` match Section 3?" | Compute SHA256, compare |

**Rule**: If a check can be answered with a file read + field parse + comparison, it MUST be resolved deterministically. Never invoke LLM reasoning for these.

### Type S: Semantic (LLM-assisted, requires judgment)

These checks require understanding of research context, derivation quality, or interpretation quality. The agent uses LLM reasoning but must ground it in specific evidence.

| Pattern | Example | Constraint |
|---------|---------|------------|
| Claim-evidence match | "Does this claim follow from the derivation?" | Must cite specific result file + line |
| Interpretation quality | "Is the interpretation consistent with assumptions?" | Must reference declared assumptions |
| Scope calibration | "Is claim scope appropriate for evidence scope?" | Must compare claim scope vs. derivation regime |

**Rule**: Semantic checks MUST cite specific evidence locations (file + section/line). Never accept "looks reasonable" as a verdict — require concrete grounding.

### Execution Order

For each quality gate phase, the agent executes Type D checks first, then Type S checks. Type D failures block the gate immediately (no need for LLM reasoning). Type S checks are only evaluated after all Type D checks pass.

## Boundary Declaration

This skill does NOT:
- Assess the quality of the writing itself (that's `/auto-review-loop`)
- Check structural invariants (that's `/invariant-check`)
- Generate new research or derivations
- Make subjective judgments about "interestingness" or "impact"

This skill DOES:
- Check objective quality criteria against the universal floor
- Detect stagnation (retry loops exceeding configurable limits)
- Verify that the agent's quality claims are cross-validated

## Configuration

Read from `AGENT_DOC.md`:

```yaml
QUALITY_GATE:
  enabled: true
  stagnation_tracking: true
  quality_floor: true
  self_deception_guard: true

RETRY_COUNTERS:
  idea_discovery: <int>
  method_registry: <int>
  leakage_audit: <int>
  theory_derivation: <int>
  result_to_claim: <int>

MAX_RETRIES:
  idea_discovery: 3
  method_registry: 3
  leakage_audit: 3
  theory_derivation: 5
  result_to_claim: 3
```

If `QUALITY_GATE.enabled` is false, skip all checks and return PASS. This is the escape hatch for exploration mode.

If any RETRY_COUNTERS field is missing, default to 0.

## Step 0: Load DISCIPLINE_CONTEXT

Read `AGENT_DOC.md` for `DISCIPLINE_CONTEXT` block. In OSS, this is **always** `general` (see [`discipline-context.md`](../shared-references/discipline-context.md)). There is no overlay to load — the universal QF-G* and SD-G* checks are inlined below.

## Phase 1: Stagnation Gate

### Check

For each entry in `MAX_RETRIES`, compare against the corresponding entry in `RETRY_COUNTERS`:
- If `RETRY_COUNTERS[key] > MAX_RETRIES[key]` → **STAGNATED**
- If `RETRY_COUNTERS[key] == MAX_RETRIES[key]` → **WARNING** (one more retry will trigger stagnation)
- If `RETRY_COUNTERS[key] < MAX_RETRIES[key]` → **OK**

### Output

Produce `quality_gate/STAGNATION_REPORT.md`:
```markdown
# Stagnation Report

## Summary
- Phases checked: N
- Stagnated: X
- Warning: Y
- OK: Z

## Stagnated Phases
| Phase | Retries | Max | Status |
|-------|---------|-----|--------|
| theory_derivation | 6 | 5 | STAGNATED — derivation chain cannot be closed after 6 attempts |

## Recommendation
[STOP | CONTINUE_WITH_CAVEAT | CONTINUE]
```

### Gate Behavior
- **Any phase STAGNATED** → Gate = FAIL. Produce stagnation report. Block paper writing. Recommend:
  - **Abandon the direction** — the current approach cannot be rescued after maximum retries. Flag for human review.
- **Any phase WARNING** → Gate = WARN. Proceed but log the warning. The paper must include a limitations section acknowledging the retry history.
- **All phases OK** → Gate = PASS.

## Phase 2: Quality Floor Gate (Universal QF-G*)

OSS has **no discipline overlay**. The universal QF-G* checks below apply to every 125-problem run:

| ID | Criterion | Type | Check | PASS condition |
|----|-----------|------|-------|----------------|
| QF-G1 | Derivation chain exists | D | `results/sympy/` contains ≥ 1 derivation log file | File exists + non-empty |
| QF-G2 | Logic audit PASS | D | `audit_report/LOGIC_VERIFICATION.json` verdict is PASS or WARN | verdict ∈ {PASS, WARN} |
| QF-G3 | Leakage audit PASS | D | `audit_report/LEAKAGE_AUDIT.json` verdict is PASS or WARN | verdict ∈ {PASS, WARN} |
| QF-G4 | Result-to-claim verdict | D | `CLAIMS_FROM_RESULTS.md` exists with `claim_supported: yes` or `partial` | claim_supported ∈ {yes, partial}; NOT `no` |
| QF-G5 | Primary outcome fidelity | D | At least 1 primary outcome at ≥ numerical fidelity (from CLAIMS_FROM_RESULTS.md fidelity gate) | ≥ 1 primary at numerical+ |
| QF-G6 | Problem anchor frozen | D | `refine-logs/FINAL_PROPOSAL.md` exists with frozen Q-id AND referenced in derivation chain | Q-id present in FINAL_PROPOSAL + derivation logs |
| QF-G7 | Method registry hash locked | D | `methods/REGISTRY_HASH.txt` matches `METHOD_REGISTRY.md` Section 3 SHA256 | Hash matches |
| QF-G8 | Interpretation consistency | S | The derivation's interpretation is consistent with the declared assumptions | LLM judgment grounded in specific assumption citations |
| QF-G9 | Scope calibration | S | Claim scope matches derivation regime (no overgeneralization) | LLM judgment comparing claim language vs. derivation regime |

### Check

For each QF-G criterion:
1. Read the required artifact
2. Apply the objective check (Type D first, then Type S)
3. Record verdict: PASS / FAIL / WARN

### Output

Produce `quality_gate/QUALITY_FLOOR_REPORT.md`:
```markdown
# Quality Floor Report (OSS Universal)

## Discipline: general (OSS — no discipline overlay)

## Quality Floor Checks
| ID | Criterion | Verdict | Evidence |
|----|-----------|---------|----------|
| QF-G1 | Derivation chain exists | PASS | results/sympy/derivation_01.log (2.3KB) |
| QF-G2 | Logic audit PASS | PASS | audit_report/LOGIC_VERIFICATION.json verdict=PASS |
| QF-G3 | Leakage audit PASS | WARN | audit_report/LEAKAGE_AUDIT.json verdict=WARN (Type I WEAK on outcome O2) |
| QF-G4 | Result-to-claim verdict | PASS | CLAIMS_FROM_RESULTS.md claim_supported=partial |
| QF-G5 | Primary outcome fidelity | PASS | 2/3 primary outcomes at numerical+ fidelity |
| QF-G6 | Problem anchor frozen | PASS | Q-id SCIMATH-042 in FINAL_PROPOSAL + derivation_01.log |
| QF-G7 | Method registry hash locked | PASS | SHA256 matches |
| QF-G8 | Interpretation consistency | PASS | Derivation interprets within declared compact-operator regime |
| QF-G9 | Scope calibration | WARN | Claim "general convergence" but derivation only for compact operators |

## Summary
- Passed: 7 / 9
- Warned: 2 / 9
- Failed: 0 / 9
- Minimum required: 7 (all QF-G1~G7 must PASS; QF-G8/G9 allow WARN)

## Verdict: WARN (proceed with caveats — QF-G3 + QF-G9 WARN)
```

### Gate Behavior
- **QF-G1~G7 any FAIL** → Gate = FAIL. Block paper writing. List specific failures.
- **QF-G8/G9 WARN only (no FAIL)** → Gate = WARN. Proceed but log the borderline quality. Paper must add a limitations section.
- **All PASS** → Gate = PASS.

## Phase 3: Self-Deception Guard (Universal SD-G*)

This is the most critical phase. The agent may produce results that look good on paper but are actually:
- **Overclaimed**: The claim is stronger than the evidence supports
- **Cherry-picked**: Only favorable results are reported
- **Self-assessed**: The agent reviewed its own work and gave itself a passing grade
- **Scope-inflated**: The derivation only holds in a limited regime but the claim is stated generally

### Mechanism

The self-deception guard uses a **structured self-consistency check** approach:
1. **Extract claims**: Read `CLAIMS_FROM_RESULTS.md` (from `/result-to-claim`) to get the list of claims.
2. **Re-verify evidence**: For each claim, trace back to the raw derivation/verification evidence.
3. **Self-consistency check**: Run a second reasoning pass on the same evidence to verify:
   - Does the evidence actually support the claim?
   - Are there unreported negative results (counterexamples found but not surfaced)?
   - Is the claim scope appropriate (regime qualification)?
   - Is the symbolic proof actually complete, or does it have a hidden gap?

### Universal Checks (OSS — no discipline overlay)

| Guard | Check | Verdict |
|-------|-------|---------|
| SD-G1 | Evidence-to-claim mapping | Each claim has a corresponding evidence entry (derivation step + numerical check) |
| SD-G2 | Negative result disclosure | Unreported counterexamples / divergent regimes are surfaced |
| SD-G3 | Scope calibration | Claim language matches derivation regime (no "general" when derivation is regime-specific) |
| SD-G4 | Symbolic proof completeness | The SymPy chain is actually complete (no hidden "TODO" / "gap" / hand-waved steps) |
| SD-G5 | Numerical sanity independence | The numerical check used parameters independent from the symbolic proof's assumptions (not circular) |

### Output

Produce `quality_gate/SELF_DECEPTION_REPORT.md`:
```markdown
# Self-Deception Guard Report (OSS Universal)

## Claims Analyzed: N

## Claim-by-Claim Verification
| Claim ID | Claim Text | Evidence | Verdict | Issue |
|----------|-----------|----------|---------|-------|
| C1 | "Convergence rate O(1/n) established" | Theorem 1 + sympy/proof_01 | PASS | Full symbolic chain |
| C2 | "Robust across settings" | sandbox/sweep_01 | WARN | Only 2 parameter sets tested, both favorable |
| C3 | "General formula" | qualitative only | FAIL | No symbolic proof, no numerical check — qualitative "looks right" |

## Summary
- Supported: X / N
- Warned: Y / N
- Failed: Z / N

## Overclaim Detected: YES (C3 labeled "formula" without proof)
## Cherry-Picking Detected: NO
## Scope Inflation Detected: YES (C2 "across settings" from 2 favorable tests)

## Verdict: FAIL
```

### Gate Behavior
- **Any FAIL (overclaim, cherry-picking, scope-inflation, incomplete proof)** → Gate = FAIL. Block paper writing. The agent must reframe claims to match evidence.
- **WARN only (minor issues)** → Gate = WARN. Proceed but the paper must add a limitations section addressing the warnings.
- **All PASS** → Gate = PASS.

## Final Verdict

The quality gate produces a single verdict:

```
quality_gate/FINAL_VERDICT.md:
  stagnation: PASS | WARN | FAIL
  quality_floor: PASS | WARN | FAIL
  self_deception: PASS | WARN | FAIL
  overall: PASS | WARN | FAIL | BLOCKED | NOT_APPLICABLE | ERROR
```

### Overall Verdict Rules
- **BLOCKED**: Any FAIL in stagnation or quality_floor → paper writing is blocked.
- **FAIL**: Self-deception FAIL → paper writing is blocked until claims are reframed.
- **WARN**: At least one WARN, no FAIL → paper writing proceeds with caveats logged.
- **PASS**: All checks pass → paper writing proceeds clean.

**NOT_APPLICABLE**: Quality gate disabled (`QUALITY_GATE.enabled=false`). **ERROR**: Internal skill failure (e.g., model unavailable, file parse error, timeout).

## Composing

```
/quality-gate
    ├── Phase 1: Stagnation Detection
    │     └: Reads AGENT_DOC.md RETRY_COUNTERS + MAX_RETRIES
    │     └: Produces STAGNATION_REPORT.md
    ├── Phase 2: Quality Floor (Universal QF-G1~G9)
    │     └: No overlay — checks inlined in this SKILL.md
    │     └: Produces QUALITY_FLOOR_REPORT.md
    └: Phase 3: Self-Deception Guard (Universal SD-G1~G5)
          └: No overlay — checks inlined in this SKILL.md
          └: Structured self-consistency check of claims
          └: Produces SELF_DECEPTION_REPORT.md
```

## Artifacts

| Artifact | Path | Phase |
|----------|------|-------|
| Stagnation Report | `quality_gate/STAGNATION_REPORT.md` | Phase 1 |
| Quality Floor Report | `quality_gate/QUALITY_FLOOR_REPORT.md` | Phase 2 |
| Self-Deception Report | `quality_gate/SELF_DECEPTION_REPORT.md` | Phase 3 |
| Final Verdict | `quality_gate/FINAL_VERDICT.md` | Final |

## Output Protocols

All quality-gate output files must follow the standard output protocols:
- **Versioning**: Follow `../shared-references/output-versioning.md` for timestamped copies of quality gate reports.
- **Manifest**: Log quality gate outputs to `MANIFEST.md` per `../shared-references/output-manifest.md`.
- **Language**: Follow `../shared-references/output-language.md` for output language conventions.

## Boundaries

- **No discipline overlays.** OSS has no `overlays/{economics,cs-ml,physics,general}.md`. Do not reintroduce discipline-specific QF-E*/QF-C*/QF-P* or SD-E*/SD-C*/SD-P* checks — they are discipline-specific and OSS is discipline-agnostic. If a problem seems to need a discipline-specific check, the agent's runtime reasoning handles it, NOT an overlay.
- **Universal QF-G* and SD-G* only.** The 9 quality floor + 5 self-deception checks above are the complete set for every 125-problem run.
- **Hard gate.** If FAIL, paper writing is blocked — no soft passes.
- **Self-consistency check for self-deception.** The self-deception guard MUST use a structured re-verification pass — the agent re-reads claims and evidence from scratch, without relying on memory of having produced them.

## See Also

- [`../shared-references/assurance-contract.md`](../shared-references/assurance-contract.md) — 6-state verdict schema
- [`../shared-references/skill-config.md`](../shared-references/skill-config.md) — RETRY_COUNTERS and MAX_RETRIES config schema
- [`../shared-references/discipline-context.md`](../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../invariant-check/SKILL.md`](../invariant-check/SKILL.md) — structural invariants (INV-G1 problem anchor freeze)
- [`../leakage-audit/SKILL.md`](../leakage-audit/SKILL.md) — Type I logic gap + Type IV escape audit
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — 3-fidelity claim gate
