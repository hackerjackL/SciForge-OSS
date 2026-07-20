---
name: 125-problems-pipeline
type: orchestrator
role: single-question-research-orchestrator
---

# 125 Problems Pipeline (SciForge-OSS — Single-Question, 17-Phase DAG Loop)

> **Status**: The **single entry orchestrator** for OSS. Executes a complete 17-phase DAG research loop on **one** 125-problem question supplied by the human user's prompt. **OSS does NOT auto-iterate over all 125 questions** — each invocation processes exactly one Q-id, end-to-end. The orchestrator does NOT execute research itself — it delegates each phase to the corresponding meta-skill or support skill, reads their outputs, and feeds the next phase.
>
> **Key OSS difference from main SciForge**: main SciForge's research-pipeline branches by discipline (economics / cs-ml / physics / general) into 4 parallel pipelines each with its own framework (AIM / SOTA / PNV / none) + reviewer persona. OSS has **no discipline branch** — one universal pipeline, the universal `senior-reviewer-agnostic` persona, and the agent's runtime reasoning handles domain-specific methodology.

## Quick Reference

- **Entry point**: `/125-problems-pipeline "Q001: 问题描述" — effort: max`
- **Scope**: 单题执行，17 阶段 DAG 循环，全领域通用
- **Output**: 完整论文 (LaTeX/PDF) + 所有中间产物
- **Key**: 不迭代 125 题，人类提供 Q-id；Phase 2.5 强制证伪；Phase 3→4 和 Phase 5→6 需人类审批

## Use When

Use this skill when the AI scientist needs to fully solve **one** of the 125 science problems end-to-end. This is the **only entry orchestrator** — it does not branch by discipline; it uses the DAG architecture to handle any scientific domain via universal meta-skills.

Typical prompts:
- "Solve Q001" / "解决 Q001：宇宙的起源与演化"
- "run the full pipeline on Q042"
- "帮我完整研究 Q015"

**The human user supplies the specific Q-id** in the prompt. OSS does **not** auto-search the 125-problem index or iterate over all 125. Each invocation = one Q-id = one complete pipeline run.

## Job

Orchestrate a complete 17-phase DAG research loop. The non-negotiable goals:
1. **Each question runs the complete loop** — no phase skipped, regardless of how simple the problem seems
2. **Each phase produces a verifiable artifact** — the pipeline is documented by output files, not promises
3. **Every citation is real** — the 3-layer anti-hallucination protocol is mandatory (see [`citation-discipline.md`](../shared-references/citation-discipline.md))
4. **Every conclusion is logic-verified** — no unsupported assertion survives to the final paper
5. **The pipeline is self-correcting** — if any phase fails or produces WARN/FAIL, auto-fallback to the relevant prior phase (bounded 3 rounds)
6. **INV-G1 PROBLEM_ANCHOR_FREEZE** — the Q-id supplied by the human is frozen at Phase 0 and referenced in every downstream phase (see [`../invariant-check/SKILL.md`](../support/invariant-check/SKILL.md))

## Performance Optimizations

### Parallelization

Where possible, phases run in parallel to reduce wall-clock time:

| Parallel Group | Phases | Rationale |
|---------------|--------|-----------|
| **Group A** | Phase 2 (idea-discovery) + Phase 4 (universal-retrieval) | Literature search does not depend on idea generation output |
| **Group B** | Phase 11 (unified-plotting) + Phase 12 (paper-writing) | Figures can be generated while the paper is being written |
| **Group C** | Phase 7 (leakage-audit) + Phase 8 (logic-verification) | Both audits are independent |

### Incremental MCTS

MCTS iteration is optimized to avoid re-scoring already-clear ideas:

- **Round 1**: Score all 8-12 root nodes on the 5-axis idea-fit
- **Round 2**: Only re-score **borderline** ideas (0.4-0.6 score range). Clear PASS (≥ 0.6) and clear FAIL (< 0.4) are not re-scored
- **Round 3**: Only re-score child nodes of borderline ideas
- **Round 4**: Final selection from promoted ideas

**Estimated savings**: 4 rounds → ~2.5 rounds equivalent (40% reduction in MCTS cost)

### Early Exit Conditions

| Phase | If condition met | Action |
|-------|-----------------|--------|
| Phase 2 | 5-axis pre-screen: all ideas BLOCKED | Return immediately, no MCTS |
| Phase 3 | Highest score > 0.8 | Skip Phase 2.5 (adversarial falsification) — idea is clearly strong |
| Phase 10 | All claims reach symbolic fidelity | Skip Phase 14 (auto-review-loop) — no improvement needed |
| Phase 12 | No figures needed | Skip Phase 11 (unified-plotting)

```
Phase  0: 加载问题（冻结 Q-id — INV-G1 锚点）
     │
Phase  1: 问题理解与分解（内置推理）
     │
     ├───────────────── DAG 分支 ─────────────────┐
     │                                             │
Phase  2: /idea-discovery [DAG 分支] — 3 视角 idea
     │  (theoretical / computational / qualitative)   │
     │  + MCTS 迭代 (4 轮, 8-12 root nodes)           │
     │  + 输出 verification_type (理论-only / 计算 / 理论+实验)
     │                                             │
Phase  2.5: /adversarial-falsification [证伪门控]   ← 新增
     │  5 维度攻击: 假设评分 → 反例构造 → 文献对抗    │
     │  → 类比映射 → 计算可行性                       │
     │  SURVIVE → 继续; WEAKENED → 回退 Phase 2      │
     │  FALSIFIED → 淘汰 (记录原因, 不再进入推导)     │
     │                                             │
Phase  3: /novelty-check [DAG 门控] — 3 维评估 + 淘汰
     │  (新颖性×0.5 + 可行性×0.3 + 相关性×0.2)        │
     │                                             │
     └ Forced human checkpoint: pick the final idea ─┘
     │
Phase  4: /universal-retrieval — 文献调研 + 3 层防幻觉
     │
     ├── 验证路径分支 (由 verification_type 决定) ────┐
     │                                                 │
     │  [理论-only]  → 跳至 Phase 8 (逻辑验证)         │
     │  [计算]       → Phase 5 → 6 → 7 → 8            │
     │  [理论+实验]  → Phase 5 → 6 → 7 → 8            │
     │  (OSS 无实验环境，实验部分输出为可验证预测)      │
     │                                                 │
Phase  5: /method-registry — 方法绑定 + hash 锁 + 强制人类审批       ← 新增
     │
Phase  6: /theory-derivation — SymPy 符号推导 + 逐步机器验证
     │          ↻ 失败回退 Phase 1（最多 3 轮）
     │          (理论-only: engine=manual, 标记为 [not machine-verified])
Phase  7: /leakage-audit — Type I 逻辑漏洞 + Type IV 逃逸审计        ← 新增
     │          ↻ CRITICAL 回退 Phase 5（3 轮 callback 上限）
     │          (理论-only: Type IV = NOT_APPLICABLE)
     │
     └── 路径汇合 ─────────────────────────────────┘
     │
Phase  8: /logic-verification — 6 维度逻辑一致性审计
     │          ↻ FATAL/CRITICAL 回退 Phase 6（最多 3 轮）
Phase  9: /invariant-check — INV-G1 问题锚点冻结验证                  ← 新增
     │
Phase 10: /result-to-claim — 3 保真度 claim 门控                     ← 新增
     │  (symbolic / numerical / qualitative; 主结果需 ≥ numerical)
     │
Phase 11: /unified-plotting — 学术图表（可选，莫兰迪色系 + Layer 2）
     │
Phase 12: /paper-writing — elsarticle 单模板写作
     │
Phase 13: /paper-compile — LaTeX 零警告零报错编译                    ← 新增
     │          ↻ 反死循环阶梯 (3 attempt per-warning → BLOCKED)
     │
Phase 14: /auto-review-loop — 跨模型评审 + kill-argument 反自欺      ← 新增
     │          ↻ 分数 < 6 回退 Phase 6（最多 4 轮）
     │
Phase 15: /citation-audit — 最终引用 3 层验证                        ← 新增
     │
Phase 16: 最终组装 + 产物归档
```

**回退契约**: 每阶段失败回退到最近的前置阶段（最多 3 轮）。3 轮失败升级到 BLOCKED + `reason_code`（复用主仓库 `paper-compile` E16 反死循环阶梯）。**永不静默重试到第 4 轮**——3 轮上限是硬约束。

## Quality Gates (Explicit Per-Phase)

| 阶段 | 门控条件 | 失败处理 |
|------|---------|---------|
| 0 | Q-id 清晰可解、来自人类提示词 | 请求用户澄清 Q-id；**不**自动搜索 125 题索引 |
| 1 | 问题可分解为形式化陈述 | 请求用户澄清问题边界 |
| 2 | 至少生成 1 个 idea (MCTS 收敛) | 放宽 perspectives 重评；再失败升级 BLOCKED |
| 2.5 | 证伪攻击: 假设健康度 ≥ 6 OR 无反例 | WEAKENED → 回退 Phase 2 重生成；FALSIFIED → 淘汰（记录原因） |
| 3 | DAG 收敛到 1 个幸存者 (≥ 0.6 idea-fit) | 放宽 strictness 重评；再失败升级 BLOCKED |
| — | **强制人类审批**：从幸存者中选最终 idea | 等待人类确认；agent 不能自选 |
| 4 | 文献找到或问题是理论型 | 空则 WARN；理论型（theory-only）则跳至 Phase 8，无需实证文献 |
| 5 | 方法 registry 构建完成 + hash 锁 + **强制人类审批** | 请求用户审批 Section 3；agent 不能自批 |
| 6 | SymPy 推导成功 + 逐步机器验证 PASS | 回退 Phase 1（最多 3 轮） |
| 7 | Type I 无 CRITICAL + Type IV 无 ESCAPE | CRITICAL → callback Phase 5 (3 轮上限)；再失败升级 BLOCKED + LOGIC_GAP_FUNDAMENTAL_ISSUE |
| 8 | 6 维度逻辑审计 PASS (零 FATAL/CRITICAL) | FATAL/CRITICAL 回退 Phase 6（最多 3 轮） |
| 9 | INV-G1 Q-id 冻结 + 在当前产物中引用 | FAIL → 重新锚定 Q-id (Phase 0) |
| 10 | 至少 1 个主结果达到 ≥ numerical 保真度 | qualitative-only → reframe 为 conjecture；numerical 缺失 → 回退 Phase 6 |
| 11 | (可选) 图表遵循莫兰迪色系 + Layer 2 数据热图 | 色系违规 → 重生成；非数据图无强制 |
| 12 | 论文非空 + 统一 elsarticle 模板 + 引用都来自验证列表 | 空则回退 Phase 1；模板违规回退 Phase 12 |
| 13 | LaTeX 编译零警告零报错 (submission 级) | 反死循环阶梯：3 attempt per-warning → BLOCKED + reason_code |
| 14 | 跨模型评审分数 ≥ 6/10 + kill-argument 反自欺 PASS | 分数 < 6 回退 Phase 6（最多 4 轮）；反自欺 FAIL 回退 Phase 10 |
| 15 | 所有引用通过 3 层防幻觉验证 | 失败 → 删除虚构引用 + 回退 Phase 4 重搜 |
| 16 | 产物归档完整 | 缺失产物回退相关阶段 |

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

On successful completion, the orchestrator produces the following structure under `{problem_id}/`:

```
{problem_id}/
├── PIPELINE_STATUS.md           ← execution report (17-phase trail)
├── refine-logs/
│   ├── FINAL_PROPOSAL.md        ← frozen Q-id + selected idea (Phase 2)
│   ├── IDEA_CANDIDATES.md       ← ranked idea list (Phase 2)
│   ├── IDEA_DAG.json            ← DAG structure (Phase 2) — 可渲染为 Mermaid 可视化
│   ├── IDEA_DAG_VISUAL.md       ← DAG 可视化报告 (Mermaid 格式，Phase 2)  ← 新增
│   └ MCTS_LOG.md                ← MCTS iteration log (Phase 2)
├── refine-logs/
│   └ novelty_report.json        ← 3-axis evaluation (Phase 3)
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
│   └ REVIEW_LEDGER.json        ← machine-readable ledger (Phase 14)
├── citation_audit/
│   └ CITATION_AUDIT.md          ← 3-layer citation audit (Phase 15)
│   └ CITATION_AUDIT.json        ← machine-readable verdict (Phase 15)
└── output/
    └ FINAL_ARTIFACTS.md         ←归档索引 (Phase 16)
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

## 6-State Verdict Schema

The orchestrator uses the 6-state machine defined in [`assurance-contract.md`](../shared-references/assurance-contract.md) for each phase boundary:

| State | Meaning | Orchestrator action |
|-------|---------|---------------------|
| `PASS` | Phase complete, proceed | Advance to next phase |
| `WARN` | Phase complete with caveat | Proceed, but log the caveat + ensure downstream addresses it |
| `FAIL` | Phase failed | Trigger fallback (bounded 3 rounds) |
| `NOT_APPLICABLE` | Phase doesn't apply (e.g., Phase 11 if no figures needed) | Skip (treat as PASS) |
| `BLOCKED` | Prerequisite missing OR fallback exhausted | Halt + surface to human |
| `ERROR` | Skill itself failed | Halt + surface to human |

The overall pipeline verdict = the **worst** verdict across all 17 phases: `ERROR > BLOCKED > FAIL > WARN > NOT_APPLICABLE > PASS`.

## Anti-Deadloop Escalation (Universal, reused from paper-compile E16)

The bounded 3-round fallback is itself bounded by a hard escalation ladder. Do NOT loop on the same failure for more than 2 fix attempts:

1. **Attempt 1**: apply the standard fix for the failure type
2. **Attempt 2**: if the same failure persists, escalate the fix approach (different method, broader scope, alternative tool)
3. **Attempt 3 (BLOCKED)**: if the same failure STILL persists after a different fix attempt, emit `PIPELINE_STATUS.json` with `verdict: BLOCKED, reason_code: unresolved_<phase>_<failure_type>, attempts: 3` and surface to the human user with the exact failure, the attempted fixes, and a recommendation. **Do NOT silently retry past attempt 3.**

The 3-attempt cap applies per-failure-type, not per-phase. A phase with 5 distinct failure types gets up to 15 fix attempts total before BLOCKED, not 3.

Only the human user can waive a failure past attempt 3; the orchestrator never self-waives.

## Boundaries

- **Single-question execution only.** Each invocation processes exactly one Q-id supplied by the human user. Do NOT auto-iterate over all 125 questions. Do NOT auto-search the 125-problem index for "what to solve next" — the human decides.
- **No discipline branch.** OSS has one universal pipeline. Do not reintroduce economics / cs-ml / physics / general parallel pipelines or their frameworks (AIM / SOTA / PNV). The agent's runtime reasoning in `/theory-derivation` + `/dynamic-sandbox` handles domain-specific methodology.
- **Paradigm selection.** The agent selects the appropriate paradigm (formal/empirical/interpretive/design) in Phase 1 based on the problem's nature, not by domain label. See [`discipline-paradigm.md`](../shared-references/discipline-paradigm.md).
- **INV-G1 is non-negotiable.** The Q-id is frozen at Phase 0 and must be referenced in every downstream phase. If any phase's output lacks the Q-id reference, Phase 9 (`/invariant-check`) BLOCKs.
- **Forced human checkpoints at Phase 3→4 and Phase 5→6.** The agent cannot self-select the final idea (Phase 3) or self-approve the method registry (Phase 5). Wait for human confirmation.
- **3-round fallback limit is hard.** Do not exceed 3 rounds on the same failure type. If exhausted, BLOCK + surface to human.
- **The orchestrator never executes research.** It delegates to the corresponding skill. Do not inline derivation / verification / writing logic into this orchestrator.
- **Theory-only verification path.** When `verification_type=theory-only` (pure theory, no code/experiment):
  - Phase 5 (method-registry) → Phase 6 (theory-derivation with `engine=manual`) → Phase 7 (Type IV = NOT_APPLICABLE) → Phase 8 (logic-verification)
  - Phase 10 (result-to-claim): qualitative fidelity is the expected norm for theory-only problems
  - The derivation output is marked `[not machine-verified]` and the claim strength is adjusted accordingly

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## See Also

- [`../shared-references/assurance-contract.md`](../shared-references/assurance-contract.md) — 6-state verdict schema
- [`../shared-references/idea-dag-schema.md`](../shared-references/idea-dag-schema.md) — DAG node schema (Phase 2)
- [`../shared-references/mcts-search-protocol.md`](../shared-references/mcts-search-protocol.md) — MCTS iteration protocol (Phase 2)
- [`../shared-references/multi-fidelity-evaluation.md`](../shared-references/multi-fidelity-evaluation.md) — 3-fidelity filter (Phase 10)
- [`../shared-references/discipline-context.md`](../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/effort-contract.md`](../shared-references/effort-contract.md) — effort level definitions
- [`../meta-skills/idea-discovery/SKILL.md`](../meta-skills/idea-discovery/SKILL.md) — Phase 2
- [`../meta-skills/universal-retrieval/SKILL.md`](../meta-skills/universal-retrieval/SKILL.md) — Phase 4
- [`../meta-skills/unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) — Phase 11
- [`../support/method-registry/SKILL.md`](../support/method-registry/SKILL.md) — Phase 5
- [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) — Phase 6
- [`../support/leakage-audit/SKILL.md`](../support/leakage-audit/SKILL.md) — Phase 7
- [`../support/logic-verification/SKILL.md`](../support/logic-verification/SKILL.md) — Phase 8
- [`../support/invariant-check/SKILL.md`](../support/invariant-check/SKILL.md) — Phase 9
- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — Phase 10
- [`../support/paper-writing/SKILL.md`](../support/paper-writing/SKILL.md) — Phase 12
- [`../support/paper-compile/SKILL.md`](../support/paper-compile/SKILL.md) — Phase 13
- [`../support/auto-review-loop/SKILL.md`](../support/auto-review-loop/SKILL.md) — Phase 14
- [`../support/citation-audit/SKILL.md`](../support/citation-audit/SKILL.md) — Phase 15
- [`../support/quality-gate/SKILL.md`](../support/quality-gate/SKILL.md) — final pre-writing gate (Phase 12 boundary)
- [`../support/kill-argument/SKILL.md`](../support/kill-argument/SKILL.md) — Phase 14 anti-self-deception
