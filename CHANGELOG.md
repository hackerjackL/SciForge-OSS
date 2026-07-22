# Changelog

## [1.1.0] - 2026-07-22

### Engineering Grounding + 全仓统一

v1.1.0 是 v1.0.0 的稳定性增强和工程落地评估（Engineering Grounding, EG）正式发布版。**v1.1.0 = 之前 v3.0 系列全部工作的总和。**

### 核心变化

- **EG 第 6 维预筛轴**：idea-discovery 5-axis → 6-axis，新增 Engineering Grounding 列
- **Phase 5b EG 评估**：adversarial-falsification 新增 Phase 5b，产出 ENGINEERING_GROUNDING.md 报告（8 维子评分：Compute/Dev Cycle/Code Complexity/Repro Risk/Dependency/Capital/Temporal Maturity/Regulatory）
- **EG 复合评分权重**：novelty-check 公式更新为 `novelty×0.45 + feasibility×0.25 + relevance×0.15 + EG×0.15`
- **DAG schema**：idea-dag-schema.md v1.0→v1.1，新增 `engineering_grounding` 节点字段
- **21-phase 全仓统一**：20-phase → 21-phase（AGENT_GUIDE + 7 个契约文件 + orchestrator + problems）
- **EG 报告 AI 开发路线图**：支持 ai-dev-path PDF 图类型，自动出图
- **EG 领域 N/A 规则**：纯理论领域可标记 EG 为 N/A，跳过工程落地评估
- **competitive-analysis 5维→8维**：方案评估矩阵扩建
- **全仓 3维→4维**：novelty、feasibility、relevance + EG 新增
- **MCTS EG exploration bonus**：EG 低的 idea 在 MCTS 中获得额外探索奖励
- **根级 SKILL.md**：新增包描述文件
- **README 安装指南**：新增 3 种安装方式 + AI agent 配置说明

### 文件清单

- **文件总数**：74 个文件（22 SKILL.md + 36 shared-references + 1 orchestrator + 13 支持 + 文档 + 问题索引）
- **新增**：根 SKILL.md、competitive-analysis 8 维评估
- **删除**：临时方案文档（v3.0 清理）
- **修复**：EG 契约 5 处坏链、README 5 处 20-phase 残留、全仓 20→21 phase 统一

### 关键指标

| 指标 | 值 |
|------|------|
| 链接完整性 | 400+ 链接，0 坏链 |
| JSON 块 (strict) | 46 块，0 invalid |
| Skill 文件 | 22 个 SKILL.md |
| 共享契约 | 36 个 shared-references |
| Pipeline 阶段 | 21-phase DAG 闭环 |
| 学科覆盖 | 全领域 |
| 工程落地评估 | 8 维 EG 子评分 |
| Team 大小 | 1 人（全员） |
| 许可证 | MIT |

---

## [1.0.0] - 2026-07-21

### 首个正式发行版

SciForge-OSS 第一个正式发行版，涵盖从初始架构到完整功能的所有演进。**v1.0.0 = 之前的 v2.0.0 + v2.1.0 + ... + v2.9.0 全部工作的总和。**

### 核心能力

- **全领域支持**：框架不限定学科，通用 pipeline。物理学、数学、计算机科学、医学、经济学、教育学、材料科学、地球科学、天文等均可使用
- **DAG 驱动科研闭环**：20-phase DAG 循环，3 个 idea 并行探索 → MCTS 4 轮迭代 → Phase 2.5 证伪门控 → Phase 3 新颖性门控 → 收敛 → 推导 → 验证 → 写作 → 评审 → 输出
- **4 个元技能**：Dynamic Sandbox / Dynamic Tooling / Universal Retrieval / Unified Plotting
- **结构化自评审**：跨模型评审→单 agent 角色切换自评审（auto-review-loop, logic-verification, kill-argument, quality-gate）
- **三路验证路径**：理论-only / 计算 / 理论+实验
- **统一 elsarticle LaTeX 模板**，零警告零报错编译
- **Learner-first 签名**：Phase 1a `/domain-signature` 降级为 OPTIONAL hint，Phase 1b `/domain-learner` 升为 MUST 唯一真相源
- **TDAL 4 维联合置信度**：T × D × A × L，product 公式，锁定额度阈值 + floor constraints
- **Ouroboros 数据集成**：Basic（D 维可用性, Phase 2.5）+ Deep（T 维理论↔数据验证, Phase 6/10 闭环）
- **自适应 pipeline**：M1 强度自适应（REDUCED/STANDARD/INTENSIFIED/REPLACED/SKIPPED）+ M3 模式自动降级（MUST/CONDITIONAL/OPTIONAL/SKIP）
- **置信度提高机制**：3 机制（假设强度分析 + 替代路径分析 + 渐进式验证）bounded uplift loop，3 轮跨机制硬上限
- **竞品对标自动定期更新**：4 differentiator × 4 decay_state 转移 rubric，季度自动触发
- **社区贡献 PR 通道**：evidence_type 开放贡献 + 6 检 review 契约 + 3+3 falsification test gate

### 文件清单

- **22 个 SKILL.md**（6 元技能 + 13 支持 + 1 编排器 + 2 领域技能）
- **36 个 shared-references 契约文件**（TDAL schema、Ouroboros 集成、领域签名消费、领域自适应指南、自适应 pipeline、置信度提高、竞争 drift 监控、社区贡献协议等）
- **problems/125-SCIENCE-PROBLEMS.md**（125 题 Demo 索引，6 大类）
- 文档：README.md、AGENT_GUIDE.md、CHANGELOG.md、CONTRIBUTING.md、CITATION.cff

### 关键指标

| 指标 | 值 |
|------|------|
| 链接完整性 | 401 链接，0 坏链 |
| JSON 块 (strict) | 46 块，0 invalid |
| Skill 文件 | 22 个 SKILL.md |
| 共享契约 | 36 个 shared-references |
| Pipeline 阶段 | 20-phase DAG 闭环 |
| 学科覆盖 | 全领域（物理、数学、CS、医学、经济、教育、材料、地球科学、天文、化学、工程等） |
| Team 大小 | 1 人（全员） |
| 许可证 | MIT |

---

## Pre-release 开发历史

以下条目记录了从初始原型到正式版之前的演进过程。

### [2.9.0] - 2026-07-21

#### 核心转变
- **v2.8→v2.9**: 新增 Engineering Grounding (EG) 轴，解决"工程落地评判"盲区。6th pre-screen axis + 5 维子评分 + Phase 5b 工程落地估计 + 复合评分 0.15 权重 + 三段式下行保护。

#### 新增
- **EG 契约**: 新建 `shared-references/engineering-grounding-contract.md`，定义 5 维子评分 (Compute/Dependency/Team-Year/Repro Risk/Capital)、N/A 处理、BLOCKED 规则、三段式 Engineering Path。
- **6th pre-screen axis**: `idea-discovery/SKILL.md` 5-axis → 6-axis，新增 Engineering Grounding 列。
- **Phase 5b**: `adversarial-falsification/SKILL.md` 拆分 Phase 5a (OSS Sandbox) + Phase 5b (EG Estimate)，产生 `ENGINEERING_GROUNDING.md` 报告。
- **复合评分权重**: `novelty-check/SKILL.md` 公式更新为 `novelty×0.45 + feasibility×0.25 + relevance×0.15 + EG×0.15`。
- **DAG schema**: `idea-dag-schema.md` v1.0→v1.1，新增 `engineering_grounding` 节点字段。
- **置信度拆分**: `result-to-claim/SKILL.md` Grounding Confidence 拆为 OSS Sandbox Grounding (重算) + Engineering Grounding (继承)。
- **Orchestrator**: `auto-pipeline/SKILL.md` 20→21 阶段，新增 Phase 2.5b 质量门控 + `ENGINEERING_GROUNDING.md` workspace。
- **竞争分析**: `competitive-analysis.md` 方案 2 标记为 ✅ 已实施。
- **包结构**: `SKILL.md` + `AGENT_GUIDE.md` shared references 30+ → 31+。

#### 修复
- EG1: competitive-analysis.md 方案 2 "实施复杂度" roadmap 从未落地 → 已实施
- EG2: 多阶段 "20-phase" 残留 → 21-phase

### [2.8.0] - 2026-07-21

#### 核心转变
- **v2.7→v2.8**: 从"规则驱动"升级为"学习驱动 + 自适应 pipeline + 置信度可提高"。落地用户上一条回复中短期/中期/长期三档路线图全部实现。

#### 短期 (S1-S3)
- **S1 — Learner-first 签名**: Phase 1a 降级为 OPTIONAL 快路径 hint；Phase 1b 升为 MUST 唯一真相源。
- **S2 — TDAL 4 维联合置信度 schema 锁定**: 新建 `domain-adaptation-contract.md`，锁定 T×D×A×L 公式 + 权重 + 阈值 + 契约。
- **S3 — Ouroboros 基础集成**: 重写 `ouroboros-integration.md`，新增 Phase 1 seed + Phase 2.5 spec + Phase 10 TDAL D-dim wiring。

#### 中期 (M1-M3)
- **M1 — 领域自适应 pipeline 强度**: 新建 `domain-adaptive-pipeline.md`，按 evidence_type × paradigm 动态调整 Phase 5/6/11 强度。
- **M2 — 置信度提高机制**: 新建 `confidence-uplift.md`，3 机制 bounded uplift loop。
- **M3 — pipeline 自适应降级**: 新建 `pipeline-adaptive-degradation.md`，phase mode 从签名自动算出。

#### 长期 (L1-L3)
- **L1 — 社区贡献 PR 通道**: 新建 `domain-contribution-protocol.md`。
- **L2 — Ouroboros 深度集成**: 新建 `ouroboros-deep-integration.md`，T 维新增 0.2 权重 `theory_data_validation` 组件。
- **L3 — 竞品对标自动定期更新**: 新建 `competitive-drift-monitor.md`。

#### 修复 (v2.7 残留 + 历史债务)
- E17: orchestrator "17-phase" 残留 → 20-phase
- E18: domain-learner 输出文件名自相矛盾 → 统一
- E19: result-to-claim 4 维置信度算术错误 → 修正
- E20: orchestrator See Also 漏链接 → 补全
- E21: result-to-claim "(新增)" 残留 → 替换
- E22: 全仓 173 处 Markdown 坏链 → 批修，最终验证 373 链接 0 坏链
- E23: 2 处 JSON template 块非法语法 → 修复，最终验证 46 JSON 块 0 invalid

### [2.7.0] - 2026-07-20

### Domain Learner + 4 维联合置信度
- 新增 meta-skill `/domain-learner`：从文献自动学习领域特性，替代硬编码签名。
- 双源签名传播：Phase 1a `/domain-signature` + Phase 1b `/domain-learner`。
- 4 维联合置信度：理论(T) × 数据(D) × 领域适配(A) × 文献支持(L)。

### [2.6.0] - 2026-07-20

### 领域自适应执行指南
- 新增 `domain-adaptation-execution.md`：7 步执行指南 + 错误恢复表 + 快速参考卡。

### [2.5.0] - 2026-07-20

### Ouroboros 集成 + 验收测试 + 竞争分析
- **Ouroboros Data-Insight 集成**：新增 `ouroboros-integration.md`。
- **领域适配验收测试**：新增 `domain-adaptation-test.md`，6 个验收测试用例。
- **竞争分析**：新增 `competitive-analysis.md`。

### [2.4.0] - 2026-07-20

### 强制启动协议 + Pipeline Integrity + Fantasy Prevention + 5 领域示例
- **强制启动协议**：新增 `startup-protocol.md`。
- **Pipeline Integrity Check**：新增 `pipeline-integrity.md`。
- **Fantasy Prevention Protocol**：新增 `fantasy-prevention.md`，5 门幻想检测系统。
- **5 领域具体示例**：新增 `domain-adaptation-examples.md`。

### [2.3.0] - 2026-07-20

### 领域签名自动消费链路 + 端到端领域自适应
- **核心改造：领域签名消费链路 (wiring layer)**：新增 `domain-signature-consumer.md` 协议。
- **端到端流程验证**：经济学 / 数学 / 医学 三领域验证。

### [2.2.0] - 2026-07-20

### 领域特征自提取 + 失败模式库 + 优雅降级 + 数据可用性 + 自适应写作
- **A — 领域特征自提取**：新增 `domain-signature` skill。
- **B — 领域失败模式库**：新增 `domain-failure-modes.md`，6 大类 40+ 已知失败模式。
- **C — 优雅降级协议**：orchestrator 新增 MUST/OPTIONAL/CONDITIONAL 三级 phase mode。
- **D — 数据可用性检查**：adversarial-falsification 新增 Phase 6 数据清单。
- **E — 领域自适应写作**：discipline-writing 更新，5 种 evidence_type 自动选择写作风格。

### [2.1.0] - 2026-07-20

### 证伪驱动 + 落地置信度 + 上下文压缩 + 领域范式 + 性能优化
- **核心改进 (P0: 落地性)**：证伪驱动（adversarial-falsification 前置）+ 落地置信度 + 上下文压缩 60%。
- **领域范式 (P1)**：5 种 evidence_type 范式定义 + 签名驱动视角权重。
- **性能优化 (P2)**：MCTS 有界轮次 + 文献检索结果缓存 + 数值沙盒内存上限。

### [2.0.0] - 2026-07-20

#### 重大变更
- **全领域支持**: 框架不限定学科。
- **结构化自评审**: 跨模型评审→单 agent 角色切换自评审。
- **理论验证路径**: 新增理论-only / 计算 / 理论+实验 三路验证路径。
- **DAG 可视化**: 新增 IDEA_DAG_VISUAL.md。

#### 新增
- LaTeX 模板文件: `main.tex` + `math_commands.tex`
- 工具模板库: symbolic-reasoner, statistical-modeler, knowledge-graph, formal-verifier, code-synthesizer, data-transformer, text-analyzer
- 理论论文写作模式: 新增 `theory_only` 结构分支
- 理论图表类型: commutative-diagram, derivation-tree, concept-map, dependency-graph, counterexample-plot
- 文档: CONTRIBUTING.md, CHANGELOG.md, CITATION.cff, .gitignore

#### 修复
- F1: DAG 路径统一 (`dag/`→`refine-logs/`)
- F3: LaTeX 模板补充
- F4: cross-review Phase 编号修复
- P0-1: auto-review-loop 路径引用修复
- P0-3: kill-argument 读取源修复
- A3/A4: result-to-claim 路径修复

#### 删除
- `cross-review/SKILL.md`（合并入 auto-review-loop）
- 跨模型评审相关引用简化

### [1.0.0] - 2026-07-19

#### 初始版本
- 单编排器架构 (auto-pipeline)
- 6 个元技能 + 13 个支持技能
- 16 个共享契约
- 17 阶段 DAG 循环（v2.8 升级为 20-phase：补 Phase 1a/1b domain signature + Phase 2.5 adversarial falsification）