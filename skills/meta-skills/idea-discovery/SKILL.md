---
name: idea-discovery
type: meta-skill
role: research-idea-generation
---

# Idea Discovery (SciForge-OSS — Discipline-Agnostic, MCTS-Enhanced)

> **Status**: Generates and pre-screens research idea candidates for a given 125-problem question. OSS merges main SciForge's `idea-creator` (MCTS iterative idea refinement + DAG node expansion) into this meta-skill. **OSS is discipline-agnostic** — there is no economics DiD/IV/RDD framing, no cs-ml SOTA framing, no physics PNV framing. The universal 4-perspective ideation (theoretical / computational / qualitative / empirical) + MCTS iteration applies to every problem.

## Quick Reference

- **Purpose**: 生成 8-12 个 idea → MCTS 4 轮迭代 → 筛选最优 1-3 个
- **Input**: 人类提供的 Q-id + 问题描述
- **Output**: IDEA_DAG.json + FINAL_PROPOSAL.md + IDEA_DAG_VISUAL.md
- **Key**: 4 视角 (theoretical/computational/qualitative/empirical), 5-axis pre-screen, 强制人类审批

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
- `refine-logs/domain-signature.json` — from Phase 1b `/domain-learner` (the SOLE writer; used for perspective weight adjustment)
- `literature/references.bib` — from `/universal-retrieval` (for novelty pre-screen)
- `data/` — from `idea-discovery` 6-axis pre-screening's data-readiness axis (built-in)

## Configuration

- **Max MCTS iterations** — 4 (default). Main SciForge uses 6; OSS uses 4 because the no-experiment setting means each iteration is cheaper (no pilot to run). Configurable.
- **Min root nodes** — 8 (default). The DAG starts with 8-12 root idea nodes; MCTS prunes to the best 3-5.
- **Perspectives** — 4 universal: `theoretical` (symbolic derivation), `computational` (numerical sanity check), `qualitative` (mechanism reasoning), `empirical` (causal-identification / data-driven estimation). The 4th `empirical` covers econometrics (DiD/IV/RDD), regression studies, and any problem whose core contribution IS an identification strategy or an estimator recovering a known parameter — it is NOT a symbolic derivation nor a numerical confirmation of a theorem. The `empirical` perspective emits `verification_type=computational` (it runs code/data) but its idea framing is "recover [causal parameter] via [identification strategy] under [assumption]" — distinct from `computational`'s "confirm [prediction] numerically."
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
| **Engineering Grounding** | **AI agent 能否实现此 idea？(see [EG contract](../../shared-references/engineering-grounding-contract.md))** | **EG average 3.0-5.9 (CONSTRAINED tier)** | **≥ 3 EG sub-dimensions = 0** |

**Hard filter**: any axis `BLOCKED` → idea is rejected before MCTS. `CONSTRAINED` axes are flagged but the idea proceeds to MCTS. The Engineering Grounding axis follows the [Engineering Grounding Contract](../../shared-references/engineering-grounding-contract.md) — HEAVY and CONSTRAINED ideas proceed to MCTS with labels; only **≥ 3 sub-dimensions = 0** triggers BLOCKED (v3.0 stricter rule: 1-2 sub-dimensions = 0 does NOT eliminate, instead produces an AI Mitigation Plan).

## MCTS Iteration Protocol

Follow [`shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) for the full contract. Summary:

1. **Round 1 (Expansion)**: Generate 8-12 root idea nodes across the 3 perspectives.
2. **Round 2 (Selection + Simulation)**: Score each node on the 6-axis idea-fit (5 original + Engineering Grounding). **B1 文献依赖 (v2.3)**: novelty 轴依赖 Phase 4 的 `literature/references.bib`——若该文件尚未就绪（Phase 4 未完成），先标注 `novelty=pending-literature` 并暂停 novelty 轴的最终判定，待文献到达后再补评；**禁止在无参考文献的情况下对 novelty 轴做最终 BLOCKED/PASS 判定**（可用 generation 视角的直觉先做可行性/相关性预筛，但 novelty 判定必须等文献）。Select top 4-6 for simulation (light-weight derivation sketch — does SymPy plausibly close the loop?). Clear FAIL (< 0.4) are not re-scored; clear PASS (≥ 0.6) get a lightweight re-score (not full re-run) to confirm stability.
3. **Round 3 (Backpropagation)**: Promote ideas with simulation score ≥ 0.6. Reject ideas with simulation score < 0.4. For borderline (0.4-0.6), generate 2-3 child nodes (refined variants) and re-score.
4. **Round 4 (Final selection)**: From promoted ideas, select the top 1-3 for `FINAL_PROPOSAL.md`. The human user picks the final one (forced checkpoint).

**0 promoted ideas fallback**: If after 4 rounds no idea reaches the promotion threshold, do NOT fall back to a legacy demo/pilot (main SciForge's path). Instead:
1. Log the failure in `MCTS_LOG.md` with the reason (usually: problem is too hard for the OSS sandbox, or literature is too dense for novelty).
2. Re-run ideation with broader perspectives (relax the `theoretical` axis to allow `conjecture + numerical evidence`; relax `computational` to allow `toy regime only`).
3. If still 0 after a 2nd pass → report to the human user: "No tractable idea found within OSS constraints. Recommend returning to the human for a problem re-scoping or an external experiment collaborator."

## Idea 写作质量门槛（v2.2.1 — 反"垃圾 idea"）

**用户硬要求**：idea 不能写得垃圾。一个 idea 若只是"我们用 X 方法做 Y"，无新颖性洞察、无机制性贡献、无与现有工作的差异点，就是垃圾 idea，必须淘汰。

每个 candidate idea 在 `IDEA_CANDIDATES.md` 必须包含以下 5 字段（缺任一即视为不达标，MCTS 前置淘汰）：

| 字段 | 内容 | 垃圾 idea 的判别信号 |
|------|------|---------------------|
| `insight` | 一句话：本 idea 超越现有工作的**科学洞察**是什么？（不是"用了什么技术"，是"为什么这能产生新知识"） | 空洞 / 可套在任何论文上 / 无机制性陈述 |
| `novelty_delta` | 一句话：相对 `references.bib` 中最接近的 1-2 篇，本 idea 的**具体差异点**（不是"更好"，是"在 X 假设/方法/数据上不同"） | "改进了 baseline"无具体维度 / 与 cited work 实质重复 |
| `falsifiable_claim` | 一句话：本 idea 的核心 claim 是**可证伪的**——什么实验/推导结果会否定它？（若无可证伪点，不是科学 idea） | "我们验证了 X"无反例条件 / claim 不可证伪 |
| `mechanism` | 一句话：**为什么**本 idea 的方法会产生预期结果？（机制性因果链，不是"经验上有效"） | 无机制 / 纯经验拟合 / "data-driven 黑箱" |
| `boundary` | 一句话：本 idea 在什么条件/尺度/领域下**会失效**？（诚实边界，不是"普适"） | "适用于所有场景" / 无边界 |

**MCTS 前置硬筛**：任一字段判为垃圾信号 → idea 直接淘汰，不进入 MCTS simulation。这比 6-axis idea-fit 更严格——6-axis 评"可行性/新颖性分数"，5 字段评"是不是真正的科学 idea"。

**Phase 2 人类 checkpoint 前的二次检查**：selected idea 在写入 `FINAL_PROPOSAL.md` 前，agent 自检 5 字段是否达标；若 selected idea 仍判为垃圾（如 MCTS 分数高但 insight 空洞），回退 Step 2 重新生成（bounded 1 轮），不直接交付垃圾 idea 给下游。

## BA (Backtracking-After) 机制（v2.2.1 — 实验否定 idea 时回溯）

**用户硬要求**：idea 写对了但实验跑完发现不行，要有 callback/BA 机制回 Phase 2 重新生成几轮，不能直接交付一个实验否定的论文。

DAG 的 fallback 已覆盖 phase 内失败（6b toy FAIL→kill idea 是最直接的）。但**实验结果否定 idea 的核心 claim**（而非实验本身失败）是更微妙的情况——toy gate PASS 但 full 实验显示 claim 不成立，或 logic-verification 发现推导结论与实验数据矛盾。这时需要 BA 回溯到 Phase 2 重新生成 idea，而非在原 idea 上打补丁。

### BA 触发条件（任一命中即触发回 Phase 2）

1. **Phase 6c full 实验完成 + STATUS.json verdict=FAIL 且 toy 曾 PASS**：toy 通过但 full 否定 → idea 在 toy scale 成立但 full scale 不成立，是 scale-dependent false trick。回 Phase 2 重生成（bounded 2 轮）。
2. **Phase 8 logic-verification FATAL: "实验数据与推导结论矛盾"**：推导说 X，实验数据说 not-X。这是 idea 本身错了。回 Phase 2 重生成（bounded 2 轮）。
3. **Phase 14 auto-review-loop 评审指出"核心 claim 被本文自己的实验数据否定"**（kill-argument 站住）。回 Phase 2 重生成（bounded 2 轮）。

### BA 执行流程

```
触发 BA (条件 1/2/3 任一)
  │
  ▼
记录 BA_EVENT.json: {triggered_by: "6c_full_FAIL_after_toy_PASS" | "8_logic_FATAL_contradiction" | "14_kill_argument_sustained",
                     original_idea_id, failed_evidence: [文件路径], reason: "..."}
  │
  ▼
回退 Phase 2 (idea-discovery) — bounded 2 轮:
  轮1: 重新生成 8-12 候选，但 EXCLUDE 原 idea_id 及其 DAG 子树（避免重蹈覆辙）；
        在 MCTS_LOG.md 记录"BA 轮1：原 idea [id] 因 [reason] 失败，已排除"
  轮2 (若轮1 仍无达标 idea): 进一步放宽——允许"修正原 idea 的失败假设"作为新候选
        （即：若原 idea 失败于假设 H，新候选可显式否定 H 并提出替代机制）
  │
  ▼
若 2 轮 BA 后仍无达标 idea → BLOCKED + BA_EXHAUSTED，交人类决策
  （不再无限循环；2 轮是 BA 的硬上限，区别于 phase 内 3 轮 fallback）
```

### BA 与 phase 内 fallback 的区别

| 机制 | 触发 | 回退到 | 上限 |
|------|------|--------|------|
| phase 内 fallback (↻) | 单 phase 失败（推导报错/编译警告） | 相邻前置 phase | 3 轮 |
| **BA (本节)** | 实验数据**否定 idea 核心claim**（非 phase 失败） | Phase 2 idea 重生成 | 2 轮 |

BA 是"idea 本身错了"的回溯，phase fallback 是"执行出错"的回溯。两者不混淆：toy gate FAIL（6b）是 phase fallback（kill idea，不回 Phase 2）；full 完成但否定 claim 是 BA（回 Phase 2 重生成）。

## Workflow

### Step 0: Load the Frozen Q-id

The Q-id + problem statement come from the human user's prompt — NOT auto-searched from `problems/125-SCIENCE-PROBLEMS.md`. The human supplies the specific question to solve; OSS does **not** iterate over all 125 problems.

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

## See Also

- [`../shared-references/idea-dag-schema.md`](../../shared-references/idea-dag-schema.md) — DAG node schema (universal, copied from main SciForge)
- [`../shared-references/mcts-search-protocol.md`](../../shared-references/mcts-search-protocol.md) — MCTS iteration protocol (UCB1 + bounded rounds)
- [`../shared-references/multi-fidelity-evaluation.md`](../../shared-references/multi-fidelity-evaluation.md) — 3-fidelity filter (OSS uses `general` row only)
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../../support/method-registry/SKILL.md`](../../support/method-registry/SKILL.md) — consumes FINAL_PROPOSAL.md to build the method registry
- [`../../support/theory-derivation/SKILL.md`](../../support/theory-derivation/SKILL.md) — consumes FINAL_PROPOSAL.md for the selected idea's framing
