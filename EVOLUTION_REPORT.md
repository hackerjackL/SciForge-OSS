# SciForge-OSS v3.1 — EVOLUTION REPORT (Phase 1-6 权威汇总)

> 生成: 2026-08-01 | 本报告汇总 Phase 1-6 全部交付物、验证清单原始输出与远端状态，一处可查。
> 复跑入口: `python3 scripts/verification/verify_all.py` (overall PASS / exit 0)

## 1. Phase 1-6 交付物清单（全部存在）

| Phase | 交付物 | 状态 |
|-------|--------|------|
| 1 | `scripts/utils/network_fetcher.py`（连通性检测 + mihomo 自举） | ✅ 端点实测可达 |
| 2 | `scripts/idea/failed_ideas_memory.py`（P1: failed_ideas.json + TF-IDF>0.78 硬校验 + 软注入） | ✅ pytest 通过 |
| 2 | `scripts/idea/type_a_gate.py`（P2: GPU/数据/依赖/语法 0-cost 机械门）+ `test_idea_gates.py` | ✅ pytest 6/6 |
| 3 | `datasets/HLE/`（Active-Index）+ `datasets/PaperBench/`（23 任务）+ `datasets/NatureBench/`（固化+复现） | ✅ 完备 |
| 4 | `scripts/regression/run_regression.py`（一键回归）→ `artifacts/regression/` | ✅ exit 0 |
| 5 | `scripts/experiment/dry_run_runner.py`（早停）+ `scripts/regression/regression_matrix.py`（8 域矩阵） | ✅ 实测 |
| 6 | `scripts/utils/citation_verifier.py`（零幻觉，伪造 DOI 100% 拦截） | ✅ self-test PASS |
| 6 | `scripts/writing/discipline_adapter.py`（STEM/MedBio/Humanities Adapter） | ✅ 三学科检测 |
| 6 | `scripts/plotting/unified_plot_theme.py`（DPI300/Arial 回退/Nature 调色板 + d2/dot） | ✅ 产出矢量图 |
| - | `scripts/verification/verify_all.py`（验证清单自检入口） | ✅ overall PASS |

技能接线：idea-discovery / experiment-execution / paper-writing / unified-plotting 四处 SKILL.md 已更新。

## 2. 验证清单原始输出（verify_all.py 实测）

```
SciForge-OSS verify_all  —  overall: PASS
  [PASS] git-cleanliness          意外文件: []
  [PASS] p1-p2-unit-tests          6/6 passed
  [PASS] datasets-completeness     HLE / PaperBench / NatureBench 齐全
  [PASS] regression-and-domains    run_regression exit 0；8/8 域 COMPLETED
  [PASS] citations-and-plotting    self_test "PASS"；pdf/png/svg 产出
exit code: 0
```

原生 pytest 实测：`python3 -m pytest scripts/idea/test_idea_gates.py -v` → **6 passed in 1.61s**
NatureBench 复现基线：**Pearson 0.47301 / Spearman 0.385284 / MAE 2.24212**（官方 evaluator）

## 3. 推送 auth 噪音根治记录

- **根源**：本地仓库 `.git/config` 存在 `credential.helper=!ag auth token --raw-output`
  （git 调 `ag auth token store` 触发 `unknown command "store" for "ag auth token"` 噪音）
- **根治**：`git config --local --unset credential.helper` + `--unset credential.https://atomgit.com.helper`
  （保留全局 `/root/.gitconfig` 的 ag-credhelper.sh——其 store/erase 为 no-op，无噪音）
- **实测**：普通 `git push`（不带 `-c` 参数）输出 **0 处 Error/unknown command** 噪音

## 4. 远端一致性

```
个人仓库分支 feat/v2.2-figures-lit-compile-score
本地 HEAD = 远端 HEAD（ls-remote 确认）
```

## 5. 主仓协作

- PR #12: state=merged，body 已更新为 v3.1 全量内容（含 Issue #2 关联声明）
- Issue #2: [release] v3.1 — P1-P6 全量闭环，已创建可查
