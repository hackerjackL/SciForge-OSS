---
name: methodology-and-context-contract
type: shared-reference
role: cross-cutting-single-agent-discipline
---

# Methodology & Context Contract (SciForge-OSS — Single-Agent Cross-Cutting Discipline)

> **Purpose (v2.3)**: Odd-central discipline for the **single-agent, single-AI, full-pipeline** configuration. Absorbs the reusable methodology of Ouroboros (sufficiency stopping, evidence-forcing), ARIS / auto-claude-code-research-in-sleep (bundle+compact context control, reviewer-only-raw-artifacts), nature-skills (static/dynamic split, figure-contract-first, no-fabrication), and legacy SciForge (type-D deterministic-first checks, hash lock, effort split). It answers the three questions the OSS keeps tripping on: **how much analysis is enough, how much context per step, and what is the pipeline's boundary.**
>
> ProducerReference: this file is referenced (`pointer-load`, not inlined) by the orchestrator and any consuming skill to avoid duplicating these rules across 24 SKILL.md files.

## 1. Sufficiency Stopping Rule (防无限分析 / Ouroboros principle)

Research loops over-eagerly drill into correlations / data / sub-questions. Stop analyzing a sub-question **only when all three hold**:

1. **All mandatory fields for the current question are assigned** (no `?</td>` `TODO`; every required axis resolved).
2. **Determination unchanged across two consecutive rounds** (the last two passes reached the same judgment).
3. **Marginal return ≤ 0** (one more pass adds no actionable, evidence-backed refinement).

Otherwise, list the open/anti-stop case and continue. If continuing, you must name the *specific* open question and the *evidence* that would resolve it — never "keep digging" as a habit. Write `stopping_rule.satisfied = true|false` into every analysis output.

**Anti-stop cases** (do NOT stop): unverifiable numeric assertion (< 0.7 confidence without raw stat, method empty), a detectably-checkable claim left unchecked, undefined data-availability term used in a conclusion, a claim whose fidelity cannot be stated.

## 2. Evidence-Forcing (Ouroboros quality-auditor principle)

- A "feature" of the data/problem (skew, long-tail, high variance, aleatoric noise) is **not** an error — never "fix" it to make results prettier. Only violations of the problem's own structure/physics count as defects.
- Every finding shipped into any output must carry `raw_stat` + `confidence` + `method`. A finding without raw evidence is void — do not emit it.
- The data/evidence layer **reports** (support / constrain / bottleneck / unknown); it never **judges** the idea ("data ceiling low ⇒ idea invalid" is an illegal inference). Boundary: analysis advises; the idea gate adjudicates.

## 3. Context Economy via Bundle + Compact (ARIS principle)

| Mechanism | Rule |
|-----------|------|
| **Bundle-out** | Large full prompts/instructions are written to a bundle file (e.g. `refine-logs/<phase>.bundle.md`); inter-phase handoffs reference the *path*, not the full text. |
| **Compact-forward** | A phase whose prior artifact is ≥ ~200 lines must first write a compact 20-40 line summary file, then base the next phase on that summary — not the raw dump. |
| **State persistence** | Always persist phase state (round, scores, frozen decisions) to a structured JSON (`*_STATE.json`) so a full run can resume after compaction without re-deriving. |
| **Pointer-load shared refs** | Shared discipline files are referenced by path (pointer-load), never copied into per-skill bodies — one canonical source, zero duplication. |

## 4. Deterministic-First Checks + Hash Lock (legacy SciForge principle)

Anything answerable by "read a file + parse a field + compare" (file existence, field presence, numeric threshold, SHA-256 match, `count ≥ n`) **must** be done deterministically, **before** any LLM judgment. No gate may silently skip a deterministic check it is capable of running.

- **Hash lock**: once a method / claim / result is frozen, write a `SHA-256` of the locked artifact to `*_HASH.txt`; downstream recomputes and refuses to proceed on mismatch (blocks post-hoc method / claim editing).
- **Effort/assurance split**: `effort` (how much work) and `assurance` (how strict the audits) are independent axes. High effort never silently relaxes audit gates.

## 5. Reviewer-Only-Raw-Artifacts (ARIS reviewer-independence principle, single-agent adaptation)

When self-reviewing or when delegating to a reviewer sub-agent, pass only **paths + role + review goal + raw artifacts** — never the executor's summary, interpretation, recommendation, leading questions, or prior round's feedback. The executor does not judge its own integrity. Single-agent adaptation: still *persist the executor's interpretation separately* from the raw artifact so a later external-review pass reads the raw copy untouched.

## 6. Figure Contract First + No-Fabrication (nature-skills principle)

- Before rendering any figure, write the 5-element contract: (1) core conclusion the figure argues, (2) evidence chain per panel (drop any panel without evidence), (3) figure archetype, (4) backend (data↦python, diagram↦d2, theory↦tikz/AI-direct-SVG), (5) journal/export contract.
- Data-integrity gate: never drop data rows to make a figure prettier; if rows are dropped, record before/after counts + reason.
- Missing evidence: write a placeholder + list it under `Assumptions or missing inputs:`; **never fabricate**.

## 7. Boundary of the Single-Agent Pipeline (边界性声明)

| In scope (single agent MUST do) | Out of scope (correctly OUT / deferred) |
|---------------------------------|-----------------------------------------|
| Full 21-phase loop on one Q-id | Multi-model cross-family adjudication (approx. via external-review perspective only) |
| Literal/sub-symbolic/numerical fidelity tri-split | GPU training / long background experiment arbitration (OSS emits predicted/falsifiable output) |
| Universal cross-disciplinary idea + methodology | Fork the whole 4-pipeline discipline orchestration |
| Deterministic + LLM checks | Multi-agent fan-out infra (Feishu/sleep scheduling) |
| Any domain, one Q-id at a time | Auto-iterating over all 125 problems (human supplies Q-id) |

**Boundary rule**: when a sub-question is out of scope, record it in the phase output as `deferred` + one-line reason, and emit the closest valid in-scope artifact — never silently pretend.

## 8. Static/Dynamic Skill Layering (nature-skills principle, OSS adaptation)

Fixed contracts & default positions live in the head of each skill (always load). Deep per-domain reference material (template galleries, venue lists, failure catalogs) lives in `shared-references/` and is loaded on-demand by path — it is **not** inlined into a skill body. Adding a domain region = adding one shared-reference file + one manifest line, not growing every skill.

---
**Single source of truth**: this file is the canonical home of the above cross-cutting rules. Consuming skills must pointer-load it by path (e.g. `[methodology-and-context-contract](../../shared-references/methodology-and-context-contract.md)`) rather than re-asserting their own partial copies.