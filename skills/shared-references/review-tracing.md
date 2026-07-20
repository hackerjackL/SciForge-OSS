# Review Tracing Protocol

## Purpose

Save full prompt/response pairs for every cross-model reviewer call, enabling:
- **Reviewer-independence audit**: verify the executor only passed file paths, not summaries
- **Reproducibility**: conversation thread preservation allows review continuation
- **Meta-optimize input**: richer data for harness improvement analysis

## When to Trace

After **every** reviewer call that serves a reviewer/critique function. This includes review scoring, experiment auditing, claim verification, idea critique, and patch gating.

Do NOT trace: purely informational LLM calls that are not reviews (e.g., code generation that is not a critique).

## Trace Directory

Each review run produces a trace directory under a project-local trace store:

```
<trace-root>/<skill-name>/<YYYY-MM-DD>_run<NN>/
  ├── run.meta.json                      # Run-level metadata
  ├── 001-<purpose>.request.json         # Request snapshot
  ├── 001-<purpose>.response.md          # Full response text
  ├── 001-<purpose>.meta.json            # Response metadata
  ├── 002-<purpose>.request.json         # Second call (e.g., reply)
  └── ...
```

- `<skill-name>`: the SciForge skill that triggered this call (e.g., `auto-review-loop`)
- `<YYYY-MM-DD>_run<NN>`: date + sequential run number (start from `01`)
- `<purpose>`: short kebab-case label (e.g., `round-1-review`, `critique`, `ideation`, `audit`, `patch-gate`)

## How to Trace

After each reviewer call, save the trace by writing the four files
below into the run directory. The trace is forensic evidence — a
missing trace-writing helper never means "skip the trace." If a
trace-writing helper is available it may handle directory creation,
run numbering, and file writing; if not, write the files directly per
the schemas below.

Concretely, after each reviewer call:

1. Determine the skill name, purpose label, model, and conversation
   thread identifier from the response.
2. Locate or create the run directory under
   `<trace-root>/<skill-name>/<YYYY-MM-DD>_run<NN>/`, incrementing the
   run number if a run for the same date already exists.
3. Write `run.meta.json` once per run.
4. For each reviewer call in the run, write the three per-call files:
   `<NNN>-<purpose>.request.json`, `<NNN>-<purpose>.response.md`,
   `<NNN>-<purpose>.meta.json`, incrementing `<NNN>` per call.
5. If tracing was explicitly disabled for this invocation (see
   Configuration), skip writing — but never skip silently because the
   helper is missing. `trace_path` is load-bearing for any mandatory
   audit emitting it in its artifact (see `assurance-contract.md`).

## File Schemas

### `run.meta.json`
```json
{
  "skill": "auto-review-loop",
  "run_id": "2026-04-15_run01",
  "started_at": "2026-04-15T14:30:00+08:00",
  "executor": "host-agent",
  "project_dir": "/path/to/project"
}
```

### `NNN-<purpose>.request.json`
```json
{
  "call_number": 1,
  "purpose": "round-1-review",
  "timestamp": "2026-04-15T14:31:00+08:00",
  "tool": "reviewer",
  "model": "gpt-5.5",
  "config": {"model_reasoning_effort": "xhigh"},
  "files_referenced": ["paper/sections/3_method.tex", "results/table1.csv"],
  "prompt": "<full prompt text>"
}
```

### `NNN-<purpose>.response.md`
The reviewer's full response, verbatim. No truncation, no summarization.

### `NNN-<purpose>.meta.json`
```json
{
  "call_number": 1,
  "purpose": "round-1-review",
  "timestamp": "2026-04-15T14:33:00+08:00",
  "thread_id": "019d8fe0-b25d-...",
  "model": "gpt-5.5",
  "duration_ms": 142000,
  "status": "ok"
}
```

## Configuration

Tracing respects three modes, set via a trace mode parameter:
- **`full`** (default): save full prompt + full response
- **`meta`**: save metadata only (no prompt/response text), useful for sensitive projects
- **`off`**: disable tracing entirely

## Integration with Event Log

After writing a trace, append a compact summary event to the project's
event log so meta-analysis skills can discover traces without reading
the full trace files:

```json
{"event":"review_trace","skill":"auto-review-loop","purpose":"round-1-review","thread_id":"...","trace_path":"<trace-root>/auto-review-loop/2026-04-15_run01/","status":"ok"}
```

## Privacy

- The trace store should be in `.gitignore` — traces are project-local, never committed.
- Traces may contain sensitive research content; treat them as confidential.
- Use trace mode `off` for projects with strict confidentiality requirements.
