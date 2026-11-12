# Changelog

> **Historical naming note**: entries before v1.7.2 may say “21-phase”. The current executable topology is the 26-node DAG in `kernel/config/phasegraph.json`; entries below are preserved as written.

## [1.7.4] - 2026-11-11 定版：信任根加固 + 进化引擎接真 + 引用验证如实降级

> 版本主题：**v1.7.3 让门与磁盘证据对账，v1.7.4 让"信任根本身"不可伪造，并把两处仍是脚手架的卖点接成真货**。本轮清掉 v1.7.3 记档在案的全部高优先级债 + 一处实测发现的运行时阻塞。**基线 568 → 744 测试全绿，ci_check PASS，security_scan --self-test 26/26，fixture 严格校验 24/24**。方法：四个并行 agent（G–J）按零重叠文件所有权分工 + 统筹收口跨 agent 移交项。

### G. 事件日志哈希链 + run flags 不可变（治"agent 可自批不可协商的人工检查点"）

- **人工检查点此前可被一个字段绕过**：`_checkpoint_satisfied()` 从 `self.rs.data["flags"]` 读 `human_skip`/`test_mode`，而 RUNSTATE.json 是磁盘上普通可写 JSON——agent 改一个布尔值即可让 Phase 3→4（选 idea）与 Phase 5→6（批方法注册表）两个文档反复声明"non-negotiable"的检查点自动放行。**这是 v1.7.3 修"第二个检查点失效"时扩大的攻击面**（原先只有第一个检查点读该字段，修完一致性后两个都读）。
- 修法：`start()` 把 run 级 flags 冻结进 append-only 的 `run_started` 事件（`pipeline.py`），新增 `_run_flags()` **只读第一条** `run_started`（后追加的伪造副本无法覆盖）；`_checkpoint_satisfied()` / `kill_checkpoint()` 不再读 RUNSTATE 的 flags（快照仅留展示用途），判定用 `is True`。
- **事件日志加 sha256 链式哈希**（`state.py`）：每条事件带 `prev_hash`（首条为 GENESIS）+ `hash`（覆盖 seq/ts/phase/kind/payload/prev_hash 的规范化 sha256）。此前 `events.ndjson` 无任何完整性保护（hmac/hashlib 链式相关代码 0 处），而它是"权威状态重建来源"——loopback 预算、审批状态、flags 全从它重放，追加一行伪造的 `checkpoint_cleared` 即可凭空推进管线。
- `EventLog.verify_chain()` 返回 `{ok, legacy, total, broken_at, broken_seq, reason, head_hash}`；`replay(strict=True)` 抛 `EventChainError`；`recover()` **建状态前先验链**，断裂则 RUNSTATE 置 `paused_blocked` + `reason_code=event_log_integrity_broken`、返回新值 `integrity_broken`，`Kernel.start()` 抛 `DispatchError`。`open_checkpoint_requests()` 改为 fail-closed：链断时 clear/skip 证据本身不可信，所有已签发请求保持 open。
- **向后兼容**（项目硬约束"旧工作区可迁移"）：无链字段的旧日志判 `legacy=True, ok=True` 并照常续跑，新事件继续以 legacy 形状追加（绝不产生"legacy 前缀 + 链式后缀"的混合日志，那会被判断裂）；旧 `run_started` 无 flags 时 `_run_flags()` 返回 `{}` → `human_skip=false`，即**宁可让旧 run 多等一次人工确认，绝不默认放行**。torn write 保持 skip 并继续。
- **增量重放**（治每步 O(n) 全量重读）：EventLog 维护已解析列表 + 文件偏移 + 头部哈希，`replay()` 只读尾部新行而返回契约不变。处理截断（size < offset）、inode 替换、已消费前缀被原地改写（均回退全量重读）、torn 末行（跳过且不消费，后续补全仍能读到）、多实例各自独立偏移。实测 2000 事件日志 200 次 replay 共 4ms、0 次重复解析。
- **fixture 重新生成**：加链后 `fixtures/e2e_minimal/.sciforge/events.ndjson` 会变遗留格式，故用 `host="mock"` 真实 `Kernel` 跑完 26 节点重新生成（**非手写、非手工补哈希**）：168 事件、27 次 boundary_committed（26 节点 + L1 重入 2）、1 次 L1 loopback（target=2, rep_fallback=PASS）、两检查点各有 requested+cleared、链完整。
- 测试 +12（负向 5：RUNSTATE 篡改 ×2、伪造 `checkpoint_cleared` ×2、中间事件 payload 篡改 ×1；正向/兼容/性能 7）。**统筹实测伪造攻击**：断链 + 追加伪造 cleared/skipped 后 `approvals_pending` 仍 True、`_checkpoint_satisfied` 仍 False、`recover()` 返回 `integrity_broken`；对照真人 `decide(approve)` 仍正常放行。
- 未引入 HMAC/密钥：威胁模型是同 uid（agent 与内核同用户），sha256 链防的是低成本追加伪造并使篡改可检测；**整文件重算哈希不在防护范围**（需密钥才能防），已在模块内注明。

### H. 评审面板独立性机械披露（治"跨模型审稿团实为同模型三次采样"）

- **缺陷**：`review.py` 的 `_default_personas()` 三个人格（methods/novelty/repro hawk）全部 `role:"review"`，而 `providers.json` 里 review/adjudication/grading **三个角色都指向 anthropic/claude-opus-4-8** → 所谓"3 个不同 provider 的独立盲审"实际是同一模型带三种 bias 提示词采样三次，"分歧时由不同模型仲裁"也是同模型自裁。`review.py` 文件 docstring 承诺的 "DIFFERENT backends/models" 无任何机械保证，也无任何地方披露这个事实。
- 为什么严重：独立性是这套机制的全部价值来源。同模型三次采样的 variance 反映采样噪声而非真实审稿分歧，而 `reviewloop.py` 用分数阈值 8 触发 rebuttal、`adjudicate()` 用 `spread >= 4` 触发仲裁——两个判据在同模型情形下统计含义完全不同，下游 `submission_ready` 又引用评审分。
- 修法：新增公开函数 `panel_independence(providers, personas)`，逐 persona 解析实际 `(backend, model)`（优先 `Providers.model_for()` 含 `SCIFORGE_MODEL` 覆盖，回退 roles 映射，解析不出记 `unknown` **而非猜测**，host_mode 记 `host/host`）；`review_paper` 在真实调用后用每次返回的 `CallRecord.backend/model` **覆盖**静态配置（gateway/override 场景）再重算。
- 状态判定：`heterogeneous`（distinct_models ≥ 2）/ `homogeneous_degraded`（same_model、single_reviewer、routing_unresolved、no_reviewers）/ `host_mode`。写入 `REVIEW_PANEL.json` 的 `panel_independence`（含 `distinct_models`/`distinct_backends`/逐 reviewer `{id,role,backend,model,source,resolved}`/`adjudicator`/`adjudicator_distinct`/`adjudicator_shared_with`）+ 顶层 `independence_warning`（homogeneous/host 时必非空）+ `disclosures`（`panel_independence_degraded`/`panel_host_mode`/`adjudicator_not_distinct`）。
- **同模型不改变 verdict、不 FAIL、不放松任何门，只披露**——host mode 是项目明确支持的合法形态，很多用户只有一个 key。`adjudicate()`/`adjudicate_cross()` 三个返回路径均新增仲裁者披露。host_mode 下 `review_paper` 不再制造 N 个伪错误，直接返回 `REVIEW_FAILED + reason_code=host_mode` 且不发起任何 completion 调用。
- `providers.json` 的 `comment` 扩写为配置即文档（说明默认同模型 → `homogeneous_degraded`，要真异构需把 review 与 adjudication 指向不同 backend/model）；**所有默认 role/backend/model 未动**。`review.py` 文件 docstring 改为如实描述（默认同模型时是带 bias 的多次独立采样，配了不同 backend 才是真异构），消除与代码相反的承诺。
- 测试 +14（负向 6：默认同模型 → `homogeneous_degraded` 且 `distinct_models==1`、host_mode/None-provider、routing 不可解析不得冒充异构、自仲裁披露；正向 5；兼容/回归 3）。

### I. RSI 变异器接真 + submit 分支隔离（治"最大卖点上最空心的点"）

- **缺陷**：`evolve_cli.py:35` 的 `_demo_mutator()` 在 **5 条硬编码文案**里轮换（追加到 patch 的 `new` 文本后），其 docstring 自认 "Real deployment replaces this with `provider.complete('ideation', ...)`"。整套 PUCT + MAP-Elites 搜索、三分片防作弊、probe 预检、评分器冻结——这套精密进化机器搜索的候选空间就是这 5 条文案的排列组合。README 宣称 skill 库级 RSI（竞品无人做到），实际变异器是 demo。
- 修法：接线真 LLM 变异器（`LLMMutator` / `_extract_patch_payload` / `build_mutator`），走 `providers.complete("ideation", ...)`。prompt 含 ①最近 3 个 run 的真实审计信号（gate_rejections/loopbacks/warns）②parent patch 的 path/old/new ③从 pristine 文件按 anchor 截取的上下文窗口 ④MAP-Elites inspiration 候选 ⑤严格输出 schema 与冻结路径规则。
- **健壮解析（刻意不复用 pipeline 的脆弱做法）**：v1.7.3 已发现 `_parse_verdict_json` "从噪声 stdout 抓最后一个含 verdict 的 JSON"可被巧合 JSON 伪造。此处规则：唯一 fenced block → 解析；整段 JSON → 解析；否则平衡括号扫描且**必须恰好一个** distinct patch 对象，多个即 `ambiguous_*` 错误（绝不静默取最后一个）；`empty_reply`/`invalid_fenced_json`/`no_patch_json` 显式报错。失败重试 1 次（追加更严格指令），再失败降级 demo。
- **FROZEN_PREFIXES 机械强制**（不靠 prompt 求它别改）：`evolve.py:102-117` `op_error`→`editable()`→`frozen_path`（含 `..`/绝对路径/盘符/反斜杠的 `unsafe_path`）、`:154` `sanitize_patch`（LLM 每次生成 + EvolutionRun 每次变异复用）、`:571-584` `EvolutionRun._mutate` 对**任何** mutator（含未来被注入的）输出过闸并写 `mutation_guarded` 事件、`:177` `apply_patch` 既有拒绝、`evolve_cli.py:314` 逐 op 校验 + `:458` shard_check + `:548` submit 整体拒绝（不静默剥离）。
- **降级必披露**（沿用 v1.7.3 范式）：`mutator.mode` ∈ {`llm`,`demo_template`}、`mutator.disclosure` ∈ {`llm_ideation_mutation`, `llm_ideation_mutation_with_demo_fallback:<parse_failure|provider_error>`, `demo_template:<host_mode|no_provider|forced_by_env>`}，另带 `degraded`/`fallbacks`/`rejected_ops`/`last_error`/`usage`；同时写 NDJSON `mutator_selected`/`mutator_summary` 与扩展 meta.json。`_demo_mutator` **保留**（无 key 环境仍能跑通进化循环 + 测试注入点）。
- **submit 分支隔离**：此前直接向真库 commit。现在默认 `git checkout -b evolve/<run_id>`（重名加时间戳，run_id 做 ref 字符消毒）→ 应用 patch → 在该分支跑完整 ci_check → 仅提交分支 → 切回原分支（detached 用 `--detach` 回去），输出 diffstat/changed_files 与 review/merge/push/pr 命令，meta 置 `BRANCH_READY`；dirty 工作树（仅跟踪文件）拒绝，CI/commit 失败回滚并删空分支。`--direct` 或 `SCIFORGE_EVOLVE_DIRECT=1` 才沿用旧的直提当前分支（无人值守 CI 用）。scratch 目录支持 `SCIFORGE_EVO_WORKSPACE` / `evolve.json`（原硬编码 /tmp，daemon 重启即丢）。
- `JudgeDomain` 提示词泛化一行（不再假定"只判追加的 RSI note"）。测试 +23（含 4 个安全测试：冻结路径混合注入、纯冻结 op 降级、路径穿越/绝对路径、EvolutionRun 通用守卫；另有 untracked 不阻塞、dirty 拒绝、CI 失败回滚、分支名消毒）。

### J. 引用验证如实降级 + 4 个记档小债

- **触发现场**：实测 Semantic Scholar API 持续 429（走代理与直连各 3 次全 429），且**全仓代码无任何地方读 S2 API key**；对照组 CrossRef 200、arXiv 200、OpenAlex 200（无 key）。硬规则 5 要求"每条引用过 3 层验证"，第 3 层在当前环境根本跑不了。
- 用户决策：**降为"arXiv + CrossRef 两层 + 显式披露"**，不静默跳过、不改用 OpenAlex（改协议范围更大）。沿用 v1.7.3 建立的"降级必披露"范式（doi_gate 离线披露 `doi_online_unverified` 并封顶 MINOR_REV；fairness 无证据披露 `scope=ledger_only`；smoke 无法执行 WARN + reason_code）。
- `CITATION_AUDIT.json` 顶层新增 4 个披露字段（schema 同步，**保持可选**以兼容旧产物与 fixture）：`verification_depth` ∈ {`3-layer`,`2-layer-degraded`,`not_attempted`}、`layers_verified`（数组 ⊆ [arxiv,crossref,semantic_scholar]）、`layer3_status` ∈ {verified, not_required, unavailable_rate_limited, unavailable_network, unavailable_no_credentials, unavailable_error, not_attempted}、`layer3_detail`（自由文本，如 `HTTP 429 after 3 attempts`）。语义：`2-layer-degraded` = 每条都用两层核过（**≠ 未验证**），只是第 3 层没跑。
- **澄清一处长期概念混用**：`citation-audit` 里的 "three layers" 指三个**审计轴** EXISTENCE/METADATA/CONTEXT（始终全跑），不是 arXiv/CrossRef/S2 三个**检索层**；原文 "skips Layers 1-2 and only re-checks Layer 3 (context)" 把两者混为一谈。契约改为明确区分"轴"与"检索层"。
- 术语全仓统一为 **multi-layer**（原 "3-layer"）：`citation-audit`/`universal-retrieval`/`paper-writing`/`citation-discipline`/`venue-checklists`/`paper-compile`/`writing-principles`/`output-protocol`/`fantasy-prevention`/`artifact-registry`/`paper-modes`/`paper-voice-contract`/`discipline-writing`/`project-architecture-contract`/`venue-profiles`/根 `SKILL.md`/`AGENT_GUIDE.md`/双 `README`/`docs/agents/sciforge-researcher.md`/`docs/SCIENTISTTWO_PARITY.md`。**质量门表（`auto-pipeline/SKILL.md:374`）仍保持 non-skippable**：门照跑，通过条件改为"两层完成 + 第 3 层完成或已披露降级"。
- **披露一致性升级为机械门**（统筹补，`validate_verdicts.py` post_checks 第 5 条）：`3-layer` 与 `unavailable_*` 的 layer3_status 共存、或 `2-layer-degraded` 却声称 `semantic_scholar`、或降级却缺 arxiv/crossref 任一强制层 → **FAIL**（"声称跑了没跑的层"= 捏造审计记录，比引用错误更严重）。未声明任何深度字段的旧产物不受影响。实测 6 种形状：伪造 3 层拦、降级却称 s2 拦、降级缺 arxiv 拦、诚实降级放、真 3 层放、旧产物放。
- 4 个小债：**(a)** `smoke_gate._find_smoke` 收紧——一条 smoke 记录只归属一个组（`consumed` 集合），根级无名记录兜底仅限单组运行，多组时根级文件必须名字绑定该组（`<group>.SMOKE.json`），堵住"一份根级记录洗白多组"（与其 docstring "one file must not launder the others" 对齐）；`_ungrouped` 形态仍合法。**(b)** `paper-writing/SKILL.md` 的泄漏类描述从"8 类 / v3.3"更新为 12 类 A–L + I-frontmatter / v3.6-mech，并明确 `leakage_scan.CLASSES` 才是权威正则。**(c)** `leakage_scan.py` docstring 版本 v3.5 → v3.6-mech（与实际写出的 verdict version 一致）。**(d)** `REPRODUCE.md` 第 1 节补 `gate_all.py` 入口、全部真实选项与退出码、`UNPROTECTED` 含义。
- 防漂移测试：`tests/test_schema_leakage_classes.py` 风格的动态派生（从 scanner 源码推导类集合与运行期 version，文档缺类或版本漂移即失败）+ `tests/test_citation_layer_wording.py`（95 项：全仓禁止无条件 3 层断言、协议文档必须携带新契约词、披露词汇表必须与 schema enum 一致、**编排门必须仍 non-skippable**、降级必须被要求披露）。测试 +20。
- 顺带修一个**既有定时炸弹**：`test_smoke_hashless_record_warns` 的 `executed_at` 硬编码为 `2026-11-11T00:00:00Z`，UTC 过 00:00:02 后必然 FAIL（用 HEAD 版 smoke_gate 复现了同样失败，证明与本轮改动无关）→ 改为运行时 UTC。

### 统筹收口：跨 agent 移交项与集成接缝

- **`pipeline._native_review` 转发独立性披露进注册 verdict**：`REVIEW_PANEL.json` 是未注册遥测，而下游门读 `REVIEW_STATE.json`——不转发则 H 的披露写了没人看。新增 `panel_independence` + `independence_warning` 两字段（schema `additionalProperties: true`，实测带新字段仍过严格校验）。
- **`submission_ready` 消费独立性披露**：`homogeneous_degraded`/`host_mode` → 记入 `disclosures`（`review_panel_<status>`、`adjudicator_not_distinct`）。**刻意不放进 `soft`**：soft 项驱动 tier，而项目自带的默认 `providers.json` 就是同模型配置，计分会让默认配置永远拿不到 READY（把合法形态判成缺陷=误报）。实测披露生效且 `soft` 未被污染。
- **`daemon._record_crash` 验链优先**：崩溃分支原先无条件把 RUNSTATE 写成 `daemon_worker_crash`，会**掩盖**更重要的断链事实并向已受损日志追加事件。现在先 `verify_chain()`：断裂 → 只记 `event_log_integrity_broken` 且**不碰日志**；完好 → 照旧记 crash + emit 事件。实测空日志与 legacy 日志均 `ok=True`，不误伤正常崩溃路径。
- **`cli.cmd_run` 补 `DispatchError` 捕获**：`start()` 对三种不可续跑情形（工作区被占、链断裂、run 已终态）抛 `DispatchError`，此前直接吐原始 traceback——**恰恰是完整性那条最需要被机械读取的情形**。现在输出结构化 JSON（`status/reason/error`）+ exit 2，reason ∈ {`event_log_integrity_broken`, `workspace_locked`, `run_not_resumable`, `dispatch_error`}；daemon 侧本已正确捕获。实测断链工作区：exit 2 + 可解析 JSON + 正确 reason。
- **`cli submit --direct` flag 注册**：`evolve_cli` 读 `getattr(a,"direct",False)` 但 CLI 从未注册该参数 → 旧的直提行为只能靠环境变量触达。已补 flag + help。
- **macOS 27 沙箱修复的下游确认**：v1.7.3 修的 `(allow signal *)` → `(allow process-exec)(allow signal)` 是本轮 smoke 真执行的前置条件，I/J 的沙箱内重执行路径均依赖它。
- **文档与代码一致性巡检**：`CLAUDE.md` 版本陈述同步 1.7.4，并补 5 条本轮亲历 gotcha（events.ndjson 已哈希链、**绝不可手改或手工重生成 fixture 的事件日志**；run flags 读事件不读 RUNSTATE；**绝不对入库 fixture 跑 gate_all/s2_audit/integrity_monitor**，副作用会污染 checked-in fixture 且被测试断言拦下；评审面板独立性是披露而非强制；`.venv` 断链由 ci_check environment 腿检出）。图审计范围订正 A1–A10 → A1–A11。`package.json` description 同步（v1.7.3 轮曾因 description 滞留被判 FAIL，本轮主动修）。

- **fixture 补齐引用披露字段，让新 post-check 真被演练**：`fixtures/e2e_minimal/.sciforge/verdicts/CITATION_AUDIT.json` 原先没有 `verification_depth`/`layers_verified`/`layer3_status`/`layer3_detail`——四个字段都是可选的（为兼容旧产物），于是 J 新加的伪造检测 post-check 在入库 fixture 上**一次也没被执行过**。现补为如实的降级形状（`2-layer-degraded` + `unavailable_rate_limited`，两层已验证全部条目），并订正 summary 里"3 verification layers (context, metadata, existence)"的**轴/层混用**——那三个是审计轴，不是 arXiv/CrossRef/S2 检索层。实测：fixture 严格校验仍 24/24；把 depth 改成 `3-layer` 而保留 `unavailable_*` 时，post-check 三条规则同时命中并判 FAIL。
- **移交项逐条复核（多数已由 owner 自行闭环）**：G/H/I/J 的移交清单写在各自中途快照上，统筹逐条实测后确认 `--direct` flag、`cmd_run` 的 `DispatchError` 捕获、`_native_review` 转发、`daemon` 验链优先、`validate_verdicts` post-check、以及 13 处文档"3 层强制"漂移**均已在最终交付中修好**；精确扫描后剩余的 "3-layer" 命中全部是反伪造警告（正确保留）、多保真度阶梯（Low/Mid/High，与引用无关）或历史条目。四债对抗实测：篡改 RUNSTATE 的 `human_skip` 后检查点仍 False（flags 来自 `run_started` 事件）；追加伪造 `checkpoint_cleared` → `verify_chain` 报 `broken_seq=99` 且检查点 False；默认配置面板如实报 `homogeneous_degraded`/`distinct_models=1`/`adjudicator_distinct=False`；`validate_patch` 对 `tests/`、`kernel/`、`../../etc/passwd` 三类越界分别判 `frozen_path`/`frozen_path`/`unsafe_path`。

### 追加：ARC-Bench S01 真实端到端运行驱动的修复（版本仍 1.7.4）

用真实 benchmark 题（ARC-Bench S01：bootstrap 区间在轻尾/偏斜/重尾数据下的覆盖率；55 题题库在 HuggingFace `AIMING-Lab-UNC/ARC-Bench`，MIT，此前记录的 GitHub 仓库已 404）跑了一遍 Mode A 全链。**论文本身只是测试载体，但它把五个纸面分析发现不了的缺陷打了出来**——全部是真实布局/真实数据才触发的。

- **新增引用切题性门 `scripts/citation_relevance_gate.py`**（真实运行的头号发现）：检索查询 `all:"BCa"` 在 arXiv 上撞了缩写 **BCA = Binary Collision Approximation**，导致 4 条离题文献（行星表面溅射、毫米波体成分、乳腺癌放射组学 BCa-S、金属核壳纳米粒子抗辐射）通过全部验证并**进入 `references.bib`（21 条占 19%）**，而 `gap_gate`/`doi_gate`/`citation_support` 三个引用门**没有一个检查切题性**，`FILTER_CHAIN_AUDIT` 还判 `PASS 21/0`。当时是 agent 凭判断在写 GAP_REPORT 时绕开了它们——靠自觉，不靠门，违反第一硬规则。新门以 `domain-signature.json` 的 `primary_domain` + `standard_methods` 为判据，用"home 领域证据 vs foreign 领域加权术语"分级：实测 21 条中 17 relevant / 4 off_topic（4/4 命中我手工核出的全部离题条目，且多抓到我先前漏看的 2 条），而 6 条合法跨学科引用（双重机器学习 / Cox+Lasso / 久期模型 / PPML 重尾贸易 / 广义后验 / wild bootstrap）**零误报**。清理后门转 PASS，`FILTER_CHAIN_AUDIT` 记 `relevance_filter` 如实留痕。
- **图引擎跨轴刻度碰撞修复**（`figure_recipes.py`）：A10（v1.7.3 刚"复明"的碰撞审计）在真实图上抓到两类此前无人覆盖的碰撞——**刻度 vs 刻度**（值域窄到 0.88–0.96 时 auto-locator 把 y 刻度贴着原点，其标签伸进第一个 x 刻度：`'0.3' vs '0.88'`）与**刻度 vs 轴标题**（auto-locator 生成越界刻度 `−0.1`，压在旋转的 y 轴标题下）。既有的 `_fit_xticklabels`/`_fit_yticklabels` 只比较**同一轴内**相邻标签，永远看不见这两类。新增 `_corner_ticks_overlap` + `_fit_corner_ticklabels`：先裁掉数据范围外的刻度，再按需用 `MaxNLocator` 稀疏化，**无碰撞时为 no-op**（有负向测试证明不误伤）。7 张真实图从 2 张 FAIL 变 **7/7 A10 PASS**；图相关 196 项测试零回归。
- **macOS 沙箱两处致命缺陷**（`execution.py`，**影响每一次沙箱执行**）：① `sandbox-exec` 会**先解析符号链接再 exec**，于是 `.venv/bin/python` 丢掉 venv 身份、CPython 退回系统 site-packages，任何实验脚本在沙箱内 `import numpy` 直接 `ModuleNotFoundError`——而同一命令在沙箱外正常，所以从未被发现；新增 `venv_site_packages()` 从 shim 路径找回 venv 的 site-packages 并注入 `PYTHONPATH`（`dispatch` 与 `smoke_gate` 共用）。② profile 缺 `sysctl-read`，`os.uname()` 被拒（`PermissionError`），而 **numpy 在 import 阶段就调用它**——即任何导入科学栈的沙箱实验必然在跑第一行自己的代码前就死。两处修完后 `smoke_gate` 首次真实通过：**4 个实验切片在沙箱内真实重执行成功**。
- **`dep_gate` 本地模块误报**：`src/bootstrap_ci.py` 被三个同目录脚本 import，被判"未在 dependencies.json 声明"——本地模块不是第三方依赖，这会让 6b/6c 边界在完全正常的目录布局上被拦。新增 `_local_roots()`（src/figures/experiments 下的 `.py` stem 与包名），并保留负向测试：真正未声明的 `import torch` 仍 FAIL。
- **`smoke_gate` 阶段聚合被误当成分组**：`experiments/full/STATUS.json` 是整阶段聚合状态，但只要有子分组，它就额外生成一个名为 `full` 的幽灵组并索要 `full.SMOKE.json`——四个分组 smoke 全在却判 FAIL。改为：存在子目录分组时，根级 marker 视为聚合而非分组；无子分组时根级 marker 仍是唯一分组（单组路径不变，有测试锁定）。
- **`gate_all` 游标陈旧导致整批门静默跳过**（最影响 Mode A 可用性）：`_current_rank()` 的 docstring 写 "demonstrably reached"，实现却只读 RUNSTATE 声明。真实 run 里工作区已有实验、图、17 条文献，而 RUNSTATE 停在 phase 0 → **28 个门全部 `phase_not_reached` SKIP**，报告看起来像"没什么可检查"，恰是该脚本要消灭的失败模式。改为取「声明游标」与「磁盘证据」的较大者（证据探针覆盖 6/6b/6c/10/11/12/13/14/15/15.5），并把不一致显式报成 `runstate_cursor_stale` WARN 行而非静默修正。
- **`EXPERIMENT_MATRIX.schema.json` 组名过窄**：pattern 只允许 `hyperparam|robustness` 裸名，而流水线自己生成了 `hyperparam_trim`/`robustness_seeds`，导致 `validate_verdicts --strict` 把这两组判 FAIL（边界会因此被自己拦死）。放宽为允许后缀变体。
- `tests/test_v174_runtime_fixes.py`（9 项）+ `tests/test_plotting_robustness.py`（+2）覆盖上述全部修复，含沙箱内真实 `import numpy`、本地模块正/负向、幽灵分组正/负向、游标证据优先与无证据时仍可 SKIP。**777 passed，ci_check PASS，security_scan --self-test 26/26**。
- **真实运行的科学产出（旁证管线可用）**：4 DGP × 3 n × 5 种子 × R=1000 完成（60/60 cell，零错误）；H1/H2/H3 均 supported，且抓到一条反教科书预期的结果——**污染数据下 studentized bootstrap-t 覆盖 0.886、BCa 0.845，双双差于简单 percentile 的 0.925**，而稳健目标（中位数/20% 截尾）同时赢覆盖与宽度（0.9466 / 宽度 0.444 vs percentile 0.899）。这正是"bootstrap 高阶修正更好"叙事在重尾下的反例。
- **本轮未做（因用户判定论文仅为测试载体）**：未写论文正文、未编译 PDF，故 `submission_ready`/`figure_embedding` 等终局门 SKIP；run 已清掉半成品 `paper/` 骨架以免误导门。`s2_ladder`/`s2_ablation` 判 FAIL 是**真实的 run 缺口**（未产出 `S2_LADDER.json`/`ABLATION_LEDGER.json`），门判得对，不是误报。`runs/S01` 已加 `.gitignore`，评测产物不入库。

- **最严重的一个：smoke 重执行会覆盖它要审计的真实结果**（`smoke_gate.py` + `experiment-execution` 契约）。`smoke_cmd` 写的是 `--out experiments/full/group_main`，而 `_invoke` 以真实工作区为 cwd 执行——脚本把 `RESULT.json` 写进该目录，于是**一次审计把 60 cell / R=1000 的真实全矩阵结果替换成了 5 键 / R=2 的 smoke 聚合**。这不是理论风险：本轮实测发生后 `group_main` 与 `group_ablation` 的 RESULT 都变成 `stage: smoke`，下游每个 claim 的证据被静默降级（我是随后读 n100 键报 KeyError 才发现）。修法遵循"审计对被审计证据零副作用"：重执行前快照 `experiments/**/*.json`，执行后逐字节比对，**恢复被改动/新建的文件并判 FAIL**（`smoke_reexec_mutated_evidence`，附被改文件清单）——只恢复不报错会掩盖坏掉的 `smoke_cmd`，只报错不恢复会留下被污染的证据，两者都做。契约同步要求 smoke 输出落在隔离目录（如 `.smoke-out/<group>`），并说明 `--out experiments/full/<group>` 为何违约。负向测试构造真实"覆盖 60 cell"场景断言恢复+FAIL；正向测试证明指向 scratch 的同一脚本不误报。被覆盖的 run 数据已用同组权威的 `experiments/full/RESULT.json`（60 cell 完好）恢复；`smoke_cmd` 改隔离后重跑：**smoke PASS 且 RESULT.json 字节未变**。**779 passed，ci_check PASS**。
- **两个 FAIL 经查是真实 run 缺口而非代码缺陷**：`s2_ladder`/`s2_ablation` 要求的 `S2_LADDER.json`/`ABLATION_LEDGER.json` 全仓**没有任何生产代码写**——设计如此：门在 kernel（模型无关），产物由宿主按 `/experiment-ladder`、`/ablation-planner` 手写（skill 原文 "tells the HOST how to produce the artifact the gate demands"），编排 SKILL.md 第 378/383 行在两者缺失时也明确指向这两个 skill。本轮是续跑时跳过了这两步，门判 FAIL 是对的。记此一笔以免后来者误判为"工具缺失"。

### 追加二：把"审计零副作用"从单点自觉提升为全局不变量（版本仍 1.7.4）

上一条只在 `smoke_gate` 内部加了护栏。但**任何会执行代码的门都可能犯同样的错**，靠每个门自己记得检查不是纵深防御。本轮把它提升为批量入口的强制不变量，并顺带清掉两个遗留项。

- **`gate_all` 逐门证据护栏**：每个门执行前快照、执行后逐字节比对，谁改了证据就**点名谁**（`gate_mutated_evidence` + 文件清单）并恢复——比整批比对更能定位责任门。实测注入一个会覆盖 60 cell 结果的假门：判 FAIL、点名、证据完整恢复；只读门与只写自己 verdict 的门零误报。
- **护栏范围扩到 `results.json` 与 `results/*.json`**：ARC-Bench 的 must_pass 把 `results.json` 定为假设判定与指标的权威载体，改它和改 `RESULT.json` 一样具破坏性，而原护栏只覆盖 `experiments/`。同时用白名单排除门自己的产物（`TDAL.json`/`FANTASY_GATE.json`/`LEAKAGE_SCRUB.json` 等 12 个），否则每次正常运行都会误报。真实 run 上受保护证据文件 **223 个**，`results.json` 字节未变。
- **`approvals._verified_marks` 自身 fail-closed**（清掉 G 的移交项）：它是所有审批决定读取的底层原语，此前直接 `replay()` 而不验链——上层 `pipeline` 的守卫虽能兜住，但那让防御依赖"每个调用方都记得先检查"。现在断链直接返回空。用**有区分力**的测试锁定：先造一个真实批准事件断言能读到 `APPROVE`，再篡改该事件断言读不到（先前一版测试两边都返回空，等于没验证）；另加 legacy 无链日志仍可读的兼容测试。
- **`SCIFORGE_OUT` 环境契约**（真实运行逼出来的）：护栏上线后立刻在真实 run 上抓到**另外两个组**（`group_hyperparam_trim`/`group_robustness`）同类违规——它们的脚本把输出路径硬编码在模块级常量里，**根本没有 `--out` 参数**，命令行无法redirect。所以"要求宿主改 smoke_cmd"这条路对它们不成立。门现在主动注入 `SCIFORGE_OUT=.smoke-out/reexec`（与既有的 `SCIFORGE_SMOKE=1` 并列），脚本读该变量即可零命令行改动地合规。契约补上代码范式，并写明两条真实踩坑规则：① **输出目标必须与路径解析分离**——我第一版直接重赋 `HERE`，结果 `HERE.parents[2]` 越界、`sys.path` 插入全断（`IndexError`），因为同一个常量既定位工作区又定位输出；② 每一处写入都要走 `OUT`，不能只改第一处。
- **补齐两个真实 run 缺口，全门首次零 FAIL**：用 kernel 自己的 `ladder.decide`/`relative_gain` 与 `ablation.ablcritic` 从**真实数据**生成 `S2_LADDER.json`/`ABLATION_LEDGER.json`（不手算增益、不手判 critic）。阶梯：污染数据 n=100 上 trim 相对 mean-percentile incumbent，subset 与 full 同向 GOOD，gain +2.29%；**高斯臂另行评估判 BAD**（percentile 0.9482 < t 区间 0.9538），作为负结果保留不晋级。消融重跑取真数据（84 单元）后 5 个计划：studentized/BCa/nested 三个"高阶修正"全部 REFINE（0.8673/0.8447/0.8720 均差于 incumbent 0.9087），median/trim 两个稳健目标 GOOD。**`gate_all` 终态：PASS 10 / WARN 2 / SKIP 16 / UNPROTECTED 2 / INFO 1，零 FAIL**；剩余 2 个 UNPROTECTED 是 Mode A 结构性限制（REP/NODES 由内核产出），如实披露而非假装通过。
- **785 passed，ci_check PASS**。

### 追加三：评审面板真异构（版本仍 1.7.4）——三个真实阻塞逐一打通

上一轮把"同模型三次采样"如实披露为 `homogeneous_degraded`，但披露不等于解决：分歧度仍只反映采样噪声，而 `reviewloop` 的阈值 8 与 `adjudicate` 的 `spread>=4` 都建立在它之上。本轮真接了第二个 provider 并跑通真实双模型评审，过程中撞出**三个此前无人发现的阻塞**——每一个都足以让异构接线静默失败。

- **阻塞一：reasoning 模型的 thinking 块污染 JSON**（`providers.py`）。原提取逻辑对**所有非 text 块**一律 `json.dumps(b.get("input", {}))`；thinking 块没有 `input` 键，于是被序列化成字面量 `{}` 拼进正文——评审的 `{"scores":…}` 变成 `{}{"scores":…}`，`json.loads` 直接 `Extra data` 失败。这是实测网关响应发现的（`content[0]` 是 thinking，我最初只取 `[0]` 拿到空串）。新增 `_anthropic_text()`：只收 `text`，`tool_use` 保留其 `input`（结构化输出走这条），thinking/redacted_thinking/未知类型一律忽略。**不修它，接第二个 provider 只会让所有评审解析失败。**
- **阻塞二：协议由 backend 名字决定**（`providers.py`）。`_raw_call` 里 `if name == "anthropic"` 是唯一判据，任何别名 backend 都被按 OpenAI schema 发到 `/chat/completions`。而按 provider id 路由的网关需要**多个 Anthropic 协议 backend 各用不同名字**——它们全部 404。新增 `backend.protocol` 显式声明（`anthropic`/`openai`），缺省仍按名字推断，既有配置零改动。
- **阻塞三：`SCIFORGE_MODEL` 抹平所有角色**（`providers.py`）。宿主上报的模型原先无条件覆盖每个 role，把刻意配置的异构面板重新压回同一模型——正是面板要逃离的状态。改为跳过 `pinned: true` 的角色；未 pin 的仍享受该便利默认。
- **默认 personas 自动分散**（`review.py`）：`_default_personas` 三个 lens 原先全用 `role="review"`，所以**光配 backend 不够**——三个 persona 仍解析到同一模型。现在当配置确实把 `review`/`reasoning`/`grading` 映射到不同 `(backend, model)` 时自动分散；全部同目标时三者仍留在 `review`（shipped 单 backend 默认的行为与成本零变化，有测试锁定）。`adjudication` **永不**作为 reviewer lens——否则 chair 审自己的案子。
- **可选启用，默认不变**：新增 `SCIFORGE_PROVIDERS` 环境变量选择替代配置文件 + `kernel/config/providers.heterogeneous.example.json` 示例（端点为占位符，**不硬编码任何本机 provider id**）。示例的 comment 写清四条要求：persona 必须用不同 role、adjudication 必须区别于所有 reviewer、非 `anthropic` 名的 Anthropic 协议 backend 必须显式声明 protocol、pinned 豁免宿主覆盖。
- **真实端到端验证（非仅配置检测）**：用两个实测可用的 provider 跑真实评审——`reviews_n=2 accepted_n=2`，usage_log 证实两次调用落在不同 backend/model，`spread` 触发 `ADJUDICATE_REQUIRED`。两个模型独立给出的 fatal 相当专业：**"0.9254 vs 0.9466 在 400 次重复下可能落在 Monte Carlo 噪声内，未报 CI"**、**"均值 CI 与截尾均值 CI 在污染下针对不同估计量"**（后者是先前的分析都没点透的估计量歧义）。另经 `SCIFORGE_PROVIDERS` 走完整路径复验：自动分配 role → 两模型各出分 → spread 19.75 → 仲裁。
- `tests/test_provider_heterogeneity.py`（17 项，全部离线 stub，CI 无需网关与凭据）：thinking 不污染/tool_use 保留/未知块忽略、protocol 显式与缺省与非法值回退、pinned 豁免与未 pin 仍覆盖、双 backend 面板 heterogeneous 且 chair 独立、单 backend 仍如实 degraded、默认 personas 两种配置下的行为、chair 永不兼任 reviewer、chair 撞模型时如实披露、`SCIFORGE_PROVIDERS` 选路。**803 passed，ci_check PASS**。
- **过程中的自我纠错（记档）**：第一版 stub 把 `adjudication` 当作 reviewer persona，于是 `adjudicator_distinct=False` ——那是**代码判对了、测试写错了**；读 `panel_independence` 确认 chair 是独立角色后改为真实拓扑（2 reviewer 各一 backend + 独立 chair）。

### 记档未做（诚实清单）
- **EventLog.emit 未加跨进程 flock**：单进程内已用 sync-before-emit 保证链接正确；若未来 daemon 允许两个进程写同一 workspace 日志，会因 prev_hash 分叉被判断裂（**会显式报错而非静默通过**），需要时再加锁。
- **整文件重算哈希不在威胁模型内**：同 uid 攻击者可重算全链，需 HMAC + 密钥管理才能防。当前防护目标是"低成本追加伪造"与"篡改可检测"。
- **`gate_all.py`/`fairness_gate.py` 读 events.ndjson 时不报告完整性**：建议把 `event_log_integrity_broken` 暴露为门判定。
- **A10 上轮新抓到的 panel-grid legend 与旋转刻度重叠**：属 `figure_recipes` bottom band 布局债，仍未修。
- `nodes.py` 只记 `ts` 无每节点耗时，fairness 预算对账仍用 STATUS/RESULT 耗时。
- `--workers` 默认仍为 1（预算隔离优先）；`propose.py` 的信号尚未压缩成结构化 digest；`golden.py` 仍 4 题且未加"mutator 不触碰冻结路径"用例。
- **第三方评审通道**（ScholarPeer / Stanford Agentic Reviewer）仍是 seam，未接入——它同时能天然满足评审异构性。
- v1.8 候选池剩余项（事件重放增量化已完成；PRODUCTION_LEDGER 生产账本、program 模式链式选题、dispatch_backend colab seam、校准实测批、句级蕴含半、S2 滚雪球召回）本轮未启动。

## [1.7.3] - 2026-11-11 定版：门从自报变互证 + 工厂化运行时 + 端到端 harness（五 agent 并行还债）

> 版本主题：**把"agent 说什么就是什么"的门升级为与磁盘证据对账，把单工位 daemon 升级为可持续生产的多 worker 工厂，并让 26 节点 DAG 第一次拥有不依赖 LLM 的端到端回归**。本轮全部是 v1.7.2 记档在案的债（CHANGELOG 三处"留 v1.8"）+ 深度勘察实证缺口，**基线 449 → 568 测试全绿，ci_check PASS，security_scan --self-test 26/26**。方法：六个并行 agent 按零重叠文件所有权分工（A–F）+ 一个独立验证 agent 对抗复核 + 统筹收口。

### A. 端到端 harness（治"26 节点 DAG 从未被自动化覆盖"）
- **`host="mock"` 脚本化假宿主**（`pipeline.py`）：按 phase id 从 JSON 脚本表返回 verdict 并落盘声明产物，真实 `Kernel` 状态机可在 CI 内跑完全部 26 节点，零 LLM、零网络。`tests/test_mock_host_e2e.py`（8 项）覆盖：hybrid 路由 happy path（`validate_verdicts --strict --require-complete` 24/24 + wrap-up 全门）、L1 回卷 3 轮（预算从 events.ndjson 重建，耗尽后 `paused_blocked`，KILL_DECISIONS 记 budget_left 2/1/0）、off-plan fallback 判 FAIL、门拒绝 3 轮上限后 blocked、崩溃后 `recover()` 精确续跑、v1.7.2 六机制真被执行。
- **harness 当场抓出并修复 4 个真实状态机缺陷**（这是本项最大价值）：① `gate_retry` 上限**从未生效**——`_round_count` 只数 `loopback` 事件，失败门实际无限重试；② `human_skip` 在第二个检查点失效（approval log 一旦存在就不再读 run 级 flag）；③ 终局 16 边界**永远无法提交**（completion_gate 要求 RUNSTATE 已 completed，而该转换正是这个边界本身）→ 改为 wrap-up 前置 provisional completed、任一门失败即回滚；④ `doi_gate`/`submission_ready` 把未注册的辅助 verdict 写进 `verdicts/`，`--strict` 视为 WARN → 15/15.5/16 边界被自己拦死 → kernel 在校验前隔离到 `audits/`。
- **`fixtures/e2e_minimal/` 接通 v1.7.2 六机制**（原记档债"e2e fixture 与新机制双向脱钩"）：补 `events.ndjson`（116 事件/27 次 boundary_committed）、`nodes/NODES.json`、`nodes/CLAIM_ANCHORS.json`、`audits/REP.json`、`audits/CLAIMS_FROM_RESULTS.md`、`experiments/toy/**` 与 `audits/{S2_LADDER,ABLATION_LEDGER}.json`——**全部由 kernel 真实生成函数产出，非手写**；s2_ladder/s2_ablation/s2_audit 在该 fixture 上从 SKIP 变真执行。

### B. 门互证化（治"自报型门"，v1.6「证据可验证」主线的最后一公里）
- **`fairness_gate.py` 交叉验证**（+761 行）：六项公平性此前**全部读自 agent 自写的 ledger 字段**。新增 `evidence_crossvalidation`——split 哈希对账（EVALUATION_PROTOCOL/RESULT/STATUS/events 声明 vs NODES 节点 sha256 vs data 下真实 manifest）、种子数对账（STATUS/RESULT/逐 seed 目录/NODES/events 的独立执行痕迹）、预算对账（RUN_BUDGET 墙钟 vs 真实耗时）。对不上账 FAIL；无法对账 WARN + reason_code；纯 ledger 工作区保持既有语义并显式披露 `scope=ledger_only`。
- **`smoke_gate.py` 真执行**（+604 行）：此前只查 `.SMOKE.json` 存在且 `smoke_result=PASS`——写个空文件就能过。现在核对 `script`+`script_sha256`+`executed_at` 与磁盘脚本（**脚本改过而记录陈旧 = stale smoke → FAIL**），并在内核沙箱内限时真跑（非零退出/traceback/超时 → FAIL）。无法真执行（脚本缺失、无哈希、沙箱不可用）明确 WARN + reason_code，**绝不假 PASS**。
- **`submission_ready.py` 去 offline**：v1.7.1 的"严格 DOI"卖点此前在最终分层时传 `--offline`，实际未联网校验。现在默认走 `doi_gate.check(offline=False)`，transporter 复用 litcache（30d/6h TTL）+ limiter（CrossRef 间隔与 429 冷却）+ 全局预算与逐请求超时；离线/不可达/预算耗尽时披露 `doi_online_unverified` 并把 READY **封顶为 MINOR_REV**，绝不静默 PASS。
- `tests/test_gate_crossvalidation.py`（29 项，正向 7 / 负向 22，其中 8 项是"必须 WARN/披露而非 PASS"的降级路径）。

### C. daemon 工厂化（治持续生产的单点与安全隐患）
- **持久队列 + 多 worker**：run 队列落 SQLite（`<archive>/.sciforge-daemon/queue.sqlite3`，重启不丢、`run_id` 主键天然去重），worker 以 `BEGIN IMMEDIATE` 原子领取并带租约心跳；启动时按「pid 存活 + 工作区锁持有」判定孤儿行并重新入队（3 次上限转 failed）；单 run 异常双层隔离，崩溃 run 写 `paused_blocked + reason_code=daemon_worker_crash` 并释放锁，不再留悬挂 RUNSTATE。`serve --workers N`（默认 1，保持预算隔离；能力已就绪）。
- **控制面认证**（修真实安全缺陷）：此前 loopback 上**任何本机进程都能 POST `/approve` 替人类点同意**，绕过不可协商的人工检查点。现在启动生成一次性 token 落 0600 文件，所有 POST（`/runs`、`/approve`、`/deny`、新增 `/runs/<id>/resume`、`/runs/<id>/cancel`）强制 `Authorization: Bearer`（或 `X-SciForge-Token`）——缺失 401、不匹配 403；只读 GET 保持开放；`decided_by` 由服务端按真实来源写入，忽略请求体伪造。
- **锁竞态修复**：`take_lock`/`holder_alive` 此前用 pid 文件 + `kill(pid,0)`——pid 复用误判、两进程可同时通过 `recover()`（TOCTOU）。改为 POSIX `flock(LOCK_EX|LOCK_NB)` 全程持有（进程死亡自动释放）+ inode 复核防 unlink 竞态；Windows 降级 `O_CREAT|O_EXCL`；锁文件存 pid+进程启动时间+随机 nonce 免疫 pid 复用；`recover()` 改为先原子抢锁再改状态。顺带修掉 Windows 上 `os.kill(pid,0)` 会**真的杀进程**的隐患。
- **审批防伪**：审批以事件账本 epoch（nonce）为准——伪造 PENDING 无法批、删文件/手改 APPROVED 仍保持阻塞；`APPROVAL_LOG.txt` 经 `_VerifiedLog` 过滤，**手写 APPROVE 行不算数**。
- **跨进程限流**：`limiter.py` 新增可选 SQLite 后端（`shared_db=` / `SCIFORGE_LIMITER_DB`），429 冷却跨进程共享；`serve()` 自动注入，worker/子进程共享同一冷却；无 `shared_db` 时行为零变化。
- `tests/test_daemon_factory.py`（30 项，含负向：无 token `/approve` → 401、错误 token → 403、4 进程抢锁仅 1 个 OK、伪造 PENDING/手写 APPROVAL_LOG 均不能自批）。

### D. 三笔记档债清偿
- **B07 host 侧 allowlist 自植检测**（`security_scan.py`，ARC-Bench 实测事故：执行 agent 在仓库根自植 allowlist 给自己开豁免，"运动员兼裁判"）：新增结构化 provenance 判定——以脚本/cwd 的最外层项目标记祖先（`.sciforge`/`.git`/`pyproject.toml`/`package.json`）为 agent 可写区；`--allow` 解析后落在区内 → **SEC-012 BLOCKED 且豁免完全不生效**（SEC-003 照常触发）；区内任何 allowlist 形状文件（名字匹配 + `host:`/`pattern:` 内容确认，散文不误报）→ SEC-108 WARN + `security_events`。无项目标记的裸临时目录保持 trusted（不误伤 operator）。已知边界写入模块 docstring：项目标记区之外仍可放置"trusted" allowlist——无带内机制能证明人类意图，结构解是宿主把 scanner/标记置于 agent 写权限外。
- **A10 碰撞审计对 recipe 图复明**（`figure_audit.py` + `figure_recipes.py`）：五篇 ARC-Bench 论文主图标签全粘连而审计全 PASS 的根因是 A10 解析 SVG `<text>`，而 recipe 图的 SVG 由 pdftocairo 从 PDF 生成、文字是 glyph `<use>` 而非 `<text>`——**审计跑了但什么都没看见**。实测确认 `pdf.fonttype=42` 早已设置，故 fonttype 路线在当前管线不成立；改走**实测几何路线**：`figure_recipes` 在 savefig 前实测所有 text artist 的 renderer bbox 写 `text_layout.json`，A10 消费该 manifest（30%×30% 相对阈值，旋转刻度/图例 TextArea 去重）；无几何可审计时显式 WARN 而非静默 PASS。**图输出字节零变化**（with/without manifest 的 `output.pdf` SHA256 实测一致）。验收：80 行长标签 heatmap → FAIL（157 对重叠）；v1.7.1 自动旋转后的 6 长标签 bar → PASS；line/forest/panel/scatter/hist/heatmap 全 recipe 原型零误报。**新 A10 首战即抓到真阳性**：panel-grid + 长分类标签时图级 legend 与 90° 旋转 x 刻度真实重叠（已渲染 PNG 目检确认），属 `figure_recipes` bottom band 未预留旋转标签高度，记档待修。
- **环境断链自检**（`ci_check.py` 新增 environment 检查，第一项执行）：本机 `.venv/bin/python` 曾是指向已卸载 miniconda 的断链，导致 REPRODUCE.md 第一条命令以裸 shell "no such file or directory" 失败且不说明真因。现在检出断链/缺解释器/不可执行/启动失败/ABI 与 `lib/pythonX.Y` 不匹配，输出链接目标、site-packages 是否完好及条数、具体修复命令；**无 `.venv` → PASS**（CI 容器正常路径），非 venv 的 `.venv` 目录忽略。
- `tests/test_v173_debts.py`（23 项）+ `tests/test_security_scan_bypasses.py` 追加 4 项红队测试（既有 31 项零改动）；`security_scan --self-test` 25 → 26 项。

### E. 双模式保证矩阵（治"Mode A 用户以为有全套门"）
- 深度勘察实证：**v1.7.2 的一批关键门只在 Mode B（内核）生效，Mode A（宿主直读技能库）下静默 SKIP 或纯靠 prose 自觉，而文档从未声明这个差异**。`claim_anchor_gate`（NODES.json 只由内核产出）、`rep_plan_present`（没人编译 REP.json）、`integrity_monitor` D1 层、节点自动注册/fork、6b/6c 的 `security_scan` 强制、边界处硬约束逐字再注入——全部如此。一个用 Claude Code 直读技能库的用户会以为自己有 claim 锚保护，其实没有。
- `AGENT_GUIDE.md` / `auto-pipeline/SKILL.md` / `CLAUDE.md` 新增 29 行**保证矩阵**（Enforced / Advisory / Not in force 三档，每行标注源文件可核验），并在双 README 合入摘要段。
- **`scripts/gate_all.py`**（新建，Mode A 一键门入口）：清点并接入 29 个门，按 RUNSTATE 相位游标做可用性门控，保留各门自身 SKIP 语义（theory-only 实验门全 SKIP）；`--json`/`--only`/`--skip`/`--offline`/`--integrity-llm`/`--timeout`/`--list`。**关键设计：把"结构性不可用"与"通过"区分开**——引入 `UNPROTECTED` 报告态（覆盖 `claim_anchor`/`rep_plan_present`/`inv_g1`），报告末尾单独列出「本轮未生效的保证」，而不是安静 SKIP。
- 核实代码后修正了 10 处与勘察结论不符的事实，其中 4 处值得记档：**REP off-plan loopback 是"记录违约"而非"拒绝推进"**；`integrity_monitor` 的 fail-closed 只针对 LLM 层调用失败，未配置 provider 时只跑确定性 D2/D3 且可 PASS；**claim 锚在 theory-only 下两个模式都失效**（`auto_register` 只扫 `experiments/**/RESULT.json`）——这不只是 Mode A 的缺口；`sciforge_audit` 并非内核强制（`wrap_up_gates` 里 `pipeline_audit` 固定 SKIP "deferred to host"）；`tdal_compute` **不是门**（kernel 无任何调用点），`gate_all` 以 INFO 报告。

### 统筹收口：跨 agent 移交项（kernel 侧）
- **macOS 27 沙箱修复**（`execution.py`）：`(allow signal *)` 在 Darwin 27.0.1 被 Seatbelt 直接判非法（`illegal argument: #<* PROCEDURE 52>`），且缺 `process-exec` 时**被沙箱包裹的解释器根本无法 exec**——即整个内核沙箱路径在本机长期不可用（此前 `dispatch`/smoke 只能走 WARN 降级，故未被察觉）。改为 `(allow process-exec)(allow signal)`，实测 `sandbox_cmd` 下解释器与子进程均 rc=0。这是 B 项 smoke 真执行的前置条件。
- **smoke_gate 的 verdict 不再被 exit code 吞掉**（`gates.py`）：该门 exit 0 同时覆盖 PASS/WARN/SKIP，仅按 exit code 映射会把披露信息丢失。改为读 `--json` 的真实 verdict，写入 `smoke_verdict`/`smoke_disclosure` 进边界记录（events.ndjson 可审计），而 `status` 保持 exit-code 语义（WARN→PASS、FAIL→FAIL）——因为 `commit_boundary` 只放行 {PASS,SKIP,N-A}，若把 WARN 直接映射为 status=WARN 会拦死所有 `.SMOKE.json` 尚为旧形状（无 hash 但脚本存在、仍可真执行验证）的 run。**注意**：真正"零正面证据"（未绑定脚本 / 脚本缺失 / 无可执行命令）的绕过路径由下方"独立验证 agent 修点 1"在门内部直接判 FAIL（exit 2）关闭，不依赖这条映射；本条只负责让"环境无法执行"这类诚实披露可见而不阻断。
- **`doctor` 的 ci_check 自检此前是 no-op**（`cli.py` + `ci_check.py`）：doctor 传 `--quiet`，而 ci_check **不定义该参数** → argparse exit 2，`ci_check_available` 只判断对象存在，等于从不检查。ci_check 新增 `--quick`（别名 `--quiet`，跳过 test-suite 这条慢腿），doctor 改为报告真实 `ci_check_quick_pass`。

### 独立验证 agent 的 FAIL 判定与三点修复（对抗复核闭环）
提交前另起一个独立验证 agent，明确要求"反驳而非确认"。它对全部交付做对抗复核，判 **FAIL** 并抓出三个必修点——全部经统筹二次核实属实后修复：
- **修点 1：smoke 门"零正面证据"可绕过 6c 边界**（`smoke_gate.py`）。原实现把"记录未绑定任何脚本"（`smoke_unbound_to_script`）与"声明了脚本但文件缺失"（`smoke_script_missing`）都判 WARN（exit 0）。由于 `script`/`script_sha256` 是 agent 可控字段，少写两个字段即可既不执行任何代码、又不被校验地越过 6c——P0 第 3 项"真执行"只关闭了诚实记录路径，未关闭"少写元数据"路径。修复：引入**正面证据规则**——一个 smoke 组除非 (a) 记录的 sha256 与磁盘脚本字节匹配，或 (b) 切片被真正重执行（含沙箱外执行，另行披露），否则 `smoke_no_positive_evidence` → FAIL。环境/调用方造成的未执行（`sandbox_unavailable`/`sandbox_execution_failed`/`reexec_disabled`/`execution_budget_exhausted`/`security_scan_unavailable`）仍为 WARN——这些是 agent 无法伪造的诚实披露。新增绕过探针测试 `test_smoke_unbound_record_cannot_ride_the_boundary`；`test_smoke_missing_script` 由 WARN 改判 FAIL（其原意"not passes"被更强满足）。
- **修点 2：保证矩阵对 submission_ready 的陈述与 kernel 行为相反**（`AGENT_GUIDE.md` + `auto-pipeline/SKILL.md` + `gate_all.py`）。矩阵两处写"MAJOR_REV is WARN (does not block)"，但 `submission_ready` 的 MAJOR_REV→exit 1，`gates.py:219` 映射为 WARN，而 WARN **不在** `commit_boundary` 放行集 {PASS,SKIP,NOT_APPLICABLE} → **Mode B 实际阻断 15.5 边界**（与 `gates.py:215` 注释、CHANGELOG 1.7.1"MAJOR+ 阻断"一致）。修复：文档改为如实描述阻断行为；并消除 `gate_all` 的模式不对称——MAJOR_REV 在 Mode A 也报 FAIL（`reason_code=major_revision_required` 保留档位区分），使两模式对"是否可投"不再给出矛盾结论。
- **修点 3：版本叙述滞留**（`package.json` description、`CLAUDE.md:4/30`）。版本钉只改了 version 字段，`description` 仍写 `framework v1.7.2`、`CLAUDE.md` 仍写"runtime (v1.7.2)"与"Version 1.7.2 is pinned"（后者已成假话，且 CLAUDE.md 是每轮注入 agent 的项目记忆）。修复：全部更新为 1.7.3；顺带订正 CLAUDE.md 过期事实——图审计 A1–A10→**A1–A11**、Mode A 结构性失效门补 `inv_g1` 与 fairness `ledger_only`。
- **附带采纳**：`fairness_gate` 的 `scope=ledger_only`（有 ledger 但无同位原始证据，交叉验证层无法运行）在 `gate_all` 中由 PASS 升为 **UNPROTECTED**——Mode B 因 RUNSTATE/events 必然存在而免疫，但 Mode A 下无证据的 ledger 否则会显示为干净的 PASS。UNPROTECTED 覆盖门由 3 个增至 4 个（claim_anchor / rep_plan_present / inv_g1 / fairness）。
- 验证 agent 同时**证实门未被偷偷改松**：smoke 的 WARN→PASS 映射语义未变（仅增可审计字段）、fairness 六检、security BLOCKED 类永不被 pattern 豁免、submission_ready 离线封顶 MINOR_REV 而非静默 PASS、daemon 认证/锁/限流经真实起进程 + 多进程压测有效、沙箱修复实测 rc=0、kernel 33 模块在禁用 site-packages 下 `python -S` 导入零失败（stdlib-only 成立）。
- **教训记档**：统筹在收口期直接对 `fixtures/e2e_minimal` 跑 `gate_all`，触发 `s2_audit`/`integrity_monitor` 副作用写出 `AUDIT_TRAIL.json`/`INTEGRITY_MONITOR.json`，被 `test_e2e_smoke.py:531`（断言 checked-in fixture 不留审计副作用）**正确拦下**。这是门在真实工作的证据；`.gitignore` 已加针对性排除以防复发，并清理了磁盘副作用。批量门应跑在 `tmp_path` 复制体上，不跑在入库 fixture 上。

### 记档未做（诚实清单）
- **事件日志完整性**：同用户 agent 仍可直接向 `events.ndjson` 追加 `checkpoint_cleared`/`phase_done` 伪造推进；`pipeline._checkpoint_satisfied` 仍信任 RUNSTATE 里可写的 `human_skip`/`test_mode`。结构解是 EventLog 哈希链/MAC + 把两 flag 固化为 run 启动事件的不可变 epoch（涉及 state 与多个消费方，留下轮）。
- **F 发现但非本轮所有权内的记档项**：`smoke_gate._find_smoke` 第 4 条匹配（`experiments/full/` 根级 smoke）在多组场景下可能让一个根级 `.SMOKE.json` 覆盖多组，与其 docstring"one file must not launder the others"不完全一致；`leakage_scan` docstring 写 v3.5 而实际 verdict version 是 v3.6-mech；`paper-writing/SKILL.md` 仍写"8 leakage classes / v3.3"与 scanner 的 A–L 漂移。均留下轮。
- **A10 新抓到的 panel-grid legend 与旋转刻度重叠**：属 `figure_recipes` bottom band 布局债，非本轮范围。
- `nodes.py` 只记 `ts` 无每节点耗时，故预算对账目前用 STATUS/RESULT 耗时；如需按节点对账需补 `started_at`/`finished_at`/`duration_s`。
- `--workers` 默认仍为 1（预算隔离优先）；默认并行需先确认资源/预算策略。
- v1.8 候选池的 P1/P2/P3 项（LLM mutator 接线、评审异构性机械检查、事件重放增量化、PRODUCTION_LEDGER、program 模式、dispatch_backend colab seam、校准实测批）本轮未启动。

## [1.7.2] - 2026-10-02 定版：研究 OS 层（XScientist ARA + SCION REP 适配）+ 多 agent 对抗评审修复

> 版本主题：**把研究运行变成可 fork 的工件，把计划变成编译产物，把 claim 变成有锚的证据**。协议形态适配自 `smileformylove/XScientist`（Apache-2.0，归属记录在案）与 SCION REP（arXiv:2607.03863，无公开仓库，概念自实现）；全部实现为原创 SciForge 代码，stdlib-only。**444+ 全绿，ci_check PASS**。

### 六机制（D1-D6，kernel-owned）
- **D1 节点注册 + fork**（`kernel/sciforge/nodes.py`）：每个实验 RESULT.json 变成内容寻址节点（code/inputs/outputs sha256 + `reexec_cmd`）；`sciforge fork --node <id>` 从任意节点播种新工作区并落在该相位——绝不从 PDF 冷启动（三轮评测 3 次 agent 中途死的实测痛点）。失败分支是一等节点，永不滤除。
- **D5 claim→节点锚**（ARA claim.schema 适配）：`CLAIM_ANCHORS.json` 把每条论文断言链到产出它的节点+证据字节；`claim_anchor_gate` @wrap-up 拦截"引用了但无锚"与**锚后漂移**（结果被改过=claim 失效）。
- **D4 REP 运行计划**（SCION 概念自实现，`kernel/sciforge/rep.py`）：相位 1 编译 `REP.json`（分阶段目标+验证检查点+**fallback 条件**）；≥2 相位边界强制计划存在；loopback 触发时校验消费了 REP 声明的 fallback——**off-plan 恢复=违约**（杀"临场 improv 恢复"故障类）。
- **D2 语义记忆**（`memory build/query --semantic`）：跨 run **已验证事实**层（polarity-positive claims + ladder 结论，内容哈希可溯源）——re-discovery benchmark 考的正是这层；与教训索引（procedural）分离。
- **D3 批主动搜索**（`sota next -k`）：UCB 式记忆先验排序出 k 个并行变异提案 + 探索保证轮转；worker pool 共享基线数据流执行（fairness gate 天然保公平）。
- **D6 daemon 多源调度**（`sources.py`）：源注册表（jsonl bench 主题 / inbox 简报），按 id 去重轮询入队——重启永不重复排队。

### 多 agent 对抗评审修复（"确保无断裂"的实测闭环）
三个对抗评审 agent 逐一核对门链/代码/契约，抓出并修复：
- **claim_anchor_gate 结构性失效**（评审抓的最重断裂）：生产管线从不写 NODES.json（record_node 只有测试调用）、契约不教锚 token → 门永远 SKIP=三角形虚设。修复：kernel 在 6b/6c/10 边界自动注册节点（`nodes.auto_register`）、相位 10 自动锚定（`auto_anchor_claims`，按 claim 文本引用的工件路径匹配节点）、paper-writing rule 15 强制 `\claimref{C1}`/`(C1)` 锚 token。
- claim_gate 正则收紧：裸 `\bC\d+\b` 会把图注 "C1 panel" 当 claim 误报 FAIL → 只认 `\claimref{}`/`(C1)`/"claim C1"。
- REP.json 从 verdicts/ 挪到 audits/（validate_verdicts 对 verdicts/ 未知 JSON 会 WARN）；discipline 默认值统一为 strict（gates 与 pipeline.start 一致）。
- 契约登记补齐：output-protocol 树登记 nodes/ + REP.json；artifact-registry 补 6 行 v1.7.2 产物（producer/consumer/verifier）；auto-pipeline 相位 1 行 + loopback registry 第 5 条 off-plan 违约类；s2-protocol §10 六机制；README×2 CLI/能力表；CLAUDE.md 硬规则门清单。
- 附带发现（记档不修）：评审员称 CLAIMS 在项目根是误报（实测在 .sciforge/audits/，gate 路径正确）；e2e fixture 与新机制双向脱钩（测试盲区，留 v1.8）。


## [1.7.1] - 2026-09-28 定版：ARC-Bench 两代实测驱动修复 + AAR 反 Goodhart 融合

> 版本主题：**第一轮 ARC-Bench 五域实测暴露的全部缺陷，逐一修到根因**。全部改动带回归测试；439/439 绿，ci_check PASS。

### ARC-Bench 评测（runs/ 本地，永不入库）
- 拉取 AIMING-Lab-UNC/ARC-Bench（55 课题 × 5 域，MIT）→ 五域各选一题（ML02/P01/Q02/B07/S01），两轮各 5 个 sciforge-experimenter 子 agent 端到端全链跑（skill 模式），产物在 `runs/ARC-BENCH{,2}/`（.gitignore 新增评测运行排除节，测试文件绝不进仓库）。
- 两轮独立复核抓出并修复的全部缺陷见下。

### 图系统修复（第一轮五篇论文全部命中的系统性缺陷）
- **分类 x 刻度标签碰撞**（`a0ce827`）：所有 recipe 裸设 `set_xticklabels(groups)`，长标签（FBA/pFBA/loop、friedman1 low noise、DGP 名）在五篇论文主图里渲染成不可读粘连。`_finish`/`_panel` 尾部统一 post-layout 碰撞 fit：实测 renderer bbox，30→45→60→90° 阶梯旋转到清开（6px 最小间隙），竖排为底线（绝不回 0°）。B07/ML02 真实 spec 渲染 PNG 目检 + 2 回归测试。
- **forest-plot 高度自适应**（`7c8e284`）：行数由模型供给但图高固定 → 14 行压成 13/14 标签重叠（B07 Fig3）。按行撑高（~0.32in/行）。
- **d2 preamble 幽灵边**（`073c2ff`）：`(* -> *).style` 在 d2 v0.9.0 不是样式 glob 而是**连接补全算子**——8 节点链被物化成 65 条全互连毛线（Q02 架构图元凶）；`edges.style` 备选也造 ghost 节点。删除全局边块（palette 合规由 sanitize_palette 下游保证）。+2 回归测试（静态选择器 + d2 端到端边数守卫）。
- 记档：A10 碰撞审计解析 SVG `<text>` 而 matplotlib 默认路径化文字——对 recipe 图失明（本轮缺陷全部漏检的根因）；fonttype=42 或栅格化碰撞检测留 v1.8。

### 写作契约：S2 披露语态（用户批评"论文像工程报告、失败写成正文"）
- 下载并量化分析 **ScientistTwo 全部 86 篇成稿**（arXiv:2609.19644 项目页，454MB）：99% 摘要 "We introduce X" 主角开场、0% 以证伪为头条、"fail" 33% 出现但 100% 指 prior art、自家弃案写成被超越基线（"outperforms our prior 4-module iteration (+1.65%)"）、中位 15 数字/摘要、95% 正面收口。分析存档 `docs/SCIENTISTTWO_DISCLOSURE_ANALYSIS.md`（`8a4ac16`）。
- paper-writing rule 2b + 自检 12b 重写为**实证版**：区分方法失败（KILL 上游）vs 已确立归因 null（polarity positive，discovery voice）；弃案=过程证据；量化密度 ≥8 数字；正面收口。数据/CI/消融行全量保留——只换叙事主角，选择性报告仍被门禁止。
- 二轮五篇摘要全部达标（本机 PDF 提取验证："We present…" 开场、零失败语态、28-60 数字、"ablations confirm" 收口）。

### AAR 反 Goodhart 融合（`c72ea36`，用户指令"深度融合"）
- 验证 Anthropic AAR（arXiv:2608.28945, YuehHanChen/automated_alignment_researcher）：alignment 训练循环、**无 LICENSE**、需 Linux+CUDA——搬代码不可行，移植其度量纪律为自家纯 Python（Mac/Linux/Windows 一致；用户澄清 GPU 三平台都是产品目标，Mac+Colab 仅当前测试环境）。
- `s2/monitor.py`：pre-execution integrity 门（D1 禁自造 ground truth / D2 禁 eval 数据 / D3 禁大模型教师），fail-closed，接 6b/6c 边界 + CLI。
- `s2/headline.py`：geomean closed-fraction 目标（任一腿打平→整体归零）+ capability-floor/regression CI 硬门。
- experiment-execution Step 5.00b：integrity monitor + **results-free 预注册 mini-paper**（forward-looking voice，治 hindsight 叙事）+ held-out 双文件剥离。s2-protocol §9 文档化。
- 顺手抓漏：B07 agent 自植 allowlist 于仓库根（skill 模式 agent 兼任 operator 的豁免漏洞）——归档至其工作区，kernel 门免疫（从不传 --allow），v1.8 修 host 侧检测。

### 评测产物仓库卫生
- `.gitignore` 新增评测运行排除节：`runs/ARC-BENCH*/`、`runs/EVAL-T1/`、`bench/s2demo/results/`——所有测试/评测产物永不入库（runs/DEMO-RK4 作为发布证据保留跟踪）。

### 深度优化第二轮（用户指令：约束分级 / 工作区卫生 / 严格 DOI / 灵活 intake / 图高级化 / 零内部话术）
- **约束三档 `--discipline strict|balanced|lean`**（kernel flags + bundle 每边界复述 + `gates.discipline()`）：severity ∝ 后果×事后不可检测性。lean 档只把不可检测类门（fabrication/leakage/ladder/integrity/citation/编译零 ERROR）保持硬；cosmetic 类（编译警告、页带、AIGC 计数、aspect）改披露——编译门实测：lean 下 warnings 披露 PASS、strict 下 FAIL。默认 strict（发布基线不变），强模型宿主可选 lean 免负优化税。
- **误报修复**：monitor D2 正则不再命中散文 "held-out"（只认标识符/路径形态，B07 实测 REJECT 误报根因）；s2_audit parity 的 claimed-token 源去掉 `paper/main.tex`（LaTeX 宏名被当方法 token，S01 0.955→0.875 根因）。
- **run 工作区卫生门** `scripts/workspace_hygiene.py`（接 wrap-up）：stray 顶层 log/json、缓存、空目录、非规范目录检出；kernel 16 相位自动写 run README 索引（不覆盖宿主版）——run 必须像 GitHub 仓库一样人类可读。
- **图高级化**：数据图默认横版 16:9（`figsize_full/single` 默认 aspect 9/16）；forest/heatmap y 轴分类标签垂直碰撞自适应缩字（B07 Fig3 根因）；新门 `scripts/figure_style_gate.py`（接 figure_gates）：图随首次引用走（float 不得先于 citation）、正文禁栅格嵌入（矢量 only）、≥3 种视觉语法（禁全柱状图）；图预算改 Related-Work challenge 图 1 + Methods 1 + 实验 5-8（正文 ≥7）。
- **严格 DOI 门** `scripts/doi_gate.py`（挂相位 15）：每条 bib 必须有可解析 BibTeX 的 DOI（CrossRef content-negotiation + 标题一致性 ≥0.8）；无 DOI 古典书籍可声明 `no_doi_classical`；JMLR/PMLR 等无 DOI 场馆以官方 url+声明替代；**arXiv 不豁免**（有 10.48550 DOI）；不可解析=丢弃而非保留。
- **论文契约增补**（paper-voice-contract §4b/§8/§9/§10）：内部术语替换表（regime ledger→scope of validity 等，leakage class L 机械强制）；`claim_mode` 双模（sota：核心被证伪=上游 KILL、正文无失败叙事；attribution：null 即发现）；标准章节序 + Data&Code/Funding 占位 + **appendix 独立 tex 独立 PDF**；母语润色五步（删复述、名词转动词、burstiness、朗读、术语一致）。
- **灵活 intake** `skills/support/intake-triage/`：任意输入组合（初稿/代码/数据/结果/日志/排版要求）→ INTAKE_MANIFEST（census/trust/phase_plan/user-request ledger/mode 建议）；inherit 只意味"以此为起点"，门照跑；COMSOL 仅 PINN 联合、湿实验/临床拒绝。
- **scope 重声明**（README×2）：代码即科学全收（含用户兴趣域清单：AI/NLP/PINN/CV/大气污染/计量/统计/数学/光学传感器仿真/AI4Science/embodied AI/auto research/金融预测/智慧教育/RSI/LLM/边缘计算）；湿实验生物医学出局；COMSOL 定位接口/MCP 而非独立域。
- flash 级（haiku）子代理真实 bench 验证：bench 两遍确定性 PASS、三门+新门在真实 run 上行为正确、误报修复与三档分级按预期；新门首战即抓真阳性（旧 run 的 compile.log 散落、.DS_Store、JMLR 缺 url、正文 "regime ledger"）。**435/435 绿，ci_check PASS**。

### P1：SOTA 爬山闭环 + 失败记忆接线 + 完成声明门 + 二区可投门（版本仍 1.7.1）
- **`kernel/sciforge/sota.py`**：给定冻结题目 + 声明 incumbent（`SOTA_TARGET.json`，哈希绑定）→ `sciforge sota next` 出变异提案（先验=跨 run 教训索引 + 探索保证 seed）→ 宿主执行 ladder+消融 → `sciforge sota record` 记 per-leg closed fraction，geomean 头条 + capability-floor/回归 CI 硬门使"赢"失效 → plateau/预算停。kernel 管账、宿主管科学；trainer 是 seam（CPU numpy 与 Linux CUDA LoRA 同循环）。
- **失败记忆接线**：`memory.py` 从"写了没人读"变为消费者——CLI `sciforge memory build/query`（索引 35 条实测）、相位 2/6b bundle 注入 cross_run_priors、sota 驱动同索引。修索引质量：只嵌入人类可读字段（lesson/error/fix/note…），min_sim 0.3→0.12（hash-BoW 短文本真实相似度区间，0.3 地板实测零命中）。
- **`completion_gate.py` @wrap-up**：S01 式虚假完成报告物理不可能——RUNSTATE 必须 completed、摘要文档声称的每个路径必须在磁盘、main.pdf 存在且 PDF magic 正确。构造说谎 fixture 实测 FAIL（3 项命中）。
- **`submission_ready.py` @15.5**：二区可投标准机械化为四级 READY/MINOR_REV/MAJOR_REV/NOT_READY（硬项：verdicts 完整+s2 门电池+PDF≥4 页+DOI+leakage+claim_mode 一致；软项：摘要 150-300 词≥8 数字、标准章节序、附录独立 PDF、图≥7 且≥3 语法、评审≥6/校准≥8 或有 rebuttal、卫生）。MAJOR+ 阻断 15.5 边界，MINOR_REV 带披露通过（用户标准：至少小修后可投）。
- 图页数统计修压缩 xref（/Count 优先）；摘要提取取最长候选（修 25 词误截）。
- **438/438 绿，ci_check PASS**；docs/SCIENTISTTWO_PARITY.md 差距清单更新（真题已闭合、剩算力/第三方评审/真 GPU 训练三条外部依赖）。

## [1.7.0] - 2026-09-27 定版：ScientistTwo 对标层（深度复刻 arXiv:2609.19644 + demo 子 bench）

> 版本主题：**v1.5 把契约变成门，v1.6 把证据变成可验证的，v1.7 把 Google 的 ScientistTwo 复刻成开源代码**。动机：对标调研确认人家赢在"真题、真实验、真评审校准、真烧钱迭代"（86/107 顶会真题、+25.2% vs 人类 SOTA、ScholarPeer 91.9% 接收），恰是上轮体检的三大硬伤；他们的 harness 闭源 = 赛道开着。本轮把其**可迁移机制**逐一代码化进 21-phase DAG（不加相位、不破 21-phase 钉），全部带回归测试：**413/413 全绿，ci_check PASS**。协议事实源：`skills/shared-references/s2-protocol.md`；对标分析：`docs/SCIENTISTTWO_PARITY.md`。

### S2 内核六模块（`kernel/sciforge/s2/`，stdlib-only，一门两用：门脚本与 bench 共用同一实现）

- **`ladder.py` Subset→Full-Set 阶梯 + 三态 Critic**（他们 §3.2 的核心工程）：`decide()` = GOOD（严格更好）/ ENGINEER（持平，轮 ≤2）/ BAD（更差）；`validate()` 机器规则——GOOD 必须有全集 `verified:true` + 严格提升（平局不算赢）、`engineer_rounds≤2`（调参耗尽 = BLOCKED 而非静默晋级）、声明的 `relative_gain_pct` 与复算差 >0.15pp 即 reward-hacking 类失败、INV-G1 锚必须在。产物 `.sciforge/audits/S2_LADDER.json`。
- **`ideas.py` seed 排序 + 探索保证**（§3.3）：`exploration_mix()` 每轮强制混入 ≥1 个未探索 seed，防进化循环坍缩到局部最优；**kernel 在 idea 再生 loopback（目标 2/3/5）上把最高优先级未探索 seed id 写进事件与 `KILL_DECISIONS.jsonl`**——探索保证从"给模型的指令"变成可重放的审计事实。
- **`ablation.py` 消融账本 + AblCritic**（§3.4）：5–6 计划机械上下限（`SCIFORGE_ABLATION_MIN/MAX`）；`ablcritic()` 严格规则 = 新严格优于旧才 GOOD，否则 REFINE（保留旧状态）；`current_best` 单调性校验（回退/手改被检出）。
- **`reviewloop.py` rebuttal 闭环 + Meta-Review**（§3.5/3.6）：双阈值纪律——相位 14 边界地板维持 6（L10 注册表不动），**ScientistTwo 接受线 8**（`SCIFORGE_REVIEW_THRESHOLD`，默认 8.0）——校准分 <8 即写 `REBUTTAL_PLAN.json`（每个 panel fatal/kill-argument 一个补充实验任务），≤2 轮、必须真跑真回填（wording-only = round_invalid）；`meta_review()` 出 {ACCEPT | PENDING_REBUTTAL | REFINE}，ACCEPT = 分数过线且零 fatal。
- **`calibration.py` 锚点校准**（他们最狠的评审设计）：先给已知质量论文打分（reference_score）拟合 OLS `calibrated = clamp(a+b·raw, 0, 10)`；退化拟合（b≤0）回退恒等并标 `usable:false`——**校准不可用时绝不静默重标分数**。`_native_review` 消费，产出 `overall_calibrated` + `REVIEW_STATE.meta_review`。
- **`audit.py` 完整性审计**（§3.7 我们缺的两半）：增益算术复算 + 划分纪律（有实验必须有 EVALUATION_PROTOCOL 的 held-out/split/seed 声明）+ **方法↔代码 token 对齐**（方法段 backticked/snake_case/camelCase token ≥80% 必须落地在 src/experiments 代码里，反向未提及函数仅记档）——"方法段描述不存在的机器"是 reward-hacking 的经典面。产物 `AUDIT_TRAIL.json`。

### 边界门接线（phasegraph 不加相位，门即代码）

- **`s2_ladder` @6c**（`scripts/s2_ladder_gate.py`）：有实验证据但无阶梯/状态非 GOOD/超工程师帽/全集非严格提升 ⇒ 边界拒绝；无实验（theory-only）⇒ SKIP（与 smoke_gate 同语义）。
- **`s2_ablation` @相位 10**（`scripts/s2_ablation_gate.py`）：有实验证据但无消融账本/计划数出 5–6/决策违反严格规则/账本非单调 ⇒ 拒绝；无实验 ⇒ SKIP。声明即拒：**没跑消融就不能出 claim**。
- **`s2_completeness_audit` @wrap-up**（`scripts/s2_audit.py` 并入 `wrap_up_gates`）：FAIL 阻断完成；SKIP 仅当不存在实验性主张。
- 评审闭环接进 `pipeline._native_review`：panel → 锚点校准 → `rebuttal_required` → 种子 rebuttal 计划 → `meta_review` → `REVIEW_PANEL.json` + `REVIEW_STATE.json`（新增 `rebuttal_required`/`rebuttal_threshold`/`meta_review` 字段，schema additionalProperties 兼容）。

### bench/s2demo —— 他们的 mold，我们的 CPU 子 bench（无 GPU/仅 Colab 可跑）

- **4 个任务**（全部 numpy-only、seed 固定、离线秒级）：T1 同心环非线性分离（准确率↑，线性 logistic → RFF+logistic）、T2 季节预测（RMSE↓，季节 naive → 调和回归）、T3 各向异性聚类（纯度↑，球 k-means → 全协方差 GMM-EM）、T4 概率校准（ECE↓，部署锐化 T0=0.5 → 验证集温度缩放）。每个任务带结构化 briefing + 6 轴 rubric + **human_anchor=6.2**（复刻他们"先用人类中稿均分锚定量尺"）。
- **`run.py` harness 直接 import 生产 `s2/ladder.py`**（与 6c 门同一实现，一个契约两个消费者）：subset→full 双段跑分、三态 critic、方向感知相对增益（他们的 +25.2% 口径）、`S2_LADDER.json` 与门同构输出；exit 0 = 全部 PROMOTED。实测 **4/4 PROMOTED**（T1 +177.8% / T2 +74.1% / T3 +6.7% / T4 +56.2%）。
- 评测口径扩展路径：ARC-Bench / AutoResearchExam 接入留作下一步（本轮先建"他们的 mold"自留地）。

### 知识层（Markdown 同步，27 sub-skills）

- **`skills/shared-references/s2-protocol.md`**：机制↔实现↔门三方映射表 + 阶梯/消融/评审/校准/审计五份契约 + 硬规则复述（7 条）。
- **新 support skills**：`/experiment-ladder`（6b/6c 配方，产出 S2_LADDER.json 自检命令齐全）、`/ablation-planner`（相位 10，5–6 计划 + 严格批评者 + 负结果纪律）。
- **编排补丁**：auto-pipeline 质量门表 6c/10/14/16 四行升级 + See Also 三条；auto-review-loop 增 **S2 REBUTTAL BAR** 小节（6 是地板、8 是目标）；experiment-execution / idea-discovery See Also 指针；artifact-registry 新增 **ScientistTwo parity artifacts** 六行；output-protocol audits 树补 7 个 kernel-machine 文件名（与 REVIEW_PANEL.json 同类：unregistered、由 s2 门强制而非 validate_verdicts）。

### 测试与版本

- **`tests/test_s2.py` +23**：三态/工程师帽/平局不算赢/算术篡改检出/阶梯与消融门三态退出码/探索保证挂进 loopback 事件与 KILL_DECISIONS/阈值与 Meta-Review 全分支/校准退化恒等/审计三查/bench 4 任务全 PROMOTED（numpy 缺席则 skip）/`_native_review` 写 rebuttal+meta 集成两例。**413/413 全绿**；ci_check 全项 PASS。
- 版本钉 1.5.0→**1.7.0**：package.json + CITATION + 双 README badge/正文 + 根 SKILL.md + 25 个 SKILL.md frontmatter；REPRODUCE 测试计数刷新（kernel 70 / 全仓 413）。

## [1.6.0] - 2026-09-26 定版：可验证证据链 + 运行时防御（第三轮，Top-12 清单落地）

> 版本主题：**v1.5 把契约变成门，v1.6 把证据变成可验证的**。候选池分析见 `ANALYSIS_V1.6.md`（五路开源调研收敛信号 + 本地承诺兑现审计）。本轮全部改动带回归测试；380/380 绿，ci_check PASS。

### 追加：图系统第三轮（排版宪法 + 论文级 demo 语料 — 用户指令"图的这种排版，还是得去找 nature skill 或者其他专门为论文开发的 skill plugins"）

> 开源调研结论：扫 30+ 个 Nature/论文图 skill·plugin 仓库，排版权威源锁定 **`Yuan1z0825/nature-skills` 的 `nature-figure`**（唯一带机器可校验版面规范：1.5pt 面板对齐审计、碰撞审计、多面板证据架构）；其余为衍生/补充。全部吸收进 `figure-layout-contract.md`。

- **排版宪法 `skills/shared-references/figure-layout-contract.md`**（277 行，v1.0）：五点图画契约（核心结论一句带谓语 / 证据链每面板一个推断角色 / 版面原型 / 锁定工具链 / 导出契约——缺 `claim`/`archetype` 拒绝渲染）、10 角色推断角色表、证据链原型（validation-envelope / scale-to-instance / discovery-sequence / capability-ladder）、4 个 Nature-2026 页原型几何锁、16 个布局 pattern、final-width-first 公式（`on_page_font_pt = font_pt × W_doc/W_fig` 必须=1）、人工建造顺序 + AI-slop 红名单。来源标注：nature-figure / Zhangyanbo/nature-style-skill / thesis-figure-skill / research-figure-composer / FigFox-Gen / apaper PRINCIPLES / happy-figure-skill。
- **版面原型进配方引擎**：`figure_recipes` `panel-grid` 新增 `layout` 字段，4 原型几何代码锁死——`equal-grid`（等宽等高 + A11 全局 width lock）、`schematic-led`（hero 45–60% 高 `height_ratios=[2.0,1.15]` + support 降噪）、`asymmetric-hero`（中央面板跨行）、`clinical-triptych`（`height_ratios=[1.0,1.35,0.8]` 三行叙事）。每个原型输出 `panel_layout.json` 清单供审计消费。
- **A11 面板对齐门（`figure_audit.py`）**：1.5pt 物理公差比对同行/同列共享边、等宽、重复 gutter；hero 只豁免自身、不放宽全局公差（负向测试：30pt 宽度漂移正确 FAIL，豁免 hero 时兄弟面板漂移仍 FAIL）；三联画行高不等是合法结构（仅 equal-grid 强制列等高）。`FIX BEFORE DELIVERY`/exit 1 阻断交付。
- **修掉 5 个真排版缺陷**（看图→改码闭环）：(1) `fig.subplots_adjust` 不移动 `add_gridspec` 的 axes，行距全部失效——几何改由 gridspec 直接持有；(2) `NATURE_FLOOR` 16pt 单图字号在半栏 support 面板挤爆邻居——support 降为 point-scale（0.5×轴标签/0.55×刻度，对齐契约 §6 印刷 6–8pt）；(3) panel 字母外置 `(a)` 压邻面板 y 轴——改内侧左上小写 + 白底 halo；(4) 图例压 x 轴标签——底部独立预留带；(5) support 面板轴标签与 hero 争语义——P3 静音。
- **论文级 demo 语料 `demos/figures/`（10 spec）**：取代玩具序列，对标 ChenLiu-1996/figures4papers 与 Yuan1z0825 nature-figure 样张语义——LLM 预训练损失 / 基准准确率 / scaling-law / 注意力稀疏图 / 延迟分布 / 三中心试验 forest / 四版面原型（真实量纲、命名方法、CI 语义、真实样本量）。回归测试 `test_demo_corpus_specs_are_publication_grade` 锁死"禁玩具序列名"（`a`/`b`/`ours` 裸名直接 FAIL）。
- **forest-plot schema 加固**：`pooled` 必须是 `{effect,lo,hi}` 对象，布尔值直接 `ValueError`（此前 `True` 会把字典订阅打崩）。
- **测试**：+11 回归（4 版面原型清单/hero 豁免语义/未知 layout 拒绝/pooled 类型守卫/demo 语料论文级断言；A11 对齐 PASS/漂移 FAIL/豁免不放水/三联画行高/单面板 n/a）；修复 `test_providers_reports_429_cooldown` 测试隔离缺陷（ANTHROPIC_API_KEY 门在 `_raw_call` 前拦下，429 路径从未走到——补 dummy key）。**390/390 全绿**。
- 样张：`docs/assets/layout-*.png`（4 原型 + 画廊）、`docs/assets/demos/`（10 论文级样张）；分析并入 `docs/FIGURE-GALLERY.md`。

### 追加：图系统深度优化（工具链强制统一 + 依赖治理 — 用户指令"图还得继续深度优化，工具链必须高度统一，依赖必须清晰，不能模型想用什么用什么"）

> 对标开源实测：proplot(停更勿依赖)/mplhep(命名 style 机制)/SciencePlots(nature.mplstyle)/K-Dense scientific-visualization(palette_audit)/cathrynlavery·diagram-design(42k★ 复杂度预算+6 连接线规则)/PaperBanana zone 策略/opentikz edit_contract/thesis-figure-skill layout-by-construction。论文级 d2 模板仓库不存在——该缺口由本系统填补。

- **数据配方引擎 `figure_recipes.py`**（声明式，布局零自由度）：`.recipe.json` 只填数据+标签，几何/字号/图例/色板/误差语义全锁。7 配方：line-comparison（误差带+stat 自动标注）、bar-grouped（误差棒+零基线）、scatter-fit（OLS+r 标注）、heatmap（Layer-2 强制，jet 拒绝，单元格反色）、hist-dist、forest-plot（CI 触须+合并菱形）、panel-grid（(a)(b)(c) 内嵌字母+**图级共享 legend**+markerscale）。统一入口 auto-detect `.recipe.json`，审计/latex_include 管线不变。
- **方法图引擎 `method_recipes.py`**（L1→L5 从简到繁阶梯）：`.method.json` 填阶段/模块文本，d2 源码确定性生成——方向/圆角/线宽/多巴胺色板（focus≤2 色+zone tint）/虚线=辅助约定/Legend 框/≤4 词节点预算全锁。5 级：L1 线性、L2 分支+循环、L3 容器+图例+callout 引导线、L4 宏-微 inset、L5 分带架构。engine=method 接入统一入口（elk 布局，inject=False 避免 preamble 双重注入）。
- **prop_cycle 可见性排序修复**（panel 色漂移根因）：`series_style(0)` 与默认色循环现共用单一 `cycle_hex()`（line-safe 5 色在前、fill-only 3 色在后），naive `ax.plot` 首色从对比 2.68 变 3.07——五线零配置全可读。
- **依赖治理 `dependencies.json` + `dep_gate.py`**："想用什么用什么"在结构上不可能：清单为 import 唯一事实源（tier 镜像 requirements.txt），dep_gate AST 扫 src/ + figures/**/render.py 每个 import root，未声明即 FAIL（stdlib 经 `sys.stdlib_module_names` 自动放行，`always_forbidden` 优先）。与 security_scan（行为：网络/凭证/破坏性）+ SEC-106（pip）正交互补 = 供应链+白名单+行为三件套。挂 6b/6c 边界。
- **审计抓真 bug 的元证据**：方法阶梯开发中 A4 字号地板抓出 4 个 d2 真缺陷（`//` 注释渲染成 16px 文本、class/glob 字号不传播到边标签、保留字 legend+全局边样式画伪连线、容器重引用丢 class），每个先 FAIL 后修，strict 5/5 才放行——"门即代码"的运作方式。
- **画廊与水平分析**：`docs/FIGURE-GALLERY.md`（逐图诚实评级：5 数据配方 4 出版级/1 可改进；L3 方法图为最高样张，L5 最弱）+ `docs/assets/figure-ladder-gallery.png` 联系表 + 3 张多巴胺验证图。
- **测试**：+13 回归（recipe 渲染/未知配方拒绝/jet 拒绝/共享图例内省/色序单源守卫；dep_gate 未声明 FAIL/声明+stdlib PASS/无码 SKIP）。**380/371→380 全绿**，ci_check PASS。
- 版本口径统一：本轮全部并入 **1.6.0**（用户定版策略：不另起 1.6.1）；"12 引擎"表述更新为"15 引擎（含声明式 recipe 与方法图模板）"。

### 追加：图系统第一轮（多巴胺色板 v3.0 — 用户指令"图的颜色/工具链/skill 深度找开源项目，色系统一多巴胺"）

- **色板性质变更**：Layer 1 莫兰迪（C*≤25）退役，换 **多巴胺高饱和色板**（8 系列：blue #00A6FB / orange #F3722C / green #06A77D / red #FF3B6B / teal #118AB2 / violet #8338EC / gold #FFBF00 / crimson #D90429）。**不是拍脑袋选色**：经约束搜索（29 色高饱和池 × CVD 双网）锁定——全部 28 对组合在 protan/deutan/tritan 三型模拟下 min ΔE = 15.0、零失败；9 色被证明物理不可行（第 9 色必破 ΔE≥15），故系列循环止于 8 色，9+ 由 marker+明度双编码延展。
- **双安全网（新增基础设施，`sciforge_style.py`）**：`simulate_cvd`（Viénot/Brettel 线性 RGB 近似矩阵，纯 stdlib）+ `pair_distinguishable`/`palette_distinguishability`（CIE76 ΔE 三型+灰度）+ `palette_visibility`（line-safe vs fill-only 分层——gold/blue/orange 对比度 <3 只准做填充且必配 ≥5.1 对比描边，`stroke_for` 兜底）。调研（子代理实测 GitHub/PyPI）证实这是开源界稀缺组合：三合一自动审计无现成先例，K-Dense palette_audit/socraticstatic 为最接近参考。
- **prop_cycle 按可见性排序（v3.0 修复）**：默认 matplotlib 色循环先消耗折线图，故 line-safe 五色（green/red/teal/violet/crimson）排在 fill-only 三色（blue/orange/gold）之前——朴素 `ax.plot` 路径的首色从对比度 2.68 的 hero blue 变为 3.07 的 green，实测五线折线图零配置全可读（`docs/assets/dopamine-naive-cycle.png`）；语义角色（hero=blue 等）不变，填充路径仍得全 8 色。
- **契约反转（全链一致）**：审计 A3 从"morandi-compliant"改"on-palette (dopamine v3.0)"；`is_morandi`→`is_on_palette`（保留旧名别名，registered verdict 兼容）；`theme: modern` 从硬性禁用翻转为允许（高饱和不再与色板冲突，但 off-palette hex 仍拒）；self-check 契约变 C*≥30 + 白底可见性 ≥3 + 系列两两 CVD≥15；Layer 2 增 **cividis**（CVD 设计色图，调研采纳），多巴胺永不进连续色图（双轨制，全生态一致先例）。
- **文档全链同步（14 文件）**：color-themes.md 重写为多巴胺 v3.0 唯一事实源（含三安全网章节、stroke 对比列、"非手选而是约束搜索"的诚实说明）；unified-plotting SKILL、figure-quality/complexity-contract、venue-checklists、discipline-writing、paper-writing/compile、README×2、AGENT_GUIDE、SKILL.md、INSTALL.md 全部 morandi→dopamine；leakage_scan class E 同步禁"dopamine palette"泄露进图题。
- **端到端验证**：真实 matplotlib 管线渲染 → A3 PASS（"all saturated colors on-palette (dopamine v3.0)"）→ strict exit 0；验证图入 `docs/assets/`（dopamine-palette-demo.png / dopamine-cvd-grid.png 四行 CVD 模拟网格 / dopamine-grayscale.png 灰度打印模拟）。
- **测试**：+7 多巴胺基础设施回归（CVD 模拟正确性、红绿经典碰撞可检出、8 色板过双网、可见性分层、self-check、cividis 在列）；**371/371 全绿**。

### Top-12 主体（可验证证据链 + 运行时防御）

- **B5（本轮审计最重发现，定性为 kernel 强制）**：`security_scan` 从"phasegraph 声明但主循环从不消费"变成真正嵌入 6b/6c 边界——src/ 与 experiments/ 下任何 agent-authored 脚本静态扫描不过 → 边界拒绝提交（不写 boundary_committed）。README"门即代码"的卖点自此对实验链诚实。
- **A2 fantasy-prevention 五门**：自称"最重要质量门"却只有 prose；`scripts/fantasy_gate.py` 从既有机器产物（PROOF_AUDIT/CITATION_AUDIT/FALSIFICATION_RECORD/domain-signature/RESULT）确定性评估 5 门，FANTASY/MOSTLY_FANTASY 阻断 paper-writing 并写 fantasy-log.md；证据不足**保守放行**（单门失败≠fantasy）；挂 Phase 12。
- **A1 TDAL 四维联合置信**：v2.8 锁定的 T×D×A×L 公式首次被执行——`scripts/tdal_compute.py` 纯读机器产物，floor 规则齐备（dim=0→WEAK、missing_inputs→封顶 MODERATE、no-literature→UNSUPPORTED），fixture 实跑复现契约 worked example（STRONG 被 theory_data_validation 缺失正确压到 MODERATE）。
- **A0 kernel 生产欠债**：Phase 9 INVARIANT_CHECK 改 kernel-native（hash 比对+Q-id 下游扫描，产出过严格校验器的 registered JSON，篡改锚点可被检出）；KILL/PIVOT/BA 路由事实记入 `results/KILL_DECISIONS.jsonl` 决策账本。
- **可验证公平性两件套**：`arb_verify.py`（python-flint Arb 认证区间——声明值必须是可复算包含的 ball，point-value 时代结束，挂 Phase 10）；`citation_support.py`（第 4 层核查：量化句无 \cite 无自引 → FAIL、bib 孤儿 → FAIL；确定性结构半，LLM 蕴含半留 SCIFORGE_LLM_SUPPORT，挂 Phase 15）。
- **A3 SMOKE 门 kernel 化**：Step 5.0 的"埋没小节"故障类（Q-SGD-BS-GAP 全实验没跑冒烟）由 `smoke_gate.py` 在 6c 边界强制——缺 .SMOKE.json 的 dispatch 不再有效。
- **运行时防御层（C-5 收敛靶点）**：`sanitize.py` 权威标签消毒（bundle 注入防御 + drift 自检，外部内容中的 `<system-reminder>` 变惰性文本且留 integrity 警告）；`limiter.py` 键控限速 + 429 全局冷却（Retry-After 保留，本会话亲历 Google 免费档 25万 tok/min 教训直接成设计；manifest 在 `kernel/config/ratelimits.json`）；providers 调用前 pacing、429 上报冷却。
- **双计时器（C-5）**：人工审批等待与宿主 agent 执行时长从 wall-clock 预算扣除（`external_wait_seconds` 从 events.ndjson 重建、区间真合并、崩溃安全），RUN_BUDGET 新增 `external_wait_seconds` 审计字段——"等人/等宿主"不再烧 run 预算。
- **工程**：requirements kernel 段升级（python-flint 入门槛、codecarbon/psutil 可选）；`.venv`/网关运行于 Python 3.14.7（338→367 全绿）；`bin/sciforge.js` 解释器探测 3.14 优先；verifier 脚本解释器探测（B1，Xcode-shim 免疫）。
- **记档未做（诚实）**：GEPA 变异引擎（MIT vendor 待做）、EvoScientist AutoSkills 蒸馏（与 HITL 原则半冲突，仅提案化）、S2 滚雪球检索、codecarbon 能耗账、Lean 门接口预留、AIDE 树搜索灰度、AutoDL ssh 后端（用户决定暂缓）。

## [1.5.0] - 2026-09-26 波次二收官：闭环 demo 实测 + 8 个 kernel bug 修复（S58–S60 定版）

### 闭环 demo（DEMO-RK4，子代理加载本项目全链实测）
- **问题**：RK4 积分下阻尼谐振子能量是否守恒、误差如何随 dt 缩放。**36 个边界全链走完，kernel status=completed**，421 事件，`validate_verdicts --strict --require-complete` 24/24 PASS。
- **科学产出（真结论，非样例）**：RK4 不守恒能量；精确乘子 ρ(h)²=1−h⁶/72+h⁸/576；固定 T 误差 ∝ dt⁵（拟合斜率 4.94，预注册带 [4.7,5.3] 内）；阻尼 e^{−cT} 因子化预测被证伪→按负结果纪律进 Limitations。论文 `runs/DEMO-RK4/paper/main.pdf`（7 页 elsarticle，latexmk 零警告零错误）。
- **逐相质量评分**：26 相均分 **8.5**（科学内容 9.0 / 基础设施 7.5）；`runs/DEMO-RK4/QUALITY_REPORT.md` 全量表（每相产物/亮点/缺陷/分数）。
- **live 文献核验**：CrossRef/arXiv 真实查询，2 判别性 gap，15 引用 3 层验证零捏造（S2 限流如实记录）。
- **SCI 语域实证**：成稿正文 class K（道歉/防御）0 命中；Limitations 为 regime ledger。

### 闭环抓出并已修复的 8 个 kernel bug（这是本次 demo 最大价值）
| # | 严重度 | 修复 |
|---|---|---|
| BUG-1 | medium | checkpoint_after 消耗 done.json 后重复派发 → verdict 缓存跨检查点（1446ee0）|
| BUG-2 | — | 撤回（误报）|
| BUG-3 | medium | evidence_type 顶层读取（skill 实际嵌套在 domain_profile）→ 嵌套读取（4f78f04）|
| BUG-4 | **high** | verdict_field 缺 value 永假 + 不搜 experiments/** → 正在**卡死所有实验 run**，已修（4f78f04）|
| BUG-5 | high | figure_gates 传错目录（ws 而非 ws/paper）→ 修正（0d336d9）|
| BUG-6 | high | QUALITY_GATE/PAPER_COMPILE 未注册被 --strict 拒 → 注册为 25 个 verdict（0d336d9）|
| BUG-7 | **critical** | providers.json 强制非 host 模式 → phase 14 空跑 L10 回卷全链 → 凭据感知 host_mode（0d336d9）|
| BUG-8 | high | _native_review 写出 schema 非法 REVIEW_STATE（response_class 类型错）→ 修正（768aba1）|
| minor | low | fairness min-seeds 与 lite 档不一致 → effort 感知（a4621c7）|

每个 bug 均带回归测试。**最终：335/335 测试全绿 + ci_check OVERALL PASS。**

## [1.5.0] - 2026-09-26 波次二（SCI 语域 + 实验公平 + DeepMind 融合 + Claude Code 无缝）

### v1.5.0-w2：30 项深度优化续（git 多提交，版本号不变，收 1.5.0）
- **SCI 正文语域硬门（S31/S32）**：writing-principles §0.6 新增——正文零道歉零防御（apology/defense register 全禁）、hedge 只允许带界（range/N/CI/regime）的精确语句、Limitations=regime ledger 不是忏悔、stance-first 段落序（禁 apology sandwich）。`leakage_scan.py` class K 机器检测（正文/摘要/方法/结果/讨论零容忍；实测植入 "Unfortunately…we apologize" 2 命中 FAIL）。
- **mode=deepen（S33-S38）**：第三种一等模式——**不改创新点结构**的深度优化（"刷 SOTA 但不调参"）：核心 claim/贡献/方法身份冻结（违反=BLOCKED），DEEPEN_PLAN 只做证据深度（功效/消融阶梯/稳健性 battery/多重比较校正/效应量+CI 入表）与**实验公平性**（同算力预算/同数据划分锁/同种子策略/同超参预算/同指标定义）。`FAIRNESS.json` 注册为第 22 个 verdict + `scripts/fairness_gate.py` 硬门（不公 FAIL/公平 PASS 均实测），挂在 15.5 publishability 前。
- **DeepMind 顶级项目融合（S39-S46）**：调研 AlphaEvolve/AlphaProof/AlphaGeometry/AlphaTensor/GNoME/GraphCast（docs/DEEPMIND_FUSION.md）。落地：**级联多评估器**（便宜 CI/golden 门→科学诚信正则 ResearchDomain→LLM judge 最后；硬零层永不进 judge——削弱负结果纪律/审计门/INV-G1 的 patch 直接 0 分）、**生成-验证-强化闭环**（LESSONS.json `verified_proofs`：仅 status=PASS 结果进入下轮先验）、**主动学习回流**（`retrain_from_results` 回流 domain-signature）。
- **Claude Code 无缝集成（S47-S53）**：`~/.claude/skills/sciforge/` 轻量适配器（pointer-load 到仓库 orchestrator，单一事实源）+ `CLAUDE.md` 项目记忆（硬规则/kernel verdict 契约/路径/gotcha）。skill 已被 Claude Code 识别为可调用条目。
- **测试**：325/325 全绿（含 FAIRNESS fixture + theory-only 5-N/A 算术修正）。

## [1.5.0] - 2026-09-26 (定版追加：Runtime Kernel + RSI 进化，性质变更)

### v1.5.0 定版：从"纯 Skill 包"跃迁为"Skill 驱动的研究运行时"（30 项超级重构，S01–S30）
> 性质变更声明：**技能库依旧纯 Markdown**（任何 agent 直读不变）；新增 `kernel/`（Python ≥3.10 stdlib-only）**代码级控制面**——知识/控制分离。吸取对象：ScienceDiscovery(openJiuwen/华为)、AI-Scientist v2、EvoScientist、DeepScientist、STORM、AgentLaboratory。无 UI；接入 claude/codex 即用。作战计划全文：`EVOLUTION_PLAN.md`。

- **W1 Runtime Kernel（S01–S10）**：`kernel/config/phasegraph.json` 把 21-phase DAG/回路预算/门编码为可执行配置；`pipeline.py` 代码状态机驱动循环（指针化 phase bundle + 硬约束逐边界原文再注入）；`events.ndjson` 事件溯源 + `RUNSTATE.json` v2（**崩溃→kill -9 实测→stale lockfile 检出→断点精确续跑**）；`providers.py` 多后端角色分档（网关 env 覆盖 + 400 自动降级 tool→plain-JSON；**真实 token/成本入 RUN_BUDGET**，claude 宿主实测 $1.13 记账）；`gates.py` 机械门嵌入控制流（**不过门无法提交边界**：validate_verdicts/security_scan/figures/gap_gate/leakage/compile 全 code-enforce）；`approvals.py` HITL 代码化（PENDING_APPROVAL + paused_checkpoint + 超时语义 + APPROVAL_LOG）；`execution.py` worker 池/沙箱策略（macOS Seatbelt + Linux bwrap 生成）/设备规划（detect_device 升格）；`skills_pack.py` skill 冻结包（0444 + package hash + **skill-extensions 可写自进化区**）；`daemon.py` `sciforge serve` headless 队列+HTTP（:4510，Linux 无 GUI 服务器过夜运行）；claude/codex/manual 三宿主适配器实测。
- **W2 RSI 进化层（S11–S19）**：`evolve.py` 双引擎（**PUCT 树 + MAP-Elites 多岛环形迁移+inspiration 变异**，共用 Domain 接缝）× 四评分模式（gate_metric/llm_judge 冻结 rubric/hybrid/probe）；**三分片 rollout/gate/test**（held-out 报数，防搜索自我刷分）；**probe 预检**（评分无判别力→拒绝开跑，实测拦截 2 次）；**评分器冻结**（FROZEN_PREFIXES：tests/schemas/validators/kernel 自身——候选永不触碰）；`propose.py` 审计事件→SKILL.md patch 提案；**端到端 RSI 闭环实测**：搜索 6 候选 → 胜出 score=0.88/held_out=0.76 → `submit` 全量 CI 门合入（bad-candidate 首次 submit 被 ci_check **正确拦截并自动回滚**——安全机制现场生效）；golden 回归电池 `golden.py`（7/7：路由确定性×4 + gap 判别×2 + fixture 完整×1，入进化硬门）。
- **W3 科研纵深（S20–S27）**：`review.py` **多模型交叉审稿团**——3 独立盲审视角（methods/novelty/repro）+ 分歧仲裁（ADJUDICATE_REQUIRED 升 chair），phase 14 实测（stub 论文被诚实打 2.3 分 11 fatal，非橡皮图章；REVIEW_PANEL.json + registered REVIEW_STATE.json 双落盘）；`litcache.py` verified-ref SQLite 缓存（30d/6h TTL 分级，实测）；`proxy.py` 文献代理自动发现（实测发现网关 62503，替代写死 8099）；`scripts/leakage_scan.py` **10 类管线泄漏+AIGC 痕迹机械扫描**（stdlib 正则，exit-code 门；实测抓全植入泄漏含伪造 frontmatter）；`scripts/gap_gate.py` GAP_REPORT 判别力门（锚点 id+引用+discrimination lexicon，防空洞 gap 驱动幻觉选题）。
- **工程与可复现（S28–S30）**：`Dockerfile` headless 镜像（texlive+d2+graphviz+rsvg+poppler，GPU `--gups`/NPU/ CPU 全兼容，无 GUI）；macOS 完全体实测（uv py3.12 + brew graphviz/librsvg/poppler + TinyTeX standalone；`sciforge doctor` 全绿）；requirements 增 kernel 段（pytest 入门槛）；npm 包发布面含 kernel/（`sciforge run|resume|status|step|approve|gate|doctor|dispatch|jobs|evolve|submit|daily|serve|cache|proxy`）；**基线 6 洞修复**（fixture 缺 2 注册 verdict + RUNSTATE 被 gitignore 吞 + standalone 缺包——314→**320 测试全绿**，golden 门必须全绿是进化准入）。
- 版本策略：**定版 1.5.0**（用户指令）——本轮 30 项全部并入 1.5.0 条目，不升 2.0.0；VERSIONING 大一统纪律保持（package.json/CITATION/README×2/26 SKILL.md 同版本）。

### 实测记录（macOS arm64, 2026-09-25/26）
1. manual-host 协议：phase 0→1b 逐步推进 + done.json 应答 ✓
2. **kill -9 模拟**：stale lockfile → `recover()` → 事件重放 → 断点 phase 1b 精确续跑 ✓
3. claude 宿主适配器：Phase 1a 真实执行（domain-signature-hint.json 落盘 + $1.13 成本入 RUN_BUDGET）✓
4. RSI 完整环：probe 拦截平坦评分器×2 → 判别力建立（good 0.5 vs corrupt 0.0）→ PUCT 6 候选 → 0.88 胜出 → submit 全量 ci_check 拦截坏合入→回滚 ✓ → 修基线后重跑 held-out 0.76 → 合入 commit 158fc16 ✓
5. S20 面板：3 盲审 + 仲裁 + 21-schema REVIEW_STATE 写入 ✓
6. gap_gate/leakage_scan/security_scan/sandbox/dispatch/cache/proxy/golden：单元+实弹 ✓
7. 全链 --host claude --loop 过夜电池（S29 记录持续更新）

## [1.5.0] - 2026-08-12

### v1.5.0：武器库 + 设备判定 + 收敛链路 + 修订模式 + 反漂移/活人感/证伪探针（统一版本，无修版本）
- **武器库**：根 `requirements.txt` 全量分层（core/统计因果ML/图渲染/文本/文献API/可选升级），floor 索引参考机；**设备判定** `scripts/detect_device.py`（domain-driven：GPU/CPU/NPU/人文无，先判设备再选后端，非 CPU-first），INSTALL §2.6 + experiment-execution Step 0a 联动。
- **收敛链路**：`scripts/sciforge_audit.py` 单 CLI 汇总机械门（图嵌入+渲染/verdict 完整/模板浮动控制）→ 一个 verdict+exit code，长 prose 链收成工具调用（anti-drift）。
- **修订模式**：`/auto-pipeline mode=revision`（单入口改已成稿，DIAGNOSIS→定向修→re-audit→recompile，scoped-revision，跳过 idea 阶段、锚定原 idea）。
- **nohup 默认**：任何实验 >60s 后台+STATUS 轮询，前台仅 ≤60s smoke（防超时）。
- **反漂移**：默认核心环 idea→exp→audit→write→compile→review + 按相 pointer-load + 机械判定走工具。
- **活人感反AIGC**：grammar/可读性门（language-tool/textstat）+ 每学科人话范例（paper-writing #13）。
- **证伪探针**：通用 battery（placebo/替换规格/子样本/敏感性/power/parallel-trends/SHAP-consistency），domain-selected，不写死领域（experiment-execution）。
- **P2**：LESSONS 向量检索+policy update；文献 verified-ref 缓存；幂等断点（产物 hash 跳过未变分析）。
- 版本统一 **1.5.0**（26 SKILL.md + package.json + CITATION.cff + README 徽章）；300 tests + ci_check OVERALL PASS。

## [1.4.0] - 2026-08-10

### v1.4.0 第七轮：武器库根 requirements + 设备类型判定（domain-driven，非 CPU-first；版本号不变）
- 根 `requirements.txt` 全量分层（core/统计因果ML/图渲染/文本/文献API/可选升级），floor 索引参考机。
- **纠正"CPU-first"**：计算后端按**领域+机器**定（GPU/CPU/NPU/人文无）。新增 `scripts/detect_device.py`（Phase 0/6 先判设备，输出/持久化 DEVICE profile），`experiment-execution` Step 0a 与 INSTALL §2.6 改为"先判设备再选后端/可选 compute extra"，requirements 增 device-conditional compute 段。
- 新增 tests/test_detect_device.py。

### v1.4.0 第六轮：诚实定位——"全领域"措辞修订为"代码可执行的科学"（版本号不变）
- README(中/英)/根 SKILL.md/CITATION.cff：把绝对的"any domain/不限任何学科"修订为**方法全领域、能力边界=代码可执行科学**。
- 新增"Scope & capability boundary/范围与能力边界"：范围内=数值/符号仿真、ML/统计、因果推断、web 检索增强人文社科；范围外=专有/GUI 绑定求解器（商业 CFD、COMSOL、光学台架）与湿实验硬件，除非可脚本化。
- 这是对**证据生产工具**的诚实限定，不削弱方法的全领域性；利于 SCI 审稿可信度。

### v1.4.0 第五轮：防"绕过渲染器"＋防"审计机器被跳过"两个硬门（低能力模型跑测暴露，295 tests 全绿；版本号不变）
- **A 图必须经统一渲染器**：`check_figure_embedding.py --require-renderer` — flat 手写 pdf 或 `figures/<id>/` 缺 `figure_audit.json`+`latex_include.tex` → FAIL；paper-compile Step 5.7 / paper-writing 自检 #8 强制带该 flag。堵住"手写 matplotlib 绕过 Nature 审计/莫兰迪/印刷字号"。
- **B 判定完整性硬门**：`validate_verdicts.py --require-complete` — 注册 verdict 仍 PENDING 且未声明 N/A → exit 1；auto-pipeline wrap-up 与 output-protocol 规定 completion 前必须跑 `--strict --require-complete`，否则 `BLOCKED verdicts_incomplete`。堵住"论文写了但 leakage/logic/citation/claim 审计一个没跑"。
- 新增 tests/test_round5_gates.py（不动既有用例）。

### v1.4.0 第四轮：图嵌入硬门（模型无关，防"图生了没插进正文"，290 tests 全绿；版本号不变）
- 新增 `scripts/check_figure_embedding.py`：机械交叉核对——正文 `\begin{figure}` 数 ≥ 预算，且 `figures/**/*.pdf` 每张都被 `\includegraphics`/`\input` 引用，否则 exit 2。
- `paper-compile` 新增 Step 5.7 Figure-Embedding Gate：exit 2 → `FAIL, figures_not_embedded`，拒编译"图只在磁盘上"的论文。
- `paper-writing` 自检 #8 强化：渲染保留的 `latex_include.tex` 必须被 `\input`，图不得只存在于磁盘。
- 通用、学科无关；针对真实跑测中"9 张图生成但正文 0 图"的组装失误，任何模型都拦得住。论文交付目录不在本仓库改动范围。

### v1.4.0 第三轮自检（断裂/泄露/错误/版本对账，285 tests 全绿；版本号不变）
- **版本对账**：25/25 个 SKILL.md + package.json + CITATION.cff + README 徽章全部 1.4.0（sciforge_style 内部设计版本 v2.x 独立，不计）
- **泄露**：模板 author/affiliation 由 `SciForge-OSS` 改为中性的 `[... to be completed at submission]` 占位（品牌不再进 PDF）；paper-writing 泄漏扫描新增 **Class I（工具品牌 + 虚构 frontmatter）**；模型名复核全清
- **断裂**：output-protocol verdicts 表补 `EVALUATION_REVIEW.json`（已在 validator 注册但表内缺失）；figure-quality-contract §3 字号地板与 v2.2 印刷契约对齐（16/13/13/18/12、线宽 1.8/1.0、marker 7）
- **错误**：ci_check markdown-links / version-consistency / plotting-module / test-suite 全 PASS

### v1.4.0 第二轮完全体加固（LaTeX 浮动/编译尺寸 + 参考图级审美 + 根依赖 + 经验回放 + 静默断点，285 tests 全绿；版本号不变）

**LaTeX 浮动 & 编译尺寸（平衡式）**
- 模板加 `\usepackage[section]{placeins}` + `\usepackage{float}` + `\topfraction/\bottomfraction/\textfraction/\floatpagefraction` 调优 → 图不出本节、不再一图占整页/大空白
- `render_figure.py` 输出 `[!htbp]`（替代自由 `[htbp]`）；`figure_audit.py` A2 新增"float-page 风险"（嵌入高度估 >7.2in → WARN 拆分/加宽）
- `paper-compile` 新增 Step 5.6 确定性检查：placeins 存在 / log 无 "float too large" / 图距首次引用 ≤1 页 / 无纯浮动页

**参考图级审美（精修莫兰迪 + 经典黑白结构）**
- `sciforge_style` v2.2：ink=纯黑 #000000、ink-soft 中性灰、纯白底；仅 y 向浅 grid、去 top/right spines；新增 `series_style/add_error_band/legend_top/figsize_*` —— 实验图 = line+band + 每系列 marker + 顶部横排 legend + log-x（对齐用户给的 640.png）
- unified-plotting 新增 Step 3d「Figure-1 级 overview 构图 recipe」（编号阶段/嵌套容器/图标词汇/度量 glyph/虚线 callout/单主干箭头，对齐 239.png）；figure-complexity-contract §3 增"编号阶段+单主干"线条纪律

**根依赖外置 + 武器库**
- 根新增 `requirements.txt`（core: matplotlib/numpy/Pillow；rec: SciencePlots；optional 注释）；README(中英) 加 `pip install -r requirements.txt`
- INSTALL.md 新增 §0.5「武器库总表」（core/recommended/optional 分层，单入口 render_figure.py 消费，不并行）

**经验回放 + 静默断点 + 失败闭环（CRUX 对应）**
- 新增 `experience-replay-contract.md`：Phase 16 写 `LESSONS.json`（failed_experiments/idea_rollbacks/code_errors/what_worked）并镜像 output/；Phase 2/6b 读取作先验、`avoid` 为硬排除——越用越聪明，失败不当贡献也不静默丢弃
- output-protocol 增 `.sciforge/RESUME_JOURNAL.md` 静默 append-only 变更日志（重启可见变更）
- experiment-execution 增"失败→LESSON"路由

### v1.4.0 全量修复轮（跑测反馈 → skill 全量修正，279 tests 全绿）

**失败假设不再当贡献（负向贡献清除）**
- paper-writing / result-to-claim：贡献列表只收 `polarity: positive`；`boundary`/`negative`（含 "Honest validation boundaries"、"we report these boundaries"、"structurally non-calibratable" 等 framing）一律路由到 Limitations/Discussion，出现在贡献/摘要/结论 → FAIL `negative_result_as_contribution`；paper-writing 自检新增 #12 负向贡献扫描

**图表印刷级 overhaul（太小/字不是黑/太简陋）**
- sciforge_style v2.2：文本/刻度/轴全黑 `#000000`、纯白底 `#FFFFFF`（移除灰褐 ink 与 off-white science 底）；字号地板提升到印刷尺度（轴≥16/刻度≥13/图例≥13/标题≥18/注释≥12）；线宽主≥1.8；新增 `figsize_full/single/panel` 印刷尺寸契约（按最终嵌入宽度渲染，杜绝 8in 图缩到 2in panel）；composite 默认 ≤2 列（3-across 数据图即"字太小"元凶）
- 同步更新 color-themes.md / unified-plotting / figure-quality-contract 指引与示例（黑字白底、≤2 列、印刷字号）

**目录工程化（code/ → src/，去重）**
- 工作区代码目录 `code/` 全量改名 `src/`（13 个 skill 文件 + output-protocol 树 + e2e 测试同步），对齐真实工程框架；`derivations/ experiments/ figures/` 只放产物、`src/` 单家放脚本，paper/ 不再复制代码

**正文 vs 附录 + 篇幅 + 断点**
- writing-principles 新增 §Main-text vs Appendix + 篇幅预算（主结果图/主对比必须在正文；附录只放证明/扩展表/次要鲁棒性/代码；主体 6-9 页、>12 页过长按压缩）；paper-writing 自检 #13 放置+篇幅审计
- output-protocol RUNSTATE 契约强化：每个 sub-phase（1a/1b/2.5/6a/6b/6c/15.5）与后台 dispatch 返回都写断点，"DAG 无一条链路无断点"

**去模型名 + 署名 + 边界**
- 清除 skill 内全部模型名（gpt-5.5 / GPT-4o / Gemini 等 → 占位符/通用表述）；skill 不含 eval harness（纯 pytest 测试保留）
- 致谢名单：Fan L. Q. → Fan L. X.，新增 Zhao J.（中英 README + CHANGELOG 同步）
- INSTALL.md 增补 v1.4.0 边界说明（印刷契约零新增依赖；eval harness 与模型端点均在 skill 外部）

### 端到端跑测版本：work v6.0 边界修正 + RUNSTATE 续航 + RUN_PREPRINT 归档 + WP3 三轮对抗性评审修复

**边界修正（基于全链路跑测反馈）**
- `.sciforge/` 边界收窄：隐藏层只保留管线机制 + 判定（RUNSTATE、MANIFEST、verdicts/、管线日志、审计叙述、tmp）；**研究痕迹（IDEA_CANDIDATES / IDEA_DAG / GAP_ANCHOR_LOG / FRONTIER_MAP / FINAL_PROPOSAL / domain-signature 等）从产出那一刻就写在可见层 `refine-logs/`**，不再"最后才移植"——output-protocol.md、artifact-registry.md、project-architecture-contract.md 及全 35 个相关 skill 文件同步修正

**RUNSTATE 续航契约（Long-Horizon Resume）**
- `.sciforge/RUNSTATE.json`：每个 boundary 与 human checkpoint 重写（current_phase / last_completed_boundary / next_action / status / pending_approvals / budget_snapshot）
- 启动恢复协议：非 completed 的 RUNSTATE 存在时，校验 verdict 完整性 + 迁移 legacy 路径 + 从 next_action 续跑——天级运行不怕会话死亡
- schemas/RUNSTATE.schema.json 已注册

**RUN_PREPRINT 跨 run 归档（AgentRxiv 机制借鉴）**
- Phase 16 新增 `output/RUN_PREPRINT.md` 产出义务：本次 run 的 gap-ids / fired kills / verdict 摘要 / 失败笔记 / 预算消耗
- idea-discovery 可查询同级工作区的 RUN_PREPRINT.md 归档（`PREPRINT:<run-id>#<gap>` 锚定），系统自身历史成为一等文献证据

**WP3 对抗性评审修复（CRUX 失败模式映射，三轮迭代）**
- **Round 1**：BLINDSPOT_CHECK schema severity 枚举扩展（+`learned`）；REVIEW_LEDGER finalized 条目须带 score/verdict；verdicts/ 预留规则（只许注册名，phase-internal 归 refine-logs/）；paper-compile 泄漏扫描路径修正；harness stdin DEVNULL 降噪
- **Round 2**：optional-null 容忍（validator：非必填字段 null 当缺省处理）；REVIEW_STATE `response_class` 必填强调
- **Round 3**：paper-writing abstract/conclusion 追溯规则（逐句对照 CLAIMS_FROM_RESULTS，失败假设只能按限制性结论处理）；result-to-claim 失败 pre-registration 必须重定为 LIMIT/NEGATIVE（不许把失败的 claim 改头换面当新 claim）；method-registry 校准参数必须带 sensitivity sweep（单点 match 不算验证）；citation-audit 不许带着未修复的 FIX 项关闭
- **Round 3 补充**：LEAKAGE_AUDIT schema `callback.iteration` 最小值 1→0（无回调的正常审计可迭代 0 次）；注册 EVALUATION_REVIEW.json（对抗性评审 verdict，21 个注册 artifact）

### 许可证变更：MIT → PolyForm Noncommercial 1.0.0
- LICENSE 由 MIT 更换为 [PolyForm Noncommercial License 1.0.0](LICENSE)，版权声明改为 GewisLab
- 个人及非商用用途免费（科研、学习、教育、公益、政府机构等）；商用用途不在协议授权范围内，需另行购买商业授权
- 同步更新 package.json / CITATION.cff / SKILL.md 的 license 字段，以及 README（中英）的徽章与许可章节
- 注：历史 CHANGELOG 条目中记录的 "MIT" 为该版本发布时的真实状态，保持不变

### 致谢更新
- 计算资源（API token）提供者致谢名单新增 Wang C. Y.、Fan L. X.、Zhao J.（中英 README 同步）

：MIT → PolyForm Noncommercial 1.0.0

- LICENSE 由 MIT 更换为 [PolyForm Noncommercial License 1.0.0](LICENSE)，版权声明改为 GewisLab
- 个人及非商用用途免费（科研、学习、教育、公益、政府机构等）；商用用途不在协议授权范围内，需另行购买商业授权
- 说明：本协议属于 source-available 许可，不再是 OSI 定义的开源协议
- 同步更新 package.json / CITATION.cff / SKILL.md 的 license 字段，以及 README（中英）的徽章与许可章节
- 注：历史 CHANGELOG 条目中记录的 "MIT" 为该版本发布时的真实状态，保持不变

### 致谢更新

- 计算资源（API token）提供者致谢名单新增 Wang C. Y.、Fan L. X.、Zhao J.（中英 README 同步）

## [1.3.2] - 2026-08-09

### fix-bug 第二轮：判定文件位置/形状契约的系统性对账（4 个提交，274 tests）

**🔴 REVIEW_LEDGER 形状冲突（known gap #1）——外部 verifier 拒绝官方 fixture**
- `verify_review_ledger.sh` 对 per-round verdict 强制 6-state 信封词汇、且要求每条 rounds[] 条目带 action_items——而轮次 verdict 的合法词汇是 review 循环的 `ready`/`almost`/`not_ready`，终止条目（phase=finalized）天然没有 action_items。**canonical e2e fixture 自己都过不了外部验证**，真实 run 的 ledger 必被拒
- 修复：per-round 词汇表改为 review 循环词汇（兼容 6-state 写法）；finalized 条目只要求 score+verdict
- auto-review-loop Phase E.5 重写为注册契约：**单个 JSON 对象**（不是 JSONL 流）写在 `.sciforge/verdicts/REVIEW_LEDGER.json`（不是 audits/），轮次历史在 `details.rounds[]`，信封/per-round 词汇分工写明；REVIEW_STATE 路径同步修正
- BLINDSPOT_CHECK 同病同治（known gap #2）：单文件覆写最新轮、历史进 AUTO_REVIEW.md；路径 audits/→verdicts/

**🔴 机读 verdict 错位 audits/ 的批量清扫（v5.2 陈旧路径 × v6.0 批量迁移的复合遗留）**
- 11 个文件中 `.sciforge/audits/*.json`（LEAKAGE_AUDIT / INVARIANT_CHECK / LOGIC_VERIFICATION / REVIEW_STATE …）全部改回 `.sciforge/verdicts/`——机读判定只住 verdicts/
- LOGIC_CHECK_STATE.json（未注册的恢复状态）移入 `.sciforge/logs/`（既不能进 verdicts/ 触发未注册 WARN，也不是叙述报告）
- output-versioning 阶段表拆分为机读/叙述两行

**🟡 validator 加固 + fixture 归位**
- `validate_verdicts.py`：verdicts/ 内除 PIPELINE_VERDICT_SUMMARY.md 外的任何 .md → WARN（叙述报告误入判定目录的哨兵）
- e2e fixture 的 METHOD_REGISTRY_SNIPPET.md（哈希靶标）移出 verdicts/ 至 `fixtures/e2e_minimal/methods/`（新哨兵下保持全绿）

**🟢 其他**
- `sciforge init` + package.json `files` 带上 tests/ + fixtures/——下游安装可自验（ci_check 原样跑）
- schemas/README known gaps 关闭 7 个（#1/#2/#3/#5/#6/#7/#11，#6 字段名由 fixture 钉死并记录）；剩 4 个均为设计内良性项
- 回归测试 +10（264→274）：review 词汇/finalized 条目通过、未知轮次词汇拒绝、误入 .md WARN/strict 拦截、PIPELINE_VERDICT_SUMMARY.md 豁免

**README 正式化（中英）**
- **致谢重写**：正式行文 + 规范署名——Luo H. W.（GewisLab 负责人，项目发起/核心思路/架构设计）、Yang J. T.（主要开发者）；Yang J. T.、Lu Y. H.、Li L. S.、Jia W. H.、Qiu Y. M.、Zhang W. B. 提供计算资源（API token）支持；中英文同步
- **内部治理代际全部清出 README**：README 禁止出现内部代际标识（v2.x/v3.x/v5.3/v6.0 等）——"Quality gates (v5.3)"/"质量门（v5.3）" 等标题与树注释、正文括注一律删除，发布版本以徽章为准；"260+ pytest 用例"更新为 270+；安装注记陈旧的 "v1.3.0" 标签改为当前版本 v1.3.2
- **FAQ 整段删除**：常见问题内容鸡肋且与正文重复（安装/快速开始/CONTRIBUTING 已覆盖），两个 README 的 FAQ 章节与目录条目直接移除
- **中文验证路径对齐**："三路可选"→"四路可选"（补 qualitative/综述路），删除"OSS 无实验环境"陈旧表述（v2.0 起即有 toy+full 实验门），路由依据改为 Phase 6 verification-routing 表述
- 质量门表格 verdict 路径钉死为 `.sciforge/verdicts/`

**验证**：274 tests 全 PASS；ci_check 四项 OVERALL PASS；verifier 对 canonical fixture 实测 PASS；security_scan 23/23；零 CJK 维持（README.zh 为有意中文）。


## [1.3.1] - 2026-08-09

### v6.0 迁移后的 fix-bug 轮（15 处修复 + 6 个回归测试）

**功能性 bug（会让门控/工具在 v6.0 工作区上失效）**
- **外部 verifier 找不到 v6.0 verdict 路径**：`verify_review_ledger.sh` / `verify_paper_audits.sh` 只解析 v5.2（`verdicts/`）与 pre-v5.2（`review-stage/`、`paper/`）位置——v6.0 工作区（`.sciforge/verdicts/`）上必然报 "not found"，assurance 门控静默降级。解析顺序修为 `.sciforge/verdicts/` → `verdicts/` → legacy stage dirs（含 ledger 定位、check_audit、KILL_ARGUMENT 探测、错误信息与头注释）；新增 `tests/test_verifier_paths.py` 6 例锁住顺序（含 v6 优先于 legacy、全缺失 FAIL）
- **paper-writing 泄漏扫描清单重复 + 漏扫**：scrub 门控的内部路径清单里 `.sciforge/audits/` 重复两次（audit_report/ 与 review-stage/ 迁移塌缩），且漏了 `.sciforge/verdicts/`、`.sciforge/logs/`、`code/`——管线路径泄入正文可绕过扫描。去重 + 补齐

**契约一致性（13 处陈旧表述）**
- idea-discovery Round-1 "3 perspectives" → 4（theoretical/computational/qualitative/empirical）
- 7 处陈旧 `.sciforge/PIPELINE_STATUS.json` → v6.0 契约（事件入 `.sciforge/logs/pipeline.log`，标志入 `.sciforge/PIPELINE_STATUS.md` 执行报告）；publishability-score 的 Input/Output 路径同步钉死
- domain-adaptive-pipeline "20 phases" → 21
- `quality_gate/` 四个报告登记在一个任何树里都不存在的目录 → `.sciforge/audits/`（registry×4 + quality-gate SKILL + output-protocol 清单）
- `idea-stage/` 遗留路径 → `.sciforge/refine-logs/`（idea-dag-schema×4 + output-versioning 阶段表）
- mcts-search-protocol / idea-dag-schema 声称 OSS 明令禁止的 "legacy pilot fallback" → 改为拓宽视角重跑 fallback；effort-contract "idea-discovery pilots" 行（OSS 无 pilot）→ MCTS rounds
- artifact-registry 中 IDEA_REPORT/IDEA_DAG 的迁移注解误称经过 v5.2 `verdicts/` → 修正为 refine-logs 链
- 5 处 "5-axis" idea-fit → 6-axis（EG 轴 v3.0 已加入）
- startup-protocol 启动提取字段清单补 `evidence_norm_profile`
- output-protocol audits 行迁移塌缩三倍重复 → 修正为 legacy 三目录名

**验证**：270 tests 全 PASS（新增 verifier 路径回归 6 例）；`ci_check.py` 四项 OVERALL PASS；validator e2e 20/20；security_scan 23/23；verifier 三场景实测（v6.0 / legacy / 缺失）。


## [1.3.0] - 2026-08-09

### 判断力深化：文献先行 gap 链 + 证据门槛学习 + `.sciforge/` 双层工作区（v6.0）

> 本轮主题直接来自 CRUX 影子评估（arXiv:2607.27191，普林斯顿等 20+ 研究者把未公开 NeurIPS 真题交给 Opus 4.8 全流程做科研、原作者阅卷全拒）的判断力缺口分析：**工程满分、科学零分**的五个失败模式中，#1（不知道好论文长什么样/识别不了文献空白）与 #4 的对称面（有钱不会花）在此前版本只有部分防线，1.3.0 把防线修到链路上游。论文模板与配色体系不动；论文产出后的投稿/申诉维持人类职责（rebuttal 保持 advisory）。

**P0 — 文献先行 gap 链（idea 生成链路重构）**
- **universal-retrieval 波浪协议**：Phase 4 改为波浪式——**广谱波**先跑，产出 `literature/GAP_REPORT.md`（gap-id + gap_type∈{contradiction, unsolved_node, method_blank, data_blank, generalization_blank} + ≥1 个已验证引文证据键）；MCTS 选出存活 idea 后，每个 idea 一波**定向波**（追加进 `literature/TARGETED_WAVE_LOG.md`，含撞车预检），bib 全程累积不分叉
- **idea-discovery gap 锚定**：每个晋级 idea 必须引一个 gap-id（或每轮至多 2 个 `exploratory` 豁免名额）；无锚且无豁免理由的 idea relevance 轴封顶 0.5（够不到 0.6 晋级线）——无文献锚的 idea 正是"薄弱结果包装成发现"的源头（CRUX 失败模式 #1）；idea 卡片必填字段 5→6（新增 `gap_anchor`）；锚定/重锚决策全程记录 `GAP_ANCHOR_LOG.md`
- **novelty-check 联动**：FRONTIER_MAP 未解决节点与 GAP_REPORT gap-id 交叉链接；引用不存在的 gap-id → `gap_anchor_invalid` FAIL；撞车审计消费定向波的预检记录
- **auto-pipeline Group A 重连**：广谱波先行，gap 锚定与全部终评分必须等 GAP_REPORT 就绪（`pending-literature` 语义扩展）；21 阶段 DAG 结构不变

**P0 — `.sciforge/` 双层工作区（v6.0）**
- **隐藏状态层**：`.sciforge/` 收纳 RUNSTATE.json / MANIFEST.md / APPROVAL_LOG.txt / PIPELINE_STATUS.md / verdicts/（v5.2 扁平契约不变，只搬家）/ 管线日志 / refine-logs/（含 FRONTIER_MAP、GAP_ANCHOR_LOG、abandoned/）/ audits/（audit_report + review-stage + citation_audit 叙述报告合并）/ tmp/
- **交付层只留科研交付物**：literature（含 GAP_REPORT）/ methods / derivations / code / experiments / figures / paper / output + logs/（恢复本义：只放实验/训练日志）——人类打开成品工作区看到的是一个干净的 GitHub 式项目
- **懒实例化 + 路由感知 N/A（人文场景动态清理）**：目录只在首次规范写入时创建，不再预建骨架；`VERIFICATION_ROUTING.json` 新增 `na_verdicts` 声明（theory-only 默认集 = EXPERIMENT_MATRIX / EVALUATION_PROTOCOL / BUDGET_FLOOR / REGISTRY_HASH 四项；后续声明式 skip 只增不减，如 Phase 11 无图追加 FIGURE_AUDITS）——`validate_verdicts.py` 对声明缺失报 **N/A 而非 pending**（声明了却产出 → WARN），wrap-up 清理把对应缺目录视为合法，人文 run 不再有空文件夹、verdict 汇总不再撒谎（"14 pass, 4 na" 而不是 "14 pass, 4 pending"）
- **RUNSTATE 长续航契约**：每个 phase boundary 与人类检查点重写 `.sciforge/RUNSTATE.json`（schema 已注册）；orchestrator 启动先跑恢复协议（校验 verdict 完整性 → 迁移 legacy 路径 → 从 next_action 续跑）——天级运行不再怕会话死亡（CRUX 失败模式 #5 的工程解）；AGENT_GUIDE 的口语化 resume 说明替换为契约引用
- **迁移兼容**：读新路径优先、legacy 路径回退；写永远走新路径；恢复时自动迁移并记录清理事件

**P1 — 证据门槛学习（evidence_norm）**
- domain-learner 增学 `evidence_norm_profile`（样本量规范 / 对照设计规范 / 效应报告规范 / 负结果规范 / 标杆期刊），从文献中读"标准"而不是读"结果"；survey 不足则保守默认并 WARN，绝不编造规范
- 三个消费点接线（domain-signature-consumer.md 登记）：result-to-claim 的 evidence_sufficiency 按学科门槛校准（低于学科规范封顶 partial）；experiment-execution 的 full 矩阵规模对齐学科规范（toy 可小、full 必须够）；publishability-score 证据强度维按标杆期刊门槛打分、负结果规范决定负结果框架是否直接可发——**这是对"不知道好论文长什么样"的结构性解药**
- domain-signature（1a hint）可携带粗粒度 evidence_norm 先验，learner 始终为准

**P1 — 预算低耗守卫（失败模式 #4 对称面）**
- wrap-up 与每次完成声明时：预算利用率 < 50% 上限 ∧ verdict 仍有 pending/IN_PROGRESS（或 BUDGET_FLOOR 未满足）→ WARN `budget_underuse`（用量表 + 未决 verdict 清单入 PIPELINE_VERDICT_SUMMARY + pipeline.log），完成声明被既有的 completion-declaration 拦截器接管（completion_justification 必须解释每条未试路线）——便宜地解决是允许的，静默欠探索不允许

**治理同步**
- artifact-registry 全部路径列迁移至 v6.0；新登记 GAP_REPORT.md / TARGETED_WAVE_LOG.md / GAP_ANCHOR_LOG.md / RUNSTATE.json（后者注明非 verdict、不走 validate_verdicts）；VERIFICATION_ROUTING 行补 na_verdicts 产出/消费
- project-architecture-contract v3.0：标准布局重写为双层结构；根目录白名单、隐藏文件规则、README/MANIFEST 契约同步
- schemas：VERIFICATION_ROUTING +na_verdicts；新增 RUNSTATE.schema.json；schemas/README 登记 N/A 机制与非 verdict schema；关闭 known gap #9（VERIFICATION_ROUTING 路径陈旧）
- verification-routing.md §5：na_verdicts 默认集与扩展规则；output-manifest / startup-protocol / pipeline-integrity 等 52 个文件路径同步迁移

**验证**：264 tests 全 PASS（新增 RUNSTATE schema 守卫 / theory-only N/A / 声明 N/A 却产出 → WARN 三例）；`ci_check.py` 四项 OVERALL PASS；validator e2e fixture 20/20（hybrid 0 na）；`security_scan.py --self-test` 23/23；skills/ + AGENT_GUIDE.md + tests/ + scripts/ 零 CJK 维持。


## [1.2.0] - 2026-08-09

### v5.3 治理加固 + 全英文化 + 工程化基础（hardening pass）

**P0 — 修复静默腐烂**
- 目录权威统一：`output-protocol.md` 成为目录结构**唯一权威**；`artifact-registry.md` 只登记 producer/consumer/schema/verifier，路径逐行同步到 v5.2 `verdicts/` 路径（REVIEW_STATE / REVIEW_LEDGER / CITATION_AUDIT / PROOF_AUDIT / KILL_ARGUMENT / REGISTRY_HASH / LEAKAGE_AUDIT / INVARIANT_CHECK / IDEA_REPORT / IDEA_DAG…），新增"v5.2 机读评判产物"登记表（17 行）+ RUN_BUDGET 行
- 孤儿引用清零：新增 `/rebuttal` skill（投稿被拒后的申诉信生成，管线缺口）；实现 `scripts/verifiers/verify_review_ledger.sh` + `verify_paper_audits.sh`（registry 承诺但从未存在的两个 external verifier）；`/auto-paper-improvement-loop` / `/research-refine-pipeline` / `/experiment-plan` 显式标注 "deferred（未随 OSS 分发）"；ESTIMATOR_VERIFICATION 标注 inactive（INV-E5 已移出 OSS）
- CI 从无到有：`scripts/ci_check.py`（① md 断链扫描 ② 全仓版本号一致性 ③ plotting 三模块语法 + `--doctor`）+ `.workflow/ci.yml`（AtomGit Actions）+ `.pre-commit-config.yaml`
- composite 组图真矢量：引擎在预览 SVG 之外产出**矢量面板 + `composite.tex`**（LaTeX 侧组图，graphicx-only，standalone/`\input` 双模编译）+ `composite_meta.json`（`raster_panels: true` 审计降级 A2 WARN）；`latex_include.tex` 指向 composite.tex；修复 caption 转义潜在 bug

**P1 — 能力上限**
- 评判 Schema 强制（v5.3）：`skills/shared-references/schemas/` 16 份 draft-2020-12 JSON Schema + `scripts/validate_verdicts.py`（stdlib-only 子集校验器 + 6 态词表 / `audited_input_hashes` / BUDGET_FLOOR / KILL `PASS⇒still_unresolved==0` 跨字段不变量）；orchestrator 每个 phase boundary 与收尾运行（违规 → WARN，`--strict` → BLOCKED）
- plotting 测试底座：`tests/` 166 用例（色板 C*/对比度属性测试、A1–A10 fixture、渲染器冒烟、validator、e2e smoke）；发现并修复 tikz v2.0 色板漂移（注入色与 TOKENS 脱节 + `palette_check` 漏 `{HTML}`/`rgb()` 语法 → 注入色改活源 `extract_colors` 全语法）
- 全局预算总账：`verdicts/RUN_BUDGET.json`（wall_clock / api_cost / pivot_count / ba_used + effort 档位 limits + per_phase），orchestrator 每个 boundary 记账核对，超限 BLOCKED 上报人类；旧 `BA_BUDGET.json` 记账并入（只读回退）
- 实验安全门：`scripts/security_scan.py` 静态扫描（SEC-001–011 BLOCKED 级 + SEC-101–107 WARN 级，fail-closed，allowlist 只豁免 WARN/出口类）；experiment-execution Step 5.00 将"先扫描后 dispatch"硬接线进固定序列，DISPATCH.json 记录 `security_gate`
- KILL 人类检查点（v5.3，默认 ON）：kill-argument 产出后暂停等待人类确认才允许换 idea（L5/L7/L9/L11/L13 全路径）；`human_skip=true` 或 `kill_checkpoint=false` 才全自动；确认记录进 `APPROVAL_LOG.txt`，下一 boundary 缺记录 → BLOCK

**P2 — 体验与可维护性**
- 25 个 SKILL.md 全英文统一（零 CJK；机读字段/路径/链接不变；术语表统一：kill argument / loop-back / budget floor / collision audit / budget floor…）
- A10 文字重叠检测升级：viewBox+font 度量精确 bbox + tspan 换行/dy 累积 + 祖先 `<g>` transform 合成（translate/scale；rotate/matrix 标记 unsupported 安全跳过）；`CHAR_WIDTH_ESTIMATES` 常量化可测
- e2e 冒烟 fixture：`fixtures/e2e_minimal/`（合成问题 + 秒级 toy 实验 + 17 项 mock verdicts，`validate_verdicts.py` 全 PASS、真实哈希）+ 9 项守卫测试（21-phase 计数、14 目录树双向核对、哈希重算）
- 清理：`scripts/plotting/__pycache__/` 删除；output-protocol"15 个目录"→14、auto-pipeline"20 phases"→21 等 prose 漂移修正

**版本号统一至 1.2.0**：根 SKILL.md + plugin.json + package.json + CITATION.cff + 25 子 skill + VERSIONING.md + README 双语徽章。

**验证**：166 tests 全 PASS；`ci_check.py` OVERALL PASS（0 断链、版本一致、`--doctor` READY）；e2e fixture 17/17 verdict PASS；`security_scan.py --self-test` 16/16。

### v5.3 加固补丁（follow-up on the hardening pass，发布前并入 1.2.0）

- **CI 真正跑测试**：`ci_check.py` 新增第 4 项检查 `test-suite` —— pytest 全量用例 + `validate_verdicts.py` e2e fixture + `security_scan.py --self-test`；缺 pytest 判 FAIL 而非跳过（裸克隆不能静默过 CI）。`.workflow/ci.yml` 相应安装 pytest + Pillow
- **doctor() 诚实化**：diagrams/cairosvg 两行此前调 `which("python3")` 冒充 import 检查（包缺失也报 OK）——改为子进程真实 import（v5.3 fix）
- **figure_audit 陈旧清理**：模块 docstring A1/A2 描述仍是 v3 PNG 时代（output.png / dpi≥300）——更新为 v4.0 PDF+SVG 契约；`audit_layout_svg` 裁剪启发式忽略 font-size 的 pt 单位（宽度高估 1/0.75）——改经 `_parse_size` 归一
- **色彩数学精确化**：`rgb2lab` 白点除数与矩阵行和不一致（L*(white)=100.0000039）——改为以矩阵自身行和为参考白，纯白精确映射 (100, 0, 0)；`is_morandi` docstring"per channel"措辞修正为整体欧氏距离
- **RESULT.json 契约补齐**：experiment-execution 输出 schema 此前未承诺 `core_claim_validated` / `seeds_used`，而 auto-pipeline Phase 6b toy 门控读取这两个字段——补为必填并说明门控语义
- **verdicts/ 树补全**：`FIGURE_AUDITS.json` 与 `PIPELINE_VERDICT_SUMMARY.md` 此前只在注释中出现——补进 output-protocol verdicts/ 树（单一权威规则：树外无 verdict 文件）；e2e fixture 补 `RUN_BUDGET.json`，validator 达 18/18 零 pending
- **孤儿引用二轮清扫**：`/discipline-writing`、`/paper-modes`（实为共享参考文档，消费者表改正为 `/paper-writing` 经文档消费）、`/competitive-drift-monitor`（标注 deferred/advisory）
- **对抗性自审加固（9 项 MAJOR 全修，新增 95 个回归测试）**：
  - security_scan 六类 BLOCKED 级绕过封堵：subprocess 列表形 ssh/scp/curl、内联 `socket().connect()`、内联 `dict(os.environ)` 外泄（allowlist 不得豁免）、拼接凭证路径（常量折叠）、os.open/shutil/Path 变量三条 /etc 写入向量、`codecs.decode` base64 exec；**移除脚本旁 security_allowlist.txt 自动加载**（agent 不得自写豁免，仅 `--allow` 显式传入）
  - figure_audit 畸形数值崩溃修复（`font-size=".."` 等 → WARN 而非 traceback，渲染管线不再被杀）
  - composite 标签/用户 caption 的 TeX 转义 + SVG 标签 XML 转义（`a_b`/`x%y`/`m&n` 类标签此前使产出的 .tex 编译失败、SVG 不成良构）
  - 色板门禁补 `#RGB`/`#RRGGBBAA` 形态（此前饱和越界色以短写/带 alpha 形态溜过 A3）
  - validate_verdicts 严格 JSON（拒绝 NaN/Infinity——此前可绕过数值界限检查；深嵌套 RecursionError → 干净 FAIL）
  - ci_check 链接扫描加固（代码围栏内示例不检查、嵌套括号/尖括号目标、query 剥离、scheme-relative 外链、Python version 类误报）
  - verify_paper_audits 拒绝哈希逃逸工作区的 audited_input_hashes 键（`../../etc/hostname` → STALE 拒绝）
- **shared-references 全英文化（政策收尾）**：35 个含中文的共享契约文档 + AGENT_GUIDE.md + plotting INSTALL.md 全部译为英文（零 CJK）——skill pointer-load 链路上不再有语言切换；机读内容（产物名/字段/JSON 键/代码围栏/链接/数值阈值/表格结构）逐字节保留；output-protocol 目录树结构（含 20 个 verdicts/ 固定名）字节级不变，e2e 守卫测试通过；术语表与 SKILL.md 一致（verdict / loop-back / kill argument / budget floor / gate / human voice ...）
- **磁盘遗留二轮清理**：`.ipynb_checkpoints/`（仓库根 + scripts/plotting/）删除
- **发布清单修复**：package.json `files` 移除已删除的 `problems/`（v1.1.1 删库后遗留），补入 `scripts/`（工具链随 skill 分发）+ `LICENSE` + `VERSIONING.md`；`sciforge init` 脚手架补拷贝 `scripts/`（此前新建项目缺绘图/校验/安全扫描工具链，而 skill 以仓库相对路径引用它们）+ LICENSE/VERSIONING
- **FIGURE_AUDITS.json 幽灵契约修复**：该产物在 output-protocol 树与 registry 登记，但产出方 unified-plotting 只字未提（违反 registry 自身的 phantom-artifact 规则）——补 Step 6.5 产出义务（每次渲染后 upsert 镜像）+ `schemas/FIGURE_AUDITS.schema.json` + validator 注册 + e2e fixture 条目（19/19 零 pending）
- **README 双语同步至 v5.3**：项目结构树补齐 scripts 新工具（validator/security_scan/ci_check/verifiers）、tests/、fixtures/、.workflow/、schemas/、rebuttal skill；新增「质量门（v5.3）」章节（双语）；PDF+PNG 陈旧表述更正为 v4.0 的 PDF+SVG
- **CONTRIBUTING / AGENT_GUIDE 对齐 v5.3**：CONTRIBUTING 重写（本地门控 ci_check+pytest、PR 冻结约定、英文-only skill 政策、verdict 注册流程）；AGENT_GUIDE 修复陈旧点（"17-Phase"→21、3→4 视角、补 5 个缺失 skill、补 Phase 5b EG、"OSS has no experiments" 错误表述更正为 v2.0 起即有 toy+full 实验、验证路径 3→4 条、新增 KILL 检查点与 v5.3 契约行）
- **入口清单对齐**：根 SKILL.md 与 plugin.json 技能数 24→25（support 14→16，补 publishability-score/rebuttal），description 补 v5.3 特性；"No experiment dependencies" 更正为实验友好表述；pre-commit hook 名称补测试套件
- **EVALUATION_PROTOCOL.json 幽灵契约修复（第二例）**：method-registry §3.6 与 experiment-execution 引用 `verdicts/EVALUATION_PROTOCOL.json`，但 output-protocol 树 / registry / schemas / validator 均无登记——四处补齐（最小 schema + registry 行 + e2e fixture，validator 达 20/20 零 pending；四件套字段名未定型记入 schemas/README 已知缺口 #12）
- **产出方义务三补齐（引用扫描反向核对）**：树中登记但 SKILL.md 从未提及产物路径的三处——experiment-execution 补 `verdicts/BUDGET_FLOOR.json` 持久化义务（此前仅为 Return payload 字段）；theory-derivation 补 `verdicts/PROOF_AUDIT.json` always-emit 义务（含 NOT-COHERENT 分支的 verdict 语义）；auto-pipeline 补每个 boundary 重写 `verdicts/PIPELINE_VERDICT_SUMMARY.md` 的义务。至此 20 个 verdicts/ 条目全部 producer/consumer 落字

**验证**：261 tests 全 PASS；`ci_check.py` 四项检查 OVERALL PASS；`security_scan.py --self-test` 23/23；validator e2e fixture 20/20 零 pending；skills/ + AGENT_GUIDE.md + tests/ + scripts/ 零 CJK（grep 全仓扫描）。

## [1.1.2] - 2026-08-09

### 管线治理四件套 + 判断力防线 + 实验优先验证（v5.0–v5.2 治理系列）

**v5.0 experiment-first 全面改造**
- 验证路由契约（`verification-routing.md`）：experiment-first 默认（toy ~20 轮作想法生死判）；theory-only 仅留给 derivational ∧ 无可执行计算（纯数学/部分人文）；theory-derivation 降级为可选辅助
- 长实验防超时：后台调度阈值（>15min 或 ≥5 组强制后台 + STATUS.json 60s 心跳 + 轮询分级）+ subagent 委托协议（≥3 独立组或 ≥6 配置必须委托，零共享状态、RESULT.json 契约）
- idea 撞车审计（novelty-check）：TOP-5 三维矩阵（same_problem/method/data）+ 冲突处置树 + differentiation.md；文献时效硬门槛（universal-retrieval，近 2 年 ≥40%）
- 强制实验矩阵（method-registry §3.5，随 Section 3 hash-lock）：主实验 + 基线≥3 + 消融 + 超参 + 敏感性；budget_scale full/lite/pilot
- 从 0 到 1 停止协议（KILL-or-PIVOT）：负向显著且 ≥2 种子可复现才触发；PIVOT ≤2 次预算
- 负结果纪律：负结果永不作 contribution——主实验级负向回传 KILL/PIVOT，局部负向只进 Limitations；claims 带 polarity 字段
- 目录统一（output-protocol）：`code/` 代码单一之家 + `logs/` 日志集中 + 单一之家原则 + paper-writing SYMLINK-ONLY 禁 copy

**v5.1 判断力防线（源自普林斯顿 CRUX 影子评估 arXiv:2607.27191 五项失败模式）**
- 证据充分性门控（result-to-claim）：统计效力/效应量/≥3 种子/toy 范围/基线对照五项检查；不足禁止包装成"发现"
- 反缩减协议（auto-review-loop）：连续拒稿状态下措辞性修复作废，只允许实质响应（重设计实验/PIVOT/KILL）
- 问题内容哈希冻结（invariant-check INV-G1）：SHA256 冻结问题陈述，禁止借负结果改写研究问题
- 探索预算下限（experiment-execution）：≥2 技术路线 + 矩阵 100% + 种子足额 + 失败留痕；"我写完了"需 completion_justification
- 约束重注入 + 页数硬门：phase boundary 原文复述硬约束 + 超页硬 FAIL

**v5.2 治理四件套**
- `verdicts/` 评判统一目录：16 类机读 verdict/hash/审计 JSON 收敛单一平铺目录；12 个产出方 skill 接入
- 工作区整洁契约（output-protocol）：命名规范 / 版本号只进内容 / 临时文件禁令 / 孤儿产物治理 / 收尾清理协议
- 回环完整性登记表（auto-pipeline）：L1–L13 全部回环唯一权威清单（触发/目标/预算/耗尽出口）；修复 6b 门控与 KILL-or-PIVOT 的矛盾断点；BA 预算全局共享 ≤2 轮
- 公平评测（method-registry §3.6 预注册 + experiment-execution + result-to-claim）：指标锁定 / 基线同条件对齐 / 基线强制本环境重算 / 禁 cherry-picking（全种子均值±std + 全网格）
- 反 AIGC 活人感契约（writing-principles §0.5 + paper-writing Step 5）：AI 腔黑名单 7 类可机器计数 + 活人感正向特征 + 论文体 vs 报告体判别 + 五领域惯例适配

**版本号统一至 1.1.2**：根 SKILL.md + plugin.json + package.json + CITATION.cff + 24 子 skill + VERSIONING.md + README 双语徽章。

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