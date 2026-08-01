---
name: novelty-check
type: reference-skill
role: novelty-verifier
---

# DAG Skill: Novelty Check & Idea Elimination

## Quick Reference

- **Purpose**: 4 维评估 (新颖性×0.45 + 可行性×0.25 + 相关性×0.15 + 工程落地×0.15) → 淘汰弱 idea
- **Input**: IDEA_DAG.json (from /idea-discovery)
- **Output**: novelty_report.json + survivor.md
- **Key**: 最多 1 个 idea 存活到推导阶段；综合评分 < 0.6 淘汰

## Use When

使用此 skill 当 idea 已由 `/idea-discovery` 生成后。每个 idea 被独立评估新颖性、可行性和相关性。弱或非新颖的 idea 被**淘汰**——只有最强的存活到推导阶段。

这是 DAG 中的**过滤/修剪门控**：它决定哪些分支存活，哪些消亡。

## Job

对 DAG 中的每个 idea，在 3 个维度上执行结构化评估：

1. **新颖性**——这个 idea 以前被探索过吗？它真正原创吗？
2. **可行性**——这个 idea 可以用可用工具和在约束内执行吗？
3. **相关性**——这个 idea 是否实际解决原始问题？

基于评估，每个 idea 收到：
- **PASS** — 进入下一阶段
- **FAIL** — 立即淘汰（记录原因）
- **REVISE** — 返回 idea-discovery 精炼（最多 2 轮）
- **PENDING** — 信息不足，需要人类判断

不可妥协的目标：**最多 1 个 idea 存活到推导阶段。** DAG 收敛到单一路径。

## 3 维评估标准

### 维度 1：新颖性检查

对每个 idea，对照现有文献检查（通过 `/universal-retrieval`）：
1. 搜索与 idea 假设和方法论匹配的先前工作
2. 如果找到匹配论文 → 检查 idea 是否提供清晰差异化
3. 分数：1-10（1 = 已经做过，10 = 完全新颖）

**新颖性判定：**
- 分数 ≥ 7 → `novel`（新颖）
- 分数 4-6 → `partially_novel`（部分新颖）
- 分数 < 4 → `not_novel`（不新颖）

### 维度 2：可行性检查

对每个 idea，评估：
1. **工具可用性**——所需库/方法是否可用？
2. **时间约束**——能否在努力预算内完成？
3. **技能匹配**——可用技能是否覆盖方法论？
4. **风险**——可能出什么问题？

**可行性判定：**
- 全部清晰 → `feasible`（可行）
- 有些担忧 → `risky`（有风险）
- 主要障碍 → `infeasible`（不可行）

### 维度 3：相关性检查

对每个 idea，验证：
1. 是否直接解决原始问题？
2. 是否尊重问题的约束？
3. 输出是否对问题有用？

**相关性判定：**
- 直接匹配 → `relevant`（相关）
- 部分匹配 → `partially_relevant`（部分相关）
- 偏离主题 → `irrelevant`（不相关）

## 综合判定矩阵

| 新颖性 | 可行性 | 相关性 | 综合判定 |
|--------|--------|--------|---------|
| novel | feasible | relevant | **PASS** ✅ |
| novel | risky | relevant | **REVISE**（修复可行性） |
| partially_novel | feasible | relevant | **REVISE**（加强新颖性） |
| not_novel | any | any | **FAIL** ❌ |
| any | infeasible | any | **FAIL** ❌ |
| any | any | irrelevant | **FAIL** ❌ |

## 复合评分

幸存者选择基于加权复合分数：

```
score = novelty × 0.45 + feasibility × 0.25 + relevance × 0.15 + engineering_grounding × 0.15
```

**Engineering Grounding 归一化**: EG score 取自 `IDEA_DAG.json` 中 `engineering_grounding.eg_average`，归一化为 0-1 尺度（除以 10）。如果所有 EG 子维均为 N/A（纯人文学科），EG = 1.0（无惩罚）。

## 配置

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `strictness` | enum | `normal` | `relaxed`（不确定时通过）、`normal`、`strict`（仅清晰新颖时通过） |
| `max_revise_cycles` | int | `2` | idea 可被送回修订的最大次数 |
| `min_survivors` | int | `1` | 必须存活的最少 idea 数（0 = 允许全部淘汰） |
| `require_literature` | bool | `true` | 是否检查文献以确认先前工作 |

## Steps

### Step 1: 从 DAG 加载 Idea

读取 `refine-logs/IDEA_DAG.json`——由 `/idea-discovery` 生成的所有 idea（与 idea-discovery 的 DAG 路径对齐，OSS 统一存放于 `refine-logs/`）。
每个 idea 有：
- `id` — 唯一标识符
- `title` — 简短描述
- `hypothesis` — 核心主张
- `methodology` — 如何推导/验证
- `perspective` — 理论 / 计算 / 定性 / 交叉学科（与 OSS 4-perspective 对齐：theoretical / computational / qualitative / empirical；其中 `empirical` 视角的 idea 以 `verification_type=computational` 推进，aligned with idea-discovery）

### Step 2: 对每个 Idea 运行 4 维评估

对每个 idea，按上述标准执行 4 维评估（新颖性 + 可行性 + 相关性 + 工程落地 EG）。

### Step 3: 计算综合判定

使用判定矩阵确定每个 idea 的综合判定。

### Step 4: 选择幸存者

如果多个 idea 通过：
1. 按复合分数排名（新颖性 × 0.45 + 可行性 × 0.25 + 相关性 × 0.15 + 工程落地 × 0.15）
2. 选择最高分 idea
3. 记录被淘汰的 idea 及其原因
4. 在 `survivor.md` 中**附加** Engineering Grounding 标签（不参与排名但人类可见）

如果没有 idea 通过：
1. 放松 strictness 一级
2. 重新运行评估（最多 1 次放松）
3. 如果仍无幸存者 → 返回 `BLOCKED`（需要人类干预）

### Step 5: 写入 DAG 状态

```json
{
  "dag_id": "dag_20260719",
  "problem_id": "Q001",
  "status": "converged",
  "total_ideas": 3,
  "eliminated": [
    {"id": "idea_1", "reason": "not_novel: matching work found"},
    {"id": "idea_3", "reason": "infeasible: requires unavailable tool"}
  ],
  "survivor": {
    "id": "idea_2",
    "title": "A First-Principles Derivation...",
    "novelty_score": 8,
    "feasibility_score": 7,
    "relevance_score": 9,
    "engineering_grounding_score": 4.2,
    "eg_tier": "CONSTRAINED"
  },
  "next_skill": "theory-derivation"
}
```

## 输出产物

- `refine-logs/novelty_report.json` — 所有 idea 的完整评估（与 idea-discovery 的 DAG 同目录）
- `refine-logs/novelty_{idea_id}.md` — 每个 idea 的详细评估
- `refine-logs/survivor.md` — 被选中的 idea

## 调用下游 skill

- `/theory-derivation` — 幸存者传递给此 skill 进行推导
- `/paper-writing` — 淘汰记录和选择理由纳入论文正文

## 共享契约引用

- [assurance-contract](../../shared-references/assurance-contract.md) — PASS/FAIL/REVISE 判定 schema
- [citation-discipline](../../shared-references/citation-discipline.md) — 新颖性检查的文献验证
- [output-manifest](../../shared-references/output-manifest.md) — 产物结构契约