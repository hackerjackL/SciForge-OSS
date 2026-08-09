# Pipeline Integrity Check (SciForge-OSS)

> **Status**: Mandatory pre-phase check that verifies the pipeline is intact before each phase executes. This prevents pipeline breaks by catching issues before they cascade.
>
> **Core principle**: Every phase checks its prerequisites BEFORE executing. If prerequisites are missing, the phase applies the graceful degradation protocol (MUST/OPTIONAL/CONDITIONAL).

## The Integrity Check Protocol

Every phase MUST execute this check before starting its main workflow:

### Step 1: Prerequisite Verification

```
For each prerequisite of this phase:
  Check if the prerequisite file exists at its expected path
  If EXISTS → PASS
  If NOT EXISTS → check the phase mode
    If MUST → BLOCKED (prerequisite missing)
    If OPTIONAL → skip with WARN
    If CONDITIONAL → check condition; if not met, skip with WARN
```

### Step 2: Domain Signature Verification

```
If the phase consumes domain signature:
  Check if .sciforge/refine-logs/domain-signature.json exists
  If EXISTS → PASS (signature is available)
  If NOT EXISTS → log WARN, use defaults, continue
```

### Step 3: Phase Mode Enforcement

```
Check the phase's mode:
  If MUST  → Phase must execute. If it fails after 3 rounds, BLOCKED.
  If OPTIONAL → Phase can be skipped. If skipped, log WARN.
  If CONDITIONAL → Check condition. If not met, skip with WARN.
```

### Step 4: Pre-Flight Log

```
Write to .sciforge/refine-logs/pipeline-integrity.md:
  - Phase number
  - Phase name
  - Prerequisites status (PASS/FAIL/BLOCKED)
  - Domain signature status (FOUND/NOT_FOUND)
  - Phase mode (MUST/OPTIONAL/CONDITIONAL)
  - Execution decision (EXECUTE/SKIP/BLOCKED)
```

## Phase-Specific Prerequisites

| Phase | Prerequisites | Mode | If Missing |
|-------|-------------|------|-----------|
| 0: load-problem | Human prompt (Q-id) | MUST | Request user input |
| 1: problem-understanding | Q-id is frozen | MUST | Fall back to Phase 0 |
| 1a: domain-signature | Phase 1 complete | MUST | Fall back to Phase 1 |
| 2: idea-discovery | domain-signature.json | MUST | Use default configuration |
| 2.5: adversarial-falsification | IDEA_CANDIDATES.md | MUST | Fall back to Phase 2 |
| 3: novelty-check | IDEA_DAG.json | MUST | Fall back to Phase 2.5 |
| 4: universal-retrieval | Final idea selected | MUST | Wait for human approval |
| 5: method-registry | Literature complete | MUST | Fall back to Phase 4 |
| 6: theory-derivation | METHOD_REGISTRY.md | MUST | Fall back to Phase 5 |
| 7: leakage-audit | derivations/{problem_id}/ | MUST | Fall back to Phase 6 |
| 8: logic-verification | derivations/{problem_id}/ | MUST | Fall back to Phase 6 |
| 9: invariant-check | .sciforge/verdicts/LEAKAGE_AUDIT.json | MUST | Fall back to Phase 7 |
| 10: result-to-claim | LOGIC_VERIFICATION.json | MUST | Fall back to Phase 8 |
| 11: unified-plotting | CLAIMS_FROM_RESULTS.md | OPTIONAL | Skip |
| 12: paper-writing | CLAIMS_FROM_RESULTS.md | MUST | Fall back to Phase 10 |
| 13: paper-compile | paper/main.tex | CONDITIONAL | WARN, degradable |
| 14: auto-review-loop | paper/main.pdf | OPTIONAL | Substitute with grounding-check |
| 15: citation-audit | paper/main.tex | MUST | Fall back to Phase 12 |
| 16: final-assembly | All artifacts | MUST | Fall back to the relevant phase |

## Integrity Check Log Format

```markdown
# Pipeline Integrity Check — Phase 2

**Timestamp**: 2026-07-21 10:00:00
**Phase**: 2 — idea-discovery
**Mode**: MUST

## Prerequisites
- [PASS] .sciforge/refine-logs/domain-signature.json exists
- [PASS] Q-id is frozen
- [INFO] Domain signature: evidence_type=causal_inference

## Domain Signature
- [FOUND] .sciforge/refine-logs/domain-signature.json
- Applied: perspective_weights = {theoretical: 0.3, computational: 0.5, qualitative: 0.2}

## Decision
- [EXECUTE] Proceeding with Phase 2
```

## Failure Recovery

### MUST Phase Fails
```
1st attempt: Apply standard fix
2nd attempt: Escalate fix approach
3rd attempt: BLOCKED → surface to human
```

### OPTIONAL Phase Fails
```
Log WARN with reason_code
Skip to next phase
Continue pipeline
```

### CONDITIONAL Phase Fails
```
Check condition
If condition not met: skip with WARN
If condition met but execution fails: apply MUST rules
```

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — graceful degradation protocol
- [`startup-protocol.md`](startup-protocol.md) — mandatory startup protocol
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — domain signature consumption