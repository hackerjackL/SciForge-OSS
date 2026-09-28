---
name: experiment-ladder
description: "ScientistTwo §3.2 subset→full-set experiment ladder with the 3-state Critic {BAD|GOOD|ENGINEER≤2}. Companion to /experiment-execution at phases 6b/6c: reproduce the baseline on the subset, run the candidate, decide the critic state, promote only on strict full-set improvement. Writes .sciforge/audits/S2_LADDER.json (kernel gate s2_ladder at the 6c boundary)."
type: support-skill
role: experiment-ladder-critic
version: 1.7.1
---

# Experiment Ladder (SciForge-OSS — Subset→Full-Set + 3-state Critic)

> **Status (v1.7.0)**: ScientistTwo parity layer. The knowledge/protocol source
> is [`s2-protocol.md`](../../shared-references/s2-protocol.md); the enforcing
> code is `kernel/sciforge/s2/ladder.py` + `scripts/s2_ladder_gate.py`. This
> skill tells the HOST how to produce the artifact the gate demands — the gate
> is the contract, this file is the recipe.

## Quick Reference

- **Purpose**: stop subset flukes from becoming claims — a candidate is promoted
  to the full set only after the Critic says GOOD, and crosses the 6c boundary
  only after strict full-set improvement over the *reproduced* baseline.
- **Input**: `experiments/subset/**` (baseline + candidate runs), `experiments/full/**`
- **Output**: `.sciforge/audits/S2_LADDER.json` (machine, gate-checked)
- **Gate**: phase 6c `s2_ladder` — missing/invalid ladder ⇒ boundary rejected
- **Caps**: ENGINEER rounds ≤ 2 (`ladder.MAX_ENGINEER_ROUNDS`); ties never count as wins

## Use When

- phase 6b/6c experiment work needs the ladder discipline (experiment-first /
  hybrid routes);
- a reviewer or the orchestrator asks "was the baseline reproduced first?";
- `scripts/s2_ladder_gate.py <ws>` reports FAIL.

## Job

1. **Reproduce the incumbent on the subset** (`experiments/subset/baseline/`):
   same metric, same protocol, seeds recorded. No reproduction = no ladder.
2. **Run the candidate on the subset** (`experiments/subset/candidate/`).
3. **Decide the Critic state** with the production function (do not eyeball):
   ```python
   import sys; sys.path.insert(0, "<repo>/kernel")
   from sciforge.s2.ladder import decide, relative_gain
   state = decide(baseline_value, candidate_value, direction="maximize")
   # GOOD: strictly better | ENGINEER: tie/below-margin | BAD: worse
   ```
4. **ENGINEER**: tune (≤2 rounds total), rerun subset, decide again.
   Exhaustion ⇒ stop and surface (loopback per L5/L7) — never force GOOD.
5. **GOOD ⇒ run the FULL set** for both arms with identical protocol.
6. **Write `.sciforge/audits/S2_LADDER.json`** exactly as below, then self-check:
   ```bash
   python3 scripts/s2_ladder_gate.py <workspace>   # must exit 0
   ```

## Output Shape

```jsonc
{
  "schema_version": "1.0",
  "problem_id": "<Q-id — INV-G1 anchor>",
  "metric": {"name": "accuracy", "direction": "maximize"},   // or minimize
  "subset":  {"n": 160, "baseline": {"value": 0.36}, "candidate": {"value": 1.0}},
  "critic":  {"state": "GOOD", "engineer_rounds": 0, "rationale": "subset GOOD + full-set strictly better"},
  "fullset": {"n": 600, "verified": true,
              "baseline": {"value": 0.36}, "candidate": {"value": 1.0}},
  "relative_gain_pct": 177.78          // direction-aware; must equal recomputation
}
```

## Boundaries

- Never edit `relative_gain_pct` by hand — recompute with `ladder.relative_gain`.
- Never mark `verified:true` without both full-set numbers present.
- BAD/ENGINEER candidates do not cross 6c; the gate rejects the state itself.
- Theory-only route never reaches this skill (6c is `skip_on_route: theory-only`).
- Do not duplicate the critic logic in prose — call `s2.ladder.decide`.
