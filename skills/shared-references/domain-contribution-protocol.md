# Domain Contribution Protocol (SciForge-OSS — community domain signature PR channel)

> **Status (v2.8 — long-term L1)**: Defines the **open contribution channel** for community-submitted domain signatures. When `/domain-learner` (Phase 1b) encounters an `evidence_type` not covered by the v2.8 adaptive matrices ([`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) M1, [`pipeline-adaptive-degradation.md`](pipeline-adaptive-degradation.md) M3), the orchestrator flags `unknown_evidence_type` and the run falls back to v2.7 defaults. This file is the contract for how a community contributor turns that unknown type into a first-class supported signature via PR — without requiring OSS core team review for every domain.
>
> **Core principle**: OSS is discipline-agnostic by design; the adaptive matrices cover a small finite alphabet of evidence_types. But research domains evolve — a novel methodological tradition (e.g., network science c. 2000, synthetic biology c. 2010) may not fit existing evidence_types cleanly. The contribution protocol lets the community propose new evidence_type rows via versioned PR, with a bounded review contract — not ad-hoc patches.

## Quick Reference

- **Purpose**: 开放领域签名 PR 通道，把 unknown_evidence_type 转为 first-class 支持签名
- **Input**: community PR proposing new `evidence_type` + matrix rows + worked example
- **Output**: merged PR → adaptive matrices extended; v2.8 schema_version bump
- **Invocation**: contributor submits PR per this protocol; OSS core team reviews against the merge contract
- **Key**: 不是任意领域加 row；schema_version 必须 bump；worked example + falsification test 是硬约束

## When to Contribute

A contributor should open a PR via this protocol when ALL of the following hold:

1. **The learner flagged `unknown_evidence_type`** on a real 125-problem run — the contribution is grounded in observed pipeline failure, not hypothetical domain addition.
2. **The new evidence_type does NOT collapse into an existing type** — the contributor tried mapping the new domain to each existing type (`derivational` / `correlational` / `causal_inference` / `experimental` / `simulational` / `interpretive`) and can document why none fit (e.g., "synthetic biology's `design-build-test` cycle is not `experimental` because the truth standard is functional implementation, not reproducible measurement — that is `design` paradigm but OSS has no `design_evidence_type` row yet").
3. **The contributor has a worked example** — a complete pipeline run on a representative problem of the new domain, with artifacts, demonstrating the adaptive matrices' proposed rows produce sensible behavior.

If only #1 holds (unknown type flagged) but #2 fails (the domain fits an existing type with minor override), the contribution is a **case-by-case override** not a new evidence_type — see § Case-by-case Overrides below.

## PR Contract

A contribution PR MUST contain the following artifacts, in this order:

### 1. `domain-signature-spec.md` (problem grounding)

```markdown
# Proposed evidence_type: `<name>` (e.g., `design`)

## Problem grounding
- Representative problem: Q-id + description
- TDAL verdict on the run that flagged `unknown_evidence_type`: [verdict + weakest dimension]
- Why the unknown_evidence_type fallback (v2.7 defaults) failed this problem: [specific failure]

## Why no existing evidence_type fits
- derivational: [why not — truth standard mismatch?]
- correlational: [why not]
- causal_inference: [why not]
- experimental: [why not]
- simulational: [why not]
- interpretive: [why not]

## Proposed evidence_type definition
- Truth standard: [proof / reproducible measurement / functional implementation / explanatory coherence / ...]
- Verification method: [theorem / statistical test / benchmark / hermeneutic / ...]
- Output format: [theorem-proof / hypothesis-method-results / design-implementation-evaluation / ...]
- Example domains: [list 3-5 subfields that fit this evidence_type]
```

### 2. `adaptive-matrix-rows.md` (matrix extensions)

Proposed additions to the three adaptive matrices:

```markdown
## M1 intensity rows (domain-adaptive-pipeline.md)

### Phase 5 — /method-registry intensity
| evidence_type | paradigm | intensity | emphasis | budget | human checkpoint |
|--------------|----------|-----------|----------|--------|------------------|
| `<name>` | `<paradigm>` | REDUCED/STANDARD/INTENSIFIED | ... | ... | ... |

### Phase 6 — /theory-derivation intensity
| evidence_type | paradigm | intensity | engine | verification strictness | output mark |
|--------------|----------|-----------|--------|-------------------------|-------------|
| `<name>` | `<paradigm>` | ... | ... | ... | ... |

### Phase 11 — /unified-plotting intensity
| evidence_type | paradigm | intensity | figure types | color compliance | data heatmap |
|--------------|----------|-----------|--------------|------------------|--------------|
| `<name>` | `<paradigm>` | ... | ... | ... | ... |

## M3 mode rows (pipeline-adaptive-degradation.md)

### `<name>` problems
| Phase | v2.8 mode | Rationale |
|-------|-----------|-----------|
| 0 | MUST (invariant) | ... |
| ... | ... | ... |

### Mixed-domain rule for `<name>`
[How `<name>` combines with other evidence_types — most stringent wins per M3]
```

### 3. `falsification-test.md` (anti-inflation)

The contributor MUST run the proposed matrix rows against a **falsification test set** — 3 problems of the new domain that the proposal should handle correctly, AND 3 problems of EXISTING domains that the proposal must NOT break:

```markdown
## Falsification test set

### New-domain problems (should pass with proposed rows)
1. [Q-id + description] → expected TDAL verdict + expected weakest_dimension
2. [Q-id + description] → ...
3. [Q-id + description] → ...

### Existing-domain regression problems (should NOT change verdict)
1. [Q-id from existing evidence_type] → expected v2.8 verdict (unchanged)
2. [Q-id from existing evidence_type] → ...
3. [Q-id from existing evidence_type] → ...

## Test results
[Run the pipeline on each; paste the TDAL verdict + weakest_dimension from each run]

## Regression check
[Confirm the 3 existing-domain problems produce IDENTICAL verdicts to current main branch]
```

**Hard gate**: if ANY existing-domain regression problem changes verdict, the PR is REJECTED — the contribution must not perturb established behavior.

### 4. `domain-learner-prompt.md` (learner integration)

The contributor MUST provide a learner prompt addition so `/domain-learner` (Phase 1b) can recognize the new evidence_type from literature:

```markdown
## Learner prompt addition

When the learner searches literature and detects the following signals:
- [list of method keywords, e.g., "design-build-test", "biofabrication", "genetic circuit"]
- [list of verification keywords, e.g., "functional validation", "benchmark evaluation"]
- [list of output keywords, e.g., "prototype", "implementation"]

Then classify `evidence_type: <name>` with confidence ≥ 0.7.

If confidence < 0.7 OR signals ambiguous with existing type, fall back to the closest existing type:
- closest: [which existing type, e.g., experimental]
- fallback rationale: [why this is the safe fallback]
```

## Review Contract (OSS core team)

The OSS core team reviews the PR against this contract:

| Check | Pass criterion | Fail action |
|-------|----------------|-------------|
| Problem grounding | Real `unknown_evidence_type` flag from a documented run | Request the run artifacts |
| No-collapse test | §2 of spec convincingly rejects all 6 existing types | Reject — use case-by-case override instead |
| Matrix rows complete | All 3 M1 tables + M3 row + mixed-domain rule present | Request missing rows |
| Falsification test | 3 new-domain pass + 3 existing-domain unchanged | Reject — proposal perturbs established behavior |
| Learner prompt | Recognition signals + safe fallback specified | Request prompt addition |
| schema_version bump | PR bumps `schema_version: "1.x"` → `"1.(x+1)"` in all touched matrices | Request version bump |

**Review SLA**: core team responds within 14 days. Three outcomes:
- **MERGE**: contract satisfied, schema_version bumped, matrices extended
- **REVISE**: specific checks failed, contributor revises within 30 days or PR closes
- **REJECT**: fundamental collapse (proposal does fit existing type) or regression failure — close PR, suggest case-by-case override

## Case-by-case Overrides (lighter-weight than new evidence_type)

If §2 of the spec fails — the domain DOES fit an existing type but needs a per-domain override — the contributor opens a smaller PR:

```markdown
# Case-by-case override for `<domain>` (fits evidence_type `<existing>`)

## Override
- evidence_type: <existing>
- domain-specific Phase 5/6/11 emphasis: [e.g., "for synthetic biology, Phase 6 emphasis = biofabrication protocol"]
- domain-specific failure modes: [list]
- learner prompt addition: [recognize "synthetic biology" signals → set evidence_type=experimental + domain_label=synbio]

## Falsification
- 3 synthetic-biology problems → expected verdict + weakest
- 3 existing experimental problems → unchanged verdict
```

Case-by-case overrides do NOT bump schema_version — they extend the learner's prompt and add domain-specific emphasis entries, not new evidence_type rows. Lighter review: core team checks the falsification test only.

## Boundaries

- **Never contribute a new evidence_type without a real `unknown_evidence_type` flag.** Hypothetical additions ("I think field X might be a new type") are rejected — the contribution is grounded in observed pipeline failure.
- **Never contribute without the falsification test.** The 3+3 test set is non-negotiable — it is the anti-inflation gate on the contribution itself.
- **Never break existing-domain regression.** A contribution that improves new-domain handling but perturbs established domains is REJECTED, not conditionally merged.
- **Never bump schema_version without core team review.** The version bump is the audit trail; sidestepping it via direct matrix edit is a rejectable offense.
- **Case-by-case overrides are preferred when possible.** Only genuinely novel truth standards warrant a new evidence_type; most "new domains" are existing types with domain-specific emphasis.
- **The learner prompt addition is mandatory.** A new evidence_type the learner cannot recognize is dead weight — the contribution must include the learner's recognition logic.

## Why this is "open" contribution

The protocol is **open** in three senses:

1. **Transparent review contract** — the 6-check review table is public; contributors know exactly what will be checked. No opaque "core team vibes."
2. **Bounded SLA** — 14-day response, 30-day revise window. Contributors are not left waiting indefinitely.
3. **Lighter case-by-case path** — most contributions are case-by-case overrides (faster review, no schema bump), reserving the new-evidence_type path for genuinely novel truth standards.

The protocol is **closed** in the sense that contributions cannot bypass the contract — no direct matrix edits, no schema bumps without review, no regression breaks. This is the balance: open contribution channel, closed quality gate.

## See Also

- [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) — M1 intensity matrix (contribution target)
- [`pipeline-adaptive-degradation.md`](pipeline-adaptive-degradation.md) — M3 mode matrix (contribution target)
- [`../meta-skills/domain-learner/SKILL.md`](../meta-skills/domain-learner/SKILL.md) — Phase 1b learner (contribution must extend its recognition prompt)
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — how the signature is consumed downstream (contribution must not break consumers)
- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL schema (contribution's falsification test reports TDAL verdicts)
- [`../CONTRIBUTING.md`](../../CONTRIBUTING.md) — repo-wide contribution guide (this file is the domain-specific supplement)
