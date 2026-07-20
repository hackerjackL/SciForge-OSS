# Self-Review Independence Protocol (SciForge-OSS)

> **OSS 使用结构化自评审，agent 通过角色切换实现对抗性评审。**
> 本文件定义自评审中的"独立性"原则——确保同一 agent 在切换角色后能有效质疑自身工作。

## 核心原则

1. **重新读取，而非回忆** — 每次角色切换后，agent 必须重新从文件读取产物，不能依赖内存中的记忆
2. **结构化检查清单** — 评审使用预定义的检查清单，而非自由格式的"评审一下"
3. **完整保留评审轨迹** — 评审输出完整保留在 `review-stage/`，不得删改
4. **角色隔离** — 评审者角色不能访问研究者角色的推理过程，只能看到最终产物文件

## 评审者可以访问的内容

- 产物文件路径（推导输出、claims 文件、验证报告、论文草稿）
- 评审目标（"评估可发表性"、"检查推导正确性"）
- 结构元数据（"论文有 8 个章节"、"推导在 derivations/ 目录"）
- 领域约束（"目标期刊级别"）

## 评审者不能访问的内容

- 研究者角色的推理过程或中间思考
- 先前的评审意见或修复记录（fresh 评审）
- 研究者对内容的摘要或解释（必须直接读取文件）

## 实现

- 角色切换由 `/auto-review-loop` 管理
- 检查清单由各 skill 定义（`/logic-verification` 的 20 分类问题体系）
- 评审轨迹保存在 `review-stage/` 目录

## 详见

- [`reviewer-routing.md`](reviewer-routing.md) — 角色切换契约
- [`../support/auto-review-loop/SKILL.md`](../support/auto-review-loop/SKILL.md) — 自评审循环
- [`review-tracing.md`](review-tracing.md) — 评审轨迹追踪