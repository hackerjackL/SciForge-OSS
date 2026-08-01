# FINAL FULL RE-VERIFY (20260801_202344) — 本轮一次性全量复核

## 验证清单 5 项
### 1. Git Status & Cleanliness
uncommitted: 1

### 2. P1/P2 pytest
============================================================================== 6 passed in 1.66s ==============================================================================

### 3. datasets
  HLE: INDEX.md README.md eval.yaml full_sample.parquet sample_head.parquet 
  PaperBench: INDEX.md README.md train.parquet 
  NatureBench: INDEX.md README.md data_description.md metadata.json task_s41467-025-63412-3_README.md ubonodin_run 

### 4. run_regression + 8 域
  naturebench: PASS Pearson=0.47301 Spearman=0.385284 MAE=2.24212
  hle: INDEX_ONLY
  paperbench: PASS
  8 domains:
    sciforge-test-econ: COMPLETED
    sciforge-test-math: COMPLETED
    sciforge-test-ml: COMPLETED
    sciforge-test-med: COMPLETED
    sciforge-test-run: COMPLETED
    sciforge-test-survey: COMPLETED
    sciforge-test-mat: COMPLETED
    sciforge-test-bg: COMPLETED

### 5. citation + plotting
  "self_test": "PASS"
  plotting: sample_figure.pdf sample_figure.png sample_pipeline.d2 sample_pipeline.svg 

## 认证 + 网络
  auth (ag issue list): #2 [release] v3.1 — P1-P6 全量闭环...
  network: mihomo RUNNING

## Git 状态
  本地: 8051857 远端: 8051857 一致
  工作树未提交: 2
