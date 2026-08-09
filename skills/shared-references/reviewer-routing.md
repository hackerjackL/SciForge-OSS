# Self-Review Role Switching (SciForge-OSS)

> **OSS uses Structured Self-Review, not cross-model review.**
> The same agent achieves adversarial review through role switching ("Researcher" → "Reviewer" → "Adjudicator").
> This file defines the role-switching contract.

## Core Principles

1. **Role switching is mandatory** — the agent must switch roles explicitly; it cannot "be both player and referee"
2. **Re-read the artifacts** — after each role switch, the agent must re-read the artifact files; it must not rely on memory
3. **Structured checklists** — reviews use structured checklists, not a free-form "just review it"
4. **Review-trail preservation** — the output of each review is preserved in full in the `review-stage/` directory

## Role Definitions

| Role | Responsibility | Output |
|------|----------------|--------|
| **Researcher** | Produces research artifacts (derivations, verifications, papers) | Research artifact files |
| **Reviewer** | Re-reads the artifacts from an adversarial stance and checks them item by item | Review report + scores |
| **Defender** | Rebuts or accepts the review comments | Defense comments |
| **Adjudicator** | Adjudicates the defense and updates the scores | Final adjudication + action items |

## Role-Switching Flow

```
Researcher → produces artifacts
    ↓
Reviewer → re-reads artifacts → outputs the review report
    ↓
Defender → responds to review comments → outputs the defense
    ↓
Adjudicator → adjudicates the defense → updates the scores
    ↓
Researcher → applies fixes per the adjudication → enters the next round
```

## Integration with OSS

- Role switching is managed by `/auto-review-loop`
- Review checklists are defined by the corresponding skills (`/logic-verification`, `/quality-gate`)
- All review outputs are saved in the `review-stage/` directory
- See also [`/auto-review-loop`](../support/auto-review-loop/SKILL.md)
