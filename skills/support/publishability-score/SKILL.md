---
name: publishability-score
description: "Final publishability scoring across dim1-first-axis + multi-dim. Phase 15.5. Invoke after citation-audit for the go/no-go submission verdict."
type: support-skill
role: paper-publishability-assessor
version: 1.1.2
---
> **v5.2 评判产物位置**：本 skill 产出的机读 verdict/hash/审计 JSON 一律写入 `verdicts/`（文件名见 [`output-protocol.md`](../../shared-references/output-protocol.md) 产物目录结构；叙述性报告留在原 stage 目录）。


# Publishability Score (SciForge-OSS — Final Paper Quality Assessment)

> **Status (v2.2)**: New support skill. The final paper-quality gate after Phase 14 (auto-review-loop) and Phase 15 (citation-audit). Produces a structured **publishability score** that tells the human whether the paper is (a) submission-ready, (b) "missing only some experiments" (the user's target — main experiments are in place, only cross/supplementary experiments needed), or (c) fundamentally flawed (main experiment logic NOT in place — supplementary experiments won't save it, "no mean").
>
> **Core principle (user mandate)**: "我们跑出来的这些 PDF，跑出来这些 latex，也是需要最后有一个单独评分，因为我们要至少验证我们的论文是，例如可能只是差某些实验就可以去发表的。但是我说的差这些某些实验是它的主实验非常的到位。如果说它的实验逻辑不到位，那么他就算补充那些交叉实验或者是补充实验，它也没有任何意义。我们不要做任何 no mean 的事情。" → The score's **primary axis is "main-experiment-logic-in-place"**. If that fails, the paper is NOT publishable regardless of how many supplementary experiments could be added. Only when main-experiment-logic passes does the "missing-supplementary-experiments" verdict make sense.

## Quick Reference

- **Purpose**: 给最终论文打一个结构化可发表性评分（publishability score）
- **Input**: `paper/main.pdf` + `paper/main.tex` + `experiments/` + `audit_report/` + `review/` + `CLAIMS_FROM_RESULTS.md` + `PIPELINE_STATUS.json`
- **Output**: `PUBLISHABILITY_SCORE.json` + `PUBLISHABILITY_SCORE.md` (human-readable)
- **Key**: 6-维评分；**主实验逻辑到位**是首要轴；区分"差补充实验" vs "主逻辑不到位(no mean)"

## Use When

Phase 16 (最终组装) 完成后、或人类想评估一篇已完成论文的可发表性时调用。

典型 prompt：
- "给这篇论文打分" / "score this paper"
- "这篇论文能发表吗？" / "is this publishable?"
- "评估可发表性" / "assess publishability"
- "还差什么实验？" / "what experiments are missing?"

## Job

读入论文 + 所有实验产物 + 审计报告，输出一个结构化的可发表性评分，明确告诉人类：
1. 这篇论文当前是否可发表（submission-ready）
2. 如果不可发表，是"只差补充实验"（主实验到位，补充即可）还是"主实验逻辑不到位"（补充再多也没用 = no mean）
3. 具体缺什么（如果是"只差补充实验"，列出缺失的补充/交叉实验清单）

不可妥协的目标：
1. **主实验逻辑到位是首要轴**——如果主实验逻辑 FAIL，总分上限 0.4（无论其他维度多好），且 verdict = NOT_PUBLISHABLE_NO_MEAN（不是"差实验"，是"逻辑不到位"）
2. **评分必须诚实**——不为了好看而虚高；一个主实验逻辑不到位的论文不能因为写作好就 PASS
3. **区分两类不可发表**——"差补充实验"(SUPPLEMENTARY_GAPS) vs "主逻辑不到位"(MAIN_LOGIC_FAILURE)，两者对人类的下一步行动完全不同
4. **评分可追溯**——每个维度分数附 1-2 句理由 + 证据文件路径

## The 6-Dimension Score

| 维度 | 权重 | 满分 | 评什么 | FAIL 条件（该维 0 分） |
|------|------|------|--------|----------------------|
| **1. 主实验逻辑到位 (Main-Experiment-Logic-in-Place)** | **首要轴** | 1.0 | 主实验是否回答了论文的核心 claim？实验设计是否与 claim 逻辑闭合？主结果是否支撑核心结论？ | 主实验缺失 / 主实验设计与 claim 无关 / 主结果与核心结论矛盾 |
| 2. 理论严谨性 (Theoretical Rigor) | 0.15 | 1.0 | 推导是否正确？符号/机器验证是否通过？假设是否 stated？ | 推导有致命错误 / 未机器验证且 claim 声称机器验证 |
| 3. 实证完整性 (Empirical Completeness) | 0.20 | 1.0 | 主实验 + 消融 + 鲁棒性 + 基线对比是否齐全？是否有 SOTA 对比？ | 无消融 / 无基线 / 无鲁棒性（但主逻辑在 → 这是 SUPPLEMENTARY_GAPS 不是 MAIN_LOGIC_FAILURE） |
| 4. 写作质量 (Writing Quality) | 0.15 | 1.0 | 结构清晰？claim 有支撑？引用真实？图表明晰？零编译警告？ | 编译有警告未修 / 引用未验证 / 图不可读 |
| 5. 新颖性与贡献 (Novelty & Contribution) | 0.15 | 1.0 | 相对已有文献是否有新贡献？novelty-check 是否 PASS？是否避免重复工作？ | 与已有工作重复 / novelty-check FAIL |
| 6. 可复现性 (Reproducibility) | 0.15 | 1.0 | 代码/数据/seed/硬件是否保留？实验可重跑？图有 render 脚本？ | 无 render 脚本 / 无 seed / 无法重跑 |

**权重说明**：维度 1 是首要轴（不计入 0.15 平均，而是 gating）；维度 2-6 各 0.15，合计 0.75；剩 0.25 由维度 1 调节。公式：
```
total = 0.25 * dim1 + 0.15*(dim2+dim3+dim4+dim5+dim6)   # 若 dim1=0 则 total ≤ 0.25*0 + 0.75 = 0.75，但见下 hard cap
hard_cap_if_main_logic_fail: if dim1 == 0 → total capped at 0.4 (NOT_PUBLISHABLE_NO_MEAN), regardless of dim2-6
```

## Verdict Tiers

| Verdict | total 范围 | dim1 | 含义 | 人类下一步 |
|---------|-----------|------|------|-----------|
| **SUBMISSION_READY** | ≥ 0.80 | ≥ 0.8 | 主实验逻辑到位 + 各维度均强 | 可投稿（按 venue-profiles 适配后） |
| **SUPPLEMENTARY_GAPS** | 0.55–0.79 | ≥ 0.7 | 主实验逻辑到位，但差一些补充/交叉实验（维度 3 < 0.8） | 按缺失清单补实验即可发表 |
| **NEEDS_MAJOR_REVISION** | 0.40–0.54 | ≥ 0.5 | 主实验逻辑基本在但需大改（设计/基线/消融） | 大改主实验后重评 |
| **NOT_PUBLISHABLE_NO_MEAN** | ≤ 0.40 | < 0.5 | **主实验逻辑不到位**——补充实验无意义 | 不要补实验；重新想 idea/实验设计 |

**关键区分**：`SUPPLEMENTARY_GAPS`（可发表，差补充）与 `NOT_PUBLISHABLE_NO_MEAN`（不可发表，主逻辑不到位）对人类的下一步完全不同。前者"补 X 个实验即可"，后者"补再多实验也没用，重新设计"。这正是用户强调的"不要做 no mean 的事情"。

## Workflow

### Step 1: Load All Artifacts

读入：
- `paper/main.pdf` + `paper/main.tex` + `paper/sections/*.tex`（论文本身）
- `paper/COMPILE_REPORT.json`（编译状态，零警告？）
- `experiments/toy/RESULT.json` + `experiments/full/STATUS.json` + `experiments/full/EXPERIMENT_RESULTS.json`（实验结果）
- `CLAIMS_FROM_RESULTS.md`（claim 门控，仓库根）
- `audit_report/LOGIC_VERIFICATION.json` + `audit_report/LEAKAGE_AUDIT.json`（逻辑/泄漏审计）
- `review-stage/REVIEW_REPORT.md` + `review-stage/KILL_ARGUMENT.md`（Phase 14 评审）
- `literature/FILTER_CHAIN_AUDIT.json`（文献链）
- `refine-logs/FINAL_PROPOSAL.md`（核心 claim 冻结）
- `PIPELINE_STATUS.json`（pipeline 状态）

### Step 2: Score Dimension 1 (Main-Experiment-Logic) — GATING

这是首要轴，必须先评。回答 4 个子问题（每个 yes=0.25）：
1. **主实验存在？** — `experiments/` 有 toy PASS + full completed？(`theory-only` 路径：推导是"主实验"，评估推导是否回答 claim)
2. **主实验设计回答核心 claim？** — 实验的 success_criteria 与 `FINAL_PROPOSAL.md` 的核心 claim 一致？不是测了一个无关的指标？
3. **主结果支撑核心结论？** — `RESULT.json`/`EXPERIMENT_RESULTS.json` 的数据方向 + 显著性与论文核心结论一致？（toy PASS + full 一致 = 强支撑；toy PASS + full 不一致 = 弱支撑）
4. **实验逻辑闭合（claim→设计→结果→结论无跳跃）？** — `CLAIMS_FROM_RESULTS.md` 的每个 claim 都有实验证据 + `LOGIC_VERIFICATION.json` 无 FATAL/CRITICAL？

dim1 = sum(yes) * 0.25。**若 dim1 < 0.5 → 直接 verdict = NOT_PUBLISHABLE_NO_MEAN，跳到 Step 4（不评 dim2-6 的细节也行，因 hard cap）。**

### Step 3: Score Dimensions 2-6

- **dim2 理论严谨性**：`derivation_output.md` 机器验证 PASS? `verification_report.md`? 假设 `premises.md` stated? → 0/0.5/1.0
- **dim3 实证完整性**：主实验 ✓ + 消融? + 鲁棒性? + 基线对比? + SOTA? （每缺一项 -0.2，min 0）→ 注意：dim3 低但 dim1 高 = SUPPLEMENTARY_GAPS
- **dim4 写作质量**：`COMPILE_REPORT.json` 零警告? 引用全验证 (`FILTER_CHAIN_AUDIT.json` PASS)? 图可读 (Nature floor)? 结构清晰? → 各 0.25
- **dim5 新颖性**：`novelty_report.json` PASS? `KILL_ARGUMENT.md` 未被 killed? 相对 `landscape_report.md` 有新贡献? → 0/0.5/1.0
- **dim6 可复现性**：`render.py`/`spec.d2` 保留? seed stated? `input_data.json` 保留? full 实验可重跑? → 各 0.25

### Step 4: Compute Total + Verdict

```
total = 0.25*dim1 + 0.15*(dim2+dim3+dim4+dim5+dim6)
if dim1 < 0.5: total = min(total, 0.4); verdict = NOT_PUBLISHABLE_NO_MEAN
elif dim3 < 0.8 and dim1 >= 0.7 and total < 0.8: verdict = SUPPLEMENTARY_GAPS
elif total >= 0.80: verdict = SUBMISSION_READY
elif total >= 0.55: verdict = SUPPLEMENTARY_GAPS  (main logic OK, some gaps)
elif total >= 0.40: verdict = NEEDS_MAJOR_REVISION
else: verdict = NOT_PUBLISHABLE_NO_MEAN
```

### Step 5: Missing-Experiments Manifest (if SUPPLEMENTARY_GAPS)

若 verdict = SUPPLEMENTARY_GAPS，列出缺失的补充/交叉实验清单（对人类最有用的输出）：
- **消融实验**（若 dim3 缺消融）：移除 X 组件，验证 Y 下降
- **鲁棒性实验**（若缺）：不同 seed/config/数据子集
- **基线对比**（若缺）：对比 [具体 baseline] from `landscape_report.md`
- **SOTA 对比**（若缺）：对比 [具体 SOTA]
- **交叉实验**（若适用）：跨领域/跨数据集验证泛化
- **统计显著性**（若缺）：更多 seed + 置信区间

每项标 `priority: high|medium|low` + `estimated_effort: hours`。这是人类的 actionable 清单。

### Step 6: Output

写 `PUBLISHABILITY_SCORE.json` + `PUBLISHABILITY_SCORE.md`（人类可读）。附在 `output/` 下。

## Output Schema (`PUBLISHABILITY_SCORE.json`)

```json
{
  "q_id": "...",
  "scored_at": "ISO-8601",
  "verdict": "SUBMISSION_READY | SUPPLEMENTARY_GAPS | NEEDS_MAJOR_REVISION | NOT_PUBLISHABLE_NO_MEAN",
  "total_score": 0.72,
  "dimensions": {
    "main_experiment_logic": {"score": 1.0, "rationale": "...", "evidence": ["experiments/full/EXPERIMENT_RESULTS.json", "CLAIMS_FROM_RESULTS.md"]},
    "theoretical_rigor": {"score": 0.9, "rationale": "...", "evidence": ["derivations/.../verification_report.md"]},
    "empirical_completeness": {"score": 0.4, "rationale": "主实验✓ 消融✗ 鲁棒性✗ 基线✗", "evidence": ["experiments/"]},
    "writing_quality": {"score": 0.9, "rationale": "零警告✓ 引用✓", "evidence": ["paper/COMPILE_REPORT.json"]},
    "novelty_contribution": {"score": 0.8, "rationale": "...", "evidence": ["refine-logs/novelty_report.json"]},
    "reproducibility": {"score": 0.9, "rationale": "render.py✓ seed42✓", "evidence": ["figures/"]}
  },
  "main_logic_gating": {"dim1_score": 1.0, "gating_triggered": false, "cap_applied": null},
  "missing_experiments": [
    {"type": "ablation", "description": "移除 label-smoothing 项，验证 val-loss 上升", "priority": "high", "estimated_effort_hours": 4},
    {"type": "baseline", "description": "对比 standard CE baseline (已部分)", "priority": "high", "estimated_effort_hours": 2},
    {"type": "robustness", "description": "5 seeds + CI", "priority": "medium", "estimated_effort_hours": 6}
  ],
  "human_next_action": "补 3 项补充实验（共约 12 小时）后可投稿；主实验逻辑已到位",
  "benchmark_ready": false,
  "notes": "..."
}
```

## Boundaries

- **主实验逻辑到位是首要轴（hard cap）**。dim1 < 0.5 → 总分硬上限 0.4 + verdict = NOT_PUBLISHABLE_NO_MEAN。不因写作好/引用全而抬高。
- **诚实评分**。不为了"好看"虚高。一个主实验逻辑不到位的论文，写作再好也是 no mean。
- **区分 verdict**。SUPPLEMENTARY_GAPS（差补充，可发表）vs NOT_PUBLISHABLE_NO_MEAN（主逻辑不到位，补实验无意义）——这是对人类最有用的区分。
- **缺失实验清单 actionable**。每项有 type/description/priority/effort，人类可直接执行。
- **不替代 Phase 14 auto-review-loop**。本 skill 是 Phase 14 之后的最终评分，消费 Phase 14 的 `REVIEW_REPORT.md` 作为 dim4/dim5 的输入。
- **benchmark-ready flag**。用户后期要打榜 benchmark——`benchmark_ready: true` 仅当 verdict = SUBMISSION_READY 且 dim1=1.0 且 dim3≥0.8。

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../../orchestrator/auto-pipeline/SKILL.md) — Phase 16 调用本 skill
- [`../auto-review-loop/SKILL.md`](../auto-review-loop/SKILL.md) — Phase 14，本 skill 消费其输出
- [`../citation-audit/SKILL.md`](../citation-audit/SKILL.md) — Phase 15，本 skill 消费其输出
- [`../../shared-references/project-architecture-contract.md`](../../shared-references/project-architecture-contract.md) — `output/` 目录结构
