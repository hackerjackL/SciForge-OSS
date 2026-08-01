# Background Dispatch Protocol

> **Status (v2.1)**: Protocol for dispatching long-running tasks (experiments, compilations, simulations) to background execution. Prevents front-end timeouts in Claude Code, Codex, Cursor, and other AI development tools.
>
> **Core principle**: The agent must NEVER block the foreground on a task whose wall-clock time may exceed the tool's session timeout. Dispatch to background, continue pipeline, check results later.
>
> **v2.1 addition — toy_bg**: the background-dispatch contract is no longer full-experiment-only. A **toy experiment estimated > 5 min** is also dispatched to background (`toy_bg`), using the same dispatch methods and STATUS.json contract. This closes the gap where a "toy" that happens to be slow would still block the foreground. The toy gate verdict is read from `RESULT.json` only after `toy_bg` completes — never busy-waited.

## When to Background-Dispatch

| Condition | Action |
|-----------|--------|
| Estimated wall-clock > 5 minutes | **MUST** background-dispatch |
| Estimated wall-clock 2-5 minutes | SHOULD background-dispatch (agent discretion) |
| Estimated wall-clock < 2 minutes | Run in foreground |
| Task is idempotent and resumable | Background-dispatch preferred |
| Task produces critical gating artifact | Run in foreground if < 5 min; background + poll otherwise |
| **Dataset / model-weight / env-dep download > 2min or > 100MB** | **MUST** background-dispatch (see Dataset Download section) |

**Hard rule**: Any full-scale experiment, any multi-hour simulation, any GPU training run — these MUST be background-dispatched. The agent must not `subprocess.run()` with a 4-hour timeout and block the session. **Likewise, a toy experiment estimated > 5 min MUST be dispatched as `toy_bg`** — "toy" status does not grant a foreground-blocking exemption. **Likewise, any dataset/model-weight download estimated > 2min MUST be background-dispatched** — "it's just a download" does not grant a foreground-blocking exemption, and network failure may NEVER cause the download step to be skipped (only downgraded to WARN).

## Dispatch Methods

### Method 1: tmux (Preferred)

**Detection**: `which tmux` returns a path.

**Dispatch**:
```bash
tmux new-session -d -s "{session_name}" \
  "cd {workdir} && {command} 2>&1 | tee {log_file}"
```

**Monitor**:
```bash
# Check if still running
tmux has-session -t {session_name} 2>/dev/null && echo "running" || echo "stopped"

# Tail log
tmux capture-pane -t {session_name} -p | tail -20

# Attach (for human inspection)
tmux attach -t {session_name}
```

**Kill**:
```bash
tmux kill-session -t {session_name}
```

### Method 2: nohup + PID tracking (Universal Fallback)

**Detection**: `which nohup` returns a path (available on virtually all Unix systems).

**Dispatch**:
```bash
cd {workdir} && nohup {command} > {log_file} 2>&1 &
echo $! > {pid_file}
disown
```

**Monitor**:
```bash
# Check if process alive
kill -0 $(cat {pid_file}) 2>/dev/null && echo "running" || echo "stopped"

# Tail log
tail -20 {log_file}
```

**Kill**:
```bash
kill $(cat {pid_file})
```

### Method 3: systemd service (Most Robust)

**Detection**: `which systemctl` returns a path AND running as root or with sudo.

**Dispatch**: Write a transient service file, `systemctl start`.

**Monitor**: `systemctl status {service_name}`

**Kill**: `systemctl stop {service_name}`

### Method Selection (Auto Mode)

```
if tmux available → tmux
elif nohup available → nohup
elif systemd available AND has privileges → systemd
else → BLOCKED (cannot background-dispatch)
```

## Status Polling Contract

When the pipeline dispatches a background job, it must establish a polling contract:

1. **STATUS.json** — the background job writes this file periodically (every `checkpoint_interval` seconds)
2. **The orchestrator does NOT poll** — it continues with other phases
3. **At the "results collection" phase** (Phase 10 or later), the orchestrator checks STATUS.json
4. If `status: completed` → read results, continue
5. If `status: running` → the orchestrator logs "experiment still running" and continues with what's available (toy results + partial full results)
6. If `status: failed` → read error log, attempt recovery (bounded 2 retries)

## Checkpoint Schema

Background jobs must support checkpointing for long runs:

```
experiments/full/checkpoints/
├── ckpt_001.pkl    ← checkpoint at step 1
├── ckpt_002.pkl    ← checkpoint at step 2
├── ...
└── ckpt_latest.pkl ← symlink to most recent
```

On recovery:
1. Find `ckpt_latest.pkl`
2. Resume from that checkpoint
3. If no checkpoint → restart from beginning

## Dataset / Model-Weight Download Dispatch (v2.2 — network never skips)

Beyond experiments, this protocol also governs **dataset, pre-trained-weight, and environment-dependency downloads** (HLE, PaperBench, NatureBench, ImageNet, COO, HF Hub weights, ModelScope models, `pip install`/conda env for experiment deps). The download case has two extra constraints over a plain long-running job:

1. **Network never skips** — a download failure may downgrade the source's verdict from `PASS` to `WARN`, but may NEVER downgrade it to `SKIP` / `NOT_APPLICABLE` / `BLOCKED`-by-network. The pipeline must keep going on the proxy + nohup retry path until the dataset is on disk or 2 bounded retries are exhausted (then WARN + `source_status: unavailable`).
2. **Proxy auto-mount before download** — every download must run after the proxy is mounted per `universal-retrieval`「代理自主检测」(candidate ports `8099→7890→7892→1080→8080`, TCP+HTTP double-check). The `http_proxy`/`https_proxy`/`ALL_PROXY` env vars MUST be exported inside the nohup command so the background job inherits them.

**Dispatch** (reuses Method 1/2/3 above; nohup example with proxy env + resume):
```bash
cd {workdir} && nohup bash -c '
  export http_proxy="{proxy_url}" https_proxy="{proxy_url}" ALL_PROXY="{proxy_url}"
  # prefer resumable tools: wget -c / aria2c -c / huggingface-cli download (built-in resume)
  {download_command}
' > {downloads_dir}/{name}.log 2>&1 &
echo $! > {downloads_dir}/{name}.pid
disown
```

**Status file** (`{downloads_dir}/{name}.STATUS.json`, written by the download script or a wrapper):
```json
{"name":"<dataset>","status":"running|completed|failed","downloaded_bytes":123456789,"total_bytes":987654321,"sha256":"<if completed>","via_proxy":true,"resume_from":"<bytes or null>","updated_at":"<ISO8601>"}
```

**Immediate return + parallel** — after dispatch the agent does NOT wait; it proceeds to other phases. Multiple independent downloads may each get their own nohup job (different `{name}`), running in parallel. Results are reconciled at Phase 10 (`/result-to-claim`) — if a needed dataset is still `running`, the toy may proceed on whatever partial data is on disk at reduced `scale_ratio` + a WARN; if `failed`, bounded 1 retry then WARN + `source_status: unavailable`.

**Download registry** — every completed download is logged in `experiments/.downloads.json` (array): `{name, source, url, sha256, size_bytes, downloaded_at, via_proxy, method:"foreground|nohup"}`. Phase 15 (`/citation-audit`) reads this to verify dataset provenance for any data figure / numeric claim that depends on it.

## Integration with Auto-Pipeline

The orchestrator integrates background dispatch as follows:

```
Phase 6b: /experiment-execution --stage=toy
    │  → foreground, fast (< 5 min)
    │  → gate check: PASS or FAIL
    │
    │  if PASS:
    ▼
Phase 6c: /experiment-execution --stage=full --background
    │  → dispatch to background
    │  → return immediately to orchestrator
    │  → orchestrator continues Phase 7, 8, 9...
    │
Phase 7-11: (run normally, experiment still in background)
    │
Phase 10: /result-to-claim
    │  → check STATUS.json
    │  → if completed: use full results
    │  → if still running: use toy results + note "full experiment pending"
    │  → if failed: use toy results + recovery attempt
    │
Phase 16: 最终组装
    │  → final check on background experiment
    │  → include full results if available
    │  → archive experiment metadata regardless
```

## Boundaries

- **Never block foreground on > 5 minute tasks.** This is non-negotiable.
- **The dispatch metadata file is mandatory.** Every background job must produce a `DISPATCH.json` with session name, PID, log path, monitor command, and kill command.
- **STATUS.json is the job's responsibility.** The experiment script must write it. If the script doesn't write STATUS.json, the orchestrator has no way to check progress.
- **The orchestrator does not busy-wait.** It continues with other phases and checks results at the appropriate gate phase.
- **Background jobs survive session termination.** tmux/nohup/systemd all survive if the agent session ends. The human can check results later.

## See Also

- [`../support/experiment-execution/SKILL.md`](../support/experiment-execution/SKILL.md) — primary consumer of this protocol
- [`../support/paper-compile/SKILL.md`](../support/paper-compile/SKILL.md) — may use background dispatch for long compilations
- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — orchestrator integration
