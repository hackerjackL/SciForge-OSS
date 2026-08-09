# Verdict Schemas (v5.3)

Machine-enforceable field contracts for the machine-readable verdict artifacts that
live flat in each research workspace's `.sciforge/verdicts/` directory (v6.0 home;
pre-v6.0 run directories use `verdicts/` — same layout, reads fall back; directory
layout authoritatively defined in [`../output-protocol.md`](../output-protocol.md)
§Artifact Directory Tree; artifact contracts registered in
[`../artifact-registry.md`](../artifact-registry.md)).

Before this directory existed, every field promise in the skill docs was prose-only:
agents could misspell or omit fields silently. These schemas + the validator make the
promises checkable.

## Schema location convention

- One schema per verdict artifact: `skills/shared-references/schemas/<NAME>.schema.json`,
  where `<NAME>` is exactly the verdict filename without `.json`
  (e.g. `.sciforge/verdicts/REVIEW_STATE.json` → `schemas/REVIEW_STATE.schema.json`).
- All schemas are JSON Schema **draft 2020-12**, but restricted to the subset the
  stdlib validator understands (see below) — do not use `$ref`, `oneOf`, `const`, etc.
- The two hash artifacts are **not JSON** and have no schema file:
  - `PROBLEM_HASH.txt` (invariant-check INV-G1) and `REGISTRY_HASH.txt` (method-registry
    hash lock) are validated by `scripts/validate_verdicts.py` directly as a
    single-line lowercase SHA256 hex string (64 chars, regex `^[0-9a-f]{64}$`).
  - Exception: method-registry §3.5 specifies that when the experiment matrix is
    incomplete the hash-lock refuses and writes `BLOCKED: experiment_matrix_incomplete`
    into `REGISTRY_HASH.txt`; the validator accepts that `BLOCKED: <reason>` form for
    `REGISTRY_HASH.txt` only.

## How `validate_verdicts.py` uses these schemas

```
python3 scripts/validate_verdicts.py <workspace_verdicts_dir> [--strict]
```

- Registered `*.json` files are validated against their `<NAME>.schema.json` plus a
  small set of cross-field post-checks (see below). Exit 0 = all valid, 1 = violations,
  2 = usage error.
- Unknown `*.json` files → **WARN** (unregistered verdict — either register it here or
  remove it). In `--strict` mode WARNs also fail the run (BLOCKED semantics).
- Registered-but-missing files are listed as **pending**, never as errors — verdicts
  appear progressively as the pipeline advances. Exception (v6.0 routing-aware
  expectation): missing files listed in `VERIFICATION_ROUTING.json` `na_verdicts`
  are reported **N/A** (the chosen route legitimately never produces them — e.g. a
  theory-only/humanities run has no experiment verdicts). Declared-N/A files that
  ARE present → WARN (routing/production inconsistency).
- Cross-field invariants enforced beyond the schemas:
  1. Audit-family verdict vocabulary — `PROOF_AUDIT`, `LOGIC_VERIFICATION`,
     `LEAKAGE_AUDIT`, `CITATION_AUDIT`, `KILL_ARGUMENT`, `PAPER_CLAIM_AUDIT`,
     `INVARIANT_CHECK` must carry `verdict` (or `overall_verdict` for
     `INVARIANT_CHECK`) from the 6-state vocabulary
     `PASS | WARN | FAIL | NOT_APPLICABLE | BLOCKED | ERROR`
     (defined in [`../assurance-contract.md`](../assurance-contract.md)).
     This is encoded both in the schemas (enum) and re-checked by the validator.
  2. `audited_input_hashes` — the audit JSONs `PROOF_AUDIT`, `CITATION_AUDIT`,
     `KILL_ARGUMENT`, `LEAKAGE_AUDIT`, `PAPER_CLAIM_AUDIT` must contain
     `audited_input_hashes` (object mapping filename → `sha256:<hex>`),
     per artifact-registry.md schema invariant 2. Encoded in the schemas as
     required + value-pattern.
  3. Budget-floor hard rules (experiment-execution SKILL.md): `budget_floor.satisfied
     == false` forbids `verdict: PASS` (only `IN_PROGRESS` / `BLOCKED` allowed), and
     `verdict: PASS` requires `completion_justification` to be present.

## Supported schema subset

`scripts/validate_verdicts.py` implements a **minimal JSON-Schema validator using only
the Python stdlib** (no `jsonschema` package). Supported keywords:

`type` (object/array/string/integer/number/boolean/null), `required`, `properties`,
`additionalProperties` (boolean or sub-schema), `enum`, `pattern` (regex on strings),
`minimum` / `maximum` (numbers), `items` (applied to every array element).

Annotation keywords are ignored: `$schema`, `$id`, `$comment`, `title`, `description`,
`examples`, `default`. Any **other** keyword (`$ref`, `oneOf`, `anyOf`, `allOf`,
`const`, `format`, `minItems`, `patternProperties`, ...) is reported as an internal
error rather than silently ignored, so schemas never over-promise.

## How to add a new verdict schema

1. Add the fixed filename to the `.sciforge/verdicts/` tree in
   [`../output-protocol.md`](../output-protocol.md) first (that file is the single
   authority for directory layout), then a row in
   [`../artifact-registry.md`](../artifact-registry.md).
2. Create `<NAME>.schema.json` here (draft 2020-12, subset above). Require exactly the
   fields the docs promise; keep the rest permissive (`"additionalProperties": true`).
3. Register the file in `scripts/validate_verdicts.py` (`REGISTRY` dict), including
   `audit_family=True` / `audit_hashes=True` flags when the artifact is an audit
   verdict (6-state vocabulary / `audited_input_hashes`).
4. Check it: `python3 -m json.tool skills/shared-references/schemas/<NAME>.schema.json`
   and run the validator against a fixture workspace.

## Non-verdict schemas in this directory

`RUNSTATE.schema.json` defines the long-horizon resume checkpoint
(`{problem_id}/.sciforge/RUNSTATE.json`). It lives here for discoverability but is
NOT a verdict artifact and NOT validated by `validate_verdicts.py` (which scans only the
verdicts directory); the orchestrator's resume protocol (output-protocol.md
§Long-Horizon Resume Contract) and `tests/test_e2e_smoke.py` check it instead.

## Known gaps (docs vague or conflicting — schemas stay permissive here)

1. **REVIEW_LEDGER shape conflict — closed in v1.3.2.** auto-review-loop SKILL.md
   used to describe a JSONL stream of round entries; artifact-registry.md describes
   a single object with `details.rounds[]`. The SKILL.md Phase E.5 contract now
   matches the registry/schema (single JSON object, round history in
   `details.rounds[]`, per-round union field names, review-loop verdict vocabulary
   `ready`/`almost`/`not_ready` for round entries + 6-state envelope verdict);
   `scripts/verifiers/verify_review_ledger.sh` enforces exactly this (per-round
   vocabulary check; `phase: "finalized"` termination entries carry no
   `action_items`).
2. **BLINDSPOT_CHECK append semantics — closed in v1.3.2.** The doc used to say
   "one per round, appended"; a flat fixed-name file can hold one JSON document.
   auto-review-loop Phase B.2 now states the contract explicitly: overwrite with
   the latest round, per-round history lives in AUTO_REVIEW.md.
3. **LEAKAGE_AUDIT `audited_input_hashes` — closed.** The skill's Step-6 example
   used to omit it; artifact-registry.md invariant 2 requires it for every audit
   JSON and the schema enforces it (registry wins). The e2e fixture carries it.
4. **`thread_id` in audit envelopes.** assurance-contract.md lists it in the minimum
   block, but kill-argument's own example omits it and OSS is single-agent (no external
   reviewer thread). Optional everywhere except `CITATION_AUDIT` (whose emission
   example includes it).
5. **LOGIC_VERIFICATION verdict vocabulary — closed.** The skill's verdict table
   now documents the full 6-state vocabulary explicitly (`NOT_APPLICABLE`
   reserved — OSS always runs logic verification for derivations); the schema
   accepts all six.
6. **BUDGET_FLOOR field names — closed (pinned by fixture).** The e2e fixture
   (fixtures/e2e_minimal/.sciforge/verdicts/BUDGET_FLOOR.json) fixes the canonical
   names: `verdict` + `budget_floor.satisfied` + `budget_floor.checks.{routes_explored,
   matrix_completion, seed_budget, failure_records, remaining_budget_declaration}` +
   `completion_justification[]` ({route, status, evidence}). The schema stays
   permissive (required: `verdict` + `budget_floor.satisfied`); the two hard rules
   are validator post-checks.
7. **REVIEW_STATE verdict spelling — closed.** Both spellings (`not_ready` and
   `not ready`) are accepted in the enum by design; producers are asked to write
   `not_ready`.
8. **PAPER_CLAIM_AUDIT has no explicit example anywhere.** Only the audit verdict,
   `audited_input_hashes`, and the `aigc_scan` field (writing-principles.md §0.5) are
   promised; `aigc_scan`'s internal shape is unconstrained.
9. **VERIFICATION_ROUTING path — closed in v6.0.** verification-routing.md used to
   say `refine-logs/VERIFICATION_ROUTING.json`; the canonical location is
   `verdicts/VERIFICATION_ROUTING.json` since v5.2 (`.sciforge/verdicts/` home since
   v6.0) — verification-routing.md now points at the current canonical path
   (single-authority rule).
10. **PROBLEM_HASH / REGISTRY_HASH are .txt**, so they are regex-checked in the
    validator rather than schema-checked (see top of this file).
11. **RUN_BUDGET.json — closed.** The producer landed (orchestrator Phase 0 init +
    per-boundary booking) and the e2e fixture pins the agreed field list; the schema
    matches it exactly.
12. **EVALUATION_PROTOCOL field names.** method-registry §3.6 documents the
    pre-registration quartet semantically (metrics lock / baseline parity / baseline
    re-implementation / anti-cherry-picking reporting), but no JSON field names are
    fixed. The schema requires only `schema_version` + `generated_at`; enforcement
    happens downstream via `parity_check` / `all_seeds_reported` / `full_grid_reported`
    checks in result-to-claim.
