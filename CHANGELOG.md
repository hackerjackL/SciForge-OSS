# Changelog

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