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

## 产物目录结构

```
{problem_id}/
├── refine-logs/        ← idea-discovery + novelty-check 产物
├── literature/         ← universal-retrieval 产物
├── methods/            ← method-registry 产物
├── derivations/        ← theory-derivation 产物
├── audit_report/       ← logic-verification + leakage-audit 产物
├── figures/            ← unified-plotting 产物
├── paper/              ← paper-writing + paper-compile 产物
├── review-stage/       ← auto-review-loop 产物
├── citation_audit/     ← citation-audit 产物
└── output/             ← 最终归档
```

## 路径回退规则

读取时先查找 stage-scoped 路径，未找到则回退到根级路径（向后兼容）。写入始终使用 stage-scoped 路径。

## 过期状态检测

状态文件 (REVIEW_STATE.json 等) 的默认过期阈值：24 小时。过期时警告用户，可继续或重新开始。