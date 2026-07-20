# Contributing to SciForge-OSS

感谢您对 SciForge-OSS 的关注！SciForge-OSS 是一个**纯 Skill 驱动的通用 AI Scientist 框架**，致力于实现"AI for Scientist Anything"的愿景。

## 如何贡献

### 1. 提交 Issue

- **Bug 报告**: 描述问题、复现步骤、期望行为
- **功能请求**: 描述新功能、使用场景、预期效果
- **Skill 改进**: 对某个 SKILL.md 的改进建议

### 2. 提交 Pull Request

1. Fork 本仓库
2. 创建新分支 `feat/your-feature-name` 或 `fix/your-fix-name`
3. 修改仅限于 `Skills/` 目录下的 `.md` 文件
4. 确保不破坏主仓库的现有文件
5. 提交 PR 时附上清晰的描述

### 3. 修改规范

- **只修改 OSS 目录**: 所有修改仅限于 `SciForge-OSS/` 目录
- **纯 Markdown**: 所有 skill 是 `.md` 文件，无 `.py` 脚本、无 bash 代码块
- **学科无关**: 不引入特定学科的硬编码
- **DAG 架构**: 保持有向无环图的架构设计
- **跨模型→自评审**: 评审使用结构化自评审模式

### 4. Skill 编写规范

每个 SKILL.md 应包含：
- `---` frontmatter (name, type, role)
- `# Title` 标题
- `> **Status**` 状态说明
- `## Use When` 使用场景
- `## Job` 职责描述
- `## Workflow` 工作流程
- `## Boundaries` 边界约束
- `## See Also` 相关引用

## 行为准则

- 尊重所有贡献者
- 保持建设性的讨论
- 关注技术问题本身