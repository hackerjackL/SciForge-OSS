# Self-Review Independence Protocol (SciForge-OSS)

> **OSS uses structured self-review; agents achieve adversarial review through role switching.**
> This file defines the "independence" principle in self-review — ensuring that the same agent can effectively challenge its own work after switching roles.

## Core Principles

1. **Re-read, don't recall** — after each role switch, the agent must re-read the artifacts from files; it must not rely on in-memory recall
2. **Structured checklists** — reviews use predefined checklists, not a free-form "just review it"
3. **Full preservation of the review trail** — review outputs are preserved in full in `review-stage/`; deletion or alteration is prohibited
4. **Role isolation** — the reviewer role cannot access the researcher role's reasoning process; it can only see the final artifact files

## What the Reviewer MAY Access

- Artifact file paths (derivation outputs, claims files, verification reports, paper drafts)
- Review objectives ("assess publishability", "check derivation correctness")
- Structural metadata ("the paper has 8 sections", "derivations are in the derivations/ directory")
- Domain constraints ("target journal tier")

## What the Reviewer MUST NOT Access

- The researcher role's reasoning process or intermediate thinking
- Prior review comments or fix records (fresh review)
- The researcher's summaries or explanations of the content (files must be read directly)

## Implementation

- Role switching is managed by `/auto-review-loop`
- Checklists are defined by each skill (the 20-category question system of `/logic-verification`)
- The review trail is saved in the `review-stage/` directory

## See Also

- [`reviewer-routing.md`](reviewer-routing.md) — the role-switching contract
- [`../support/auto-review-loop/SKILL.md`](../support/auto-review-loop/SKILL.md) — the self-review loop
- [`review-tracing.md`](review-tracing.md) — review-trail tracing
