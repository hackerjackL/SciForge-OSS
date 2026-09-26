# SciForge v1.6.0 候选池分析（深度全面版 · 仅分析不改代码）

> 分析日期：2026-09-26 ｜ 基线：v1.5.0（338/338 测试绿，tag 已打，HEAD 8f57ddc）
> 方法：① 本地仓库"契约承诺 vs kernel 实现"差距审计 ② 5 路并行开源调研（自我改进agent / 实验工程agent / 文献检索新势力 / 形式化验证+科学工具+benchmark / sciencediscovery 未吸收模式）
> 状态：**候选池 A、B 已定（本地实证）；候选池 C 待外部调研回填**

---

## 候选池 A⁰：verdict 生产责任甄别（修正认知，防误债）

22 个注册 verdict 的实测分布：kernel 有生成路径 12 个；其余 10 个由宿主 agent 填写。**但这不是 10 个欠债**——按"orchestrator is structural, not substantive"设计原则，审计内容类（PROOF_AUDIT / LOGIC_VERIFICATION / LEAKAGE_AUDIT / PAPER_CLAIM_AUDIT / BLINDSPOT_CHECK / EVALUATION_REVIEW / REVIEW_LEDGER / PUBLISHABILITY_SCORE 的叙事部分）**本就该由做研究的宿主产出、kernel 只做 schema+hash 校验**。真正的欠债只有 2 个：

- **INVARIANT_CHECK**：INV-G1 是 kernel 自己 hash 比对的结果，kernel 却没写这个 verdict 文件（应 `_native` 生产，宿主填反而违背"结构不变量归 kernel"原则）
- **KILL_ARGUMENT**：KILL/BA 路由是 kernel 的 loopback 决策，应由 kernel 落 `KILL_ARGUMENT.json` 骨架（reason_code+trace），宿主补论证细节

其余 8 个 = 设计正确的职责分工，v1.6 不要"顺手代码化"它们（会破坏 kernel 不懂科学的原则）。

## 候选池 A：我们自己"承诺了但没代码化"的欠债（最高优先，零调研依赖）

这些是 SciForge 技能库里**写了契约、kernel 却 0 实现**的核心机制。它们不是"新功能"，是"已声称的能力没兑现"——补齐即提升可信度，且挂接点清晰。

| # | 机制 | 现状证据 | 应做成什么 | 工程量 | 收益 |
|---|---|---|---|---|---|
| A1 | **TDAL 四维联合置信**（ouroboros-integration.md） | 6 个 skill 文件引用，`grep ouroboros kernel/ = 0` | result-to-claim 阶段代码化 T×D×A×L 联合公式，产出 `TDAL.json` 注册 verdict；D 维吃 Ouroboros/数据核查、T 维吃 SymPy+逻辑+证伪 | M | 把"信心"从 prose 变可审计数字 |
| A2 | **fantasy-prevention 5 门** | 自称"最重要质量门"，6 文件，kernel 0 | 机械门：每 claim 必须命中{推导链∨引用∨显式假设∨反例检查∨数据可得}之一，否则 FAIL `fantasy_claim` | S | 直接落地我们自己的"反幻想"纲领 |
| A3 | **SMOKE 全代码冒烟门** | v3.4 声明 `.SMOKE.json`，kernel 无 | Phase 6c 后真跑一遍 `src/` 脚本（沙箱内、限时），无 traceback 才放行——现只 security_scan 静态 | S | 堵"代码写了没跑过" |
| A4 | **multi-fidelity 三档判定** | 契约5文件，prose-only | Low/Mid/High 保真阶梯做成 verdict 字段+门，非纯文字 | M | claim 强度可机器校验 |
| A5 | **rebuttal 返修闭环** | 9 文件技能，kernel 0、非 phase | 可选后置 phase：投稿被拒→审稿意见→REVISION_PLAN→scoped 修订→重编译，复用 L10 环 | L | 打通"投稿后"，竞品无 |
| A6 | **blindspot / venue-profiles 机械门** | 有 schema 无 kernel 接线 | 领域专家盲点检查、目标会场清单做成门 | S | 低垂果实 |

**判定**：A1–A4、A6 是"补自己的债"，优先级高于任何外部新特性——因为 v1.5 的卖点是"契约即门"，这些没兑现就是空头支票。

---

## 候选池 B：结构加固与边界记档（本次决策留痕）

| # | 项 | 说明 | 处置建议 |
|---|---|---|---|
| B1 | **verifier/*.sh 裸调 python3** | Xcode shim 被重置时会挂（本会话实测 7 项挂过）；Linux/新机同样脆弱 | 脚本头加解释器探测：`command -v python3 || uv run python || ~/.local/bin/uv run python` 兜底 |
| B2 | **colab-mcp 仅 cc-haha 层** | 本次用户决策：先只做 cc-haha MCP，不进 sciforge kernel | 记档。kernel 侧未来加 `dispatch_backend=colab-ssh` 附着模式（含 budget-hook 关机） |
| B3 | **AutoDL 集成** | 已设计（开机API/ssh跑torch/花费HITL检查点），用户决定暂缓 | 记档待用。比 Colab 更适合 headless 过夜；充值/开机需人类批准 |
| B4 | **发布通道** | remote=atomgit/GewisLab，本地 1.6 未 push | 定版后再推；GitHub 镜像可并行 |
| B5 | **⚠️ 安全门/实验沙箱在 kernel 主循环未接线**（本轮审计最重发现） | 硬证据：`pipeline.py` **0 import execution.py**；`commit_boundary` **0 消费 phasegraph 的 `boundary_gates` 段**（该段白纸黑字写 `security_scan.when=[6b,6c]`）。6b/6c 真实只挂 `verdict_field` RESULT/STATUS 门 | README 卖点"agent 实验脚本 dispatch 前强制 security_scan（BLOCKED）"当前**靠宿主自觉、非 kernel 强制**；DEMO-RK4 里 security_scan 是宿主手跑的。**需你定性**：若"实验执行本就委托宿主沙箱"=设计边界（则 README 措辞应改），若要 kernel 强制=接线债（execution.dispatch + boundary_gates 需接进 commit_boundary，工程量 S-M）。二者必择一，不能都现状 |

---

## 候选池 C：外部开源可融入的新能力（五路调研已回填，数据 2026-09-26 实测）

### C 池核心发现：四路独立调研出现**收敛信号**——同一靶点被多方指向，即为最高优先

| 收敛靶点 | 独立指向它的调研路 | 我们的现状缺口 |
|---|---|---|
| **① claim 级证据核查**（"引用真实但没说过这话"） | C-3 PaperQA 句级归因（第4层）+ C-5 SciDis E0–E4 证据分级门禁（locator 强制、不足自动降级 INCONCLUSIVE） | 3 层核查只验存在性/元数据；gap_gate 查不出此漏洞。**v1.6 头号增量** |
| **② 公平性从"自报"升级为"可验证"** | C-2 DVC(划分哈希锁定)+conda-lock(环境sha256)+codecarbon(kWh实测) + C-4 python-flint Arb(数值点值→认证区间) | FAIRNESS.json 目前靠宿主申报，无字节级证明 |
| **③ 评估级联完备化** | C-1 OpenEvolve/ShinkaEvolve(便宜门先筛→昂贵评估后置) + C-5 E-gate | 我们的 HybridDomain 已做一半(gate→research→judge)，可升级为全管线级联：SMOKE→机械门→区间验证→审稿团(省数倍审稿token) |
| **④ 运行时防御** | C-5 注入消毒(外部文本转义,我们全裸)+限速器429冷却(我们刚亲历Google 429!) +C-5 双计时器(审批等待不应耗超时——我们blocked语义正缺) | 低成本高防御，全是 S 级 |

### C 池候选清单（按挂接点归位，★=建议进 v1.6）

**C-进化引擎（RSI 层）**
- ★ **GEPA**（6,747★ MIT，2026-09-25 活跃，纯 Python 可 vendor）：trace→自然语言反思→变异→Pareto 保全，省 ~35× rollout。补我们"文本变异纯靠 prompt"的算法化缺口
- **EvoScientist AutoSkills 模式**（5,023★ Apache，今日发版）：从失败记忆蒸馏**新候选 skill**→人工审核。与我们的 LESSONS+approvals 天然契合（v1.6 可做半自动：提案不自动合入）
- **DGM archive 谱系**（2,373★）：补丁必须回放历史任务胜出才保留——我们 golden set 已有雏形，补"谱系记录"
- ShinkaEvolve 采样高效版思想（同厂血脉，机制参考）

**C-实验链（6b/6c/FAIRNESS 层）**
- ★ **DVC+conda-lock+codecarbon 三件套**（全 S 级）：split哈希锁进 FAIRNESS、环境锁、能耗实测入公平性账本与论文能耗声明
- **Optuna TPE+MedianPruner**（14,8k★ MIT）：同预算砍 trial，省下的算力记入公平性账本（pruner 预算化 = 公平性首次与超参搜索闭环）
- **AIDE 解空间树搜索**（1,5k★ MIT）：实验方案多草稿/调试/改进树，token 成本高→作 Colab 后端灰度特性（v1.6 可选实验项）
- **DoWhy refutation tests**（8,3k★）：因果声明自动反驳（placebo/随机共因/子集），通过率入质量门——我们证伪 battery 的升级形态
- SWE-agent ACI 思想：给 colab/ssh 后端封 6-8 个原子工具（配合 B2/B3 未来做）

**C-文献链（4/4broad/15 层）**
- ★ **句级归因门（第 4 层核查）**：sentence→[@key]→摘要蕴含检查，不蕴含判 WEAK_CITE（PaperQA 机制，纯 API+提示词，S 级）——直击引用链最后缺口
- ★ **S2 引用滚雪球**（前向/后向 2 跳+共引排序）：补**召回**短板（现有链全在验精度），零新依赖，S 级
- **对比表结构判别**（AutoSurvey 机制，无 LICENSE 只取思想）：GAP_REPORT 强制对比表，gap 从空单元格推出——把 gap_gate 的词汇判别升级为结构判别
- STORM 视角枚举（只取"视角提问"子模块逼盲区，可 L 级缓做）

**C-可验证性层（6a/8/10 层）**
- ★ **python-flint Arb 区间算术**（MIT，pip 即装）：数值 verdict 加 `arb_bound` 字段，实验数字获得可认证误差界——当天可挂
- ★ **unsorry 协议移植**（零依赖纯机制）：公理足迹审计（我们 schema 只验结构不验假设引入）+ 形式化忠实性双翻译 diff（"语句是否忠实于自然语言命题"这一盲区分析直接写进理论推导门条件）
- **PySR 符号回归**（3,777★）：数据→公式正向通道接 SymPy 闭环——我们理论推导缺的方向（假设生成升级）
- **PyPantograph+Lean4 门**（M-L 级）：`lean_proof_verdict.json`（lake build+sorry拒绝+公理白名单），疑难命题进内核终检。价值最高但工程最重——v1.6 做**接口预留**（schema+phasegraph 挂载点），实现排 v1.7
- MLR-Bench"捏造结果"对抗协议（36★ NeurIPS'25）：给负结果纪律+审计 phase 现成测试集
- diffrax 梯度一致性软门（JAX 生态，观望）

**C-SciDis 未吸收模式（kernel 工程层）**
- ★ **E0–E4 证据分级门禁**：评审/审计结论必须带网关签发 locator，不足强制降级——与句级归因合并成"可验证证据链"一个工程
- ★ **外部内容注入消毒**：远程文本 HTML-escape+权威标签 denylist（drift test 同步）——我们大量消费网页/PDF，当前裸奔（S 级）
- ★ **键控限速器+429 全局冷却**（Retry-After 保留）：文献检索 pacing——本会话亲历 Google 25万token/min 429，教训直接变设计
- **双计时器**：runIdleTimeout 与总超时分离 + `begin_external_wait()`（审批等待扣除外耗，blocked 是我们常态）
- **审批串行队列+allow_matching**：消并发批准竞态；"允许同类"可复用 Grant
- CAS 双池内容寻址（S-M）：产物字节级不可变——与 PROBLEM_HASH 思路同源，升级
- trajectory 序号连续性断言（EventLog 小补丁）

### 候选池 C 明确"不适用/跳过"
- 通义 DeepResearch/open_deep_research/WebThinker（agent 训练型+静态 DAG 冲突大，边际低）；AISR/Connected Papers/MLE-STAR 官方无开源（实测确认）；OpenHands 整框架引入过重（事件流我们已有）；Nix（陡）；Sakana 代码（license 禁复用，只取机制）；K-Dense（根目录无 LICENSE，合规未确认）；SciDis 多租户凭据/代理注册表（单用户本地无需求）

---

## v1.6.0 定版判断（综合 A⁰/A/B/C）

**版本主题建议：「证据链闭环」——v1.5 让契约变成门，v1.6 让证据变成可验证的。**

叙事逻辑：契约(Markdown) → 门(kernel 强制) → **证据(字节可验证+句级归因+区间数值)** → 进化(RSI 吃这些硬信号)。每环都对应真实缺口与收敛调研信号，且大部分是 S 级工程量。

### Top 12 定版清单（按 ROI 排序，纯分析未动）

| # | 项 | 来源 | 级 | 一句话收益 |
|---|---|---|---|---|
| 1 | B5 定性+接线（security_scan/boundary_gates 进 commit_boundary） | 本地审计 | S-M | 核心卖点的诚实性，不修就是空头支票 |
| 2 | 句级归因门 E4-lite（claim→引用蕴含检查，新 verdict `CITATION_SUPPORT.json`） | C-3+C-5 收敛★ | S-M | 消灭"引了但没说过"，引用链补最后缺口 |
| 3 | FAIRNESS 可验证三件套：DVC split 哈希 + conda-lock 环境锁 + codecarbon 能耗 | C-2 收敛★ | S | 公平性从自报变证明，投稿加分项 |
| 4 | Arb 区间数值门（python-flint，verdict 加 arb_bound） | C-4 收敛★ | S | 数字带认证误差界 |
| 5 | 检索限速器+429 冷却+注入消毒 | C-5 收敛★ | S | 运行时防御，本会话两个教训直接变设计 |
| 6 | TDAL 四维置信代码化（A1，`TDAL.json` 注册 verdict） | 本地欠债 | M | "信心"变可审计数字，喂审稿团 |
| 7 | GEPA 接入 evolve 变异引擎（vendor MIT 纯 Py） | C-1★ | M | 进化样本效率质变，RSI 大版本主题 |
| 8 | fantasy-prevention 5 门机械码化（A2）+ SMOKE 冒烟门（A3） | 本地欠债 | S | 自称"最重要门"落地；堵"代码没跑过" |
| 9 | S2 滚雪球检索（补召回，零新依赖） | C-3★ | S | gap 证据基础加固 |
| 10 | 双计时器+审批等待暂停+审批队列串行化 | C-5 | S | blocked 常态的正确超时语义 |
| 11 | unsorry 协议移植（公理审计+双翻译 diff 门条件）+ INVARIANT_CHECK/KILL_ARGUMENT kernel 生产 | C-4+A⁰ | S | 两个验证盲区补上+结构不变量归位 |
| 12 | Lean 门**接口预留**（schema+挂载点，实现 v1.7）；PySR 数据→公式通道 | C-4 | M | 不欠技术债地占住数学级 sound 路径 |

**明确不进 v1.6**：AIDE 树搜索（灰度另议）、AutoSkills 全自动蒸馏（与 HITL 原则冲突，只做到提案）、Lean 完整实现（工程量 L）、STORM 全量、任何 LLM 训练型方案。

### 收口核对（定版前硬条件）
- 338 测试基线不动 + 每个新 verdict 注册 schema 并进 golden 电池（进化选择压力同步扩容）
- ci_check 全绿；verifier 解释器探测（B1）顺手修
- README"security_scan 强制"表述与实际接线一致后才可发布（防"文档先行"复现）
