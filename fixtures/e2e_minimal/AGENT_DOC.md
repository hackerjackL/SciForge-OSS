# AGENT_DOC.md — Q001 (e2e minimal fixture)

Produced at `/auto-pipeline` Phase 0 for the minimal e2e smoke run
(see `PROBLEM.md` in this directory for the frozen problem statement).
Per `artifact-registry.md`, this file is re-read at every phase entry to
confirm the configuration is intact; required fields are `discipline`,
`venue`, `methodology_class`.

## DISCIPLINE_CONTEXT

```yaml
DISCIPLINE_CONTEXT:
  discipline: general      # OSS is discipline-agnostic; always 'general'
  sub_discipline: null     # not used in OSS
  target_venue: null       # unified elsarticle preprint, no venue targeting
```

## Configuration

| Field | Value | Source of contract |
|---|---|---|
| discipline | general | `discipline-context.md` (OSS single-row contract) |
| venue | n/a-test | fixture run; no real venue |
| methodology_class | empirical-simulation | Monte Carlo estimation on synthetic Gaussian data |
| verification_type | hybrid | analytic ground truth + executable simulation (`verification-routing.md`) |
| effort | lite | `effort-contract.md` (implies assurance: draft) |
| language | english | `output-language.md` default |

## Gates

Default gates — no overrides for this fixture:

- forced human checkpoints at Phase 3→4 and Phase 5→6: enabled
  (no `test_mode`, no `human_skip`)
- toy gate (Phase 6b): `RESULT.json` must carry `status: PASS` and
  `core_claim_validated: true`
- bounded fallback: 3 rounds per failure type, then BLOCKED
- background dispatch mandatory for full experiments > 5 min
- paper-compile: zero warnings / zero errors

## Pipeline Status

language: english
problem_id: Q001
status: fixture (synthetic smoke run — not a real research problem)
