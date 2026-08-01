# Artifact Registry — Single Source of Truth

Every cross-skill integration in SciForge pivots on a small set of **load-bearing artifacts**. This registry is the canonical contract for those artifacts: where they live, who produces them, who consumes them, what fields they must contain, and what verifiers guard them. SKILL.md prose can describe an integration; this registry *guarantees* one.

> **Advisory layer (optional, non-binding)**: For optional plugin consultation (e.g., additional literature databases, dataviz guides, domain knowledge), see [`plugin-router.md`](plugin-router.md). Plugin output is advisory only and NEVER produces registered artifacts, NEVER triggers INV-X checks, and NEVER alters pipeline semantics. Removing `research-plugins/` from the filesystem MUST NOT break any registered artifact's producer/consumer contract.

> **Rule of thumb**: if a downstream skill's behavior depends on the existence or content of a file produced upstream, that file MUST appear in this registry. Unlisted artifacts are advisory only — no skill may gate on them.

## Why this registry exists

Two recurring failure modes motivated this SSoT:

1. **Phantom artifacts.** A producer skill described an output in its SKILL.md but the consumer skill looked for a different filename (`CLAIMS_FROM_RESULTS.md` vs `CLAIM_VERDICT.md`). Both sides thought the contract was honored; the chain silently broke.
2. **Schema drift.** A producer added a field (`PREREG_HASH`) and three phases later a consumer checked the field — but neither side documented the field, so two other consumers never checked it. Pre-registration lock was a no-op for them.

This registry closes both gaps by being the **single, machine-checkable** list of artifact names, schemas, producers, consumers, and verifiers.

## Registered Artifacts

### Economics pipeline artifacts (Pipeline A)

> **Note**: Legacy alias wrappers (`/empirical-assumption-registry`, `/econometric-leakage-audit`) have been REMOVED. All artifacts are now produced by canonical shared-backbone skills (`/method-registry`, `/leakage-audit`) with the economics overlay.

| Artifact | Path | Producer | Consumers | Schema enforced by | Verifier |
|---|---|---|---|---|---|
| `methods/METHOD_REGISTRY.md` | methods/ | `/method-registry` (canonical, economics overlay) | `/leakage-audit`, `/experiment-execution`, `/result-to-claim`, `/auto-review-loop` (econ variant), `/paper-writing`, `/invariant-check`, `/citation-audit` | Sections 1-8 mandatory; Section 3 immutable post-lock (Method Selection = hash lock target) | `/invariant-check` at every phase entry |
| `methods/REGISTRY_HASH.txt` | methods/ | `/method-registry` (canonical, economics overlay) | `/result-to-claim`, `/invariant-check`, `/citation-audit`, `/leakage-audit` (re-audit), replication `run_all.sh` | Single-line SHA256 hex | `/invariant-check` recomputes and compares |

| `methods/OUTCOME_CLASSIFICATION.md` | methods/ | `/method-registry` (canonical, economics overlay, Step 9) | `/result-to-claim` (Step 0 + 3.2), `/invariant-check` INV-E2, `/auto-review-loop`, `/paper-writing`, `/citation-audit`, replication package | Primary + Secondary outcome tables; REGISTRY_HASH pointer; locked flag | `/invariant-check` INV-E2 verifies existence and both sections non-empty |
| `methods/METHOD_BINDING.md` | methods/ | `/method-registry` (canonical, Step 8) | `/experiment-execution` (Phase 1.7 verification), `/result-to-claim` (Step 3.2 estimator cross-check), `/citation-audit` (failure mode 11: estimator_name_mismatch), `/paper-writing` (Empirical Strategy section uses bound names), `/invariant-check` (econ invariant INV-E5) | Selected Methods table + Lock Status + Binding Hash; LOCKED state is immutable post-lock | `/experiment-execution` Phase 1.7 rejects EXPERIMENT_PLAN.md on LOCKED-binding mismatch; `/invariant-check` INV-E5 verifies existence |
| `review-stage/AUTO_REVIEW.md` + `REVIEW_STATE.json` | review-stage/ | `/auto-review-loop` | `/paper-writing` (passes to writer as reviewer feedback), `/rebuttal` | 6-state verdict schema in `assurance-contract.md`; `REVIEW_STATE.json` is the canonical JSON artifact (`REVIEW_OUTPUT.json` is a deprecated alias, see `assurance-contract.md` for current schema) | `/paper-writing` Phase 6 verifier checks existence at `assurance=submission` |
| `review-stage/REVIEW_LEDGER.json` | review-stage/ | `/auto-review-loop` (Phase E.5 per round; finalized at Termination) | `/citation-audit` (cross-checks review history without parsing prose), `/paper-writing` Phase 0.5 (Economics Pre-Submission Gate reads statistical_gate status), external verifier | 6-state verdict schema in `assurance-contract.md` extended with `details.rounds[]` array (per-round: score, verdict, action_items, debate_rulings, statistical_gate) | External verifier `verify_review_ledger.sh` checks existence and per-round schema; `/citation-audit` treats missing ledger as `WARN: missing_review_ledger` |
| `paper/main.pdf` + `paper/main.tex` + `paper/sections/*.tex` | paper/ | `/paper-writing` (compiled by `/paper-compile`) | `/auto-paper-improvement-loop`, `/logic-verification`, `/citation-audit`, `/kill-argument` | LaTeX compilation = 0 warnings | `/paper-compile` is the gate |
| `paper/CITATION_AUDIT.{md,json}` | paper/ | `/citation-audit` | `/paper-writing` Phase 6 verifier | 6-state verdict schema in `assurance-contract.md` | External verifier `verify_paper_audits.sh` |
| `paper/PROOF_AUDIT.{md,json}` | paper/ | `/logic-verification` | `/paper-writing` Phase 6 verifier | 6-state verdict schema in `assurance-contract.md` | External verifier `verify_paper_audits.sh` |
| `paper/KILL_ARGUMENT.{md,json}` | paper/ | `/kill-argument` | `/paper-writing` Phase 5.6 | 6-state verdict schema in `assurance-contract.md` | External verifier (when assurance=submission and theory-heavy) |
| `AGENT_DOC.md` | project root | `/auto-pipeline` Phase 0 (and equivalent Phase 0 in other pipelines) | Every downstream phase (re-reads at phase entry to confirm config intact) | Discipline / venue / methodology / gate settings table | `/invariant-check` validates discipline-specific fields |

### Shared backbone artifacts (all pipelines)

| Artifact | Path | Producer | Consumers | Schema enforced by |
|---|---|---|---|---|
| `RESEARCH_BRIEF.md` / `AGENT_DOC.md` | project root | User (or `/idea-discovery` Phase 0) | All pipelines Phase 0 | Free-form markdown; required fields: discipline, venue, methodology_class |
| `data/<dataset_name>/DATA_PROVENANCE.json` (real) OR `data/simulated/DATA_PROVENANCE.json` (synthetic) | data/ | — | `/universal-retrieval` (selects real-vs-synthetic profiling branch), `/citation-audit` (failure mode 13 reads `data_type`), `/auto-review-loop` (statistical gate reads `data_type` as BLOCK override for empirical claims on synthetic), `/invariant-check` (physics overlay verifies `physical_validity` for synthetic), `/idea-discovery` (overclaim_risk flag when `data_type: synthetic`) | `data_type: real\|synthetic` field is MANDATORY; real schema adds `source_url`/`license`/`acquisition_method`; synthetic schema adds `generator_skill`/`simulation_config`/`random_seed`/`validation_status`/`physical_validity`; both end with `provenance_hash: sha256:<hash>` |
| `data_acquisition_report.md` | project root | — | `/invariant-check` (INV-E4 reads DATA_SOURCE flag), `/citation-audit` (failure mode 13 reads data_type) | markdown with DATA_SOURCE flag (real\|synthetic), provenance details | |
| `data_analysis/.cache/insight_cache.json` | data_analysis/.cache/ | `/universal-retrieval` (Phase 7 writes; Phase 0 reads) | `/universal-retrieval` (self-consumed across invocations — Phase 0 of next run checks hash match to decide skip-vs-rerun) | `schema_version` + `input_hash` (data_files/research_brief/ref_paper_summary) + `data_type` + `stopping_rule` + `data_profile_summary` (6-dim) + `artifacts` (per-file SHA256) | Phase 0 hash-mismatch auto-invalidates; read-only for all other skills |
| `data_analysis/DATA_INSIGHT_REPORT.md` | data_analysis/ | `/universal-retrieval` | `/idea-discovery` (MANDATORY input — hard filter on CONSTRAINED/BLOCKED axes) | ≤500 words; 6-dim profile; top 3 supportive; top 3 restrictive; info ceiling; one-sentence advisory |
| `data_analysis/final_reference_report.md` | data_analysis/ | `/universal-retrieval` | advisory only; user review | Full 7-8 file structured report |
| `idea-stage/IDEA_REPORT.md` | idea-stage/ | `/idea-discovery` | `/novelty-check`, `/research-refine-pipeline` | Ranked idea list + per-idea AIM Sketch (economics) or PNV Sketch (physics) |
| `idea-stage/IDEA_DAG.json` | idea-stage/ | `/idea-discovery` Phase 2.5 (DAG-Based Idea Search) | `/idea-discovery` (self-consumed across MCTS iterations), `/novelty-check` (reads promoted ideas) | DAG JSON v1.0 per [`idea-dag-schema.md`](idea-dag-schema.md): nodes with fidelity_scores + ucb_score + visits; edges (mutation/crossover); search_metadata |
| `problem_anchor_hash.txt` | project root | `/research-refine-pipeline` (Phase 0 Problem Anchor freeze) | `/invariant-check` (INV-G1) | single-line SHA256 hex | optional, advisory only |
| `refine-logs/FINAL_PROPOSAL.md` | refine-logs/ | `/research-refine-pipeline` | `/method-registry`, `/experiment-execution` | Problem Anchor frozen section (idea-confirmed state) |
| `EXPERIMENT_PLAN.md` + `EXPERIMENT_TRACKER.md` | refine-logs/ | `/experiment-plan` (canonical), `/idea-discovery` Phase 4.5, `/research-refine-pipeline` | `/experiment-execution`, `/result-to-claim` | Plan = roadmap with claim map + blocks + run order; Tracker = state machine (Run ID/Milestone/Purpose/Status) |
| `CLAIMS_FROM_RESULTS.md` | project root | `/result-to-claim` | `/citation-audit` (failure mode 10: significance_gate_violation), `/paper-writing` Phase 0.5 (Economics Pre-Submission Gate), `/invariant-check` (INV-E2) | Per-claim verdict + significance gate (yes/partial/no) + REGISTRY_HASH pointer; Claims-Evidence Matrix |
| `NARRATIVE_REPORT.md` | project root | `/auto-pipeline` | `/paper-writing` | Structured research narrative with claims and evidence; discipline-aware (economics=AIM chain / cs-ml=SOTA narrative / physics=PNV chain) |
| `SIMULATION_CONFIG.md` | methods/ | `/auto-pipeline` Phase 3 | `/experiment-execution` (Phase 1.8 reads convergence study plan) | Solver config: software+version, mesh/grid, boundary conditions, convergence criteria, pseudopotentials, system size, code availability, benchmarking |
| `MANIFEST.md` | project root | every skill appends | pre-flight check at every skill entry | `output-manifest.md` schema |
| `EXPERIMENT_LOG.md` | project root | `/experiment-execution` | `/result-to-claim`, `/auto-review-loop`, replication | Run-by-run append-only log |
| `figures/latex_includes.tex` | figures/ | `/unified-plotting` | `/paper-writing`, `/paper-compile` | Valid LaTeX `\includegraphics` commands referencing `.pdf` files | `/paper-compile` (compilation → figure reference resolution) |
| `figures/d2_output/<name>.d2` + `<name>.pdf` | figures/d2_output/ | `/unified-plotting` | `/paper-writing`, `/paper-compile` | D2 source compiles without error; PDF output is valid vector | `/paper-compile` (figure reference resolution) |
| `figures/specs/<name>.json` + `figures/<name>.svg` or `.pdf` | figures/specs/ + figures/ | `/unified-plotting` | `/paper-writing`, `/paper-compile` | FigureSpec JSON schema valid per `unified-plotting/SKILL.md`; SVG is valid vector | `/paper-compile` (figure reference resolution) |

### Pre-writing boundary artifacts (cross-discipline, discipline-aware via overlays)

These artifacts are produced by the shared backbone skills (`/method-registry`, `/leakage-audit`, `/invariant-check`) and consumed by downstream pre-writing skills. They are discipline-aware: the same artifact name carries different schema depending on `DISCIPLINE_CONTEXT` (economics=AIM / cs-ml=SOTA-targeted / physics=PNV / general=Method Sketch).

| Artifact | Path | Producer | Consumers | Schema enforced by | Verifier |
|---|---|---|---|---|---|---|
| `methods/METHOD_REGISTRY.md` | methods/ | `/method-registry` | `/leakage-audit`, `/result-to-claim`, `/auto-review-loop`, `/invariant-check` | 8-section schema (discipline-aware: economics=AIM / cs-ml=SOTA-targeted / physics=PNV / general=Method Sketch); Section 3 hash-locked | `/invariant-check` recomputes REGISTRY_HASH and compares |
| `methods/REGISTRY_HASH.txt` | methods/ | `/method-registry` | `/invariant-check` (drift detection) | Single-line SHA256 hex of `METHOD_REGISTRY.md` Section 3 | `/invariant-check` recomputes and compares |
| `methods/APPROVAL_LOG.txt` | methods/ | `/method-registry` | `/invariant-check` (human checkpoint record) | Structured log: timestamp, approver, section, action (lock/unlock/revise), reason | `/invariant-check` verifies log entries match hash lock state |
| `methods/METHOD_BINDING.md` | methods/ | `/method-registry` (canonical, Step 8) | `/experiment-execution` (Phase 1.7 verification), `/leakage-audit`, `/result-to-claim`, `/citation-audit` (failure mode 11), `/invariant-check` (INV-E5 / INV-C1) | Selected Methods table + Lock Status + Binding Hash; LOCKED state immutable post-lock | `/experiment-execution` rejects on LOCKED-binding mismatch; `/invariant-check` INV-E5 verifies existence |
| `methods/OUTCOME_CLASSIFICATION.md` | methods/ | `/method-registry` (canonical, Section 4 extraction) | `/result-to-claim` (Step 0 + 3.2 primary/secondary gate), `/invariant-check` INV-E2, `/auto-review-loop`, `/paper-writing`, `/citation-audit` | Primary + Secondary outcome tables; REGISTRY_HASH pointer; locked flag | `/invariant-check` INV-E2 verifies existence and both sections non-empty |
| `audit_report/LEAKAGE_AUDIT.md` + `.json` | audit_report/ | `/leakage-audit` (canonical) | `/result-to-claim`, `/auto-review-loop`, `/paper-writing`, `/citation-audit`, `/invariant-check` | JSON schema in `leakage-audit/SKILL.md` Step 6 (discipline-aware: Type I/II/III/IV detection); 6-state verdict | `/result-to-claim` rejects if `verdict==FAIL`; `/invariant-check` re-verifies verdict consistency |
| `audit_report/Type_I.md` / `Type_II.md` / `Type_III.md` / `Type_IV.md` | audit_report/ | `/leakage-audit` | `/auto-review-loop` (per-type pitfall context for reviewer prompt) | Per-type pitfall checklist (discipline-aware: economics=14-class / cs-ml=14-class / physics=10-class / general=N/A) | `leakage-audit` Step 6 verifies per-type verdict consistency with aggregate verdict |
| `methods/BENCHMARK_BINDING.md` | methods/ | `/experiment-execution` (Phase 1.7', CS/ML only) | `/invariant-check` (INV-C1), `/result-to-claim` (Step 3.2' SOTA Gate input) | Locked benchmark protocol: dataset version + split hash + metric computation code hash + seed strategy + baseline checkpoint hash; SHA256 hash lock | `/invariant-check` INV-C1 verifies existence and hash match; drift detection on any field change |
| `methods/ESTIMATOR_VERIFICATION.md` | methods/ | / | `/leakage-audit` (Type II pitfall context: IV first-stage F < 10 → weak-IV CRITICAL), `/invariant-check` (INV-E5) | Per-estimator pass/fail table: Estimator / Impl match / SE correct / F-stat / Pre-trend / Conley SE / Romano-Wolf / Verdict | `/invariant-check` INV-E5 verifies estimator implementation matches pre-registered binding |
| `audit_report/INVARIANT_CHECK.md` + `.json` | audit_report/ | `/invariant-check` | All pipeline orchestrators (phase-boundary gate), `/paper-writing` (gate) | 6-state verdict per invariant (INV-C1/C2/C3 for CS/ML / INV-P1~P5 for physics / INV-E1~E5 for economics / INV-G1 for general) | External verifier checks existence at phase boundaries |
| `quality_gate/FINAL_VERDICT.md` | quality_gate/ | `/quality-gate` (Final) | `/paper-writing` (all disciplines, pre-writing gate) | `stagnation` / `quality_floor` / `self_deception` / `overall` gate verdicts (PASS / WARN / FAIL / BLOCKED) | `/quality-gate` (self-verifying, Phase 3) |
| `quality_gate/STAGNATION_REPORT.md` | quality_gate/ | `/quality-gate` (Phase 1) | `/quality-gate` Phase 3 (final verdict input) | Per-phase retry counter comparison against MAX_RETRIES; STAGNATED / WARNING / OK per phase | `/quality-gate` Phase 1 |
| `quality_gate/QUALITY_FLOOR_REPORT.md` | quality_gate/ | `/quality-gate` (Phase 2) | `/quality-gate` Phase 3 (final verdict input) | QF-N checks per discipline overlay; PASS / FAIL / WARN per criterion | `/quality-gate` Phase 2 |
| `quality_gate/SELF_DECEPTION_REPORT.md` | quality_gate/ | `/quality-gate` (Phase 3) | `/paper-writing` (all disciplines, limitations section input) | SD-N checks per discipline overlay; claim-by-claim evidence verification; overclaim / cherry-picking flags | `/quality-gate` Phase 3 |

## Schema Invariants (cross-cutting)

These invariants apply to every registered artifact:

1. **Always emit, never silent-skip.** A producer skill must write the registered artifact even when its detector is negative. Detector-negative = `NOT_APPLICABLE` verdict with reason code; missing artifact = chain break.
2. **SHA256 hash in audit artifacts.** Every audit JSON (`PAPER_CLAIM_AUDIT.json`, `CITATION_AUDIT.json`, `PROOF_AUDIT.json`, `KILL_ARGUMENT.json`, `LEAKAGE_AUDIT.json`) must include `audited_input_hashes` mapping every consumed file to its SHA256. The external verifier rehashes and flags `STALE` on mismatch.
3. **6-state verdict vocabulary.** Audit skills emit exactly one of: `PASS` / `WARN` / `FAIL` / `NOT_APPLICABLE` / `BLOCKED` / `ERROR`. See `assurance-contract.md` for semantics.
4. **Section 3 immutability (hash lock).** Once `METHOD_REGISTRY.md` Section 3 (Method Selection) is approved and `REGISTRY_HASH.txt` is written, no skill may modify Section 3 (Method Selection). Any drift = `FAIL` verdict from `/invariant-check`.
5. **Stage-scoped paths.** Artifacts live in their stage directory (`idea-stage/`, `refine-logs/`, `review-stage/`, `paper/`, `audit_report/`, `results/`, `data_analysis/`, `replication/`). Legacy root-level paths are read as fallback only; producers always write to stage-scoped paths. See `output-versioning.md`.

## Adding a new artifact to this registry

When a new cross-skill artifact is introduced:

1. Add a row to the appropriate table above with all columns populated.
2. The producer skill's SKILL.md must declare the artifact in its Output Shape section with a reference back to this registry: `[Artifact Registry](../shared-references/artifact-registry.md)`.
3. The consumer skill's SKILL.md must declare the artifact in its Inputs section with the same reference.
4. If a verifier exists, list it; if not, mark `none (advisory)` and explain why the artifact is non-load-bearing.
5. Update `METHODOLOGY.md` artifact contracts table to mirror the new row.

## Anti-patterns to refuse in review

- **"The skill will produce a report."** — which filename? which path? Rejected unless listed here.
- **"The downstream skill reads the upstream output."** — which artifact? which fields? Rejected unless the consumer column names the skill and the schema column names the fields.
- **"Optional artifact."** — if it's optional, it's not load-bearing; don't register it here. If it's load-bearing, it's not optional.
- **"Same as <other artifact> but for <discipline>."** — list it as a separate row with discipline tag. Don't make readers infer.
- **Schema described in prose but not enforced by a verifier.** — Mark `advisory only` explicitly. Don't pretend a prose schema is a guarantee.

## Economics Alias Removal (2026-06-30)

The legacy alias wrapper skills (`/empirical-assumption-registry`, `/econometric-leakage-audit`) have been **removed** as of 2026-06-30. All economics pipeline functionality is now served directly by the canonical shared-backbone skills (`/method-registry`, `/leakage-audit`) with the economics overlay.

**Artifact path migration (completed)**:

| Legacy artifact / skill | Canonical artifact / skill | Path change | Notes |
|---|---|---|---|
| `ASSUMPTIONS.md` (produced by `/empirical-assumption-registry`) | `methods/METHOD_REGISTRY.md` (produced by `/method-registry` economics overlay) | project root → `methods/` | Schema upgraded from free-form to AIM 8-section rigid |
| `results/PREREG_HASH.txt` (produced by `/empirical-assumption-registry`) | `methods/REGISTRY_HASH.txt` (produced by `/method-registry`) | `results/` → `methods/` | Hash lock mechanism unchanged |
| `results/OUTCOME_CLASSIFICATION.md` (produced by `/empirical-assumption-registry` Step 9) | `methods/OUTCOME_CLASSIFICATION.md` (produced by `/method-registry` economics overlay) | `results/` → `methods/` | Canonical path is `methods/` |
| `audit_report/LEAKAGE_AUDIT.md` + `.json` (produced by `/econometric-leakage-audit`) | `audit_report/LEAKAGE_AUDIT.md` + `.json` (produced by `/leakage-audit` economics overlay) | path unchanged | Producer switched from alias to canonical |
| `/empirical-assumption-registry` (skill) | `/method-registry` (economics overlay) | skill invocation | REMOVED — use `/method-registry` directly |
| `/econometric-leakage-audit` (skill) | `/leakage-audit` (economics overlay) | skill invocation | REMOVED — use `/leakage-audit` directly |

**Canonical invocation**: All economics pipeline phases now invoke `/method-registry` and `/leakage-audit` directly with `DISCIPLINE_CONTEXT=economics`. The canonical artifacts (`methods/METHOD_REGISTRY.md`, `methods/REGISTRY_HASH.txt`, `methods/OUTCOME_CLASSIFICATION.md`) are the single source of truth.

## See Also

- [`assurance-contract.md`](assurance-contract.md) — 6-state verdict state machine, audit artifact JSON schema
- [`integration-contract.md`](integration-contract.md) — 5-component cross-skill integration contract (activation / artifact / checklist / backfill / verifier)
- [`output-versioning.md`](output-versioning.md) — stage-scoped path + timestamped-then-fixed-name protocol
- [`output-manifest.md`](output-manifest.md) — `MANIFEST.md` append protocol
- [`effort-contract.md`](effort-contract.md) — depth/cost axis
- [`skill-config.md`](skill-config.md) — centralized public knobs (MAX_ROUNDS, EFFORT, ASSURANCE, etc.)
