# Reviewer Routing — Review Backend Selection

> 本文件定义评审 backend 的选择契约。支持两种模式：**跨模型对抗评审**（推荐）和**自审查模式**（self-review）。
> 核心思想：跨模型评审可避免单模型盲区，但自审查在资源受限或快速迭代场景下也是合理选择。executor 不能挑选、过滤或转述 reviewer 看到的内容。

## 为什么需要跨模型评审

同一模型家族在生成和评审时共享相似的盲区：它倾向于认可自己会输出的论证结构、忽略同类的事实性错误、对自身风格的问题宽容。如果 executor 和 reviewer 来自同一模型家族，评审退化为自我背书。

因此 SciForge 的评审契约要求：

- **reviewer 与 executor 来自不同模型家族**（例如 executor 是 Claude 系列，reviewer 应来自 GPT / Gemini / Qwen / MiniMax 等其他家族）。
- 用户可显式指定 reviewer 模型；未指定时使用与 executor 不同家族的默认 reviewer。
- 任何 effort / difficulty 等级都不改变跨家族要求——它们控制评审深度，不改变模型家族选择。
- 高强度模式（beast）可推荐更强 reviewer，但永不强制；用户始终拥有最终选择权。

## Reviewer Independence Protocol（所有 reviewer 通用）

无论使用哪个模型作为 reviewer，以下不变量始终成立：

1. **reviewer 只看产物文件路径，不看 executor 的解释或摘要。** executor 向 reviewer 传递的是文件路径（论文段落、结果表、代码文件），不是 executor 自己对内容的总结。这防止 executor 通过转述隐藏问题。
2. **executor 不能过滤 reviewer 的输入或输出。** reviewer 收到的 prompt 和返回的 response 必须完整保留，executor 不得删改。
3. **effort 和 difficulty 与 reviewer 选择正交。** 它们控制评审深度，不改变模型家族选择。
4. **beast 模式可推荐更强 reviewer 但永不强制。** 用户始终拥有最终选择权。

## Fresh Context vs Carried Context

评审调用分两种上下文模式：

- **Fresh context（新会话）**：每次评审开新会话，reviewer 不带任何先前记忆。适用于独立轮次评审、首次审计、单次压力测试。默认模式。
- **Carried context（续评）**：保留先前评审会话的上下文，reviewer 可基于上一轮反馈继续深入。适用于多轮迭代评审、rebuttal 准备、连续追问。

切换到 carried context 时，必须保留先前会话的 thread identifier，并在新一轮调用中引用它。thread identifier 必须记录在 trace 中（见 `review-tracing.md`）以保证可复现。

### Reviewer Memory（within and across threads）

Reviewer memory is the protocol for what carries across review rounds:

- **Within the same thread** — the reviewer may reference its own previous feedback to check whether an issue was resolved.
- **Across threads / new review sessions** — memory resets. Each new review session starts with a fresh context so the reviewer forms an independent assessment. This is what makes cross-model adversarial review work; see [`reviewer-independence.md`](reviewer-independence.md).
- **Executor interpretations are never carried into reviewer memory.** Even within the same thread, the reviewer must not receive the executor's summary, paraphrase, or recommendations. Memory is for the reviewer's own prior observations only.

## Difficulty Levels

评审难度等级控制 reviewer 的推理深度与压力：

- **standard**：常规评审，覆盖明显问题。
- **beast**：深度评审，推荐使用更强 reviewer 模型，但不强制。
- **nightmare**：极限压力测试，要求 reviewer 直接读取 repo（而非依赖 executor 传递的片段），确保 executor 无法过滤信息。

nightmare 模式与人工评审（manual reviewer）不兼容——人工评审无法实现"直接读 repo"的语义，必须显式报错而非静默降级。

## Manual Reviewer（零 API 成本回退）

当没有任何付费 API 可用时，可使用人工评审模式：executor 将评审材料整理好，由人工粘贴到任意 LLM 前端完成评审，再将结果回填。此模式：

- 仍必须遵守 Reviewer Independence Protocol（人工只看文件路径，不看 executor 摘要）。
- 仍必须保存完整 trace（prompt/response 对，见 `review-tracing.md`）。
- 不与 nightmare 模式兼容。

## Self-Review Mode（自审查模式）

当用户将 reviewer backend 设置为 `self-review` 时，executor 和 reviewer 可以是同一模型家族。此模式适用于：

- 资源受限场景（只有一个模型 API 可用）
- 快速迭代场景（不需要外部视角，只需要结构化自审）
- 调试和开发阶段（不需要严格的对抗评审）

**自审查模式的约束**：

- 仍然遵守 Reviewer Independence Protocol 中的文件路径传递规则（不传递 executor 摘要）。
- 仍然保存完整 trace（prompt/response 对）。
- 评审结果中必须标注 `[SELF-REVIEW]`，以区别于跨模型评审结果。
- 不适用于 `nightmare` 难度（自审查 + 极限压力测试无意义）。

**如何启用**：在 `AGENT_DOC.md` 中设置 `REVIEWER_BACKEND: self-review`，或在调用时传参 `— reviewer: self-review`。

## 不可用时的策略

- 付费 reviewer 不可用时，可回退到默认 reviewer（若默认也不可用则停止，不静默降级到 executor 同家族）。
- 用户显式指定 manual reviewer 但 manual 不可用时必须停止——目标用户可能没有任何付费 API，静默 fallback 会误导。
- 任何回退都必须显式告知用户，不静默切换。

## 使用跨模型评审的 skill

| skill | 用途 |
|---|---|
| research-review | 论文草稿深度评审 |
| auto-review-loop | 末轮压力测试 |
| experiment-audit | 逐行 eval 代码审计 |
| proof-checker | 深度数学推理 |
| rebuttal | 投稿前压力测试 |
| idea-creator | idea 评估深度 |
| auto-paper-improvement-loop | 论文润色循环 |
| citation-audit | 引用诚实度审计 |
| paper-claim-audit | 数值声明审计 |
| training-check | 训练健康检查 |
| meta-optimize | 框架自进化评审 |

## 未来工作

- 评审循环与 image review 的集成。
- 更多模型家族按相同协议接入即可。
