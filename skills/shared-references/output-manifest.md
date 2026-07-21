# Output Manifest Protocol (SciForge-OSS — MANIFEST.md append-only ledger)

> **Status (v2.8 — backfilled missing contract)**: Defines the **MANIFEST.md append-only ledger** protocol every skill MUST follow. Backfilled in v2.8 because 16 SKILL.md files referenced this contract but the file itself was missing from OSS inheritance — a historical gap. This file closes that gap.
>
> **Core principle**: Every output file is logged to `MANIFEST.md` at the project root via append-only. MANIFEST.md is the single ledger of what was produced, when, by which skill, at which path (both timestamped and fixed). Pre-flight checks at every skill entry read MANIFEST.md to confirm upstream prerequisites exist.

## Quick Reference

- **Purpose**: 锁定 MANIFEST.md append-only 协议，全仓 output 文件统一登记
- **Producer**: every skill appends a row after dual-writing its output
- **Consumer**: pre-flight check at every skill entry reads MANIFEST.md to verify prerequisites
- **Output**: MANIFEST.md at project root (append-only, never rewrite)
- **Key**: append-only ledger; never rewrite or delete rows; pre-flight gate

## MANIFEST.md Location

```
<project_root>/MANIFEST.md
```

Single file at project root. Never stage-scoped — MANIFEST.md is the global ledger across all stages.

## Append Row Schema

Every skill, after dual-writing its output (per [`output-versioning.md`](output-versioning.md)), appends ONE row to MANIFEST.md:

```markdown
| <YYYY-MM-DDTHH:MM:SSZ> | <skill_name> | <artifact_name> | <stage_dir>/<timestamped_path> | <stage_dir>/<fixed_path> | <sha256_hash> |
```

**Example row**:
```markdown
| 2026-07-21T10:00:00Z | /domain-learner | domain-signature | refine-logs/domain-signature_20260721T100000Z.json | refine-logs/domain-signature.json | a3f5e8c1d2b4f6a8e0c2d4b6f8a0e2c4d6b8f0a2c4e6d8b0f2a4 |
```

**Field semantics**:
- `timestamp`: UTC ISO-8601, matches the timestamped file's timestamp
- `skill_name`: the skill that produced the artifact (e.g., `/domain-learner`, `/paper-writing`)
- `artifact_name`: the artifact's canonical name from [`artifact-registry.md`](artifact-registry.md)
- `timestamped_path`: relative to project root; the immutable audit copy
- `fixed_path`: relative to project root; the working copy downstream skills read
- `sha256_hash`: SHA-256 of the fixed-path file content (for staleness detection — downstream hashes and compares)

## Pre-Flight Check (every skill entry)

At skill entry, before any work, the skill MUST:

```
Step 1: Read MANIFEST.md
Step 2: For each declared prerequisite (from the skill's SKILL.md "Consumes" section):
        → check if a row exists with matching artifact_name
        → check if the fixed_path file exists
        → re-hash the fixed_path file and compare to the row's sha256_hash
        → if hash mismatch: surface STALE warning (the file was modified after MANIFEST logging)
        → if file missing: BLOCK with reason_code: missing_prerequisite_<artifact_name>
Step 3: If all prerequisites present and non-stale: proceed
Step 4: If any STALE: WARN but proceed (staleness is advisory, not blocking — the file may have been legitimately updated)
Step 5: If any missing: BLOCK (missing prerequisites are blocking — the skill cannot run without its inputs)
```

**Stale vs missing distinction**: stale = file exists but hash mismatch (maybe updated; advisory); missing = file does not exist (blocking). Confusing these two either blocks the pipeline unnecessarily or lets skills run on missing inputs.

## Append-Only Contract

- **MANIFEST.md is append-only.** No skill rewrites, reorders, or deletes rows. A new run appends new rows; it does NOT update old rows.
- **Stale rows are the audit trail.** If a skill overwrites the fixed-name copy, the NEW run appends a new row with the new hash; the OLD row remains (its hash is now stale, which is the intended audit record of "this file was updated at time X").
- **Never delete MANIFEST.md.** It is the global ledger; deleting it breaks every downstream skill's pre-flight check.
- **One row per dual-write.** A skill that produces 3 artifacts appends 3 rows, not 1 summary row. Granularity is per-artifact.

## Boundaries

- **MANIFEST.md is append-only.** Never rewrite, reorder, or delete rows. New runs append; old rows remain as audit.
- **Stale is advisory; missing is blocking.** Pre-flight WARNs on staleness, BLOCKs on missing — never invert these.
- **One row per artifact.** Do NOT summary-row multiple artifacts; each gets its own row for per-artifact audit.
- **SHA-256 is mandatory.** The hash field is not optional — downstream staleness detection depends on it.
- **MANIFEST.md sits at project root, not stage-scoped.** It is the global ledger; stage-scoping would fragment the audit trail.
- **Pre-flight check is at skill entry, not skill exit.** Verify prerequisites BEFORE working; do not discover missing inputs mid-work.

## See Also

- [`output-versioning.md`](output-versioning.md) — dual-write protocol (companion: every MANIFEST row corresponds to a dual-written file)
- [`artifact-registry.md`](artifact-registry.md) — load-bearing artifacts (whose rows in MANIFEST are mandatory)
- [`assurance-contract.md`](assurance-contract.md) — 6-state verdict vocabulary (STALE → WARN; MISSING → BLOCK)
- [`integration-contract.md`](integration-contract.md) — cross-skill integration (pre-flight check is the activation component)
