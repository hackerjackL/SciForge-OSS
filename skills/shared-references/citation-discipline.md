# Citation Discipline (SciForge-OSS — Condensed)

> **核心**: 每篇引用必须通过 3 层防幻觉验证。没有论文凭记忆捏造。

## 3 层防幻觉验证协议

### 第 1 层：arXiv 批量验证
- 收集 arXiv ID，以 40 个为一批查询 `http://export.arxiv.org/api/query`
- 验证标题、作者、摘要、分类一致
- 状态：`verified` / `unverified` / `error`

### 第 2 层：CrossRef DOI 验证
- 对有 DOI 的论文查询 `https://api.crossref.org/works/{doi}`
- 验证 DOI 可解析、标题匹配、至少一个作者匹配
- 状态：`verified` / `unverified` / `error`

### 第 3 层：Semantic Scholar 模糊匹配
- 查询 `https://api.semanticscholar.org/graph/v1/paper/search?query={title}`
- 验证标题、作者、year 匹配
- 状态：`verified` / `unverified` / `error`

## 最终验证检查清单

- 每篇引用使用 `\cite{key}`，key 在 `references.bib` 中存在
- 每篇引用至少有 1 层验证通过（最好是 3 层）
- 无 `\cite{TODO}`、`\cite{forthcoming}`、`\cite{arxiv:TODO}`
- 每篇引用在正文中实际被引用（无 orphan 引用）
- BibTeX 条目从已验证源生成，不手写

## BibTeX 管理规则

- 从 arXiv/CrossRef/S2 自动生成 BibTeX，不手写
- 每个条目包含 `verification_status: verified` 标签
- 同一论文引用统一 key，不重复
- 不包含无法验证的条目

## 常用模板

```
@article{key,
  author    = {Author, A. and Author, B.},
  title     = {Title},
  journal   = {Journal},
  year      = {2024},
  volume    = {N},
  pages     = {X--Y},
  doi       = {10.xxx/xxxxx},
  verification_status = {verified}
}
```

## 快速参考

- **3 层验证**: arXiv → CrossRef → Semantic Scholar
- **禁止**: `\cite{TODO}`, `\cite{forthcoming}`, 手写 BibTeX
- **强制**: 每篇引用至少 1 层验证通过
- **输出**: `literature/references.bib` + `VERIFICATION_LOG.md`