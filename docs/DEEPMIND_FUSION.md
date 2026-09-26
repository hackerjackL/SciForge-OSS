# DeepMind 顶级项目融合调研（v1.5.0-w2）

> 调研方式：子代理 WebFetch DeepMind 官方博客/论文/GitHub（AlphaEvolve / AlphaProof /
> AlphaGeometry / AlphaTensor / GNoME / GraphCast）。下方为原文事实摘录 + 本项目已落地的融合映射。
> FunSearch / AI Co-Scientist 本次未抓全（已标注跳过），其核心机制（程序进化 / tournament 评审）
> 我们已有等价实现（evolve.py PUCT+MAP-Elites / review.py 盲审团+仲裁）。

## 已落地的融合映射（kernel 级）

| DeepMind 模式 | 项目来源 | 我们的实现 | 位置 |
|---|---|---|---|
| 多评估器持续反馈 + 级联评估（便宜的先跑，贵的 LLM 最后） | AlphaEvolve | HybridDomain cascade: CI/golden 门 → research_validity 科学诚信正则 → LLM judge | `kernel/sciforge/evolve.py` |
| 反 reward-hacking（评估器冻结 + 候选不得改测量仪） | AlphaEvolve | FROZEN_PREFIXES + 三分片 held-out + probe 预检 | `evolve.py` S12/S13/S16 |
| 生成→形式验证→强化闭环（已验证证明回流训练） | AlphaProof | LESSONS.json `verified_proofs`（仅 status=PASS 进入）+ memory 检索索引 | `pipeline.py` / `memory.py` |
| 主动学习回流（预测→验证→回流训练数据） | GNoME | `retrain_from_results`：验证过的 regime/metric 回流 domain-signature | `domain-adaptation-contract.md` |
| 神经-符号分工（LLM 出直觉构造，符号引擎严格证明） | AlphaGeometry | LLM 出想法/推导步骤，SymPy 机器验证 + kernel 机械门 | theory-derivation + gates |
| 形式可验证性作为质量锚 | AlphaProof/AlphaGeometry | verdict schema + validate_verdicts 硬门（22 注册 artifact） | `scripts/validate_verdicts.py` |
| 稳定性判据 + 与实验的关系（预测必须落 DFT/实测） | GNoME | toy gate + full 实验 + FAIRNESS 公平性门 | `fairness_gate.py` |
| 科学基础模型的管线启示（确定性基线 + 概率模型对照） | GraphCast | experiment matrix 强制 baseline 对照 + 效应量/CI | method-registry §3 |

## 原文事实摘录（未加工）

# AlphaGeometry 设计要点（基于原文事实）

## 符号引擎与语言模型的结合
- 采用神经-符号（neuro-symbolic）架构，由一个神经语言模型与一个符号演绎引擎协作，比喻为"thinking, fast and slow"：语言模型提供快速、直觉式的线索，符号引擎做严谨推理。
- 语言模型擅长识别数据中的模式与关系，能快速预测有用构造，但不擅长严格推理或解释决策；符号引擎基于形式逻辑、规则明确、可解释，但独立处理复杂问题时"slow and inflexible"。
- 语言模型引导符号引擎走向可能的解。

## 辅助点/几何构造搜索
- IMO 几何题的图需先加入新的几何构造（点、线、圆）才能求解。语言模型从无限多种可能中预测最有用的构造。
- 流程：符号引擎先穷尽推导图中可得的新陈述；若无解，语言模型加入一个潜在有用的构造（蓝色元素），打开新的演绎路径，循环直到求解。文中简单示例只需一个构造。

## 训练数据（合成数据）
- 生成了约十亿个随机几何图，对每个图中点线关系做穷尽推导，找出所有证明，再反向追溯所需构造，称为"symbolic deduction and traceback"。
- 过滤去重后得到 1 亿个独特训练样本（其中九百万含加入的构造），完全无需人类演示，绕过数据瓶颈。

## 形式验证
- 每个问题的解答均由计算机检查和验证；并与既有 AI 方法、人类成绩对比。
- 数学教练/前 IMO 金牌得主 Evan Chen 评价：输出"verifiable and clean"，具"machine-verifiable structure"且仍可被人阅读；用的是角度、相似三角形等经典几何规则，而非暴力坐标代数计算。

## 与纯 LLM 证明的差异
- 原文未直接对比纯 LLM，但指出语言模型不擅长严谨推理/解释，需符号引擎补足；Chen 也批评过往 AI 对证明类竞赛题的输出"hit-or-miss"、需人工检查，而 AlphaGeometry 输出可机器验证。
- 开源代码与模型：github.com/google-deepmind/alphageometry，Nature 论文 2024-01-17。

## IMO 成绩
- 在 IMO-AG-30 基准（2000–2022 年 30 道 IMO 几何题）上，AlphaGeometry 在标准时限内解出 25 题；此前 SOTA（Wu's method）解出 10 题；人类金牌得主平均 25.9 题（铜牌 19.3、银牌 22.9）。
- 示例：2015 年 IMO 第 3 题的解答有 109 个逻辑步骤，加入了三个构造点。
- 局限：IMO 每场六题、通常仅两题为几何，故只能覆盖约三分之一题目；但其几何能力使其成为首个达到 2000 与 2015 年 IMO 铜牌线的 AI 模型。

---

# AlphaProof 设计要点（基于原文事实）

## 1. 符号形式化验证与 LLM/RL 的结合

- **形式语言的选择**：AlphaProof 在形式语言 **Lean** 中训练自己证明数学陈述。原文指出形式语言的核心优势是数学推理证明可被形式化验证正确性（"proofs involving mathematical reasoning can be formally verified for correctness"）。
- **LLM 的角色**：用 **Gemini** 微调，将自然语言题目自动翻译为形式语句，从而建立一个覆盖不同难度的大型形式化题库，桥接自然语言与形式语言两个领域（原文称此前形式化 ML 受限于人工形式化数据极少）。
- **强化学习**：基于 AlphaZero 算法——该算法此前用于自学到国际象棋、将棋和围棋。找到并验证的每个证明都用于强化其语言模型，使其能解决后续更难的问题。

## 2. 证明搜索机制

- 生成解题候选，然后在 Lean 中**搜索可能的证明步骤**以证明或反驳候选解。
- **训练循环**：约一百万个非形式化数学题 → 形式化网络翻译 → 求解网络搜索证明/反驳 → 通过 AlphaZero 算法逐步训练以应对更难题目。
- **竞赛期间的持续训练**：对竞赛题的自生成变体持续强化证明，直到找到完整解。

## 3. 与 Lean 的集成

- 全部证明在 Lean 中进行并可验证。
- 致谢中提及多位 Lean 专家参与，以及 Lean 与 **Mathlib** 社区的贡献者。

## 4. IMO 2024 成绩

- 与 AlphaGeometry 2 组合系统解决了 **6 题中的 4 题**，总分 **28/42**，与银牌水平持平；金牌门槛为 29 分。
- **AlphaProof** 解出 2 道代数题 + 1 道数论题，含本届最难的题（仅 5 名参赛者解出）；**AlphaGeometry 2** 证明了几何题（收到形式化后 19 秒内解出 Problem 4）；2 道组合题未解出。
- 解题时间：一题几分钟内解决，其他题最长耗时约三天（正式比赛为每场 4.5 小时的两场）。
- 评分由 Timothy Gowers 爵士与 Joseph Myers 博士按 IMO 规则完成。Gowers 评价：系统能给出这样的非显然构造非常出色，"well beyond what I thought was state of the art"。

## 5. 可迁移至自动科研管线的验证化设计

- **核心可迁移机制**：LLM 生成 + 形式化验证（Lean）+ RL 强化已验证证明 → 构成"生成—验证—强化"闭环，可抑制 LLM 幻觉出错误推理步骤的问题。
- **RL 自迭代**：训练期间证明或反驳数百万个题目、覆盖多领域难度；竞赛中还可对题目变体持续搜索。
- **AlphaGeometry 2 的改进**（展示工程化升级路径）：基于 Gemini 的神经符号混合系统、比前身多一个数量级的合成数据、快两个数量级的符号引擎、知识共享机制组合搜索树。历史 IMO 几何题解出率从 53% 提升至 83%。
- **自然语言路线**：还实验了基于 Gemini 的自然语言推理系统，无需形式化翻译、可与其他 AI 系统组合，结果"showed great promise"。
- 原文愿景：AI 帮助数学家探索假设、尝试大胆方法、快速完成证明中耗时环节。后续技术细节已发表于 Nature（2025 年 11 月 12 日）。

---

# GNoME 关键设计事实要点

## 1. 图神经网络如何表示材料
- GNoME 是"Graph Networks for Materials Exploration"，一种图神经网络（GNN）模型
- 输入以图的形式表示，可以类比为原子之间的连接关系，这种表示天然适合发现晶体材料
- 初始训练数据来自 Materials Project 公开的晶体结构与稳定性数据

## 2. 主动学习 / 迭代训练循环
- 采用"active learning"训练过程：模型预测新稳定晶体结构 → 用 DFT 验证 → 高质量结果回流为训练数据
- 含两条并行管线：结构管线（基于已知晶体结构生成候选）与组成管线（基于化学式的更随机探索）
- 两条管线的输出均经 DFT 计算评估，结果加入 GNoME 数据库，用于下一轮学习
- 性能提升：稳定性预测发现率从约 50% 提升至 80%（基于 MatBench Discovery 基准）；发现率从低于 10% 提升到超过 80%

## 3. 稳定性判据（DFT 验证）
- 稳定性定义为不分解为能量更低的相似成分，数学上材料须落在凸包（convex hull）上
- 2.2M 晶体位于此前发现的凸包之下；其中 380,000 个位于"最终"凸包，为最强稳定候选
- 使用 Density Functional Theory（DFT）在渐进训练周期中反复校验模型预测能力

## 4. 数据库规模与产出
- 2.2M 新晶体，"equivalent to nearly 800 years' worth of knowledge"
- 380,000 最稳定材料，贡献给 Materials Project 在线数据库
- 稳定材料总数从约 20,000（ICSD 实验）→ 48,000（计算方法）→ 421,000（GNoME）
- 具体产出：52,000 类石墨烯层状化合物（此前仅约 1,000）；528 个锂离子导体（此前研究的 25 倍）

## 5. 自动化程度
- 与 Berkeley Lab 合作的第二篇 Nature 论文展示了自主材料合成
- A-Lab 实验室由 AI 引导机器人，成功合成超过 41 种新材料
- 机器自动产生新配方并合成，开启 AI 驱动材料合成的可能

## 6. 与实验验证的关系
- 外部研究者独立实验制成了 736 种 GNoME 预测的新结构
- 例如：Li4MgGe2S7（首创碱土类金刚石光学材料）、Mo5GeB2（潜在超导体）
- 开放数据集已发布于 GitHub（google-deepmind/materials_discovery），向研究社区提供"recipes"

## 7. 论文与作者
- 主论文发表于 Nature（2023-11-29），作者 Amil Merchant 与 Ekin Dogus Cubuk
- 配套 Berkeley Lab 论文同步发表于 Nature
- 合作方包括 Google Research、Materials Project 与全球团队

---

# GraphCast 关键设计要点

## 1. 模型架构
- 基于**图神经网络（GNN）**，适合处理空间结构化数据
- **迭代式滚动预测**：输入两组数据（6小时前状态 + 当前状态），预测未来6小时天气，再以6小时为步长向前滚动，"rolled forward in 6-hour increments"可生成最长10天预报
- 输出分辨率 0.25° 经纬度（赤道处约 28km × 28km），超过一百万网格点
- 每个网格点预测5个地表变量（温度、风速风向、平均海平面气压等）+ 37个高度层上6个大气变量（比湿、风、温度等）

## 2. 训练数据
- 训练自**ERA5 四十年再分析数据**（ECMWF）——基于卫星、雷达、气象站观测，并用传统数值预报填补观测空缺
- 体现"传统NWP与深度学习互补"的思路：数据层依赖物理模型重建历史

## 3. 与数值天气预报（NWP/HRES）的评估
- 对照基线：ECMWF 的 **HRES**（行业金标准确定性系统）
- 评估覆盖1380个测试变量×预报时效组合，GraphCast 在**超过90%**的项上更优
- 限定对流层（6–20km）时，精度优于HRES达 **99.7%**
- 极端事件评估：用简单飓风追踪器叠加在预报上，飓风路径误差更低；大气河流的均方根误差全程更低

## 4. 精度-速度权衡
- **训练计算量大，但推理极高效**：10天预报在单台 Google TPU v4 上不到1分钟；HRES 需数百台机器的超算运行数小时
- 极端事件预警：Hurricane Lee 提前约9天预测登陆新斯科舍，传统预报仅提前约6天锁定

## 5. 开源与部署
- **模型代码已在 GitHub 开源**（google-deepmind/graphcast）
- ECMWF 已在其网站进行**实时实验运行**
- 附带开源获取论文（作者版本）与 Science 正式发表版（doi: 10.1126/science.adi2336）

## 6. 对科学基础模型管线设计的启示
1. **GNN/图架构适配地球系统数据**：空间关系建模是核心归纳偏置
2. **自回归滚动（autoregressive rollout）**：短期预测器+迭代展开 = 中长期预报，训练用一步预测目标但评估长程展开效果
3. **混合数据来源**：用物理模拟（NWP）生成的再分析数据弥补观测不完整性，实现"AI + 物理模型"协同，而非纯替代
4. **多尺度/多层变量联合预测**：地表+多高度层大气变量同步输出
5. **直接以金标准物理基线为对照**：量化优于多少比例的变量×时效组合，分层报告（全大气 vs 关键层）
6. **通用涌现能力**：未专门训练去检测极端事件，但可通过简单后处理（追踪器）得到更好的极端天气预警
7. **效率与可及性优先**：单卡推理、开源代码，让全球机构可复用
8. **可扩展性**：随更高质量数据增加而持续改进——为科学基础模型的持续训练管线留出空间

---

The web page content provided is an arXiv abstract page for a paper on coupled nonlinear Schrödinger equations (arXiv:2207.03218) — it contains **no information about AlphaTensor**.

I cannot extract the requested technical points (tensor decomposition formulation, action/state spaces, reward definition, AlphaZero search role, discovered algorithms, rank lower bounds) from this document, because none of those topics appear here.

What the actual document does contain:
- **Paper:** "Semiclassical states for coupled nonlinear Schrödinger equations with a critical frequency" by Taiyong Chen, Yahui Jiang, Marco Squassina, Jianjun Zhang
- **System studied:** a coupled nonlinear Schrödinger system on ℝᴺ with small parameter ε > 0
- **Results:** existence of positive ground state solutions, plus concentration behavior as ε → 0
- **Conditions:** 1 ≤ N ≤ 3, positive coupling parameters μ₁, μ₂, β, nonnegative continuous potentials a(x), b(x) that either "achieve 0 with a homogeneous behaviour or vanish in some nonempty open set with smooth boundary"
- **Metadata:** 23 pages, Analysis of PDEs (math.AP), MSC classes 35B05 and 35J50, submitted July 2022, revised May 2023, to appear in Asymptotic Analysis

If you provide the AlphaTensor paper (DeepMind's Nature 2022 work on discovering matrix multiplication algorithms via reinforcement learning) or its text, I'd be happy to extract those technical points for you.

---

根据提供的页面内容（仅包含 arXiv 摘要页，不含全文），我只能提取摘要中明确提到的技术细节。以下是事实要点：

**系统概况**
- AlphaEvolve 是一个"evolutionary coding agent"，通过直接修改代码来改进算法，属于白皮书性质的论文（arXiv:2506.13131，2025年6月16日提交）。
- 系统"orchestrates an autonomous pipeline of LLMs"，即自主编排多个 LLM 组成的流水线。
- 采用进化方法，"continuously receiving feedback from one or more evaluators"——从一个或多个评估器持续获取反馈，迭代改进算法。
- 摘要明确说这扩展了 Romera-Paredes et al., 2023 的自动发现方法范围。

**应用成果（摘要中提到）**
- Google 数据中心：开发了更高效的调度算法。
- 硬件加速器：发现了功能等价的电路设计简化。
- 加速了支撑 AlphaEvolve 本身的 LLM 训练。
- 数学/CS 领域：发现"novel, provably correct algorithms"（新颖且可证明正确的算法）。
- 4×4 复数矩阵乘法：用 48 次标量乘法，"offering the first improvement, after 56 years, over Strassen's algorithm in this setting"（56 年来在该设定下首次超越 Strassen 算法）。AlphaEvolve 开发了一个搜索算法来找到该过程。

**页面未包含的信息**
关于以下内容，摘要页中**没有**技术细节（需要查看 PDF 或 HTML 全文）：
- programs database、islands 岛屿模型、sampler 等进化系统具体组件
- LLM ensemble 的具体工作机制
- 防止 reward hacking / 评估作弊的机制
- 代码表示方式（diff、AST 等）
- 评估流水线设计（级联、并行评估）

如需这些细节，需访问论文全文（arXiv:2506.13131 的 PDF 或实验版 HTML）。

---

The provided content is only raw PDF source (metadata, outlines, object tables, compressed streams) — the body text is compressed in FlateDecode streams that weren't extracted. From what is readable, I can only confirm document-level facts, not the technical details you asked about. Here's what the visible content does establish:

**Document identification**
- Title: "AlphaEvolve: A coding agent for scientific and algorithmic discovery" (arXiv 2506.13131, CC BY-NC-ND 4.0 license).
- Authors include Alexander Novikov, Ngân Vũ, Marvin Eisenberger, Emilien Dupont, Po-Sen Huang, Adam Zsolt Wagner, Sergey Shirobokov, Borislav Kozlovskii, Francisco J. R. Ruiz, Abbas Mehrabian, M. Pawan Kumar, Abigail See, Swarat Chaudhuri, George Holland, Alex Davies, Sebastian Nowozin, Pushmeet Kohli, Matej Balog.

**Structural hints (from outline/destination names)**
- Sections labeled section.1–6, plus appendix.A "Faster matrix multiplication: Full results" and appendix.B "Details of mathematical discoveries of AlphaEvolve".
- Appendix B includes subsections such as "First autocorrelation inequality" (B.1) and "Packing circles inside a rectangle of perimeter 4 to maximize sum of radii" (B.13).
- The paper contains multiple code listings (lstlisting.-1 through -6, with numbered lines up to ~130 in one), a lemma, and figures 1–18 — consistent with a system description plus applied case studies.
- Citation keys hint at related work on evolutionary methods (koza1994genetic, lehman2023evolution, ye2024reevo), LLM coding agents (gemini25, o3, shinn2023reflexion, yao2023react), and application domains (matrix multiplication via strassen1969gaussian/laderman, Erdős-type problems, sphere/kissing numbers).

**What I cannot verify from this content**
Your five specific questions — programs database/islands/sampler, Flash/Pro LLM ensemble and prompting, diff/AST/file-level code representation, cascading parallel evaluation pipeline, and anti-reward-hacking measures — are all described in the compressed content streams, which are not readable here. The metadata does reference section.2 subsections (2.1–2.6) that likely cover the system architecture, and section.3 subsections 3.1–3.3 plus subsubsections 3.3.1–3.3.4 that likely cover applications, but the actual text is unavailable.

To extract those details, you would need the decoded PDF text (e.g., via pdftotext or a text extraction tool) or the arXiv HTML/source version, then I can summarize the five topics with quotes kept under 125 characters each.

[Binary content (application/pdf, 3.4MB) also saved to /Users/imakemacmini/.claude/projects/-Users-imakemacmini-MKSoft-LHW-SCIforge/49e8f8bf-4fb4-4036-8845-f597f578f662/tool-results/webfetch-1790394139989-clwknp.pdf]