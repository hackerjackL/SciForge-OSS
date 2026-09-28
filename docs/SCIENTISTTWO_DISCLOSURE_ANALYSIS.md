# ScientistTwo 86 篇成稿披露模式分析（v1.7.1 写作契约实证依据）

> 语料：`scientist-two.github.io` 仓库 `generated-papers/` 全部 86 篇 PDF（8 领域，
> 中位 17.5 页，ICLR 2025 模板匿名评审格式），逐篇提取摘要 + 结构 + 正文披露段。
> 本文回答三个问题：他们**怎么写**、怎么**披露数据**、怎么**呈现结果**。
> 结论已编码进 `skills/support/paper-writing/SKILL.md` rule 2b / 自检 12b。

## 1. 摘要骨架（86/86 解析成功，中位 240 词 / 7 句）

| 模式 | 占比 | 含义 |
|---|---|---|
| "We introduce/present/propose X" 开场 | **99%** | 方法永远是主角 |
| 显式 %/points/× 量化主张 | **87%** | 主张必带数字 |
| 摘要末句为正面定位或"ablations confirm" | **95%** | 收口永远落在成立的事上 |
| "We are the first" | 0% | 不吹首创，用证据说话 |
| "We refute/falsify" 作主语 | **0%** | **没有一篇把证伪当头条** |
| "We report negative results" | **0%** | 不存在"以负结果为名"的写法 |

## 2. 失败词的真相：33% 含 "fail"，但全部指向他人

抽读例句：

- "standard methods … **fail to capture** non-stationary dynamics"（TVCS-IF）
- "existing approaches **suffer from** three failure modes"（CS-HLA）
- "they **struggle with** explicit 3D spatial reasoning"（SAVVY-Vortex）

**"fail" 在 86 篇摘要里 100% 是 prior-art 动机（问题陈述），0% 是自家结果。**
自家迭代失败的处理方式（直接例句）：

> "This **outperforms** both the original Spike-driven PointFormer-S baseline
> (+1.65% on ModelNet40, +1.37% on Objaverse-LVIS) **and our prior unsimplified
> 4-module design iteration**"（DWGR-SVL）

——自己上一代失败设计被写成**被超越的基线**，一个括号带过，主语是 outperforms。
这就是"失败是过程，不是论文"的实操形态。

## 3. 数据披露密度

- 每摘要**中位 15 个数字**（min 8 / max 28）：+2.1%、0.059µs/prompt、369,740-structure、
  p_clean<0——所有主张当场兑现为量。
- 正文标配：`Ablation Studies` 独立小节 + "characterize the design space through
  **six ablations**"（CS-HLA）+ "systematic ablations show that exact rational
  recovery eliminates floating-point false positives"（DiffTrop）。
- **消融的写法是 confirm/eliminate/characterize，不是 confess**：每个被保留组件
  被证明必要（confirm necessity），每个被弃组件被证明多余（eliminate），
  整个设计空间被"刻画"（characterize）——负向测量全部转化为对最终方法的支撑。
- Limitations 存在（19% 摘要提及，多为 "under review" 版式尾部），但**从不进摘要
  主角位**，且写法是 regime/边界陈述而非忏悔。

## 4. 结构模板（以 CS-HLA 为例，86 篇同构）

```
1 Introduction（gap→contributions 列表，全 positive）
2 Related Work（他人局限=fail 词唯一容身处）
3 Method（问题形式化→机制→闭式解）
4 Experiments
  4.1 Setup and Evaluation Protocol（预注册式协议）
  4.2 Main Results（主表，全数字）
  4.3 Comparison with Baselines（含自家前代迭代当基线）
  4.4 Cross-Benchmark Generalization
  4.5 Ablation Studies（"六消融刻画设计空间"）
  4.6 Efficiency / Latency
5 Conclusion（正面定位收口）
```

## 5. 与 SciForge 第一轮产出的差距诊断

| 维度 | S2 86 篇 | 我们 ARC-BENCH 五篇 |
|---|---|---|
| 摘要开场 | 99% "We introduce X" | Q02 以 "We test that attribution" 引入质疑 |
| 自家失败 | 括号内当被超越基线 | ML02 摘要写 "was discarded by its own promotion gate" |
| null 处理 | 0% 当头条；归因 null 转写为 regime 事实+仪器贡献 | Q02 摘要 "no consistent loss…refuted" 三连 |
| 数字密度 | 中位 15/摘要 | 我们约 8-12，偏低 |
| 收口 | 95% 正面定位 | S01 收口在 "consequential decisions"（中性） |

**根因**：旧契约 rule 2 强制"limitation first"+ 负贡献扫描把一切"负"压进
Limitations——agent 于是把归因研究写成失败报告。S2 的语料证明成熟写法是：
**失败只活在两个地方——related work 里别人的 fail，和消融表里被 confirm/
eliminate 的过程证据；摘要和贡献列表里只有成立的事。**

## 6. 契约变更（已落地 paper-writing SKILL.md）

- **rule 2b（重写为实证版）**：方法永远主角；自家弃案写成"被超越的前代/
  设计空间刻画"；归因 null 写成 regime 正面事实（polarity: positive）；
  数据/CI/消融行一个不少——只换叙事主角，选择性报告仍然禁止。
- **自检 12b（机械四查）**：protagonist test（自家结果失败语态当主语→WARN
  `failure_as_protagonist`；prior-art fail 词保留）；量化密度 <8 数字→WARN
  `under_quantified`；弃案未整合（无"超越/确认/刻画"框架）→WARN
  `failure_not_integrated`；摘要收口非正面→WARN。

## 7. 红线（不变）

S2 模式是**呈现纪律**，不是造假许可：他们的消融表全量披露、每数可复算
（1814 引文零幻觉、方法-代码逐行比对）。我们同步保留：CLAIMS_FROM_RESULTS
polarity 门、fairness ledger、s2_audit 增益复算。删数据=reward hacking，
任何门都不会放行。
