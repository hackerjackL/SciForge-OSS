---
name: universal-retrieval
type: reference-skill
role: academic-retriever
---

# Meta-Skill: Universal Academic Retrieval

## Quick Reference

- **Purpose**: 多源学术搜索 + 3 层防幻觉引用验证
- **Input**: 搜索查询
- **Output**: references.bib + landscape_report.md + VERIFICATION_LOG.md
- **Key**: 6 源 (arXiv→S2→CrossRef→PubMed→Web→OpenAlex)；每篇引用必须通过验证

## Use When

当 AI scientist 需要为任何科学问题查找、验证或检索真实的学术参考文献时——无论学科——使用此 skill。

典型 prompt：
- "找关于这个问题的参考文献"
- "search for papers on quantum entanglement"
- "find recent work on this topic"
- "verify if this paper exists"
- "get the DOI for this reference"

这是**防幻觉**元技能：确保最终输出中的每篇引用都有真实的、可验证的学术来源。没有论文凭记忆捏造。

## Job

提供一个统一的多源学术搜索接口，将查询路由到最合适的数据库，通过真实 API 验证每篇候选论文，并返回结构化的、可引用的结果。

**skill 不理解论文内容——它只检索、验证和格式化元数据。**

不可妥协的目标：
1. **输出中的每篇论文必须有真实存在验证标签**——没有论文凭信仰被包含
2. **没有论文被静默丢弃**——每篇候选论文要么被验证，要么被明确标记为不可验证
3. **3 层防幻觉协议是强制性的**——arXiv 批量检查 → CrossRef DOI → Semantic Scholar 模糊匹配
4. **每篇引用包含可验证的 DOI 或 arXiv ID**——没有"即将发表"、"已投稿"而不验证

## 数据源

按优先级顺序搜索。所有源都是可选的——如果某个源不可用，静默跳过并继续下一个。

| 优先级 | 源 | 提供内容 | 覆盖范围 |
|--------|----|---------|---------|
| 1 | **arXiv API** | 预印本元数据（标题、摘要、作者、分类、PDF URL） | 所有 STEM 领域，更新最快 |
| 2 | **Semantic Scholar API** | 已发表论文、引用数、会议/期刊、TLDR | 广泛的 CS + 科学，适合找影响力 |
| 3 | **CrossRef API** | DOI 解析、期刊元数据、作者名 | 所有已发表期刊 |
| 4 | **PubMed API** | 生物医学文献 | 生物学、医学、神经科学 |
| 5 | **Web Search** | 通用网络 + Google Scholar | 以上 API 未覆盖的任何内容 |
| 6 | **OpenAlex API** | 开放学术图谱、作者消歧 | 所有学科，适合引用网络 |

## 3 层防幻觉验证协议

每篇候选论文在进入最终报告前**必须**通过以下层：

### 第 1 层：arXiv 批量验证
- 收集所有候选论文的 arXiv ID
- 以 40 个 ID 为一批查询 `http://export.arxiv.org/api/query`
- 验证：标题、作者、摘要、分类一致
- 状态：`verified` / `unverified` / `error`

### 第 2 层：CrossRef DOI 验证
- 对有 DOI 的论文查询 `https://api.crossref.org/works/{doi}`
- 验证：DOI 可解析、标题匹配、至少一个作者匹配
- 状态：`verified` / `unverified` / `error`

### 第 3 层：Semantic Scholar 模糊匹配
- 对第 1-2 层未验证的论文，按标题查询 Semantic Scholar API
- 使用模糊匹配（阈值 ≥ 0.6）
- 验证：至少 2 个元数据字段匹配（作者、年份、会议/期刊、标题）
- 状态：`verified` / `unverified` / `error`

### 最终判定
- `PASS` — 至少通过 3 层中的 2 层
- `WARN` — 通过 1 层，或在 2 层中部分匹配
- `BLOCKED` — 通过 0 层，或致命不匹配
- `ERROR` — API 失败，无法确定

## OSS 单活动条策略（升级补充）

OSS 是学科无关的，125 问题跨 10+ 領域，**不能按学科硬切换源优先级**（主仓库 SciForge 有 4 学科的不同源优先级 + 引文窗口；OSS 没有）。OSS 用**统一优先级**（arXiv → S2 → CrossRef → PubMed → Web → OpenAlex，见上表），并对所有问题应用同一套参数：

- **统一引文窗口** `min_year=2020`（主仓库有 6/12/18 月按学科变；OSS 用统一绝对年份）
- **统一源优先级**（上表priority 1-6，无学科切换）
- **统一检索条数** `max_papers=30`（主仓库按学科变；OSS 统一）
- **统一验证级别** `verification_level=full`（3 层防幻觉是强制的，无学科降级路径）

**OSS 没有 `discipline-context` 的源优先级覆盖**——见 [`discipline-context.md`](../shared-references/discipline-context.md) OSS 单行契约：所有 125 问题用 `general` 行，即上表的统一优先级。如果你看到迁移自主仓库的旧代码引用 `DISCIPLINE_CONTEXT.source_priorities`，**删除该分支**——OSS 没有这种按学科切换的逻辑。

## 配置

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sources` | list | `["arxiv", "semantic_scholar", "crossref", "pubmed", "web", "openalex"]` | 搜索哪些源——OSS 默认全 6 源（主仓库只默认 4 源，OpenAlex 是主仓库升级后新增；OSS 已含） |
| `max_papers` | int | `30` | 最终输出最大论文数（OSS 统一，不按学科变） |
| `min_year` | int | `2020` | 考虑的最早出版年份（OSS 统一绝对年份，不按学科变引文窗口） |
| `verification_level` | enum | `full` | `full`（3 层，OSS 强制默认）、`quick`（仅 arXiv）、`none`（无验证，**OSS 不建议**——会破坏下游 `/citation-audit` 的 3 层契约） |

## Steps

### Step 1: 解析搜索查询

从请求中提取：
1. **研究主题**——核心科学问题或领域
2. **子主题**——要探索的特定方面
3. **时间范围**——论文应多新
4. **类型**——综述、原创研究、方法论、数据集
5. **约束**——要包含/排除的特定作者、会议/期刊或方法

### Step 2: 多源搜索

按优先级顺序执行搜索：
1. arXiv API — 带分类过滤器的结构化查询
2. Semantic Scholar — 按研究领域过滤
3. CrossRef — 基于 DOI 的元数据查询
4. Web Search — 学术 API 未覆盖的主题

按 arXiv ID 或 DOI 去重。

### Step 3: 3 层验证

对每篇候选论文运行 3 层验证协议：
1. 如果有 arXiv ID → 第 1 层（arXiv）
2. 如果有 DOI → 第 2 层（CrossRef）
3. 如果仍未验证 → 第 3 层（Semantic Scholar）
4. 计算最终判定

**特殊处理：**
- 书籍：通过 CrossRef ISBN 查询验证
- 技术报告：通过网络搜索 + 机构库验证
- 会议论文：通过 Semantic Scholar 会议过滤器验证

### Step 4: 综合综述报告

将经过验证的论文组织成结构化综述：
1. **子方向聚类**——按研究子领域分组
2. **方法论家族**——按方法分组（理论、实验、仿真）
3. **时间地图**——领域如何随时间演变
4. **空白识别**——哪些问题尚未回答

### Step 5: 生成引用产物

对每篇经过验证的论文：
1. 生成 BibTeX 条目 → `literature/references.bib`
2. 生成结构化 JSON → `literature/verified_papers.json`
3. 写入验证状态 → `literature/VERIFICATION_LOG.md`

## 输出产物

- `literature/landscape_report.md` — 结构化综述报告
- `literature/references.bib` — 所有验证论文的 BibTeX
- `literature/verified_papers.json` — 结构化元数据
- `literature/VERIFICATION_LOG.md` — 每篇论文的验证状态
- `literature/unverified_papers.json` — 验证失败的论文（含原因）

## 调用下游 skill

- `/theory-derivation` — 文献调研后，用找到的引用指导推导
- `/paper-writing` — 文献产物直接喂给论文写作

## 共享契约引用

- [citation-discipline](../shared-references/citation-discipline.md) — 3 层防幻觉验证协议
- [discipline-context](../shared-references/discipline-context.md) — 学科感知搜索路由
- [output-manifest](../shared-references/output-manifest.md) — 产物结构契约