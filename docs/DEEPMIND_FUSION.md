# DeepMind 顶级项目融合调研（v1.5.0-w2，最终版）

> 子代理 WebFetch DeepMind 官方博客/论文/GitHub 完成的完整调研。下方为调研全文 +
> 本项目已落地映射。GNoME 湿实验类确认不适用 kernel。

## 本项目已落地映射（kernel 级）

| DeepMind 模式 | 来源 | 我们的实现 | 位置 |
|---|---|---|---|
| Evaluator 契约 + 评估级联 | AlphaEvolve | HybridDomain cascade: CI/golden → research_validity → LLM judge | kernel/sciforge/evolve.py |
| 防 reward-hacking（评分器冻结+泛化切分） | AlphaEvolve | FROZEN_PREFIXES + 三分片 held-out + probe 预检 | evolve.py S12/S13/S16 |
| 生成→验证→强化 | AlphaProof | LESSONS.verified_proofs（仅 PASS 进先验）+ memory 索引 | pipeline.py / memory.py |
| 主动学习回流 | GNoME | retrain_from_results → domain-signature | domain-adaptation-contract.md |
| 神经-符号分工 | AlphaGeometry | LLM 出构造，SymPy/机械门严格验证 | theory-derivation + gates |
| 形式可验证性锚 | AlphaProof/Geometry | 25 个注册 verdict + validator 硬门 | scripts/validate_verdicts.py |
| Tournament 评审 | AI Co-Scientist | 3 盲审视角 + 分歧仲裁 | kernel/sciforge/review.py |
| 双轨评估（代理指标+真实成本） | AlphaTensor | FAIRNESS 效应量/CI + RUN_BUDGET 真实成本 | fairness_gate.py / providers.py |
| EVOLVE-BLOCK diff 变异 | AlphaEvolve | Patch ops old/new 精确替换（非整段重写） | evolve.py Patch |

---

信息已足够（Deep Research 产品页多链 404，该小节按"部分跳过"处理）。以下为调研报告。

---

# DeepMind 自动科研/算法发现项目设计模式调研（2023–2026）

## 1. AlphaEvolve / FunSearch
**定位**：LLM+进化搜索改写算法代码，用自动评分器闭环优化。  
链接：https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/ ；arXiv:2506.13131；FunSearch 同源博客（cap set、bin packing）。

**可迁移模式**
- **程序表征 = `# EVOLVE-BLOCK` 包裹的代码块 + SEARCH/REPLACE diff**：我们 Runtime Kernel 可把"待进化产物"（检索策略、prompt 模板、工具编排代码）用同样方式标记演化区，变异走 diff 而非整段重写。
- **Evaluator 契约化**：用户只需提供 `evaluate(program) -> dict[str,float]`（约定最大化）；评分函数即管线中"可执行、可回归"的 metric 模块，天然适合 21-phase 中每个阶段的 gate。
- **评估级联 + 并行**：先小样本/便宜测试剪枝，昂贵评估（可花百计算小时）放 asyncio 异步集群——对应 kernel 的"分层验证闸门"。
- **Islands + MAP-Elites 程序库**：数据库存"程序+分数"，按探索/利用权衡重采样；比 FunSearch 省两个数量级样本。可直接做成"假设/方法库"的演化调度器。
- **防作弊**：代码执行 grounding（拒绝未通过评估的建议）、正确性 by construction（只允许改动安全区域，如 tiling 而非数学核）、泛化切分（一半输入形状训练/一半评估）、数值边界处理（舍入到整数/半整数）。LLM 还可给"简洁性"等软评分，避免硬指标单点作弊。

**代码化/验证化**：把"创意"压缩为 diff 建议，把"对错"全部交给可运行 evaluator；人只写 h 函数与 seed。

## 2. AI Co-Scientist
**定位**：Gemini 2.0 多 agent 从科研目标生成可验证假说（research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/）。

**可迁移模式**
- **角色分解**：Generation / Reflection / Ranking / Evolution / Proximity / Meta-review + Supervisor 排队调度——对应我们管线里"生成-评审-进化-元评审"独立 phase，而不是一个长 prompt。
- **Tournament Elo 评审**：两两对比自博弈出分，再与专家偏好校验（GPQA 相关性）；可作为论文/假说排序模块，但须保留"自评≠ground truth"告警。
- **生成-筛选-细化闭环 + test-time scaling**：推理预算↑→Elo↑；把"迭代轮数/并行假设数"做成显式算力参数。
- **人机种子注入**：科学家可投喂想法与自然语言反馈——对应管线的 human-in-the-loop 反馈通道。

**代码化/验证化**：评审流程与队列调度被 agent 化编排，但假说真伪仍靠外部实验（KIRA6、肝类器官等湿实验）——纯软件管线只能做到"内部一致性+文献 grounding"。

## 3. AlphaProof / AlphaGeometry
**定位**：Lean 形式验证 + 搜索/RL；神经-符号几何证明（IMO 银牌级）。链接见 DeepMind IMO/AlphaGeometry 博客与 Nature。

**可迁移模式**
- **符号验证闸门**：候选产出必须过 Lean/规则引擎类"机器可检查"关卡，才允许进入下一 phase——kernel 的 formal-check gate 原型。
- **快慢双系统**：LLM 预测"辅助构造/引理"（打开新搜索分支），符号引擎穷尽推导；适合文献论证链：LLM 提假设骨架，验证器做引用/逻辑核查。
- **合成数据 + traceback**：先穷尽推导再反推所需构造，造 1 亿训练样本——可迁移为"从可验证结果反推方法描述"的训练数据生成器。
- **竞赛期持续搜索**：对题目变体自我强化直至找到解，对应管线的"难题专用长搜索预算"。

**代码化/验证化**：证明正确性 100% 机器验证，消除幻觉推理步；代价是领域受限（Lean/Mathlib 覆盖面）。

## 4. AlphaTensor
**定位**：RL 发现更快矩阵乘法（Nature 2022；github.com/google-deepmind/alphatensor）。博客直链 404，方法细节以仓库+AlphaEvolve 文中对比为准，**未深读论文正文，此处仅用已验证事实**。

**可迁移模式**
- **搜索空间=可验证数学对象**（张量分解），评分=秩/乘法次数，产物自带正确性证明。
- **非等价性认证**（14,236 个 4×4 算法用 invariants 证明互不等价）→ 结果去重/多样性认证模块。
- **理论指标 + 实测 benchmark 双评估**（rank 之外还测 V100 真速）→ 我们评估应"代理指标+真实成本"双轨。

## 5. GNoME / GraphCast
**定位**：材料图网络主动学习（2.2M 晶体，Nature 2023）；GNN 天气基础模型（超 90% 变量优于 HRES，开源）。

**可迁移模式**
- GNoME：**预测→DFT 验证→回流训练**的主动学习环，双管线（结构/组成）并行探索；凸包判据=领域可计算真值。湿实验/算力依赖重，**不适合进 kernel**，但"验证-回流"环可借鉴。
- GraphCast：自回归短程滚动=长程预报；**直接对标金标准基线并报告胜率**；用再分析数据补观测——对应"用仿真/旧数据当 oracle"。

## 6. 文献/知识工具
Deep Research 与 Gemini for Science 官方页多次 404，**该类产品机制细节跳过**（仅 publications 页可见 Gemini for Science、ProEval 评测等条目）。Co-Scientist 自陈文献核查是短板——提示我们文献 grounding 需独立 phase，而非默认能力。

---

## 融合优先级表（对 21-phase Runtime Kernel）

| 模式 | 优先级 | 落点 | 理由 |
|---|---|---|---|
| Evaluator 契约 + 评估级联 | **P0** | 各 phase gate | 纯软件、防 reward hacking 的地基 |
| EVOLVE-BLOCK + diff 变异 | **P0** | 策略/prompt 演化模块 | 低算力、立刻可做 |
| Tournament/Elo 评审 | **P1** | 论文/假说排序 phase | 便宜有效，需防自评偏差 |
| Formal-check gate（Lean/规则/引用核查） | **P1** | 结论发布前闸门 | 领域受限但价值最高 |
| Islands 程序库 + MAP-Elites | **P1** | 假设/方法库 | 中等工程量，长期收益大 |
| 多 agent 角色分解 + Supervisor | **P2** | phase 间编排 | 可先用工作流脚本近似 |
| 正确性 by construction / 泛化切分 | **P2** | 评估设计规范 | 设计原则，随处可嵌 |
| 非等价性认证 | **P3** | 结果去重 | 小众但便宜 |
| GNoME 主动学习+湿实验 | **不适用** | — | 需 DFT/机器人 |
| GraphCast 级基础模型 | **不适用** | — | 需大规模算力与专有数据 |

**一句话结论**：DeepMind 把"假说对不对"从 prompt 里抠出来，变成**可执行 evaluator + 符号/数值验证 + 泛化切分**；LLM 只负责提 diff、开搜索分支。我们的 Runtime Kernel 应优先代码化"Evaluate 契约、级联闸门、演化库"，评审用 tournament 佐证，最后才考虑湿实验类不可迁移组件。