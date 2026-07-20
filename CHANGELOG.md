# Changelog

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