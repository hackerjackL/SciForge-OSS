# Verdict Schemas (v5.3)

Machine-enforceable field contracts for the machine-readable verdict artifacts that
live flat in each research workspace's `verdicts/` directory (directory layout
authoritatively defined in [`../output-protocol.md`](../output-protocol.md) §Artifact Directory Tree;
artifact contracts registered in [`../artifact-registry.md`](../artifact-registry.md)).

Before this directory existed, every field promise in the skill docs was prose-only:
agents could misspell or omit fields silently. These schemas + the validator make the
promises checkable.

## Schema location convention

- One schema per verdict artifact: `skills/shared-references/schemas/<NAME>.schema.json`,
  where `<NAME>` is exactly the verdict filename without `.json`
  (e.g. `verdicts/REVIEW_STATE.json` → `schemas/REVIEW_STATE.schema.json`).
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
  appear progressively as the pipeline advances.
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

1. Add the fixed filename to the `verdicts/` tree in
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

## Known gaps (docs vague or conflicting — schemas stay permissive here)

1. **REVIEW_LEDGER shape conflict.** auto-review-loop SKILL.md describes a JSONL
   stream of round entries; artifact-registry.md describes a single object with
   `details.rounds[]`. A `.json` file must be parseable JSON, so the schema follows
   the registry (object form) — JSONL output will fail validation. Per-round field
   names also differ between the two docs (`statistical_gate`/`action_items`/
   `debate_rulings` vs `fidelity_delta`/`key_criticisms`/`actions_taken`); the schema
   accepts the union, requiring only `round`/`score`/`verdict`/`phase`.
2. **BLINDSPOT_CHECK append semantics.** The doc says "one per round, appended", but a
   flat fixed-name file can hold one JSON document. The schema validates a single
   latest-round object; producers should overwrite with the latest round.
3. **LEAKAGE_AUDIT `audited_input_hashes`.** The skill's own Step-6 JSON example omits
   it, but artifact-registry.md invariant 2 requires it for every audit JSON — the
   schema enforces it (registry wins).
4. **`thread_id` in audit envelopes.** assurance-contract.md lists it in the minimum
   block, but kill-argument's own example omits it and OSS is single-agent (no external
   reviewer thread). Optional everywhere except `CITATION_AUDIT` (whose emission
   example includes it).
5. **LOGIC_VERIFICATION verdict vocabulary.** The Phase-5 example lists only
   PASS|WARN|FAIL|BLOCKED|ERROR; the skill's own 6-state table reserves
   `NOT_APPLICABLE`. The schema accepts the full 6-state vocabulary.
6. **BUDGET_FLOOR field names.** The 5 floor checks (routes explored, matrix
   completion, seed budget, failure records, remaining-budget declaration) and
   `completion_justification` are documented semantically but no JSON field names are
   fixed. The schema requires only `verdict` + `budget_floor.satisfied`; the two hard
   rules are enforced as validator post-checks.
7. **REVIEW_STATE verdict spelling.** Phase A output format says
   `ready / almost / not ready`; the ledger field spec says `not_ready`. Both
   spellings are accepted in the enum.
8. **PAPER_CLAIM_AUDIT has no explicit example anywhere.** Only the audit verdict,
   `audited_input_hashes`, and the `aigc_scan` field (writing-principles.md §0.5) are
   promised; `aigc_scan`'s internal shape is unconstrained.
9. **VERIFICATION_ROUTING path.** verification-routing.md still says
   `refine-logs/VERIFICATION_ROUTING.json`; the v5.2 canonical location is
   `verdicts/` (output-protocol.md wins, per the single-authority rule).
10. **PROBLEM_HASH / REGISTRY_HASH are .txt**, so they are regex-checked in the
    validator rather than schema-checked (see top of this file).
11. **RUN_BUDGET.json** is newly introduced alongside v5.3 (task P1-7); its schema is
    implemented per the agreed field list and may tighten once the producer lands.
12. **EVALUATION_PROTOCOL field names.** method-registry §3.6 documents the
    pre-registration quartet semantically (metrics lock / baseline parity / baseline
    re-implementation / anti-cherry-picking reporting), but no JSON field names are
    fixed. The schema requires only `schema_version` + `generated_at`; enforcement
    happens downstream via `parity_check` / `all_seeds_reported` / `full_grid_reported`
    checks in result-to-claim.
