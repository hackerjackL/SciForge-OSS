---
name: cross-review
type: reference-skill
role: cross-model-reviewer
---

# Support Skill: Cross-Model Adversarial Review

## Use When

当 AI scientist 产生了研究产物（问题分析、理论推导、逻辑验证报告或论文草稿）并需要由独立评审者——最好来自不同模型家族——批判性评审以发现错误、空白和弱点时，使用此 skill。

典型 prompt：
- "评审这个推导"
- "review this paper"
- "critique this argument"
- "cross-check this derivation"
- "act as a peer reviewer for this output"

这是**质量门** skill。它实现了原始 SciForge 的跨模型对抗协作原则：评审者应该是与执行者不同的模型，防止自我强化错误。

## Job

接受研究产物（问题分析、推导、验证报告或论文草稿）并执行结构化同行评审，识别：
1. **优势**——什么做得好
2. **关键错误**——事实错误、逻辑缺陷或遗漏
3. **弱点**——空白、不清晰的推理、支持不足
4. **建议**——具体、可操作的改进
5. **总体评估**——分数和建议

不可妥协的目标：
1. **评审者是对抗性的**——默认立场是怀疑，而非同意
2. **每个批评都是具体的**——指向确切位置并解释原因
3. **每个建议都是可操作的**——"增加更多细节"不可接受；"从边界条件推导方程 5"可以
4. **评审是独立的**——评审者无法访问执行者的推理过程，只能访问输出产物

## 评审维度

每个维度独立评分：

### 1. 技术正确性（权重 3×）
- 事实是否正确？
- 方程是否有效？
- 推导是否严谨？
- 引用是否相关？

### 2. 逻辑结构（权重 2×）
- 论证是否连贯？
- 步骤顺序是否正确？
- 是否有逻辑跳跃？
- 结论是否得到支持？

### 3. 完整性（权重 2×）
- 是否所有必要组件都存在？
- 假设是否已陈述？
- 是否考虑了边界情况？
- 是否承认了局限性？

### 4. 清晰度（权重 1×）
- 写作是否清晰？
- 术语是否定义？
- 图表是否有帮助？
- 叙述是否可访问？

### 5. 新颖性/重要性（权重 1×）
- 工作是否解决有意义的问题？
- 是否有清晰的贡献？
- 工作是否在现有文献背景下定位？

## 配置

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `difficulty` | enum | `hard` | `medium`（标准评审）、`hard`（对抗性）、`nightmare`（极端审查） |
| `reviewer_role` | enum | `general` | `general`、`domain_expert`、`methodologist`、`logician` |
| `score_scale` | int | `10` | 分数范围（1-10 或 1-5） |
| `min_score` | int | `6` | 无需修订的最低通过分数 |
| `max_rounds` | int | `3` | 最大评审-修订循环数 |

## Steps

### Step 1: 接收产物

读取要评审的产物：
1. 识别产物类型（问题分析、推导、验证报告、论文草稿）
2. 识别目标受众（一般科学读者、领域专家）
3. 注意产物自身关于其成就的声明
4. 检查调用者是否提供了任何明确评审标准

### Step 2: 执行初读

完整阅读产物并记录：
1. **第一印象**——整体质量、清晰度、组织
2. **红旗**——任何看起来错误或可疑的内容
3. **缺失部分**——应该存在但不存在的内容
4. **强项**——做得特别好的部分

### Step 3: 详细维度评分

用具体证据对每个维度评分：

**每个维度提供：**
- **分数**——数字分数（1-10）
- **证据**——来自产物的具体引用或位置
- **问题**——存在的问题（含位置）
- **优势**——好的方面（含位置）

### Step 4: 生成评审报告

```markdown
# Review Report: {artifact_id}

## Overall Score: {score}/10
## Recommendation: Accept | Minor Revision | Major Revision | Reject

### Executive Summary
{2-3 句评审摘要}

### Dimension Scores
| Dimension | Score | Weight | Weighted Score |
|-----------|-------|--------|----------------|
| Technical Correctness | X/10 | 3× | X |
| Logical Structure | X/10 | 2× | X |
| Completeness | X/10 | 2× | X |
| Clarity | X/10 | 1× | X |
| Novelty / Significance | X/10 | 1× | X |
| **Total** | | | **X/100** |

### Critical Issues (must fix before acceptance)
1. **{Issue}** (Technical Correctness)
   - Location: {section/paragraph}
   - Problem: {what is wrong}
   - Suggested fix: {how to fix}
   - Severity: high/medium/low

### Minor Issues (should address)
1. **{Issue}** (Clarity)
   - Location: {section/paragraph}
   - Problem: {what could be improved}
   - Suggested fix: {how to fix}

### Strengths
1. {Strength} — {why it's good}

### Reviewer Comments
{free-form commentary, context, and meta-observations}
```

### Step 5: 返回结果

返回评审报告，包含：
- **总体分数**和建议
- **关键问题**——含位置和建议修复
- **小问题**——可改进之处
- **优势**——要保留的
- **修订指导**——如果分数 < min_score，提供具体优先修复指导

## 输出产物

- `reviews/{artifact_id}/review_report.md` — 完整结构化评审
- `reviews/{artifact_id}/review_scorecard.md` — 各维度分数及证据
- `reviews/{artifact_id}/reviewer_notes.md` — 原始评审笔记

## 调用方式

本 skill 通常由 `/125-problems-pipeline` 在 Phase 9 调用：
```
/cross-review "review the paper at output/PAPER.md" — difficulty: hard
```

如果分数不足，管线回退到 Phase 8（论文写作）修复问题，然后重新提交评审。

## 共享契约引用

- [reviewer-independence](../shared-references/reviewer-independence.md) — 评审者独立性规则
- [reviewer-routing](../shared-references/reviewer-routing.md) — 评审者分配规则
- [review-tracing](../shared-references/review-tracing.md) — 评审可追溯性
- [assurance-contract](../shared-references/assurance-contract.md) — 判定 schema