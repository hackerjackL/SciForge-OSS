---
name: auto-pipeline
version: 1.2.1
description: "SciForge-OSS autonomous 21-phase research pipeline: one scientific question → submission-ready paper. Idea discovery → theory derivation → experiments → logic/leakage audits → paper writing → compile → cross-model review → citation audit. v3.4 adds: human_skip=true (production-grade checkpoint skip), figure budget + composite/group figures, Reproducibility/Data Availability statements, LaTeX pipeline-leakage scrub gate. Invoke when the user wants a complete end-to-end research run on a specific problem or Q-id. Single-question per invocation (does not auto-iterate over all problems). Calls sub-skills (domain-learner, idea-discovery, novelty-check, universal-retrieval, theory-derivation, experiment-execution, leakage-audit, logic-verification, paper-writing, paper-compile, auto-review-loop, citation-audit) via use_skill during the run."
argument-hint: "[Q-id or research question] — effort: lite|balanced|max|beast, human_skip: true|false, test_mode: true|false"
type: orchestrator
role: single-question-research-orchestrator
---

# Auto Pipeline (SciForge-OSS — Single-Question, 21-Phase DAG Loop)

> **Status**: The **single entry orchestrator** for OSS. Executes a complete 21-phase DAG research loop on **one** question supplied by the human user's prompt. **OSS does NOT auto-iterate over all problems** — each invocation processes exactly one Q-id, end-to-end. The orchestrator does NOT execute research itself — it delegates each phase to the corresponding meta-skill or support skill, reads their outputs, and feeds the next phase.
>
> **Key OSS difference from main SciForge**: main SciForge's research-pipeline branches by discipline (economics / cs-ml / physics / general) into 4 parallel pipelines each with its own framework (AIM / SOTA / PNV / none) + reviewer persona. OSS has **no discipline branch** — one universal pipeline, the universal `senior-reviewer-agnostic` persona, and the agent's runtime reasoning handles domain-specific methodology.

## Quick Reference

- **Entry point**: `/auto-pipeline "Q001: problem description" — effort: max`
- **Scope**: single-question execution, 21-phase DAG loop, universal across all domains
- **Output**: complete paper (LaTeX/PDF) + all intermediate artifacts
- **Key**: single-question execution, does not iterate the problem index, human supplies the Q-id; Phase 2.5 falsification is mandatory; Phase 3→4 and Phase 5→6 require human approval
- **Optional flags**: `test_mode=true` (auto-waive the 2 human checkpoints for end-to-end stress testing — see TEST_MODE exemption below); `language=chinese`; `effort=lite|balanced|max|beast`

## Use When

Use this skill when the AI scientist needs to solve **one** user-supplied research problem end-to-end (fully autonomous research). This is the **only entry orchestrator** — it does not branch by discipline; it uses the DAG architecture to handle any scientific domain via universal meta-skills.

Typical prompts:
- "Solve Q001" / "Solve Q001: the origin and evolution of the universe"
- "run the full pipeline on Q042"
- "Run the complete research pipeline on Q015 for me"

**The human user supplies the specific Q-id** in the prompt. OSS does **not** auto-search the problem index or iterate over all questions. Each invocation = one Q-id = one complete pipeline run.

## Job

Orchestrate a complete 21-phase DAG research loop. The non-negotiable goals:
1. **Each question runs the complete loop** — no phase skipped, regardless of how simple the problem seems
2. **Each phase produces a verifiable artifact** — the pipeline is documented by output files, not promises
3. **Every citation is real** — the 3-layer anti-hallucination protocol is mandatory (see [`citation-discipline.md`](../../shared-references/citation-discipline.md))
4. **Every conclusion is logic-verified** — no unsupported assertion survives to the final paper
5. **The pipeline is self-correcting** — if any phase fails or produces WARN/FAIL, auto-fallback to the relevant prior phase (bounded 3 rounds)
6. **INV-G1 PROBLEM_ANCHOR_FREEZE** — the Q-id supplied by the human is frozen at Phase 0 and referenced in every downstream phase (see [`../invariant-check/SKILL.md`](../../support/invariant-check/SKILL.md))
7. **Domain signature propagation** — the domain signature is produced ONLY by Phase 1b (`/domain-learner`) and written to `refine-logs/domain-signature.json`, consumed by all downstream phases. See [`../shared-references/domain-signature-consumer.md`](../../shared-references/domain-signature-consumer.md).
8. **Domain learner is the source of truth** (v2.8) — Phase 1a (`/domain-signature`) is downgraded to OPTIONAL fast-path hint writing `domain-signature-hint.json`, consumed only by the learner as a prior. Phase 1b (`/domain-learner`) is MUST and the sole writer of `domain-signature.json`. This eliminates the rule-hardcoded signature failure mode.

## Domain Signature Propagation

The domain signature is the **central wiring mechanism** that makes domain adaptation automatic. **The learner (Phase 1b) is the single source of truth** — Phase 1a is an optional fast-path hint that the learner may consume as a prior, never the final signature.

```
Phase 1a: /domain-signature (OPTIONAL fast-path, rule-based hint)
     │  → writes refine-logs/domain-signature-hint.json (temporary hint, confidence may be < 0.7)
     │  → used only as a prior / cold-start seed for the learner; not consumed directly downstream
     ↓
Phase 1b: /domain-learner (MUST, literature-based learning)  ← single source of truth
     │  → learns domain characteristics from scratch from literature + seed papers
     │  → reads hint.json as a prior (if present) + corrects via autonomous literature retrieval
     │  → overwrites refine-logs/domain-signature.json (sole downstream consumption source)
     ↓
refine-logs/domain-signature.json (written ONLY by Phase 1b)
     ↓
Phase 2:  /idea-discovery        → reads signature → adjusts perspective weights
Phase 2.5: /adversarial-falsification → reads signature → loads domain failure modes + calibrates EG sub-dimension N/A judgments
Phase 2.5b: (Phase 5b EG) → reads signature → domain-specific EG sub-dimension weighting (Compute/N/A judgment)
Phase 3:  /novelty-check         → reads signature → adjusts evaluation weights
Phase 5:  /method-registry       → reads signature → adjusts hypothesis scoring criteria
Phase 6:  /verification-routing  → reads signature → routing decision (experiment-first default / theory-only exception / hybrid) → writes VERIFICATION_ROUTING.json, then dispatches Phase 6a/6b/6c
Phase 10: /result-to-claim       → reads signature → calibrates confidence
Phase 12: /paper-writing         → reads signature → selects writing style / citation format
```

**Key design (v2.8 — learner-first)**: Phase 1b is **mandatory** and is the only writer of `domain-signature.json`. Phase 1a is **optional** and writes a separate `domain-signature-hint.json` consumed only by the learner as a prior. This eliminates the "rule-hardcoded signature" failure mode: even when 1a's rules match cleanly, the learner still re-derives the signature from literature to catch rule mismatches. Each downstream skill reads `domain-signature.json` independently at startup. If the signature doesn't exist (learner failed), all skills use default behavior — the pipeline continues but flags reduced domain adaptation.

## Performance Optimizations

### Parallelization

Where possible, phases run in parallel to reduce wall-clock time:

| Parallel Group | Phases | Rationale |
|---------------|--------|-----------|
| **Group A** | Phase 2 (idea-discovery) + Phase 4 (universal-retrieval) | Literature search does not depend on idea generation output. **B1 hard serialization (v2.3)**: Phase 2 is split into two segments — Round 1 (idea generation) may run in parallel with Phase 4 literature retrieval; but **the novelty pre-screen (the novelty axis of the 6-axis) and the Round 2-4 evaluations MUST wait for Phase 4 to complete** (the novelty axis runs only once `literature/references.bib` is readable; pre-screening against an empty bib or acting first and reporting later is forbidden). If Phase 4 WARNs / returns empty literature, the novelty axis is marked `pending-literature` and recorded faithfully — never silently degraded to guessing. |
| **Group B** | Phase 11 (unified-plotting) + Phase 12 (paper-writing) | Figures can be generated while the paper is being written |
| **Group C** | Phase 7 (leakage-audit) + Phase 8 (logic-verification) | Both audits are independent |

### Incremental MCTS

MCTS iteration is optimized to avoid re-scoring already-clear ideas:

- **Round 1**: Score all 8-12 root nodes on the 6-axis idea-fit
- **Round 2**: Only re-score **borderline** ideas (0.4-0.6 score range). Clear PASS (≥ 0.6) and clear FAIL (< 0.4) are not re-scored
- **Round 3**: Only re-score child nodes of borderline ideas
- **Round 4**: Final selection from promoted ideas

**Estimated savings**: 4 rounds → ~2.5 rounds equivalent (40% reduction in MCTS cost)

### Early Exit Conditions

| Phase | If condition met | Action |
|-------|-----------------|--------|
| Phase 2 | 6-axis pre-screen: all ideas BLOCKED | Return immediately, no MCTS |
| Phase 3 | — | Adversarial falsification is MANDATORY — never skipped |
| Phase 10 | All claims reach symbolic fidelity | Skip Phase 14 (auto-review-loop) — no improvement needed |
| Phase 12 | No figures needed | Skip Phase 11 (unified-plotting)

### Context Economy & Boundary (single-agent) — v2.3

The single-agent full-pipeline configuration must obey the cross-cutting discipline in:
**[`shared-references/methodology-and-context-contract.md`](../../shared-references/methodology-and-context-contract.md)** — pointer-load, do NOT inline.

Non-negotiable for OSS runs (esp. multi-round / context-constrained):

1. **Bundle-out**: any ≥ 10-line prompt/instruction a phase produces is written to a bundle file (`refine-logs/<phase>.bundle.md`); the next phase is handed the **path**, not the blurb.
2. **Compact-forward**: before Phase 8 (logic) and Phase 12 (paper-writing), write a 20-40 line compact summary of the prior phase's decisive artifacts; base the downstream phase on that summary.
3. **Sufficiency stopping**: analysis sub-loops stop only when (mandatory fields assigned) ∧ (verdict stable 2 rounds) ∧ (marginal return ≤ 0). Persist `stopping_rule.satisfied` in every analysis output. Boundary: never "keep digging" as a habit; name the specific open question + the evidence that resolves it.
4. **Evidence-forcing**: every finding ships with `raw_stat`+`confidence`+`method`; data-features ≠ errors (never clean a real feature to prettify); analysis layer reports, never judges.
5. **Deterministic-first**: file-existence/field/threshold/SHA-256 checks run before any LLM judgment; frozen artifacts get a hash lock.
6. **Reviewer-only-raw-artifacts** (single-agent adaptation): pass paths+raw artifacts, not the executor's interpretation/leading conclusions.
7. **Boundary**: anything out of single-agent scope is written as `deferred` + one-line reason, and the closest valid artifact is emitted — never silently skipped. Human supplies the Q-id; OSS runs exactly one Q-id per invocation.

This section replaces ad-hoc instructions duplicated across skills; the contract file is the single source of truth.

```
Phase  0: load problem (freeze Q-id — INV-G1 anchor)
     │
Phase  1: problem understanding & decomposition (built-in reasoning) [MUST]
     │
     ├───────────────── DAG branch ─────────────────┐
     │                                             │
Phase  1a: /domain-signature domain feature extraction [OPTIONAL] ← v2.8 demoted to fast-path hint
     │  analyze problem text → extract domain hint (rule-based)    │
     │  writes refine-logs/domain-signature-hint.json  │
     │  (not consumed directly downstream; only a prior for Phase 1b)    │
     │                                             │
Phase  1b: /domain-learner domain learning [MUST] ← v2.8 promoted to single source of truth
     │  learn domain characteristics from scratch from literature + seed papers           │
     │  (literature search + seed paper analysis)   │
     │  read hint.json as prior + correct via autonomous retrieval      │
     │  writes refine-logs/domain-signature.json      │
     │  (sole downstream consumption source; learner confidence threshold 0.7)│
     │                                             │
Phase  2: /idea-discovery [DAG branch] [MUST] — 3-perspective ideas
     │  (theoretical / computational / qualitative)   │
     │  + MCTS iteration (4 rounds, 8-12 root nodes)           │
     │  + outputs verification_type (theory-only / computational / theory+experiment)
     │                                             │
Phase  2.5: /adversarial-falsification [falsification gate] [MUST]
     │  6-dimension attack: assumption scoring → counterexample construction → literature adversarial    │
     │  → analogy mapping → sandbox feasibility → engineering grounding → data availability │
     │  SURVIVE → continue; WEAKENED → fall back to Phase 2      │
     │  FALSIFIED → eliminated (record reason, does not enter derivation)     │
     │                                             │
     │  Phase 5a: OSS Sandbox Feasibility (can the sandbox run it)│
     │  Phase 5b: AI Engineering Grounding (can the AI be implemented)│
     │                                             │
Phase  3: /novelty-check [DAG gate] [MUST] — 4-dimension evaluation + elimination
     │  (novelty×0.45 + feasibility×0.25 + relevance×0.15 + engineering grounding×0.15)│
     │                                             │
     └ Forced human checkpoint: pick the final idea ─┘
     │
Phase  4: /universal-retrieval — literature survey + 3-layer anti-hallucination
     │
     ├── verification path branch (determined by verification_type) ────┐
     │                                                 │
     │  [theory-only]  → skip to Phase 8 (logic verification)         │
     │  [computational]       → Phase 5 → 6 → 7 → 8            │
     │  [theory+experiment]  → Phase 5 → 6 → 7 → 8            │
     │  (OSS has no experiment environment; the experiment part outputs verifiable predictions)      │
     │                                                 │
Phase  5: /method-registry — method binding + hash lock + forced human approval       ← new
     │
Phase  6: /verification-routing — verification routing decision [MUST]                ← v5.0
     │  read domain-signature.evidence_type + computability signals →
     │  experiment-first (default) / theory-only (exception: derivational ∧ no executable computation) / hybrid
     │  → writes refine-logs/VERIFICATION_ROUTING.json (route/evidence_type/reason)
     │  see shared-references/verification-routing.md
     │
Phase  6a: /theory-derivation — symbolic derivation + step-by-step machine verification [ROUTED]
     │  theory-only / hybrid → MUST (primary verification or parallel primary verification)
     │  experiment-first → OPTIONAL auxiliary (take it only if derivational structure exists; non-blocking, full-step SymPy not forced)
     │          ↻ on failure fall back to Phase 1 (max 3 rounds)
     │          (theory-only: engine=manual, marked [not machine-verified])
     │
     │  ── experiment execution layer (v2.0, v5.0 default primary verification) ──
     │
Phase  6b: /experiment-execution --stage=toy [ROUTED]                 ← v2.0/v5.0
     │  toy experiment: minimal scale (~20 rounds) verifies "is the idea direction right" (idea life-or-death verdict)
     │  (theory-only → SKIP; experiment-first/hybrid → MUST)
     │  foreground hard cap 5 minutes; estimated > 5 minutes → also dispatch to background (toy_bg)
     │  Gate: PASS → Phase 6c; FAIL → KILL-or-PIVOT decision (see experiment-execution
     │  from-0-to-1 stop protocol; triggered only when significantly negative and reproducible on ≥2 seeds; PIVOT budget ≤2)
     │  (judge the Gate after toy_bg completes; do not wait on the foreground)
     │
Phase  6c: /experiment-execution --stage=full --background [ROUTED]  ← v2.0/v5.0
     │  full experiment: background scheduling (tmux/nohup/systemd); execute the mandatory experiment matrix per method-registry §3
     │  (theory-only → SKIP; experiment-first/hybrid → MUST)
     │  Dispatch → return immediately, pipeline continues
     │  v5.1 completion criteria: on experiment completion read budget_floor from the Return payload —
     │  satisfied=false → verdict may only be IN_PROGRESS/BLOCKED; must not enter Phase 10
     │  ("do not declare completion before the minimum exploration budget is consumed"; completion_justification
     │  see experiment-execution Step 6 exploration budget floor)
     │
Phase  7: /leakage-audit — Type I logic leakage + Type IV escape audit
     │          ↻ CRITICAL falls back to Phase 5 (3-round callback cap)
     │          (theory-only: Type IV = NOT_APPLICABLE)
     │
     └── paths merge ─────────────────────────────────┘
     │
Phase  8: /logic-verification — 6-dimension logic consistency audit
     │          ↻ FATAL/CRITICAL fall back to Phase 6 (max 3 rounds)
Phase  9: /invariant-check — INV-G1 problem-anchor freeze verification                  ← new
     │
Phase 10: /result-to-claim — 3-fidelity claim gate                     ← new
     │  (symbolic / numerical / qualitative; primary result requires ≥ numerical)
     │
Phase 11: /unified-plotting — academic figures (optional, Morandi palette + Layer 2)
     │
Phase 12: /paper-writing — single-template writing (elsarticle)
     │
Phase 13: /paper-compile — LaTeX zero-warning zero-error compilation                    ← new
     │          ↻ anti-deadloop ladder (3 attempts per-warning → BLOCKED)
     │
Phase 14: /auto-review-loop — cross-model review + kill-argument anti-self-deception      ← new
     │          ↻ score < 6 falls back to Phase 6 (max 4 rounds)
     │
Phase 15: /citation-audit — final 3-layer citation verification                        ← new
     │
Phase 15.5: /publishability-score — publishability score (dim1 first-axis gate)     ← new v2.2
     │         produces PUBLISHABILITY_SCORE.json/md
     │
Phase 16: final assembly + artifact archival
```

**Fallback contract**: each phase failure falls back to the nearest prior phase (max 3 rounds). 3 failed rounds escalate to BLOCKED + `reason_code` (reuses the main repo's `paper-compile` E16 anti-deadloop ladder). **Never silently retry into round 4** — the 3-round cap is a hard constraint.

## Graceful Degradation Protocol

Not all phases apply to all problems. Each phase has a **mode** that determines behavior on failure:

| Mode | Meaning | On Failure |
|------|---------|------------|
| `[MUST]` | Required for all problems | 3-round fallback → BLOCKED |
| `[OPTIONAL]` | Skipped if not applicable | Log WARN, continue pipeline |
| `[CONDITIONAL]` | Depends on problem type | Check condition first; skip gracefully if not met |

### Phase Mode Table

| Phase | Mode | Condition |
|-------|------|-----------|
| 0: load problem | MUST | — |
| 1: problem understanding | MUST | — |
| 1a: domain-signature | OPTIONAL | v2.8 demoted to fast-path hint, outputs domain-signature-hint.json; disabled when the learner is unavailable |
| 1b: domain-learner | MUST | v2.8 promoted to single source of truth; reads hint.json as prior, outputs domain-signature.json |
| 2: idea-discovery | MUST | — |
| 2.5: adversarial-falsification | MUST | — |
| 2.5b: adversarial-falsification Phase 5b (EG) | MUST | ENGINEERING_GROUNDING.md mandatory; HEAVY/CONSTRAINED full output, READY simplified version |
| 3: novelty-check | MUST | — |
| 4: universal-retrieval | MUST | v2.2: non-skippable — must run even for theory-only (theory problems need a duplication check to avoid re-proving known results); access arxiv/s2/crossref via the mihomo proxy (rule mode) |
| 5: method-registry | MUST | — |
| 6: verification-routing | MUST | v5.0: routing decision at the Phase 6 entry → VERIFICATION_ROUTING.json (experiment-first default) |
| 6a: theory-derivation | ROUTED | v5.0: theory-only/hybrid → MUST; experiment-first → OPTIONAL auxiliary (non-blocking) |
| 6b: experiment-execution (toy) | ROUTED | v5.0: theory-only → SKIP; experiment-first/hybrid → MUST (idea life-or-death verdict, FAIL → KILL-or-PIVOT) |
| 6c: experiment-execution (full+bg) | ROUTED | v5.0: theory-only → SKIP; experiment-first/hybrid → MUST (background dispatch + mandatory experiment matrix) |
| 7: leakage-audit | MUST | — |
| 8: logic-verification | MUST | — |
| 9: invariant-check | MUST | — |
| 10: result-to-claim | MUST | — |
| 11: unified-plotting | MUST | v2.2: figures are not optional — every paper has at least 1 figure (architecture/result figure); when no data figures exist, draw at least 1 pipeline/concept figure |
| 12: paper-writing | MUST | — |
| 13: paper-compile | MUST | v2.2: zero-warning zero-error mandatory (non-waivable); real compile to PDF once texlive is installed |
| 14: auto-review-loop | MUST | v2.2: self-review mandatory (role rotation researcher→reviewer→adjudicator); score < 6 falls back to Phase 6/12 (max 4 rounds); can no longer be replaced by grounding-check |
| 15: citation-audit | MUST | — |
| 15.5: publishability-score | MUST | v2.2 new: final publishability score (primary axis = main experiment logic in place); produces PUBLISHABILITY_SCORE.json/md |
| 16: final assembly + cleanliness audit | MUST | v2.2: adds the project-architecture-contract cleanliness audit (orphan files / empty directories / README completeness) |

### Degradation Rules

1. **OPTIONAL phase fails** → Log WARN with reason, skip to next phase, continue pipeline
2. **MUST phase fails after 3 rounds** → BLOCKED, surface to human with complete failure trace
3. **CONDITIONAL phase** → Check condition before running. If condition not met, skip with WARN
4. **paper-compile** (v2.2: now MUST, zero-warnings non-negotiable) → zero-warning zero-error mandatory; real compile to PDF once texlive is installed; warnings non-waivable (the old degradable rule is abolished); still FAIL after the 3-attempt-per-warning anti-deadloop ladder → BLOCKED + human
5. **auto-review-loop** (v2.2: now MUST) → self-review mandatory, 3-round role rotation (researcher→reviewer→adjudicator); can no longer be replaced by grounding-check; score < 6 falls back to Phase 6/12 (max 4 rounds)
6. **unified-plotting** (v2.2: now MUST) → every paper has at least 1 figure (architecture/result/concept); when no data figures exist, draw 1 pipeline/concept figure (d2 or tikz)

## Quality Gates (Explicit Per-Phase)

| Phase | Gate condition | On failure |
|------|---------|---------|
| 0 | Q-id is clear, well-posed, and comes from the human prompt | Ask the user to clarify the Q-id; do **not** auto-search the problem index |
| 1 | Problem decomposes into formal statements | Ask the user to clarify the problem boundary |
| 2 | At least 1 idea generated (MCTS converges) | Relax perspectives and re-evaluate; further failure escalates to BLOCKED |
| 2.5 | Falsification attack: assumption health ≥ 6 OR no counterexample | WEAKENED → fall back to Phase 2 and regenerate; FALSIFIED → eliminated (record reason) |
| 2.5b | Engineering Grounding report output (Phase 5b): ENGINEERING_GROUNDING.md generated | Required output only for HEAVY/CONSTRAINED; BLOCKED eliminates (sub-dimension = 0)
| 3 | DAG converges to 1 survivor (≥ 0.6 idea-fit) | Relax strictness and re-evaluate; further failure escalates to BLOCKED |
| — | **Forced human approval**: pick the final idea from the survivors | Wait for human confirmation; the agent cannot self-select |
| 4 | Literature search complete + 3-layer verification passed + screening-chain (truth+completeness) integrity check PASS | v2.2: **non-skippable** — must run even for theory-only (theory problems need a duplication check to avoid re-proving known results); if empty WARN but continue (literature requires manual remediation); screening-chain check: every reference has ≥ 1 verification layer + no orphan references + references cover the core claims |
| 5 | Method registry built + hash lock + **forced human approval** | Ask the user to approve Section 3; the agent cannot self-approve |
| 6 | SymPy derivation succeeds + step-by-step machine verification PASS | Fall back to Phase 1 (max 3 rounds) |
| 6b | Toy experiment RESULT.json status=PASS + core_claim_validated=true | **v5.1**: FAIL → KILL-or-PIVOT decision (triggered only when significantly negative and reproducible on ≥2 seeds: PIVOT back to Phase 5 to re-register the method (budget ≤2) / KILL → kill argument → back to Phase 2 for a new idea); TIMEOUT/ERROR → 1 retry; INCONCLUSIVE → 1 redesign retry |
| 6c | Full experiment DISPATCH.json generated + background process launch confirmed + **v5.1 budget_floor.satisfied** (route exploration ≥2 or veto evidence + 100% matrix + full seed quota + failure traces + completion_justification) | No background method available → BLOCKED; launch failure → 1 retry; theory-only → SKIP; budget_floor not satisfied → IN_PROGRESS (keep exploring; must not enter Phase 10) |
| 6c-BA | Full experiment complete and STATUS.json verdict=FAIL (toy previously PASSed) | **v2.2.1 BA**: fall back to Phase 2 to regenerate ideas (bounded 2 rounds) — see [idea-discovery BA mechanism](../../meta-skills/idea-discovery/SKILL.md) |
| 7 | Type I has no CRITICAL + Type IV has no ESCAPE | CRITICAL → callback to Phase 5 (3-round cap); further failure escalates to BLOCKED + LOGIC_GAP_FUNDAMENTAL_ISSUE |
| 8 | 6-dimension logic audit PASS (zero FATAL/CRITICAL) | FATAL/CRITICAL fall back to Phase 6 (max 3 rounds); **FATAL = experimental data contradicts derivation conclusions → v2.2.1 BA back to Phase 2** (bounded 2 rounds) |
| 9 | INV-G1 Q-id frozen + referenced in the current artifacts | FAIL → re-anchor the Q-id (Phase 0) |
| 10 | At least 1 primary result reaches ≥ numerical fidelity | qualitative-only → reframe as conjecture; numerical missing → fall back to Phase 6 |
| 11 | (optional) figures follow the Morandi palette + Layer 2 data heatmaps | Palette violation → regenerate; non-data figures not enforced |
| 12 | Paper non-empty + unified elsarticle template + all citations come from the verified list | If empty fall back to Phase 1; template violation falls back to Phase 12 |
| 13 | LaTeX compiles zero-warning zero-error (submission grade) | Anti-deadloop ladder: 3 attempts per-warning → BLOCKED + reason_code |
| 14 | Cross-model review score ≥ 6/10 + kill-argument anti-self-deception PASS | Score < 6 falls back to Phase 6 (max 4 rounds); anti-self-deception FAIL falls back to Phase 10; **kill-argument holds (claim refuted by its own experiments) → v2.2.1 BA back to Phase 2** (bounded 2 rounds) |
| 15 | All references pass the 3-layer anti-hallucination verification | Fail → delete fabricated references + fall back to Phase 4 and re-search |
| 16 | Artifact archive complete | Missing artifact → fall back to the relevant phase |

## Fallback Contract (Bounded 3 Rounds, Universal)

For every phase with a fallback arrow (↻):

```
Round 1: apply the standard fix for the failure type
Round 2: if the same failure persists, escalate the fix approach
Round 3: if the same failure STILL persists, emit BLOCKED + reason_code
         ─ surface to the human user with the exact failure + attempted fixes
         ─ do NOT silently retry past round 3
```

**The 3-round cap applies per-failure-type, not per-phase.** A phase with 3 distinct failure types gets up to 9 fix attempts total before BLOCKED, not 3.

Only the human user can waive a failure past round 3; the orchestrator never self-waives.

## Required Workspace

On successful completion, the orchestrator produces the following structure under `{problem_id}/` (21-phase trail). **v2.2**: the full GitHub-style layout, README.md/MANIFEST.md contracts, workspace-hygiene rules, and the Phase 16 cleanliness audit are defined in [`project-architecture-contract.md`](../../shared-references/project-architecture-contract.md) — that contract applies to every run (auto-pipeline OR partial skill invocation). Summary tree:

```
{problem_id}/
├── PIPELINE_STATUS.md           ← execution report (21-phase trail)
├── refine-logs/
│   ├── FINAL_PROPOSAL.md        ← frozen Q-id + selected idea (Phase 2)
│   ├── IDEA_CANDIDATES.md       ← ranked idea list (Phase 2)
│   ├── IDEA_DAG.json            ← DAG structure (Phase 2) — renderable as a Mermaid visualization
│   ├── IDEA_DAG_VISUAL.md       ← DAG visualization report (Mermaid format, Phase 2)  ← new
│   ├── ENGINEERING_GROUNDING.md ← Engineering Grounding report (Phase 5b)  ← new v2.9
│   └ MCTS_LOG.md                ← MCTS iteration log (Phase 2)
├── refine-logs/
│   └ novelty_report.json        ← 4-axis evaluation (Phase 3)
│   └ survivor.md                ← the surviving idea (Phase 3)
├── literature/
│   ├── landscape_report.md      ← literature survey (Phase 4)
│   ├── references.bib           ← verified BibTeX (Phase 4)
│   └ VERIFICATION_LOG.md        ← citation verification log (Phase 4)
├── methods/
│   ├── METHOD_REGISTRY.md       ← 8-section registry (Phase 5)
│   ├── REGISTRY_HASH.txt        ← SHA256 of Section 3 (Phase 5)
│   ├── APPROVAL_LOG.txt         ← human approval log (Phase 5)
│   ├── METHOD_BINDING.md        ← derived binding (Phase 5)
│   └ OUTCOME_CLASSIFICATION.md  ← primary/secondary outcomes (Phase 5)
├── derivations/
│   └ {problem_id}/
│       ├── premises.md          ← frozen assumptions (Phase 6)
│       ├── derivation.py        ← SymPy script (Phase 6)
│       ├── derivation_output.md ← derivation report (Phase 6)
│       └ verification_report.md ← SymPy verification (Phase 6)
├── experiments/                  ← v2.0 experiment execution layer
│   ├── toy/
│   │   └ session_{timestamp}/
│   │       ├── toy_experiment.py ← agent-written toy script (Phase 6b)
│   │       ├── RESULT.json       ← toy gate verdict (Phase 6b)
│   │       └ experiment_plan.json ← toy design rationale (Phase 6b)
│   └ full/
│       ├── {experiment_id}.py    ← agent-written full script (Phase 6c)
│       ├── FULL_EXPERIMENT_DISPATCH.json ← background dispatch metadata (Phase 6c)
│       ├── STATUS.json           ← periodic status from background job
│       ├── {experiment_id}.log   ← stdout/stderr log
│       ├── {experiment_id}.pid   ← PID file (nohup mode)
│       └ checkpoints/            ← intermediate checkpoints
├── audit_report/
│   ├── LOGIC_VERIFICATION.md    ← 6-dim logic audit (Phase 8)
│   ├── LOGIC_VERIFICATION.json  ← machine-readable verdict (Phase 8)
│   ├── LEAKAGE_AUDIT.md         ← Type I + Type IV audit (Phase 7)
│   ├── LEAKAGE_AUDIT.json       ← machine-readable verdict (Phase 7)
│   ├── INVARIANT_CHECK.md       ← INV-G1 freeze check (Phase 9)
│   ├── INVARIANT_CHECK.json     ← machine-readable verdict (Phase 9)
│   └ Type_I.md / Type_IV.md     ← per-lens detail (Phase 7)
├── CLAIMS_FROM_RESULTS.md       ← 3-fidelity claim gate output (Phase 10)
├── figures/
│   └ FIGURE_INDEX.md            ← figure index (Phase 11)
│   └ {figure_name}/             ← per-figure output + preserved source (Phase 11)
├── paper/
│   ├── main.tex                 ← unified elsarticle template (Phase 12)
│   ├── math_commands.tex        ← shared notation (Phase 12)
│   ├── references.bib           ← symlink to literature/references.bib (Phase 12)
│   ├── sections/*.tex           ← section sources (Phase 12)
│   ├── figures/                 ← symlink to figures/ (Phase 12)
│   └ main.pdf                   ← compiled PDF (Phase 13)
│   └ compile.log                ← compilation log (Phase 13)
│   └ COMPILE_REPORT.json        ← compile verdict (Phase 13)
├── review-stage/
│   ├── AUTO_REVIEW.md           ← cross-model review log (Phase 14)
│   ├── REVIEW_STATE.json        ← recovery state (Phase 14)
│   └ PUBLISHABILITY_SCORE.json  ← publishability score (Phase 15.5)  ← new
│   └ PUBLISHABILITY_SCORE.md    ← human-readable score report (Phase 15.5)  ← new
│   └ REVIEW_LEDGER.json        ← machine-readable ledger (Phase 14)
├── citation_audit/
│   └ CITATION_AUDIT.md          ← 3-layer citation audit (Phase 15)
│   └ CITATION_AUDIT.json        ← machine-readable verdict (Phase 15)
└── output/
    └ FINAL_ARTIFACTS.md         ← archive index (Phase 16)
```

## Phase Boundaries

**The orchestrator is structural, not substantive.** It does NOT:
- Assess methodology quality (that's `/leakage-audit`'s job)
- Assess whether claims are supported (that's `/result-to-claim`'s job)
- Assess whether the paper is well-written (that's `/auto-review-loop`'s job)
- Make subjective judgments about "interestingness" or "impact"

The orchestrator DOES:
- Route each phase to the correct skill
- Read each skill's output verdict
- Apply the explicit quality gate for the phase boundary
- Trigger fallback when a phase FAILs or WARNs
- Surface BLOCKED to the human user (never silently retry past round 3)
- Rewrite `verdicts/PIPELINE_VERDICT_SUMMARY.md` at EVERY phase boundary — the aggregated overview of all verdicts currently in `verdicts/` (per output-protocol Unified Verdict Principles #3); the human and downstream skills read pipeline verdict state from this one file

## 6-State Verdict Schema

**Constraint Re-injection (v5.1 — from CRUX shadow-evaluation failure mode #5)**:

**Background** (arXiv:2607.27191): for hard rules such as minimum exploration time, review cadence, and page limits, agents recite them verbatim early on but **gradually forget** them over six-day long-horizon runs — "long-term goal management remains the Achilles' heel of large models". Context compression and long-horizon runs naturally erode constraint memory; constraints must be re-injected structurally, not left to the agent remembering on its own.

**Mandatory mechanism** (the orchestrator executes it at every phase boundary, writing to `logs/pipeline.log`):
1. **Hard-constraint list re-read**: at every phase boundary, the orchestrator re-reads and explicitly recites the following hard-constraint list into the current context (not a summary — a verbatim recitation): verification routing (the route from VERIFICATION_ROUTING.json), exploration budget floor (the five budget_floor checks), page-tier cap (length tier), mandatory experiment matrix (the group list from EXPERIMENT_MATRIX.json), remaining PIVOT budget (current remainder of ≤2), negative-result discipline (polarity rules), **global run budget (RUN_BUDGET.json current usage vs limits, v5.3)**
1b. **Verdict schema validation (v5.3)**: at every phase boundary and at wrap-up, run `python3 scripts/validate_verdicts.py {problem_id}/verdicts/` (contract: [output-protocol.md](../../shared-references/output-protocol.md) §Verdict Schema Enforcement) — misspelled or missing-field registered verdicts are caught here; under `--strict`, violations are treated as BLOCKED
2. **Drift detection**: every phase's output artifacts must carry the hard-constraint fields they consume/produce (e.g., CLAIMS_FROM_RESULTS.md carries evidence_sufficiency, REVIEW_STATE.json carries response_class, compile artifacts carry the page-count verdict) — a missing field downgrades that phase's verdict to WARN (`constraint_field_missing`); the same field class missing in 2 consecutive phases → BLOCKED, surfaced to the human (this is a structural signal of instruction drift)
3. **Completion-declaration interception**: whenever any phase declares completion (PASS), the orchestrator checks that the phase's hard-constraint fields are complete and met — incomplete → the PASS is not accepted; downgrade to IN_PROGRESS and require completion. This is the structural interceptor for "I'm done" declarations

The orchestrator uses the 6-state machine defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md) for each phase boundary:

| State | Meaning | Orchestrator action |
|-------|---------|---------------------|
| `PASS` | Phase complete, proceed | Advance to next phase |
| `WARN` | Phase complete with caveat | Proceed, but log the caveat + ensure downstream addresses it |
| `FAIL` | Phase failed | Trigger fallback (bounded 3 rounds) |
| `NOT_APPLICABLE` | Phase doesn't apply (e.g., Phase 11 if no figures needed) | Skip (treat as PASS) |
| `BLOCKED` | Prerequisite missing OR fallback exhausted | Halt + surface to human |
| `ERROR` | Skill itself failed | Halt + surface to human |

The overall pipeline verdict = the **worst** verdict across all 21 phases: `ERROR > BLOCKED > FAIL > WARN > NOT_APPLICABLE > PASS`.

## Loop-Back Integrity Registry (v5.2 — Loop-Back Registry, guards against "broken chains")

**Field feedback**: whether a chain is broken must not rely on memory — it must rely on structure. This table is the **single authoritative list of all loop-backs** — every phase's FAIL/WARN exit, loop-back target, budget, and exhaustion exit must be registered here; any new phase or loop-back must update this table in sync, and the orchestrator checks against this table at every phase boundary (an off-table loop-back = contract violation).

| # | Trigger point | Trigger condition | Loop-back target | Action | Budget | Exhaustion exit |
|---|--------|---------|---------|------|------|---------|
| L1 | Phase 2.5 | WEAKENED | Phase 2 | idea regeneration | 3 rounds | BLOCKED, surfaced to human |
| L2 | Phase 2.5 | FALSIFIED | — | record idea elimination in failed_ideas.json, continue evaluating the next candidate | 1 per idea | all candidates eliminated → BLOCKED |
| L3 | Phase 3 | no survivor | Phase 3 | relax strictness and re-evaluate | 1 round | BLOCKED |
| L4 | Phase 5 | hash lock mismatch | Phase 5 | rebuild registry | 3 rounds | BLOCKED |
| L5 | Phase 6b toy | FAIL (significantly negative and reproducible on ≥2 seeds) | **PIVOT → Phase 5** (re-register with a new method + re-lock the hash) or **KILL → Phase 2** (kill argument, then a new idea) | PIVOT: method redesign; KILL: idea rebirth | PIVOT ≤2 times; KILL goes through BA | PIVOT exhausted → forced KILL; BA exhausted → BLOCKED + BA_EXHAUSTED |
| L6 | Phase 6b toy | TIMEOUT/ERROR | Phase 6b | rescale/fix and re-run | 1 each | BLOCKED |
| L7 | Phase 6c-BA | full FAIL and toy previously PASSed | Phase 2 | idea regeneration | BA ≤2 rounds | BLOCKED + BA_EXHAUSTED |
| L8 | Phase 7 | CRITICAL | Phase 5 | method patch | 3 rounds | BLOCKED + LOGIC_GAP |
| L9 | Phase 8 | FATAL/CRITICAL | Phase 6 | derivation fix | 3 rounds | FATAL = data contradicts conclusions → BA back to Phase 2 (≤2 rounds) |
| L10 | Phase 14 | score <6 | Phase 6 | evidence reinforcement | 4 rounds | BLOCKED |
| L11 | Phase 14 | kill-argument holds | Phase 2 | BA idea rebirth | BA ≤2 rounds | BLOCKED + BA_EXHAUSTED |
| L12 | Phase 13 | page-overflow FAIL | Phase 12 | cut content and recompile | until the page limit is met | nothing left to cut → drop a length tier and re-layout |
| L13 | Anti-shrinkage | 3 consecutive rounds without substantive response | Phase 2 | forced KILL path | — | BLOCKED |

**Loop-back discipline (hard rules)**:
1. **Every loop-back must carry a budget**: a budgetless loop-back = a breeding ground for deadloops; budget exhaustion must have an **explicit non-loop-back exit** (BLOCKED surfaced to the human, or an elimination record) — verbal relaxations like "one more round" are forbidden
2. **Loop-backs must change state**: a phase re-entered via loop-back must consume the evidence of the previous failure (failed_ideas.json / KILL_ARGUMENT.json / the response_class from REVIEW_STATE.json) — re-running the same input unchanged is forbidden (anti-deadloop)
3. **KILL paths must go through kill-argument**: any "switch idea" decision must first produce KILL_ARGUMENT.json (verdicts/) — switching ideas without a kill argument is drift, not stop-loss (the INV-G1 content hash will intercept it)
4. **BA budget is globally shared**: the three BA trigger points L7/L9/L11 share a total budget of ≤2 rounds (from v5.3, accounted in `ba_rounds_used`/`ba_rounds_max` of `verdicts/RUN_BUDGET.json`; the old `verdicts/BA_BUDGET.json` is a read-only fallback) — not 2 rounds each — preventing three BAs from stacking into 6 idle rounds
5. **KILL requires a human checkpoint (v5.3, default ON)**: on any KILL path (L5/L7/L9/L11/L13), after the kill-argument produces `verdicts/KILL_ARGUMENT.json` and before returning to Phase 2 to regenerate ideas, the orchestrator must pause and present the kill-argument summary to the human, awaiting confirmation; fully automatic only when the invocation carries `kill_checkpoint=false` or `human_skip=true`. The checkpoint record is written to `APPROVAL_LOG.txt` (see the Boundaries section)

## Global Run Budget Ledger (v5.3 — RUN_BUDGET.json)

**Why**: loop-back budgets (PIVOT ≤2, BA ≤2) cap *rounds*, but nothing capped the two resources that actually kill long runs — wall-clock time and API cost. A run can sit under every round cap and still burn for a week (or, conversely, stall forever consuming nothing). The ledger gives every run an aggregate ceiling with a structural cut-off.

**Ledger**: `verdicts/RUN_BUDGET.json` (schema: [`schemas/RUN_BUDGET.schema.json`](../../shared-references/schemas/RUN_BUDGET.schema.json)). Initialized by the orchestrator at Phase 0, updated at EVERY phase boundary, absorbing the old `verdicts/BA_BUDGET.json` accounting (read the old file as fallback for pre-v5.3 workspaces, never write it):

```json
{
  "schema_version": "1.0", "run_id": "Q042", "started_at": "2026-08-09T01:00:00Z",
  "wall_clock_seconds": 0, "api_cost_usd": 0.0,
  "pivot_count": 0, "ba_rounds_used": 0, "ba_rounds_max": 2,
  "per_phase": {}, "limits": {"wall_clock_seconds_max": 172800, "api_cost_usd_max": 40.0, "pivot_count_max": 2}
}
```

**Default limits by effort level** (human may override in `AGENT_DOC.md` at Phase 0 — record the override in `logs/pipeline.log`):

| effort | wall_clock_seconds_max | api_cost_usd_max | pivot_count_max | ba_rounds_max |
|--------|------------------------|------------------|-----------------|---------------|
| lite   | 43 200 (12 h)          | 10.0             | 2               | 2             |
| balanced | 172 800 (48 h)       | 40.0             | 2               | 2             |
| max    | 345 600 (96 h)         | 120.0            | 2               | 2             |
| beast  | 864 000 (240 h)        | 400.0            | 2               | 2             |

**Boundary protocol** (orchestrator, every phase boundary, in order):
1. **Account**: `wall_clock_seconds` = now − `started_at`; `api_cost_usd` += phase estimate (when the runtime exposes token/cost accounting; otherwise keep last value and set `per_phase.<n>.cost_estimated: true`); increment `pivot_count`/`ba_rounds_used` when L5-PIVOT / BA loop-backs fire; append `per_phase.<n>` entry (duration, cost, verdict).
2. **Check**: any of `wall_clock_seconds ≥ wall_clock_seconds_max`, `api_cost_usd ≥ api_cost_usd_max`, `pivot_count > pivot_count_max`, `ba_rounds_used > ba_rounds_max` → **stop**: write the ledger, emit `PIPELINE_STATUS.json` event `verdict: BLOCKED, reason_code: budget_exhausted_<resource>`, surface to the human with usage-vs-limit table and a recommendation (extend limit / archive partial results / abandon). Only the human can raise a limit — the orchestrator never self-extends.
3. **Log**: one ledger-update line to `logs/pipeline.log` (usage + remaining) — budget accounting is itself auditable.

**Anti-gaming**: an agent cannot hold a phase open to dodge wall-clock accounting (the ledger is written by the orchestrator at boundaries from the clock, not from the phase's self-report), and `api_cost_usd` may only increase — corrections are additive notes, never downward rewrites.

## Anti-Deadloop Escalation (Universal, reused from paper-compile E16)

The bounded 3-round fallback is itself bounded by a hard escalation ladder. Do NOT loop on the same failure for more than 2 fix attempts:

1. **Attempt 1**: apply the standard fix for the failure type
2. **Attempt 2**: if the same failure persists, escalate the fix approach (different method, broader scope, alternative tool)
3. **Attempt 3 (BLOCKED)**: if the same failure STILL persists after a different fix attempt, emit `PIPELINE_STATUS.json` with `verdict: BLOCKED, reason_code: unresolved_<phase>_<failure_type>, attempts: 3` and surface to the human user with the exact failure, the attempted fixes, and a recommendation. **Do NOT silently retry past attempt 3.**

The 3-attempt cap applies per-failure-type, not per-phase. A phase with 5 distinct failure types gets up to 15 fix attempts total before BLOCKED, not 3.

Only the human user can waive a failure past attempt 3; the orchestrator never self-waives.

## Boundaries

- **Single-question execution only.** Each invocation processes exactly one Q-id supplied by the human user. Do NOT auto-iterate over all questions. Do NOT auto-search the problem index for "what to solve next" — the human decides.
- **No discipline branch.** OSS has one universal pipeline. Do not reintroduce economics / cs-ml / physics / general parallel pipelines or their frameworks (AIM / SOTA / PNV). The agent's runtime reasoning in `/theory-derivation` + `/dynamic-sandbox` handles domain-specific methodology.
- **Paradigm selection.** The agent selects the appropriate paradigm (formal/empirical/interpretive/design) in Phase 1 based on the problem's nature, not by domain label. See [`discipline-paradigm.md`](../../shared-references/discipline-paradigm.md).
- **INV-G1 is non-negotiable.** The Q-id is frozen at Phase 0 and must be referenced in every downstream phase. If any phase's output lacks the Q-id reference, Phase 9 (`/invariant-check`) BLOCKs.
- **Forced human checkpoints at Phase 3→4 and Phase 5→6.** The agent cannot self-select the final idea (Phase 3) or self-approve the method registry (Phase 5). Wait for human confirmation.
  - **`human_skip=true` — explicit production-grade skip (v3.4 — NEW).** When the invocation carries `human_skip=true` (set by the human who has decided to delegate BOTH checkpoints to the agent for this run), the 2 human checkpoints are **explicitly skipped at production grade**: the agent performs the EQUIVALENT work each checkpoint guards (selects the top MCTS survivor as the final idea; builds the method registry + hash lock), and records the skip in `APPROVAL_LOG.txt` with `skipped_by=human_skip, original_checkpoint=Phase 3→4 / Phase 5→6, agent_action_taken=auto-selected/auto-approved, human_decision=EXPLICIT_SKIP`. Unlike `test_mode`, `human_skip` is a **production-grade decision** — `PIPELINE_STATUS.json` flags `checkpoints_skipped: true, production_ready: true, skip_authority: human_explicit` (NOT `production_ready: false`). The human has made an informed choice to delegate; the run is production-ready with that choice recorded. All other phases (INV-G1, fallback cap, toy gate, background dispatch, zero-warnings compile, leakage scrub) remain HARD even with `human_skip`. Use `human_skip=true` when the human trusts the agent's idea-selection + method-registry judgment for this run; use `test_mode=true` only for mechanical stress-testing where the human intends to later confirm.
  - **TEST_MODE checkpoint bypass (v2.2 — bypass, not skip).** When the invocation carries `test_mode=true` (set by the human for autonomous end-to-end stress testing), the 2 human checkpoints are **bypassed, NOT skipped**: the agent still performs the EQUIVALENT work each checkpoint guards (selects the top MCTS survivor as the final idea; builds the method registry + hash lock), but records the bypass in `APPROVAL_LOG.txt` with `bypassed_by=test_mode, original_checkpoint=Phase 3→4 / Phase 5→6, agent_action_taken=auto-selected/auto-approved, human_review_status=PENDING_DEFERRED`. The bypass is **provisional** — `PIPELINE_STATUS.json` flags `checkpoints_bypassed: true, human_review_deferred: true, production_ready: false` so a human MUST later confirm both decisions before the run is considered production-grade. The work the checkpoint guards is done (idea selected, method registry built) — only the human-approval step is deferred, never the underlying quality control. All other phases (INV-G1, fallback cap, toy gate, background dispatch, zero-warnings compile) remain HARD even in TEST_MODE. TEST_MODE is for stress-testing the pipeline mechanics; production runs MUST keep both checkpoints human-gated with no bypass.
  - **`human_skip` vs `test_mode` (when to use each)**:
    - `human_skip=true` — human has **decided** to delegate both checkpoints, run is production-grade, no later confirmation needed. Use for autonomous production runs where the human trusts the agent's judgment.
    - `test_mode=true` — human is **stress-testing** the pipeline mechanics, run is NOT production-grade, later confirmation required. Use for testing/debugging the pipeline itself.
    - Neither flag — both checkpoints are human-gated (wait for explicit confirmation at Phase 3→4 and Phase 5→6). The default, and the safest.
- **KILL decisions have a human checkpoint (v5.3 — DEFAULT ON).** Killing an idea (KILL → back to Phase 2 for a new idea; loop-back rows L5/L7/L9/L11/L13) silently reshapes the whole run — an autonomous pipeline can cycle through several ideas overnight with the human none the wiser. Therefore: after `/kill-argument` produces `verdicts/KILL_ARGUMENT.json`, the orchestrator PAUSES and presents the kill case (strongest rejection paragraph + still_unresolved list + which loop-back fired) to the human, and proceeds to idea regeneration only after explicit human confirmation. Reuses the existing delegation knobs:
  - `human_skip=true` — the KILL checkpoint is skipped along with the two phase checkpoints (same `APPROVAL_LOG.txt` recording: `skipped_by=human_skip, original_checkpoint=KILL-confirmation`).
  - `kill_checkpoint=false` — explicit opt-out for this checkpoint only (recorded: `skipped_by=kill_checkpoint_optout`).
  - Neither — checkpoint ON (default): the pipeline waits. A KILL executed without the required confirmation is a contract violation; the next phase boundary MUST detect the missing `APPROVAL_LOG.txt` entry and BLOCK.
- **3-round fallback limit is hard.** Do not exceed 3 rounds on the same failure type. If exhausted, BLOCK + surface to human.
- **The orchestrator never executes research.** It delegates to the corresponding skill. Do not inline derivation / verification / writing logic into this orchestrator.
- **Theory-only verification path.** When `verification_type=theory-only` (pure theory, no code/experiment):
  - Phase 5 (method-registry) → Phase 6 (theory-derivation with `engine=manual`) → Phase 6b/6c (SKIP) → Phase 7 (Type IV = NOT_APPLICABLE) → Phase 8 (logic-verification)
  - Phase 10 (result-to-claim): qualitative fidelity is the expected norm for theory-only problems
  - The derivation output is marked `[not machine-verified]` and the claim strength is adjusted accordingly
- **Experiment execution path (v2.0).** When `verification_type` is NOT `theory-only`:
  - Phase 6 (theory-derivation) → Phase 6b (toy experiment) → Phase 6c (full experiment, **background dispatch mandatory**) → Phase 7+ (pipeline continues, experiment runs async)
  - **Toy dispatch rule (v2.1)**: estimate toy wall-clock first. `≤ 5 min` → run foreground. `> 5 min` → dispatch to background as `toy_bg` (same dispatch protocol as full), continue pipeline. The toy gate verdict (PASS/FAIL from `RESULT.json`) is read **at the Phase 6c dispatch boundary** — if `toy_bg` is still running when the pipeline reaches 6c, the orchestrator **skips 6c** (no full experiment dispatched yet) and continues with Phase 7+ for non-experiment work; the toy verdict is re-checked at Phase 10 alongside other live background jobs. Never busy-wait at 6c for `toy_bg`.
  - Toy experiment FAIL → **kill the idea** (BLOCKED, do not proceed to full experiment). This holds whether toy ran foreground or background.
  - Full experiment dispatched to background → pipeline continues with Phase 7-16 while experiment runs
  - At Phase 10 (result-to-claim): check STATUS.json for whichever background jobs are live (toy_bg if still running, full if still running); if still running, use whatever completed results exist + note "experiment pending"
  - See [`../support/experiment-execution/SKILL.md`](../../support/experiment-execution/SKILL.md) and [`../shared-references/background-dispatch-protocol.md`](../../shared-references/background-dispatch-protocol.md)
- **Background dispatch is non-negotiable for full experiments.** The agent must NEVER block the foreground on tasks estimated > 5 minutes. See [`../shared-references/background-dispatch-protocol.md`](../../shared-references/background-dispatch-protocol.md).
- **HARD vs FLEXIBLE boundaries:**
  - **HARD (non-negotiable)**: INV-G1 freeze, forced human checkpoints (Phase 3→4, 5→6), KILL human checkpoint (v5.3, default ON; opt out only via `human_skip=true` or `kill_checkpoint=false`), 3-round fallback cap, toy gate FAIL = kill idea, background dispatch for full experiments, run-budget ledger limits (RUN_BUDGET.json, v5.3)
  - **FLEXIBLE (agent discretion)**: MCTS round count (default 4, may reduce if convergence is clear), experiment scale_ratio, toy experiment design, strictness thresholds, effort level

## Output Protocols
> **v5.2 verdict artifact location**: all machine-readable verdict/hash/audit JSON produced by this skill is written to `verdicts/` (see the artifact directory structure in [`output-protocol.md`](../../shared-references/output-protocol.md) for filenames; narrative reports stay in their original stage directories).


> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## See Also

- [`../shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md) — 6-state verdict schema
- [`../shared-references/idea-dag-schema.md`](../../shared-references/idea-dag-schema.md) — DAG node schema (Phase 2)
- [`../shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) — MCTS iteration protocol (Phase 2)
- [`../shared-references/multi-fidelity-evaluation.md`](../../shared-references/multi-fidelity-evaluation.md) — 3-fidelity filter (Phase 10)
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/effort-contract.md`](../../shared-references/effort-contract.md) — effort level definitions
- [`../shared-references/domain-adaptation-contract.md`](../../shared-references/domain-adaptation-contract.md) — TDAL 4-dim joint confidence locked schema (Phase 10 boundary)
- [`../shared-references/ouroboros-integration.md`](../../shared-references/ouroboros-integration.md) — Ouroboros basic (Phase 2.5 → D dim) + deep (Phase 6/10 → T dim uplift) integration
- [`../shared-references/domain-adaptive-pipeline.md`](../../shared-references/domain-adaptive-pipeline.md) — Phase 5/6/11 intensity override by evidence_type/paradigm (mid-term M1)
- [`../shared-references/confidence-uplift.md`](../../shared-references/confidence-uplift.md) — 3-mechanism bounded uplift loop when TDAL verdict ≤ WEAK (mid-term M2)
- [`../shared-references/pipeline-adaptive-degradation.md`](../../shared-references/pipeline-adaptive-degradation.md) — signature-driven phase mode override, replaces v2.7 static Phase Mode Table (mid-term M3)
- [`../shared-references/domain-contribution-protocol.md`](../../shared-references/domain-contribution-protocol.md) — open community PR channel for new evidence_types (long-term L1)
- [`../shared-references/competitive-drift-monitor.md`](../../shared-references/competitive-drift-monitor.md) — automated quarterly competitor drift tracking, keeps competitive-analysis.md current (long-term L3)
- [`../meta-skills/idea-discovery/SKILL.md`](../../meta-skills/idea-discovery/SKILL.md) — Phase 2
- [`../meta-skills/domain-signature/SKILL.md`](../../meta-skills/domain-signature/SKILL.md) — Phase 1a (rule-based signature)
- [`../meta-skills/domain-learner/SKILL.md`](../../meta-skills/domain-learner/SKILL.md) — Phase 1b (literature-based learning fallback)
- [`../meta-skills/universal-retrieval/SKILL.md`](../../meta-skills/universal-retrieval/SKILL.md) — Phase 4
- [`../meta-skills/unified-plotting/SKILL.md`](../../meta-skills/unified-plotting/SKILL.md) — Phase 11
- [`../support/method-registry/SKILL.md`](../../support/method-registry/SKILL.md) — Phase 5
- [`../support/theory-derivation/SKILL.md`](../../support/theory-derivation/SKILL.md) — Phase 6
- [`../support/experiment-execution/SKILL.md`](../../support/experiment-execution/SKILL.md) — Phase 6b (toy) + Phase 6c (full+background) [v2.0]
- [`../shared-references/background-dispatch-protocol.md`](../../shared-references/background-dispatch-protocol.md) — background dispatch protocol [v2.0]
- [`../support/leakage-audit/SKILL.md`](../../support/leakage-audit/SKILL.md) — Phase 7
- [`../support/logic-verification/SKILL.md`](../../support/logic-verification/SKILL.md) — Phase 8
- [`../support/invariant-check/SKILL.md`](../../support/invariant-check/SKILL.md) — Phase 9
- [`../support/result-to-claim/SKILL.md`](../../support/result-to-claim/SKILL.md) — Phase 10
- [`../support/paper-writing/SKILL.md`](../../support/paper-writing/SKILL.md) — Phase 12
- [`../support/paper-compile/SKILL.md`](../../support/paper-compile/SKILL.md) — Phase 13
- [`../support/auto-review-loop/SKILL.md`](../../support/auto-review-loop/SKILL.md) — Phase 14
- [`../support/citation-audit/SKILL.md`](../../support/citation-audit/SKILL.md) — Phase 15
- [`../support/quality-gate/SKILL.md`](../../support/quality-gate/SKILL.md) — final pre-writing gate (Phase 12 boundary)
- [`../support/kill-argument/SKILL.md`](../../support/kill-argument/SKILL.md) — Phase 14 anti-self-deception
