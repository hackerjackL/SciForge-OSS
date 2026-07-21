# Changelog

## [2.9.0] - 2026-07-21

### v2.8「最后一公里」收尾

v2.8 改了引擎但没换说明书——本轮统一入口文档与编排器实际状态，并补齐 CHANGELOG 版本断层。

#### 文档一致性修复（P0）

- **E24 — Phase 数顶层文档统一**: AGENT_GUIDE.md 5 处 + README.md 3 处 + CHANGELOG 1 处的 "17-phase / 17 阶段" 全改 "20-phase / 20 阶段"。修复 v2.8 E17 只改 orchestrator 内部、漏改入口文档的半截修复。
- **E25 — README 版本徽章**: `version-2.0.0` → `version-2.9.0`，与 CHANGELOG 头节同步。
- **E26 — CHANGELOG 版本断层补遗**: 补录 v2.1-v2.7 共 7 个版本的简要记录（git commit log 提炼），消除 CHANGELOG 从 [2.0.0] 直接跳 [2.8.0] 的 8 版本断层。

#### README 结构修复（P1）

- **E27 — README 项目结构 auto-review-loop 重复**: 第 166/172 行重复列同一文件，删除冗余行。

#### shared-references 结构梳理（P1）

- **E28 — `domain-*` 系列 7 文件梳理**: (a) 每个文件 Status 行补 v2.x 版本标签，明确是 v2.7 遗产还是 v2.8 新写；(b) `domain-adaptation-examples.md` / `domain-adaptation-execution.md` / `domain-adaptation-test.md` 三件套（共 763 行）合并为单文件 `domain-adaptation-guide.md` 分节，砍重复叙述 ~40%。
- **E29 — Ouroboros 双文件合并**: `ouroboros-integration.md` (303 行) + `ouroboros-deep-integration.md` (310 行) 合并为单一 `ouroboros-integration.md`，内分 "Basic integration" / "Deep integration (L2)" 两节，消除两文件互相交叉引用造成的读取顺序歧义。

#### TDAL schema 澄清（P2）

- **E30 — TDAL 权重层级澄清**: `domain-adaptation-contract.md` 新增 "权重层级表"，显式区分两个层级：(a) TDAL 四维权重（T/D/A/L 在联合置信度中的占比）；(b) T 维内部子组件权重（symbolic / theory_data_validation / external_validation 等 4 子组件 0.3/0.25/0.25/0.2 分布）。消除 CHANGELOG v2.8 第 20 行 "T 维新增 0.2 权重 theory_data_validation" 的语义歧义。
- **E31 — adaptive-pipeline 双文件分工澄清**: `domain-adaptive-pipeline.md` (M1 强度) 与 `pipeline-adaptive-degradation.md` (M3 模式) 在 Status 行互相引用对方，明确"强度 vs 模式"正交分工。

#### README DAG 图示失真（P3）

- **E32 — README DAG 图示补全**: 第 68-77 行 DAG 图示补 MCTS 4 轮迭代 + Phase 2.5 证伪门控，消除原图只画"3 idea 并行"的简化失真。

#### 引用闭合 + 死目录清理（P3）

- **E33 — `problems/125-SCIENCE-PROBLEMS.md` stub 补建**: README/AGENT_GUIDE 多处引用但文件不存在，补 125 题占位索引 stub。
- **E34 — `skills/support/cross-review/` 死目录清理**: 该目录无 SKILL.md，是 v2.0 cross-review 合并入 auto-review-loop 后的残留死目录，删除。

### 文件清单 (v2.9 新增/修改/删除)

- **新增 (1)**: `problems/125-SCIENCE-PROBLEMS.md` (E33 stub)
- **合并新增 (2)**: `domain-adaptation-guide.md` (E28 三合一)、`ouroboros-integration.md` (E29 二合一重写)
- **修改 (9+)**: README.md、AGENT_GUIDE.md、CHANGELOG.md、domain-adaptation-contract.md、domain-adaptive-pipeline.md、pipeline-adaptive-degradation.md、domain-adaptation-examples.md（标记待删）、domain-adaptation-execution.md（标记待删）、domain-adaptation-test.md（标记待删）、ouroboros-deep-integration.md（标记待删）
- **删除 (4)**: `domain-adaptation-examples.md`、`domain-adaptation-execution.md`、`domain-adaptation-test.md`（合并入 guide）、`ouroboros-deep-integration.md`（合并入 integration）、`skills/support/cross-review/`（死目录）

### 关键指标更新

| 指标 | v2.8 | v2.9 目标 |
|------|------|-----------|
| 17-phase 残留 | 9 处顶层文档 | 0 处（E24） |
| CHANGELOG 版本断层 | 2.0→2.8 跳 8 版本 | 2.1-2.7 全补录（E26） |
| shared-references 文件数 | 41 个 | 36 个（4 删 + 1 新合并） |
| domain-* 命名前缀数 | 4 种（adaptation/adaptive/signature/failure） | 保留但 Status 行标注版本归属（E28） |
| ouroboros 入口数 | 2 个（integration/deep-integration 交叉引用） | 1 个单文件两节（E29） |
| TDAL 权重歧义 | 0.3/0.25/0.25/0.2 含义不清 | 权重层级表显式分层（E30） |
| problems/ 引用 | 引用不存在的 125-SCIENCE-PROBLEMS.md | stub 补建，引用闭合（E33） |
| 死目录 | cross-review/ 残留 | 删除（E34） |

---

## [2.7.0] - 2026-07-20

### Domain Learner + 4 维联合置信度
- 新增 meta-skill `/domain-learner`：从文献自动学习领域特性，替代硬编码签名。三步流程：文献搜索 → 种子论文分析 → 综合学习，学习失败优雅回退默认配置。
- 双源签名传播：Phase 1a `/domain-signature`（规则快速，置信度<0.7 触发）+ Phase 1b `/domain-learner`（文献学习，彻底但慢）。下游 skill 无感知，统一消费 `refine-logs/domain-signature.json`。
- 4 维联合置信度：理论(T) × 数据(D) × 领域适配(A) × 文献支持(L)，每维明确权重和计算方式。联合置信度 <0.3→UNSUPPORTED，0.3-0.5→WEAK，0.5-0.7→MODERATE，≥0.7→STRONG。

## [2.6.0] - 2026-07-20

### 领域自适应执行指南
- 新增 `domain-adaptation-execution.md`：7 步执行指南，Agent 可直接按步骤操作。每步包含具体 prompt 示例和验证检查点。
- 含错误恢复表和快速参考卡。

## [2.5.0] - 2026-07-20

### Ouroboros 集成 + 验收测试 + 竞争分析
- **Ouroboros Data-Insight 集成**：新增 `ouroboros-integration.md`，OSS 理论验证 ↔ Ouroboros 数据验证双向协议。数据需求规范 (OSS→Ouroboros) + 数据可用性报告 (Ouroboros→OSS)。联合置信度 = theoretical × data_availability × data_quality。
- **领域适配验收测试**：新增 `domain-adaptation-test.md`，6 个验收测试用例（经济学/数学/医学领域适配 + 幻想预防 + Pipeline 完整性 + Ouroboros 集成）。
- **竞争分析**：新增 `competitive-analysis.md`，全框架对比 + 5 个更高层面优化方案。当前能力矩阵 (A+) → 目标能力矩阵 (S)。

## [2.4.0] - 2026-07-20

### 强制启动协议 + Pipeline Integrity + Fantasy Prevention + 5 领域示例
- **强制启动协议**：新增 `startup-protocol.md`，每个 skill 启动时必须执行的 5 步协议，含验证日志 + 失败降级机制。
- **Pipeline Integrity Check**：新增 `pipeline-integrity.md`，每个 phase 执行前的 4 步完整性检查，含 16 个 phase 完整前置条件表。
- **Fantasy Prevention Protocol**：新增 `fantasy-prevention.md`，5 门幻想检测系统 + 5 级幻想判定 (GROUNDED→FANTASY) + 幻想日志。
- **5 领域具体示例**：新增 `domain-adaptation-examples.md`，经济学/数学/医学/物理/哲学 完整端到端流程。

## [2.3.0] - 2026-07-20

### 领域签名自动消费链路 + 端到端领域自适应
- **核心改造：领域签名消费链路 (wiring layer)**：新增 `domain-signature-consumer.md` 协议，定义所有下游 skill 如何消费领域签名。paper-writing 自动消费签名（写作风格/引用格式/章节结构），idea-discovery 视角权重根据 evidence_type 调整，adversarial-falsification 自动加载匹配的失败模式。
- **端到端流程验证**：经济学 (causal_inference→DiD 视角权重+内生性检查+AER 风格)、数学 (derivational→定理证明视角+隐藏假设检查+定理-证明结构)、医学 (experimental→实验设计视角+混杂检查+IMRaD)。无签名时所有 skill 使用默认行为（向后兼容）。

## [2.2.0] - 2026-07-20

### 领域特征自提取 + 失败模式库 + 优雅降级 + 数据可用性 + 自适应写作
- **A — 领域特征自提取**：新增 `domain-signature` skill，自动从问题文本提取领域签名 (evidence_type, methodology, writing_style, failure_modes, data_availability)。不硬编码领域分类，运行时自动推断。
- **B — 领域失败模式库**：新增 `domain-failure-modes.md`，6 大类 (causal_inference/experimental/correlational/derivational/simulational/interpretive) 40+ 已知失败模式。
- **C — 优雅降级协议**：orchestrator 新增 MUST/OPTIONAL/CONDITIONAL 三级 phase mode，OPTIONAL phase 失败不阻塞 pipeline。
- **D — 数据可用性检查**：adversarial-falsification 新增 Phase 6 数据清单 + 可用性评分 + 缺口影响分析，DATA_READY/DATA_LIMITED/DATA_BLOCKED 三级判定，理论-only 问题跳过检查。
- **E — 领域自适应写作**：discipline-writing 更新，5 种 evidence_type 自动选择写作风格，签名驱动引用格式/章节结构/论证风格。

## [2.1.0] - 2026-07-20

### 证伪驱动 + 落地置信度 + 上下文压缩 60% + 领域范式 + 性能优化
- **核心改进 (P0: 落地性)**：证伪驱动（adversarial-falsification 前置）+ 落地置信度（区分理论可证明/数据可验证/实验可执行）+ 上下文压缩 60%（refine-logs/ 精简 + Phase 间只传必要 schema）。
- **领域范式 (P1)**：5 种 evidence_type 范式定义 + 签名驱动视角权重。
- **性能优化 (P2)**：MCTS 有界轮次 + 文献检索结果缓存 + 数值沙盒内存上限。

---

## [2.8.0] - 2026-07-21

### 核心转变
- **v2.7→v2.8**: 从"规则驱动"（告诉 agent 每个领域是什么）升级为"学习驱动 + 自适应 pipeline + 置信度可提高"（让 agent 从文献自己发现领域特性 + pipeline 结构按签名动态调整 + 3 机制主动拉升 TDAL）。落地用户上一条回复中短期/中期/长期三档路线图全部实现。

### 短期 (S1-S3)
- **S1 — Learner-first 签名**: Phase 1a (`/domain-signature`) 降级为 OPTIONAL 快路径 hint，输出 `domain-signature-hint.json`；Phase 1b (`/domain-learner`) 升为 MUST 唯一真相源，写 `domain-signature.json`。消除"规则硬编码签名"失败模式。
- **S2 — TDAL 4 维联合置信度 schema 锁定**: 新建 `shared-references/domain-adaptation-contract.md` (208 行)，锁定 T×D×A×L 公式 + 权重 + 阈值 + producer/consumer/orchestrator 契约 + floor constraints。`result-to-claim` 节精简为引用 + producer 契约。
- **S3 — Ouroboros 基础集成**: 重写 `ouroboros-integration.md` (303 行)，新增 Phase 1 seed 基础层 + Phase 2.5 finalized spec + Phase 10 TDAL D-dim wiring + theory-only 路径 + fallback。

### 中期 (M1-M3)
- **M1 — 领域自适应 pipeline 强度**: 新建 `domain-adaptive-pipeline.md` (161 行)，按 evidence_type × paradigm 动态调整 Phase 5/6/11 强度 (REDUCED/STANDARD/INTENSIFIED/REPLACED/SKIPPED)。5 evidence_types × 3 phases 完整覆盖，混合域取最严。
- **M2 — 置信度提高机制**: 新建 `confidence-uplift.md` (314 行)，3 机制 (假设强度分析 + 替代路径分析 + 渐进式验证) bounded uplift loop，3 轮跨机制硬上限。从"评估 TDAL"升级为"提高 TDAL"。
- **M3 — pipeline 自适应降级**: 新建 `pipeline-adaptive-degradation.md` (192 行)，phase mode (MUST/CONDITIONAL/OPTIONAL/SKIP) 从签名自动算出，替代 v2.7 固定 Phase Mode Table。invariants 显式标注不可降级。

### 长期 (L1-L3)
- **L1 — 社区领域贡献 PR 通道**: 新建 `domain-contribution-protocol.md` (197 行)，开放 evidence_type 贡献通道 + 6 检 review 契约 + 14 天 SLA + 3+3 falsification test gate + case-by-case override 轻量路径。
- **L2 — Ouroboros 深度集成**: 新建 `ouroboros-deep-integration.md` (310 行)，basic vs deep 调用分离 + `theoretical-prediction.json` schema + `theory-data-validation-report.json` 联合验证 + T 维新增 0.2 权重 `theory_data_validation` 组件 (T 权重重分布 0.3/0.25/0.25/0.2) + FALSIFIED_SIGN 升级路径。
- **L3 — 竞品对标自动定期更新**: 新建 `competitive-drift-monitor.md` (252 行)，4 differentiator × 4 decay_state 转移 rubric + 季度自动触发 + structured PR contract + OVERTAKEN 战略升级路径。

### 修复 (v2.7 残留内部一致性 bug)
- E17: orchestrator "17-phase" 残留 → 20-phase (DAG 流图补 Phase 1b + Phase Mode Table 补 Phase 1b + 全仓统一)
- E18: domain-learner 输出文件名自相矛盾 (`domain-profile.json` vs `domain-signature.json`) → 统一到 `domain-signature.json`
- E19: result-to-claim 4 维置信度算术错误 (`combined: 0.61`、`D2=0.85` 漏 Theory-only flag、`Joint=0.43`) → 统一为 D2=0.725、combined=0.37、Joint=0.37
- E20: orchestrator See Also 漏 domain-learner/domain-signature 链接 → 补全 (本轮另补 8 条 v2.8 新文件链接)
- E21: result-to-claim "(新增)" v2.7 残留标注 → 替换为 "(TDAL — emitted per Phase 10 producer contract)"

### 修复 (OSS 历史债务清理 — v2.8 顺手闭合)
- E22: 全仓 173 处 Markdown 坏链 (`../shared-references/` 从 3 层深子目录出发少一层 `..`) → 批修加 `../`，补建 3 个被引用但缺失的契约文件 (`output-versioning.md` / `output-manifest.md` / `plugin-router.md`)，最终验证 373 链接 0 坏链
- E23: 2 处 JSON template 块非法语法 (dynamic-tooling 用 `"x" | "y"` 联合类型非 JSON；citation-audit 用裸 fragment 块缺外层 `{}`) → 改为 `"one of: x | y"` 合法字符串 + 补外层对象包裹，最终验证 46 JSON 块 0 invalid

### 文件清单 (v2.8 新增/重写)
- 新增 (11): `domain-adaptation-contract.md`、`ouroboros-integration.md` (重写)、`ouroboros-deep-integration.md`、`domain-adaptive-pipeline.md`、`confidence-uplift.md`、`pipeline-adaptive-degradation.md`、`domain-contribution-protocol.md`、`competitive-drift-monitor.md`、`output-versioning.md` (backfill)、`output-manifest.md` (backfill)、`plugin-router.md` (backfill)
- 修改 (5 + 2 历史债务): `orchestrator/125-problems-pipeline/SKILL.md`、`meta-skills/domain-learner/SKILL.md`、`meta-skills/domain-signature/SKILL.md`、`shared-references/domain-signature-consumer.md`、`support/result-to-claim/SKILL.md`；另批修 22 个 SKILL.md 的坏链路径 + 2 个文件的非法 JSON 块 (dynamic-tooling / citation-audit)

### 关键指标更新
| 指标 | v2.7 | v2.8 目标 |
|------|------|-----------|
| 领域覆盖 | 5 示例 | 6 evidence_types 覆盖全学科 (签名驱动 + 社区贡献通道) |
| 落地率 | 60-70% 估计 | TDAL 可量化 + 3 uplift 机制主动拉升 |
| Pipeline 弹性 | 手动降级 | 签名驱动自动降级 (M3) + 强度自适应 (M1) |
| 幻想检测 | 5 门 | 5 门 + TDAL missing_inputs floor + T维 external validation (L2) |
| 联合置信度 | 3 维 | 4 维 TDAL (T×D×A×L) + uplift 可提高 |
| 竞品对标 | 静态快照 | 季度自动 drift monitor (L3) |

## [2.0.0] - 2026-07-20

### 重大变更
- **全领域支持**: 框架不限定学科，物理学/数学/医学/经济学/教育学/材料/地球科学/天文等均可使用
- **结构化自评审**: 跨模型评审→单 agent 角色切换自评审 (auto-review-loop, logic-verification, kill-argument, quality-gate)
- **理论验证路径**: 新增理论-only / 计算 / 理论+实验 三路验证路径
- **DAG 可视化**: 新增 IDEA_DAG_VISUAL.md (Mermaid 格式)，全链路可追踪

### 新增
- LaTeX 模板文件: `main.tex` + `math_commands.tex`
- 工具模板库: symbolic-reasoner, statistical-modeler, knowledge-graph, formal-verifier, code-synthesizer, data-transformer, text-analyzer
- 理论论文写作模式: 新增 `theory_only` 结构分支
- 理论图表类型: commutative-diagram, derivation-tree, concept-map, dependency-graph, counterexample-plot
- 文档: CONTRIBUTING.md, CHANGELOG.md, CITATION.cff, .gitignore

### 修复
- F1: DAG 路径统一 (`dag/`→`refine-logs/`)
- F3: LaTeX 模板补充
- F4: cross-review Phase 编号修复 (Phase 9→14, Phase 8→12)
- P0-1: auto-review-loop 路径引用修复
- P0-3: kill-argument 读取源修复
- A3/A4: result-to-claim 路径修复

### 删除
- `cross-review/SKILL.md` (合并入 auto-review-loop)
- 跨模型评审相关引用 (reviewer-routing.md, reviewer-independence.md 简化)

## [1.0.0] - 2026-07-19

### 初始版本
- 单编排器架构 (125-problems-pipeline)
- 6 个元技能 + 13 个支持技能
- 16 个共享契约
- 17 阶段 DAG 循环（v2.8 升级为 20-phase：补 Phase 1a/1b domain signature + Phase 2.5 adversarial falsification）