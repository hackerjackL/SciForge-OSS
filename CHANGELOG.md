# Changelog

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
- 17 阶段 DAG 循环