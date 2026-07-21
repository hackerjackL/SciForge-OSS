# Output Versioning Protocol (SciForge-OSS — timestamped + fixed-name dual-write)

> **Status (v2.8 — backfilled missing contract)**: Defines the **dual-write versioning protocol** every skill MUST follow for output files. Backfilled in v2.8 because 16 SKILL.md files referenced this contract but the file itself was missing from OSS inheritance — a historical gap. This file closes that gap and makes all those references resolve.
>
> **Core principle**: Every output file is written TWICE — first to a timestamped path (immutable audit record), then copied to a fixed-name path (latest version for downstream consumers). The timestamped copy is the audit trail; the fixed-name copy is the working file. Downstream skills read the fixed name; auditors read the timestamped name.

## Quick Reference

- **Purpose**: 锁定双写本版本化协议（timestamped + fixed-name），全仓 output 文件统一
- **Producer**: every skill that writes an output file
- **Consumer**: downstream skills read fixed-name; auditors read timestamped
- **Output**: timestamped + fixed-name file pair per output
- **Key**: timestamped = immutable audit; fixed-name = latest working copy

## Dual-Write Protocol

Every output file MUST be written in two steps:

```
Step 1: Write to timestamped path (immutable)
  path: <stage_dir>/<base_name>_<YYYYMMDDTHHMMSS>Z.<ext>
  example: refine-logs/domain-signature_20260721T100000Z.json
  this file is NEVER modified after write — it is the audit record of what was produced at that time

Step 2: Copy to fixed-name path (latest)
  path: <stage_dir>/<base_name>.<ext>
  example: refine-logs/domain-signature.json
  this file is the working copy downstream skills read; it is overwritten on each new run
```

**Why both**: the timestamped copy lets auditors (`/invariant-check`, `/auto-review-loop`) reconstruct what was produced when, even after the fixed-name copy is overwritten. The fixed-name copy lets downstream skills read a stable path without timestamp search. Deleting the fixed-name copy breaks downstream; deleting the timestamped copy breaks audit.

## Stage-Scoped Paths

Artifacts live in their **stage directory**, not the project root:

| Stage | Directory | Examples |
|-------|-----------|----------|
| idea | `idea-stage/` | IDEA_DAG.md, IDEA_DAG_VISUAL.md |
| refine | `refine-logs/` | domain-signature.json, FALSIFICATION.md |
| review | `review-stage/` | PAPER_CLAIM_AUDIT.json |
| paper | `paper/` | main.tex, references.bib |
| audit | `audit_report/` | CITATION_AUDIT.json, PROOF_AUDIT.json |
| results | `results/` | CLAIMS_FROM_RESULTS.md |
| data_analysis | `data_analysis/` | ANALYSIS_REPORT.md |
| replication | `replication/` | REPLICATION_PACKAGE.md |

**Legacy root-level paths**: read as fallback ONLY (e.g., if a v1.0 artifact sits at project root). Producers ALWAYS write to stage-scoped paths; the root-level fallback is for backward compatibility with pre-v2.0 artifacts, not for new writes.

## Timestamp Format (locked)

```
YYYYMMDDTHHMMSSZ
  YYYY = 4-digit year
  MM = 2-digit month (01-12)
  DD = 2-digit day (01-31)
  T = literal 'T' separator
  HH = 2-digit hour (00-23, UTC)
  MM = 2-digit minute (00-59)
  SS = 2-digit second (00-60, UTC)
  Z = literal 'Z' (UTC marker)
```

**Examples**: `20260721T100000Z`, `20260721T143022Z`. Always UTC; never local time. The `Z` suffix is mandatory.

## Boundaries

- **Every output file is dual-written.** No skill writes only to a fixed name or only to a timestamped name — both are required. A skill that writes only the fixed name has no audit trail; a skill that writes only the timestamped name breaks downstream.
- **The timestamped copy is immutable.** After write, no skill modifies it. If the content needs revision, write a NEW timestamped copy (with a new timestamp) and overwrite the fixed-name copy — do NOT edit the existing timestamped file.
- **Stage-scoped paths are mandatory for new writes.** Root-level writes are forbidden for v2.8+ artifacts; the root-level fallback is read-only for legacy compatibility.
- **Timestamp is UTC always.** Local timezones introduce audit ambiguity; the `Z` suffix makes UTC explicit.
- **Fixed-name copy is the downstream contract.** Downstream skills read `<base_name>.<ext>` (no timestamp) — they do NOT search for the latest timestamp. Producers MUST ensure the fixed-name copy is valid after each run.
- **Deleting the fixed-name copy breaks downstream.** Deleting the timestamped copy breaks audit. Neither is disposable.

## See Also

- [`output-manifest.md`](output-manifest.md) — MANIFEST.md append protocol (companion: every dual-written file is also logged to MANIFEST.md)
- [`output-language.md`](output-language.md) — output language protocol (what language the content is in)
- [`output-protocol.md`](output-protocol.md) — output protocol aggregation
- [`artifact-registry.md`](artifact-registry.md) — which artifacts are load-bearing (producers/consumers)
- [`assurance-contract.md`](assurance-contract.md) — 6-state verdict vocabulary for audit artifacts
