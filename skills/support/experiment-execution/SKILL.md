---
name: experiment-execution
type: support-skill
role: experiment-runner
version: 2.0.0
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

## Workflow

### Step 0: Determine Experiment Type

Read `FINAL_PROPOSAL.md` and `domain-signature.json` to determine:

1. **What needs to be validated?** — the idea's core claim (from FINAL_PROPOSAL.md)
2. **What is the minimal test?** — the smallest experiment that can validate or kill the core claim
3. **What scale is "toy"?** — typically 1-10% of full (subset of data, fewer epochs, coarser mesh, smaller sample)
4. **What is the full experiment?** — complete-scale validation

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
         → experiments/toy/session_{timestamp}/toy_experiment.py

Step 2c: Execute with timeout
         → subprocess.run(timeout=timeout_toy)

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

### Step 3: Toy Gate (Decision Point)

| RESULT.status | Action |
|---------------|--------|
| `PASS` | Proceed to full experiment design (Step 4) |
| `FAIL` | **Kill the idea.** Return `BLOCKED` with reason. Do NOT proceed to full experiment. |
| `INCONCLUSIVE` | Redesign toy experiment (bounded 1 retry). If still inconclusive → `BLOCKED`. |
| `TIMEOUT` | Reduce scale_ratio, retry once. If still timeout → `BLOCKED`. |
| `ERROR` | Diagnose error, fix script, retry once. If still error → `BLOCKED`. |

**Hard rule**: A FAIL toy experiment **must not** proceed to full experiment. This prevents wasting compute on dead-end ideas.

### Step 4: Design Full Experiment

If toy gate passed, design the full-scale experiment:

1. **Scale up** from toy to full (full dataset, full epochs, full resolution)
2. **Add rigor** — proper controls, ablation, robustness checks
3. **Add checkpointing** — save intermediate results every `checkpoint_interval` seconds
4. **Add monitoring** — periodic status updates to `experiments/full/STATUS.json`

### Step 5: Dispatch Full Experiment to Background

**Background dispatch is MANDATORY for full experiments.** The agent must NOT wait in the foreground for long-running jobs.

**Dispatch method selection** (`auto` mode):

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
  "cd {workdir} && python experiments/full/{script}.py 2>&1 | tee experiments/full/{experiment_id}.log"

# Monitor: tmux attach -t sfexp_{experiment_id}
```

**nohup dispatch** (universal fallback):

```bash
cd {workdir} && nohup python experiments/full/{script}.py \
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
ExecStart=/usr/bin/python3 experiments/full/{script}.py
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

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../../shared-references/output-manifest.md)** — log every output to MANIFEST.md

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../../orchestrator/auto-pipeline/SKILL.md) — orchestrator that invokes this skill at Phase 6b/6c
- [`../meta-skills/dynamic-sandbox/SKILL.md`](../../meta-skills/dynamic-sandbox/SKILL.md) — used for toy experiment code execution
- [`../meta-skills/dynamic-tooling/SKILL.md`](../../meta-skills/dynamic-tooling/SKILL.md) — used when experiment needs custom tools
- [`../../shared-references/engineering-grounding-contract.md`](../../shared-references/engineering-grounding-contract.md) — EG axis informs experiment scope
- [`../../shared-references/domain-adaptive-pipeline.md`](../../shared-references/domain-adaptive-pipeline.md) — evidence_type drives experiment template
