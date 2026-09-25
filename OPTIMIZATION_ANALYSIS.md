# SciForge-OSS 优化分析：从 Skill 包跃迁到 RSI 级 Auto-Research 开源项目

> 分析日期：2026-09-25 ｜ 依据：本仓库 README/orchestrator/CHANGELOG 全量阅读 + AUTO_RESEARCH_LANDSCAPE.md 调研 + 5 个标杆项目源码级架构对比（AI-Scientist-v2 / EvoScientist / AgentLaboratory / DeepScientist / STORM）

---

## 一、现状诊断：SciForge-OSS 是什么，缺什么

### 1.1 本质定位

SciForge-OSS 当前是一个**知识包（knowledge pack）**，不是运行时（runtime）：

- 21-phase DAG、6-state verdict、预算账本、fallback 契约、经验回放——全部是 **Markdown 契约**，靠宿主 agent（Claude Code/Cursor/Trae）"自觉遵守"
- `scripts/` 下只有校验工具（validate_verdicts / sciforge_audit / ci_check），**没有控制循环**
- "谁在推进 phase、进程挂了谁恢复、token 谁在数、模型谁在选"——这些问题的答案目前是"宿主 agent 自己看着办"

### 1.2 已经领先的资产（不要丢）

对比 5 个标杆项目，我们在**契约工程**上其实是最强的一家：

| 资产 | 竞品对照 |
|---|---|
| verdict JSON Schema + `validate_verdicts.py --strict --require-complete` | AI-Scientist v2 无 schema 层；AgentLaboratory 无；这是我们独有 |
| RUN_BUDGET.json 全局预算账本 + budget-underuse guard | 全部 5 家都没有"预算欠花"这一半——只防超支不防偷懒 |
| RUNSTATE.json 长续航断点契约 | AgentLaboratory 用 pickle 每阶段快照；我们契约更完整但**没有代码执行它** |
| LESSONS.json 经验回放 + RUN_PREPRINT 跨 run 归档 | EvoScientist 有 memory 图谱（代码强制）；我们只有 Markdown 约定，靠 agent 记得去读 |
| Loop-Back Integrity Registry（L1–L13 回路预算表） | 没有任何竞品有形式化的回路登记——这是 RSI 的天然骨架 |
| 修订模式 mode=revision、单入口哲学 | 竞品全部是多入口脚本，我们的"一管线不分学科"更干净 |

### 1.3 五个标杆项目共同具备、而纯 Markdown skill 必然缺失的运行时能力

（源码级调研结论，逐家核实过实现文件）

1. **持久化可恢复的控制循环**：AI-Scientist v2 是 `while current_stage` 状态机 + `checkpoint.pkl`；DeepScientist 每个 turn 由 daemon 路由落盘（`events.jsonl` + `runtime_state.json`，quest 即 git 仓库，可重放可接管）。Markdown 提供不了"进程死了之后循环还活着"。
2. **嵌在控制流里的机械质量门**：AI-Scientist v2 的 BFTS 树搜索要求"必须优于 baseline 节点"才能推进（代码判分）；AgentLaboratory 的 `code_repair` 限次重试且把报错历史注入"勿重复"。我们的门（validate_verdicts 等）写成了脚本，但**调用时机仍靠 prose 规定**——低能力模型漏跑一次门，整个审计链就静默失效（你们 v1.4.0 已经观测到"论文写了但审计一个没跑"，本质就是这个问题的症状）。
3. **provider 抽象层**：STORM 用 litellm 逐组件配模型（对话模拟用便宜模型、成文用强模型）；AI-Scientist v2 有 `--model_writeup/--model_review` + backoff 重试 + `track_token_usage`。我们无 provider 层，RUN_BUDGET 的 `api_cost_usd` 只能靠 agent 自报（契约里自己都承认 "when the runtime exposes token/cost accounting; otherwise keep last value"）。
4. **真正的并发调度**：AI-Scientist v2 `num_workers/num_seeds/num_drafts` 并行树扩展；EvoScientist 有 daemon + cron + stream-json 输出。我们的"后台派发"是把 nohup 指令写在 Markdown 里求 agent 执行。
5. **代码级 HITL 与沙箱策略**：EvoScientist execute 默认人工审批 + `shell_allow_list` 白名单，DeepScientist 人可随时 pause/take over——都由代码强制。我们的 human checkpoint 是 prompt 里的"请等待人类确认"，agent 完全可以忘记。

### 1.4 对症：你说的四个局限，全部指向同一个根因

- **纯 skill 对低能力模型不行** → 因为没有运行时兜底，知识正确≠执行正确；漂移检测（v5.1 Constraint Re-injection）本身也靠 prose
- **可控性不够** → checkpoint/kill/预算全靠自觉
- **智力不够** → 没有 provider 分层（便宜模型干粗活、强模型干判分）、没有并行多 seed 采样提智
- **自主度不够** → 单问题单 run 是契约设计限制，但更根本的是：没有 daemon，就谈不上"过夜自主跑、跨 run 成纲领"

**根因一句话：SciForge-OSS 把 21-phase 的"知识"和"控制"焊死在同一层 Markdown 里。跃迁 = 把两者拆开。**

---

## 二、目标架构：Runtime Kernel + Skill Library + RSI 进化层

### 2.1 三层分离

```
┌────────────────────────────────────────────────────────┐
│ L3  RSI 进化层（Evolution Loop）                        │
│     跑完→审计本次 run 的全部事件/verdict/LESSONS        │
│     →生成对 skills/*.md 和 kernel 配置的 patch 提案     │
│     →对抗评审→硬门（ci_check+e2e smoke+golden set）     │
│     →合入 git→下一代更强                                 │
├────────────────────────────────────────────────────────┤
│ L2  Skill Library（现有 assets/，知识层，仍是 Markdown）│
│     25 个子 skill + 31+ 契约——继续做全领域方法论的       │
│     single source of truth；但只描述"内容与判据"，        │
│     不再描述"何时调用、怎么恢复、谁去调用"                │
├────────────────────────────────────────────────────────┤
│ L1  Runtime Kernel（新增，控制层，代码）                 │
│     单 CLI/daemon（headless，零 GUI）：                  │
│     · 状态机执行 21-phase DAG（RUNSTATE.json 升格为      │
│       kernel 权威状态，Markdown 契约变其 schema）        │
│     · 事件日志 events.jsonl（每个 phase 边界/门/回环     │
│       一条事件，可重放、可接管——对齐 DeepScientist）     │
│     · provider 层（litellm 式多后端路由 + 角色分档       │
│       ideation=强模型 / replay=便宜模型 + token 实测记账 │
│       →RUN_BUDGET 的 api_cost_usd 变真数）               │
│     · 机械门内嵌：phase 转换=代码强制先跑                │
│       validate_verdicts/sciforge_audit，不过则无法前进   │
│     · checkpoint/kill = CLI 暂停 + 队列等待，非 prose    │
│     · worker 池：toy/full 实验多 seed 并行 + 后台队列    │
│     · resume：进程崩溃→读 events+RUNSTATE 从 next_action │
│       续跑（你们的续航契约第一次真正被执行）              │
└────────────────────────────────────────────────────────┘
```

**关键原则：kernel 不懂科学，skill 不懂调度。** LLM 降级为"节点内容生成器"，循环结构、状态存储、终止/回退判据全部代码化——这是 5 家竞品的共识形态，也是 PaperBench/CRUX 类长任务失败的共同解药。

### 2.2 RSI 递归进化（L3）的具体设计

利用你们已有的独特资产，RSI 不需要发明新机制，只需要把三样东西接成闭环：

1. **进化信号源（已有）**：LESSONS.json + PIPELINE_VERDICT_SUMMARY + events.jsonl（新增）+ 每个 BLOCKED/BA/KILL 的 reason_code
2. **变异体生成（新）**：`/evolve` meta-skill——读 N 个 run 的信号，产出三类 patch：
   - **契约 patch**：改 skills/*.md 的判据/阈值/措辞（如"toy FAIL 判定过松"→提高 seed 复现要求）
   - **路由 patch**：改 kernel 配置（如某 domain-signature 下该走 theory-only 却走了 experiment，更新 verification-routing 默认）
   - **探针 patch**：向证伪 battery 新增/淘汰探针（哪些探针真的拦住了幻觉）
3. **选择压力（已有雏形，需硬化）**：
   - golden problem set（从你们 10 轮全域实测里挑 6-8 题做固定回归基准）
   - 硬门顺序：`ci_check.py` → `pytest tests/` → `fixtures/e2e_minimal` e2e smoke → golden set 对比（新版必须 ≥ 旧版 verdict 完整率 / publishability-score / 审计拦截率）
   - **对抗评审**：复用 adversarial-falsification + auto-review-loop 评审 patch 本身（skill 用自己的武器评审自己——这就是 RSI 的"递归"）
   - **进化不可触碰区（硬编码在 kernel）**：tests/、schemas/、validate_verdicts.py、ci_check.py、LICENSE——防止进化 agent 改判卷器本身（自我优化的第一安全公理）
4. **代际记录（已有）**：git 仓库 + CHANGELOG；每次进化 = 一个 tagged commit，失败进化 revert。DeepScientist 的 "quest 即 git 仓库" 直接可抄。

版本节奏建议：evolution round 的频率 = 每 5 个 run 或每晚（linux 服务器 daemon cron），与你们的 competitive-drift-monitor（季度竞品追踪）形成"对内进化 + 对外追踪"双环。

### 2.3 与竞品的差异化定位（为什么值得做）

| 维度 | AI-Scientist v2 | EvoScientist | AgentLaboratory | SciForge-OSS 目标态 |
|---|---|---|---|---|
| 全领域方法 | 模板限定→去模板 | 通用 | 人给方向 | **domain-learner 证据规范学习（最强）** |
| 审计链 | 模拟评审 | memory 图谱 | 评审循环 | **20 个 machine-readable verdict + schema 硬门（独有）** |
| 预算治理 | token 计数 | 成本展示 | 无 | **双向账本（超支+欠花，独有）** |
| 负结果纪律 | 无 | 无 | 无 | **polarity 路由 Limitations（独有）** |
| 自我进化 | 无 | 有（memory 层） | 无 | **skill 库级 RSI（竞品无人做到）** |
| 真·发论文背书 | ICLR workshop 过线 | ICAIS 6/6 | 无 | 目标：先过 ScienceAgentBench/MLE-bench lite，再谈投稿 |

结论：我们的 Markdown 契约层是竞品**全部缺失**的质量文化资产；缺的只是把这些契约"执行化"的 kernel。这是改造而非重写——25 个 skill 里 80% 的内容原封不动迁移为 kernel 的 prompt 模板与门判据。

---

## 三、分阶段路线图（macOS 优先实测）

### Phase A（现在就能在这台 Mac 开始）：Kernel MVP —— "会跑的 auto-pipeline"

1. 单入口 CLI（建议 Node 或 Python 单文件起步，与 `bin/sciforge.js` 同族）：`sciforge run "Q001..." --effort lite`
2. 先只做 4 件事：状态机推进（读 orchestrator 的 phase 表为配置而非 prose）→ 事件落盘 events.jsonl → 门强制（每次转换前跑 validate_verdicts）→ resume（读 RUNSTATE）
3. provider 层 v1：接两个模型档位 + 真实 token 计数写 RUN_BUDGET
4. **验收标准（macOS 无 GUI 实测）**：`kill -9` 进程后重启，pipeline 从断点续跑且 verdict 完整率 100%；用 fixtures/e2e_minimal 做第一轮回归

### Phase B：自主度 —— daemon + 多问题队列 + 跨 run 纲领

1. `sciforge serve`（headless daemon，对齐 EvoScientist 的 serve/deploy 双模）：任务队列 + cron 定时进化轮
2. 把"单问题单 run"升级为可选的 **program 模式**：一组相关问题自动按 RUN_PREPRINT 链式选题（人批准纲领，机器迭代问题）
3. toy/full 实验多 seed worker 池（GPU/NPU 用现成 detect_device.py）

### Phase C：RSI 闭环上线

1. `/evolve` meta-skill + golden problem set + 不可触碰区硬编码
2. 每晚进化轮：审计→patch 提案→对抗评审→门→tagged merge；进化日报推送（此处再接微信 bot——企业微信 webhook 最稳，Linux 无 GUI 服务器 curl 一个 POST 就通，与你们跨平台目标天然兼容）
3. 打榜：ScienceAgentBench（102 任务，当前 SOTA 33%）优先——比 DeepResearch Bench 更贴我们"代码可执行的科学"边界

### Phase D：三平台工程化

- Linux headless：Docker 镜像（无 GUI 依赖已是我们的传统优势：d2/texlive/render_figure 全 headless）
- NPU 通路验证；Windows WSL2 文档 + 原生 CI 矩阵
- npm 包升级：kernel 入 `@gewislab/sciforge-oss`，skill 库继续纯 Markdown 可单独 clone（保持"知识层与运行层可分离消费"）

### 风险与对策

| 风险 | 对策 |
|---|---|
| RSI 自改 skill 导致质量回退/奖励作弊 | 进化只提 patch 不合 patch；tests+schemas+审计脚本划为不可触碰区；golden set 双版本对跑；关键合入留人审开关 |
| kernel 化后失去"任何 Markdown agent 可消费"的普适性 | L2 保持纯 Markdown 不绑 kernel——kernel 只是第一个也是最好的"宿主"，Codex/Claude Code 仍可直读 skill 跑（降级为 LLM 驱动模式），双模共存 |
| "无 .py 无 bash"的 README 哲学冲突 | 措辞升级为："skill 库依旧零依赖纯知识；运行时可选、可替换、kernel 不掺学科知识"——哲学不变，边界更准 |
| 低能力模型仍被用作执行者 | provider 分档：门禁/路由/判分节点强制高能力模型，格式化/检索整理可用便宜模型——智力预算花在刀刃上 |

---

## 四、下一步（建议立即执行的最小实验）

在这台 Mac 上做一个 **1 天量级的 Kernel Spike**：写 300-500 行的最小状态机（只覆盖 Phase 0→3 + 门强制 + events.jsonl + resume），用 fixtures/e2e_minimal 跑通，`kill -9` 三次验证续航。这一步不需要动任何现有 skill 文件，就能实证"知识/控制分离"路线的可行性，也为后续 RSI 提供第一个可进化的控制对象。
