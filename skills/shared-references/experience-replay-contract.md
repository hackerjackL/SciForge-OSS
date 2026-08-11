# Experience-Replay Contract (SciForge-OSS — "gets smarter with use", v1.4.0)

> **Why this exists**: a single run that dies or fails should make the NEXT run
> better, not repeat the same mistake. Inspired by skill-library / reinforced
> self-improvement work (RL-for-self-improving-agents, self-evolving agents) and
> by CRUX (arXiv:2607.27191) failure-mode #1 (agents don't learn what good work
> looks like). This contract turns every run's failures AND successes into a
> structured, replayable prior — **inside the single serial pipeline** (never a
> parallel side-system).

## 1. The artifact: `LESSONS.json`

Written at **Phase 16** (final assembly) next to `output/RUN_PREPRINT.md`, and
mirrored into the cross-run archive (sibling workspaces) so later runs can read it.
Machine-readable; narrative detail stays in the referenced artifacts.

```json
{
  "schema_version": "1.0",
  "run_id": "Q042",
  "discipline": "general",
  "failed_experiments": [
    {"id": "exp-full-seed3", "what": "full matrix seed 3 diverged",
     "root_cause": "lr too high for stiff regime", "evidence": "experiments/full/group_a/RESULT.json",
     "lesson": "stiff regime needs lr<=1e-3; sweep lr first", "avoid": "do not reuse lr=1e-2 here"}
  ],
  "idea_rollbacks": [
    {"idea": "I7", "why_killed": "falsified by counterexample (Phase 2.5)",
     "evidence": ".sciforge/verdicts/KILL_ARGUMENT.json", "lesson": "assumption A3 untenable"}
  ],
  "code_errors": [
    {"file": "src/experiments/run.py", "error": "overflow in enthalpy term",
     "fix": "cast to float64", "lesson": "use float64 for enthalpy accumulators"}
  ],
  "what_worked": [
    {"what": "overflow-enthalpy reduced model", "evidence": "CLAIMS_FROM_RESULTS.md",
     "reuse": "strong baseline for any open-vessel thermal problem"}
  ]
}
```

## 2. Producer (Phase 16) and consumers (Phase 2 / 6b) — serial

- **Phase 16** (`/auto-pipeline`): after `RUN_PREPRINT.md`, aggregate the run's
  KILL_ARGUMENT.json / BUDGET_FLOOR.json / RESULT.json / compile+audit FAILs into
  `LESSONS.json`. Missing categories → empty arrays (never omit the key).
- **Phase 2** (`/idea-discovery`): before scoring, read sibling workspaces'
  `LESSONS.json` (`idea_rollbacks` + `what_worked`) as a prior: down-weight ideas
  matching a killed pattern, seed from `what_worked`. This is the AgentRxiv/RUN_PREPRINT
  mechanism extended from gaps to lessons.
- **Phase 6b** (`/experiment-execution`): before designing the toy/full matrix, read
  `failed_experiments` + `code_errors` to avoid repeating a known-bad configuration
  (the `avoid` fields are hard exclusions unless the human overrides).

All reads/writes are part of the existing DAG order — **no parallel pipeline**, no
new orchestrator. A run with no prior lessons simply proceeds with empty priors.

## 3. Failure routing (with [`result-to-claim` negative-discipline] and CRUX)

- A failed experiment / killed idea / code error is **never a contribution** (it goes
  to `LESSONS.json` + Limitations, per the negative-result discipline).
- It is **never silently dropped**: every FAIL that triggered a fallback/KILL must
  appear in exactly one `LESSONS.json` category with a `lesson` + `evidence` pointer.
- This is the structural answer to CRUX "engineering-perfect, science-zero": the
  pipeline accumulates judgment (what fails and why) across runs, not just artifacts.

## 4. Hygiene

- `LESSONS.json` lives in `.sciforge/` (hidden state) AND is mirrored to the visible
  cross-run archive as `output/LESSONS.json` so sibling runs can read it without
  opening another run's hidden dir.
- Lessons are advisory priors, not hard rules: a human or a stronger contrary
  evidence can override, and the override is recorded (`override_reason`).

## 5. Retrieval-augmented lessons + policy update (v1.5.0 — RL-grade, still serial)

- **Vector lessons store**: embed each `LESSONS.json` entry (lesson + context) into a local
  index (`chromadb`/`faiss`, optional deps) so Phase 2/6b retrieve *similar* past runs'
  lessons (not just sibling files) as priors. Falls back to sibling-file scan when absent.
- **Per-run policy update**: after each run, record which fix-types actually moved a verdict
  (e.g. "adding parallel-trends probe turned WARN→PASS"); weight future probe selection by
  these outcomes. This is the "gets smarter with use" loop — experience replay + simple
  credit assignment, no gradient, no parallel system.
