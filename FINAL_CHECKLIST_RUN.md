=== CHECKLIST 1: Git Status & Cleanliness ===
?? FINAL_CHECKLIST_RUN.md
uncommitted_files: 1

=== CHECKLIST 2: P1/P2 原生 pytest ===
collecting ... collected 6 items

scripts/idea/test_idea_gates.py::test_p1_add_and_check_reject PASSED                                                                                                    [ 16%]
scripts/idea/test_idea_gates.py::test_p1_unrelated_passes PASSED                                                                                                        [ 33%]
scripts/idea/test_idea_gates.py::test_p1_prompt_injection_contains_banner PASSED                                                                                        [ 50%]
scripts/idea/test_idea_gates.py::test_p2_ok_idea_passes PASSED                                                                                                          [ 66%]
scripts/idea/test_idea_gates.py::test_p2_bad_idea_fails_all_checks PASSED                                                                                               [ 83%]
scripts/idea/test_idea_gates.py::test_p2_zero_llm_cost_always PASSED                                                                                                    [100%]

============================================================================== 6 passed in 1.61s ==============================================================================

=== CHECKLIST 3: datasets 完备性 ===
--- ../datasets/HLE ---
    INDEX.md
    README.md
    eval.yaml
    full_sample.parquet
    sample_head.parquet
--- ../datasets/PaperBench ---
    INDEX.md
    README.md
    train.parquet
--- ../datasets/NatureBench ---
    INDEX.md
    README.md
    data_description.md
    metadata.json
    task_s41467-025-63412-3_README.md
    ubonodin_run

=== CHECKLIST 4: run_regression.py + 8 域状态 ===
  naturebench: PASS Pearson=0.47301
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

=== CHECKLIST 5: citation_verifier + unified-plotting ===
{
  "fake_doi_rejected": true,
  "real_doi_pass": true,
  "arxiv_pass": true,
  "self_test": "PASS"
}
  plot_out: sample_figure.pdf
  plot_out: sample_figure.png
  plot_out: sample_pipeline.d2
  plot_out: sample_pipeline.svg
