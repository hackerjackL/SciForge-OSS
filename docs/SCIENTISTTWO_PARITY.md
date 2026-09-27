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

## 4. 尚未追平的差距（诚实清单）

1. **真题**：他们 107 个顶会已接收问题 + 官方 codebase；我们是合成 demo 任务。
   下一步候选：ARC-Bench（55 话题 × 5 域、ML 域 CPU 可跑、带 rubric）→
   AutoResearchExam（29 任务 Docker+hidden tests）。
2. **量级**：86 篇成稿 vs 我们 1 篇全链 demo + 4 个 bench 任务。差距 = 算力 ×
   迭代轮次，不是机制缺失。
3. **评审校准的实证**：`CALIBRATION.json` 机制在，但还没有跑过"先给 N 篇已知
   论文打分建映射"的实测批（需要评分数据）。
4. **方法-代码比对的粒度**：他们声称逐行；我们是 token 级（≥80% 落地 + 反向清单），
   结构等价、粒度更粗。
5. **外部评审双通道**（ScholarPeer + Stanford Agentic Reviewer）：我们是自建面板 +
   锚点校准，无第三方评审服务接入。

## 5. 一句话

他们有引擎没开放，我们有门有引擎（本轮补齐）；**机制差距在 v1.7 归零，
真题与算力差距用 bench 起步、靠 ARC 类外部标尺收敛**。
