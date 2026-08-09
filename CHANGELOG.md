# Changelog

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

**验证**：274 tests 全 PASS；ci_check 四项 OVERALL PASS；verifier 对 canonical fixture 实测 PASS；security_scan 23/23；零 CJK 维持。


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