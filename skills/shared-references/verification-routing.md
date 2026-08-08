# Verification Routing Contract (SciForge-OSS — Experiment-First by Default)

> **Status (v1.0)**: 决定"这篇论文的验证方式"的路由契约。实测反馈（v5.0）：旧管线默认任何论文都先走符号/理论推导、实验只是补充验证——对有数据、可计算的问题是**本末倒置**，且符号验证本身被判定"无意义"。本契约把验证路由**前移到 Phase 6 入口**：先判路由，再选验证链。

## 1. 路由规则（入口判定，一次定终身）

Phase 6（theory-derivation / experiment-execution）入口，读 `refine-logs/domain-signature.json` 的 `evidence_type` + 问题自身的可计算性信号，按下表路由，写入 `refine-logs/VERIFICATION_ROUTING.json`：

| 路由 | 触发条件 | 验证链 |
|------|---------|--------|
| **experiment-first（默认）** | `evidence_type` ∈ {correlational, causal_inference, simulational, empirical, experimental}，或问题涉及数据集/训练/仿真/实证 | `/experiment-execution` 主验证：toy 快速验证（~20 轮量级）→ 主实验 → 强制实验矩阵（method-registry §3）。`/theory-derivation` **降级为可选辅助**（仅当方法有可推导结构且推导能指导实现时才走；无推导不阻塞） |
| **theory-only（例外）** | `evidence_type = derivational` 且问题**无数据、无可执行计算**（纯数学证明、部分人文/哲学论证、概念性理论构建） | `/theory-derivation`（engine=sympy 或 manual）主验证 + `/logic-verification`；不跑实验，但 toy 级数值 sanity（若可行）仍鼓励 |
| **hybrid（显式声明）** | 论文贡献同时依赖理论结果与实验验证（如"定理 + 算法"型工作） | 理论推导与实验并行推进，两者都是主验证；`verification_type = theory+experiment` |

**判定纪律**:
1. **默认 experiment-first**——拿不准就按实验路由，因为"有东西可跑"的论文占绝大多数
2. theory-only 必须满足**双条件**（derivational ∧ 无可执行计算），只满足一条仍按 experiment-first
3. 路由结果写入 `VERIFICATION_ROUTING.json`（route/evidence_type/reason 三字段），下游 skill 只读不改
4. 人文/社科无数据问题 → theory-only 合法（"没有东西的就是没有办法"）；但只要存在可收集数据或可仿真对象，优先 experiment-first

## 2. experiment-first 的验证形态

1. **Toy 快速验证**（idea 级）：小规模（~20 轮训练 / 1-10% 数据 / 合成已知效应数据）验证"这个想法方向对不对"——这是**想法生死判**，不是论文实验
2. **主实验**（论文级）：按 method-registry §3 强制实验矩阵执行（主实验 + 基线对比 + 消融 + 超参 + 敏感性）
3. **理论辅助**（可选）：有推导结构时补充理论分析，放正文 Theory 小节或附录；**不要求** SymPy 全步验证，手推 + 数值交叉核对即可

## 3. 与各 skill 的关系

- `/auto-pipeline` Phase 6 入口调用本契约完成路由，再分发
- `/theory-derivation`：接受 `route` 字段——experiment-first 下被调用时以辅助模式运行（不阻塞、不强制全步 SymPy）
- `/experiment-execution`：experiment-first / hybrid 下的主验证执行者
- `/method-registry`：hash-lock 前检查强制实验矩阵完整性（experiment-first / hybrid 路由下）
- `/paper-modes`：读 `VERIFICATION_ROUTING.json` 选 section 布局（experiment 模式优先）

## 4. See Also

- [`methodology-and-context-contract.md`](methodology-and-context-contract.md) — 充分性停止规则
- [`../support/experiment-execution/SKILL.md`](../support/experiment-execution/SKILL.md) — 实验执行（toy→full + 后台调度）
- [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) — 理论推导（辅助模式）
- [`../support/method-registry/SKILL.md`](../support/method-registry/SKILL.md) — 强制实验矩阵
