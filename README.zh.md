# SciForge-OSS

> **[中文](README.zh.md)** | **[English](README.md)**

[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.7.1-green.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub](https://img.shields.io/badge/repo-gitcode-blue)](https://gitcode.com/GewisLab/SciForge-OSS)
[![AI for Science](https://img.shields.io/badge/AI%20for-Science-ff69b4)](https://gitcode.com/GewisLab/SciForge-OSS)

> **AI for Scientist Anything** — Skill 驱动的通用科研运行时：**Skill 库（纯 Markdown）+ Runtime Kernel（代码强制控制循环）+ RSI 进化层**。
>
> 知识层保留原精神：**skill 依旧是纯 Markdown**——无 `.py` 无 bash 无 IDE 专属语法，任何能读文件的 agent（Claude Code、Cursor、Trae、Codex…）都能消费。1.5.0 的变化是**拆分**，v1.6.0 进一步把证据变成**可验证**（实验安全扫描 kernel 强制、TDAL 联合置信、反幻想五门、Arb 认证区间、句级引用归因、SMOKE 门、注入消毒、限速器、双计时器）：**"做什么"留在 Markdown，"如何强制"进入代码**。v1.7.0 加入 **ScientistTwo 对标层**——把 Google arXiv:2609.19644 成绩背后的机制复刻为开源代码：Subset→Full-Set 实验阶梯 + 三态 Critic（6c 边界门）、5–6 计划消融账本 + 严格 AblCritic（相位 10 门）、score<8 rebuttal 闭环 ≤2 轮 + Meta-Review {ACCEPT|REFINE} + 锚点校准评审分、wrap-up 的 reward-hacking + 方法↔代码完整性审计、带探索保证的 idea evolution，以及同构的 CPU 级 `bench/s2demo` 子 bench。v1.7.1 加入 **AAR 反 Goodhart 层**（移植 Anthropic arXiv:2608.28945 的模式）：实验边界的 fail-closed 预执行完整性监控（D1/D2/D3）、geomean 头条度量、results-free 预注册——外加图系统修复与实证版 S2 披露语态，全部由两轮五域 ARC-Bench 实测驱动。可选的 `kernel/`（Python ≥3.10，仅标准库）把 21-phase DAG 跑成真正的状态机：事件溯源续跑、机械门强制、把人工检查点变成代码、多后端 provider、跨模型审稿团，以及让 skill 库自我进化的递归闭环。**无 UI**——headless CLI（`sciforge run …`）或宿主 agent 模式均可。
>
> 两种用法：**(A) 纯 skill**（任意 agent 内 `/auto-pipeline "问题"`）——与从前一致；**(B) skill + kernel**（`sciforge run --workspace … --host claude`）——管线再也不能静默跳过门、进程死了能续、且每一轮都变得更强（RSI）。
>
> SciForge 是**全自动科研系统**，不是解题基准：人类提供一个研究问题（任意领域），管线从想法发现到投稿级论文端到端自主跑完。

---

## 目录

- [这是什么](#这是什么)
- [Runtime Kernel（v1.5.0）](#runtime-kernelv150)
- [RSI：skill 库自我进化](#rsiskill-库自我进化)
- [安装指南](#安装指南)
- [架构：DAG 驱动的科研闭环](#架构dag-驱动的科研闭环)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [质量门](#质量门)
- [全领域支持](#全领域支持)
- [验证路径：四路可选](#验证路径四路可选)
- [多领域示例](#多领域示例)
- [核心设计原则](#核心设计原则)
- [绘图工具链](#绘图工具链)
- [致谢](#致谢)
- [Star 增长趋势](#star-增长趋势)
- [许可证](#许可证)

## 这是什么

**SciForge-OSS** 是一个纯 Skill 驱动的 **通用 AI Scientist 框架**。它的**方法**是全领域的（单一管线、无学科分支），并已在物理、数学、计算机、生命科学、医学、经济学、教育学、材料、地学等领域实践；它的**能力边界**（诚实表述）是**代码可执行的科学**：凡方法论能落成一台 Linux 机器或 GPU 集群上的代码、数据与文献工作的领域，都在其内。

**核心哲学**：全领域的是**方法**。框架本身不预设任何学科知识，所有学科方法论由 agent 运行时推理处理——且以**程序、数值/符号计算、检索证据**的形式产出。

### 范围与能力边界（v1.4.0 — 诚实定位）

- **范围内（v1.7.1 重述——"代码即科学"）**：一切证据可由代码/数据/文献在单机或集群上产出的学科——文、理、工、社科皆可：数值与符号仿真（NumPy/SciPy/SymPy/Julia）、机器学习与统计估计、因果推断、计量学与计量基准、代码求解的 agent-based/ODE-PDE 模型、PINN/代理模型、CV 与 NLP、大气污染建模、光学传感器仿真、金融预测、智慧教育分析、embodied AI 与 LLM/RSI/auto-research 研究、边缘计算，以及 web 检索增强的定性/人文/社科分析。计算生物学（基因组尺度模型、仿真）作为代码可执行科学在范围内。
- **范围外**：**湿实验/临床生物医学**（证据依赖物理实验或患者数据）；核心证据依赖**专有或 GUI 绑定求解器**（商业 CFD/FEA、光学仪器台架软件）或**物理硬件**的领域。若该方法能约化为可脚本化、开放或可代码调用的管线（如用 OpenFOAM/Julia PDE 代替 GUI CFD），则重新进入范围；纯 GUI 工作流本身不在内。
- **COMSOL（v1.7.1 定位）**：不作为独立领域。仅以**联合**方式进入——作为 PINN/代理模型或材料预测研究的仿真数据来源；专用 COMSOL 接口/MCP 是规划中的集成路径；"替我跑 COMSOL"类请求由 `/intake-triage` 拒绝。
- 这是对**证据生产工具**的限定，不是对智能的限定：同一管线可对任何领域推理，但只在存在机器可执行方法处产出证据。

**OSS = Open Single-question Stream** ——单题执行：每次 invocation 处理一个 Q-id，不自动迭代全部问题；全领域 1 universal pipeline（无 overlay，无学科分支）；agent 运行时推理处理领域方法；senior-reviewer-agnostic 唯一；单一 unified `elsarticle` 模板；理论-only + 计算 + 理论+实验 + qualitative 四路验证可选；INV-G1 唯一不变量（PROBLEM_ANCHOR_FREEZE 通用）。

SciForge-OSS 提炼出 **4 个通用元技能**（Meta-Skills），以不变应万变：

| 元技能 | 角色 | 说明 |
|--------|------|------|
| **Dynamic Sandbox** | 计算引擎 | 运行任意 Python/Julia 科学计算（NumPy/SciPy/SymPy）——无 GPU 训练，仅数值 sanity check |
| **Dynamic Tooling** | 工具工厂 | 运行时发现工具不足时，动态编写并注册临时工具 |
| **Universal Retrieval** | 文献检索 | 多源学术搜索（arXiv/S2/CrossRef/PubMed/Web/OpenAlex）+ 3 层防幻觉验证 |
| **Unified Plotting** | 图表渲染 | 结构化数据 → 出版级矢量图（SVG/PDF）；多巴胺色系（Layer 1，色盲可辨校验的高饱和盘）+ viridis/magma/cividis 数据热图（Layer 2） |

## Runtime Kernel（v1.5.0）

`kernel/` 是 skill 库的**代码控制面**（Python ≥3.10，仅标准库——唯一的额外 pip 依赖是 pytest）。skill 依旧是**方法**的唯一来源；kernel 是**控制**所在：

| 能力 | 机制 |
|---|---|
| **状态机** | `kernel/config/phasegraph.json` 把 21-phase DAG、回路预算（L1–L13）、按相门编码为可执行配置——编排循环由代码驱动，而非 prose |
| **事件溯源续跑** | `.sciforge/events.ndjson`（追加式）+ `RUNSTATE.json`；进程死亡经 stale lockfile 检出，**从精确边界重放续跑**（macOS kill -9 实测通过） |
| **门嵌入控制流** | 每个边界以代码强制跑 `validate_verdicts.py --strict`、`security_scan.py`、`gap_gate.py`、`check_figure_embedding.py --require-renderer`、`leakage_scan.py`；门不过则无法推进——审计再也无法被静默跳过 |
| **HITL 数据化** | 检查点 = `paused_checkpoint` + 审批记录 + `APPROVAL_LOG.txt`；用 `sciforge approve/deny` 决策，或 `--human-skip` / `--test-mode` 委托 |
| **provider 层** | 按角色分档多后端路由（Anthropic/OpenAI 兼容/Ollama；网关 env 生效），真实 token 记账入 `RUN_BUDGET.json` |
| **宿主适配** | `--host claude`（Claude Code CLI，回传 `total_cost_usd`）、`--host codex`，或 `manual` bundle 协议（任意 agent 经 `.sciforge/host/*.done.json` 驱动） |
| **实验执行** | 沙箱门控派发（macOS Seatbelt / Linux bubblewrap）、worker 池、后台 nohup + STATUS.json 聚合、设备规划（CUDA/ROCm/NPU/MPS/CPU 经 `detect_device.py`） |
| **ScientistTwo 对标（v1.7）** | `s2/` 包 + 边界门：Subset→Full-Set 阶梯与三态 Critic（`s2_ladder` @6c）· 5–6 消融计划与严格 AblCritic（`s2_ablation` @10）· score<8 rebuttal ≤2 轮 + Meta-Review {ACCEPT\|REFINE} · 锚点校准评审分 · reward-hacking + 方法↔代码对齐审计（`s2_audit` @wrap-up）· 探索保证 idea evolution · `bench/s2demo`（CPU、仅 numpy） |
| **SOTA 爬山 + 失败记忆（v1.7.1）** | `sota.py` 驱动：声明 incumbent → 由跨 run 教训索引（`sciforge memory build/query`）播种变异提案 → 每轮 geomean closed-fraction 头条 + capability-floor/回归 CI 使"赢"失效 → plateau/预算停止。`completion_gate` 让 S01 式虚假完成报告在 wrap-up 物理上不可能；`submission_ready` 按二区标准给论文分级 READY / MINOR_REV / MAJOR_REV / NOT_READY |
| **约束三档（v1.7.1）** | `--discipline strict|balanced|lean`：severity ∝ 后果 × 事后不可检测性。lean 只把 fabrication/leakage/ladder/integrity/citation/编译零 ERROR 保持硬门；cosmetic 检查（警告、页带、计数）改披露而非回环——强模型不再付负优化税 |
| **daemon** | `sciforge serve`——headless 队列 + loopback HTTP（:4510），服务器过夜运行；**任何环节无 GUI** |

```bash
sciforge run --workspace ./runs/Q001 --problem "你的问题" --host claude --loop
sciforge run --workspace ./runs/Q001 --problem "..." --discipline lean \
             --claim-mode sota                     # 强模型宿主 + SOTA 目标
sciforge status  --workspace ./runs/Q001
sciforge resume  --workspace ./runs/Q001 --loop    # 崩溃后：重放事件，续跑
sciforge approve --workspace ./runs/Q001 idea-pick # 人工检查点
sciforge memory build && sciforge memory query "bootstrap 覆盖率 重尾" -k 5
sciforge sota next --workspace ./runs/Q001         # 爬山：下一个变异提案
sciforge sota record --workspace ./runs/Q001 --variant v2 --legs legs.json
sciforge doctor                                    # 环境自检
```

## RSI：skill 库自我进化

完成的 run 会产出信号（回路计数、门拒绝、`LESSONS.json`、事件日志）。`sciforge evolve` 把它们转成 **SKILL.md patch 候选**，用真正的优化器搜索最优——PUCT 树或 MAP-Elites 多岛——每个候选用**混合门**打分：机械 CI/schema/golden 回归（失败即硬零）+ 冻结 rubric 的 LLM judge（提供判别力）。防线取自 openJiuwen/ScienceDiscovery 与 AI-Scientist v2，均已实测：

- **三分片** rollout/gate/**held-out test**——报出的提升不可能被搜索过程自己灌水
- **probe 预检**——区分不了好/坏 patch 的评分器，在预算花出去之前就被拒绝
- **评分器冻结**——候选永远碰不到 `tests/`、`schemas/`、校验器或 rubric 本身
- **冻结 + 扩展区**——staged skill 包只读（`0444` + package hash）；进化产物落在 `skill-extensions/`
- **人工合入**——`sciforge submit` 只有在**全量 `ci_check` 门**通过后才把胜出 patch 落库；合入后校验失败会**自动回滚**（第一轮进化现场触发过）

```bash
sciforge evolve --workspace ./runs --proposes ./patches.json --budget 8 --algorithm puct
sciforge submit --workspace ./runs evo_123456   # 人工授权合入，全量 CI 门
sciforge daily  --workspace ./runs              # 纯文本日报（可推送任意渠道）
```


## Deepen 模式与 SCI 正文语域（v1.5.0 波次二）

- **`mode=deepen`** —— 第三种一等模式：在**不改创新点结构**（claim/贡献/方法身份冻结，违反=BLOCKED）的前提下，深度优化已有论文的**证据深度与实验公平性**（"刷 SOTA 但不调参"）。公平性清单（同算力预算、冻结数据划分、种子策略、超参预算对等、指标定义一致、效应量+CI 入表、多重比较校正）由 `scripts/fairness_gate.py` 机器检查 → 注册 verdict `FAIRNESS.json`（第 22 个）。
- **SCI 正文语域**（writing-principles §0.6）—— 正文面向科学读者而非审稿人：**零道歉、零防御**；hedge 仅允许带界的精确语句；Limitations 是 regime 账本不是忏悔。`leakage_scan.py` class K 机器强制（正文段零容忍）。
- **DeepMind 模式融合**（docs/DEEPMIND_FUSION.md）—— 级联多评估器进化（AlphaEvolve）、生成-验证-强化（AlphaProof）、主动学习回流（GNoME）、神经-符号分工（AlphaGeometry）。
- **Claude Code 无缝接入**：安装轻量 `sciforge` skill 适配器（`~/.claude/skills/sciforge/`）+ `CLAUDE.md` 项目记忆——在 Claude Code 内直接 `/sciforge` 或 `/auto-pipeline`。

## 安装指南

> **v1.4.0**：文献先行 gap 链（idea 锚定文献空白）、证据门槛领域学习、`.sciforge/` 双层工作区（RUNSTATE 长续航恢复 + 路由感知 N/A verdict）。纯 Skill 包 + 可选工具链。skill 本身是纯 Markdown，任何能读 Markdown 的 AI agent 直接消费；但完整跑通（图/文献/编译/实验）需要可选工具链，见下文「工具链（可选但推荐）」。

### 方式一：克隆仓库（推荐，标准 skill 集成）

```bash
git clone https://gitcode.com/GewisLab/SciForge-OSS.git
cd SciForge-OSS
```

然后在 AI agent（Claude Code / Cursor / Trae / Codex 等）中打开项目目录，agent 会自动读取 `AGENT_GUIDE.md` 作为入口。skill 文件本身无需安装、无需编译、无依赖管理。

### 方式二：npm 全局安装（`sciforge` 命令，已发布）

包已发布到 npm registry：`@gewislab/sciforge-oss`——这样就装好了：

```bash
npm install -g @gewislab/sciforge-oss

sciforge --help          # 安装完成——sciforge 命令全局可用
```

第 3 步——检查可选工具链（按需安装）：

```bash
sciforge tools-check     # 检查可选工具链是否齐全（见下文）
sciforge tools-install   # 一键安装可选工具链（apt: texlive/d2/rsvg-convert/inkscape/graphviz；npm: svgo）
```

初始化项目骨架：

```bash
sciforge init ./my-research   # 在指定目录初始化一个 SciForge 项目骨架
```

`package.json` 的 `bin` 字段注册 `sciforge` 命令指向 `./bin/sciforge.js`；`files` 字段声明分发内容（`skills/` + `AGENT_GUIDE.md` + 根 `SKILL.md` + `bin/`）。CLI 无外部依赖（纯 Node stdlib）。

> 更想本地 checkout？克隆仓库后在根目录运行 `node bin/sciforge.js --help`（见方式一）——命令相同，无需 npm 安装。

若不想用 npm，可直接 clone 后用 `bin/sciforge.js`（无外部依赖，纯 Node stdlib）：

```bash
git clone https://github.com/hackerjackL/SciForge-OSS.git
cd SciForge-OSS

# 直接用 node 调 bin（无需安装）
node bin/sciforge.js --help
node bin/sciforge.js tools-check
node bin/sciforge.js init ./my-research

# 或 npm link 从这个 clone 注册全局命令
npm link
sciforge --help
```

`package.json` 的 `bin` 字段注册 `sciforge` 命令指向 `./bin/sciforge.js`；`files` 字段声明分发内容（`skills/` + `AGENT_GUIDE.md` + 根 `SKILL.md` + `bin/`）。scoped 名 `@gewislab/sciforge-oss` 表示 npm registry 上该包归属 `gewislab` 组织。

### 方式四：将技能文件加入已有研究项目

```bash
cp -r SciForge-OSS/skills/ /your-project/
cp SciForge-OSS/AGENT_GUIDE.md /your-project/
```

### AI agent 配置

#### Claude Code / Codex / Cursor / Trae

```bash
cd SciForge-OSS        # 或 npm init 后的项目目录
claude                  # 或 codex / cursor / trae
# 然后直接输入：
/auto-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
# 或测试模式（bypass 人类 checkpoint，agent 自跑全程）：
/auto-pipeline "你的问题" — test_mode=true
```

#### 其他 AI agent

任何支持 Markdown 上下文或自定义技能集的 AI agent 均可：将 `AGENT_GUIDE.md` 提供给 agent 作为系统提示/初始上下文，agent 读取后会自动理解 21-phase DAG 循环和所有可用 skill，直接输入 `/auto-pipeline "你的科学问题"` 即可启动。

### 工具链（可选但推荐——完整跑通需要）

skill 本身是纯 Markdown，但完整跑通（图渲染 / 文献检索 / LaTeX 编译 / 实验执行）需要以下可选工具。`sciforge tools-check` 检查缺失项，`sciforge tools-install` 一键安装。Python 侧集中在仓库根目录一个文件：`pip install -r requirements.txt`（core: matplotlib/numpy/Pillow；recommended: SciencePlots）。跨平台"武器库"总表（d2/texlive/rsvg… 逐系统命令）见 [scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md)。

> 📊 **绘图工具链**：所有图（数据图、架构/流程/机制/组图——全领域通用）都通过唯一入口 `scripts/plotting/render_figure.py` 产出（15 引擎（含声明式 recipe 与方法图模板引擎）：matplotlib / d2 / graphviz / tikz / asymptote / typst / diagrams / blockdiag 家族 / mermaid / pikchr / 手工装配 SVG / composite 组图——单一链路，禁止并行工具；PDF+SVG 双产出 + 内嵌 Nature 级审计）。**跨平台：Linux / macOS / Windows 均支持**（Windows 推荐 WSL2；字体按平台自动发现，无机器专属路径）。完整依赖清单、逐系统安装命令、国内镜像、字体与不采用工具评估：**[scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md)**。环境自检：`python scripts/plotting/render_figure.py --doctor`。

| 工具 | 用途 | 安装 | 必需性 |
|------|------|------|--------|
| **Python 3.10+** | 数据图、SymPy 推导、实验脚本 | 系统自带或 conda | 必需（核心计算） |
| **texlive (pdflatex/latexmk/bibtex)** | Phase 13 零警告 PDF 编译 | `apt install texlive-latex-base texlive-latex-extra texlive-science texlive-publishers texlive-bibtex-extra texlive-lang-chinese latexmk` | 必需（论文编译） |
| **d2** (v0.7+) | 复杂架构/流程/拓扑图（headless-native，主用） | `curl -fsSL https://d2lang.com/install.sh \| sh -s --` | 推荐（图） |
| **graphviz/dot** | 密集网络/依赖图（d2 兜底） | `apt install graphviz` | 推荐（图兜底） |
| **rsvg-convert** (librsvg) | SVG → PDF 转换（d2/graphviz 输出转交付格式） | `apt install librsvg2-bin` | 推荐（图双产出） |
| **inkscape** | rsvg-convert 兜底（SVG→PDF） | `apt install inkscape` | 可选（图兜底） |
| **svgo** | SVG 优化（减小中间文件） | `npm install -g svgo` | 可选（图优化） |
| **mihomo** (或任意 HTTP/SOCKS5 代理) | Phase 4 文献检索访问 arxiv/s2/crossref/openalex/huggingface | 见 [mihomo 文档](https://wiki.metacubex.one/)，规则模式 `mode: rule`，`mixed-port: 8099` | 必需（文献检索，CN 环境直连 arxiv 会超时） |
| **PyTorch** (可选) | ML/深度学习实验（CPU/GPU/NPU） | `pip install torch` 或 conda | 可选（仅 ML 问题；CPU/GPU 自动检测） |

**GPU/NPU**：SciForge 自动检测（experiment-execution Step 0a）——`nvidia-smi`(cuda) / `rocminfo`(rocm) / `npu-smi`(npu) / `torch.backends.mps`(Apple Silicon)，缺 GPU 自动回退 CPU + WARN，不阻塞。never hardcode `.cuda()`。

**为什么不用 drawio / blender**：drawio-desktop 是 GUI 应用，非 headless 友好；Blender 无头渲染黑屏问题无法可靠修复。mermaid-cli (`mmdc`) 已集成（root 下自动 `--no-sandbox`）；pikchr、resvg、cairosvg 也已接入。完整引擎清单与评估记录：[scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md)。如人类后续想用 drawio GUI 手改图，可导入 d2/dot 产出的 SVG，但管线本身只用 headless 工具。

### mihomo 代理配置（文献检索必需）

Phase 4 universal-retrieval 通过 mihomo 规则模式访问外网。配置示例（`~/.config/mihomo/config.yaml`）：

```yaml
mixed-port: 8099          # HTTP + SOCKS5
mode: rule                # 规则模式（CN 直连，外网走代理）
# 节点列表 + 代理组略，按你的 VPN 配置
```

启动后，所有 arxiv/s2/crossref/openalex/huggingface/github 请求自动走代理。skill 内 `universal-retrieval` 已内置 `http_proxy=http://127.0.0.1:8099` 契约。超时则 `nohup` 后台重试，不跳 Phase 4。

### 验证安装

完成后，在 AI agent 中测试：

```
/auto-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
```

如果 agent 正确识别并启动了 21-phase 研究流程，说明安装成功。

## 架构：DAG 驱动的科研闭环

SciForge-OSS 采用 **DAG（有向无环图）** 架构，而非简单的线性管线。这是整个框架最核心的"show"：

```
                    ┌→ Idea 1 (theoretical)   ─┐
                    │                           │
Problem → Discover ─┼→ Idea 2 (computational) ─┼→ MCTS 4 轮迭代 (UCB1 选择 × expand × rollout × backprop)
                    │                           │   ↓ 每轮淘汰弱 idea
                    └→ Idea 3 (qualitative)   ─┘   ↓
                                                  survivors
                                                     │
                                                     ▼
                                              Phase 2.5: adversarial-falsification (证伪门控)
                                                  ↓ 假设评分 + 反例构造 + 文献对抗
                                                  ↓ falsified ideas eliminated
                                                     │
                                                     ▼
                                              Phase 3: novelty-check (3 维门控)
                                                  ↓ 新颖性 × 可行性 × 相关性
                                                  ↓ only strongest idea survives
                                                     │
                                                     ▼
                                          Derive (Phase 6) → Verify (Phase 7-10)
                                                     │
                                                     ▼
                                          Write (Phase 12) → Review (Phase 14) → Output (Phase 16)
                                                     │
                                                     └→ DAG 可视化追踪 (refine-logs/IDEA_DAG.json)
```

### DAG 原理

1. **分支（Branch）**：从问题出发，并行生成 3 个不同方法论视角的 idea（理论/计算/定性）
2. **MCTS 迭代**：每个 idea 经 4 轮 MCTS 迭代（UCB1 选择 → expand → rollout → backprop），弱 idea 在迭代中被淘汰
3. **证伪门控（Falsification Gate, Phase 2.5）**：存活的 idea 接受 6 维度 adversarial-falsification 攻击（假设评分 + 反例构造 + 文献对抗 + 类比映射 + 沙盒可行性 + AI 工程落地），被证伪的 idea 淘汰。Phase 5b 同时产出 **AI 工程落地评估报告**，含 8 维子评分（Compute/Dev Cycle/Code Complexity/Repro Risk/Dependency/Capital/Temporal Maturity/Regulatory）和 AI 开发路线图
4. **新颖性门控（Novelty Gate, Phase 3）**：通过证伪的 idea 经 4 维评估（新颖性 × 0.45 + 可行性 × 0.25 + 相关性 × 0.15 + 工程落地 × 0.15），只有最优 idea 存活进入后续推导、验证、写作阶段
5. **追踪（Trace）**：整条链路的 DAG 结构保存在 `refine-logs/IDEA_DAG.json`，可生成 Mermaid 可视化

### 21 阶段 DAG 循环

```
Phase  0: 加载问题（冻结 Q-id — INV-G1 锚点）
Phase  1: 问题理解与分解（内置推理）
Phase  2: /idea-discovery [DAG 分支] — 3 视角 idea + MCTS 迭代
Phase  3: /novelty-check [DAG 门控] — 4 维评估 + 淘汰
    ─── Forced human checkpoint: pick the final idea ───
Phase  4: /universal-retrieval — 文献调研 + 3 层防幻觉
Phase  5: /method-registry — 方法绑定 + hash 锁 + 强制人类审批
    ─── Forced human checkpoint: approve the method registry ───
Phase  6: /theory-derivation — SymPy 符号推导 + 逐步机器验证
Phase  7: /leakage-audit — Type I 逻辑漏洞 + Type IV 逃逸审计
Phase  8: /logic-verification — 6 维度逻辑一致性审计
Phase  9: /invariant-check — INV-G1 问题锚点冻结验证
Phase 10: /result-to-claim — 3 保真度 claim 门控
Phase 11: /unified-plotting — 学术图表（可选，多巴胺色系 + Layer 2）
Phase 12: /paper-writing — elsarticle 单模板写作
Phase 13: /paper-compile — LaTeX 零警告零报错编译
Phase 14: /auto-review-loop — 跨模型评审 + kill-argument 反自欺
Phase 15: /citation-audit — 最终引用 3 层验证
Phase 16: 最终组装 + 产物归档
```

## 快速开始

AI agent 读取 `AGENT_GUIDE.md` 后，直接调用：

```
/auto-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
```

或手动逐步执行：

```
# 1. 创意生成（DAG 分支）
/idea-discovery "Q001: 宇宙的起源与演化" — num_ideas: 3

# 2. 新颖性验证（DAG 门控）
/novelty-check "Q001" — strictness: normal

# 3. 文献调研
/universal-retrieval "宇宙起源 暗物质" — max_papers: 20

# 4. 理论推导
/theory-derivation "从 Friedmann 方程推导宇宙演化" — mode: derive

# 5. 逻辑验证
/logic-verification "验证推导的逻辑一致性" — mode: full

# 6. 图表生成（可选）
/unified-plotting "绘制宇宙膨胀曲线" — format: svg

# 7. 论文写作
/paper-writing "基于研究成果撰写论文" — format: markdown

# 8. 跨模型评审
/auto-review-loop "评审论文" — difficulty: hard
```

## 项目结构

```
SciForge-OSS/
├── AGENT_GUIDE.md                          ← AI agent 入口（从这里开始读）
├── README.md                               ← 人类阅读
├── bin/sciforge.js                         ← CLI（init/tools-check/run/resume/approve/evolve/serve…→kernel）
├── kernel/                                 ← v1.5.0 runtime kernel（Python ≥3.10 纯 stdlib 控制面）
│   ├── config/phasegraph.json              ← 21-phase DAG 可执行配置（回路/门/预算）
│   ├── config/providers.json               ← 角色分档多后端路由
│   ├── config/evolve.json                  ← RSI 门阵列（CI + schema + golden）
│   └── sciforge/                           ← 状态机 pipeline · events state · gates · approvals · execution · providers · review 跨模型审稿 · evolve PUCT+MAP-Elites · skills_pack 冻结包 · daemon · golden · cli
├── skills/
│   ├── meta-skills/                        ← 8 个元技能
│   │   ├── dynamic-sandbox/SKILL.md        ← 计算沙盒（数值 sanity check，无 GPU）
│   │   ├── dynamic-tooling/SKILL.md        ← 工具制造
│   │   ├── universal-retrieval/SKILL.md    ← 学术检索 + 3 层防幻觉（6 源）
│   │   ├── unified-plotting/SKILL.md       ← 矢量图表渲染（多巴胺 + Layer 2 数据热图）
│   │   ├── idea-discovery/SKILL.md         ← [DAG] 多视角创意 + MCTS 迭代
│   │   ├── novelty-check/SKILL.md          ← [DAG] 新颖性验证+淘汰
│   │   ├── domain-learner/SKILL.md         ← 从文献学习领域签名（唯一写入方）
│   │   └── domain-signature/SKILL.md       ← 规则式签名提示（可选快路径）
│   ├── support/                            ← 17 个支持技能
│   │   ├── theory-derivation/SKILL.md      ← SymPy 推导 + 逐步机器验证
│   │   ├── logic-verification/SKILL.md     ← 6 维度逻辑审计（跨模型对抗）
│   │   ├── paper-writing/SKILL.md          ← 统一 elsarticle 模板写作
│   │   ├── paper-compile/SKILL.md          ← LaTeX 零警告零报错编译 + 反死循环阶梯
│   │   ├── method-registry/SKILL.md        ← 方法 registry + hash 锁 + 强制人类审批
│   │   ├── leakage-audit/SKILL.md          ← Type I 逻辑漏洞 + Type IV 逃逸审计（通用）
│   │   ├── invariant-check/SKILL.md        ← INV-G1 问题锚点冻结验证
│   │   ├── result-to-claim/SKILL.md        ← 3 保真度 claim 门控
│   │   ├── quality-gate/SKILL.md           ← 终极前置写作门（universal QF-G* + SD-G*）
│   │   ├── auto-review-loop/SKILL.md       ← 跨模型迭代评审 + kill-argument 反自欺
│   │   ├── citation-audit/SKILL.md         ← 最终 3 层引用防幻觉验证
│   │   ├── kill-argument/SKILL.md          ← 反自欺练习（kill your own argument）
│   │   ├── experiment-execution/SKILL.md   ← toy + full + 后台派发 + 安全门
│   │   ├── adversarial-falsification/SKILL.md ← Phase 2.5 对抗证伪
│   │   ├── publishability-score/SKILL.md   ← 6 维发表性终评
│   │   └── rebuttal/SKILL.md               ← 拒稿后逐点申诉信
│   ├── orchestrator/                       ← 1 个编排器
│   │   └ auto-pipeline/SKILL.md  ← 21 阶段 DAG 闭环（单题执行，含 Phase 5b 工程落地评估）
│   └── shared-references/                  ← 共享契约（学科无关）
│       ├── artifact-registry.md            ← 跨 skill 产物唯一登记处（SSoT）
│       ├── output-protocol.md              ← 工作区目录树唯一权威（verdicts/ 统一）
│       ├── schemas/                        ← 全部机读 verdict 的 JSON Schema
│       ├── idea-dag-schema.md              ← DAG 节点 schema
│       ├── mcts-search-protocol.md         ← MCTS 迭代协议（UCB1 + 有界轮次）
│       ├── multi-fidelity-evaluation.md    ← 3 保真度筛选
│       ├── citation-discipline.md          ← 3 层防幻觉引用验证协议
│       ├── assurance-contract.md           ← 6 态判定 schema（PASS/WARN/FAIL/...）
│       ├── venue-profiles.md              ← 单一统一 elsarticle 模板 spec
│       ├── venue-checklists.md            ← 单一通用 pre-submission checklist
│       ├── discipline-context.md          ← OSS 全领域契约（无学科分支）
│       ├── discipline-writing.md          ← 通用 section-by-section 写作指南
│       ├── color-themes.md                ← 多巴胺（Layer 1）+ viridis/magma/cividis（Layer 2）
│       ├── writing-principles.md           ← 学术写作风格指南
│       ├── output-manifest.md + output-versioning.md ← 产物结构 + 版本化
│       ├── reviewer-independence.md + reviewer-routing.md + review-tracing.md ← 跨模型评审契约
│       ├── effort-contract.md              ← effort level 定义（lite/balanced/max/beast）
│       ├── skill-config.md                 ← skill 元信息 schema
│       └ ... (其他通用契约)
├── scripts/
│   ├── plotting/                          ← 绘图工具链（单一入口）
│   │   ├── render_figure.py               ← 统一渲染器——15 引擎（含声明式 recipe 与方法图模板引擎）、一条链路、内嵌审计
│   │   ├── sciforge_style.py              ← 多巴胺设计 token（单一事实源）
│   │   ├── figure_audit.py                ← A1–A10 Nature 级审计（内嵌）
│   │   └── INSTALL.md                     ← 三平台复刻手册
│   ├── validate_verdicts.py               ← verdict JSON schema 校验器（纯 stdlib）
│   ├── security_scan.py                   ← agent 实验脚本派发前静态安全扫描
│   ├── ci_check.py                        ← CI 单一入口（断链/版本/plotting/测试）
│   └── verifiers/                         ← 外部产物校验器（评审台账、论文审计）
├── tests/                                 ← 300+ pytest 用例（色板/审计/校验器/e2e 冒烟/verifier）
├── fixtures/e2e_minimal/                  ← 最小端到端 fixture（toy 实验 + 完整 verdict 链）
├── .workflow/ci.yml                       ← AtomGit Actions CI（与 ci_check.py 同一门控）
└── [删除: templates/ 占位目录、discipline-templates/、experiment-*、plugin-router、wiki-helper、problems/ 题库]
```

## 质量门

管线由机器可校验的门控守护，而不是文字承诺。

| 门控 | 执行者 |
|------|--------|
| **Verdict Schema 强制** | 运行工作区 `.sciforge/verdicts/` 里每个机读 verdict 必须通过 `shared-references/schemas/*.schema.json` 校验——`scripts/validate_verdicts.py` 在每个 phase boundary 与收尾运行（拼错/漏字段会被拦截） |
| **运行预算总账** | `.sciforge/verdicts/RUN_BUDGET.json` 按 effort 档位约束墙钟 / API 成本 / PIVOT / BA 轮次；orchestrator 每个 boundary 记账，超限 BLOCKED 上报人类 |
| **KILL 人类检查点** | 杀掉 idea 前默认暂停等人类确认（`human_skip=true` 或 `kill_checkpoint=false` 才全自动） |
| **实验安全门** | agent 自写的全量实验脚本派发前先过 `scripts/security_scan.py`（凭证访问 / env 外泄 / 破坏性操作 / 未授权外发 → BLOCKED） |
| **图契约** | 统一渲染器 + 内嵌 A1–A10 Nature 级审计；组图交付真矢量 LaTeX 装配（`composite.tex`），栅格预览被审计降级标注 |
| **ScientistTwo 门（v1.7）** | `scripts/s2_ladder_gate.py` @6c（无严格全集提升不得晋级，engineer 轮 ≤2）· `scripts/s2_ablation_gate.py` @相位 10（5–6 计划、账本单调）· `scripts/s2_audit.py` @wrap-up（增益算术 + 划分纪律 + 方法↔代码对齐 ≥80%）——见 `skills/shared-references/s2-protocol.md` |
| **仓库 CI** | `scripts/ci_check.py`（AtomGit Actions + pre-commit）：md 断链扫描、全仓版本一致性、plotting `--doctor`、全量 pytest（含 e2e 冒烟 fixture） |

开发者快速自检：`python3 scripts/ci_check.py` · `python3 -m pytest tests/ -q` · `python3 scripts/plotting/render_figure.py --doctor`。

## 全领域支持

SciForge-OSS 不限定任何学科领域。以下仅为示例，而非限制：

| 领域大类 | 子领域示例 |
|---------|-----------|
| 理科 | 数学、物理、化学、生物、天文 |
| 工科 | 计算机、电子、机械、材料、光电、传感器 |
| 医学 | 基础医学、临床医学、药物发现、流行病学 |
| 地球科学 | 地质、海洋、大气、气候、环境 |
| 社会科学 | 经济学、教育学、心理学、社会学 |
| 交叉学科 | 复杂系统、网络科学、数据科学、AI for Science |

**核心机制**：框架不预设学科知识，所有领域特定的方法论、符号体系、验证标准均由 agent 运行时推理处理。详见 [`discipline-context.md`](skills/shared-references/discipline-context.md)。

## 验证路径：四路可选

每个问题的 `verification_type`（规范取值：`theory-only` | `computational` | `theory+experiment` | `qualitative`）决定验证路由与论文模式：

| verification_type | Phase 6b/6c（toy/full 实验门） | 论文模式 | 示例 |
|-------------------|-------------------------------|---------|------|
| `theory-only` | SKIP | 理论论文 | 纯数学证明、概念论证 |
| `computational` | MUST | 计算论文 | ML 消融、数值扫描 |
| `theory+experiment` | MUST | 混合论文 | 物理推导 + 数值验证 |
| `qualitative` | SKIP | 综述论文 | 文献分类/综合 |

判断依据：Phase 6 入口的 verification-routing 依据 domain signature 的 `evidence_type` 与问题可计算性信号做一次性路由决策（experiment-first 为默认，theory-only 为例外）。

## 核心设计原则

1. **纯 Skill 驱动** — 每个 skill 是一份 `.md` 方法论文档。没有 `.py` 脚本、没有 bash 代码块、没有 IDE 专属语法。任何能读 Markdown 的 agent 都能消费这些 skill。

2. **DAG 优于线性** — 多条 idea 并行探索，弱 idea 在门控处被淘汰，只有最强的存活。DAG 结构可追踪、可可视化。

3. **元技能优于学科技能** — 4 个通用元技能替代 74 个学科特定技能。系统处理任意科学问题，无需硬编码学科知识。

4. **计算优于知识** — 当 AI 不知道答案时，它推导出来。动态沙盒执行 AI 写的代码，而不是程序员预写的代码。

5. **防幻觉优先** — 每篇引用通过 3 个独立学术 API（arXiv + CrossRef + Semantic Scholar）验证。没有论文凭记忆捏造。

6. **结构化自评审** — 评审使用角色切换模式（研究者→评审者→裁决者），无需跨模型协作。

7. **可复现** — 每次计算、推导和图表都保留为可执行代码 + 输入数据，而不仅仅是输出文本。

## 多领域示例

以下是 SciForge-OSS 在不同领域的应用示例：

### 物理学
```
/auto-pipeline "Q001: 宇宙的起源与演化" — effort: max, language: chinese
```
→ 输出：宇宙学理论推导 + ΛCDM 模型验证

### 数学
```
/auto-pipeline "证明：对于任意 n≥3，不存在正整数解满足 x^n + y^n = z^n"
```
→ 输出：Fermat 大定理的初等证明思路 + 文献综述

### 经济学
```
/auto-pipeline "Analyze: general equilibrium under incomplete markets"
```
→ 输出：一般均衡存在性证明 + 数值验证

### 教育学
```
/auto-pipeline "研究：基于认知负荷理论的教学设计优化"
```
→ 输出：理论模型 + 逻辑验证 + 实验设计建议

### 材料科学
```
/auto-pipeline "Predict: band structure of MoS2 under strain"
```
→ 输出：能带结构推导 + 数值验证

### 医学
```
/auto-pipeline "Study: AI-driven drug discovery for Alzheimer's disease"
```
→ 输出：药物靶点识别 + 分子动力学模拟验证

## 绘图工具链

出版级图表由**唯一入口** `scripts/plotting/render_figure.py` 产出（管线 Phase 11），**15 引擎（含声明式 recipe 与方法图模板引擎）收敛一条链路**（禁止并行工具）：matplotlib（数据图）、d2、graphviz、TikZ、Asymptote、Typst、diagrams、blockdiag 家族、mermaid、pikchr、手工装配 SVG、**composite 组图引擎**（Nature 风格 (a)(b)(c)… 面板编号，面板数硬上限 9，SCI 一区组版规范）。

- **双产出**：矢量 PDF（LaTeX 嵌入）+ SVG（agent 审阅/编辑）
- **内嵌 Nature 级审计（A1–A10）**：可读性下限、多巴胺色板（C* ≥ 30 + 两两色盲 ΔE ≥ 15 数值校验）、16:9 默认、复杂度下限（图标密度/边密度）、视觉丰富度、**品牌泄露守卫**（图是论文插图，不是工具海报）、**文字零重叠**（附精确偏移修正建议）
- **两级视觉审阅**：具备原生视觉的宿主 agent 按 9 项清单自审 PNG（零外部 API——宿主自身的视觉能力就是审阅者）；纯文本宿主降级机械审计
- **期刊宽度预设**：`--width-preset nature-single|aaai-double|...`（14 种版面）
- **跨平台**：Linux / macOS / Windows——字体按平台自动发现、无机器专属路径；见 [scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md)

## 致谢

SciForge-OSS 的完成离不开以下贡献，谨此致以诚挚谢意：

- **Luo H. W.**（GewisLab 负责人）——项目发起、核心研究思路与整体架构设计。
- **Yang J. T.**——主要开发者，负责框架的实现与工程落地。
- **Yang J. T.、Lu Y. H.、Li L. S.、Jia W. H.、Qiu Y. M.、Zhang W. B.、Wang C. Y.、Fan L. X.、Zhao J.**（排名不分先后）——慷慨提供计算资源（API token）支持，支撑本仓库持续的自迭代、优化与维护。

同时感谢所有通过 issue 与 pull request 改进 SciForge-OSS 的贡献者。

## 许可证

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)。个人及非商用用途（科研、学习、教育、公益等）免费；商用用途需向 GewisLab 购买商业授权。

## Star 增长趋势

![Stargazers over time](https://atomgit.com/GewisLab/SciForge-OSS/starcharts.svg?variant=adaptive)

---

**SciForge-OSS — AI for Scientist Anything**