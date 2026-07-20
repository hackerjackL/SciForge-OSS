# SciForge-open

> **纯 Skill 驱动的 AI Scientist** — 专为上海交通大学 125 个科学问题设计。
>
> 继承 SciForge 的纯 skill 驱动精神：**没有 `.py` 脚本，没有 bash 代码块，没有 IDE 专属语法**。
> 任何能读 Markdown 的 AI agent（Claude Code、Cursor、Trae 等）都能消费这些 skill。

---

## 这是什么

**SciForge-open** 是一个纯 Skill 驱动的通用 AI Scientist 框架，用于自动化解决**上海交通大学 125 个科学问题**（2023 版），涵盖物理学、计算机科学、生命科学、数学、地球科学、医学等领域。

**OSS = Open Single-question Stream** — 专为 125 问题挑战设计，与主仓库 SciForge 的关键差异：

| 维度 | 主仓库 SciForge | SciForge-OSS |
|------|----------------|--------------|
| **学科** | 4 并行 pipeline（econ/cs-ml/physics/general） + 16 overlay 文件 | **1 universal pipeline**（always `general`，无 overlay） |
| **执行** | 一次可多问题 | **单题执行**——每次 invocation 处理一个 Q-id，不自动迭代 125 题 |
| **框架** | AIM(econ) / SOTA(cs-ml) / PNV(physics) / none | None——agent 运行时推理处理领域方法 |
| **评审 persona** | 4 学科专属 persona | senior-reviewer-agnostic 唯一 |
| **模板** | 10+ venue families（NeurIPS/ICLR/PRL/AER...） | **单一 unified `elsarticle` 模板** |
| **实验** | 完整 empirical pipeline（GPU 训练 + benchmark binding + SOTA gate） | **无实验**——SymPy 符号推导 + 数值沙盒 sanity check |
| **图表** | Python 管线强制（matplotlib/seaborn） | 数据图 Python 管线；**简单架构图允 AI 直出 SVG**（莫兰迪色系仍强制） |
| **保真度** | 5-fidelity（text/symbolic/minimal/empirical/full） | **3-fidelity**（symbolic/numerical/qualitative）——无 empirical、无 full |
| **不变量** | INV-E*/INV-C*/INV-P* + INV-G1 | **INV-G1 唯一**（PROBLEM_ANCHOR_FREEZE 通用） |
| **泄漏审计** | Type I+II+III+IV + 14-class econ/cs-ml/physics pitfall lists | Type I（通用）+ Type IV（universalized）——Type II/III NOT_APPLICABLE |
| **125 题索引** | N/A | stub at `problems/125-SCIENCE-PROBLEMS.md`——**不自动搜索**，人类提示词给 Q-id |

与传统的"为每个学科写死工具"不同，SciForge-open 提炼出 **4 个通用元技能**（Meta-Skills），以不变应万变：

| 元技能 | 角色 | 说明 |
|--------|------|------|
| **Dynamic Sandbox** | 计算引擎 | 运行任意 Python/Julia 科学计算（NumPy/SciPy/SymPy）——无 GPU 训练，仅数值 sanity check |
| **Dynamic Tooling** | 工具工厂 | 运行时发现工具不足时，动态编写并注册临时工具 |
| **Universal Retrieval** | 文献检索 | 多源学术搜索（arXiv/S2/CrossRef/PubMed/Web/OpenAlex）+ 3 层防幻觉验证 |
| **Unified Plotting** | 图表渲染 | 结构化数据 → 出版级矢量图（SVG/PDF）；莫兰迪色系（Layer 1）+ viridis/magma 数据热图（Layer 2） |

## 架构：DAG 驱动的科研闭环

SciForge-open 采用 **DAG（有向无环图）** 架构，而非简单的线性管线：

```
                    ┌→ Idea 1 (theoretical)  ─→ novelty check ─→ eliminated ┐
Problem → Discover ─┼→ Idea 2 (computational) ─→ novelty check ─→ selected  ─┼→ Derive → Verify
                    └→ Idea 3 (empirical)     ─→ novelty check ─→ eliminated ┘
                                                                              └→ Write → Review → Output
```

1. **分支（Branch）**：从问题出发，并行生成 3 个不同方法论视角的 idea（理论/计算/实证）
2. **门控（Gate）**：每个 idea 经过新颖性 × 可行性 × 相关性 3 维评估，弱被淘汰
3. **收敛（Converge）**：只有最优 idea 存活，进入后续推导、验证、写作阶段

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
/cross-review "评审论文" — difficulty: hard
```

## 项目结构

```
SciForge-open/
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
│   │   ├── cross-review/SKILL.md           ← 跨模型评审
│   │   ├── method-registry/SKILL.md        ← 方法 registry + hash 锁 + 强制人类审批
│   │   ├── leakage-audit/SKILL.md          ← Type I 逻辑漏洞 + Type IV 逃逸审计（通用）
│   │   ├── invariant-check/SKILL.md        ← INV-G1 问题锚点冻结验证
│   │   ├── result-to-claim/SKILL.md        ← 3 保真度 claim 门控
│   │   ├── quality-gate/SKILL.md           ← 终极前置写作门（universal QF-G* + SD-G*）
│   │   ├── auto-review-loop/SKILL.md       ← 跨模型迭代评审 + kill-argument 反自欺
│   │   ├── citation-audit/SKILL.md         ← 最终 3 层引用防幻觉验证
│   │   └ kill-argument/SKILL.md           ← 反自欺练习（kill your own argument）
│   ├── orchestrator/                       ← 1 个编排器
│   │   └ 125-problems-pipeline/SKILL.md  ← 17 阶段 DAG 闭环（单题执行）
│   └ shared-references/                  ← 共享契约（学科无关）
│       ├── idea-dag-schema.md              ← DAG 节点 schema
│       ├── mcts-search-protocol.md         ← MCTS 迭代协议（UCB1 + 有界轮次）
│       ├── multi-fidelity-evaluation.md    ← 3 保真度筛选
│       ├── citation-discipline.md          ← 3 层防幻觉引用验证协议
│       ├── assurance-contract.md           ← 6 态判定 schema（PASS/WARN/FAIL/...）
│       ├── venue-profiles.md              ← 单一统一 elsarticle 模板 spec
│       ├── venue-checklists.md            ← 单一通用 pre-submission checklist
│       ├── discipline-context.md          ← OSS 单行（general）学科契约
│       ├── discipline-writing.md          ← 通用 section-by-section 写作指南
│       ├── color-themes.md                ← 莫兰迪（Layer 1）+ viridis/magma（Layer 2）
│       ├── writing-principles.md           ← 学术写作风格指南
│       ├── output-manifest.md + output-versioning.md ← 产物结构 + 版本化
│       ├── reviewer-independence.md + reviewer-routing.md + review-tracing.md ← 跨模型评审契约
│       ├── effort-contract.md              ← effort level 定义（lite/balanced/max/beast）
│       ├── skill-config.md                 ← skill 元信息 schema
│       └ ... (其他通用契约)
├── problems/
│   └ 125-SCIENCE-PROBLEMS.md             ← 125 科学问题索引 stub（不自动搜索；人类给 Q-id）
└── [删除: templates/ 占位目录、discipline-templates/、experiment-*、plugin-router、wiki-helper]

上海交通大学 2023 年发布的 125 个科学问题，涵盖：

| 领域 | 代码 | 示例问题 |
|------|------|---------|
| 物理学 | PHY | 宇宙的起源与演化、量子引力、高温超导、暗物质 |
| 计算机科学 | CS | 深度学习理论、图神经网络、强化学习、可解释 AI |
| 生命科学 | BIO | 意识神经基础、蛋白质折叠、细胞衰老、微生物组 |
| 数学 | MAT | 黎曼猜想、P vs NP |
| 地球科学 | EAR | 气候变化预测 |
| 医学 | MED | AI 药物发现 |
| 工程 | ENG | 机器人、能源 |
| 交叉/通用 | GEN | 复杂系统涌现现象 |

完整索引见 [problems/125-SCIENCE-PROBLEMS.md](problems/125-SCIENCE-PROBLEMS.md)。

## Skill 目录

### 元技能（Meta-Skills）

| Skill | 路径 | 说明 |
|-------|------|------|
| `/dynamic-sandbox` | [skills/meta-skills/dynamic-sandbox/SKILL.md](skills/meta-skills/dynamic-sandbox/SKILL.md) | 运行任意 Python/Julia 科学计算，预装 NumPy/SciPy/SymPy |
| `/dynamic-tooling` | [skills/meta-skills/dynamic-tooling/SKILL.md](skills/meta-skills/dynamic-tooling/SKILL.md) | 运行时发现工具不足时，动态编写并注册临时工具 |
| `/universal-retrieval` | [skills/meta-skills/universal-retrieval/SKILL.md](skills/meta-skills/universal-retrieval/SKILL.md) | 多源文献搜索 + 3 层防幻觉验证协议 |
| `/unified-plotting` | [skills/meta-skills/unified-plotting/SKILL.md](skills/meta-skills/unified-plotting/SKILL.md) | 结构化数据 → 出版级矢量图（SVG/PDF） |

### 支持技能（Support Skills）

| Skill | 路径 | 说明 |
|-------|------|------|
| `/theory-derivation` | [skills/support/theory-derivation/SKILL.md](skills/support/theory-derivation/SKILL.md) | SymPy 符号推导 + 逐步验证 |
| `/logic-verification` | [skills/support/logic-verification/SKILL.md](skills/support/logic-verification/SKILL.md) | 6 维度逻辑一致性审计 |
| `/paper-writing` | [skills/support/paper-writing/SKILL.md](skills/support/paper-writing/SKILL.md) | 从研究产物组装学术论文 |
| `/cross-review` | [skills/support/cross-review/SKILL.md](skills/support/cross-review/SKILL.md) | 5 维度对抗性同行评审 |

### DAG 技能

| Skill | 路径 | 说明 |
|-------|------|------|
| `/idea-discovery` | [skills/meta-skills/idea-discovery/SKILL.md](skills/meta-skills/idea-discovery/SKILL.md) | DAG 分支：多方法论视角并行生成 idea |
| `/novelty-check` | [skills/meta-skills/novelty-check/SKILL.md](skills/meta-skills/novelty-check/SKILL.md) | DAG 门控：3 维评估 + 淘汰弱 idea |

### 编排器

| Skill | 路径 | 说明 |
|-------|------|------|
| `/125-problems-pipeline` | [skills/orchestrator/125-problems-pipeline/SKILL.md](skills/orchestrator/125-problems-pipeline/SKILL.md) | 11 阶段 DAG 完整闭环 |

## 核心设计原则

1. **纯 Skill 驱动** — 每个 skill 是一份 `.md` 方法论文档。没有 `.py` 脚本、没有 bash 代码块、没有 IDE 专属语法。任何能读 Markdown 的 agent 都能消费这些 skill。

2. **DAG 优于线性** — 多条 idea 并行探索，弱 idea 在门控处被淘汰，只有最强的存活。

3. **元技能优于学科技能** — 4 个通用元技能替代 74 个学科特定技能。系统处理 125 个问题中的任何一个，无需硬编码学科知识。

4. **计算优于知识** — 当 AI 不知道答案时，它推导出来。动态沙盒执行 AI 写的代码，而不是程序员预写的代码。

5. **防幻觉优先** — 每篇引用通过 3 个独立学术 API（arXiv + CrossRef + Semantic Scholar）验证。没有论文凭记忆捏造。

6. **跨模型对抗评审** — 评审者与执行者是不同模型，防止自我强化错误。

7. **可复现** — 每次计算、推导和图表都保留为可执行代码 + 输入数据，而不仅仅是输出文本。

## 与 SciForge 的关系

SciForge-open 继承自 [SciForge](https://gitcode.com/GewisLab/SciForge.git) 的纯 skill 驱动和跨模型对抗精神，但做了以下关键转变：

| 维度 | SciForge | SciForge-open |
|------|----------|---------------|
| 学科覆盖 | 4 方向（经济学/CS/物理/通用） | 125 科学问题全领域 |
| 架构 | 4 条并行 pipeline | **DAG 分支 + 门控 + 收敛** |
| 实验 | experiment-bridge（GPU 训练） | **理论验证沙盒（SymPy 推导 + 逻辑审计）** |
| 核心 skill 数 | 74 个学科特定 skill | **4 个元技能 + 6 个通用 skill** |
| 写作 | venue 特定模板（NeurIPS/ICLR/PRL） | **简化版学术写作，学科无关** |
| 共享契约 | 21 个 | **36 个（复用 + 扩展）** |

## 许可证

本项目基于 SciForge 的原有许可证。详见 [LICENSE](LICENSE)。

---

**参与 125 科学问题挑战：** https://university.aliyun.com/action/tzbjbgs2026