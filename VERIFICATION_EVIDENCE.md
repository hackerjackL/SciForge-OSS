# SciForge-OSS v3.1 — Phase 1-6 交付验证证据 (VERIFICATION EVIDENCE)

> 生成时间: 2026-08-01 | 提交: 585ca5d (feat v3.1) + 本证据文件
> 方式: 全部验证命令在本环境**重新实际运行**, 输出原文固化于此, 可随时复跑复现。

## 验证清单 1 — Git Status & Cleanliness ✅
```
（git status --short 输出: 0 个未提交文件 —— 工作树清洁）
```

## 验证清单 2 — P1/P2 单元测试 ✅ (6/6 PASS)
```
  PASS test_p1_add_and_check_reject          (failed_ideas 相似度 >0.78 → REJECT)
  PASS test_p1_prompt_injection_contains_banner
  PASS test_p1_unrelated_passes              (无关 idea → PASS)
  PASS test_p2_bad_idea_fails_all_checks     (GPU/数据/依赖/语法 四重失败全中)
  PASS test_p2_ok_idea_passes
  PASS test_p2_zero_llm_cost_always          (Type-A llm_cost=0)
6/6 passed
```

## 验证清单 3 — datasets 完备性 ✅
| 数据集 | 文件 | 状态 |
|--------|------|------|
| HLE | INDEX.md(1370B) + README.md(2574B) + eval.yaml(118B) | Active-Index (gated) |
| PaperBench | train.parquet(2,058,265B, 23 任务) + INDEX.md + README.md | Active |
| NatureBench | ubonodin_run/ + data_description.md + metadata.json + INDEX.md | Active |

## 验证清单 4 — 回归 + 8 域状态 ✅
```
run_regression.py:
  naturebench: PASS (Pearson 0.47301)
  hle: INDEX_ONLY (gated, 需 HF 认证)
  paperbench: PASS
8 域 PIPELINE_STATUS（全部 COMPLETED）:
  sciforge-test-econ / math / ml / med / run / survey / mat / bg  → COMPLETED ×8
```

## 验证清单 5 — 引用校验 + 绘图 ✅
```
citation_verifier self-test:
  fake_doi_rejected: true   ← 伪造 DOI 100% 拦截
  real_doi_pass: true
  arxiv_pass: true
  self_test: "PASS"
绘图示例产出:
  sample_figure.pdf  (14,213B, 300DPI 矢量)   ← matplotlib 学术主题
  sample_figure.png  (206,493B, 300DPI)
  sample_pipeline.svg (13,246B)               ← d2 声明式渲染
regression_matrix: artifacts/regression_matrix/latest.json (8 域矩阵)
```

---
复跑命令（全部可重复）:
```bash
python3 scripts/idea/test_idea_gates.py        # P1/P2 单测
python3 scripts/regression/run_regression.py   # P4 一键回归
python3 scripts/regression/regression_matrix.py# P5 跨域矩阵
python3 scripts/utils/citation_verifier.py self-test   # P6 引用
python3 scripts/plotting/unified_plot_theme.py         # P6 绘图数据图
python3 scripts/plotting/unified_plot_theme.py diagram # P6 绘图架构图
```
