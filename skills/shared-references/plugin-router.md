# Plugin Router (SciForge-OSS — advisory plugin consultation, non-binding)

> **Status (v2.8 — backfilled missing contract)**: Defines the **advisory plugin consultation layer** for optional, non-binding plugin consultation. Backfilled in v2.8 because [`artifact-registry.md`](artifact-registry.md) referenced this file but it was missing from OSS inheritance — a historical gap.
>
> **Core principle**: Plugins are advisory only. They NEVER produce registered artifacts, NEVER trigger INV-X checks, NEVER alter pipeline semantics. Removing the entire `research-plugins/` directory from the filesystem MUST NOT break any registered artifact's producer/consumer contract. Plugins enhance; they do not gate.

## Quick Reference

- **Purpose**: 锁定 advisory plugin 堨议层契约——可选、非 binding、永不 gate pipeline
- **Producer**: plugin authors (community or core team)
- **Consumer**: any skill MAY consult a plugin for advisory input; NO skill MUST
- **Output**: advisory suggestions (never registered artifacts)
- **Key**: removing research-plugins/ MUST NOT break any registered contract

## What Plugins Are

Plugins are optional modules under `research-plugins/` that provide advisory consultation:

- **Additional literature databases**: e.g., a plugin exposing a domain-specific literature index beyond the default 6 sources in `/universal-retrieval`
- **Dataviz guides**: e.g., a plugin providing domain-specific figure templates beyond `/unified-plotting`'s defaults
- **Domain knowledge**: e.g., a plugin providing domain-specific background knowledge beyond what `/domain-learner` extracts from literature

**Plugins are NOT**: producers of registered artifacts (see [`artifact-registry.md`](artifact-registry.md) for the load-bearing artifact list), verifiers (they cannot emit PASS/FAIL verdicts), or gates (they cannot block the pipeline).

## Non-Binding Contract

```
1. Plugin output is advisory only.
   → A skill MAY consult a plugin's suggestion; it is NOT required to follow it.
   → A skill that ignores all plugin output MUST still produce correct, complete artifacts.

2. Plugin output NEVER produces registered artifacts.
   → If a plugin suggests a citation, the citation is NOT added to CITATION_AUDIT.json unless /citation-audit verifies it.
   → If a plugin suggests a figure, the figure is NOT added to figures/ unless /unified-plotting renders and validates it.

3. Plugin output NEVER triggers INV-X checks.
   → INV-G1 (problem anchor freeze), INV-G2 (artifact hash), etc. are triggered by registered producers only.
   → A plugin cannot mint a Q-id, cannot freeze an assumption, cannot lock a method hash.

4. Plugin output NEVER alters pipeline semantics.
   → A plugin cannot change phase order, cannot downgrade a MUST phase, cannot waive a human checkpoint.
   → Pipeline semantics are owned by the orchestrator and the adaptive matrices (see [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md), [`pipeline-adaptive-degradation.md`](pipeline-adaptive-degradation.md)).

5. Removing research-plugins/ MUST NOT break any registered contract.
   → Every skill's SKILL.md MUST be written so that the skill works correctly with research-plugins/ absent.
   → Plugin consultation is wrapped in "if plugin exists, consult; else proceed without" — never "if plugin missing, BLOCK".
```

## Plugin Discovery

Skills consult plugins via a capability-based discovery, NOT a hardcoded plugin list:

```
Step 1: Skill declares an advisory capability it would like (e.g., "domain-specific literature index")
Step 2: Skill scans research-plugins/ for any plugin providing that capability
        → plugin manifest declares capabilities (e.g., "provides: literature_index, domain: synthetic_biology")
Step 3: If a matching plugin exists: skill consults it, receives advisory suggestions
Step 4: If no matching plugin exists: skill proceeds with default behavior (no advisory, no BLOCK)
```

**No hardcoded plugin names**: skills declare capabilities, not plugin names. This lets plugins be added/removed without editing skills.

## Plugin Manifest Schema

Each plugin under `research-plugins/<plugin_name>/` MUST have a `PLUGIN.md` manifest:

```json
{
  "plugin_manifest": {
    "schema_version": "1.0",
    "plugin_name": "synbio_literature_index",
    "provides": ["literature_index"],
    "domain": "synthetic_biology",
    "advisory_only": true,
    " removable_without_break": true,
    "consultation_protocol": "skill sends a literature query; plugin returns advisory paper list (never verified citations)"
  }
}
```

**Fields**:
- `provides`: capabilities the plugin offers (skills match on these, not on plugin_name)
- `advisory_only`: MUST be `true` — if `false`, the module is NOT a plugin, it is a core skill and belongs in `skills/` not `research-plugins/`
- `removable_without_break`: MUST be `true` — asserts the non-binding contract; if `false`, the module is load-bearing and belongs in `skills/`

## Boundaries

- **Plugins are advisory only.** Their output is never binding; skills may ignore it without penalty.
- **Plugins never produce registered artifacts.** Registered artifacts come from core skills only; plugin suggestions must be verified by the corresponding core skill before entering the artifact registry.
- **Plugins never gate the pipeline.** No BLOCK, no MUST, no INV-X trigger — only advisory suggestions.
- **Removing research-plugins/ MUST NOT break any contract.** Every skill works correctly with plugins absent; plugin consultation is wrapped in "if exists" guards, never "if missing, BLOCK".
- **Capabilities, not names.** Skills declare capabilities they want; plugins declare capabilities they provide. Matching is capability-based, not name-based.
- **advisory_only and removable_without_break are mandatory `true`.** A module with either `false` is NOT a plugin — it is a core skill and belongs in `skills/`.

## See Also

- [`artifact-registry.md`](artifact-registry.md) — load-bearing artifacts (plugins NEVER produce these)
- [`integration-contract.md`](integration-contract.md) — cross-skill integration (plugins are NOT integration partners; they are advisory only)
- [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) — pipeline semantics (plugins NEVER alter these)
- [`pipeline-adaptive-degradation.md`](pipeline-adaptive-degradation.md) — phase modes (plugins NEVER change these)
