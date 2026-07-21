# 125 Science Problems Demo Index

> **Status (v2.9 — stub补建)**: This file is a **Demo-only** index of 125 representative science problems. It is referenced by [`README.md`](../README.md) and [`AGENT_GUIDE.md`](../AGENT_GUIDE.md) as the canonical "what does a Q-id look like" example. **NOT auto-searched**: the human user supplies the Q-id (or free-form problem text) at invocation; the orchestrator does NOT iterate this index.

## Purpose

1. **Demo of the framework's scope**: 125 problems spanning physics, mathematics, computer science, medicine, economics, education, materials, earth science, astronomy, chemistry, engineering — to illustrate that SciForge-OSS is discipline-agnostic.
2. **Q-id format reference**: shows the `Q001`-style identifier convention (but the framework accepts any Q-id format, or even no Q-id for ad-hoc problems).
3. **Invocation examples**: each problem below is a valid input to `/125-problems-pipeline`.

## How to use

### Solve one problem (canonical)

```
/125-problems-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
```

The human supplies the specific Q-id. OSS processes exactly one problem end-to-end per invocation.

### Free-form problem (no Q-id needed)

```
/125-problems-pipeline "Prove that the Riemann zeta function has no zeros for Re(s) > 1"
```

The framework does NOT require a Q-id from this index — any scientific problem text is a valid input.

## The 125 Problems (Demo Index)

> **Note**: This is a **demo index**, not an exhaustive problem bank. The framework supports any number of problems in any domain. The 125 problems below are curated examples for the "AI for Scientist Anything" demonstration.

### Physics (Q001-Q020)

| Q-id | Problem |
|------|---------|
| Q001 | 宇宙的起源与演化 |
| Q002 | 暗物质与暗能量的本质 |
| Q003 | 黑洞信息悖论 |
| Q004 | 量子引力理论的构建 |
| Q005 | 时空的量子结构 |
| Q006 | 基本粒子的质量起源 |
| Q007 | 中微子质量的本质 |
| Q008 | 强 CP 问题 |
| Q009 | 宇宙弦的存在性 |
| Q010 | 引力波的探测与性质 |
| Q011-Q020 | *(additional physics problems — demo placeholder)* |

### Mathematics (Q021-Q040)

| Q-id | Problem |
|------|---------|
| Q021 | 黎曼猜想的证明路径 |
| Q022 | P vs NP 问题 |
| Q023 | Birch 和 Swinnerton-Dyer 猜想 |
| Q024 | Navier-Stokes 方程解的存在性与光滑性 |
| Q025 | Hodge 猜想 |
| Q026 | Collatz 猜想 |
| Q027 | 孪生素数猜想的最新进展 |
| Q028 | Goldbach 猜想 |
| Q029 | 大基数的存在性 |
| Q030 | 非交换几何在数学物理中的应用 |
| Q031-Q040 | *(additional mathematics problems — demo placeholder)* |

### Computer Science / AI (Q041-Q060)

| Q-id | Problem |
|------|---------|
| Q041 | 大语言模型的涌现能力 |
| Q042 | AI 系统的可解释性 |
| Q043 | 神经网络的泛化理论 |
| Q044 | 强化学习的样本效率 |
| Q045 | AI 对齐问题的理论框架 |
| Q046 | 量子优势的实验验证 |
| Q047 | 分布式系统的 CAP 定理实践 |
| Q048 | 计算复杂性类的相对化障碍 |
| Q049 | 算法公平性的数学定义 |
| Q050 | AI 安全的形式化验证 |
| Q051-Q060 | *(additional CS/AI problems — demo placeholder)* |

### Life Sciences / Medicine (Q061-Q080)

| Q-id | Problem |
|------|---------|
| Q061 | 蛋白质折叠的物理机制 |
| Q062 | 意识的神经相关物 |
| Q063 | 衰老的生物学基础 |
| Q064 | 癌症的进化动力学 |
| Q065 | 神经退行性疾病的分子机制 |
| Q066 | 免疫系统的记忆形成 |
| Q067 | 基因调控网络的设计原理 |
| Q068 | 微生物组的生态稳定性 |
| Q069 | 表观遗传信息的跨代传递 |
| Q070 | 脑机接口的神经编码 |
| Q071-Q080 | *(additional life sciences problems — demo placeholder)* |

### Economics / Social Sciences (Q081-Q100)

| Q-id | Problem |
|------|---------|
| Q081 | 金融市场波动性的微观结构 |
| Q082 | 经济增长的内生动力 |
| Q083 | 不平等的代际传递 |
| Q084 | 货币政策的最优设计 |
| Q085 | 教育回报的因果识别 |
| Q086 | 社会网络的形成机制 |
| Q087 | 投票系统的数学性质 |
| Q088 | 博弈论中的 Nash 均衡学习 |
| Q089 | 行为经济学的偏好理论 |
| Q090 | 发展经济学的制度基础 |
| Q091-Q100 | *(additional economics/social problems — demo placeholder)* |

### Earth / Climate / Materials / Astronomy (Q101-Q125)

| Q-id | Problem |
|------|---------|
| Q101 | 气候敏感度的约束 |
| Q102 | 板块构造的驱动机制 |
| Q103 | 地磁反转的触发因素 |
| Q104 | 高温超导的配对机制 |
| Q105 | 拓扑绝缘体的表面态 |
| Q106 | 电池材料的离子扩散 |
| Q107 | 系外行星的大气探测 |
| Q108 | 宇宙再电离的时序 |
| Q109 | 恒星形成的初始质量函数 |
| Q110 | 系外行星宜居带的定义 |
| Q111-Q125 | *(additional problems — demo placeholder)* |

## See Also

- [`README.md`](../README.md) — project overview + 125 题 Demo 说明
- [`AGENT_GUIDE.md`](../AGENT_GUIDE.md) — invocation patterns + Q-id format
- [`skills/orchestrator/125-problems-pipeline/SKILL.md`](../skills/orchestrator/125-problems-pipeline/SKILL.md) — the 20-phase DAG loop orchestrator
