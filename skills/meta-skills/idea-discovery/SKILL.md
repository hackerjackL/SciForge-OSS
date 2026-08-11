---
name: idea-discovery
version: 1.5.0
description: "Generate 8-12 candidate research ideas via MCTS over a DAG, with 6-axis pre-screen (novelty/feasibility/relevance/tractability/data-readiness/EG) and v6.0 gap anchoring (every promoted idea cites a gap-id from literature/GAP_REPORT.md). Phase 2. Invoke after domain signature is ready, before novelty-check."
type: meta-skill
role: research-idea-generation
---

# Idea Discovery (SciForge-OSS — Discipline-Agnostic, MCTS-Enhanced)

> **Status**: Generates and pre-screens research idea candidates for a given research question. OSS merges main SciForge's `idea-creator` (MCTS iterative idea refinement + DAG node expansion) into this meta-skill. **OSS is discipline-agnostic** — there is no economics DiD/IV/RDD framing, no cs-ml SOTA framing, no physics PNV framing. The universal 4-perspective ideation (theoretical / computational / qualitative / empirical) + MCTS iteration applies to every problem.

## Quick Reference

- **Purpose**: Generate 8-12 ideas → 4 MCTS iteration rounds → select the best 1-3
- **Input**: Q-id + problem description supplied by the human + `literature/GAP_REPORT.md` (broad wave; v6.0 gap chain)
- **Output**: IDEA_DAG.json + FINAL_PROPOSAL.md + IDEA_DAG_VISUAL.md + GAP_ANCHOR_LOG.md
- **Key**: 4 perspectives (theoretical/computational/qualitative/empirical), 6-axis pre-screen, gap anchoring (v6.0), mandatory human approval

> **No legacy pilot fallback**: main SciForge's `idea-creator` has a legacy demo/pilot experimental fallback when MCTS produces 0 promoted ideas. OSS has **no legacy demo/pilot-experiment fallback** — the fallback is instead "re-run ideation with broader perspectives" (a demo run is never substituted for the real toy/full experiment gates).

## Use When

Use this skill when the user wants to generate and pre-screen research idea candidates for a research question.

Typical prompts:
- "Generate research ideas"
- "Idea discovery"
- "Brainstorm approaches"
- "Brainstorm research directions"
- "What are the possible approaches to this problem"
- "List potential methodologies"

## Job

Take a frozen research question (Q-id supplied by the human user's prompt) and produce a ranked list of 8-12 research idea candidates with:
1. Clear framing (theoretical / computational / qualitative perspective)
2. Pre-screened against the universal 6-axis idea-fit (novelty / feasibility / relevance / tractability / data-readiness / Engineering Grounding)
3. MCTS-iteratively refined (best ideas promoted across rounds)
4. DAG-structured (each idea is a node; dependencies encoded)

The non-negotiable goal: **never commit to a single idea before MCTS iteration completes — the first idea is rarely the best.**

## Required Workspace

Create or maintain:
- `refine-logs/IDEA_CANDIDATES.md` — the ranked list of idea candidates (primary output)
- `refine-logs/IDEA_DAG.json` — the DAG structure (nodes = ideas, edges = dependencies)
- `refine-logs/MCTS_LOG.md` — MCTS iteration log (rounds, promotions, rejections)
- `refine-logs/FINAL_PROPOSAL.md` — the selected idea after MCTS convergence (frozen for downstream skills)

Key artifacts consumed:
- The frozen Q-id + problem statement (supplied by the human user's prompt)
- `refine-logs/domain-signature.json` — from Phase 1b `/domain-learner` (the SOLE writer; used for perspective weight adjustment)
- `literature/references.bib` — from `/universal-retrieval` (for novelty pre-screen)
- `literature/GAP_REPORT.md` — from `/universal-retrieval` broad wave (v6.0 gap chain; MANDATORY for final scoring: every promoted idea must anchor to a gap-id)
- Sibling workspaces' `output/RUN_PREPRINT.md` archives (v1.4.0, when present in the parent run directory) — prior runs' discovered gaps / fired kill arguments / failure notes; an idea may anchor on a preprint gap-id (`PREPRINT:<run-id>#<gap>`) exactly like a literature gap-id — the system's own history is first-class anchoring evidence
- `data/` — from `idea-discovery` 6-axis pre-screening's data-readiness axis (built-in)

## Configuration

- **Max MCTS iterations** — 4 (default). Main SciForge uses 6; OSS uses 4 because the no-experiment setting means each iteration is cheaper (no pilot to run). Configurable.
- **Min root nodes** — 8 (default). The DAG starts with 8-12 root idea nodes; MCTS prunes to the best 3-5.
- **Perspectives** — 4 universal: `theoretical` (symbolic derivation), `computational` (numerical sanity check), `qualitative` (mechanism reasoning), `empirical` (causal-identification / data-driven estimation). The 4th `empirical` covers econometrics (DiD/IV/RDD), regression studies, and any problem whose core contribution IS an identification strategy or an estimator recovering a known parameter — it is NOT a symbolic derivation nor a numerical confirmation of a theorem. The `empirical` perspective emits `verification_type=computational` (it runs src/data) but its idea framing is "recover [causal parameter] via [identification strategy] under [assumption]" — distinct from `computational`'s "confirm [prediction] numerically."
- **Promotion threshold** — score ≥ 0.6 on the 6-axis idea-fit (see below).
- **Domain-adaptive perspectives** — If `refine-logs/domain-signature.json` exists, use the perspective weights from the signature instead of the default equal weights. See [`shared-references/domain-signature-consumer.md`](../../shared-references/domain-signature-consumer.md).

## The 6-Axis Idea-Fit Pre-Screen (Universal)

Every idea candidate is pre-screened against **6 axes** before MCTS promotion:

| Axis | What it checks | CONSTRAINED | BLOCKED |
|------|----------------|-------------|---------|
| Novelty | Does this approach appear in the existing literature? | Covered by > 3 papers in `references.bib` | Directly duplicated by a known paper |
| Feasibility | Can the SymPy derivation / numerical sanity check plausibly close the loop? | Requires contested assumptions | Mathematically impossible under stated assumptions |
| Relevance | Does this approach address the frozen Q-id's core question? | Tangential to the core question | Solves a different problem |
| Tractability | Is the derivation chain tractable within the OSS sandbox (SymPy + numpy)? | Requires non-standard compute | Requires GPU / long-running experiments OSS cannot run |
| Data-readiness | Are the required parameters / data available? | Requires data not in `data/` | Requires data that does not exist |
| **Engineering Grounding** | **Can the AI agent implement this idea? (see [EG contract](../../shared-references/engineering-grounding-contract.md))** | **EG average 3.0-5.9 (CONSTRAINED tier)** | **≥ 3 EG sub-dimensions = 0** |

**Hard filter**: any axis `BLOCKED` → idea is rejected before MCTS. `CONSTRAINED` axes are flagged but the idea proceeds to MCTS. The Engineering Grounding axis follows the [Engineering Grounding Contract](../../shared-references/engineering-grounding-contract.md) — HEAVY and CONSTRAINED ideas proceed to MCTS with labels; only **≥ 3 sub-dimensions = 0** triggers BLOCKED (v3.0 stricter rule: 1-2 sub-dimensions = 0 does NOT eliminate, instead produces an AI Mitigation Plan).

## MCTS Iteration Protocol

Follow [`shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) for the full contract. Summary:

1. **Round 1 (Expansion)**: Generate 8-12 root idea nodes across the 4 perspectives (theoretical / computational / qualitative / empirical).
2. **Round 2 (Selection + Simulation)**: Score each node on the 6-axis idea-fit (5 original + Engineering Grounding). **B1 literature dependency (v2.3, extended v6.0)**: the novelty axis depends on Phase 4's `literature/references.bib`, and — v6.0 gap chain — ALL final scoring additionally depends on `literature/GAP_REPORT.md` (broad wave): if either file is not yet ready, first mark `novelty=pending-literature` and suspend final verdicts, then re-score once the literature arrives. **Never issue a final BLOCKED/PASS verdict without references, and never promote an idea without a gap anchor** (generation-stage intuition may pre-screen feasibility/relevance — Round 1 brainstorming may run in parallel with the broad wave — but every final verdict waits for the literature). **Gap anchoring (v6.0)**: assign each surviving node a `gap_anchor` — the gap-id from GAP_REPORT.md whose statement the idea addresses (or the literal `exploratory` + one-line justification; exploratory slots are capped at 2 per round so serendipity survives without drowning the chain). A node with neither a gap-id nor a justified exploratory slot gets its relevance axis capped at 0.5 (cannot reach the 0.6 promotion threshold) — ideas untethered from any known gap are exactly the ones that become "thin results packaged as findings" (CRUX failure mode #1). Every anchoring decision (including re-anchoring after a targeted wave shows the gap was misread) is appended to `refine-logs/GAP_ANCHOR_LOG.md`. Select top 4-6 for simulation (light-weight derivation sketch — does SymPy plausibly close the loop?). Clear FAIL (< 0.4) are not re-scored; clear PASS (≥ 0.6) get a lightweight re-score (not full re-run) to confirm stability.
3. **Round 3 (Backpropagation)**: Promote ideas with simulation score ≥ 0.6. Reject ideas with simulation score < 0.4. For borderline (0.4-0.6), generate 2-3 child nodes (refined variants) and re-score.
4. **Round 4 (Final selection)**: From promoted ideas, select the top 1-3 for `FINAL_PROPOSAL.md`. The human user picks the final one (forced checkpoint).

**0 promoted ideas fallback**: If after 4 rounds no idea reaches the promotion threshold, do NOT fall back to a legacy demo/pilot (main SciForge's path). Instead:
1. Log the failure in `MCTS_LOG.md` with the reason (usually: problem is too hard for the OSS sandbox, or literature is too dense for novelty).
2. Re-run ideation with broader perspectives (relax the `theoretical` axis to allow `conjecture + numerical evidence`; relax `computational` to allow `toy regime only`).
3. If still 0 after a 2nd pass → report to the human user: "No tractable idea found within OSS constraints. Recommend returning to the human for a problem re-scoping or an external experiment collaborator."

## Idea Writing Quality Gate (v2.2.1 — Anti-Garbage-Idea)

**User hard requirement**: ideas must not be written as garbage. An idea that is only "we use method X to do Y", with no novel insight, no mechanistic contribution, no point of difference from existing work, is a garbage idea and must be eliminated.

## Anti-Repetition Memory (v3.1 — P1 anti-repetition mechanism)

**Prevent regenerating ideas already eliminated/falsified.** Persistence + dual detox (0 LLM cost, mechanical verdicts):

1. **Persistence**: whenever an idea is `FALSIFIED` (eliminated in Phase 2.5), fails the toy gate (`FAIL`), is killed in a BA back-track, or is eliminated by novelty-check, append `{id, description, reason}` to `refine-logs/failed_ideas.json` (idempotent, deduplicated by id).
2. **Hard check (0 LLM cost)**: before generating each root node in MCTS Round 1, run a **TF-IDF cosine similarity** check of the new idea description against the `failed_ideas.json` corpus; similarity **> 0.78 → discard outright** (does not enter MCTS). `REJECT` → the candidate is not added to the DAG; the reason is written to `MCTS_LOG.md` (reason_code `duplicate_failed_idea`).
3. **Soft prompt injection**: before MCTS Round 1 generation, inject the N historically most similar killed ideas + their failure reasons into the generation prompt (prevents "same idea, new wording"). The injected text starts with `[failed-ideas prompt injection]` and is handed to the agent together with the generation instruction.

> Implementation can be done by the agent at runtime with any lightweight script (pure stdlib TF-IDF suffices); this skill only specifies the protocol and threshold, and does not depend on any specific tool file in the repo.

## Type-A Objective Hard Elimination vs Type-B Quality Sentencing (v3.1 — P2 decoupling)

**Strictly forbidden: letting the LLM eliminate feasible options by subjective taste at the pre-screen stage.** The screening pipeline is decoupled into two layers:

| Layer | Content | LLM Cost | Verdict method |
|-------|---------|----------|----------------|
| **Type-A (objective hard-condition elimination)** | Four mechanical checks: GPU VRAM estimate, data availability, dependency import, code syntax (AST). Any FAIL → **killed at zero cost**; never enters any quality review | **0** | Deterministic scripts / mechanical rules |
| **Type-B (quality sentencing)** | Only after passing Type-A does the idea enter Peer-Review subagents such as Phase 2.5 (adversarial-falsification) / Phase 3 (novelty-check) for weighted multi-dimensional scoring on Novelty / Soundness / Impact | LLM | Existing Phase 2.5 / Phase 3 |

**Execution protocol**:
1. Each candidate idea in MCTS Round 1 first produces a structured spec (`requires_gpu_gb` / `requires_packages` / `data_required` / `data_sources` / `code_snippet`); run the Type-A mechanical checks on it (GPU VRAM estimate ×1.5 safety factor vs available VRAM, data-source reachability, dependency importability, code-snippet AST syntax).
2. `FAIL` → the idea is eliminated outright; `MCTS_LOG.md` records `reason_code=type_a_<fail_reason>` (e.g., `type_a_gpu_oom_estimated` / `type_a_missing_data_source` / `type_a_missing_dependency` / `type_a_code_syntax_error`); it **must not** enter Phase 2.5/3.
3. `PASS` → only then does it enter Type-B (Phase 2.5 falsification + Phase 3 novelty scoring).
4. Type-A verdicts **never call the LLM**; no LLM may replace or override Type-A's mechanical verdicts at the pre-screen stage.

Every candidate idea in `IDEA_CANDIDATES.md` must contain the following 6 fields (missing any one is below standard — eliminated before MCTS):

| Field | Content | Garbage-idea signals |
|-------|---------|----------------------|
| `insight` | One sentence: what is the **scientific insight** with which this idea surpasses existing work? (not "which technique is used" but "why this produces new knowledge") | Empty / could be pasted onto any paper / no mechanistic statement |
| `novelty_delta` | One sentence: relative to the 1-2 closest papers in `references.bib`, the **concrete point of difference** of this idea (not "better" but "different in assumption/method/data X") | "Improves the baseline" with no concrete dimension / substantively duplicates cited work |
| `falsifiable_claim` | One sentence: the core claim of this idea is **falsifiable** — which experiment/derivation outcome would refute it? (with no falsifiable point it is not a scientific idea) | "We verified X" with no counterexample condition / unfalsifiable claim |
| `mechanism` | One sentence: **why** does this idea's method produce the expected outcome? (mechanistic causal chain, not "empirically effective") | No mechanism / pure empirical fit / "data-driven black box" |
| `boundary` | One sentence: under what conditions/scales/domains does this idea **fail**? (honest boundary, not "universal") | "Applies to every scenario" / no boundary |
| `gap_anchor` | The gap-id from `literature/GAP_REPORT.md` this idea addresses (v6.0 gap chain) — or `exploratory` + one-line justification (capped at 2 per round) | No gap-id and no justification / cites a gap-id that does not exist in GAP_REPORT.md / "general improvement of the field" |

**Pre-MCTS hard filter**: any field judged as a garbage signal → the idea is eliminated outright and does not enter MCTS simulation. This is stricter than the 6-axis idea-fit — the 6-axis scores "feasibility/novelty"; the 6 fields judge "whether it is a genuine scientific idea".

**Second check before the Phase 2 human checkpoint**: before the selected idea is written into `FINAL_PROPOSAL.md`, the agent self-checks that the 5 fields meet the bar; if the selected idea is still judged garbage (e.g., high MCTS score but empty insight), fall back to Step 2 and regenerate (bounded 1 round); never deliver a garbage idea to downstream.

## BA (Backtracking-After) Mechanism (v2.2.1 — back-track when the experiment falsifies the idea)

**User hard requirement**: if the idea was framed correctly but the completed experiment shows it fails, a callback/BA mechanism must return to Phase 2 and regenerate for a few rounds; never deliver a paper falsified by its own experiment.

The DAG's fallback already covers in-phase failure (6b toy FAIL → kill idea is the most direct case). But **the experiment result falsifying the idea's core claim** (rather than the experiment itself failing) is a subtler case — the toy gate PASSes but the full experiment shows the claim does not hold, or logic-verification finds the derivation's conclusion contradicts the experimental data. In this case BA must back-track to Phase 2 and regenerate the idea rather than patch the original idea.

### BA Trigger Conditions (any hit triggers a return to Phase 2)

1. **Phase 6c full experiment complete + STATUS.json verdict=FAIL with toy previously PASS**: toy passes but full falsifies → the idea holds at toy scale but not at full scale — a scale-dependent false trick. Return to Phase 2 and regenerate (bounded 2 rounds).
2. **Phase 8 logic-verification FATAL: "experimental data contradicts the derivation's conclusion"**: the derivation says X, the experimental data says not-X. The idea itself is wrong. Return to Phase 2 and regenerate (bounded 2 rounds).
3. **Phase 14 auto-review-loop review states "the core claim is falsified by this paper's own experimental data"** (the kill argument stands). Return to Phase 2 and regenerate (bounded 2 rounds).

### BA Execution Flow

```
Trigger BA (any of conditions 1/2/3)
  │
  ▼
Record BA_EVENT.json: {triggered_by: "6c_full_FAIL_after_toy_PASS" | "8_logic_FATAL_contradiction" | "14_kill_argument_sustained",
                       original_idea_id, failed_evidence: [file paths], reason: "..."}
  │
  ▼
Back-track to Phase 2 (idea-discovery) — bounded 2 rounds:
  Round 1: regenerate 8-12 candidates, but EXCLUDE the original idea_id and its DAG subtree (avoid repeating the same mistake);
           record in MCTS_LOG.md: "BA round 1: original idea [id] failed for [reason], excluded"
  Round 2 (if round 1 still yields no qualifying idea): relax further — allow "fixing the original idea's failed assumption" as a new candidate
           (i.e., if the original idea failed on assumption H, the new candidate may explicitly deny H and propose an alternative mechanism)
  │
  ▼
If no qualifying idea after 2 BA rounds → BLOCKED + BA_EXHAUSTED, hand to the human for a decision
  (no infinite loop; 2 rounds is BA's hard cap, distinct from the in-phase 3-round fallback)
```

### BA vs In-Phase Fallback

| Mechanism | Trigger | Back-track target | Cap |
|-----------|---------|-------------------|-----|
| In-phase fallback (↻) | Single-phase failure (derivation error / compile warning) | Adjacent upstream phase | 3 rounds |
| **BA (this section)** | Experimental data **falsifies the idea's core claim** (not a phase failure) | Phase 2 idea regeneration | 2 rounds |

BA is the back-track for "the idea itself is wrong"; phase fallback is the back-track for "execution went wrong". Do not conflate the two: toy gate FAIL (6b) is phase fallback (kill the idea, no return to Phase 2); full complete but falsifying the claim is BA (return to Phase 2 and regenerate).

## Workflow

### Step 0: Load the Frozen Q-id

The Q-id + problem statement come from the human user's prompt. OSS solves ONE user-supplied question per invocation — it does **not** iterate over a problem bank.

Record the Q-id in `refine-logs/FINAL_PROPOSAL.md` Problem Anchor (frozen by INV-G1 for downstream skills).

### Step 1: Literature-Aware Ideation

Read `literature/references.bib` (from `/universal-retrieval`) to understand what's already been done. For each perspective, generate 3-4 idea candidates that are NOT direct duplicates of cited work.

### Step 2: 4-Perspective Generation (8-12 root nodes)

| Perspective | What it produces | Example framing |
|-------------|------------------|-----------------|
| `theoretical` | A symbolic derivation chain from assumptions to outcome | "We establish [outcome] by deriving [chain] under [assumptions]" |
| `computational` | A numerical sanity check that confirms a theoretical prediction | "We confirm [prediction] numerically via [sweep] in [regime]" |
| `qualitative` | A mechanism reasoning that explains why a prediction holds | "We show [mechanism] implies [prediction] by [qualitative argument]" |
| `empirical` | A causal-identification / estimation strategy recovering a target parameter | "We recover [causal parameter] via [identification strategy] under [assumption]" |

Generate 8-12 root nodes across these 4 perspectives. For causal-design / econometrics / data-estimation problems, the `empirical` perspective is the primary axis — do NOT force-fit such problems into `computational` (which is for confirming a theoretical prediction, not for being the identification strategy itself). A problem may span multiple perspectives (e.g., theory + empirical for structural estimation); record all applicable perspectives on the node. Record each in `IDEA_CANDIDATES.md` with:
- ID (e.g., `IDEA-001`)
- Perspective
- Framing (1-2 sentences)
- 6-axis idea-fit pre-screen verdict (including Engineering Grounding tier)

### Step 3: DAG Construction

Encode dependencies in `IDEA_DAG.json`:
- Some ideas depend on others (e.g., a `computational` confirmation depends on the `theoretical` prediction it confirms)
- Edges = "depends on" relationships
- The DAG is acyclic by construction (no idea depends on itself)

### Step 3b: DAG Visualization (Mermaid)

After constructing `IDEA_DAG.json`, generate a Mermaid-format visualization in `IDEA_DAG_VISUAL.md`:

```mermaid
graph TD
    Q[Problem: {Q-id}] --> T[Idea 1: theoretical]
    Q --> C[Idea 2: computational]
    Q --> QL[Idea 3: qualitative]
    C --> T
    T --> M[MCTS promoted]
    QL --> E[Eliminated]
    M --> F[Final proposal]
```

This file is updated after each MCTS round to reflect the current DAG state. The final visualization shows the complete idea evolution path, including which ideas were eliminated and why. This is the **"show"** of the DAG architecture — the user can see the full reasoning graph at a glance.

### Step 4: MCTS Iteration (4 rounds)

Follow the MCTS protocol above. Log each round in `MCTS_LOG.md`:
- Round number
- Nodes scored
- Promotions / rejections
- Child nodes generated (for borderline cases)

### Step 5: Final Proposal (Forced Human Checkpoint)

From promoted ideas (1-3), present to the human user:
- Each idea's framing, 6-axis scores, MCTS round-by-round trajectory
- The DAG position (which other ideas it depends on / supports)

The human picks the final idea. Record in `FINAL_PROPOSAL.md`:
- Problem Anchor (Q-id, frozen)
- Selected idea (framing, perspective, assumptions)
- Rejected alternatives (with reasons — for audit trail)
- MCTS convergence evidence (round-by-round scores)

**This is a forced human checkpoint.** The agent cannot self-select the final idea.

### Step 6: Notify Downstream

- `/method-registry` → reads `FINAL_PROPOSAL.md` to build the method registry
- `/theory-derivation` → reads `FINAL_PROPOSAL.md` for the selected idea's framing + assumptions
- `/invariant-check` → verifies INV-G1 (Q-id frozen in FINAL_PROPOSAL + referenced downstream)

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **No legacy pilot fallback.** OSS has no experiments. 0 promoted ideas → re-run ideation with broader perspectives, OR report to human for problem re-scoping. Never fall back to a "demo experiment".
- **No discipline-specific framing.** Do not reintroduce economics DiD/IV/RDD, cs-ml SOTA, or physics PNV framings. The universal 4-perspective (theoretical / computational / qualitative / empirical) applies to every problem.
- **Forced human checkpoint at final selection.** The agent cannot self-select the final idea.
- **MCTS iteration is mandatory.** Do not commit to the first idea generated — the first idea is rarely the best. Always run ≥ 4 MCTS rounds.
- **6-axis hard filter is non-negotiable.** Any axis `BLOCKED` → idea rejected before MCTS, no exceptions. Engineering Grounding BLOCKED = any sub-dimension = 0 (see [EG contract](../../shared-references/engineering-grounding-contract.md)).

## Output Shape

The final output is:
1. `refine-logs/IDEA_CANDIDATES.md` — ranked list of 8-12 idea candidates with 6-axis scores
2. `refine-logs/IDEA_DAG.json` — DAG structure (nodes + edges)
3. `refine-logs/IDEA_DAG_VISUAL.md` — DAG visualization in Mermaid format (for human-readable graph)
4. `refine-logs/MCTS_LOG.md` — round-by-round MCTS iteration log
5. `refine-logs/FINAL_PROPOSAL.md` — selected idea (frozen for downstream) with Problem Anchor + MCTS convergence evidence
6. `refine-logs/GAP_ANCHOR_LOG.md` — v6.0 gap chain: per-idea anchoring decisions (idea-id → gap-id, exploratory justifications, re-anchoring events); consumed by /novelty-check and /auto-review-loop

## See Also

- [`../shared-references/idea-dag-schema.md`](../../shared-references/idea-dag-schema.md) — DAG node schema (universal, copied from main SciForge)
- [`../shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) — MCTS iteration protocol (UCB1 + bounded rounds)
- [`../shared-references/multi-fidelity-evaluation.md`](../../shared-references/multi-fidelity-evaluation.md) — 3-fidelity filter (OSS uses `general` row only)
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../../support/method-registry/SKILL.md`](../../support/method-registry/SKILL.md) — consumes FINAL_PROPOSAL.md to build the method registry
- [`../../support/theory-derivation/SKILL.md`](../../support/theory-derivation/SKILL.md) — consumes FINAL_PROPOSAL.md for the selected idea's framing
