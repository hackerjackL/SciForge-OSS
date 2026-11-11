# Reproduction Guide — SciForge v1.5.0 (macOS 实测记录)

> 目的：任何人（或任何 agent）在干净机器上，按本文命令能逐条复现 v1.5.0 定版的**全部关键行为**。
> 实测环境：macOS (Darwin arm64), Python 3.14.7 (uv venv), Node 22, TinyTeX, Homebrew；所有命令在仓库根目录执行。

## 0. 环境（S28 完全体，一次性）

```bash
# Python ≥3.10（kernel 要求）+ 科学栈
uv venv --python 3.14 .venv            # 或 conda create -n sciforge python=3.14（kernel 最低 ≥3.10，实测 3.14.7 全绿）
.venv/bin/pip install -r requirements.txt

# 非 Python 工具链（绘图/编译）
brew install graphviz librsvg poppler  # Linux: apt 等价，见 scripts/plotting/INSTALL.md
# d2: curl -fsSL https://d2lang.com/install.sh | sh
# LaTeX: TinyTeX（含 standalone 包，composite 图需要）：
#   tlmgr install standalone etoolbox xkeyval varwidth

# 自检
.venv/bin/python -m sciforge.cli doctor   # 或经 npm CLI: node bin/sciforge.js doctor
.venv/bin/python scripts/plotting/render_figure.py --doctor
```

`.venv/bin/python` 若是指向已卸载解释器的断链，上面第一条命令会以裸 shell 的 "no such file or directory" 失败且不说明原因；`scripts/ci_check.py` 的环境检查会先检出断链，打印目标路径、site-packages 是否完好，以及修复命令（重指 symlink 或重建 venv）。

## 1. 门系统（全部门在真实工作）

Mode A（纯 skills、无内核边界）的推荐入口是 `gate_all.py`：一次调用跑完该 workspace 适用的全部门并打印一张表（Mode B 仍由内核 `commit_boundary()` 在边界强制，本脚本只是事后报告，不把 Mode A 变成 Mode B）。结构性无法在 Mode A 生效的门（依赖内核产物的 `REP.json`/`NODES.json`/`RUNSTATE.problem_hash`，或只有自报 ledger、无同址原始证据的 fairness 交叉验证）会报 `UNPROTECTED`——意思是**该保证在本 run 中不存在**，既不是 PASS 也不是普通 SKIP，必须当作未受保护项阅读。

```bash
# Mode A 一键门（推荐）：--list 先看门名与相位
.venv/bin/python scripts/gate_all.py --list
.venv/bin/python scripts/gate_all.py <your-run>                 # 表格报告
.venv/bin/python scripts/gate_all.py <your-run> --json          # 机器可读
.venv/bin/python scripts/gate_all.py <your-run> --only doi_gate,citation_support
.venv/bin/python scripts/gate_all.py <your-run> --skip tdal_compute
.venv/bin/python scripts/gate_all.py <your-run> --offline       # doi_gate 只做结构检查，不联网
.venv/bin/python scripts/gate_all.py <your-run> --integrity-llm # 额外跑 integrity 的语义 D1 层（需 provider）
.venv/bin/python scripts/gate_all.py <your-run> --timeout 600   # 单门超时（秒）
# 退出码：0 = 无 FAIL/BLOCKED/ERROR；1 = 至少一个；2 = 用法错误

# verdict schema 校验（fixture 24/24 PASS）
.venv/bin/python scripts/validate_verdicts.py fixtures/e2e_minimal/.sciforge/verdicts --strict --require-complete
# 安全扫描自测（26/26）
.venv/bin/python scripts/security_scan.py --self-test
# gap 判别门（好报告 PASS，含糊报告 FAIL——防空洞 gap 驱动幻觉选题）
.venv/bin/python scripts/gap_gate.py <your-run>
# 泄漏扫描（12 类 A–L；K = SCI 正文语域，L = 内部机制行话，另含伪造 frontmatter 的 I-frontmatter 子类）
.venv/bin/python scripts/leakage_scan.py <your-run>
# 全仓 CI 门（链接/版本/绘图/测试）
.venv/bin/python scripts/ci_check.py
```

## 2. 崩溃恢复（S02 核心卖点）

```bash
# 起一个 manual-host 跑，phase 1a 等待宿主时 kill -9 内核进程
node bin/sciforge.js run --workspace ./runs/CRASHTEST --problem "test" --host manual
# (另开终端) pkill -9 -f sciforge  # 模拟进程死亡
node bin/sciforge.js resume --workspace ./runs/CRASHTEST
# 预期：recovery: resume；RUNSTATE 从断点 phase 精确续跑（events.ndjson 重放）
```
实测结论：stale lockfile 检出 → 事件重放 → 从 1b 续跑成功。

## 3. RSI 进化闭环（S11–S19，第一轮真实进化）

```bash
# 信号提案（audit 完成的 run）→ patches.json
PYTHONPATH=kernel .venv/bin/python -c "
import sys; sys.path.insert(0,'kernel')
from sciforge.propose import audit_run, proposals_from_signals
from pathlib import Path
sigs=[audit_run(r) for r in Path('./runs').iterdir() if (r/'.sciforge/events.ndjson').exists()]
import json; Path('patches.json').write_text(json.dumps({'proposals':proposals_from_signals(sigs, Path('.'))},indent=2))"

# 进化搜索（probe 预检 → PUCT/MAP-Elites → 三分片评分）
PYTHONPATH=kernel .venv/bin/python -m sciforge.cli evolve --workspace ./runs --proposes ./patches.json --budget 8 --algorithm puct [--fast]
# 人工合入（全量 ci_check 门；失败自动回滚——第一轮实测就拦截过坏候选）
PYTHONPATH=kernel .venv/bin/python -m sciforge.cli submit --workspace ./runs evo_<id>
# golden 回归电池（进化硬门）
PYTHONPATH=kernel .venv/bin/python -m sciforge.golden
```
实测结论：probe 正确拒绝平坦评分器×2；胜出候选 score=0.88/held_out=0.76；坏候选被 ci_check 拦截并回滚；好候选合入为 git commit（`evolve(evo_…)`）。

## 4. 多模型交叉审稿（S20/S21）

配置网关（`ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY` 或 `kernel/config/providers.json`）后，Phase 14 自动跑：3 独立盲审（methods/novelty/repro 视角）→ 分歧→仲裁 → `REVIEW_PANEL.json` + registered `REVIEW_STATE.json`。实测：stub 论文诚实收到 2.3/10、11 fatal——面板非橡皮图章。

## 5. 全链 headless（S01/S08/S23，claude 宿主）

```bash
node bin/sciforge.js run --workspace ./runs/Q001 --problem "..." --host claude --loop --effort lite
# 后台派发：phase=一次 claude 子进程调用，5s 节流轮询；重阶段（MCTS）不再撞超时墙
# 成本实测：RUN_BUDGET.json api_cost_usd = claude CLI 回传的 total_cost_usd 累加（非自报）
# 产物：RUNSTATE/verdicts/refine-logs/domain-signature 等与 skills-only 模式完全同构
```

## 6. headless 服务器（S29，Linux 无 GUI）

```bash
docker build -t sciforge .
docker run --rm -v $PWD:/work -w /work sciforge run --workspace /work/r --problem "..." --host manual
# 或裸机：daemon 只监听 loopback :4510；--workers N 起 N 个并发 worker（默认 1）
nohup node bin/sciforge.js serve --archive ./runs --workers 2 > /tmp/sciforge-daemon.log 2>&1 &
curl localhost:4510/health          # 只读端点，无需 token

# 启动时生成一次性 token，落盘 <archive>/.sciforge-daemon/token（权限 0600）；每次重启换新
TOKEN=$(cat runs/.sciforge-daemon/token)
# 所有改变状态的端点都要求 Bearer token（也接受 X-SciForge-Token: <token>）
curl -H "Authorization: Bearer $TOKEN" -X POST localhost:4510/runs \
     -d '{"problem":"...","run_id":"Q001"}'
curl localhost:4510/runs/Q001          # 只读：RUNSTATE + 事件计数 + 队列状态
curl -H "Authorization: Bearer $TOKEN" -X POST \
     localhost:4510/runs/Q001/approve -d '{"checkpoint":"idea-pick"}'
curl -H "Authorization: Bearer $TOKEN" -X POST localhost:4510/runs/Q001/resume
curl -H "Authorization: Bearer $TOKEN" -X POST localhost:4510/runs/Q001/cancel
```

- 只读 GET 端点开放：`/health`、`/runs`（`?state=queued` 可过滤）、`/runs/<id>`、`/daily`；所有 POST（入队、approve/deny、resume、cancel）无 token 返回 401，token 错误返回 403。
- 持久队列是 SQLite（`<archive>/.sciforge-daemon/queue.sqlite3`，重启不丢）；`<archive>/queue.json` 只是派生镜像，可删。daemon 重启时会回收死 worker 留下的 running 行。
- token 每次启动都重新生成，重启后客户端需要重新读取 token 文件。

GPU/NPU：镜像内 `detect_device.py` 自动 cuda/rocm/npu/mps/cpu；NPU allow-list 作业模式见 `scripts/` 与 AGENTS.md。

## 7. 单元测试（全部机制）

```bash
.venv/bin/python -m pytest tests/test_kernel.py -q     # kernel 子集
.venv/bin/python -m pytest tests/ -q                   # 全仓测试（数量以运行输出为准；基线随版本增长，macOS Python 3.14 实测全绿）
```

## 已知边界（诚实）

- Mode A（纯 skills）行为与 v1.5.0 之前完全一致——kernel 是增量，不是强制。
- 宿主 claude 单次阶段调用时长取决于宿主 agent 本身；kernel 负责不阻塞、可恢复、门强制。
- llm_judge 评分依赖 provider 可达；无网关时 hybrid 自动退化为 gate-only。


## 8. Wave-2 capabilities (v1.5.0-w2)

```bash
# SCI body voice (class K): plant an apology and watch it fail
.venv/bin/python scripts/leakage_scan.py <ws>   # class K = apology/defense register
# Experiment fairness (mode=deepen): unfair ledger -> FAIL, fair -> PASS
.venv/bin/python scripts/fairness_gate.py <ws> --write-verdict
# DeepMind cascade multi-evaluator (ResearchDomain hard-zero on science-integrity hits)
PYTHONPATH=kernel .venv/bin/python -c "import sys; sys.path.insert(0,'kernel'); from sciforge.evolve import ResearchDomain, Patch; print(ResearchDomain().score(Patch({'ops':[{'path':'x','old':'a','new':'package the failure as a contribution'}]})))"
# Claude Code seamless: skill + subagent roles + project memory
ls ~/.claude/skills/sciforge/SKILL.md ~/.claude/agents/sciforge-*.md CLAUDE.md
# Closed-loop demo (RK4 energy conservation): run it yourself — run
# workspaces are local-only and never shipped (v1.7.1 repo hygiene):
sciforge run --workspace ./runs/DEMO-RK4 --problem "RK4 energy conservation" --test-mode --loop
```

## 9. GPU 后端：colab-mcp（免费 T4）接入 Claude Code

SciForge 的 Phase 6b/6c 实验可选用 Google Colab 的免费 T4 GPU，通过 `colab-mcp` 桥接。它注册为 cc-haha/Claude Code 的 MCP server，**不是常驻进程**（客户端按需 spawn，故等效开机自启）。

- 官方仓库只发 git HEAD，且要求 **Python ≥3.13**（`pyproject` 钉死，独立于 SciForge 的 3.14 venv）。本机 Xcode CLT 许可会卡 `git`/`python3` shim，因此用 uv 托管 Python 从本地源码部署：
  ```bash
  # 一次性部署（已在本机完成，产物在 ~/.sciforge-gateway/colab-mcp）
  curl -sL -o /tmp/cm.tar.gz https://codeload.github.com/googlecolab/colab-mcp/tar.gz/refs/heads/main
  mkdir -p ~/.sciforge-gateway/colab-mcp && tar xzf /tmp/cm.tar.gz -C ~/.sciforge-gateway/colab-mcp --strip-components=1
  cd ~/.sciforge-gateway/colab-mcp && uv sync   # uv 自动拉 py3.13，绕开 Xcode shim git
  ~/.sciforge-gateway/colab-mcp/.venv/bin/colab-mcp --help   # 冒烟
  ```
- cc-haha/Claude Code 注册（`~/.claude.json` 的 `mcpServers.colab-mcp`，指向 `.venv/bin` 直接二进制避免 `uv run` 冷启动握手超时）：
  ```bash
  # 用官方命令写入更稳；本机已注册并 `✓ Connected`
  # 注意 add-json 可能丢 cwd，验证后需确认 command 指向 .venv/bin/colab-mcp
  claude mcp list | grep colab   # 期望：colab-mcp ... ✓ Connected
  ```
- **用法（GPU 在浏览器侧开启，colab-mcp 只是桥）**：
  1. 浏览器打开 colab.research.google.com，新建 notebook
  2. 网页菜单「修改 → 笔记本设置 → 硬件加速器 → T4 GPU」
  3. cc-haha 里说"连接我的 Colab" → agent 调 `open_colab_browser_connection`（首次弹浏览器授权）→ 连上后动态解锁 notebook 读/写/运行工具 → 可把 `src/` 训练脚本丢到 T4 跑并回收结果
