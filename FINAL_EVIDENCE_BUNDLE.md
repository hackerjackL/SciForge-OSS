# FINAL EVIDENCE BUNDLE — SciForge-OSS v3.1（紧凑单文件，小体积不截断）

> 生成: 2026-08-01 | 网络/认证实证 + Phase 1-6 五项验证，全部实跑、本文件为单一证据源。

## 1. 网络实证（network_fetcher）
- mihomo_running: True（proxy: http://127.0.0.1:8099）
- huggingface.co: proxy=True ok=True
- modelscope.cn: direct=True proxy=True ok=True
- github.com: direct=True proxy=True ok=True
- api.crossref.org: direct=True proxy=True ok=True
- export.arxiv.org: proxy=True ok=True

## 2. 认证实证（ag CLI）
- `ag pr comment create` PR #12: ✅ Created（#d767fb5e, #f3527b47）
- `ag issue comment create` Issue #2: ✅ Created（#182803514）
- `ag pr edit` PR #12 body: ✅ Updated
- `git push`（普通）: ✅ 0 噪音（credential helper 已根治）

## 3. 验证清单（5 项实跑）
- [PASS] git-cleanliness: 工作树 0 未提交
- [PASS] p1-p2-unit-tests: pytest 6 passed in 1.46s
- [PASS] datasets: HLE(INDEX/README/eval.yaml) + PaperBench(train.parquet 23tasks/INDEX) + NatureBench(INDEX/ubonodin_run/描述/元数据)
- [PASS] regression-and-domains: naturebench PASS (Pearson 0.47301 / Spearman 0.385284 / MAE 2.24212) + paperbench PASS + 8/8 域 COMPLETED
- [PASS] citations-and-plotting: citation self-test PASS (fake_doi_rejected=true) + sample_figure.pdf/png + sample_pipeline.svg

## 4. Git 状态
- 提交链: 585ca5d → … → 2e35ac5
- 本地 HEAD = 远端 HEAD（一致）

## 5. 交付物（存在）
network_fetcher / failed_ideas_memory / type_a_gate / test_idea_gates / run_regression / regression_matrix / naturebench_ubonodin_baseline / dry_run_runner / citation_verifier / discipline_adapter / unified_plot_theme / verify_all
