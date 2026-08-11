---
name: experiment-execution
description: "Two-stage experiments (toy→full+background) with v3.2 proxy auto-mount + async dataset download + v3.4 Step 0d.0 local benchmark registry check (avoid re-download) + Step 5.0 full-code smoke gate (1-step end-to-end, writes .SMOKE.json, wired into ordered chain before dispatch). Phase 6b/6c. Invoke for any computational/experimental verification."
type: support-skill
role: experiment-runner
version: 1.4.0
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
- `verification_type = theory+experiment` → run src/data experiments
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
5. **What does the discipline count as enough? (v6.0)** — read `evidence_norm_profile.sample_size_norm` from `domain-signature.json`: seed counts / run counts / scale of the FULL matrix must reach the discipline's published norm (toy may run smaller — it is a direction verdict, not paper evidence). A shortfall must be justified item-by-item in BUDGET_FLOOR's `completion_justification`; unknown norm → default ≥3 seeds / ≥2 scales / baseline+ablation (method-registry §3.5 minimums)

### Step 0p: Network Proxy Auto-Mount (MANDATORY before any dataset/model download)

**Never skip dataset/model/dependency downloads due to network problems** (user hard requirement). Toy/full experiments often need to pull datasets or pretrained weights from GitHub / HuggingFace / ModelScope / arXiv / Zenodo / Kaggle / OpenNeuro, etc.; this skill must complete proxy mounting before any network request, with logic aligned to `universal-retrieval`'s "Proxy Auto-Detection" (the same `literature/.proxy-resolved.json` can be reused):

1. **Reuse an already-probed proxy**: if `literature/.proxy-resolved.json` exists with `detected_at` < 1h old, or the environment variables `http_proxy`/`https_proxy`/`ALL_PROXY` are already set, reuse directly and skip probing.
2. **Candidate port probing** (same sequence as universal-retrieval): `8099` (mihomo mixed-port) → `7890` (Clash HTTP) → `7892` (Clash SOCKS) → `1080` → `8080`. Try each with `socket.connect_ex(('127.0.0.1',<port>), timeout=2)`; after TCP succeeds, double-check via that proxy with a GET to `https://huggingface.co` or `https://github.com` (`timeout=3s`, expect 2xx/3xx). The first candidate passing both checks is selected.
3. **Mount**: write `experiments/.proxy-resolved.json` (the experiment-side copy, same schema as `literature/.proxy-resolved.json`), and set `http_proxy`/`https_proxy` for all subsequent downloads.
4. **All candidates unreachable** → **never give up on the download**: (a) try direct connection once (`timeout=10s`); (b) if direct fails → move to "Step 0d Async Dataset Download" (nohup background) and downgrade the download verdict to `WARN` — **never downgrade to SKIP/NOT_APPLICABLE/BLOCKED for network reasons**. Network can only downgrade PASS to WARN.
5. **Re-probing**: if the mounted proxy times out 2 consecutive times → delete `.proxy-resolved.json` and return to step 2 to re-probe.
6. **Download artifact archiving**: write all downloaded datasets/weights to `experiments/datasets/` or `experiments/weights/`, and register them in `experiments/.downloads.json` with `{source, url, sha256, size_bytes, downloaded_at, via_proxy:bool, method:"foreground|nohup"}`, for traceability by Phase 10 result-to-claim and Phase 15 citation-audit.

### Step 0d: Async Dataset Download (nohup — user hard requirement: large files/long tasks async in background)

When large datasets (HLE ~several GB, PaperBench, NatureBench, ImageNet, COCO, Pile, OpenWebText, HF Hub model weights) or environment dependencies (`pip install`, conda env, `huggingface-cli download`, `modelscope download`) are expected to take a long time, **you MUST download asynchronously in the background via `nohup` and immediately switch to other code-refactoring/test tasks**, following [`background-dispatch-protocol.md`](../../shared-references/background-dispatch-protocol.md):

**0d.0 — Check the local dataset registry first (v3.2 — avoid re-downloading existing benchmarks)**: before initiating any download, this skill **must first check the local benchmark registry** — the workspace often has benchmarks such as HLE / NatureBench / PaperBench pre-provisioned under `/root/autodl-tmp/datasets/` (or the project-root `datasets/`) (with `README.md` + `INDEX.md` + parquet/csv). Lookup order:
1. Read `datasets/README.md` (benchmark registry) + each `datasets/<name>/INDEX.md` — if the target dataset is already registered with complete files (e.g., `datasets/PaperBench/train.parquet` exists and size > 0), **directly symlink or copy it into `experiments/datasets/<name>/`**, record `method: "local_registry", via_proxy: false, source: "local datasets/<name>"` in `.downloads.json`, and **skip the network download**.
2. If registered but with missing files (e.g., HLE full parquet incomplete because it is gated, only README/eval.yaml present) → use the nohup async download below to complete the missing parts (gated datasets require `huggingface-cli login` first).
3. If not registered at all → use the nohup async download below for the full dataset.
**Strictly forbidden**: re-downloading the same dataset from HF when `datasets/<name>/` already exists — wastes bandwidth + time + risks fetching a different version.

1. **Trigger thresholds**: single file/batch estimated > 2min or size > 100MB → MUST background; 2-5min/≤100MB → SHOULD background (agent's judgment); <2min/≤100MB → foreground.
2. **nohup dispatch** (same stack as Step 5, tmux→nohup→systemd fallback):
   ```bash
   cd {workdir} && nohup bash -c '
     export http_proxy="{proxy_url}" https_proxy="{proxy_url}" ALL_PROXY="{proxy_url}"
     {download_command}   # e.g.: huggingface-cli download <repo> --local-dir experiments/datasets/<name>
                          # or: wget -c <url> -O experiments/datasets/<name>
                          # or: pip install -r requirements-exp.txt
   ' > experiments/downloads/{name}.log 2>&1 &
   echo $! > experiments/downloads/{name}.pid
   disown
   ```
3. **Return immediately**: after dispatching, **do not wait**; the foreground immediately switches to Step 1 (design the toy) / other phases; download status is collected at Phase 10 (result-to-claim) — read `experiments/downloads/{name}.STATUS.json`; if `status=running`, continue the toy with whatever has finished downloading (reduce scale); if `failed`, retry once per the Recovery Protocol; if still failing, verdict WARN + record `source_status: unavailable`.
4. **Parallel downloads**: multiple independent datasets/dependencies may each launch their own nohup job in parallel (different `{name}`), without blocking each other; each writes its own `.pid`/`.log`/`.STATUS.json`.
5. **Download integrity check**: after completion, compute the sha256 of each file and write it to `experiments/.downloads.json` (step 0p·6); compare the hash against the upstream-published one (HuggingFace/HF Hub `LFS` sha256, Zenodo checksum); mismatch → WARN + re-download once.
6. **Resume support**: prefer tools that support `-c`/`--resume`/`--local-dir-use-symlinks False` (`wget -c`, `aria2c -c`, `huggingface-cli download` with built-in resume); STATUS.json records the `resume_from` field.

**Strictly forbidden**: skipping dataset acquisition because downloads are slow/timed out, substituting purely synthetic data for the real dataset (unless domain-signature explicitly allows it), or basing a toy gate PASS on incomplete, not-fully-downloaded data without flagging it.

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
         → src/experiments/toy/session_{timestamp}/toy_experiment.py

Step 2c: Execute with timeout
         → subprocess.run(timeout=timeout_toy)

**P5 Dry-Run early stopping (v3.1)**: toy execution should first dry-run on a 1%-5% subset / 3-5min hard cap; three early-stop types trigger automatically and feed back into the idea-revision loop, avoiding waste of full-scale compute:

| Early-stop reason | Trigger | Feedback action |
|----------|----------|----------|
| `UNCAUGHT_EXCEPTION` | script throws an exception (import/syntax/runtime) | loop back to Phase 6b to fix the code (1 retry) |
| `LOSS_EXPLOSION` | output contains NaN/Inf or metric absolute value > threshold | loop back to Phase 6 to check derivation assumptions (reformulate) |
| `BELOW_BASELINE` | metric > 1.5× baseline | loop back to Phase 2 to regenerate the idea (bounded 2 rounds) |
| `DRY_RUN_TIMEOUT` | exceeds the hard cap | reduce scale and retry once; still timeout → toy gate BLOCKED |

All early-stop decisions are mechanical (no LLM cost); only a `PASS` dry-run proceeds to the normal RESULT.json gating flow.

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
  "core_claim_validated": true,
  "seeds_used": 3,
  "kill_signal": null,
  "recommendation": "PROCEED_TO_FULL | BLOCK | REDESIGN"
}
```

`core_claim_validated` (bool) and `seeds_used` (int) are **mandatory**:
the auto-pipeline Phase 6b toy gate reads both (PASS requires
`core_claim_validated: true`; multi-seed reproducibility claims are
checked against `seeds_used`). Omitting either degrades the gate to
INCONCLUSIVE.

**Gate logic** (`gate_logic` field) — how multiple metrics combine into the PASS/FAIL verdict:
- `all_metrics_pass` (default): every metric's `passed` must be true. Use for problems where all criteria are load-bearing (e.g., causal inference needs correct sign AND magnitude AND parallel-trends).
- `primary_only`: only `primary_metric.passed` decides; secondary metrics are informational. Use when secondary checks are diagnostic but not gating.
- `majority_pass`: PASS if >50% of all metrics pass. Use for exploratory toys where no single metric is decisive.

**For causal_inference toys specifically** (per `discipline-writing.md` §0): `primary_metric` = recovered ATE/coefficient magnitude vs known effect; `secondary_metrics` MUST include coefficient sign and parallel-trends p-value — all three load-bearing, so `gate_logic: all_metrics_pass`.

### Step 3: Toy Gate (Decision Point — v5.0 KILL-or-PIVOT stopping protocol)

| RESULT.status | Action |
|---------------|--------|
| `PASS` | Proceed to full experiment design (Step 4) |
| `FAIL` | **Enter the KILL-or-PIVOT decision** (see below) — no longer uniformly kill the idea |
| `INCONCLUSIVE` | Redesign toy experiment (bounded 1 retry). If still inconclusive → `BLOCKED`. |
| `TIMEOUT` | Reduce scale_ratio, retry once. If still timeout → `BLOCKED`. |
| `ERROR` | Diagnose error, fix script, retry once. If still error → `BLOCKED`. |

**Hard rule**: A FAIL toy experiment **must not** proceed to full experiment — this is the life-or-death verdict on the idea, preventing compute waste on dead ends.

**Zero-to-one stopping protocol (KILL-or-PIVOT) — solves "zero-to-one never knows when to stop"**:

Incremental papers have marginal-gain signals to stop on; zero-to-one does not — it must rely on **pivot on falsification**. FAIL trigger conditions (both must hold simultaneously, to prevent false kills):
1. The negative result is **significant** (core metric below baseline and the difference > noise level)
2. The negative result is **reproducible** (same direction under ≥2 random seeds, or a single toy re-run still FAILs)

Once triggered, enter the decision (written to the `kill_or_pivot` field of `EXPERIMENT_REPORT.md`):

| Decision | Applies when | Action |
|------|------|------|
| **PIVOT** | problem is valuable, current method path falsified | keep the problem and RQ, redesign with a different method/component → loop back to Phase 5 (method-registry re-registration) → re-run the toy. **PIVOT budget ≤2**; over budget forces KILL |
| **KILL** | core hypothesis falsified with no viable alternative path, or PIVOT budget exhausted | invoke `/kill-argument` to write the kill argument → `BLOCKED, reason: core_hypothesis_falsified` → loop back to Phase 2 to change the idea |

**Forbidden behaviors**:
- "Keep tuning to force-rescue" is forbidden — when the toy has already falsified the core direction, tuning is stalling, not PIVOT
- Repackaging negative toy results as "honest findings" to keep going is forbidden (negative-result discipline: see result-to-claim)

**Failure → lesson (v1.4.0, experience replay)**: every FAIL / TIMEOUT / ERROR and every KILL-or-PIVOT decision is recorded with root cause + fix into the run's `LESSONS.json` (`failed_experiments` / `code_errors` / `idea_rollbacks`) per [`experience-replay-contract.md`](../../shared-references/experience-replay-contract.md), so the next run avoids the same configuration (`avoid` fields are hard exclusions at Phase 6b). The failure is thus *useful* (reusable judgment) without ever becoming a paper contribution.
- PIVOT must change the **method** (method-registry re-registration, hash re-lock), not the hyperparameters

### Step 4: Design Full Experiment

If toy gate passed, design the full-scale experiment:

1. **Scale up** from toy to full (full dataset, full epochs, full resolution)
2. **Add rigor** — proper controls, ablation, robustness checks
3. **Add checkpointing** — save intermediate results every `checkpoint_interval` seconds
4. **Add monitoring** — periodic status updates to `experiments/full/STATUS.json`
5. **Expose a 1-step cap flag** (`--max-steps`/`--max-epochs`/`--steps`) — Step 5.0's smoke gate REQUIRES slicing the full script to 1 step; a full script with no step-cap flag is itself a design defect. Add the flag here, retroactively enforced at Step 5.0.
6. **Execute per the pre-registered evaluation protocol (v5.2 — fair evaluation)**: read `.sciforge/verdicts/EVALUATION_PROTOCOL.json` (method-registry §3.6 pre-registration) and obey the four-part contract throughout — metrics must not be added/removed, baseline conditions aligned item by item (same split / same preprocessing / same compute budget / same tuning effort), all baselines re-run in this environment (citing others' numbers is forbidden), report across all seeds and the full grid. Any deviation → mark `protocol_violation: <which clause>` in RESULT.json, and that result set must not serve as comparison evidence (`/result-to-claim` will block it). **Post-hoc "optimizing" the evaluation is forbidden** — wanting to change metrics/baseline conditions after seeing results = changing the method = loop back to Phase 5 and redo hash-lock

### Step 5: Dispatch Full Experiment to Background

**The full-experiment dispatch sequence is FIXED and top-to-bottom — the agent MUST execute Step 5.00 (security gate) → Step 5.0 (smoke) → Step 5.1 (method select) → Step 5.2 (dispatch) → Step 6 (return) in this exact order. Dispatching a full experiment WITHOUT first running Step 5.00 and Step 5.0 is a contract violation — the agent must NEVER skip the security gate or the smoke gate because it's "only a static scan" / "only a 1-step slice".**

1. **Step 5.00 — Security Gate** (v5.3, MANDATORY — see below; verdict recorded in `FULL_EXPERIMENT_DISPATCH.json` as `security_gate`)
2. **Step 5.0 — Full-Code Smoke Gate** (v3.2, MANDATORY — see below; produces `.SMOKE.json`)
3. **Step 5.1 — Dispatch Method Selection** (tmux → nohup → systemd)
4. **Step 5.2 — Execute Dispatch** (writes `FULL_EXPERIMENT_DISPATCH.json`)
5. **Step 6 — Return to Orchestrator** (immediate, do not wait)

> **v3.2 hard-wiring note (the runtime bug this fixes)**: in the prior structure, Step 5.0 was a **buried subsection** between Step 5 (dispatch) and Step 5.1 (method) — the agent read the numbered Step 4→5→6 chain and **silently skipped 5.0** because it was not in the explicit execution list. The Q-SGD-BS-GAP test run confirmed this: `experiments/full/` has `FULL_EXPERIMENT_DISPATCH.json` + `STATUS.json` (state=DONE, 184s) but **NO `.SMOKE.json`** — the full experiment ran successfully by luck (the script happened to work), but the smoke gate that v3.2 mandates to catch a 6-hour-late crash never executed. This is the same buried-subsection bug class as the auto-review-loop B.2 fix. The `.SMOKE.json` file is the load-bearing evidence — a full dispatch that completes without first writing `.SMOKE.json` is invalid regardless of whether the experiment ultimately succeeded.

**Background dispatch is MANDATORY for full experiments.** The agent must NOT wait in the foreground for long-running jobs.

**v5.0 background dispatch threshold rules (prevent agent timeouts)**:

| Condition (any one forces background) | Action |
|---------------------------|------|
| Estimated runtime > 15 min | background dispatch (tmux/nohup/systemd), main agent returns immediately |
| Experiment groups ≥ 5 (counting baselines/ablations/hyperparameter combos together) | background dispatch + subagent delegation (see below) |
| Dataset must be downloaded and > 1GB | Step 0d async download + background experiment |
| Estimated ≤ 15 min and experiment groups < 5 | foreground allowed, but foreground hard cap 15 min; on timeout auto-convert to background |

**Heartbeat and status (mandatory for background tasks)**: background scripts must write `STATUS.json` every 60 seconds (state/progress/eta/last_error) — the main agent judges liveness by polling STATUS.json and **must not block-wait in the foreground**; if STATUS.json is not updated for more than 5 minutes the task is considered dead, triggering the Recovery Protocol. The estimated completion time is written to `estimated_completion` in `FULL_EXPERIMENT_DISPATCH.json`; the main agent sets its polling interval accordingly (estimated <1h → poll every 5 min; 1-6h → every 30 min; >6h → every 2 hours).

### Subagent Delegation Protocol (v5.0 — timeout prevention + parallel speedup)

The main agent is an **orchestrator**, not an executor. When the following conditions hold, it **must** delegate to subagents (the host agent's `task` tool); the main agent only orchestrates and aggregates:

| Delegation scenario | Delegated work | Main agent keeps |
|---------|---------|--------------|
| Independent experiment groups ≥3 (baselines/ablations/hyperparameters each independent) | one subagent per group running in parallel (each in its own directory `experiments/full/group_<name>/`) | summary aggregation + writing EXPERIMENT_REPORT.md |
| Parameter sweep ≥6 configurations | shard by configuration (2-3 configurations per subagent) | merging sweep results into a table |
| Data preprocessing separable from training | one preprocessing subagent runs first, training follows | dependency orchestration |

**Delegation discipline**:
1. Every subagent task instruction must be self-contained: data paths, script paths, output directory, completion criteria — subagents share **zero shared state** and exchange only through the filesystem
2. Subagent artifacts uniformly go to `experiments/full/group_<name>/RESULT.json` (same schema as STATUS.json) — when aggregating, the main agent reads RESULT.json only, never subagent process logs
3. A group whose delegation failed → the main agent re-runs that group locally (bounded 1 time); if it fails again → mark the group `failed` and list it truthfully in the aggregation report — **never fabricate**
4. Subagent count cap = number of CPU cores (GPU experiments = number of GPUs), preventing resource contention from slowing things down

### Step 5.00: Security Gate (v5.3 — MANDATORY before smoke/dispatch)

> **Why this exists (P1-8 gap)**: full-mode experiment scripts are agent-authored and had been executed directly on the host with no security scan — toy mode already runs inside [`dynamic-sandbox`](../../meta-skills/dynamic-sandbox/SKILL.md), but full mode had no isolation at all. The gate is a static scan (executes nothing) and MUST run before Step 5.0, because the smoke slice already *executes* the script: no agent-authored full-mode code may run on the host, even as a 1-step slice, before being scanned.

Before dispatching ANY full-mode experiment script, run the scanner (exit 0 = PASS/WARN, exit 3 = BLOCKED):

```bash
python3 scripts/security_scan.py src/experiments/full/{script}.py   # add --json for machine-readable output
```

| Verdict | Action |
|---------|--------|
| `PASS` | Record `security_gate: "PASS"` in `FULL_EXPERIMENT_DISPATCH.json`; proceed to Step 5.0 |
| `WARN` | Record `security_gate: "WARN"` + the finding list in `FULL_EXPERIMENT_DISPATCH.json`; proceed only with a logged justification (`security_gate_justification`) — never silence findings |
| `BLOCKED` | The run is REFUSED. Record `security_gate: "BLOCKED"` + reason in `FULL_EXPERIMENT_DISPATCH.json` and surface to the human — never auto-bypass; a rewritten script must pass a fresh scan before dispatch |

**Scope & notes**: the gate binds agent-authored scripts; user-provided scripts are exempt from blocking but are still scanned advisory (findings recorded the same way). Allowlists are supplied ONLY via explicit `--allow FILE` from the dispatching human/orchestrator — the scanner deliberately does NOT auto-load any allowlist sitting next to the script, because the script's directory is agent-authored workspace and an agent must never be able to write its own exemption. Allowlist entries are echoed in the scan report for auditability, and a `host:` exemption never exonerates credential access or exfiltration findings. Containerization (`docker`/`podman`, never `--privileged`) remains the recommended stronger isolation when available; toy mode keeps using `dynamic-sandbox`. `FULL_EXPERIMENT_DISPATCH.json` (the full-mode DISPATCH.json) now carries `security_gate` — the artifact-registry owner may mirror this field into the artifact registry later.

### Step 5.0: Full-Code Smoke Gate (v3.2 — MANDATORY before dispatch)

> **Why this exists (honest gap)**: the toy gate (Step 3) validates the *idea's reasoning chain* at 1-10% scale; it does NOT validate that the *full-scale script itself* runs end-to-end on the real data without crashing. [`leakage-audit`](../leakage-audit/SKILL.md) and [`logic-verification`](../logic-verification/SKILL.md) are both **structural/symbolic** audits that deliberately "do not run the code" (leakage-audit boundary) — so neither catches runtime crashes. Without this gate, a full experiment can be dispatched to background, run 6+ hours, and die at the final aggregation step because of a shape mismatch or an OOM only triggered at full scale — discovered only when Phase 10 reads a `failed` STATUS.json. This gate runs a 60-second end-to-end smoke on the full script at a 1-step/1-batch slice and refuses to dispatch if it cannot complete that slice.

**Procedure**:
1. **Slice to 1 step / 1 batch**: invoke the full-scale script (`src/experiments/full/{script}.py`) with an override that caps it to 1 training step (ML), 1 timestep (PDE sim), 1 bootstrap iteration (causal), 1 k-point (eigenvalue), or 1 claim (interpretive). The script MUST already expose such a cap (Step 4 design rule "Add checkpointing" implies a `--max-steps`/`--max-epochs`/`--steps` flag; if it doesn't, **add one now** — this is part of full-experiment design, not optional).
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
  "cd {workdir} && python src/experiments/full/{script}.py 2>&1 | tee logs/experiments/{experiment_id}.log"

# Monitor: tmux attach -t sfexp_{experiment_id}
```

**nohup dispatch** (universal fallback):

```bash
cd {workdir} && nohup python src/experiments/full/{script}.py \
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
ExecStart=/usr/bin/python3 src/experiments/full/{script}.py
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

**Exploration budget floor (v5.1 — Exploration Budget Floor, from CRUX shadow-evaluation failure mode #4)**:

**Background** (arXiv:2607.27191): of a $3000 API budget, both main runs used only about 40%; the exploration phase was squeezed into a mere few hours; after its self-review rejected the draft again, with ~7 hours left before the deadline, the agent **proactively declared "I'm done writing"** — "having budget but not knowing how to spend it". More resources do not guarantee better research, but **declaring completion while the minimum exploration budget is unspent** is a clear judgment defect.

**Completion criteria (the `budget_floor` field of the Return payload; verdict=PASS is forbidden if any item is missing)**:

| Check item | Floor | Notes |
|--------|------|------|
| **Technical-route exploration** | ≥2 independent technical routes actually attempted (not just literature survey), or 1 route + explicit route-rejection evidence | "Abandoning the most ambitious goal within the first dozen hours and making no strategic-level adjustment afterward" is the CRUX death mode; at least one alternative route must have been tried, or rejection evidence held |
| **Mandatory experiment matrix completion** | group completion rate of the method-registry §3.5 matrix ≥100% (lite tier uses its reduced scope) | a matrix missing groups = incomplete, not "optional and skipped" |
| **Seed/replication budget consumed** | robustness-group seeds ≥3 (lite ≥2) all finished | partial seed counts must not produce mean±std conclusions |
| **Failed-experiment records** | all failed/negative runs recorded (RESULT.json `failed` entries + reasons), nothing concealed | the CRUX log audit found no whitewashing — keep this strength; failures must leave a trace |
| **Remaining budget/time declaration** | the Return payload explicitly declares remaining compute/time budget and "whether any viable route remains untried" | the agent must proactively answer "are there untried paths" — answering "yes" without trying them → completion may not be declared |

**Hard rules**:
1. When `budget_floor.satisfied = false`, the Return payload verdict must not be `PASS` — only `IN_PROGRESS` (continue exploring) or `BLOCKED` (resource/direction constrained, with reasons)
2. **"I'm done writing" requires justification**: declaring completion (at any stage) must attach `completion_justification`: list of attempted routes + status of each route (success / rejected + evidence) + list of remaining untried routes (must be empty, or explain item by item why not tried)
3. This field is read and re-verified by `/auto-review-loop` at each round's Phase A — if completion_justification's "untried routes" is non-empty while the agent has stopped exploring → the review concern is forced to the `experiment_redesign` class (triggering the anti-reduction protocol's substantive response)

**Persistence (v5.3)**: the budget-floor evaluation is ALSO written to `.sciforge/verdicts/BUDGET_FLOOR.json` (machine-readable verdict per [`schemas/BUDGET_FLOOR.schema.json`](../../shared-references/schemas/BUDGET_FLOOR.schema.json): `verdict` PASS/IN_PROGRESS/BLOCKED + `budget_floor.satisfied` + the five checks + `completion_justification` when declaring done). The Return payload carries the same content; the orchestrator's Phase 6c gate reads the verdict file (payload as fallback). Never silent-skip: an unevaluated floor is written as `IN_PROGRESS`, not omitted.

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
> **v5.2 verdict artifact location**: all machine-readable verdict/hash/audit JSON produced by this skill goes into `.sciforge/verdicts/` (for filenames see the artifact directory structure in [`output-protocol.md`](../../shared-references/output-protocol.md); narrative reports stay in their original stage directory).


> Follow the shared output protocol for all output files (versioned writes, MANIFEST logging, output language):
> - **[Output Protocol](../../shared-references/output-protocol.md)** — merged single source of truth

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../../orchestrator/auto-pipeline/SKILL.md) — orchestrator that invokes this skill at Phase 6b/6c
- [`../meta-skills/dynamic-sandbox/SKILL.md`](../../meta-skills/dynamic-sandbox/SKILL.md) — used for toy experiment code execution
- [`../meta-skills/dynamic-tooling/SKILL.md`](../../meta-skills/dynamic-tooling/SKILL.md) — used when experiment needs custom tools
- [`../../shared-references/engineering-grounding-contract.md`](../../shared-references/engineering-grounding-contract.md) — EG axis informs experiment scope
- [`../../shared-references/domain-adaptive-pipeline.md`](../../shared-references/domain-adaptive-pipeline.md) — evidence_type drives experiment template
