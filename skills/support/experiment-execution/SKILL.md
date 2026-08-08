---
name: experiment-execution
description: "Two-stage experiments (toy→full+background) with v3.2 proxy auto-mount + async dataset download + v3.4 Step 0d.0 local benchmark registry check (avoid re-download) + Step 5.0 full-code smoke gate (1-step end-to-end, writes .SMOKE.json, wired into ordered chain before dispatch). Phase 6b/6c. Invoke for any computational/experimental verification."
type: support-skill
role: experiment-runner
version: 1.1.1
---

# Experiment Execution (SciForge-OSS — Toy + Full + Background Dispatch)

> **Status (v2.0)**: New support skill that fills the missing experiment layer. Executes **toy experiments** to validate the idea's core reasoning chain before committing to **full experiments**. Full experiments are dispatched to **background** to avoid front-end timeouts. This skill is domain-agnostic — it adapts to whatever the domain signature says.
>
> **Core principle**: Never invest full compute in an unvalidated idea. Toy first, gate check, then full. And never block the foreground on a long-running job.

## Quick Reference

- **Purpose**: Run toy experiments → gate check → dispatch full experiments to background
- **Input**: `FINAL_PROPOSAL.md` (selected idea), `domain-signature.json`, `METHOD_REGISTRY.md`
- **Output**: `EXPERIMENT_REPORT.md` (toy results) + `FULL_EXPERIMENT_DISPATCH.json` (background job metadata)
- **Key**: Two-stage (toy → full), async dispatch, domain-agnostic

## Use When

The pipeline reaches this skill when `verification_type` is NOT `theory-only`:
- `verification_type = computational` → run numerical experiments
- `verification_type = theory+experiment` → run code/data experiments
- `verification_type = theory-only` → **skip this skill entirely** (handled by Phase 6 alone)

Typical invocation from orchestrator:
- Phase 6b: `/experiment-execution` (toy experiment)
- Phase 6c: `/experiment-execution --full --background` (full experiment, dispatched)

## Job

Execute experiments in two stages with a gate between them:

1. **Toy experiment** — minimal-scale validation of the idea's core claim. Fast, cheap. Runs in foreground **if estimated ≤ 5 min**, otherwise dispatched to background (`toy_bg`). Goal: validate or kill the reasoning chain.
2. **Full experiment** — complete-scale execution. Runs in **background** (nohup/tmux/systemd). Goal: produce publishable results.

The non-negotiable goal: **the toy experiment must validate the idea's core reasoning chain before any full-scale compute is committed.**

## Architecture

```
FINAL_PROPOSAL.md (selected idea)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 0: TOY DISPATCH DECISION                     │
│  • estimate toy wall-clock                          │
│  • ≤ 5 min → foreground (fast path)                 │
│  • > 5 min → background (toy_bg) — do NOT block     │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────────┐  ┌──────────────────────────────┐
│ STAGE 1a: TOY   │  │ STAGE 1b: TOY_BG (background)│
│  (foreground)   │  │  • Dispatch: nohup/tmux/sys  │
│  • Scope: 1-10% │  │  • Writes STATUS.json        │
│  • Timeout:5min │  │  • Gate read after completion│
│  • Goal: valid. │  │  • Goal: same as foreground  │
│  • Gate: PASS→2 │  │  • Gate: PASS→2 FAIL→BLOCKED │
│  • Gate:FAIL→BLK│  │  • Never block foreground    │
└────────┬─────────┘  └───────────────┬──────────────┘
         │ TOY_GATE: PASS              │ TOY_GATE: PASS
         ▼                             ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 2: FULL EXPERIMENT (background, async)       │
│  • Scope: 100% scale                                │
│  • Dispatch: nohup / tmux / systemd                 │
│  • Goal: produce publishable results                │
│  • Monitoring: status file + log tailing            │
│  • Recovery: resume from checkpoint on failure      │
└──────────────────────────┬──────────────────────────┘
                           │ completion signal
                           ▼
                    EXPERIMENT_RESULTS/
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stage` | enum | `toy` | `toy` or `full` |
| `background` | bool | `false` | If true, dispatch to background (mandatory for `full` stage) |
| `toy_bg_threshold` | int | `300` | Toy estimated wall-clock (sec) above which the toy is auto-dispatched to background as `toy_bg` (v2.1) |
| `toy_bg` | bool | `false` | Set true by the dispatch decision (Stage 0) when toy runs in background (v2.1) |
| `timeout_toy` | int | `300` | Toy experiment max seconds (hard cap, foreground path) |
| `timeout_full` | int | `86400` | Full experiment max seconds (24h default) |
| `scale_ratio` | float | `0.1` | Toy experiment scale (fraction of full) |
| `dispatch_method` | enum | `auto` | `nohup` / `tmux` / `systemd` / `auto` (auto-detect) |
| `checkpoint_interval` | int | `600` | Seconds between checkpoints for full experiment (and toy_bg if long) |
| `language` | enum | `python` | Primary execution language |
| `device` | enum | `auto` | v2.2: `auto` (auto-detect CPU/GPU/NPU — see Device Detection below), `cpu`, `cuda` (NVIDIA GPU), `mps` (Apple Silicon), `npu` (Ascend/Cambricon/etc.), `rocm` (AMD GPU). The experiment script MUST honor this — never hardcode `.cuda()`; use the detected device. |
| `fallback_device` | enum | `cpu` | v2.2: if the requested device is unavailable, fall back to this (default CPU) + log WARN. Do NOT BLOCK on a missing GPU — the toy may still run on CPU within the foreground budget. |

## Workflow

### Step 0: Determine Experiment Type

Read `FINAL_PROPOSAL.md` and `domain-signature.json` to determine:

1. **What needs to be validated?** — the idea's core claim (from FINAL_PROPOSAL.md)
2. **What is the minimal test?** — the smallest experiment that can validate or kill the core claim
3. **What scale is "toy"?** — typically 1-10% of full (subset of data, fewer epochs, coarser mesh, smaller sample)
4. **What is the full experiment?** — complete-scale validation

### Step 0p: Network Proxy Auto-Mount (MANDATORY before any dataset/model download)

**绝对禁止因网络问题跳过数据集/模型/依赖下载**（用户硬要求）。toy/full 实验常需从 GitHub / HuggingFace / ModelScope / arXiv / Zenodo / Kaggle / OpenNeuro 等拉取数据集或预训练权重；本 skill 在任何网络请求前必须先完成代理挂载，逻辑与 `universal-retrieval` 的「代理自主检测」对齐（同一份 `literature/.proxy-resolved.json` 可复用）：

1. **复用已探测代理**：若 `literature/.proxy-resolved.json` 存在且 `detected_at` 距今 < 1h，或环境变量 `http_proxy`/`https_proxy`/`ALL_PROXY` 已设，直接复用，跳过探测。
2. **候选端口探测**（与 universal-retrieval 同序列）：`8099`（mihomo mixed-port）→ `7890`（Clash HTTP）→ `7892`（Clash SOCKS）→ `1080` → `8080`。逐个 `socket.connect_ex(('127.0.0.1',<port>), timeout=2)`，TCP 通后再经该代理 GET `https://huggingface.co` 或 `https://github.com`（`timeout=3s`，期望 2xx/3xx）双检。第一个双检通过即选中。
3. **挂载**：写入 `experiments/.proxy-resolved.json`（实验侧副本，与 `literature/.proxy-resolved.json` 同 schema），并对后续所有下载设 `http_proxy`/`https_proxy`。
4. **全部候选不可达** → **绝不放弃下载**：(a) 直连试 1 次（`timeout=10s`）；(b) 直连失败 → 转入「Step 0d 异步下载」（nohup 后台），下载 verdict 降为 `WARN`，**永不降级为 SKIP/NOT_APPLICABLE/网络原因 BLOCKED**。网络只能把 PASS 降到 WARN。
5. **重探测**：已挂载代理连续超时 2 次 → 删 `.proxy-resolved.json` 回步骤 2 重探测。
6. **下载产物归档**：所有下载的数据集/权重写 `experiments/datasets/` 或 `experiments/weights/`，并在 `experiments/.downloads.json` 登记 `{source, url, sha256, size_bytes, downloaded_at, via_proxy:bool, method:"foreground|nohup"}`，供 Phase 10 result-to-claim 与 Phase 15 citation-audit 回溯。

### Step 0d: Async Dataset Download (nohup — 用户硬要求：大文件/长任务后台异步)

大型数据集（HLE ~数 GB、PaperBench、NatureBench、ImageNet、COCO、Pile、OpenWebText、HF Hub 模型权重）或环境依赖（`pip install`、conda env、`huggingface-cli download`、`modelscope download`）预计耗时较长时**必须用 `nohup` 后台异步下载，立刻切其他代码重构/测试任务**，遵循 [`background-dispatch-protocol.md`](../../shared-references/background-dispatch-protocol.md)：

**0d.0 — 先查本地已有数据集注册表（v3.2 — 避免重下已存在的 benchmark）**：在发起任何下载前，本 skill **必须先查本地 benchmark 注册表**——工作区常有 `/root/autodl-tmp/datasets/`（或项目根的 `datasets/`）已预置好 HLE / NatureBench / PaperBench 等 benchmark（含 `README.md` + `INDEX.md` + parquet/csv）。查表顺序：
1. 读 `datasets/README.md`（benchmark 注册表）+ 各 `datasets/<name>/INDEX.md`——若目标数据集已在册且文件齐全（如 `datasets/PaperBench/train.parquet` 存在且 size > 0），**直接 symlink 或 copy 到 `experiments/datasets/<name>/`**，在 `.downloads.json` 记 `method: "local_registry", via_proxy: false, source: "local datasets/<name>"`，**跳过网络下载**。
2. 若在册但文件缺失（如 HLE 全量 parquet 因 gated 未下完，只有 README/eval.yaml）→ 走下面的 nohup 异步下载补全缺失部分（gated 数据集需先 `huggingface-cli login`）。
3. 若完全不在册 → 走下面的 nohup 异步下载全量。
**绝对禁止**：在已存在 `datasets/<name>/` 的情况下重新从 HF 下载同一数据集——浪费带宽 + 时间 + 可能拿到不同版本。

1. **触发阈值**：单文件/批次预计 > 2min 或体积 > 100MB → MUST 后台；2-5min/≤100MB → SHOULD 后台（agent 自主）；<2min/≤100MB → 前台。
2. **nohup 调度**（与 Step 5 同栈，tmux→nohup→systemd 降级）：
   ```bash
   cd {workdir} && nohup bash -c '
     export http_proxy="{proxy_url}" https_proxy="{proxy_url}" ALL_PROXY="{proxy_url}"
     {download_command}   # 如: huggingface-cli download <repo> --local-dir experiments/datasets/<name>
                          # 或: wget -c <url> -O experiments/datasets/<name>
                          # 或: pip install -r requirements-exp.txt
   ' > experiments/downloads/{name}.log 2>&1 &
   echo $! > experiments/downloads/{name}.pid
   disown
   ```
3. **立即返回**：调度后**不等待**，前台立即切到 Step 1（设计 toy）/其他 phase；下载状态在 Phase 10（result-to-claim）回收——读 `experiments/downloads/{name}.STATUS.json`，若 `status=running` 用已下完的部分继续 toy（缩 scale），若 `failed` 按 Recovery Protocol 重试 1 次，仍失败 verdict WARN + 记录 `source_status: unavailable`。
4. **多下载并行**：多个独立数据集/依赖可并行各起一个 nohup job（不同 `{name}`），互不阻塞；每个写独立 `.pid`/`.log`/`.STATUS.json`。
5. **下载完整性核**：完成后对每个文件算 sha256 写入 `experiments/.downloads.json`（步骤 0p·6）；哈希与上游公布的（HuggingFace/HF Hub 的 `LFS` sha256、Zenodo 的 checksum）比对，不符 → WARN + 重下 1 次。
6. **断点续传**：优先用支持 `-c`/`--resume`/`--local-dir-use-symlinks False` 的工具（`wget -c`、`aria2c -c`、`huggingface-cli download` 自带断点）；STATUS.json 记录 `resume_from` 字段。

**绝对禁止**：因下载慢/超时而跳过数据集获取、改用纯合成数据替代真实数据集（除非 domain-signature 明确允许）、或把 toy gate PASS 建立在未下完的残缺数据上而不标记。

### Step 0a: Device Detection (v2.2 — CPU/GPU/NPU auto-detect)

Before running any experiment script, detect the available compute device. This machine has a small GPU (may not always); some machines have NPU; CPU is always available.

**Detection order** (first match wins):
1. `nvidia-smi` returns a GPU → `device=cuda` (NVIDIA GPU; PyTorch `torch.cuda.is_available()` confirms; check VRAM — this machine has ~12GB)
2. `rocminfo` / `hip` available → `device=rocm` (AMD GPU)
3. `npu-smi` or Ascend/Cambricon toolkit present → `device=npu` (NPU — Ascend/Cambricon; check toolkit env vars `ASCEND_HOME`/`CANN_HOME`)
4. macOS with Apple Silicon → `device=mps` (Metal Performance Shaders; `torch.backends.mps.is_available()`)
5. None of the above → `device=cpu` (always available, the `fallback_device`)

**The experiment script MUST honor the detected device — NEVER hardcode `.cuda()` or `.to('cuda:0')`.** Use a helper at the top of every script:
```python
import torch, os, subprocess
def detect_device():
    if torch.cuda.is_available(): return torch.device('cuda')
    try:
        if subprocess.run(['npu-smi','info'],capture_output=True).returncode==0: return 'npu'  # torch_npu if available
    except: pass
    if hasattr(torch.backends,'mps') and torch.backends.mps.is_available(): return torch.device('mps')
    return torch.device('cpu')
DEVICE = detect_device()
# ALL tensors/models: x = x.to(DEVICE); model = model.to(DEVICE)
```

**Fallback contract**: if the requested `device` (e.g., `cuda`) is unavailable, fall back to `fallback_device` (default `cpu`) + log WARN to `RESULT.json`/`STATUS.json` (`device_fallback: cuda->cpu, reason: no_cuda`). **Do NOT BLOCK on a missing GPU** — the toy may still run on CPU within the foreground 5-min budget. For a full experiment requiring a GPU, if only CPU is available, the full experiment is dispatched to background with `device=cpu` + a longer `timeout_full` estimate (CPU is slower) + WARN.

**VRAM awareness** (GPU): check `nvidia-smi --query-gpu=memory.total --format=csv,noheader`; if < 8GB free, reduce `scale_ratio` for the toy (e.g., 0.1 → 0.05) to avoid OOM — log `scale_ratio_adjusted: OOM_risk` to `RESULT.json`.

```json
{
  "experiment_plan": {
    "core_claim": "[one sentence from FINAL_PROPOSAL.md]",
    "toy_scope": "[what the toy experiment tests]",
    "toy_success_criteria": "[what constitutes PASS]",
    "toy_scale": "10% of full (e.g., 100 samples, 5 epochs, coarse mesh)",
    "full_scope": "[what the full experiment tests]",
    "full_estimated_time": "[estimated wall-clock time]",
    "domain": "[from domain-signature.json]"
  }
}
```

### Step 1: Design Toy Experiment

Write a self-contained Python script that tests the core claim at minimal scale:

**Design rules:**
1. **One core claim, one test** — do not bundle multiple hypotheses
2. **Synthetic data OK** — if real data is unavailable at toy scale, generate synthetic data that matches the expected distribution
3. **Known-answer test preferred** — if the method has known properties, test those first
4. **Deterministic** — fix random seed (`np.random.seed(42)`)
5. **Fast** — must complete within `timeout_toy` seconds
6. **Structured output** — write results to `experiments/toy/RESULT.json`

**Domain-adaptive toy design** (driven by `domain-signature.json`):

| evidence_type | Toy experiment pattern | Example |
|--------------|----------------------|---------|
| `derivational` | Numerical check of symbolic result | SymPy result vs numpy numerical evaluation |
| `correlational` | Regression on 10% sample, check sign + significance | OLS on subset, verify coefficient direction |
| `causal_inference` | DiD/IV on synthetic data with known treatment effect | Generate data with known ATE, recover it |
| `experimental` | Power analysis + effect size on pilot sample | Compute required N, check if effect > MDE |
| `simulational` | Coarse mesh / reduced resolution simulation | PDE on 10x10 grid vs expected analytical solution |
| `interpretive` | Argument coherence check on 3 key claims | Verify logical consistency of core argument |

### Step 2: Execute Toy Experiment (Foreground)

```
Step 2a: Create experiment directory
         → experiments/toy/session_{timestamp}/

Step 2b: Write experiment script
         → code/experiments/toy/session_{timestamp}/toy_experiment.py

Step 2c: Execute with timeout
         → subprocess.run(timeout=timeout_toy)

**P5 Dry-Run 早停（v3.1）**: toy 执行应在 1%-5% 子集 / 3-5min 硬上限下先做 dry-run，三类早停自动触发并把反馈送回 idea 修正循环，避免全量算力浪费：

| 早停原因 | 触发条件 | 反馈动作 |
|----------|----------|----------|
| `UNCAUGHT_EXCEPTION` | 运行脚本抛异常（import/语法/运行时） | 回 Phase 6b 修代码（1 retry） |
| `LOSS_EXPLOSION` | 输出出现 NaN/Inf 或指标绝对值 > 阈值 | 回 Phase 6 检查推导假设（reformulate） |
| `BELOW_BASELINE` | 指标 > 1.5× baseline | 回 Phase 2 重生成 idea（bounded 2 轮） |
| `DRY_RUN_TIMEOUT` | 超硬上限 | 降 scale 重试一次；仍超时 → toy gate BLOCKED |

早停判定全部机械（无 LLM cost）；dry-run `PASS` 才进入正常 RESULT.json 门控流程。

Step 2d: Capture output
         → stdout, stderr, return code, RESULT.json

Step 2e: Evaluate against success criteria
         → PASS / FAIL / INCONCLUSIVE
```

**Output schema** (`RESULT.json`):

```json
{
  "experiment_id": "toy_20260730_120000",
  "stage": "toy",
  "status": "PASS | FAIL | INCONCLUSIVE | TIMEOUT | ERROR",
  "core_claim_tested": "[one sentence]",
  "success_criteria": "[what was tested]",
  "result_summary": {
    "primary_metric": {
      "metric_name": "[name]",
      "metric_value": 0.85,
      "threshold": ">= 0.7",
      "passed": true
    },
    "secondary_metrics": [
      { "metric_name": "[e.g. parallel_trends_p_value]", "metric_value": 0.34, "threshold": "> 0.05", "passed": true },
      { "metric_name": "[e.g. coefficient_sign]", "metric_value": "negative", "threshold": "== expected_sign", "passed": true }
    ]
  },
  "gate_logic": "all_metrics_pass | primary_only | majority_pass",
  "execution_time_seconds": 42,
  "scale_ratio": 0.1,
  "reasoning_chain_validated": true,
  "kill_signal": null,
  "recommendation": "PROCEED_TO_FULL | BLOCK | REDESIGN"
}
```

**Gate logic** (`gate_logic` field) — how multiple metrics combine into the PASS/FAIL verdict:
- `all_metrics_pass` (default): every metric's `passed` must be true. Use for problems where all criteria are load-bearing (e.g., causal inference needs correct sign AND magnitude AND parallel-trends).
- `primary_only`: only `primary_metric.passed` decides; secondary metrics are informational. Use when secondary checks are diagnostic but not gating.
- `majority_pass`: PASS if >50% of all metrics pass. Use for exploratory toys where no single metric is decisive.

**For causal_inference toys specifically** (per `discipline-writing.md` §0): `primary_metric` = recovered ATE/coefficient magnitude vs known effect; `secondary_metrics` MUST include coefficient sign and parallel-trends p-value — all three load-bearing, so `gate_logic: all_metrics_pass`.

### Step 3: Toy Gate (Decision Point — v5.0 KILL-or-PIVOT 停止协议)

| RESULT.status | Action |
|---------------|--------|
| `PASS` | Proceed to full experiment design (Step 4) |
| `FAIL` | **进入 KILL-or-PIVOT 决策**（见下）——不再一律 kill idea |
| `INCONCLUSIVE` | Redesign toy experiment (bounded 1 retry). If still inconclusive → `BLOCKED`. |
| `TIMEOUT` | Reduce scale_ratio, retry once. If still timeout → `BLOCKED`. |
| `ERROR` | Diagnose error, fix script, retry once. If still error → `BLOCKED`. |

**Hard rule**: A FAIL toy experiment **must not** proceed to full experiment — 这是想法生死判，防止把算力浪费在死胡同上。

**从 0 到 1 停止协议（KILL-or-PIVOT）——解决"从 0 到 1 不知道何时停"**:

增量论文有边际收益信号可停；从 0 到 1 没有——必须靠**证伪即转向**。FAIL 触发条件（两者同时满足才触发，防误杀）：
1. 负向结果**显著**（核心指标低于 baseline 且差异 > 噪声水平）
2. 负向结果**可复现**（≥2 个随机种子同向，或 toy 重跑一次仍 FAIL）

触发后进入决策（写入 `EXPERIMENT_REPORT.md` 的 `kill_or_pivot` 字段）：

| 决策 | 适用 | 动作 |
|------|------|------|
| **PIVOT** | 问题有价值，当前方法路径证伪 | 保留问题与 RQ，换方法/换组件重设计 → 回 Phase 5（method-registry 重注册）→ 重跑 toy。**PIVOT 预算 ≤2 次**，超预算强制 KILL |
| **KILL** | 核心假设被证伪且无可替代路径，或 PIVOT 预算耗尽 | 引用 `/kill-argument` 写杀论证 → `BLOCKED, reason: core_hypothesis_falsified` → 回 Phase 2 换 idea |

**禁止行为**:
- 禁止"继续调参硬救"——toy 已证伪核心方向时，调参不是 PIVOT 是拖延
- 禁止把负向 toy 结果包装成"诚实的发现"继续推进（负结果纪律见 result-to-claim）
- PIVOT 必须换**方法**（method-registry 重注册、hash 重锁），不是换超参

### Step 4: Design Full Experiment

If toy gate passed, design the full-scale experiment:

1. **Scale up** from toy to full (full dataset, full epochs, full resolution)
2. **Add rigor** — proper controls, ablation, robustness checks
3. **Add checkpointing** — save intermediate results every `checkpoint_interval` seconds
4. **Add monitoring** — periodic status updates to `experiments/full/STATUS.json`
5. **Expose a 1-step cap flag** (`--max-steps`/`--max-epochs`/`--steps`) — Step 5.0's smoke gate REQUIRES slicing the full script to 1 step; a full script with no step-cap flag is itself a design defect. Add the flag here, retroactively enforced at Step 5.0.
6. **按预注册评测协议执行（v5.2 — 公平评测）**: 读取 `verdicts/EVALUATION_PROTOCOL.json`（method-registry §3.6 预注册），全程遵守四件套——指标不得增删、基线条件逐项对齐（同 split/同预处理/同算力预算/同调参力度）、基线一律本环境重跑（禁引用他人数字）、全种子全网格报告。任何偏离 → RESULT.json 标 `protocol_violation: <哪一条>`，该组结果不得作为对比证据（`/result-to-claim` 会拦）。**禁止事后"优化"评测方式**——看结果后想改指标/改基线条件 = 改方法 = 回 Phase 5 重走 hash-lock

### Step 5: Dispatch Full Experiment to Background

**The full-experiment dispatch sequence is FIXED and top-to-bottom — the agent MUST execute Step 5.0 (smoke) → Step 5.1 (method select) → Step 5.2 (dispatch) → Step 6 (return) in this exact order. Dispatching a full experiment WITHOUT first running Step 5.0 is a contract violation — the agent must NEVER skip the smoke gate because it's "only a 1-step slice".**

1. **Step 5.0 — Full-Code Smoke Gate** (v3.2, MANDATORY — see below; produces `.SMOKE.json`)
2. **Step 5.1 — Dispatch Method Selection** (tmux → nohup → systemd)
3. **Step 5.2 — Execute Dispatch** (writes `FULL_EXPERIMENT_DISPATCH.json`)
4. **Step 6 — Return to Orchestrator** (immediate, do not wait)

> **v3.2 hard-wiring note (the runtime bug this fixes)**: in the prior structure, Step 5.0 was a **buried subsection** between Step 5 (dispatch) and Step 5.1 (method) — the agent read the numbered Step 4→5→6 chain and **silently skipped 5.0** because it was not in the explicit execution list. The Q-SGD-BS-GAP test run confirmed this: `experiments/full/` has `FULL_EXPERIMENT_DISPATCH.json` + `STATUS.json` (state=DONE, 184s) but **NO `.SMOKE.json`** — the full experiment ran successfully by luck (the script happened to work), but the smoke gate that v3.2 mandates to catch a 6-hour-late crash never executed. This is the same buried-subsection bug class as the auto-review-loop B.2 fix. The `.SMOKE.json` file is the load-bearing evidence — a full dispatch that completes without first writing `.SMOKE.json` is invalid regardless of whether the experiment ultimately succeeded.

**Background dispatch is MANDATORY for full experiments.** The agent must NOT wait in the foreground for long-running jobs.

**v5.0 后台调度阈值规则（防 agent 超时）**:

| 条件（任一满足即强制后台） | 动作 |
|---------------------------|------|
| 预估运行时间 > 15 分钟 | 后台调度（tmux/nohup/systemd），主 agent 立即返回 |
| 实验组 ≥ 5（含基线/消融/超参组合计） | 后台调度 + subagent 委托（见下） |
| 数据集需下载且 > 1GB | Step 0d 异步下载 + 后台实验 |
| 预估 ≤ 15 分钟且实验组 < 5 | 允许前台，但前台硬上限 15 分钟，超时自动转后台 |

**心跳与状态（后台任务必备）**: 后台脚本必须每 60 秒写一次 `STATUS.json`（state/progress/eta/last_error）——主 agent 通过轮询 STATUS.json 判活，**不做前台阻塞等待**；STATUS.json 超过 5 分钟未更新视为任务死亡，触发 Recovery Protocol。预估时间写入 `FULL_EXPERIMENT_DISPATCH.json` 的 `estimated_completion`，主 agent 据此安排轮询间隔（预估 <1h → 每 5 分钟轮询；1-6h → 每 30 分钟；>6h → 每 2 小时）。

### Subagent 委托协议（v5.0 — 防超时 + 并行加速）

主 agent 是**编排者**，不是执行者。满足以下条件时**必须**委托 subagent（宿主 agent 的 `task` 工具），主 agent 只做编排与聚合：

| 委托场景 | 委托内容 | 主 agent 保留 |
|---------|---------|--------------|
| 独立实验组 ≥3（基线/消融/超参各自独立） | 每组一个 subagent 并行跑（各自独立目录 `experiments/full/group_<name>/`） | 汇总聚合 + 写 EXPERIMENT_REPORT.md |
| 参数扫描 ≥6 个配置 | 按配置分片委托（每 subagent 2-3 个配置） | 扫描结果合并成表 |
| 数据预处理与训练可分离 | 预处理一个 subagent 先行，训练随后 | 依赖编排 |

**委托纪律**:
1. 每个 subagent 任务指令必须自包含：数据路径、脚本路径、输出目录、完成判据——subagent 之间**零共享状态**，只通过文件系统交换
2. subagent 产物统一写 `experiments/full/group_<name>/RESULT.json`（同 STATUS.json schema）——主 agent 聚合时只读 RESULT.json，不读 subagent 过程日志
3. 委托失败的组 → 主 agent 本地补跑该组（bounded 1 次），再失败 → 该组标记 `failed`，聚合报告如实列出，**不伪造**
4. subagent 数量上限 = CPU 核心数（GPU 实验 = GPU 数），防止资源争抢反而更慢

### Step 5.0: Full-Code Smoke Gate (v3.2 — MANDATORY before dispatch)

> **Why this exists (honest gap)**: the toy gate (Step 3) validates the *idea's reasoning chain* at 1-10% scale; it does NOT validate that the *full-scale script itself* runs end-to-end on the real data without crashing. [`leakage-audit`](../leakage-audit/SKILL.md) and [`logic-verification`](../logic-verification/SKILL.md) are both **structural/symbolic** audits that deliberately "do not run the code" (leakage-audit boundary) — so neither catches runtime crashes. Without this gate, a full experiment can be dispatched to background, run 6+ hours, and die at the final aggregation step because of a shape mismatch or an OOM only triggered at full scale — discovered only when Phase 10 reads a `failed` STATUS.json. This gate runs a 60-second end-to-end smoke on the full script at a 1-step/1-batch slice and refuses to dispatch if it cannot complete that slice.

**Procedure**:
1. **Slice to 1 step / 1 batch**: invoke the full-scale script (`code/experiments/full/{script}.py`) with an override that caps it to 1 training step (ML), 1 timestep (PDE sim), 1 bootstrap iteration (causal), 1 k-point (eigenvalue), or 1 claim (interpretive). The script MUST already expose such a cap (Step 4 design rule "Add checkpointing" implies a `--max-steps`/`--max-epochs`/`--steps` flag; if it doesn't, **add one now** — this is part of full-experiment design, not optional).
2. **Run with a 60-second foreground timeout** (`subprocess.run(timeout=60)`). This is cheap and stays in the foreground budget. The slice must: (a) import without exception, (b) load the real dataset (or a 1-row slice of it — verifying the data path + parsing are correct, not just synthetic), (c) execute 1 step of the actual computation, (d) write a checkpoint + 1 row to STATUS.json, (e) exit 0.
3. **Verdict**:
   - Smoke `PASS` (exit 0, 1 STATUS.json row written, no exception) → proceed to dispatch the **full** run (remove the step cap). The gate's only job was to prove the script is dispatchable; it does not validate the *results* (that's Phase 10's job).
   - Smoke `FAIL` (exception / non-zero exit / timeout / no STATUS.json row) → **DO NOT dispatch**. Classify the failure into one of 4 codes, each with a bounded fix path (this is the same early-stop taxonomy as the toy P5 dry-run, applied to the full script):

   | Smoke failure code | Trigger | Fix path (bounded) |
   |---------------------|---------|--------------------|
   | `IMPORT_OR_SYNTAX` | `SyntaxError`/`ImportError`/`ModuleNotFoundError` in first 5s | Fix the script (1 retry); re-run smoke |
   | `DATA_PATH_BROKEN` | `FileNotFoundError` on dataset / `KeyError` on column / shape mismatch | Fix data path or parsing (1 retry); re-run smoke. If the dataset genuinely isn't downloaded yet (Step 0d pending), **do not block** — dispatch a `data_pending` smoke that skips the data step, and the full run's STATUS.json will record `status: waiting_on_data` until Step 0d completes |
   | `OOM_AT_SLICE` | `RuntimeError: CUDA out of memory` / `MemoryError` even at 1 step | Reduce `scale_ratio` or `batch_size` in the full config (1 retry); re-run smoke. If still OOM at 1 step, the full run is `BLOCKED, reason_code: oom_at_minimal_scale` — do not dispatch a job that cannot even take 1 step |
   | `LOGIC_RUNTIME_CRASH` | `ValueError`/`AssertionError`/`KeyError` mid-step (not import, not data, not OOM) | This is a real bug — fix the script logic (1 retry); re-run smoke. If it persists, **fallback to Phase 6** (the derivation assumption the full script encodes may be wrong) per the Phase 8 FATAL→Phase 6 contract |

   All fix paths are bounded to **1 retry** — the smoke gate is not a debugging loop; if 1 fix doesn't clear it, the full dispatch is `BLOCKED` with the failure code, surfacing to the human. Never dispatch a full experiment whose 1-step smoke fails twice.

4. **Smoke artifact**: write `experiments/full/{experiment_id}.SMOKE.json`:
   ```json
   {"experiment_id":"...","smoke_scale":"1-step","smoke_result":"PASS|FAIL","fail_code":"<code or null>","fix_attempts":0,"status_row_written":true,"executed_at":"<ISO8601>","duration_seconds":<n>}
   ```
   Phase 10 (`/result-to-claim`) reads this — if `smoke_result=FAIL` and a full DISPATCH.json exists anyway, that's an invariant violation (Phase 9 INV-check catches it).

**Boundaries**:
- The smoke runs at **1 step, NOT 1% of steps** — it validates runnability, not convergence. Running 1% would itself take minutes on a full-scale job; 1 step is seconds.
- The smoke is **foreground** (≤60s budget). It is NOT background-dispatched — its whole point is a synchronous gate before the async dispatch.
- The smoke does **not** validate result *correctness* — only that the script executes end-to-end on real data for 1 step without crashing. Correctness is Phase 10 (`/result-to-claim`) + Phase 8 (`/logic-verification`).
- If the full script has no step-cap flag, adding one is **part of Step 4 (Design Full Experiment)**, retroactively enforced here. A full script that cannot be sliced to 1 step is itself a design defect.
- This gate is **additive to** the toy gate (Step 3): toy validates the *idea* at 1-10% scale; smoke validates the *full script* at 1 step. Both must pass before dispatch.

### Step 5.1: Dispatch Method Selection

```
Check environment:
  1. tmux available? → use tmux (preferred — easiest to monitor)
  2. nohup available? → use nohup (universal fallback)
  3. systemd available? → use systemd service (most robust)
  4. None? → BLOCKED (no background dispatch method available)
```

**tmux dispatch** (preferred):

```bash
# Create detached session
tmux new-session -d -s "sfexp_{experiment_id}" \
  "cd {workdir} && python code/experiments/full/{script}.py 2>&1 | tee logs/experiments/{experiment_id}.log"

# Monitor: tmux attach -t sfexp_{experiment_id}
```

**nohup dispatch** (universal fallback):

```bash
cd {workdir} && nohup python code/experiments/full/{script}.py \
  > experiments/full/{experiment_id}.log 2>&1 &
echo $! > experiments/full/{experiment_id}.pid
disown
```

**systemd dispatch** (most robust):

```bash
# Create service file
cat > /etc/systemd/system/sfexp-{experiment_id}.service << 'EOF'
[Unit]
Description=SciForge Experiment {experiment_id}
[Service]
WorkingDirectory={workdir}
ExecStart=/usr/bin/python3 code/experiments/full/{script}.py
StandardOutput=append:{workdir}/experiments/full/{experiment_id}.log
StandardError=append:{workdir}/experiments/full/{experiment_id}.log
Restart=on-failure
RestartSec=30
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl start sfexp-{experiment_id}
```

**Dispatch metadata** (`FULL_EXPERIMENT_DISPATCH.json`):

```json
{
  "experiment_id": "full_20260730_130000",
  "stage": "full",
  "dispatch_method": "tmux | nohup | systemd",
  "session_name": "sfexp_full_20260730_130000",
  "pid_file": "experiments/full/full_20260730_130000.pid",
  "log_file": "experiments/full/full_20260730_130000.log",
  "status_file": "experiments/full/STATUS.json",
  "checkpoint_dir": "experiments/full/checkpoints/",
  "started_at": "ISO-8601",
  "timeout_seconds": 86400,
  "monitor_command": "[command to check status]",
  "kill_command": "[command to stop experiment]",
  "resume_command": "[command to resume from last checkpoint]"
}
```

### Step 6: Return to Orchestrator

After dispatching the full experiment to background, the skill returns control to the orchestrator immediately. The orchestrator proceeds with other pipeline phases (writing, review, etc.) while the experiment runs.

**探索预算下限（v5.1 — Exploration Budget Floor，源自 CRUX 影子评估失败模式 #4）**:

**背景**（arXiv:2607.27191）：3000 美元 API 额度两次主运行都只用了约四成；探索阶段被压缩到区区几个小时；agent 在自审再度拒稿后、离截稿还有约 7 小时时**主动宣布"我写完了"**——"有钱不会花"。给更多资源不等于做更好的研究，但**未消耗最低探索预算就宣布完成**是明确的判断力缺陷。

**完成判据（Return payload 的 `budget_floor` 字段，缺项不得 verdict=PASS）**:

| 检查项 | 下限 | 说明 |
|--------|------|------|
| **技术路线探索** | ≥2 条独立技术路线被实际尝试（非仅文献调研），或 1 条路线 + 明确的路线否决证据 | "最初十几小时就放弃最有雄心的目标，此后再没做过战略级调整"是 CRUX 死法；至少试过一条替代路线或持有否决证据 |
| **强制实验矩阵完成度** | method-registry §3.5 矩阵的组完成率 ≥100%（lite 档按其缩减后口径） | 矩阵缺组 = 未完成，不是"可选没做" |
| **种子/重复预算消耗** | 鲁棒性组种子 ≥3（lite ≥2）全部跑完 | 半截种子数不得出均值±std 结论 |
| **失败实验记录** | 所有失败/负向运行记录在案（RESULT.json `failed` 条目 + 原因），未隐瞒 | CRUX 日志审查未发现粉饰——保持该优点，失败必须留痕 |
| **预算/时间余量声明** | Return payload 显式声明剩余算力/时间预算与"是否还有未尝试的可行路线" | agent 必须主动回答"还有没有没试的路"——回答"有"而未试 → 不允许宣布完成 |

**硬规则**:
1. `budget_floor.satisfied = false` 时，Return payload 的 verdict 不得为 `PASS`——只能是 `IN_PROGRESS`（继续探索）或 `BLOCKED`（资源/方向受限，附理由）
2. **"我写完了"需要证成**：宣布完成（任何阶段）必须附 `completion_justification`：已尝试路线清单 + 每条路线的状态（成功/否决+证据）+ 剩余未试路线清单（须为空或逐条说明为何不试）
3. 该字段由 `/auto-review-loop` 在每轮 Phase A 读取复核——发现 completion_justification 的"未试路线"非空而 agent 已停止探索 → 评审 concern 强制为 `experiment_redesign` 类（触发反缩减协议的实质性响应）

**Return payload:**

```json
{
  "verdict": "PASS",
  "toy_experiment": {
    "status": "PASS",
    "core_claim_validated": true,
    "toy_result_file": "experiments/toy/session_*/RESULT.json"
  },
  "full_experiment": {
    "status": "DISPATCHED",
    "dispatch_file": "experiments/full/FULL_EXPERIMENT_DISPATCH.json",
    "estimated_completion": "ISO-8601 or 'unknown'",
    "monitor_command": "cat experiments/full/STATUS.json"
  },
  "pipeline_continuation": "PROCEED — full experiment running in background, pipeline may continue with Phase 7+"
}
```

## Monitoring & Recovery

### Status File Schema (`STATUS.json`)

The full experiment script must write this file periodically:

```json
{
  "experiment_id": "full_20260730_130000",
  "status": "running | completed | failed | checkpoint_saved",
  "progress_percent": 45.2,
  "current_step": "epoch 45/100",
  "elapsed_seconds": 3600,
  "estimated_remaining_seconds": 4400,
  "last_checkpoint": "checkpoints/ckpt_045.pkl",
  "errors": [],
  "updated_at": "ISO-8601"
}
```

### Recovery Protocol

If the full experiment fails:
1. Read last checkpoint from `checkpoints/`
2. Resume from checkpoint (not from scratch)
3. If no checkpoint exists → restart from beginning
4. Max 2 recovery attempts, then BLOCKED

## Domain-Adaptive Experiment Templates

The skill auto-selects experiment templates based on `evidence_type`:

| evidence_type | Toy template | Full template | Key metrics |
|--------------|-------------|---------------|-------------|
| `derivational` | Numerical verification of symbolic result | Large-scale numerical sweep + convergence study | Relative error, convergence rate |
| `correlational` | OLS on 10% sample | Full regression + robustness checks | Coefficient, p-value, R², Oster bound |
| `causal_inference` | DiD/IV on synthetic known-effect data | Full identification + placebo + sensitivity | ATE, first-stage F, parallel trends p |
| `experimental` | Power analysis + pilot effect size | Full protocol + pre-registration spec | Effect size, CI, power, p-value |
| `simulational` (physics/PDE) | Coarse mesh simulation | Fine mesh + convergence + benchmark | CFL number, residual norm, mesh-independence |
| `simulational` (eigenvalue/band-structure) | Coarse k-grid diagonalization; compare gap vs analytical/derived expression | Fine k-grid + k-point convergence study + benchmark | k-grid convergence, relative error vs analytical gap, eigenvalue residual |
| `simulational` (ML/training) | Train 2 small models (idea vs baseline) on 10% data, 3-10 epochs | Full training + ablation sweep (remove novel component) | idea_val_loss vs baseline_val_loss, gradient_health |
| `interpretive` | Argument coherence on 3 claims | Full textual analysis + counter-evidence survey | Coherence score, counter-evidence count |

## Boundaries

- **Toy experiment is MANDATORY for non-theory-only problems.** Never skip toy and go straight to full.
- **Toy dispatch decision is load-bearing (v2.1).** Estimate toy wall-clock BEFORE running. If estimated > `toy_bg_threshold` (default 300s), dispatch the toy to background as `toy_bg` — do NOT block the foreground. The toy gate verdict is read from `RESULT.json` after `toy_bg` completes, at the appropriate downstream gate (never busy-wait). The same gate semantics (PASS→full, FAIL→kill idea) apply whether toy ran foreground or background.
- **Full experiment MUST run in background.** The agent must not wait in the foreground.
- **FAIL toy = kill the idea.** Do not rationalize, do not retry with a different toy test (except the bounded 1 retry for INCONCLUSIVE/TIMEOUT/ERROR). This holds for both foreground toy and `toy_bg`.
- **Domain-agnostic by design.** The experiment template is selected by evidence_type, not by discipline label.
- **One core claim, one toy test.** Do not bundle multiple hypotheses into the toy experiment.
- **The experiment script is written by the agent, not pre-coded.** This is dynamic-tooling-style: the agent writes the script, tests it, and runs it.
- **Background dispatch is non-negotiable.** If no background method is available (no tmux, no nohup, no systemd), BOTH the full experiment AND a `toy_bg` are BLOCKED — the agent does NOT wait in foreground. A foreground toy (≤ threshold) may still run if the dispatch stack is unavailable, since it stays within the 5-min foreground budget.
- **STATUS.json polling feeds Phase 10.** Both `toy_bg` and full background jobs write `STATUS.json`. The orchestrator does NOT poll; it reads `STATUS.json` once at Phase 10 (`/result-to-claim`). If a background job is still `running`, use whatever completed results exist (foreground toy, or partial) + note "experiment pending". This is the single integration seam between background experiments and the claim gate.

## Output Protocols
> **v5.2 评判产物位置**：本 skill 产出的机读 verdict/hash/审计 JSON 一律写入 `verdicts/`（文件名见 [`output-protocol.md`](../../shared-references/output-protocol.md) 产物目录结构；叙述性报告留在原 stage 目录）。


> Follow the shared output protocol for all output files (versioned writes, MANIFEST logging, output language):
> - **[Output Protocol](../../shared-references/output-protocol.md)** — merged single source of truth

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../../orchestrator/auto-pipeline/SKILL.md) — orchestrator that invokes this skill at Phase 6b/6c
- [`../meta-skills/dynamic-sandbox/SKILL.md`](../../meta-skills/dynamic-sandbox/SKILL.md) — used for toy experiment code execution
- [`../meta-skills/dynamic-tooling/SKILL.md`](../../meta-skills/dynamic-tooling/SKILL.md) — used when experiment needs custom tools
- [`../../shared-references/engineering-grounding-contract.md`](../../shared-references/engineering-grounding-contract.md) — EG axis informs experiment scope
- [`../../shared-references/domain-adaptive-pipeline.md`](../../shared-references/domain-adaptive-pipeline.md) — evidence_type drives experiment template
