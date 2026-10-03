---
name: ablation-planner
description: "ScientistTwo §3.4 component ablation: planner emits 5–6 plans, AblCritic decides {GOOD|REFINE} under the strict 'new must strictly beat old' rule, ledger stays monotone. Phase 10 companion (before result-to-claim). Writes .sciforge/audits/ABLATION_LEDGER.json (kernel gate s2_ablation at the phase-10 boundary)."
type: support-skill
role: ablation-planner-critic
version: 1.7.2
---

# Ablation Planner (SciForge-OSS — Component Ablation + AblCritic)

> **Status (v1.7.0)**: ScientistTwo parity layer. Protocol:
> [`s2-protocol.md`](../../shared-references/s2-protocol.md) §3. Enforcing code:
> `kernel/sciforge/s2/ablation.py` + `scripts/s2_ablation_gate.py`. This skill
> produces the artifact; the gate is the contract.

## Quick Reference

- **Purpose**: no claim crosses phase 10 without component-level evidence —
  which part of the method actually earns the result?
- **Input**: `methods/METHOD_REGISTRY.md` (components), `experiments/full/**` (arm results)
- **Output**: `.sciforge/audits/ABLATION_LEDGER.json` (machine, gate-checked)
- **Gate**: phase 10 `s2_ablation` — experiments exist but ledger absent ⇒ FAIL
- **Caps**: **5–6 plans** (`SCIFORGE_ABLATION_MIN/MAX`); AblCritic is mechanical

## Use When

- phase 10 (result-to-claim) preparation on any experiment-backed run;
- `scripts/s2_ablation_gate.py <ws>` reports FAIL;
- the paper is about to attribute gains to a component.

## Job

1. **Enumerate components** from the method registry (features, loss terms,
   regularizers, data augments, scheduler steps — whatever the method claims).
2. **Plan 5–6 ablations**, one component each:
   `{id: "A1", component, hypothesis, metric}` — hypothesis states the expected
   sign ("removing X drops accuracy ≥ …").
3. **Execute each plan** on the full set under the same protocol/budget as the
   main arm; record `prev_value` (state before) and `new_value` (state with the
   ablation applied — normally the ablated variant is *worse*; `new_value` here
   means "the measurement of this plan's state").
4. **Decide with the production critic** (never by feel):
   ```python
   import sys; sys.path.insert(0, "<repo>/kernel")
   from sciforge.s2.ablation import ablcritic
   decision = ablcritic(prev_value, new_value, direction="maximize")  # GOOD | REFINE
   ```
   Strict rule: GOOD **iff** strictly better; ties keep the old state (REFINE).
5. **Maintain `current_best`** = best GOOD outcome — it may only move in the
   improving direction (the gate recomputes and rejects regressions).
6. **Self-check**: `python3 scripts/s2_ablation_gate.py <workspace>` (exit 0).

## Output Shape

```jsonc
{
  "schema_version": "1.0",
  "problem_id": "<Q-id — INV-G1 anchor>",
  "metric": {"name": "accuracy", "direction": "maximize"},
  "plans": [
    {"id": "A1", "component": "fourier_features", "hypothesis": "removing RFF collapses nonlinear separation", "metric": "accuracy", "status": "executed"},
    {"id": "A2", "component": "standardization",  "...": "..."},
    {"id": "A3", "...": "..."}, {"id": "A4", "...": "..."}, {"id": "A5", "...": "..."}
  ],
  "results": [
    {"plan": "A1", "prev_value": 1.0, "new_value": 0.41, "decision": "REFINE", "note": "ablated variant worse — old state kept"}
  ],
  "current_best": 1.0
}
```

## Boundaries

- <5 or >6 plans ⇒ gate FAIL (micro-runs: set `SCIFORGE_ABLATION_MIN` explicitly
  and record it in the run notes; the default is ScientistTwo's 5–6).
- `decision` must equal `ablcritic(prev, new)` — hand-declared GOOD without
  strict improvement is rejected.
- Ablations run on the **full** set with the main arm's protocol (no cheaper
  proxy — proxy ablations are how ablation tables go wrong).
- Negative-result discipline: an ablation that *fails to hurt* is a finding —
  it goes in the paper as "component X is redundant", not silently dropped.
