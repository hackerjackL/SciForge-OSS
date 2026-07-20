# Fantasy Prevention Protocol (SciForge-OSS)

> **Status**: Mandatory protocol that prevents "pure fantasy" — ideas that are theoretically coherent but have no grounding in reality. This is the **most important quality gate** in the entire pipeline.
>
> **Core principle**: Every theoretical claim must be traceable to either (a) a verified derivation, (b) a verified citation, or (c) an explicit assumption with a reasonability score. If none of these hold, the claim is "fantasy" and must be flagged.

## The Fantasy Detection Framework

A claim is classified as **fantasy** if:

1. **No derivation chain** — The claim cannot be traced to a SymPy-verified derivation
2. **No citation support** — The claim is not supported by a verified citation
3. **No explicit assumption** — The claim's assumptions are not listed and scored
4. **No counterexample check** — No one has tried to falsify the claim
5. **No data availability check** — No one has checked if the required data exists

## The 5-Gate Fantasy Prevention System

### Gate 1: Derivation Traceability

```
Check: Can every claim be traced to a SymPy derivation step?
If YES → PASS (derivation traceable)
If NO → Check if the claim has a citation
  If YES → PASS (citation traceable)
  If NO → Check if the claim has an explicit assumption
    If YES → PASS (assumption traceable, but mark as WEAK)
    If NO → FANTASY (no traceability at all)
```

### Gate 2: Citation Verifiability

```
Check: Is every citation backed by a 3-layer verified reference?
If YES → PASS
If NO → FANTASY (citation is fabricated)
```

### Gate 3: Assumption Reasonability

```
Check: Are all assumptions explicitly listed with reasonability scores?
If YES → Check if any fatal assumption has reasonability < 5
  If NO → PASS (assumptions are reasonable)
  If YES → WARN (assumption is weak, but not fantasy)
If NO → FANTASY (assumptions are hidden)
```

### Gate 4: Falsifiability

```
Check: Has someone tried to falsify this claim?
If YES → Check if the falsification attempt was honest
  If YES → PASS (claim is falsifiable)
  If NO → WARN (falsification was superficial)
If NO → WARN (claim has not been stress-tested)
```

### Gate 5: Data Availability

```
Check: Does the required data exist?
If YES → PASS (data exists)
If PARTIAL → WARN (some data may be unavailable)
If NO → FANTASY (claim requires data that doesn't exist)
```

## Fantasy Verdict

| Gates Passed | Verdict | Action |
|-------------|---------|--------|
| 5/5 | GROUNDED | Proceed to paper writing |
| 4/5 | MOSTLY GROUNDED | Proceed with caveats |
| 3/5 | WEAKLY GROUNDED | Must strengthen before paper writing |
| 2/5 | MOSTLY FANTASY | Block paper writing |
| 0-1/5 | FANTASY | Reject immediately |

## Implementation

### In /adversarial-falsification

The 5 gates are checked during the falsification phase:

```
Gate 1: Phase 1 (Assumption Attack) → Assumption Reasonability
Gate 2: Phase 3 (Literature Adversarial Search) → Citation Verifiability
Gate 3: Phase 1 (Assumption Attack) → Assumption Listing
Gate 4: Phase 2 (Counterexample Construction) → Falsifiability
Gate 5: Phase 6 (Data Availability Check) → Data Availability
```

### In /result-to-claim

The fantasy verdict is included in the confidence assessment:

```json
{
  "fantasy_prevention": {
    "gates_passed": 4,
    "total_gates": 5,
    "verdict": "MOSTLY_GROUNDED",
    "failed_gates": ["Gate 3: Assumption Reasonability"],
    "recommendation": "Strengthen assumption A2 before paper writing"
  }
}
```

### In /paper-writing

Before writing, the fantasy verdict is checked:

```
If verdict = FANTASY or MOSTLY_FANTASY:
  BLOCK paper writing
  Return to adversarial-falsification for strengthening
If verdict = WEAKLY_GROUNDED:
  Allow paper writing, but MUST include "Limitations" section
  discussing the weak assumptions
If verdict = GROUNDED or MOSTLY_GROUNDED:
  Proceed to paper writing normally
```

## The "Fantasy Log"

Every time a claim is flagged as fantasy, write to `refine-logs/fantasy-log.md`:

```markdown
## Fantasy Entry — 2026-07-21 10:00:00

**Claim**: "The algorithm converges in O(log n) steps"
**Phase**: 6 (theory-derivation)
**Gate Failed**: Gate 1 (Derivation Traceability)
**Reason**: No SymPy derivation chain for the convergence claim
**Action**: Derivation attempted but failed. Claim marked as conjecture.
**Status**: WEAKLY_GROUNDED — allowed in paper as "conjecture" only
```

## Boundaries

- **Fantasy is not the same as wrong.** A claim can be fantasy even if it's true (no evidence) or grounded even if it's false (evidence exists but is wrong).
- **The goal is not to eliminate fantasy, but to label it.** A labeled conjecture is valuable; an unlabeled one is dangerous.
- **Fantasy prevention applies to ALL domains.** A mathematical proof without a derivation chain is fantasy. An economics claim without data is fantasy. A medical claim without a trial is fantasy.
- **The fantasy verdict is a spectrum, not binary.** GROUNDED → MOSTLY_GROUNDED → WEAKLY_GROUNDED → MOSTLY_FANTASY → FANTASY.

## See Also

- [`../support/adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — executes the 5 gates
- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — includes fantasy verdict in confidence assessment
- [`../support/paper-writing/SKILL.md`](../support/paper-writing/SKILL.md) — checks fantasy verdict before writing
- [`grounding-check.md`](grounding-check.md) — complementary grounding checklist