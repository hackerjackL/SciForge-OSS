# Integration Contract

When one SciForge skill delegates work to another (or to persistent project
state), the coupling must be **engineered**, not assumed. This document
formalizes what every cross-skill integration inside SciForge must provide.

Rule of thumb: **SKILL.md prose can *describe* an integration; it cannot
*guarantee* one.** Any integration whose silent failure would damage the
research result needs the components below. Prose-only "MUST invoke X"
has repeatedly failed in practice — the executor skips under context
pressure and the caller has no way to detect it.

## Known failure mode (why this contract exists)

Two bugs in the same week, same pathology:

1. **Assurance gate bypass.** A paper-writing run at high effort
   silently skipped the logic-verification, result-to-claim, and citation-audit
   skills because each phase's content detector could return negative
   and the outer prose said "audit is optional."
2. **Research wiki ingest no-op.** A research-wiki init created the
   papers directory but no paper ever landed there: the various
   paper-discovery skills — none carried a wiki-ingest hook, and the
   two that did only had soft prose ("optional and automatic").

Both bugs ship through the same gap: **one skill "called" another via
prose without a concrete artifact, a verifier, or an observable
activation predicate**.

## Required components

Every integration between two SciForge skills (or between a skill and a
persistent project artifact) must provide all five:

### 1. Activation predicate — single, explicit, observable

A one-line test that says "does this integration fire in this context?"
Must be observable from outside the LLM (a file exists, an argument is
set, an environment variable is present). Not a vibe, not "probably
relevant."

- ✅ "if the `research-wiki/` directory exists"
- ✅ "if the assurance level is `submission`"
- ❌ "if the user seems to want this"

### 2. Concrete artifact or log entry

Successful execution must leave an observable side effect: a file, a
JSON record, a log line. The artifact is the receipt — something a
third party (verifier, code reviewer, human auditor) can inspect to
answer "did this integration run?"

- ✅ `paper/PROOF_AUDIT.json` with the verdict schema
- ✅ `research-wiki/papers/<slug>.md` + `research-wiki/log.md` append
- ❌ "the model said it ran"

### 3. Visible checklist — for long workflows

If the integration fires inside a multi-step workflow (paper-writing
final phase, idea-discovery late phase, etc.), render a **visible
checkbox block** at the start of the phase so the executor has to
confront each row before claiming done. Prose-only "MUST" inside a long
SKILL.md is the first thing to get skipped.

```
📋 Submission audits required before Final Report:
   [ ] 1. logic-verification  → paper/PROOF_AUDIT.json
   [ ] 2. result-to-claim     → paper/PAPER_CLAIM_AUDIT.json
   [ ] 3. citation-audit      → paper/CITATION_AUDIT.json
   [ ] 4. Run the submission verifier against paper/ at assurance=submission
   [ ] 5. Block Final Report iff verifier exit code != 0
```

Cheap, and empirically resists lazy skipping. Skip only for single-step
invocations (one-off skills).

### 4. Backfill / repair — explicit manual fallback

An escape hatch for when the integration didn't fire. Users must be
able to run a command that **declares** the missed inputs and ingests
them retroactively. Prefer explicit arguments over trace-scanning — the
backfill should not have to guess what to backfill.

- ✅ `research-wiki sync --arxiv-ids 2501.12345,1706.03762`
- ✅ `research-wiki sync --from-file ids.txt`
- ⚠️ `research-wiki sync` that scans the trace store for arxiv IDs —
     only as a best-effort secondary mode, not the primary UX, and
     clearly labeled as heuristic.

### 5. Verifier or diagnostic (only when load-bearing)

If silent failure of this integration would damage the research result
(wrong numbers shipped to a conference, claims unsupported by
evidence, citations in wrong context), a verifier must exist whose
exit code is the source of truth for downstream gates.

- ✅ A submission-readiness verifier — exit 1 blocks the Final Report
- ✅ A wiki-coverage diagnostic — reports gaps but does not block
     (coverage is not load-bearing on any research outcome)

Verifiers must be **external processes** (not LLM self-report), must
validate **concrete artifacts** (§2) against a schema, and must emit a
structured report callers can parse.

A diagnostic-only verifier (no exit-1 blocking) is still valuable — it
surfaces drift to humans. But do not market a diagnostic as a gate.

## Anti-patterns to refuse in review

When reviewing a new integration proposal, reject any of:

- **"Optional and automatic"** — contradicts itself; if it's automatic,
  it's not optional. Pick one and mean it.
- **"The skill will intelligently decide"** — indecision surface, not
  a predicate (§1).
- **"Copy the following 10 lines into each caller"** — missing a single
  canonical implementation; will drift within a month.
- **"The reviewer can see from the logs that..."** — if the evidence is
  unstructured logs, write a schema and make it an artifact (§2).
- **"Users should remember to..."** — missing backfill (§4); humans
  don't reliably remember.
- **"Trust the LLM to self-report completion"** — missing verifier (§5)
  when the failure is load-bearing.
- **"Same artifact, different filename"** — the producer writes
  `CLAIMS_FROM_RESULTS.md` and the consumer reads `RESULT_CLAIMS.md`;
  the integration silently no-ops because the file exists under a
  different name. The canonical filename must live in
  [`artifact-registry.md`](artifact-registry.md) and be referenced
  verbatim by both sides.
- **"Prose says MUST, code says MAYBE"** — the SKILL.md text reads
  "MUST verify PREREG_HASH before proceeding" but no activation
  predicate, no artifact, and no verifier exist; the executor treats
  it as aspirational. If it is load-bearing, it needs all five
  components; if it is not, downgrade the prose to "SHOULD".

## Enforcement: how the five components are verified

The five required components above are necessary but not sufficient —
they must also be **verified** at runtime. SciForge provides three
verification layers, each catching a different failure class.

### Layer 1 — Pre-flight checker (per skill invocation)

Before a skill's main body runs, the orchestrator checks the
**activation predicate** (§1) and the existence of required input
artifacts (§2). If the predicate is false, the skill is skipped with
a logged `NOT_APPLICABLE` verdict. If the predicate is true but a
required input artifact is missing, the skill aborts with `BLOCKED`
and emits a backfill hint (§4).

This is the first line of defense against silent no-ops. It is
implemented by the orchestrator skill (e.g. `/paper-writing`,
`/idea-discovery`) at each phase boundary, not by
the callee skill itself — the callee cannot be trusted to verify its
own activation.

### Layer 2 — `/invariant-check` skill (phase-boundary verifier)

**Status**: NEW, economics-first, shared extension.
**Reserved hooks**: `invariant-check/overlays/physics.md`,
`invariant-check/overlays/cs-ml.md`, `invariant-check/overlays/general.md` (placeholder
files, to be populated when those pipelines add invariants).

`/invariant-check` is a structural verifier that runs at phase
boundaries and confirms load-bearing invariants hold before the next
phase begins. It is **not** a reviewer — it does not assess quality,
novelty, or correctness. It only checks that the artifacts the next
phase depends on exist, are well-formed, and carry the expected
verdicts.

Economics invariants (canonical, hardcoded — do not infer):

| Check | Trigger | Pass condition | Fail action |
|-------|---------|----------------|-------------|
| `REGISTRY_HASH` | Before `/result-to-claim`, `/paper-writing`, `/auto-review-loop` | `METHOD_REGISTRY.md` Section 3 exists AND `REGISTRY_HASH.txt` matches `SHA256(Section 3)` | BLOCK — re-run `/method-registry` |
| `OUTCOME_CLASSIFICATION` | Before `/result-to-claim` | `methods/OUTCOME_CLASSIFICATION.md` exists AND lists primary vs secondary outcomes | BLOCK — re-run `/method-registry` Step 4 |
| `LEAKAGE_AUDIT_VERDICT` | Before `/paper-writing` | `audit_report/LEAKAGE_AUDIT.json` exists AND `verdict ∈ {PASS, WARN}` | BLOCK if FAIL — re-run `/leakage-audit` |
| `DATA_SOURCE_CONSISTENCY` | Before `/paper-writing` | If `DATA_SOURCE=synthetic`, no occurrence of "empirical evidence" / "policy implication" in `paper/` | BLOCK — re-write affected sections |

Output: `audit_report/INVARIANT_CHECK.json` with the 6-state verdict
schema from [`assurance-contract.md`](assurance-contract.md). Consumed
by the orchestrator as a gate.

### Layer 3 — Audit-verifier external process (submission gate)

For the final submission gate (paper-writing Phase 6), an external
verifier process validates the concrete artifacts (§2) against their
schemas and emits an exit code. Exit 1 blocks the Final Report. This
is already normative in [`assurance-contract.md`](assurance-contract.md)
and is referenced here for completeness — it is the last line of
defense, not the first.

A diagnostic-only verifier (no exit-1 blocking) is still valuable for
non-load-bearing integrations (e.g. research-wiki coverage gaps) — it
surfaces drift to humans without blocking progress.

## Live integration registry

Every cross-skill integration that has passed the 5-component check is
listed here. New integrations must be added to
[`artifact-registry.md`](artifact-registry.md) AND this table; the two
are cross-referenced. Integrations not listed here are non-normative
and may be silently skipped by the orchestrator.

| # | Caller | Callee | Activation predicate | Concrete artifact | Verifier |
|---|--------|--------|----------------------|-------------------|----------|
| 1 | `paper-writing` (Phase 4.5) | `logic-verification` | `assurance=submission` AND `paper/sections/proof.tex` exists | `paper/PROOF_AUDIT.json` | submission verifier (exit 1) |
| 2 | `paper-writing` (Phase 4.7) | `result-to-claim` | `paper/main.pdf` exists | `paper/PAPER_CLAIM_AUDIT.json` | submission verifier (exit 1) |
| 3 | `paper-writing` (Phase 5.5) | `citation-audit` | `paper/main.pdf` exists | `paper/CITATION_AUDIT.json` | submission verifier (exit 1) |
| 4 | `paper-writing` (Phase 1, economics overlay) | `method-registry` | economics pipeline entered | `methods/METHOD_REGISTRY.md` + `methods/REGISTRY_HASH.txt` | `/invariant-check` (REGISTRY_HASH) |
| 5 | `method-registry` (post) | `leakage-audit` | `methods/METHOD_REGISTRY.md` exists | `audit_report/LEAKAGE_AUDIT.json` | `/invariant-check` (LEAKAGE_AUDIT_VERDICT) |
| 6 | `leakage-audit` → `paper-writing` | (verdict gate) | `LEAKAGE_AUDIT.json` exists | (consumed as gate) | `/invariant-check` (LEAKAGE_AUDIT_VERDICT) |
| 7 | `paper-writing` (Phase 5, economics overlay) | `result-to-claim` | `results/` non-empty AND `methods/METHOD_REGISTRY.md` exists | `CLAIMS_FROM_RESULTS.md` | `/invariant-check` (REGISTRY_HASH) |
| 8 | `result-to-claim` → `paper-writing` | (input contract) | `CLAIMS_FROM_RESULTS.md` exists | (consumed as input) | `paper-writing` internal |
| 9 | `paper-writing` (Phase 7, economics overlay) | `auto-review-loop` | `paper/main.pdf` exists AND `REVIEWER_PROMPT_VARIANT=senior-econ-editor` | `review-stage/REVIEW_STATE.json` | auto-review-loop internal (MAX_ROUNDS gate) |
| 10 | `idea-discovery` (Phase 1.5) | `universal-retrieval` | local data exists OR `/universal-retrieval` completed | `DATA_INSIGHT_REPORT.md` | `/idea-discovery` consumes (MANDATORY input check) |
| 11 | (shared) paper-reading skills | `research-wiki` ingest | `research-wiki/` directory exists | `research-wiki/papers/<slug>.md` + `log.md` append | Wiki-coverage diagnostic (non-blocking) |
| 12 | `paper-writing` (Phase 2) | `unified-plotting` | `PAPER_PLAN.md` exists AND `figures/` directory exists | `figures/latex_includes.tex` + `figures/*.pdf` | `/paper-compile` (figure reference resolution) |
| 13 | `paper-writing` (Phase 2b) | `unified-plotting` | `illustration=d2` AND `PAPER_PLAN.md` figure plan has architecture/pipeline entries | `figures/d2_output/*.pdf` + `*.d2` source | `/paper-compile` (figure reference resolution) |
| 14 | `paper-writing` (Phase 2b) | `unified-plotting` | `illustration=figurespec` AND `PAPER_PLAN.md` figure plan has manual-layout entries | `figures/specs/*.json` + `figures/*.svg` | `/paper-compile` (figure reference resolution) |

**Reserved rows** (placeholders for other pipelines — to be populated
when those pipelines add integrations):

| Pipeline | Reserved integration | Status |
|----------|---------------------|--------|
| `idea-discovery` (general) | → `universal-retrieval` (cross-discipline) | placeholder |

When adding a new cross-skill integration, add a row to the table above
AND a corresponding entry in
[`artifact-registry.md`](artifact-registry.md), then confirm all
columns are populated.

## See Also

- [`artifact-registry.md`](artifact-registry.md) — single source of
  truth for every cross-skill artifact filename, producer, consumer,
  and schema
- [`skill-config.md`](skill-config.md) — canonical definitions of
  shared knobs (`EFFORT`, `ASSURANCE`, `MAX_ROUNDS`,
  `REVIEWER_PROMPT_VARIANT`, `DATA_SOURCE`, etc.) referenced by the
  activation predicates above
- [`assurance-contract.md`](assurance-contract.md) — implementation of
  the paper-writing submission gate under this contract; defines the
  6-state verdict schema used by `/invariant-check`
- [`reviewer-independence.md`](reviewer-independence.md) — the adjacent
  contract for cross-model review (executor never filters reviewer
  inputs)
