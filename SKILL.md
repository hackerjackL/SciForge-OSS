---
name: sciforge-oss
type: skill-package
role: ai-scientist-framework
version: 1.1.0
description: 纯 Skill 驱动的通用 AI Scientist 框架 — 全领域 (Domain-Agnostic) 科学推理引擎，v3.0 新增 AI 视角工程落地评判
entry: skills/orchestrator/auto-pipeline/SKILL.md
license: MIT
tags: [ai-scientist, research, latex, open-science, discipline-agnostic]
---

# SciForge-OSS — AI for Scientist Anything

> **纯 Skill 驱动的通用科学智能框架**。没有 `.py` 脚本，没有 bash 代码块，没有 IDE 专属语法。
> 任何能读 Markdown 的 AI agent（Claude Code、Cursor、Trae 等）都能消费这些 skill。

## 包结构

| 类型 | 数量 | 说明 |
|------|------|------|
| **Orchestrator** | 1 | `/auto-pipeline` — 单入口，21 阶段 DAG 科研循环（v3.0 Phase 5b 新增 AI 8 维 EG 评估） |
| **Meta-Skills** | 8 | 通用元技能：idea-discovery, universal-retrieval, unified-plotting, dynamic-sandbox, dynamic-tooling, domain-learner, domain-signature, novelty-check |
| **Support Skills** | 13 | 支撑技能：paper-writing, paper-compile, quality-gate, auto-review-loop, theory-derivation, logic-verification, result-to-claim, leakage-audit, citation-audit, invariant-check, kill-argument, method-registry, adversarial-falsification |
| **Shared References** | 31+ | 共享配置：skill-config, assurance-contract, effort-contract, color-themes, venue-profiles, **engineering-grounding-contract** 等 |

## 包含的子技能

### Orchestrator
- `/auto-pipeline` — 单题 21 阶段 DAG 科研循环（唯一入口，v3.0 Phase 5b AI 8 维 EG 评估 + Extreme Protocol）

### Meta-Skills
- `/idea-discovery` — MCTS 增强的研究想法生成
- `/universal-retrieval` — 文献检索 + 3 层反幻觉引用验证
- `/unified-plotting` — 出版级图表渲染（莫兰迪色板）
- `/dynamic-sandbox` — 轻量数值验证沙盒（Python/NumPy）
- `/dynamic-tooling` — 动态工具编写与注册
- `/domain-learner` — 从文献自动学习领域特性
- `/domain-signature` — 领域签名标记
- `/novelty-check` — 新颖性检测

### Support Skills
- `/paper-writing` — 统一 `elsarticle` 模板论文撰写
- `/paper-compile` — LaTeX 零警告零报错编译
- `/quality-gate` — 写作前硬门控
- `/auto-review-loop` — 跨模型对抗式评审迭代
- `/theory-derivation` — SymPy 符号推导与机器验证
- `/logic-verification` — 6 维逻辑一致性审计
- `/result-to-claim` — 3 保真度声明门控
- `/leakage-audit` — Type I/IV 漏洞审计
- `/citation-audit` — 最终 3 层引用验证
- `/invariant-check` — INV-G1 不变量验证
- `/kill-argument` — 反自我欺骗论证
- `/method-registry` — 方法论注册表（强制人类审批）
- `/adversarial-falsification` — 对抗性证伪

## 快速开始

```bash
# 在支持 SKILL.md 的 AI agent 中导入此包后：
"帮我完整研究 Q015：宇宙的起源与演化"
"Solve Q042: 高效能源存储"
"run the full pipeline on Q001"
```

## 设计原则

- **全领域通用**：不预设任何学科知识
- **单题执行**：每次 invocation 处理一个 Q-id
- **3 保真度**：symbolic / numerical / qualitative
- **无实验依赖**：无需 GPU，无需训练
- **统一模板**：单一 `elsarticle` LaTeX 模板