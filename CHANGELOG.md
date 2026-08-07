# Changelog

## [1.1.1] - 2026-08-07

### 定位收敛 + 绘图工具链大一统（figure toolchain overhaul）

**定位收敛：全自动科研 skill**
- 删除 `problems/` 目录（125 问题 Demo 索引）——SciForge-OSS 不是解题基准，是**全自动科研 skill**：人类提供一个研究问题（任意领域），管线端到端自主跑完
- 全部 skill 文档中的"125 问题集"表述改为通用表述（Q-id 保留为用户提供的问题锚点机制，INV-G1 冻结契约不变）
- 版本号全链路统一至 `1.1.1`（根 SKILL.md + plugin.json + package.json + CITATION.cff + 24 子 skill + VERSIONING.md）

**绘图工具链：单一入口 12 引擎 + 内嵌审计**
- `scripts/plotting/render_figure.py` 统一渲染器：matplotlib / d2 / graphviz / tikz / asymptote / typst / diagrams(mingrammer) / blockdiag 家族 / mermaid / pikchr / 手工装配 SVG / **composite 组图**——单一链路，禁止并行工具；PDF+PNG 双产出 + 内嵌 Nature 级审计
- 莫兰迪设计系统单一事实源 `scripts/plotting/sciforge_style.py`：14 个数值校验 token（C*≤25 + WCAG-AA 对比度），修复历史双色表矛盾；`sanitize_palette()` 引擎泄漏色确定性净化；`recolor_icon()` 运行时图标重着色
- 内嵌审计 A1–A10：输出完整性 / DPI / 色板 / 字号下限 / 16:9 / 源码保留 / 复杂度（图标占比+边密度）/ 视觉丰富度 / **品牌泄露守卫** / **文字零重叠**（含 suggested_fixes 精确偏移建议）
- 组图引擎（SCI 一区规范）：`.composite.json` 清单装配 (a)(b)(c)… 面板编号（上方预留条）、面板数硬上限 9（防"一锅粥"）、Nature/Science/Cell 组版决策（按叙事单元组版）、Nature 句式逐面板 caption
- 期刊宽度预设 `--width-preset`：14 种版面（nature/science/cell/aaai/ieee/elsevier × single/1.5/double + wide），LaTeX include 自动 mm 物理宽度，审计宽度下限自适应
- 运行时图标词汇协议（契约 §5.5）：白名单开源图标（bioicons/Tabler/Lucide/Feather/Font Awesome Free）运行时抓取 + 强制莫兰迪重着色，图标资产不入库
- 两级视觉审阅协议（v3.9）：一级 = 宿主 agent 原生视觉自审（9 项清单，多模态宿主强制）；二级 = 外部顾问可选；纯文本宿主降级机械审计——零外部 API
- 全领域契约：figure-complexity-contract.md（领域中立原则 §0 + 八类结构角色×引擎映射 §0.5 + 复杂度下限 §6 + 纵深技法 §6.5）、figure-quality-contract.md §1.5 期刊宽度预设、图层模型 §4.5、Scoped Revision 纪律 §4.6

**跨平台可复刻性**
- 代码消除全部机器专属假设：`os.geteuid()` → 可移植 `_is_root()`；字体动态发现（fontconfig → 三平台目录扫描，用户目录优先）；无绝对路径残留
- `scripts/plotting/INSTALL.md` 重写为三平台复刻手册：Linux(apt/dnf/pacman) / macOS(brew) / Windows(winget/choco/scoop/MSYS2, WSL2 推荐) + 国内镜像 + 4 步验证清单
- 明确不采用记录：blender（无头黑屏）、plotly+kaleido（headless Chrome）；Memslides/AutoFigure-Edit 仅借鉴方法论

**验证**
- 复杂图实测：四泳道架构图（14 卡片/图标/渐变/端口/干线汇流）、里程碑脊柱方法论图、等距机制图、6 面板白底复合图——审计全过、精确 16:9、elsarticle 嵌入零警告
- 全流水完整性：433 文档链接 0 断链、24 插件符号链接有效、`--doctor` READY、figure_audit.json schema 向后兼容

## [1.1.0] - 2026-08-02

### 正式版发布（大一统版本号，取代旧编号体系）

**版本策略（见 VERSIONING.md）**
- 单一版本号 `1.1.0` 统一全链路：根 SKILL.md + .atomcode-plugin/plugin.json + 24 个子 skill + README 徽章 + CHANGELOG + release tag + marketplace
- 后续 bug 修复 / 文档修正记为 `1.1.0.x`（补丁号递增）；功能性重大变更才升主版本（1.2.0 / 2.0.0）
- 废弃历史编号：v2.3/v3.0/v3.2/v3.4（改为 description 里的内容特性标识）、1.2.0/1.3.0（根 SKILL.md 旧值）、2.0.0（experiment-execution）、2.2.0（publishability-score）、0.1.0（marketplace 首发草案）

**v3.4 完整特性集（本正式版内置）**
- human_skip=true：生产级检查点跳过（production_ready=true, skip_authority=human_explicit），区别于 test_mode（降级）
- Figure Budget Contract：per-section 最低图数（Intro≥1、Methods≥1 架构图强制、Results 2-4），总正文最低 4，复合组图（Composite/Group, subcaption 契约）
- LaTeX pipeline 泄露清洗门（paper-writing Step 3.5 + paper-compile Step 1.5 消费）：8 类 regex，正文零内部路径/术语
- Reproducibility + Data Availability 声明（paper-writing Step 4.5，中性 supplementary/ 归档）
- domain-expert blind-spot 评审（auto-review-loop Phase B.2，BLINDSPOT_CHECK.json，effective_score=min(Phase C, B.2 cap)）
- full-code smoke gate（experiment-execution Step 5.0，.SMOKE.json，dispatch 前 1-step 端到端）
- proxy auto-mount + 异步数据集下载 + 本地 benchmark 注册表检查（Step 0d.0）


## [1.3.0] - 2026-08-01

### v2.3 — 单 Agent 全流程纪律 + 全量清理迭代（15 轮自迭代）

**架构级纪律契约**
- 新增 `shared-references/methodology-and-context-contract.md`：充分性停止规则、证据强制、bundle+compact 上下文经济、确定性优先 + 哈希锁、评审只传原始工件、figure-contract-first + 禁编造、单 Agent 边界性声明（7 条）；接线进 auto-pipeline "Context Economy & Boundary" 小节
- 新增 `shared-references/figure-quality-review.md`：外部 LLM 绘图优化辅助（可选顾问——给出改进建议 → 重渲染；非评分门、不阻塞管线），接线进 unified-plotting
- output-protocol 扩展为聚合权威（版本化 + Manifest + 路径回退 + 过期检测 + 输出语言），15 个 SKILL.md 三行 boilerplate 收敛为单指针

**一致性/路径/断链修复（B/C/D/R 系列）**
- domain-signature v2.8 统一为 hint-only；adversarial-falsification 签名来源改指 Phase 1b learner
- 4 视角统一（theoretical/computational/qualitative/empirical）横跨 idea-discovery ↔ novelty-check
- quality-gate QF-G1 路径修正、QF-G5/G6/G7 改为消费权威裁决；publishability-score/method-registry 路径修正
- C1: shared-references 死域引用全清（19 文件）；C2: citation-audit 无经济残留；C3: domain-learner/signature 示例中性化（物理/时序）
- D1-D9: 6 个技能文件死链改下跨正名
- R1-R7: novelty-check 只做幸存者选择；SD-G 角色边界；leakage-audit Type I 交叉引用；paper-writing 删遗留版式；kill-argument 定为 auto-review-loop 子步骤
- B1: idea-discovery novelty 预筛与文献依赖硬性串行化（pending-literature）；B10: Phase 15.5 补入 DAG + workspace

**测试与实证**
- 干净 worker 子代理恢复验证 + explore 子代理 5 域健康检查
- 外部 LLM 绘图优化辅助实操：v1 架构图按建议 v2 闭环（补文献接入 + 反馈回路）
- NatureBench 实际跑题（ubonodin_rnap_inhibition）：Ridge 基线，官方 evaluator Pearson 0.473 / Spearman 0.385 / MAE 2.24
- ITERATION_LOG.md：15 轮大版本自迭代记录
- package.json → 1.3.0

## [1.2.0] - 2026-07-31

### 全领域出版级论文管线 + BA 回溯

v1.2.0 是 v1.1.0 的全领域文风/图/文献/编译/评分/回溯增强。**v1.2.0 = v2.0/v2.1/v2.1.1/v2.1.2/v2.2/v2.2.1 全部增量工作的总和（PR #8 + #9）。**

### 核心变化（按 v2.x 增量分层）

**v2.0 — 实验执行层**
- experiment-execution 新 support skill（toy + full 两阶段，toy 前台 gate，full 后台调度）
- background-dispatch-protocol（tmux→nohup→systemd，>5min 强制后台）
- auto-pipeline Phase 6b/6c 接线，theory-only 路径 SKIP

**v2.1/v2.1.1/v2.1.2 — 5 模式选择器 + 路由修复**
- paper-modes.md 新契约：5 模式（theory/experiment/computational/survey/hybrid），单 elsarticle 骨架，signal 驱动（verification_type + evidence_type），0 学科硬编码
- canonical verification_type tokens：theory-only | computational | theory+experiment | qualitative（v2.1.2 加 qualitative，survey 路由修复）
- 路由修复：v2.1.1 causal_inference/correlational → experiment（伪代码字面一致性）；v2.1.2 qualitative → survey（分支前置）
- venue-profiles 页数表 mode-aware；discipline-writing section-set 延迟到 paper-modes
- idea-discovery 4th empirical perspective（因果识别/数据估计）
- experiment-mode Section 4 adapts by evidence_type（identification strategy for causal_inference）
- RESULT.json 多指标 schema（primary + secondary + gate_logic）
- multi-fidelity universal（去学科硬编码，ML instantiation as trend_score/gradient_health）
- experiment-execution simulational ML/eigenvalue/band-structure toy 模板
- paper-modes computational mode ML 适配（ablation table + reproducibility statement MANDATORY）
- experiment mode ethics/IRB 强制槽
- TEST_MODE bypass-not-skip（agent 做工作，推迟人类审批，production_ready=false）

**v2.2 — 图/文献/编译/评分/架构/设备**
- figure-quality-contract.md 新契约：16:9 横版默认，PDF+PNG 双产出（PDF 给 LaTeX，PNG 给查看），Nature 级可读性（axis≥12pt, ticks≥10pt），d2 为主 + graphviz/dot 兜底（mermaid-cli/drawio 不采用——headless-native 优先）
- unified-plotting 重写：dual output，d2 管线，humanities 图同管线
- Phase 4 universal-retrieval MUST 不可跳过（即使 theory-only，查重）+ mihomo 代理契约（http://127.0.0.1:8099 规则模式）+ FILTER_CHAIN_AUDIT.json（真+全完整性核）+ nohup 超时回退
- Phase 13 paper-compile MUST 零警告不可豁免（texlive 安装验证）
- project-architecture-contract.md 新契约：GitHub 式项目树，README.md 强制，MANIFEST.md 逐阶段追加，工作区卫生（无 orphan 文件/目录/symlink），Phase 16 清洁度审计门控，部分运行也遵守
- experiment-execution Step 0a 设备检测（cpu/cuda/npu/mps/rocm auto-detect）+ fallback_device + VRAM 感知，不硬编码 .cuda()
- publishability-score 新 support skill：6 维评分，dim1 主实验逻辑到位 GATING（<0.5 硬上限 0.4），4 档 verdict（SUBMISSION_READY/SUPPLEMENTARY_GAPS/NEEDS_MAJOR_REVISION/NOT_PUBLISHABLE_NO_MEAN），区分"差补充实验"vs"主逻辑不到位 no mean"，缺失实验清单 actionable
- discipline-writing §3 加 Humanities/Arts + Law/Jurisprudence 行
- Phase 接线：Phase 11 unified-plotting MUST（≥1 图/论文），Phase 14 auto-review-loop MUST，新 Phase 15.5 publishability-score MUST，Phase 16 加清洁度审计

**v2.2.1 — 文风/idea质量/BA回溯**
- writing-principles §0 分领域文风契约（人文/CS/物理/医学/材料/地学/经济 7 族文风 + 开头钩子 + 禁忌）+ 反工程报告腔条款（Nature/一区 top 级别，禁流水账，页数不作为退化借口）
- idea-discovery 5 字段质量门槛（insight/novelty_delta/falsifiable_claim/mechanism/boundary）—反"垃圾 idea"，MCTS 前置硬筛
- BA (Backtracking-After) 机制：实验否定 idea 核心 claim（6c full FAIL after toy PASS / 8 logic FATAL 矛盾 / 14 kill-argument 站住）→ 回 Phase 2 重生成（bounded 2 轮），区别于 phase 内 3 轮 fallback

### 真实端到端验证（8 轮，跨 5 领域 × 5 模式）

| 领域 | 模式 | 全 21 phase | 文献 | 图 | 编译 | 评分 |
|------|------|------------|------|-----|------|------|
| 物理（阻尼振子） | hybrid | 全 PASS | 8 篇 | 4 文件 dual | 零警告 10 页 | SUPPLEMENTARY_GAPS 0.805 |
| 经济（DiD） | experiment | 全 PASS | — | — | — | toy PASS |
| CS/ML（标签平滑） | computational | 全 PASS | — | — | — | toy FAIL（诚实，gate 不放水） |
| 材料（MoS2 带隙） | hybrid | 全 PASS | — | — | — | toy PASS |
| 医学（Alzheimer 诊断） | experiment | 全 PASS | — | — | — | toy PASS |
| 纯数学（AM-GM） | theory | 全 PASS | — | — | — | SymPy PASS, 6b/6c SKIP |
| 综述（正则化） | survey | 全 PASS | 6 篇 proxy | — | — | — |
| 后台调度专项 | — | 全 PASS | — | — | — | nohup + STATUS.json 周期 ✓ |
| 物理 v2.2 全量 | hybrid | 全 PASS | 8 篇 | 4 文件 dual | 零警告 10 页 | SUPPLEMENTARY_GAPS 0.805 |
| 人文（罗马衰亡）v2.2 全量 | survey | 全 PASS | 14 篇 | 4 文件 d2 dual | 零警告 13 页 author-year | SUPPLEMENTARY_GAPS 0.74 |

### 文件清单

- **新增**：figure-quality-contract.md, project-architecture-contract.md, publishability-score/SKILL.md, experiment-execution/SKILL.md, background-dispatch-protocol.md, paper-modes.md
- **重写**：unified-plotting/SKILL.md, universal-retrieval/SKILL.md（mihomo + FILTER_CHAIN_AUDIT）, multi-fidelity-evaluation.md（universal）, venue-profiles.md（mode-aware）, discipline-writing.md（ Humanities/Arts 行 + section-set 延迟）
- **接线**：auto-pipeline/SKILL.md（Phase 4/11/13/14/15.5/16 + TEST_MODE + BA 三处 + 设备检测）

### 关键指标

| 指标 | 值 |
|------|-----|
| 真实端到端跑通 | 10 轮（8 领域 + 2 v2.2 全量），全 21 phase，0 断裂 |
| 5 模式全覆盖 | theory/experiment/computational/hybrid/survey 均有真实执行 |
| 4 canonical tokens | theory-only/computational/theory+experiment/qualitative 均验证 |
| 图工具 | d2 + graphviz/dot + rsvg-convert + inkscape + svgo（headless-native） |
| 编译 | texlive 装好，零警告强制，2 轮全量跑均零警告 |
| 网络 | mihomo 规则模式，arxiv/crossref/openalex/hf/github 全通 |
| PR | #8 (v2.1) merged, #9 (v2.2) merged |

## [1.1.0] - 2026-07-22

### Engineering Grounding + 全仓统一

v1.1.0 是 v1.0.0 的稳定性增强和工程落地评估（Engineering Grounding, EG）正式发布版。**v1.1.0 = 之前 v3.0 系列全部工作的总和。**

### 核心变化

- **EG 第 6 维预筛轴**：idea-discovery 5-axis → 6-axis，新增 Engineering Grounding 列
- **Phase 5b EG 评估**：adversarial-falsification 新增 Phase 5b，产出 ENGINEERING_GROUNDING.md 报告（8 维子评分：Compute/Dev Cycle/Code Complexity/Repro Risk/Dependency/Capital/Temporal Maturity/Regulatory）
- **EG 复合评分权重**：novelty-check 公式更新为 `novelty×0.45 + feasibility×0.25 + relevance×0.15 + EG×0.15`
- **DAG schema**：idea-dag-schema.md v1.0→v1.1，新增 `engineering_grounding` 节点字段
- **21-phase 全仓统一**：20-phase → 21-phase（AGENT_GUIDE + 7 个契约文件 + orchestrator + problems）
- **EG 报告 AI 开发路线图**：支持 ai-dev-path PDF 图类型，自动出图
- **EG 领域 N/A 规则**：纯理论领域可标记 EG 为 N/A，跳过工程落地评估
- **competitive-analysis 5维→8维**：方案评估矩阵扩建
- **全仓 3维→4维**：novelty、feasibility、relevance + EG 新增
- **MCTS EG exploration bonus**：EG 低的 idea 在 MCTS 中获得额外探索奖励
- **根级 SKILL.md**：新增包描述文件
- **README 安装指南**：新增 3 种安装方式 + AI agent 配置说明

### 文件清单

- **文件总数**：74 个文件（22 SKILL.md + 36 shared-references + 1 orchestrator + 13 支持 + 文档 + 问题索引）
- **新增**：根 SKILL.md、competitive-analysis 8 维评估
- **删除**：临时方案文档（v3.0 清理）
- **修复**：EG 契约 5 处坏链、README 5 处 20-phase 残留、全仓 20→21 phase 统一

### 关键指标

| 指标 | 值 |
|------|------|
| 链接完整性 | 400+ 链接，0 坏链 |
| JSON 块 (strict) | 46 块，0 invalid |
| Skill 文件 | 22 个 SKILL.md |
| 共享契约 | 36 个 shared-references |
| Pipeline 阶段 | 21-phase DAG 闭环 |
| 学科覆盖 | 全领域 |
| 工程落地评估 | 8 维 EG 子评分 |
| Team 大小 | 1 人（全员） |
| 许可证 | MIT |

---

## [1.0.0] - 2026-07-21

### 首个正式发行版

SciForge-OSS 第一个正式发行版，涵盖从初始架构到完整功能的所有演进。**v1.0.0 = 之前的 v2.0.0 + v2.1.0 + ... + v2.9.0 全部工作的总和。**

### 核心能力

- **全领域支持**：框架不限定学科，通用 pipeline。物理学、数学、计算机科学、医学、经济学、教育学、材料科学、地球科学、天文等均可使用
- **DAG 驱动科研闭环**：20-phase DAG 循环，3 个 idea 并行探索 → MCTS 4 轮迭代 → Phase 2.5 证伪门控 → Phase 3 新颖性门控 → 收敛 → 推导 → 验证 → 写作 → 评审 → 输出
- **4 个元技能**：Dynamic Sandbox / Dynamic Tooling / Universal Retrieval / Unified Plotting
- **结构化自评审**：跨模型评审→单 agent 角色切换自评审（auto-review-loop, logic-verification, kill-argument, quality-gate）
- **三路验证路径**：理论-only / 计算 / 理论+实验
- **统一 elsarticle LaTeX 模板**，零警告零报错编译
- **Learner-first 签名**：Phase 1a `/domain-signature` 降级为 OPTIONAL hint，Phase 1b `/domain-learner` 升为 MUST 唯一真相源
- **TDAL 4 维联合置信度**：T × D × A × L，product 公式，锁定额度阈值 + floor constraints
- **Ouroboros 数据集成**：Basic（D 维可用性, Phase 2.5）+ Deep（T 维理论↔数据验证, Phase 6/10 闭环）
- **自适应 pipeline**：M1 强度自适应（REDUCED/STANDARD/INTENSIFIED/REPLACED/SKIPPED）+ M3 模式自动降级（MUST/CONDITIONAL/OPTIONAL/SKIP）
- **置信度提高机制**：3 机制（假设强度分析 + 替代路径分析 + 渐进式验证）bounded uplift loop，3 轮跨机制硬上限
- **竞品对标自动定期更新**：4 differentiator × 4 decay_state 转移 rubric，季度自动触发
- **社区贡献 PR 通道**：evidence_type 开放贡献 + 6 检 review 契约 + 3+3 falsification test gate

### 文件清单

- **22 个 SKILL.md**（6 元技能 + 13 支持 + 1 编排器 + 2 领域技能）
- **36 个 shared-references 契约文件**（TDAL schema、Ouroboros 集成、领域签名消费、领域自适应指南、自适应 pipeline、置信度提高、竞争 drift 监控、社区贡献协议等）
- **problems/125-SCIENCE-PROBLEMS.md**（125 题 Demo 索引，6 大类）
- 文档：README.md、AGENT_GUIDE.md、CHANGELOG.md、CONTRIBUTING.md、CITATION.cff

### 关键指标

| 指标 | 值 |
|------|------|
| 链接完整性 | 401 链接，0 坏链 |
| JSON 块 (strict) | 46 块，0 invalid |
| Skill 文件 | 22 个 SKILL.md |
| 共享契约 | 36 个 shared-references |
| Pipeline 阶段 | 20-phase DAG 闭环 |
| 学科覆盖 | 全领域（物理、数学、CS、医学、经济、教育、材料、地球科学、天文、化学、工程等） |
| Team 大小 | 1 人（全员） |
| 许可证 | MIT |

---

## Pre-release 开发历史

以下条目记录了从初始原型到正式版之前的演进过程。

### [2.9.0] - 2026-07-21

#### 核心转变
- **v2.8→v2.9**: 新增 Engineering Grounding (EG) 轴，解决"工程落地评判"盲区。6th pre-screen axis + 5 维子评分 + Phase 5b 工程落地估计 + 复合评分 0.15 权重 + 三段式下行保护。

#### 新增
- **EG 契约**: 新建 `shared-references/engineering-grounding-contract.md`，定义 5 维子评分 (Compute/Dependency/Team-Year/Repro Risk/Capital)、N/A 处理、BLOCKED 规则、三段式 Engineering Path。
- **6th pre-screen axis**: `idea-discovery/SKILL.md` 5-axis → 6-axis，新增 Engineering Grounding 列。
- **Phase 5b**: `adversarial-falsification/SKILL.md` 拆分 Phase 5a (OSS Sandbox) + Phase 5b (EG Estimate)，产生 `ENGINEERING_GROUNDING.md` 报告。
- **复合评分权重**: `novelty-check/SKILL.md` 公式更新为 `novelty×0.45 + feasibility×0.25 + relevance×0.15 + EG×0.15`。
- **DAG schema**: `idea-dag-schema.md` v1.0→v1.1，新增 `engineering_grounding` 节点字段。
- **置信度拆分**: `result-to-claim/SKILL.md` Grounding Confidence 拆为 OSS Sandbox Grounding (重算) + Engineering Grounding (继承)。
- **Orchestrator**: `auto-pipeline/SKILL.md` 20→21 阶段，新增 Phase 2.5b 质量门控 + `ENGINEERING_GROUNDING.md` workspace。
- **竞争分析**: `competitive-analysis.md` 方案 2 标记为 ✅ 已实施。
- **包结构**: `SKILL.md` + `AGENT_GUIDE.md` shared references 30+ → 31+。

#### 修复
- EG1: competitive-analysis.md 方案 2 "实施复杂度" roadmap 从未落地 → 已实施
- EG2: 多阶段 "20-phase" 残留 → 21-phase

### [2.8.0] - 2026-07-21

#### 核心转变
- **v2.7→v2.8**: 从"规则驱动"升级为"学习驱动 + 自适应 pipeline + 置信度可提高"。落地用户上一条回复中短期/中期/长期三档路线图全部实现。

#### 短期 (S1-S3)
- **S1 — Learner-first 签名**: Phase 1a 降级为 OPTIONAL 快路径 hint；Phase 1b 升为 MUST 唯一真相源。
- **S2 — TDAL 4 维联合置信度 schema 锁定**: 新建 `domain-adaptation-contract.md`，锁定 T×D×A×L 公式 + 权重 + 阈值 + 契约。
- **S3 — Ouroboros 基础集成**: 重写 `ouroboros-integration.md`，新增 Phase 1 seed + Phase 2.5 spec + Phase 10 TDAL D-dim wiring。

#### 中期 (M1-M3)
- **M1 — 领域自适应 pipeline 强度**: 新建 `domain-adaptive-pipeline.md`，按 evidence_type × paradigm 动态调整 Phase 5/6/11 强度。
- **M2 — 置信度提高机制**: 新建 `confidence-uplift.md`，3 机制 bounded uplift loop。
- **M3 — pipeline 自适应降级**: 新建 `pipeline-adaptive-degradation.md`，phase mode 从签名自动算出。

#### 长期 (L1-L3)
- **L1 — 社区贡献 PR 通道**: 新建 `domain-contribution-protocol.md`。
- **L2 — Ouroboros 深度集成**: 新建 `ouroboros-deep-integration.md`，T 维新增 0.2 权重 `theory_data_validation` 组件。
- **L3 — 竞品对标自动定期更新**: 新建 `competitive-drift-monitor.md`。

#### 修复 (v2.7 残留 + 历史债务)
- E17: orchestrator "17-phase" 残留 → 20-phase
- E18: domain-learner 输出文件名自相矛盾 → 统一
- E19: result-to-claim 4 维置信度算术错误 → 修正
- E20: orchestrator See Also 漏链接 → 补全
- E21: result-to-claim "(新增)" 残留 → 替换
- E22: 全仓 173 处 Markdown 坏链 → 批修，最终验证 373 链接 0 坏链
- E23: 2 处 JSON template 块非法语法 → 修复，最终验证 46 JSON 块 0 invalid

### [2.7.0] - 2026-07-20

### Domain Learner + 4 维联合置信度
- 新增 meta-skill `/domain-learner`：从文献自动学习领域特性，替代硬编码签名。
- 双源签名传播：Phase 1a `/domain-signature` + Phase 1b `/domain-learner`。
- 4 维联合置信度：理论(T) × 数据(D) × 领域适配(A) × 文献支持(L)。

### [2.6.0] - 2026-07-20

### 领域自适应执行指南
- 新增 `domain-adaptation-execution.md`：7 步执行指南 + 错误恢复表 + 快速参考卡。

### [2.5.0] - 2026-07-20

### Ouroboros 集成 + 验收测试 + 竞争分析
- **Ouroboros Data-Insight 集成**：新增 `ouroboros-integration.md`。
- **领域适配验收测试**：新增 `domain-adaptation-test.md`，6 个验收测试用例。
- **竞争分析**：新增 `competitive-analysis.md`。

### [2.4.0] - 2026-07-20

### 强制启动协议 + Pipeline Integrity + Fantasy Prevention + 5 领域示例
- **强制启动协议**：新增 `startup-protocol.md`。
- **Pipeline Integrity Check**：新增 `pipeline-integrity.md`。
- **Fantasy Prevention Protocol**：新增 `fantasy-prevention.md`，5 门幻想检测系统。
- **5 领域具体示例**：新增 `domain-adaptation-examples.md`。

### [2.3.0] - 2026-07-20

### 领域签名自动消费链路 + 端到端领域自适应
- **核心改造：领域签名消费链路 (wiring layer)**：新增 `domain-signature-consumer.md` 协议。
- **端到端流程验证**：经济学 / 数学 / 医学 三领域验证。

### [2.2.0] - 2026-07-20

### 领域特征自提取 + 失败模式库 + 优雅降级 + 数据可用性 + 自适应写作
- **A — 领域特征自提取**：新增 `domain-signature` skill。
- **B — 领域失败模式库**：新增 `domain-failure-modes.md`，6 大类 40+ 已知失败模式。
- **C — 优雅降级协议**：orchestrator 新增 MUST/OPTIONAL/CONDITIONAL 三级 phase mode。
- **D — 数据可用性检查**：adversarial-falsification 新增 Phase 6 数据清单。
- **E — 领域自适应写作**：discipline-writing 更新，5 种 evidence_type 自动选择写作风格。

### [2.1.0] - 2026-07-20

### 证伪驱动 + 落地置信度 + 上下文压缩 + 领域范式 + 性能优化
- **核心改进 (P0: 落地性)**：证伪驱动（adversarial-falsification 前置）+ 落地置信度 + 上下文压缩 60%。
- **领域范式 (P1)**：5 种 evidence_type 范式定义 + 签名驱动视角权重。
- **性能优化 (P2)**：MCTS 有界轮次 + 文献检索结果缓存 + 数值沙盒内存上限。

### [2.0.0] - 2026-07-20

#### 重大变更
- **全领域支持**: 框架不限定学科。
- **结构化自评审**: 跨模型评审→单 agent 角色切换自评审。
- **理论验证路径**: 新增理论-only / 计算 / 理论+实验 三路验证路径。
- **DAG 可视化**: 新增 IDEA_DAG_VISUAL.md。

#### 新增
- LaTeX 模板文件: `main.tex` + `math_commands.tex`
- 工具模板库: symbolic-reasoner, statistical-modeler, knowledge-graph, formal-verifier, code-synthesizer, data-transformer, text-analyzer
- 理论论文写作模式: 新增 `theory_only` 结构分支
- 理论图表类型: commutative-diagram, derivation-tree, concept-map, dependency-graph, counterexample-plot
- 文档: CONTRIBUTING.md, CHANGELOG.md, CITATION.cff, .gitignore

#### 修复
- F1: DAG 路径统一 (`dag/`→`refine-logs/`)
- F3: LaTeX 模板补充
- F4: cross-review Phase 编号修复
- P0-1: auto-review-loop 路径引用修复
- P0-3: kill-argument 读取源修复
- A3/A4: result-to-claim 路径修复

#### 删除
- `cross-review/SKILL.md`（合并入 auto-review-loop）
- 跨模型评审相关引用简化

### [1.0.0] - 2026-07-19

#### 初始版本
- 单编排器架构 (auto-pipeline)
- 6 个元技能 + 13 个支持技能
- 16 个共享契约
- 17 阶段 DAG 循环（v2.8 升级为 20-phase：补 Phase 1a/1b domain signature + Phase 2.5 adversarial falsification）