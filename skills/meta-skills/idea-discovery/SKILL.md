---
name: idea-discovery
type: meta-skill
role: research-idea-generation
---

# Idea Discovery (SciForge-OSS — Discipline-Agnostic, MCTS-Enhanced)

> **Status**: Generates and pre-screens research idea candidates for a given 125-problem question. OSS merges main SciForge's `idea-creator` (MCTS iterative idea refinement + DAG node expansion) into this meta-skill. **OSS is discipline-agnostic** — there is no economics DiD/IV/RDD framing, no cs-ml SOTA framing, no physics PNV framing. The universal 3-perspective ideation (theoretical / computational / qualitative) + MCTS iteration applies to every problem.

## Quick Reference

- **Purpose**: 生成 8-12 个 idea → MCTS 4 轮迭代 → 筛选最优 1-3 个
- **Input**: 人类提供的 Q-id + 问题描述
- **Output**: IDEA_DAG.json + FINAL_PROPOSAL.md + IDEA_DAG_VISUAL.md
- **Key**: 3 视角 (theoretical/computational/qualitative), 5-axis pre-screen, 强制人类审批

> **No legacy pilot fallback**: main SciForge's `idea-creator` has a legacy demo/pilot experimental fallback when MCTS produces 0 promoted ideas. OSS has **no experiments** — the fallback is instead "re-run ideation with broader perspectives" (not "fall back to a demo experiment").

## Use When

Use this skill when the user wants to generate and pre-screen research idea candidates for a 125-problem question.

Typical prompts:
- "Generate research ideas"
- "Idea discovery"
- "Brainstorm approaches"
- "研究方向头脑风暴"
- "What are the possible approaches to this problem"
- "List potential methodologies"

## Job

Take a frozen research question (Q-id from `problems/125-SCIENCE-PROBLEMS.md`, supplied by the human user's prompt) and produce a ranked list of 8-12 research idea candidates with:
1. Clear framing (theoretical / computational / qualitative perspective)
2. Pre-screened against the universal 5-axis idea-fit (novelty / feasibility / relevance / tractability / data-readiness)
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
- The frozen Q-id + problem statement (from the human user's prompt — NOT auto-searched from the 125-problem index)
- `refine-logs/domain-signature.json` — from Phase 1a `/domain-signature` (for perspective weight adjustment)
- `literature/references.bib` — from `/universal-retrieval` (for novelty pre-screen)
- `data/` — from `/ouroboros-data-insight` if it has run (for data-readiness pre-screen)

## Configuration

- **Max MCTS iterations** — 4 (default). Main SciForge uses 6; OSS uses 4 because the no-experiment setting means each iteration is cheaper (no pilot to run). Configurable.
- **Min root nodes** — 8 (default). The DAG starts with 8-12 root idea nodes; MCTS prunes to the best 3-5.
- **Perspectives** — 3 universal: `theoretical` (symbolic derivation), `computational` (numerical sanity check), `qualitative` (mechanism reasoning). Main SciForge has a 4th `empirical` (experiment) which OSS removes.
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
| **Engineering Grounding** | **Can a real engineering team build this? (see [EG contract](../../shared-references/engineering-grounding-contract.md))** | **EG average 3.0-5.9 (CONSTRAINED tier)** | **Any EG sub-dimension = 0** |

**Hard filter**: any axis `BLOCKED` → idea is rejected before MCTS. `CONSTRAINED` axes are flagged but the idea proceeds to MCTS. The Engineering Grounding axis follows the [Engineering Grounding Contract](../../shared-references/engineering-grounding-contract.md) — HEAVY and CONSTRAINED ideas proceed to MCTS with labels; only sub-dimension = 0 BLOCKED eliminates.

## MCTS Iteration Protocol

Follow [`shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) for the full contract. Summary:

1. **Round 1 (Expansion)**: Generate 8-12 root idea nodes across the 3 perspectives.
2. **Round 2 (Selection + Simulation)**: Score each node on the 6-axis idea-fit (5 original + Engineering Grounding). Select top 4-6 for simulation (light-weight derivation sketch — does SymPy plausibly close the loop?).
3. **Round 3 (Backpropagation)**: Promote ideas with simulation score ≥ 0.6. Reject ideas with simulation score < 0.4. For borderline (0.4-0.6), generate 2-3 child nodes (refined variants) and re-score.
4. **Round 4 (Final selection)**: From promoted ideas, select the top 1-3 for `FINAL_PROPOSAL.md`. The human user picks the final one (forced checkpoint).

**0 promoted ideas fallback**: If after 4 rounds no idea reaches the promotion threshold, do NOT fall back to a legacy demo/pilot (main SciForge's path). Instead:
1. Log the failure in `MCTS_LOG.md` with the reason (usually: problem is too hard for the OSS sandbox, or literature is too dense for novelty).
2. Re-run ideation with broader perspectives (relax the `theoretical` axis to allow `conjecture + numerical evidence`; relax `computational` to allow `toy regime only`).
3. If still 0 after a 2nd pass → report to the human user: "No tractable idea found within OSS constraints. Recommend returning to the human for a problem re-scoping or an external experiment collaborator."

## Workflow

### Step 0: Load the Frozen Q-id

The Q-id + problem statement come from the human user's prompt — NOT auto-searched from `problems/125-SCIENCE-PROBLEMS.md`. The human supplies the specific question to solve; OSS does **not** iterate over all 125 problems.

Record the Q-id in `refine-logs/FINAL_PROPOSAL.md` Problem Anchor (frozen by INV-G1 for downstream skills).

### Step 1: Literature-Aware Ideation

Read `literature/references.bib` (from `/universal-retrieval`) to understand what's already been done. For each perspective, generate 3-4 idea candidates that are NOT direct duplicates of cited work.

### Step 2: 3-Perspective Generation (8-12 root nodes)

| Perspective | What it produces | Example framing |
|-------------|------------------|-----------------|
| `theoretical` | A symbolic derivation chain from assumptions to outcome | "We establish [outcome] by deriving [chain] under [assumptions]" |
| `computational` | A numerical sanity check that confirms a theoretical prediction | "We confirm [prediction] numerically via [sweep] in [regime]" |
| `qualitative` | A mechanism reasoning that explains why a prediction holds | "We show [mechanism] implies [prediction] by [qualitative argument]" |

Generate 8-12 root nodes across these 3 perspectives. Record each in `IDEA_CANDIDATES.md` with:
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
- Each idea's framing, 5-axis scores, MCTS round-by-round trajectory
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
> - **[Output Versioning Protocol](../../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../../shared-references/output-language.md)** — respect the project's language setting

## Boundaries

- **No legacy pilot fallback.** OSS has no experiments. 0 promoted ideas → re-run ideation with broader perspectives, OR report to human for problem re-scoping. Never fall back to a "demo experiment".
- **No discipline-specific framing.** Do not reintroduce economics DiD/IV/RDD, cs-ml SOTA, or physics PNV framings. The universal 3-perspective (theoretical / computational / qualitative) applies to every problem.
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

## See Also

- [`../shared-references/idea-dag-schema.md`](../../shared-references/idea-dag-schema.md) — DAG node schema (universal, copied from main SciForge)
- [`../shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) — MCTS iteration protocol (UCB1 + bounded rounds)
- [`../shared-references/multi-fidelity-evaluation.md`](../../shared-references/multi-fidelity-evaluation.md) — 3-fidelity filter (OSS uses `general` row only)
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../../support/method-registry/SKILL.md`](../../support/method-registry/SKILL.md) — consumes FINAL_PROPOSAL.md to build the method registry
- [`../../support/theory-derivation/SKILL.md`](../../support/theory-derivation/SKILL.md) — consumes FINAL_PROPOSAL.md for the selected idea's framing
