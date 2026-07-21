# SciForge-OSS

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.9.0-green.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub](https://img.shields.io/badge/repo-gitcode-blue)](https://gitcode.com/GewisLab/SciForge-OSS)
[![AI for Science](https://img.shields.io/badge/AI%20for-Science-ff69b4)](https://gitcode.com/GewisLab/SciForge-OSS)

> **AI for Scientist Anything** — 纯 Skill 驱动的通用科学智能框架。
>
> 继承 SciForge 的纯 skill 驱动精神：**没有 `.py` 脚本，没有 bash 代码块，没有 IDE 专属语法**。
> 任何能读 Markdown 的 AI agent（Claude Code、Cursor、Trae 等）都能消费这些 skill。
>
> 125 个科学问题是「AI for Scientist Anything」的 Demo 展示，全世界的问题远不止 125 个。

---

## 目录

- [这是什么](#这是什么)
- [架构：DAG 驱动的科研闭环](#架构dag-驱动的科研闭环)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [全领域支持](#全领域支持)
- [验证路径：三路可选](#验证路径三路可选)
- [多领域示例](#多领域示例)
- [核心设计原则](#核心设计原则)
- [125 科学问题 Demo](#125-科学问题-demo)
- [与 SciForge 的关系](#与-sciforge-的关系)
- [常见问题 (FAQ)](#常见问题-faq)
- [许可证](#许可证)

## 这是什么

**SciForge-OSS** 是一个纯 Skill 驱动的 **通用 AI Scientist 框架**，不限定任何学科领域。无论你是物理学、数学、计算机科学、生命科学、医学、经济学、教育学、材料科学、地球科学、大气科学、天文学、化学、工程、传感器、光电——任何科学领域，都能使用本框架。

**核心哲学**：全领域（Domain-Agnostic）。框架本身不预设任何学科知识，所有学科特定的方法论由 agent 运行时推理处理。

**OSS = Open Single-question Stream** — 与主仓库 SciForge 的关键差异：

| 维度 | 主仓库 SciForge | SciForge-OSS |
|------|----------------|--------------|
| **学科** | 4 并行 pipeline（econ/cs-ml/physics/general） + 16 overlay 文件 | **全领域 1 universal pipeline**（无 overlay，无学科分支） |
| **执行** | 一次可多问题 | **单题执行**——每次 invocation 处理一个 Q-id，不自动迭代全部问题 |
| **框架** | AIM(econ) / SOTA(cs-ml) / PNV(physics) / none | None——agent 运行时推理处理领域方法 |
| **评审 persona** | 4 学科专属 persona | senior-reviewer-agnostic 唯一 |
| **模板** | 10+ venue families（NeurIPS/ICLR/PRL/AER...） | **单一 unified `elsarticle` 模板** |
| **实验** | 完整 empirical pipeline（GPU 训练 + benchmark binding + SOTA gate） | **无实验**——SymPy 符号推导 + 数值沙盒 sanity check |
| **验证路径** | 假设有代码/实验条件 | **理论-only + 计算 + 理论+实验 三路可选**——纯理论领域无需写代码 |
| **保真度** | 5-fidelity（text/symbolic/minimal/empirical/full） | **3-fidelity**（symbolic/numerical/qualitative）——无 empirical、无 full |
| **不变量** | INV-E*/INV-C*/INV-P* + INV-G1 | **INV-G1 唯一**（PROBLEM_ANCHOR_FREEZE 通用） |
| **问题** | N/A | 任意数量，125 题为 Demo 展示 |

与传统的"为每个学科写死工具"不同，SciForge-OSS 提炼出 **4 个通用元技能**（Meta-Skills），以不变应万变：

| 元技能 | 角色 | 说明 |
|--------|------|------|
| **Dynamic Sandbox** | 计算引擎 | 运行任意 Python/Julia 科学计算（NumPy/SciPy/SymPy）——无 GPU 训练，仅数值 sanity check |
| **Dynamic Tooling** | 工具工厂 | 运行时发现工具不足时，动态编写并注册临时工具 |
| **Universal Retrieval** | 文献检索 | 多源学术搜索（arXiv/S2/CrossRef/PubMed/Web/OpenAlex）+ 3 层防幻觉验证 |
| **Unified Plotting** | 图表渲染 | 结构化数据 → 出版级矢量图（SVG/PDF）；莫兰迪色系（Layer 1）+ viridis/magma 数据热图（Layer 2） |

## 架构：DAG 驱动的科研闭环

SciForge-OSS 采用 **DAG（有向无环图）** 架构，而非简单的线性管线。这是整个框架最核心的"show"：

```
                    ┌→ Idea 1 (theoretical)   ─┐
                    │                           │
Problem → Discover ─┼→ Idea 2 (computational) ─┼→ MCTS 4 轮迭代 (UCB1 选择 × expand × rollout × backprop)
                    │                           │   ↓ 每轮淘汰弱 idea
                    └→ Idea 3 (qualitative)   ─┘   ↓
                                                  survivors
                                                     │
                                                     ▼
                                              Phase 2.5: adversarial-falsification (证伪门控)
                                                  ↓ 假设评分 + 反例构造 + 文献对抗
                                                  ↓ falsified ideas eliminated
                                                     │
                                                     ▼
                                              Phase 3: novelty-check (3 维门控)
                                                  ↓ 新颖性 × 可行性 × 相关性
                                                  ↓ only strongest idea survives
                                                     │
                                                     ▼
                                          Derive (Phase 6) → Verify (Phase 7-10)
                                                     │
                                                     ▼
                                          Write (Phase 12) → Review (Phase 14) → Output (Phase 16)
                                                     │
                                                     └→ DAG 可视化追踪 (refine-logs/IDEA_DAG.json)
```

### DAG 原理

1. **分支（Branch）**：从问题出发，并行生成 3 个不同方法论视角的 idea（理论/计算/定性）
2. **MCTS 迭代**：每个 idea 经 4 轮 MCTS 迭代（UCB1 选择 → expand → rollout → backprop），弱 idea 在迭代中被淘汰
3. **证伪门控（Falsification Gate, Phase 2.5）**：存活的 idea 接受 adversarial-falsification 攻击（假设评分 + 反例构造 + 文献对抗），被证伪的 idea 淘汰
4. **新颖性门控（Novelty Gate, Phase 3）**：通过证伪的 idea 经新颖性 × 可行性 × 相关性 3 维评估，只有最优 idea 存活进入后续推导、验证、写作阶段
5. **追踪（Trace）**：整条链路的 DAG 结构保存在 `refine-logs/IDEA_DAG.json`，可生成 Mermaid 可视化

### 20 阶段 DAG 循环

```
Phase  0: 加载问题（冻结 Q-id — INV-G1 锚点）
Phase  1: 问题理解与分解（内置推理）
Phase  2: /idea-discovery [DAG 分支] — 3 视角 idea + MCTS 迭代
Phase  3: /novelty-check [DAG 门控] — 3 维评估 + 淘汰
    ─── Forced human checkpoint: pick the final idea ───
Phase  4: /universal-retrieval — 文献调研 + 3 层防幻觉
Phase  5: /method-registry — 方法绑定 + hash 锁 + 强制人类审批
    ─── Forced human checkpoint: approve the method registry ───
Phase  6: /theory-derivation — SymPy 符号推导 + 逐步机器验证
Phase  7: /leakage-audit — Type I 逻辑漏洞 + Type IV 逃逸审计
Phase  8: /logic-verification — 6 维度逻辑一致性审计
Phase  9: /invariant-check — INV-G1 问题锚点冻结验证
Phase 10: /result-to-claim — 3 保真度 claim 门控
Phase 11: /unified-plotting — 学术图表（可选，莫兰迪色系 + Layer 2）
Phase 12: /paper-writing — elsarticle 单模板写作
Phase 13: /paper-compile — LaTeX 零警告零报错编译
Phase 14: /auto-review-loop — 跨模型评审 + kill-argument 反自欺
Phase 15: /citation-audit — 最终引用 3 层验证
Phase 16: 最终组装 + 产物归档
```

## 快速开始

AI agent 读取 `AGENT_GUIDE.md` 后，直接调用：

```
/125-problems-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
```

或手动逐步执行：

```
# 1. 创意生成（DAG 分支）
/idea-discovery "Q001: 宇宙的起源与演化" — num_ideas: 3

# 2. 新颖性验证（DAG 门控）
/novelty-check "Q001" — strictness: normal

# 3. 文献调研
/universal-retrieval "宇宙起源 暗物质" — max_papers: 20

# 4. 理论推导
/theory-derivation "从 Friedmann 方程推导宇宙演化" — mode: derive

# 5. 逻辑验证
/logic-verification "验证推导的逻辑一致性" — mode: full

# 6. 图表生成（可选）
/unified-plotting "绘制宇宙膨胀曲线" — format: svg

# 7. 论文写作
/paper-writing "基于研究成果撰写论文" — format: markdown

# 8. 跨模型评审
/auto-review-loop "评审论文" — difficulty: hard
```

## 项目结构

```
SciForge-OSS/
├── AGENT_GUIDE.md                          ← AI agent 入口（从这里开始读）
├── README.md                               ← 人类阅读
├── skills/
│   ├── meta-skills/                        ← 6 个元技能
│   │   ├── dynamic-sandbox/SKILL.md        ← 计算沙盒（数值 sanity check，无 GPU）
│   │   ├── dynamic-tooling/SKILL.md        ← 工具制造
│   │   ├── universal-retrieval/SKILL.md    ← 学术检索 + 3 层防幻觉（6 源）
│   │   ├── unified-plotting/SKILL.md       ← 矢量图表渲染（莫兰迪 + Layer 2 数据热图）
│   │   ├── idea-discovery/SKILL.md         ← [DAG] 多视角创意 + MCTS 迭代
│   │   └ novelty-check/SKILL.md           ← [DAG] 新颖性验证+淘汰
│   ├── support/                            ← 13 个支持技能
│   │   ├── theory-derivation/SKILL.md      ← SymPy 推导 + 逐步机器验证
│   │   ├── logic-verification/SKILL.md     ← 6 维度逻辑审计（跨模型对抗）
│   │   ├── paper-writing/SKILL.md          ← 统一 elsarticle 模板写作
│   │   ├── paper-compile/SKILL.md          ← LaTeX 零警告零报错编译 + 反死循环阶梯
│   │   ├── method-registry/SKILL.md        ← 方法 registry + hash 锁 + 强制人类审批
│   │   ├── leakage-audit/SKILL.md          ← Type I 逻辑漏洞 + Type IV 逃逸审计（通用）
│   │   ├── invariant-check/SKILL.md        ← INV-G1 问题锚点冻结验证
│   │   ├── result-to-claim/SKILL.md        ← 3 保真度 claim 门控
│   │   ├── quality-gate/SKILL.md           ← 终极前置写作门（universal QF-G* + SD-G*）
│   │   ├── auto-review-loop/SKILL.md       ← 跨模型迭代评审 + kill-argument 反自欺
│   │   ├── citation-audit/SKILL.md         ← 最终 3 层引用防幻觉验证
│   │   └ kill-argument/SKILL.md           ← 反自欺练习（kill your own argument）
│   ├── orchestrator/                       ← 1 个编排器
│   │   └ 125-problems-pipeline/SKILL.md  ← 20 阶段 DAG 闭环（单题执行）
│   └ shared-references/                  ← 共享契约（学科无关）
│       ├── idea-dag-schema.md              ← DAG 节点 schema
│       ├── mcts-search-protocol.md         ← MCTS 迭代协议（UCB1 + 有界轮次）
│       ├── multi-fidelity-evaluation.md    ← 3 保真度筛选
│       ├── citation-discipline.md          ← 3 层防幻觉引用验证协议
│       ├── assurance-contract.md           ← 6 态判定 schema（PASS/WARN/FAIL/...）
│       ├── venue-profiles.md              ← 单一统一 elsarticle 模板 spec
│       ├── venue-checklists.md            ← 单一通用 pre-submission checklist
│       ├── discipline-context.md          ← OSS 全领域契约（无学科分支）
│       ├── discipline-writing.md          ← 通用 section-by-section 写作指南
│       ├── color-themes.md                ← 莫兰迪（Layer 1）+ viridis/magma（Layer 2）
│       ├── writing-principles.md           ← 学术写作风格指南
│       ├── output-manifest.md + output-versioning.md ← 产物结构 + 版本化
│       ├── reviewer-independence.md + reviewer-routing.md + review-tracing.md ← 跨模型评审契约
│       ├── effort-contract.md              ← effort level 定义（lite/balanced/max/beast）
│       ├── skill-config.md                 ← skill 元信息 schema
│       └ ... (其他通用契约)
├── problems/
│   └ 125-SCIENCE-PROBLEMS.md             ← 125 科学问题 Demo 索引（不自动搜索；人类给 Q-id）
└── [删除: templates/ 占位目录、discipline-templates/、experiment-*、plugin-router、wiki-helper]
```

## 全领域支持

SciForge-OSS 不限定任何学科领域。以下仅为示例，而非限制：

| 领域大类 | 子领域示例 |
|---------|-----------|
| 理科 | 数学、物理、化学、生物、天文 |
| 工科 | 计算机、电子、机械、材料、光电、传感器 |
| 医学 | 基础医学、临床医学、药物发现、流行病学 |
| 地球科学 | 地质、海洋、大气、气候、环境 |
| 社会科学 | 经济学、教育学、心理学、社会学 |
| 交叉学科 | 复杂系统、网络科学、数据科学、AI for Science |

**核心机制**：框架不预设学科知识，所有领域特定的方法论、符号体系、验证标准均由 agent 运行时推理处理。详见 [`discipline-context.md`](skills/shared-references/discipline-context.md)。

## 验证路径：三路可选

不是所有科学领域都能写代码做实验。SciForge-OSS 支持三种验证路径：

| 路径 | 适用场景 | 验证手段 | 输出 |
|------|---------|---------|------|
| **理论-only** | 数学猜想、经济学模型、教育学理论 | 概念推演 + 逻辑一致性 + 文献支撑 | 严格证明或理论论证 |
| **计算** | 物理模拟、数值分析、CS 算法 | SymPy 符号推导 + Python 数值 sanity check | 符号推导 + 数值验证 |
| **理论+实验** | 有实验条件（但 OSS 无实验环境） | 理论推导 + 实验设计建议 | 理论框架 + 可验证预测 |

判断依据：Phase 2（idea-discovery）自动识别问题性质，选择验证路径。

## 核心设计原则

1. **纯 Skill 驱动** — 每个 skill 是一份 `.md` 方法论文档。没有 `.py` 脚本、没有 bash 代码块、没有 IDE 专属语法。任何能读 Markdown 的 agent 都能消费这些 skill。

2. **DAG 优于线性** — 多条 idea 并行探索，弱 idea 在门控处被淘汰，只有最强的存活。DAG 结构可追踪、可可视化。

3. **元技能优于学科技能** — 4 个通用元技能替代 74 个学科特定技能。系统处理任意科学问题，无需硬编码学科知识。

4. **计算优于知识** — 当 AI 不知道答案时，它推导出来。动态沙盒执行 AI 写的代码，而不是程序员预写的代码。

5. **防幻觉优先** — 每篇引用通过 3 个独立学术 API（arXiv + CrossRef + Semantic Scholar）验证。没有论文凭记忆捏造。

6. **结构化自评审** — 评审使用角色切换模式（研究者→评审者→裁决者），无需跨模型协作。

7. **可复现** — 每次计算、推导和图表都保留为可执行代码 + 输入数据，而不仅仅是输出文本。

## 多领域示例

以下是 SciForge-OSS 在不同领域的应用示例：

### 物理学
```
/125-problems-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
```
→ 输出：宇宙学理论推导 + ΛCDM 模型验证

### 数学
```
/125-problems-pipeline "证明：对于任意 n≥3，不存在正整数解满足 x^n + y^n = z^n"
```
→ 输出：Fermat 大定理的初等证明思路 + 文献综述

### 经济学
```
/125-problems-pipeline "Analyze: general equilibrium under incomplete markets"
```
→ 输出：一般均衡存在性证明 + 数值验证

### 教育学
```
/125-problems-pipeline "研究：基于认知负荷理论的教学设计优化"
```
→ 输出：理论模型 + 逻辑验证 + 实验设计建议

### 材料科学
```
/125-problems-pipeline "Predict: band structure of MoS2 under strain"
```
→ 输出：能带结构推导 + 数值验证

### 医学
```
/125-problems-pipeline "Study: AI-driven drug discovery for Alzheimer's disease"
```
→ 输出：药物靶点识别 + 分子动力学模拟验证

## 125 科学问题 Demo

`problems/125-SCIENCE-PROBLEMS.md` 包含 125 个科学问题，作为 **"AI for Scientist Anything" 的 Demo 展示**。全世界的问题远不止 125 个——框架设计为通用方案，可处理任意数量、任意领域的问题。

- 125 题是**演示题库**，不是完整题库
- 框架支持任意数量的问题（通过 `problems/` 目录自动发现）
- Q ID 格式灵活，无需死板命名

## 与 SciForge 的关系

SciForge-OSS 继承自 [SciForge](https://gitcode.com/GewisLab/SciForge.git) 的纯 skill 驱动和跨模型对抗精神，但做了以下关键转变：

| 维度 | SciForge | SciForge-OSS |
|------|----------|--------------|
| 学科覆盖 | 4 方向（经济学/CS/物理/通用） | **全领域（AI for Scientist Anything）** |
| 架构 | 4 条并行 pipeline | **DAG 分支 + 门控 + 收敛 + 可视化追踪** |
| 实验 | experiment-bridge（GPU 训练） | **理论验证沙盒（SymPy 推导 + 逻辑审计 + 理论-only 路径）** |
| 核心 skill 数 | 74 个学科特定 skill | **4 个元技能 + 6 个通用 skill** |
| 问题 | N/A | **任意数量，125 题为 Demo** |
| 验证 | 假设有代码/实验 | **理论-only / 计算 / 理论+实验 三路可选** |
| 评审 | 跨模型评审 | **结构化自评审（角色切换）** |

## 常见问题 (FAQ)

### Q: SciForge-OSS 支持哪些学科？
A: 所有学科。物理学、数学、计算机科学、医学、经济学、教育学、材料科学、地球科学、大气科学、天文学、化学、工程、传感器、光电——任何科学领域都可以使用。

### Q: 125 个问题是必须的吗？
A: 不是。125 个科学问题是「AI for Scientist Anything」的 Demo 展示。框架支持任意数量、任意领域的问题。

### Q: 需要多个 AI 模型才能运行吗？
A: 不需要。SciForge-OSS 使用**结构化自评审**模式——同一 agent 通过角色切换（研究者→评审者→裁决者）实现对抗性评审，无需跨模型协作。

### Q: 如何运行一个完整的科学问题研究？
A: 执行 `/125-problems-pipeline "Q001: 问题描述" — effort: max`，自动化完成 20 阶段 DAG 循环。

### Q: 输出什么格式的论文？
A: 统一 `elsarticle` LaTeX 格式，可编译为 PDF。理论论文使用"理论论文结构"（Main Results + Proofs），实验论文使用标准结构。

### Q: 如何贡献新的 skill？
A: 参考 [CONTRIBUTING.md](CONTRIBUTING.md)。所有 skill 是纯 Markdown 文件，遵循统一的 frontmatter 格式。

### Q: 与主仓库 SciForge 的区别是什么？
A: 见上方表格。核心区别：全领域、单 pipeline、DAG 架构、结构化自评审、125 题为 Demo。

## 许可证

本项目基于 SciForge 的原有许可证。详见 [LICENSE](LICENSE)。

---

**SciForge-OSS — AI for Scientist Anything**