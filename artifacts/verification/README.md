# Verification Evidence (SciForge-OSS v3.1)

> 本目录为 Phase 1-6 交付的**可复跑验证证据**。每次运行 `verify_all.py` 会生成时间戳 JSON
> （`verify_<YYYYMMDD_HHMMSS>.json`）并更新 `latest.json`。

## 如何复跑

```bash
cd SciForge-OSS
python3 scripts/verification/verify_all.py
echo $?   # 0 = 全部通过（overall PASS）
```

## 验证清单 ↔ 检查项映射

| 清单项 | verify_all 检查 | 通过条件 |
|--------|----------------|----------|
| 1. Git Status & Cleanliness | `git-cleanliness` | 无意外未提交文件（artifacts/scripts/datasets 内的固化产物除外） |
| 2. P1/P2 单元测试 | `p1-p2-unit-tests` | `test_idea_gates.py` 退出码 0（6/6） |
| 3. datasets 完备性 | `datasets-completeness` | HLE(README/eval.yaml/INDEX) + PaperBench(train.parquet/INDEX) + NatureBench(INDEX/ubonodin_run) 全部存在 |
| 4. 回归 + 8 域状态 | `regression-and-domains` | `run_regression.py` 退出码 0 且 8/8 域 PIPELINE_STATUS = COMPLETED |
| 5. 引用 + 绘图 | `citations-and-plotting` | citation_verifier self-test PASS（伪造 DOI 100% 拦截）+ 绘图示例 pdf/png/svg 产出 |

## 历史运行记录

| 时间戳 | overall | 说明 |
|--------|---------|------|
| 20260801_194226 | FAIL | 初版 verify_all 自检（bug：输出截断 + git 误判），已修复 |
| 20260801_194307 | PASS | 修复后首过 |
| 20260801_194452 | PASS | 复跑确认 |
| 20260801_194703 | PASS | 最终复跑确认 |

> 说明：194226 的 FAIL 是 verify_all 自身两处 bug（`_run` 截断输出致关键词漏检、git 检查把 artifacts 固化产物误判为意外文件），修复后 194307 起持续 PASS——交付物本身自始通过，FAIL 仅反映验证器 bug。
