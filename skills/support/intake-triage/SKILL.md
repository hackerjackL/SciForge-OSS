---
name: intake-triage
description: "Flexible user-intake triage (v1.7.1): the user may hand over ANY combination — a bare question, a draft manuscript, code, data, experiment results, logs, a target venue, formatting demands — and the run adapts instead of refusing. Produces INTAKE_MANIFEST.json (what arrived, what is trusted, which phases are inherited vs re-run) and routes the pipeline accordingly. Phase 0 companion; never gates, only plans."
type: support-skill
role: intake-triage-router
version: 1.7.2
---

# Intake Triage (SciForge-OSS — flexible user-intake router)

> **Status (v1.7.1)**: the pipeline used to assume one intake shape: a fresh
> question. Real users arrive with a draft + code + results + logs + opinions
> ("fix the layout", "run the whole thing", "just polish section 4"). This
> skill makes every arrival shape first-class. **It plans; it never weakens a
> gate** — inherited artifacts still face every mechanical gate at their
> boundary (an inherited RESULT.json still needs the ladder/ablation/parity
> evidence; an inherited draft still faces leakage/claim/DOI gates).

## Quick Reference

- **Input**: whatever the user dropped in the workspace root or `intake/`
- **Output**: `.sciforge/verdicts/INTAKE_MANIFEST.json` + `INTAKE_REPORT.md`
- **Effect**: phase routing hints (which phases are *inherited* vs *re-run*),
  `claim_mode` + `discipline` suggestions, user-request ledger
- **Gate**: none (planning artifact); downstream gates unchanged

## Job

1. **Census** — list what arrived, by class:
   `question | draft_tex | draft_md | code | data | results | logs | figures |
   bibliography | venue_spec | style_demands | other`. Record path + size +
   a one-line content note for each. Never read full drafts into context;
   sample heads/structure.
2. **Trust classification** — per artifact: `machine-verifiable` (results
   JSON, logs with numbers, code) vs `narrative` (draft prose, claims).
   Machine-verifiable artifacts may seed phases 6b/6c/10 **only after** the
   relevant gate re-derives them (ladder re-runs the baseline; parity
   re-checks code↔method; DOI gate re-resolves every reference). Narrative
   artifacts seed phases 12-14 (writing/review) and are rewritten under the
   voice contract — never copied verbatim into the manuscript.
3. **User-request ledger** — every explicit user demand (layout, section
   order, figure style, "make it SOTA", "appendix separate", language) as a
   numbered item with its target phase; the ledger is re-read at phases 11,
   12, 13 so demands cannot be forgotten mid-run.
4. **Routing proposal** — for each of the 21 phases: `inherit` (artifact
   arrives trusted and gate-re-derivable), `re-run`, or `skip` (route-N/A).
   Write it to `INTAKE_MANIFEST.json` as `phase_plan`; the orchestrator
   treats it as advisory (a phase marked inherit still executes its gate).
5. **Mode suggestion** — `claim_mode` (sota when the user demands a win or
   supplies winning results; attribution when the question is a measurement),
   `discipline` (lean for strong hosts on cosmetic-heavy venues, strict for
   submission-grade), and the manuscript tier (short/standard/long).

## Output Shape

```jsonc
{
  "schema_version": "1.0",
  "census": [{"class": "results", "path": "intake/results.json", "trust": "machine-verifiable", "note": "…"}],
  "user_requests": [{"id": "R1", "demand": "appendix as separate PDF", "phase": 13}],
  "phase_plan": {"6b": "inherit", "6c": "re-run", "12": "inherit-rewrite", "…": "…"},
  "suggested": {"claim_mode": "sota", "discipline": "balanced", "tier": "standard"}
}
```

## Boundaries

- Intake never bypasses gates: `inherit` means "start from this artifact",
  not "trust this artifact".
- Wet-lab / clinical / proprietary-GUI-solver intakes are OUT OF SCOPE
  (see SKILL.md scope): refuse with the scope statement, not with a run.
- COMSOL: accepted ONLY as a joint PINN/surrogate target (simulation data as
  input); a "run COMSOL for me" request is refused (external MCP/interface is
  the planned path, not this pipeline).
