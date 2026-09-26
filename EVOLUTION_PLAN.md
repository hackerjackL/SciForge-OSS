# SciForge 超级迭代作战计划 — v1.5.0（30 项大重构定版映射）

> 性质变更声明：SciForge-OSS 从"纯 Skill 包"升级为 **Skill 驱动的研究运行时**（Runtime Kernel + Skill Library + RSI Evolution）。技能库依旧纯 Markdown、可被任何 agent 直读；新增 `kernel/` 提供代码级控制循环。无 UI——通过 `sciforge run` CLI + claude/codex 宿主适配器使用。
> 吸取对象：ScienceDiscovery(openJiuwen/华为: evolve sidecar、三 shard、评分冻结、probe、skill 冻结包+扩展区、run 状态机、NPU broker)、AI-Scientist v2(PUCT 树、worker 池、token 实测)、EvoScientist(6-agent、自演化 memory、serve/deploy、cron)、DeepScientist(事件可重放、quest-as-git、runner 委托)、STORM(逐角色模型分档、stage 开关断点续跑)、AgentLaboratory(报错历史注入勿重复、best_codes 精英池)。

| # | 超级优化项 | 吸取自 | 归属波次 |
|---|---|---|---|
| S01 | 代码状态机 kernel：21-phase 图从 prose 变为 `kernel/phasegraph.json`，循环由 Python 驱动 | SciDis native-agent / AI-Sci v2 agent_manager | W1 |
| S02 | events.ndjson 事件溯源 + RUNSTATE v2：崩溃→`interrupted`→自动从断点重放续跑 | SciDis events.ndjson + DeepScientist 事件可重放 | W1 |
| S03 | provider 层：anthropic/openai/ollama 多后端；角色分档(判分强模/粗活廉模)；重试退避；**真实 token 成本写入 RUN_BUDGET** | STORM 逐组件配置 + AI-Sci v2 track_token_usage | W1 |
| S04 | 门嵌入控制流：phase 转换=代码强制先跑 validate_verdicts/sciforge_audit/security_scan，不过则无法前进 | SciDis 控制面治理 / AI-Sci v2 baseline 判分 | W1 |
| S05 | HITL 代码化：checkpoint 落 PENDING_APPROVAL.json + run 标 blocked + 超时暂停；`sciforge approve/deny` | SciDis permission.required 状态机 | W1 |
| S06 | worker 池：toy/full 多 seed 并行、队列、STATUS.json 聚合 | AI-Sci v2 num_workers/num_seeds | W1 |
| S07 | 沙箱执行策略：macOS Seatbelt / Linux bwrap profile 生成 + allow-list（实验代码默认沙箱内跑） | SciDis sandbox-execution | W1 |
| S08 | claude/codex 宿主适配器：`sciforge run` 自动检测宿主，phase bundle→pointer-load 投喂→回收 verdict；纯 API provider 模式兜底 | DeepScientist runner 委托 | W1 |
| S09 | CLI 全体验：run/resume/status/approve/deny/evolve/gate/doctor/init 一个命令面 | EvoScientist CLI | W1 |
| S10 | 设备调度：detect_device 升格 kernel 侧 compute planner（cuda/rocm/npu/mps/cpu），NPU allowlist job 模式 | SciDis Ascend broker + 原 detect_device | W1 |
| S11 | evolve sidecar：kernel 内置搜索引擎——PUCT 精炼 + MAP-Elites 多岛（ring migration、ε-greedy、inspiration 变异）双算法，同一 Domain 接缝可换核 | SciDis puct_engine/openevolve_engine | W2 |
| S12 | 三分片防作弊：rollout/gate/test——test 分片搜索永不可见，最终报告数出自 held-out | SciDis 数据三分片 | W2 |
| S13 | 评分探针预检：进化开跑前 4 项判别力检查（好/坏分离、起点 headroom、重复稳定、错误可定位）；不过→拒绝开跑 | SciDis probe | W2 |
| S14 | skill 冻结包：SKILL.md 按 revision+package hash staged，run 内只读 0444；预留 skill-extensions 可写区 | SciDis progressive disclosure | W2 |
| S15 | skill 库 RSI 闭环：run 审计(LESSONS+events)→生成 SKILL.md patch 候选→evolve 搜索最优→人审合入 | 自研（吸取四家之长） | W2 |
| S16 | 不可触碰区：tests/、schemas/、validator、ci_check、LICENSE 硬编码为 frozen paths（评分器冻结） | SciDis scorer-frozen | W2 |
| S17 | 进化日报：每轮 evolve 输出日报文本，`sciforge report --out`（微信/邮件通道即插即用，暂本地） | 用户需求 | W2 |
| S18 | 经验向量检索：LESSONS.json 嵌入相似度索引（stdlib 哈希向量兜底），Phase 2/6b 检索作先验，`avoid` 硬排除 | SciDis science-memory + EvoScientist 图谱 | W2 |
| S19 | golden problem set：6 题固定回归基准（跨 4 verification_type），进化轮必须 ≥ 旧版拦截率/完整率 | 自研选择压力 | W2 |
| S20 | 多模型交叉审稿团：同一论文≥3 个不同 provider persona 独立盲审，schema 化 verdict，分歧→仲裁 | AI-Sci v2 评审循环 + CRUX 独立评审 | W3 |
| S21 | 跨模型仲裁：审稿分歧自动进入 adjudicator（第三强模）；kill-argument 交叉复核 | EvoScientist 多 agent | W3 |
| S22 | rebuttal→修订→再审迭代环：审稿意见→REVISION_PLAN→scoped 修订→重编译→再审，≤2 轮 | AgentLaboratory 递归 refine | W3 |
| S23 | 成本追踪：provider 层真实 usage(输入/输出/缓存)按 phase/role 聚合入 RUN_BUDGET，effort 契约自动换算 USD | STORM litellm 分档 | W3 |
| S24 | 文献层缓存+代理自动发现：verified-ref 本地 SQLite/JSON 缓存（7d TTL）；proxy auto-detect（mihomo/Clash Verge 端口扫描+env）替代写死 8099 | PaperQA2 缓存 + 现状痛点 | W3 |
| S25 | 图工具链 headless 完整性：render_figure 在缺 rsvg/inkscape 时用 pymupdf/resvg 兜底链重排；--doctor 升级为 kernel doctor 子项 | 现状实测 | W3 |
| S26 | LaTeX 泄漏扫描 v2：Class I 品牌泄漏 + AIGC 痕迹 + 管线词三簇正则入 sciforge_audit 机械门 | 原 v3.4 8-class | W3 |
| S27 | 检索质量门：GAP_REPORT 判别力检查（gap-id 必须引用可验证矛盾/空白 + 引用密度下限），防空洞 gap 驱动幻觉选题 | OpenScholar 自反馈 | W3 |
| S28 | 环境完全体：macOS pip venv(3.12) + TinyTeX + brew 工具链一键 `sciforge install --full`；requirements 分层重做含 kernel extras | SciDis start-stack 经验 | W4 |
| S29 | 三平台工程化：Docker headless 镜像、GitHub Actions 三平台 CI 矩阵、Linux bwrap、Windows WSL2 实测文档 | 用户目标 linux 无GUI | W4 |
| S30 | 文档定版：README(中英)/AGENT_GUIDE/CHANGELOG 1.5.0 定版重写——性质变更、新架构图、复现实验清单、30 项映射表；demo 实测记录 | 用户定版要求 | W4 |

## 硬约束（不变量）
- 技能库保持纯 Markdown 可独立消费（kernel 是第一个宿主，不是唯一宿主；Codex/Claude Code 直读模式保留）
- verdict schema 向后兼容；旧工作区可迁移
- 所有新增机械门必须模型无关（低能力模型漏跑=被门拦截，而非静默通过）
- 进化不可触碰区优先于任何进化提案


---

# 波次二（v1.5.0-w2）30 项续 — 同版本号，git 多提交

| # | 项 | 吸取自 | 状态 |
|---|---|---|---|
| S31 | SCI 正文语域硬门：零道歉零防御（§0.6 + class K 机器检测） | 用户要求 + Nature/Science 文风 | ✅ |
| S32 | hedge 带界规则（range/N/CI/regime），禁 apology sandwich | 同上 | ✅ |
| S33 | FAIRNESS.json 注册 verdict + fairness_gate.py（同预算/同划分/同种子/同超参/同指标） | MLE-bench 公平性原则 | ✅ |
| S34 | mode=deepen：创新点冻结 + 证据深度优化（功效/消融/稳健/多重比较/效应量+CI） | 用户"刷SOTA不调参"要求 | ✅ |
| S35 | DEEPEN_FREEZE.json 哈希锁：方法/claim 变异=BLOCKED | INV-G1 同构 | ✅ |
| S36 | 数字过期语义（numbers_stale）：公平性重跑前的表格数值作废 | 深化模式纪律 | ✅ |
| S37 | Limitations=regime ledger（3-6 条，边界+可观测后果+解决测量） | SCI 写作法 | ✅ |
| S38 | stance-first 段落序 + hedge 删除测试（claim 不得靠 hedge 站立） | §0.6 | ✅ |
| S39 | 级联多评估器（便宜门→科学诚信正则→LLM judge） | **AlphaEvolve** | ✅ |
| S40 | ResearchDomain 科学诚信硬零层（削弱纪律/审计/锚点的 patch 直接 0 分） | AlphaEvolve 反 reward-hacking | ✅ |
| S41 | 生成-验证-强化闭环：verified_proofs 仅 PASS 结果进下轮先验 | **AlphaProof** | ✅ |
| S42 | active-learning 回流：retrain_from_results → domain-signature | **GNoME** | ✅ |
| S43 | 神经-符号分工：LLM 出构造，SymPy/门严格验证 | **AlphaGeometry** | ✅ |
| S44 | 形式可验证性锚：22 个注册 verdict + validator 硬门 | AlphaProof/Geometry | ✅ |
| S45 | DeepMind 融合调研文档（6 项目映射表） | docs/DEEPMIND_FUSION.md | ✅ |
| S46 | baseline 对照强制 + 效应量/CI（GraphCast 管线启示入 method-registry） | GraphCast | ✅ |
| S47 | Claude Code skill 适配器（pointer-load，单一事实源） | 用户"无缝集成 claudecode" | ✅ |
| S48 | CLAUDE.md 项目记忆（硬规则/verdict 契约/gotcha） | Claude Code 惯例 | ✅ |
| S49 | 三个子代理角色：researcher/reviewer/experimenter | AI Co-Scientist 角色分解 | ✅ |
| S50 | kernel verdict JSON 契约写入 CLAUDE.md（宿主应答格式） | 实测经验 | ✅ |
| S51 | docs/agents/ 镜像（可移植，不绑家目录） | 工程化 | ✅ |
| S52 | REPRODUCE.md wave-2 复现命令集 | 可复现要求 | ✅ |
| S53 | CHANGELOG 波次二条目 | 定版要求 | ✅ |
| S54 | 单项测试：ResearchDomain 级联（含 judge 不可调用断言） | 测试纪律 | ✅ |
| S55 | 单项测试：fairness 不公/公平双路 | 同上 | ✅ |
| S56 | 单项测试：class K 道歉扫描 + verified_proofs PASS-only | 同上 | ✅ |
| S57 | deepen freeze 单测 + mode 参数遮蔽 bug 修复 | 实测发现 | ✅ |
| S58 | 闭环 demo：子代理加载项目全链跑 RK4 问题 + 逐相质量评分 | 用户核心要求 | ✅ 26 相均分 8.5，completed |
| S59 | demo 发现的 kernel bug 修复轮 | 闭环价值 | ✅ 8 bug 全修复+回归测试 |
| S60 | 最终 ci_check + 335 测试全绿 + 文档定版收尾 | 收尾 | ✅ 335/335 + OVERALL PASS + v1.5.0 tag |
