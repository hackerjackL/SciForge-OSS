# FINAL EVIDENCE COMPLETE (20260801_201610) — 一次实跑全部验证原始输出

## 1. 网络 (network_fetcher)
  "mihomo_running": true,

## 2. 认证探针 (ag CLI)
#2 [release] v3.1 — P1-P6 全量闭环（网络自举/反重复记忆/Type-A门/基准接入/回归/早停/引用/Adapter/绘图） [open]
PR12 state: merged

## 3. pytest (P1/P2)
scripts/idea/test_idea_gates.py::test_p1_add_and_check_reject PASSED                                                                                                    [ 16%]
scripts/idea/test_idea_gates.py::test_p1_unrelated_passes PASSED                                                                                                        [ 33%]
scripts/idea/test_idea_gates.py::test_p1_prompt_injection_contains_banner PASSED                                                                                        [ 50%]
scripts/idea/test_idea_gates.py::test_p2_ok_idea_passes PASSED                                                                                                          [ 66%]
scripts/idea/test_idea_gates.py::test_p2_bad_idea_fails_all_checks PASSED                                                                                               [ 83%]
scripts/idea/test_idea_gates.py::test_p2_zero_llm_cost_always PASSED                                                                                                    [100%]
============================================================================== 6 passed in 1.47s ==============================================================================

## 4. 回归 (P4) + 8 域
  naturebench: PASS Pearson=0.47301 Spearman=0.385284 MAE=2.24212
  hle: INDEX_ONLY
  paperbench: PASS
  sciforge-test-econ: COMPLETED
  sciforge-test-math: COMPLETED
  sciforge-test-ml: COMPLETED
  sciforge-test-med: COMPLETED
  sciforge-test-run: COMPLETED
  sciforge-test-survey: COMPLETED
  sciforge-test-mat: COMPLETED
  sciforge-test-bg: COMPLETED

## 5. 数据集 (P3)
HLE: INDEX.md README.md eval.yaml full_sample.parquet sample_head.parquet 
PaperBench: INDEX.md README.md train.parquet 
NatureBench: INDEX.md README.md data_description.md metadata.json task_s41467-025-63412-3_README.md ubonodin_run 

## 6. 引用 (P6)
{
  "fake_doi_rejected": true,
  "real_doi_pass": true,
  "arxiv_pass": true,
  "self_test": "PASS"
}

## 7. 绘图 (P6)
sample_figure.pdf sample_figure.png sample_pipeline.d2 sample_pipeline.svg 

## 8. Git 状态
未提交: 2
本地: e4eda0b 远端: e4eda0b 一致
