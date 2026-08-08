# Output Protocol (SciForge-OSS — Merged)

> **核心**: 每次输出写两个版本——时间戳版（历史） + 固定名版（最新）。

## 版本化写入

1. 写入时间戳文件：`{FILENAME}_{YYYYMMDD_HHmmss}.md`
2. 复制到固定名文件：`{FILENAME}.md`（覆盖最新版）
3. 下游 skill 始终读固定名文件

**需要时间戳的**：IDEA_REPORT.md, FINAL_PROPOSAL.md, AUTO_REVIEW.md, paper/main.tex, 状态文件
**不需要时间戳的**：append-only 文件 (findings.md)、按轮次编号的文件 (round_N_*.md)、MANIFEST.md

## Manifest 记录

每次写入后，在 `MANIFEST.md` 追加一行：

```markdown
| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
| 2026-07-20 14:30 | /idea-discovery | refine-logs/IDEA_CANDIDATES.md | idea-discovery | 12 ideas generated |
```

## 产物目录结构（v5.2 — verdicts/ 评判统一 + logs/ 集中 + code/ 单一之家）

```
{problem_id}/
├── refine-logs/        ← idea-discovery + novelty-check 产物（决策类文档）
├── literature/         ← universal-retrieval 产物
├── methods/            ← method-registry 产物（METHOD_REGISTRY.md/METHOD_BINDING.md）
├── derivations/        ← theory-derivation 产物（仅 .md 文档；脚本归 code/）
├── code/               ← 算法与源代码的【单一之家】（v5.0）
│   ├── derivations/    ←   推导/符号验证脚本（原 derivations/*.py 迁入）
│   ├── experiments/    ←   实验脚本（toy/full/消融/超参，含 group_<name>/）
│   ├── figures/        ←   渲染脚本（render.py / spec.d2 / *.composite.json）
│   └── utils/          ←   共享工具函数
├── verdicts/           ← 全流程评判产物的【统一目录】（v5.2 新增）
│   ├── VERIFICATION_ROUTING.json   ← 验证路由判定（Phase 6 入口）
│   ├── PROBLEM_HASH.txt            ← INV-G1 问题内容哈希（invariant-check）
│   ├── REGISTRY_HASH.txt           ← 方法 hash-lock（method-registry）
│   ├── EXPERIMENT_MATRIX.json      ← 强制实验矩阵（method-registry §3.5）
│   ├── BUDGET_FLOOR.json           ← 探索预算下限完成判据（experiment-execution）
│   ├── PROOF_AUDIT.json            ← 推导逐步验证（theory-derivation）
│   ├── LOGIC_VERIFICATION.json     ← 6 维逻辑审计（logic-verification）
│   ├── LEAKAGE_AUDIT.json          ← Type I/IV 审计（leakage-audit）
│   ├── BLINDSPOT_CHECK.json        ← 领域盲区审计（auto-review-loop B.2）
│   ├── REVIEW_STATE.json           ← 评审轮次状态 + response_class（auto-review-loop）
│   ├── REVIEW_LEDGER.json          ← 评审意见台账（auto-review-loop）
│   ├── KILL_ARGUMENT.json          ← 杀论证（kill-argument）
│   ├── PAPER_CLAIM_AUDIT.json      ← 论文-claim 一致性（paper-writing 自检）
│   ├── LEAKAGE_SCRUB.json          ← LaTeX 泄漏清洗门（paper-writing §3.5）
│   ├── CITATION_AUDIT.json         ← 3 层引用核验（citation-audit）
│   └── PUBLISHABILITY_SCORE.json   ← 发表性终评（publishability-score）
├── logs/               ← 全流程日志的【集中目录】（v5.0）
│   ├── pipeline.log    ←   auto-pipeline 状态流水（唯一权威状态记录）
│   ├── phase_<n>.log   ←   各阶段运行日志（各 skill 写入，不再散落）
│   └── experiments/    ←   实验 STATUS.json 汇总镜像
├── audit_report/       ← logic-verification + leakage-audit 的【叙述性报告】（.md；机读 verdict 归 verdicts/）
├── figures/            ← unified-plotting 产物（PDF+SVG 交付 + figure_audit.json 随图；汇总 verdict 镜像 verdicts/FIGURE_AUDITS.json）
├── experiments/        ← experiment-execution 产物（RESULT.json/数据；脚本归 code/experiments/）
├── paper/              ← paper-writing + paper-compile 产物（编译产物与 .tex；评判归 verdicts/）
├── review-stage/       ← auto-review-loop 的【叙述性产物】（AUTO_REVIEW.md；机读 verdict 归 verdicts/）
├── citation_audit/     ← citation-audit 的【叙述性报告】（机读 verdict 归 verdicts/）
└── output/             ← 最终归档（submission bundle）
```

**评判统一原则（v5.2 — 治"评判文件散落难追溯"）**:
1. **机读评判一律归 `verdicts/`**：所有 `*.json` verdict / hash / 审计结论写 `verdicts/`（文件名固定如上表，不加阶段前缀、不嵌套子目录——一个平铺目录扫一遍即知全管线评判状态）
2. **叙述性报告留在原 stage 目录**：人读的长报告（AUTO_REVIEW.md、audit 叙述、citation 报告）不动；只有机读 verdict 迁移
3. **单一状态文件**：`PIPELINE_STATUS.json` 只存在于 `logs/`（事件流水），各阶段不得自建 PIPELINE_STATUS 副本；orchestrator 汇总时读 `verdicts/` 全目录生成管线评判总览（`verdicts/PIPELINE_VERDICT_SUMMARY.md`，每次 phase boundary 重写）
4. 迁移兼容：读取先查 `verdicts/`，未找到回退旧 stage 路径；写入一律 `verdicts/`

**单一之家原则（v5.0 — 治"目录混乱 + 代码重复"）**:
1. 每类产物有**唯一规范路径**（上表）；写入其他位置的同类产物 → 审计 WARN，写入方负责迁移
2. **代码只在 `code/` 一处存在**：实验/推导/渲染脚本一律归 `code/` 对应子目录；`derivations/`、`figures/`、`experiments/` 只放**产物与文档**（.md/.json/PDF/SVG/数据），**绝不放脚本**——这消灭了"论文写作时代码被复制进 paper/ 一遍"的重复现象（paper/ 内无代码副本，代码引用只走 Reproducibility 声明指向 `code/`）
3. **日志只在 `logs/` 集中**：各阶段不再各自建日志文件散落根目录；`pipeline.log` 是唯一权威状态流水（含 PIPELINE_STATUS 事件），各 skill 的过程日志写 `logs/phase_<n>.log`
4. 迁移兼容：读取时先查新规范路径，未找到回退旧路径（向后兼容旧运行目录）；写入一律新路径

## 路径回退规则

读取时先查找 stage-scoped 路径，未找到则回退到根级路径（向后兼容）。写入始终使用 stage-scoped 路径。

## 工作区整洁契约（v5.2 — Workspace Hygiene，治"工作区混乱/重复/垃圾文件"）

**命名规范（全管线强制）**:
1. **文件名全大写 + 下划线**（`CLAIMS_FROM_RESULTS.md`、`REGISTRY_HASH.txt`）用于**契约性产物**（被下游 skill 按固定名读取的）；**小写 + 连字符**（`derivation_output.md` 类叙述产物）用于阶段内部产物——一眼区分"契约文件"与"过程文件"
2. **版本号只进内容不进文件名**：禁止 `report_v2.md`、`final_FINAL.tex`、`draft3.py`——迭代用版本化写入（本节上方）与 `revision_log.md`，文件名保持稳定（下游按固定名引用，改名即断链）
3. **实验目录**：`experiments/full/group_<name>/`（name = 实验矩阵的组名）；**禁止** `exp1/`、`test2/`、`new_folder/` 这类无语义命名
4. **一图一文件夹**：`figures/<fig_id>/`（fig_id 与 LaTeX label 一致）——图产物不与其他产物混放

**临时文件禁令（硬规则）**:
1. 工作区根目录**只允许**目录树定义的 15 个目录 + `refine-logs/` 入口文件；任何散落的 `.py`/`.tmp`/`.bak`/`.swp`/`nohup.out`/`core.*`/`*.orig`/`__pycache__/` → 收尾清理协议删除或迁移
2. **临时文件只进 `/tmp` 或 `logs/tmp/`**：调试脚本、渲染中间产物、下载缓存一律写 `/tmp`（管线外）或 `logs/tmp/`（收尾时整目录删除）；**绝不**写工作区根目录或 stage 目录
3. 实验数据集（下载的原始数据）放 `experiments/data/<dataset_id>/`，不进 `code/`、不进工作区根
4. `nohup.out` / 后台进程输出一律重定向到 `logs/experiments/<experiment_id>.log`（experiment-execution dispatch 命令模板强制 tee 到该路径）

**孤儿产物治理**:
1. **孤儿 = 无上游引用的产物**：每个阶段产物必须被至少一个下游契约引用（MANIFEST 的 `consumer` 字段）；MANIFEST 写入时 consumer 为空 → WARN `orphan_artifact`
2. **被否决分支的产物**：KILL/PIVOT 后，被否决 idea 的产物**不删除**（审计追溯需要），统一移入 `refine-logs/abandoned/<idea_id>/` 归档——保持活跃工作区只有当前 idea 的产物，历史可查不碍眼
3. **重复产物零容忍**：同一内容出现在两个路径（如代码在 `code/` 又在 `paper/`）→ 审计 FAIL `duplicate_artifact`；symlink 是唯一合法的"同一产物多处可见"机制

**收尾清理协议（每个 phase boundary + 管线终态执行）**:
1. 扫描工作区：删除 `logs/tmp/`、空目录、`*.pyc`/`__pycache__/`、0 字节文件（保留有契约引用的）
2. 核对 MANIFEST：活跃产物全部在规范路径、全部有 consumer；违规项迁移/告警（不静默删除有内容文件）
3. 写 `logs/pipeline.log` 一条清理事件（删了什么、迁了什么）——清理动作本身可审计
4. 管线终态（Phase 17 归档）：`output/` submission bundle 只含交付物（paper PDF + LaTeX 源 + figures PDF/SVG + 引用 bib），**不含**中间产物——打包前逐文件核对清单

## 过期状态检测

状态文件 (REVIEW_STATE.json 等) 的默认过期阈值：24 小时。过期时警告用户，可继续或重新开始。

## 输出语言 (Output Language)

尊重项目的语言设置（`language=chinese` 时输出中文，默认英文；图表/代码注释使用英文标识符）。论文正文与标题语言遵循 pipeline 启动时的语言声明；不可在单一交付物中混用语言。

---
> **单一权威 (single source of truth)**：输出版本化、Manifest 记录、产物目录、路径回退、过期检测与语言规则全部由此文件统一定义。各 SKILL.md 只需 pointer-load 本文件（`../../shared-references/output-protocol.md`），不再内联三行重复块。