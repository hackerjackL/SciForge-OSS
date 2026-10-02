# ScientistTwo Parity — v1.7.0 对标复刻记录

> 结论先行：**我们复刻的是他们的机制，不是他们的算力**。ScientistTwo（arXiv:2609.19644,
> Google Cloud AI Research + Waterloo, 2026-09-17）的 harness 闭源；本文件记录
> （a）他们靠什么赢、（b）哪些机制已在 v1.7.0 变成我们的开源代码、（c）哪些差距
> 是诚实存在、尚未追平的。协议事实源（机制↔实现↔门映射）：
> [`skills/shared-references/s2-protocol.md`](../skills/shared-references/s2-protocol.md)。

## 1. 他们的成绩单（为什么值得对标）

| 指标 | ScientistTwo | 我们（v1.6 → v1.7） |
|---|---|---|
| 输入 | 107 个 ICLR/NeurIPS/ICML **已接收论文**的问题定义 + 官方 codebase | 自带问题 / 21-phase DAG；**v1.7 起有 CPU demo 子 bench** |
| 产出 | 86/107 成功（80.4%），平均相对人类 SOTA **+25.2%** | DEMO-RK4 单例 + bench 4/4 PROMOTED（demo 级） |
| 评审 | ScholarPeer 7.5±1.3，接收率 91.9%；Stanford Agentic Reviewer 72.1% | 跨模型面板 + 分数驱动 rebuttal（**v1.7 起锚点校准 + <8 必 rebuttal**） |
| 完整性审计 | 重跑代码 / reward-hacking / 1814 引文零幻觉 / **方法-代码逐行比对** | 3 层引用 + leakage/fantasy（v1.7 补上 **增益算术 + 划分纪律 + 方法↔代码 token 对齐**） |
| 成本 | $3765 / 2–3 天每篇（idea refinement + 评审循环为大头） | RUN_BUDGET 真记账；单机 host-mode 近零成本（产出亦 demo 级） |
| 代码 | **闭源**（GitHub 仅项目页 + 86 篇 PDF） | 全开源（本轮起含对标层） |

## 2. 已复刻机制（全部是代码，不是 prose）

| 他们的机制（论文） | v1.7.0 实现 | 强制点 |
|---|---|---|
| Subset→Full-Set 阶梯 + 三态 Critic {Bad\|Good\|Engineer≤2} | `kernel/sciforge/s2/ladder.py` | **6c 边界门** `s2_ladder`（`scripts/s2_ladder_gate.py`） |
| 工程师轮耗尽 = 不晋级 | `ladder.validate` `engineer_rounds≤2` | 同上 |
| 全集复验严格优于基线（平局不算赢） | `ladder.is_improvement`（方向感知） | 同上 |
| Component Ablation 5–6 计划 + AblCritic {Good\|Refine} | `s2/ablation.py` | **相位 10 边界门** `s2_ablation` |
| "新必须严格优于旧"才换状态 | `ablation.ablcritic` + 单调 `current_best` | 同上 |
| 评审分 <8 触发 Rebuttal（≤2 轮，真跑补充实验） | `s2/reviewloop.py`（默认阈值 8.0，env 可覆） | `_native_review` 写 `REBUTTAL_PLAN.json` + `REVIEW_STATE.meta_review` |
| Meta-Review {Accept\|Refine} | `reviewloop.meta_review`（ACCEPT=过线且零 fatal） | 同上 |
| 先给已知质量论文打分锚定量尺（人类中稿均分 6.2） | `s2/calibration.py` OLS + `usable` 退化保护 | `_native_review` 消费 `CALIBRATION.json` |
| Idea Evolution + **探索保证**（每轮混入未评 seed） | `s2/ideas.py` | **loopback 事件 + `KILL_DECISIONS.jsonl` 携带 `exploration_seed`** |
| 完整性审计：reward-hacking + 方法-代码逐行比对 | `s2/audit.py`（三查：增益算术/划分纪律/方法↔代码 ≥80%） | **wrap-up 门** `s2_audit` |
| 相对人类 SOTA 增益口径（+25.2%） | bench `relative_gain_pct`（方向感知） | `bench/s2demo/run.py` exit code |
| 成本透明（$3765/篇） | `RUN_BUDGET.json` + bench 每臂耗时 | 既有预算门 |

工程取舍：**不加相位**（21-phase 钉保持，e2e/文档/注册表零连锁），门全部遵循
smoke_gate 的 SKIP 语义（theory-only 路由不受影响），S2 机器产物走 `.sciforge/audits/`
（与 `REVIEW_PANEL.json` 同类：s2 门强制，`validate_verdicts` 不索要）。

## 3. demo 子 bench（`bench/s2demo/`）—— 他们的 mold，我们的算力

无 GPU、仅 Colab/本机 CPU 的约束下，先建"自留地"再谈接真题：

- 4 个 numpy-only 任务（非线性分离 / 季节预测 / 各向异性聚类 / 概率校准），
  每个 = 结构化 briefing + 基线复现 + 6 轴 rubric + human_anchor 6.2；
- harness **import 生产 ladder**（门与 bench 同一契约）；
- 实测 4/4 PROMOTED（T1 +177.8% / T2 +74.1% / T3 +6.7% / T4 +56.2%），
  exit 0；报告含 subset/full 双段与每臂耗时。

## 4. 已闭合与尚未追平的差距（v1.7.1 更新）

**已闭合（两轮 ARC-Bench 实测）**：
1. **真题**：ARC-Bench（AIMING-Lab-UNC，55 话题 × 5 域）已拉取并两代全量跑
   （`runs/ARC-BENCH{,2,3}/`，本地不入库）：五域各一题 × 两轮 + v1.7.1 验证轮，
   全部独立复核（门重跑 + PDF 逐页读 + 摘要语态量化）。
2. **完成诚实性**：`completion_gate`（wrap-up）把 S01 式"报告声称完成但工作区
   没有 PDF"变成物理不可能——声明的每个路径必须存在于磁盘。
3. **写作标准**：86 篇 S2 语料量化分析 → voice contract（方法主角开场、
   ≥8 数字、正面收口、弃案=过程证据）；二轮五篇摘要全部达标（本机 PDF 提取验证）。

**尚未追平（诚实清单）**：
1. **量级**：86 篇成稿 vs 我们 ~11 篇全链 run。差距 = 算力 × 迭代轮次，不是机制缺失。
2. **评审校准的实证**：`CALIBRATION.json` 机制在，尚无"先给 N 篇已知论文打分建
   映射"的实测批（需要评分数据）。
3. **方法-代码比对粒度**：他们声称逐行；我们 token 级（≥80% + 反向清单）。
4. **外部评审双通道**（ScholarPeer + Stanford Agentic Reviewer）：自建面板 +
   锚点校准，无第三方评审服务接入。
5. **SOTA 真训练后端**：`sota.py` 爬山驱动与 trainer seam 已就位，但真 GPU
   训练（LoRA/PEFT）尚未在集群上跑通一轮——CPU 测试环境只能爬合成/数值 SOTA。

## 5. v1.7.1 深度优化（用户指令：约束分级 / 卫生 / 严格 DOI / 灵活 intake / 图高级化 / 二区可投）

- **约束三档** `--discipline strict|balanced|lean`：severity ∝ 后果 × 事后不可
  检测性；lean 只留不可检测类硬门，cosmetic 类披露——强模型免负优化税。
- **claim_mode 双模**：`sota`（核心必须赢，被证伪=上游 KILL，正文零失败叙事）/
  `attribution`（null 即发现）；数据全保留，禁选择性报告。
- **二区可投就绪门** `submission_ready.py` @15.5：READY / MINOR_REV / MAJOR_REV /
  NOT_READY 四级（硬项：verdicts 完整 + s2 门电池 + PDF + DOI + leakage + claim
  一致性；软项：摘要形状、章节序、附录独立、图预算/多样性、评审分、卫生）。
- **SOTA 爬山 + 失败记忆**：`sota.py`（incumbent 复现 → 记忆播种变异 → geomean
  closed-fraction + capability-floor/回归 CI → plateau 停）；`sciforge memory
  build/query` 让 LESSONS.json 从"写了没人读"变成相位 2/6b 与爬山的可检索先验。
- **严格 DOI / intake / 图 / 卫生 / 零内部话术**：见 CHANGELOG 1.7.1 增补节。

## 6. 一句话

他们有引擎没开放，我们有门有引擎还有**两轮真题实测**；机制差距 v1.7 归零、
真题差距 v1.7.1 用 ARC-Bench 闭合一半，剩算力与第三方评审两条外部依赖。
