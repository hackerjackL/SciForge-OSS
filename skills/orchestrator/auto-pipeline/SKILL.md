---
name: auto-pipeline
version: 1.1.1
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

- **Entry point**: `/auto-pipeline "Q001: 问题描述" — effort: max`
- **Scope**: 单题执行，21 阶段 DAG 循环，全领域通用
- **Output**: 完整论文 (LaTeX/PDF) + 所有中间产物
- **Key**: 单题执行，不迭代问题索引，人类提供 Q-id；Phase 2.5 强制证伪；Phase 3→4 和 Phase 5→6 需人类审批
- **Optional flags**: `test_mode=true` (auto-waive the 2 human checkpoints for end-to-end stress testing — see TEST_MODE exemption below); `language=chinese`; `effort=lite|balanced|max|beast`

## Use When

Use this skill when the AI scientist needs to solve **one** user-supplied research problem end-to-end (fully autonomous research). This is the **only entry orchestrator** — it does not branch by discipline; it uses the DAG architecture to handle any scientific domain via universal meta-skills.

Typical prompts:
- "Solve Q001" / "解决 Q001：宇宙的起源与演化"
- "run the full pipeline on Q042"
- "帮我完整研究 Q015"

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
     │  → 输出 refine-logs/domain-signature-hint.json (临时 hint，置信度可能 < 0.7)
     │  → 仅用作 learner 的 prior / 冷启动种子；不直接被下游消费
     ↓
Phase 1b: /domain-learner (MUST, literature-based learning)  ← 唯一真相源
     │  → 从文献 + 种子论文从零学习领域特性
     │  → 读取 hint.json 作为 prior（若存在）+ 自主文献检索修正
     │  → 输出覆盖 refine-logs/domain-signature.json (下游唯一消费源)
     ↓
refine-logs/domain-signature.json (written ONLY by Phase 1b)
     ↓
Phase 2:  /idea-discovery        → 读取签名 → 调整视角权重
Phase 2.5: /adversarial-falsification → 读取签名 → 加载领域失败模式 + 校准 EG 子维 N/A 判定
Phase 2.5b: (Phase 5b EG) → 读取签名 → 领域特定 EG 子维加权（Compute/N/A 判定）
Phase 3:  /novelty-check         → 读取签名 → 调整评估权重
Phase 5:  /method-registry       → 读取签名 → 调整假设评分标准
Phase 6:  /verification-routing  → 读取签名 → 路由判定（experiment-first 默认 / theory-only 例外 / hybrid）→ 写 VERIFICATION_ROUTING.json，再分发 Phase 6a/6b/6c
Phase 10: /result-to-claim       → 读取签名 → 校准置信度
Phase 12: /paper-writing         → 读取签名 → 选择写作风格/引用格式
```

**Key design (v2.8 — learner-first)**: Phase 1b is **mandatory** and is the only writer of `domain-signature.json`. Phase 1a is **optional** and writes a separate `domain-signature-hint.json` consumed only by the learner as a prior. This eliminates the "rule-hardcoded signature" failure mode: even when 1a's rules match cleanly, the learner still re-derives the signature from literature to catch rule mismatches. Each downstream skill reads `domain-signature.json` independently at startup. If the signature doesn't exist (learner failed), all skills use default behavior — the pipeline continues but flags reduced domain adaptation.

## Performance Optimizations

### Parallelization

Where possible, phases run in parallel to reduce wall-clock time:

| Parallel Group | Phases | Rationale |
|---------------|--------|-----------|
| **Group A** | Phase 2 (idea-discovery) + Phase 4 (universal-retrieval) | Literature search does not depend on idea generation output. **B1 硬性串行化 (v2.3)**: Phase 2 拆两段——Round 1 (idea 生成) 可与 Phase 4 文献检索并行；但 **novelty 预筛 (6-axis 中 novelty 轴) 与 Round 2-4 评估必须等 Phase 4 完成**（读到 `literature/references.bib` 才跑 novelty 轴，禁止用空 bib 预筛或先斩后奏）。若 Phase 4 WARN/空文献，novelty 轴标记 `pending-literature` 并如实记录，不静默降级为猜测。 |
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
Phase  0: 加载问题（冻结 Q-id — INV-G1 锚点）
     │
Phase  1: 问题理解与分解（内置推理）[MUST]
     │
     ├───────────────── DAG 分支 ─────────────────┐
     │                                             │
Phase  1a: /domain-signature 领域特征提取 [OPTIONAL] ← v2.8 降级为快路径 hint
     │  分析问题文本 → 提取领域 hint (rule-based)    │
     │  输出 refine-logs/domain-signature-hint.json  │
     │  (不直接被下游消费，仅供 Phase 1b 作 prior)    │
     │                                             │
Phase  1b: /domain-learner 领域学习 [MUST] ← v2.8 升为唯一真相源
     │  从文献 + 种子论文从零学习领域特性           │
     │  (literature search + seed paper analysis)   │
     │  读取 hint.json 作 prior + 自主检索修正      │
     │  输出 refine-logs/domain-signature.json      │
     │  (下游唯一消费源；learner confidence 阈值 0.7)│
     │                                             │
Phase  2: /idea-discovery [DAG 分支] [MUST] — 3 视角 idea
     │  (theoretical / computational / qualitative)   │
     │  + MCTS 迭代 (4 轮, 8-12 root nodes)           │
     │  + 输出 verification_type (理论-only / 计算 / 理论+实验)
     │                                             │
Phase  2.5: /adversarial-falsification [证伪门控] [MUST]
     │  6 维度攻击: 假设评分 → 反例构造 → 文献对抗    │
     │  → 类比映射 → 沙盒可行性 → 工程落地 → 数据可用性 │
     │  SURVIVE → 继续; WEAKENED → 回退 Phase 2      │
     │  FALSIFIED → 淘汰 (记录原因, 不再进入推导)     │
     │                                             │
     │  Phase 5a: OSS Sandbox Feasibility (沙盒能否跑)│
     │  Phase 5b: AI Engineering Grounding (AI 能否落地)│
     │                                             │
Phase  3: /novelty-check [DAG 门控] [MUST] — 4 维评估 + 淘汰
     │  (新颖性×0.45 + 可行性×0.25 + 相关性×0.15 + 工程落地×0.15)│
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
Phase  6: /verification-routing — 验证路由判定 [MUST]                ← v5.0
     │  读 domain-signature.evidence_type + 可计算性信号 →
     │  experiment-first（默认）/ theory-only（例外：derivational ∧ 无可执行计算）/ hybrid
     │  → 写 refine-logs/VERIFICATION_ROUTING.json（route/evidence_type/reason）
     │  见 shared-references/verification-routing.md
     │
Phase  6a: /theory-derivation — 符号推导 + 逐步机器验证 [ROUTED]
     │  theory-only / hybrid → MUST（主验证或并行主验证）
     │  experiment-first → OPTIONAL 辅助（有推导结构才走；不阻塞、不强制全步 SymPy）
     │          ↻ 失败回退 Phase 1（最多 3 轮）
     │          (theory-only: engine=manual, 标记为 [not machine-verified])
     │
     │  ── 实验执行层 (v2.0, v5.0 默认主验证) ──
     │
Phase  6b: /experiment-execution --stage=toy [ROUTED]                 ← v2.0/v5.0
     │  玩具实验：最小规模（~20 轮量级）验证"想法方向对不对"（想法生死判）
     │  (theory-only → SKIP; experiment-first/hybrid → MUST)
     │  前台硬上限 5 分钟；预计 > 5 分钟 → 也挂后台 (toy_bg)
     │  Gate: PASS → Phase 6c; FAIL → KILL-or-PIVOT 决策（见 experiment-execution
     │  从 0 到 1 停止协议；负向显著且 ≥2 种子可复现才触发；PIVOT ≤2 次预算）
     │  (toy_bg 完成后再判 Gate，不等前台)
     │
Phase  6c: /experiment-execution --stage=full --background [ROUTED]  ← v2.0/v5.0
     │  全量实验：后台调度 (tmux/nohup/systemd)；按 method-registry §3 强制实验矩阵执行
     │  (theory-only → SKIP; experiment-first/hybrid → MUST)
     │  Dispatch → 立即返回，pipeline 继续
     │  v5.1 完成判据：实验完成时读取 Return payload 的 budget_floor——
     │  satisfied=false → verdict 只认 IN_PROGRESS/BLOCKED，不得进 Phase 10
     │  （"未消耗最低探索预算不得宣布完成"；completion_justification 见
     │  experiment-execution Step 6 探索预算下限）
     │
Phase  7: /leakage-audit — Type I 逻辑漏洞 + Type IV 逃逸审计
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
Phase 15.5: /publishability-score — 可发表性评分 (dim1 首轴门控)     ← 新增 v2.2
     │         产出 PUBLISHABILITY_SCORE.json/md
     │
Phase 16: 最终组装 + 产物归档
```

**回退契约**: 每阶段失败回退到最近的前置阶段（最多 3 轮）。3 轮失败升级到 BLOCKED + `reason_code`（复用主仓库 `paper-compile` E16 反死循环阶梯）。**永不静默重试到第 4 轮**——3 轮上限是硬约束。

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
| 0: 加载问题 | MUST | — |
| 1: 问题理解 | MUST | — |
| 1a: domain-signature | OPTIONAL | v2.8 降级为快路径 hint，输出 domain-signature-hint.json；learner 不可用时禁用 |
| 1b: domain-learner | MUST | v2.8 升为唯一真相源；读取 hint.json 作 prior，输出 domain-signature.json |
| 2: idea-discovery | MUST | — |
| 2.5: adversarial-falsification | MUST | — |
| 2.5b: adversarial-falsification Phase 5b (EG) | MUST | ENGINEERING_GROUNDING.md 必产；HEAVY/CONSTRAINED 全量输出，READY 简化版 |
| 3: novelty-check | MUST | — |
| 4: universal-retrieval | MUST | v2.2: 不可跳过 — 即使 theory-only 也必须跑（理论问题需查重避免重复证明）；走 mihomo 代理（规则模式）访问 arxiv/s2/crossref |
| 5: method-registry | MUST | — |
| 6: verification-routing | MUST | v5.0: Phase 6 入口路由判定 → VERIFICATION_ROUTING.json（experiment-first 默认） |
| 6a: theory-derivation | ROUTED | v5.0: theory-only/hybrid → MUST；experiment-first → OPTIONAL 辅助（不阻塞） |
| 6b: experiment-execution (toy) | ROUTED | v5.0: theory-only → SKIP；experiment-first/hybrid → MUST（想法生死判，FAIL → KILL-or-PIVOT） |
| 6c: experiment-execution (full+bg) | ROUTED | v5.0: theory-only → SKIP；experiment-first/hybrid → MUST（background dispatch + 强制实验矩阵） |
| 7: leakage-audit | MUST | — |
| 8: logic-verification | MUST | — |
| 9: invariant-check | MUST | — |
| 10: result-to-claim | MUST | — |
| 11: unified-plotting | MUST | v2.2: 图非可选——每篇论文至少 1 图（架构图/结果图）；无数据图时至少画 1 个 pipeline/概念图 |
| 12: paper-writing | MUST | — |
| 13: paper-compile | MUST | v2.2: 零警告零报错强制（不可豁免）；装好 texlive 后真编译产 PDF |
| 14: auto-review-loop | MUST | v2.2: 自审查强制（角色切换 researcher→reviewer→adjudicator）；分数 < 6 回退 Phase 6/12（最多 4 轮）；不再可用 grounding-check 替代 |
| 15: citation-audit | MUST | — |
| 15.5: publishability-score | MUST | v2.2 新增：最终可发表性评分（主实验逻辑到位为首要轴）；产出 PUBLISHABILITY_SCORE.json/md |
| 16: 最终组装 + 清洁度审计 | MUST | v2.2: 加 project-architecture-contract 清洁度审计（orphan 文件/空目录/README 完整性） |

### Degradation Rules

1. **OPTIONAL phase fails** → Log WARN with reason, skip to next phase, continue pipeline
2. **MUST phase fails after 3 rounds** → BLOCKED, surface to human with complete failure trace
3. **CONDITIONAL phase** → Check condition before running. If condition not met, skip with WARN
4. **paper-compile** (v2.2: now MUST, zero-warnings non-negotiable) → 零警告零报错强制；装好 texlive 后真编译产 PDF；警告不豁免（旧的可降级规则已废除）；3 attempt per-warning 反死循环阶梯后仍 FAIL → BLOCKED + 人工
5. **auto-review-loop** (v2.2: now MUST) → 自审查强制，3 轮角色切换 (researcher→reviewer→adjudicator)；不再可用 grounding-check 替代；分数 < 6 回退 Phase 6/12（最多 4 轮）
6. **unified-plotting** (v2.2: now MUST) → 每篇论文至少 1 图（架构图/结果图/概念图）；无数据图时画 1 个 pipeline/概念图（d2 或 tikz）

## Quality Gates (Explicit Per-Phase)

| 阶段 | 门控条件 | 失败处理 |
|------|---------|---------|
| 0 | Q-id 清晰可解、来自人类提示词 | 请求用户澄清 Q-id；**不**自动搜索问题索引 |
| 1 | 问题可分解为形式化陈述 | 请求用户澄清问题边界 |
| 2 | 至少生成 1 个 idea (MCTS 收敛) | 放宽 perspectives 重评；再失败升级 BLOCKED |
| 2.5 | 证伪攻击: 假设健康度 ≥ 6 OR 无反例 | WEAKENED → 回退 Phase 2 重生成；FALSIFIED → 淘汰（记录原因） |
| 2.5b | Engineering Grounding 报告输出（Phase 5b）: ENGINEERING_GROUNDING.md 生成 | 仅 HEAVY/CONSTRAINED 必需输出；BLOCKED 淘汰（子维 = 0）
| 3 | DAG 收敛到 1 个幸存者 (≥ 0.6 idea-fit) | 放宽 strictness 重评；再失败升级 BLOCKED |
| — | **强制人类审批**：从幸存者中选最终 idea | 等待人类确认；agent 不能自选 |
| 4 | 文献搜索完成 + 3 层验证通过 + 筛选链(真+全)完整性核 PASS | v2.2: **不可跳过**——即使 theory-only 也必须跑（理论问题需查重避免重复证明）；空则 WARN 但继续（需人工补救文献）；筛选链核：每篇引用至少 1 层验证 + 无 orphan 引用 + 引用覆盖核心 claim |
| 5 | 方法 registry 构建完成 + hash 锁 + **强制人类审批** | 请求用户审批 Section 3；agent 不能自批 |
| 6 | SymPy 推导成功 + 逐步机器验证 PASS | 回退 Phase 1（最多 3 轮） |
| 6b | 玩具实验 RESULT.json status=PASS + core_claim_validated=true | FAIL → BLOCKED (kill idea); TIMEOUT/ERROR → 1 retry; INCONCLUSIVE → 1 redesign retry |
| 6c | 全量实验 DISPATCH.json 生成 + 后台进程启动确认 + **v5.1 budget_floor.satisfied**（路线探索≥2 或否决证据 + 矩阵 100% + 种子足额 + 失败留痕 + completion_justification） | 无后台方法 → BLOCKED; 启动失败 → 1 retry; theory-only → SKIP; budget_floor 不满足 → IN_PROGRESS（继续探索，不得进 Phase 10） |
| 6c-BA | 全量实验完成且 STATUS.json verdict=FAIL（toy 曾 PASS） | **v2.2.1 BA**: 回退 Phase 2 重生成 idea（bounded 2 轮）—见 [idea-discovery BA 机制](../../meta-skills/idea-discovery/SKILL.md) |
| 7 | Type I 无 CRITICAL + Type IV 无 ESCAPE | CRITICAL → callback Phase 5 (3 轮上限)；再失败升级 BLOCKED + LOGIC_GAP_FUNDAMENTAL_ISSUE |
| 8 | 6 维度逻辑审计 PASS (零 FATAL/CRITICAL) | FATAL/CRITICAL 回退 Phase 6（最多 3 轮）；**FATAL=实验数据与推导结论矛盾 → v2.2.1 BA 回 Phase 2**（bounded 2 轮） |
| 9 | INV-G1 Q-id 冻结 + 在当前产物中引用 | FAIL → 重新锚定 Q-id (Phase 0) |
| 10 | 至少 1 个主结果达到 ≥ numerical 保真度 | qualitative-only → reframe 为 conjecture；numerical 缺失 → 回退 Phase 6 |
| 11 | (可选) 图表遵循莫兰迪色系 + Layer 2 数据热图 | 色系违规 → 重生成；非数据图无强制 |
| 12 | 论文非空 + 统一 elsarticle 模板 + 引用都来自验证列表 | 空则回退 Phase 1；模板违规回退 Phase 12 |
| 13 | LaTeX 编译零警告零报错 (submission 级) | 反死循环阶梯：3 attempt per-warning → BLOCKED + reason_code |
| 14 | 跨模型评审分数 ≥ 6/10 + kill-argument 反自欺 PASS | 分数 < 6 回退 Phase 6（最多 4 轮）；反自欺 FAIL 回退 Phase 10；**kill-argument 站住(claim 被自身实验否定) → v2.2.1 BA 回 Phase 2**（bounded 2 轮） |
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

On successful completion, the orchestrator produces the following structure under `{problem_id}/` (21-phase trail). **v2.2**: the full GitHub-style layout, README.md/MANIFEST.md contracts, workspace-hygiene rules, and the Phase 16 cleanliness audit are defined in [`project-architecture-contract.md`](../../shared-references/project-architecture-contract.md) — that contract applies to every run (auto-pipeline OR partial skill invocation). Summary tree:

```
{problem_id}/
├── PIPELINE_STATUS.md           ← execution report (21-phase trail)
├── refine-logs/
│   ├── FINAL_PROPOSAL.md        ← frozen Q-id + selected idea (Phase 2)
│   ├── IDEA_CANDIDATES.md       ← ranked idea list (Phase 2)
│   ├── IDEA_DAG.json            ← DAG structure (Phase 2) — 可渲染为 Mermaid 可视化
│   ├── IDEA_DAG_VISUAL.md       ← DAG 可视化报告 (Mermaid 格式，Phase 2)  ← 新增
│   ├── ENGINEERING_GROUNDING.md ← Engineering Grounding report (Phase 5b)  ← 新增 v2.9
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
│   └ PUBLISHABILITY_SCORE.json  ← publishability score (Phase 15.5)  ← 新增
│   └ PUBLISHABILITY_SCORE.md    ← human-readable score report (Phase 15.5)  ← 新增
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

**约束重注入（v5.1 — Constraint Re-injection，源自 CRUX 影子评估失败模式 #5）**:

**背景**（arXiv:2607.27191）：关于最短探索时间、审稿节奏、页数限制等硬规则，agent 早期会一字不差地复述，但在六天长程运行中**逐渐遗忘**——"长期目标管理，依然是大模型的阿喀琉斯之踵"。上下文压缩与长程运行天然侵蚀约束记忆，必须结构性重注入，不能依赖 agent 自觉记住。

**强制机制**（orchestrator 在每个 phase boundary 执行，写入 `logs/pipeline.log`）:
1. **硬约束清单重读**：每过一个 phase boundary，orchestrator 重新读取并显式复述以下硬约束清单到当前上下文（不是摘要，是原文复述）：验证路由（VERIFICATION_ROUTING.json 的 route）、探索预算下限（budget_floor 五检查项）、页数档位上限（length 档）、强制实验矩阵（EXPERIMENT_MATRIX.json 的组清单）、PIVOT 剩余预算（≤2 的当前余量）、负结果纪律（polarity 规则）
2. **漂移检测**：每个 phase 的输出产物必须携带其消费/产出的硬约束字段（如 CLAIMS_FROM_RESULTS.md 带 evidence_sufficiency、REVIEW_STATE.json 带 response_class、compile 产物带页数 verdict）——缺字段即该 phase verdict 降级 WARN（`constraint_field_missing`），连续 2 个 phase 缺同类字段 → BLOCKED 上报人类（这是指令漂移的结构性信号）
3. **完成宣告拦截**：任何 phase 宣告完成（PASS）时，orchestrator 核对该 phase 的硬约束字段齐全且达标——不齐 → 不接受 PASS，降级为 IN_PROGRESS 并要求补齐。这是"我写完了"的结构性拦截器

The orchestrator uses the 6-state machine defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md) for each phase boundary:

| State | Meaning | Orchestrator action |
|-------|---------|---------------------|
| `PASS` | Phase complete, proceed | Advance to next phase |
| `WARN` | Phase complete with caveat | Proceed, but log the caveat + ensure downstream addresses it |
| `FAIL` | Phase failed | Trigger fallback (bounded 3 rounds) |
| `NOT_APPLICABLE` | Phase doesn't apply (e.g., Phase 11 if no figures needed) | Skip (treat as PASS) |
| `BLOCKED` | Prerequisite missing OR fallback exhausted | Halt + surface to human |
| `ERROR` | Skill itself failed | Halt + surface to human |

The overall pipeline verdict = the **worst** verdict across all 20 phases: `ERROR > BLOCKED > FAIL > WARN > NOT_APPLICABLE > PASS`.

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
  - **TEST_MODE checkpoint bypass (v2.2 — 规避而非跳过).** When the invocation carries `test_mode=true` (set by the human for autonomous end-to-end stress testing), the 2 human checkpoints are **bypassed, NOT skipped**: the agent still performs the EQUIVALENT work each checkpoint guards (selects the top MCTS survivor as the final idea; builds the method registry + hash lock), but records the bypass in `APPROVAL_LOG.txt` with `bypassed_by=test_mode, original_checkpoint=Phase 3→4 / Phase 5→6, agent_action_taken=auto-selected/auto-approved, human_review_status=PENDING_DEFERRED`. The bypass is **provisional** — `PIPELINE_STATUS.json` flags `checkpoints_bypassed: true, human_review_deferred: true, production_ready: false` so a human MUST later confirm both decisions before the run is considered production-grade. The work the checkpoint guards is done (idea selected, method registry built) — only the human-approval step is deferred, never the underlying quality control. All other phases (INV-G1, fallback cap, toy gate, background dispatch, zero-warnings compile) remain HARD even in TEST_MODE. TEST_MODE is for stress-testing the pipeline mechanics; production runs MUST keep both checkpoints human-gated with no bypass.
  - **`human_skip` vs `test_mode` (when to use each)**:
    - `human_skip=true` — human has **decided** to delegate both checkpoints, run is production-grade, no later confirmation needed. Use for autonomous production runs where the human trusts the agent's judgment.
    - `test_mode=true` — human is **stress-testing** the pipeline mechanics, run is NOT production-grade, later confirmation required. Use for testing/debugging the pipeline itself.
    - Neither flag — both checkpoints are human-gated (wait for explicit confirmation at Phase 3→4 and Phase 5→6). The default, and the safest.
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
  - **HARD (non-negotiable)**: INV-G1 freeze, forced human checkpoints (Phase 3→4, 5→6), 3-round fallback cap, toy gate FAIL = kill idea, background dispatch for full experiments
  - **FLEXIBLE (agent discretion)**: MCTS round count (default 4, may reduce if convergence is clear), experiment scale_ratio, toy experiment design, strictness thresholds, effort level

## Output Protocols

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
