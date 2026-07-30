# Background Dispatch Protocol

> **Status (v2.0)**: Protocol for dispatching long-running tasks (experiments, compilations, simulations) to background execution. Prevents front-end timeouts in Claude Code, Codex, Cursor, and other AI development tools.
>
> **Core principle**: The agent must NEVER block the foreground on a task whose wall-clock time may exceed the tool's session timeout. Dispatch to background, continue pipeline, check results later.

## When to Background-Dispatch

| Condition | Action |
|-----------|--------|
| Estimated wall-clock > 5 minutes | **MUST** background-dispatch |
| Estimated wall-clock 2-5 minutes | SHOULD background-dispatch (agent discretion) |
| Estimated wall-clock < 2 minutes | Run in foreground |
| Task is idempotent and resumable | Background-dispatch preferred |
| Task produces critical gating artifact | Run in foreground if < 5 min; background + poll otherwise |

**Hard rule**: Any full-scale experiment, any multi-hour simulation, any GPU training run — these MUST be background-dispatched. The agent must not `subprocess.run()` with a 4-hour timeout and block the session.

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
