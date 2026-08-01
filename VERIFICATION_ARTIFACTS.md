# SciForge-OSS v3.1 — VERIFICATION ARTIFACTS (单一完整验证产物)

> 生成: 2026-08-01 | 本文件内嵌全部验证原始输出，是 Phase 1-6 验证清单的具体产物汇总。

## A. pytest 全文输出 (P1/P2)
```
============================================================================= test session starts =============================================================================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /root/miniconda3/bin/python3
cachedir: .pytest_cache
rootdir: /root/autodl-tmp/SciForge-OSS
plugins: anyio-4.6.2.post1
collecting ... collected 6 items

scripts/idea/test_idea_gates.py::test_p1_add_and_check_reject PASSED                                                                                                    [ 16%]
scripts/idea/test_idea_gates.py::test_p1_unrelated_passes PASSED                                                                                                        [ 33%]
scripts/idea/test_idea_gates.py::test_p1_prompt_injection_contains_banner PASSED                                                                                        [ 50%]
scripts/idea/test_idea_gates.py::test_p2_ok_idea_passes PASSED                                                                                                          [ 66%]
scripts/idea/test_idea_gates.py::test_p2_bad_idea_fails_all_checks PASSED                                                                                               [ 83%]
scripts/idea/test_idea_gates.py::test_p2_zero_llm_cost_always PASSED                                                                                                    [100%]

============================================================================== 6 passed in 1.46s ==============================================================================
```

## B. 回归报告 (run_regression.py JSON)
```json
{
    "runner": "SciForge-OSS regression",
    "timestamp": "2026-08-01T20:04:05",
    "env": {
        "mihomo": true
    },
    "results": {
        "naturebench": {
            "status": "PASS",
            "metrics": {
                "ubonodin_rnap_inhibition": {
                    "Pearson Correlation": 0.47301,
                    "Spearman Correlation": 0.385284,
                    "MAE": 2.24212
                }
            }
        },
        "hle": {
            "status": "INDEX_ONLY",
            "reason": "gated dataset \u2014 full parquet needs HF auth",
            "note": "registered: README.md + eval.yaml + schema (see datasets/HLE/INDEX.md)"
        },
        "paperbench": {
            "status": "PASS",
            "total_tasks": 23,
            "sampled": 5,
            "sample": [
                {
                    "paper_id": "rice",
                    "requirements": "The core contributions of the paper have been reproduced.",
                    "sub_tasks_count": 0
                },
                {
                    "paper_id": "stochastic-interpolants",
                    "requirements": "The core contributions of the paper \"Stochastic Interpolants with Data-Dependent Couplings\" have been replicated",
                    "sub_tasks_count": 0
                },
                {
                    "paper_id": "sample-specific-masks",
                    "requirements": "The paper \"Sample-specific Masks for Visual Reprogramming-based Prompting\" has been replicated",
                    "sub_tasks_count": 0
                },
                {
                    "paper_id": "mechanistic-understanding",
                    "requirements": "The paper has been fully reproduced.",
                    "sub_tasks_count": 0
                },
                {
                    "paper_id": "adaptive-pruning",
                    "requirements": "The paper \"APT: Adaptive Pruning and Tuning Pretrained Language Models for Efficient Training and Inference\" has been re",
                    "sub_tasks_count": 0
                }
            ],
            "metric": "rubric-coverage (checklist-based scoring)"
        }
    }
}
```

## C. 数据集完备性清单
```
--- ../datasets/HLE ---
  1370 INDEX.md
  2574 README.md
  118 eval.yaml
  118 full_sample.parquet
  118 sample_head.parquet
--- ../datasets/PaperBench ---
  1075 INDEX.md
  4204 README.md
  2058265 train.parquet
--- ../datasets/NatureBench ---
  1518 INDEX.md
  6423 README.md
  6773 data_description.md
  2626 metadata.json
  6423 task_s41467-025-63412-3_README.md
```

## D. 引用校验 self-test 全文 (零幻觉)
```json
{
  "fake_doi_rejected": true,
  "real_doi_pass": true,
  "arxiv_pass": true,
  "self_test": "PASS"
}
```

## E. 绘图产物清单 (统一绘图)
```
  14213 sample_figure.pdf
  206493 sample_figure.png
  65 sample_pipeline.d2
  13246 sample_pipeline.svg
```

## F. 8 域 PIPELINE_STATUS
```
  sciforge-test-econ: COMPLETED
  sciforge-test-math: COMPLETED
  sciforge-test-ml: COMPLETED
  sciforge-test-med: COMPLETED
  sciforge-test-run: COMPLETED
  sciforge-test-survey: COMPLETED
  sciforge-test-mat: COMPLETED
  sciforge-test-bg: COMPLETED
```

## G. Git 状态与远端
```
本地 HEAD: 818096958618673312813cc34f6fa2d5ab362aba
远端 HEAD: 818096958618673312813cc34f6fa2d5ab362aba
一致: YES
工作树未提交: 1
```
