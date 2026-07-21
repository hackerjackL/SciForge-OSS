# Pipeline Adaptive Degradation (SciForge-OSS — signature-driven auto-degrade)

> **Status (v2.8 — mid-term M3)**: Defines how the orchestrator **automatically** downgrades phase mode (MUST→CONDITIONAL→OPTIONAL→SKIP) based on the `evidence_type` + `reasoning_paradigm` + `theory_only` flag in `refine-logs/domain-signature.json` (Phase 1b). Replaces v2.7's **hardcoded** Phase Mode Table (20 rows of manually-assigned MUST/OPTIONAL/CONDITIONAL) with a **signature-driven** degradation matrix. The orchestrator now reads the signature at pipeline start and computes the per-phase mode table at runtime — no human pre-assignment.
>
> **Core principle**: The pipeline structure (20-phase order, fallback contract, 3-round cap) is invariant; only the **mode per phase** adapts. v2.7 asked the human to pre-mark which phases are OPTIONAL; v2.8 asks the signature. This is the third leg of the v2.8 adaptive trio: [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) adapts **intensity**, this file adapts **mode**, [`confidence-uplift.md`](confidence-uplift.md) adapts **verdict ceiling**.

## Quick Reference

- **Purpose**: phase mode (MUST/CONDITIONAL/OPTIONAL/SKIP) 从签名自动算出，替代 v2.7 固定 Phase Mode Table
- **Input**: refine-logs/domain-signature.json (`evidence_type`, `reasoning_paradigm`, `theory_only`) from Phase 1b
- **Output**: refine-logs/pipeline-mode-override.json (runtime-computed 20-row mode table, replaces v2.7 static table)
- **Invocation**: orchestrator reads signature at Phase 0 (after INV-G1 freeze) and emits the override BEFORE Phase 1
- **Key**: 降级永不能触碰 INV-G1 / 人类审批门控 / 3 轮回退上限——这些是 invariants 不是 modes

## Degradation Matrix (locked)

For each `(phase, evidence_type, paradigm, theory_only)` combination, the matrix returns one of: `MUST` / `CONDITIONAL` / `OPTIONAL` / `SKIP`. The matrix below is the **complete** v2.8 rule set — the orchestrator looks up this matrix, never invents modes.

### Theory-only problems (theory_only = true)

| Phase | v2.7 mode | v2.8 adaptive mode | Rationale |
|-------|-----------|--------------------|-----------|
| 0 加载问题 | MUST | MUST (invariant) | INV-G1 freeze — never degrades |
| 1 问题理解 | MUST | MUST | decomposition always required |
| 1a domain-signature | OPTIONAL | OPTIONAL | already optional per S1 |
| 1b domain-learner | MUST | MUST | sole signature source per S1 |
| 2 idea-discovery | MUST | MUST | idea generation always required |
| 2.5 adversarial-falsification | MUST | MUST | falsification gate always required |
| 3 novelty-check | MUST | MUST | DAG gate always required |
| 4 universal-retrieval | MUST | **CONDITIONAL** (degrade) | theory-only may have minimal literature; WARN if retrieval < 5 papers but continue |
| 5 method-registry | MUST | MUST (intensity REDUCED via M1) | hash-lock + human checkpoint invariant; intensity adapts via M1 not mode |
| 6 theory-derivation | MUST | MUST | core phase for theory-only |
| 7 leakage-audit | MUST | MUST | Type IV auto NOT_APPLICABLE for theory-only (existing behavior) |
| 8 logic-verification | MUST | MUST | core phase for theory-only |
| 9 invariant-check | MUST | MUST (invariant) | INV-G1 — never degrades |
| 10 result-to-claim | MUST | MUST | TDAL emission always required; theory-only caps D at 0.5 per contract |
| 11 unified-plotting | OPTIONAL | **SKIP** (degrade) | theory-only math rarely needs figures; if proof-structure diagram wanted, human re-enables |
| 12 paper-writing | MUST | MUST | output phase always required |
| 13 paper-compile | CONDITIONAL | CONDITIONAL | existing behavior preserved |
| 14 auto-review-loop | OPTIONAL | OPTIONAL | existing behavior preserved |
| 15 citation-audit | MUST | MUST | anti-hallucination invariant |
| 16 最终组装 | MUST | MUST | archival always required |

**Theory-only net effect**: Phase 4 degrades MUST→CONDITIONAL (lighter literature burden); Phase 11 degrades OPTIONAL→SKIP (no quantitative figures). All other phases keep v2.7 mode. Theory-only problems run **18 active phases** (vs 20 for full empirical).

### Empirical problems with `data_relevant = true` (theory_only = false)

| Phase | v2.7 mode | v2.8 adaptive mode | Rationale |
|-------|-----------|--------------------|-----------|
| 0–3, 5–10, 12, 15, 16 | MUST | MUST (invariant) | core pipeline — never degrades |
| 1a domain-signature | OPTIONAL | OPTIONAL | per S1 |
| 1b domain-learner | MUST | MUST | per S1 |
| 4 universal-retrieval | MUST | MUST | empirical problems need literature |
| 11 unified-plotting | OPTIONAL | **CONDITIONAL** (intensify) | empirical primary outcomes need Layer 2 heatmap; degrade to OPTIONAL only if no quantitative result |
| 13 paper-compile | CONDITIONAL | CONDITIONAL | preserved |
| 14 auto-review-loop | OPTIONAL | OPTIONAL | preserved |

**Empirical net effect**: Phase 11 intensifies OPTIONAL→CONDITIONAL (figures expected, not optional). All other phases keep v2.7 mode. Empirical problems run **20 active phases**.

### Interpretive problems (paradigm = interpretive)

| Phase | v2.7 mode | v2.8 adaptive mode | Rationale |
|-------|-----------|--------------------|-----------|
| 4 universal-retrieval | MUST | MUST | interpretive needs textual corpus |
| 6 theory-derivation | MUST | MUST (mode REPLACED via M1) | per M1: interpretive_mode replaces SymPy; mode stays MUST, engine changes |
| 7 leakage-audit | MUST | MUST | Type I still applies; Type IV auto NOT_APPLICABLE |
| 11 unified-plotting | OPTIONAL | **CONDITIONAL** (mode REPLACED via M1) | per M1: concept-map_mode; degrade to OPTIONAL only if no argument structure to visualize |
| All others | (per theory_only row above) | (same) | interpretive inherits theory_only=false row for non-paradigm-specific phases |

**Interpretive net effect**: Phase 6 and 11 mode stay active but engine/intensity REPLACED via M1. Interpretive problems run **20 active phases** with replaced Phase 6/11 semantics.

### Mixed evidence_type problems (signature has >1 evidence_type)

Apply the **most stringent** mode across the mix for each phase:
- If ANY evidence_type in the mix marks the phase MUST → MUST
- If ALL evidence_types mark the phase SKIP → SKIP
- Otherwise → the most stringent non-MUST mode (CONDITIONAL > OPTIONAL)

**Rationale**: mixed-domain problems (e.g., computational biology = derivational + experimental) must not under-verify either side. Phase 11 for computational biology: derivational says SKIP, experimental says CONDITIONAL → CONDITIONAL wins (figures expected for the experimental side).

## Override Schema (machine-readable)

`refine-logs/pipeline-mode-override.json` (emitted at Phase 0 after INV-G1 freeze, BEFORE Phase 1):

```json
{
  "mode_override": {
    "schema_version": "1.0",
    "computed_at": "ISO-8601",
    "source_signature": "refine-logs/domain-signature.json",
    "evidence_type": "experimental",
    "reasoning_paradigm": "empirical",
    "theory_only": false,
    "mixed_evidence_types": null,
    "active_phase_count": 20,
    "phase_modes": {
      "0": {"mode": "MUST", "source": "invariant"},
      "1": {"mode": "MUST", "source": "invariant"},
      "1a": {"mode": "OPTIONAL", "source": "S1"},
      "1b": {"mode": "MUST", "source": "S1"},
      "2": {"mode": "MUST", "source": "invariant"},
      "2.5": {"mode": "MUST", "source": "invariant"},
      "3": {"mode": "MUST", "source": "invariant"},
      "4": {"mode": "MUST", "source": "empirical_row"},
      "5": {"mode": "MUST", "source": "invariant", "intensity": "INTENSIFIED", "intensity_source": "M1"},
      "6": {"mode": "MUST", "source": "invariant", "intensity": "REDUCED", "intensity_source": "M1"},
      "7": {"mode": "MUST", "source": "invariant"},
      "8": {"mode": "MUST", "source": "invariant"},
      "9": {"mode": "MUST", "source": "invariant"},
      "10": {"mode": "MUST", "source": "invariant"},
      "11": {"mode": "CONDITIONAL", "source": "empirical_row_intensified", "intensity": "STANDARD", "intensity_source": "M1"},
      "12": {"mode": "MUST", "source": "invariant"},
      "13": {"mode": "CONDITIONAL", "source": "v27_preserved"},
      "14": {"mode": "OPTIONAL", "source": "v27_preserved"},
      "15": {"mode": "MUST", "source": "invariant"},
      "16": {"mode": "MUST", "source": "invariant"}
    },
    "degradation_notes": [
      "Phase 11 intensifyed OPTIONAL→CONDITIONAL: empirical primary outcomes need Layer 2 heatmap",
      "Phase 5/6 intensity from M1 adaptive-pipeline; mode stays MUST (invariants)"
    ]
  }
}
```

**Field semantics**:
- `mode`: the v2.8 adaptive mode (MUST / CONDITIONAL / OPTIONAL / SKIP)
- `source`: why this mode — `invariant` (non-degradable), `S1` (learner-first), `v27_preserved` (unchanged from v2.7), `<row_name>` (from this matrix)
- `intensity` / `intensity_source`: cross-referenced from [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) M1 — mode and intensity are orthogonal adaptations
- `active_phase_count`: sanity check — 18 for theory-only, 20 for empirical/interpretive

## Degradation Rules (v2.8 — replaces v2.7 § Degradation Rules)

The v2.7 manual rules (1–6) are now signature-driven:

| v2.7 rule | v2.8 replacement |
|-----------|------------------|
| 1. OPTIONAL phase fails → WARN + skip | Preserved (operational behavior unchanged); the phase is **marked** OPTIONAL by this matrix, not by human |
| 2. MUST phase fails 3 rounds → BLOCKED | Preserved (invariant); MUST assignment is now signature-driven but the 3-round cap is universal |
| 3. CONDITIONAL phase → check condition | Preserved; condition lookup now comes from this matrix's `source` field, not human pre-assignment |
| 4. paper-compile WARN → user accept | Preserved (invariant — paper-compile is special) |
| 5. auto-review-loop OPTIONAL → grounding skip | Preserved; auto-review-loop stays OPTIONAL across all signatures |
| 6. unified-plotting OPTIONAL → no figures skip | Now **signature-driven**: Phase 11 is SKIP for theory-only, CONDITIONAL for empirical, REPLACED for interpretive — the human no longer decides |

**New v2.8 rules** (additions):

| Rule | Behavior |
|------|----------|
| 7. **SKIP phase** → do NOT invoke the skill at all; log `"phase_skipped_per_signature"` in PIPELINE_STATUS.md with the signature evidence_type that justified the skip. SKIP is distinct from OPTIONAL (which invokes but tolerates failure) — SKIP does not invoke. |
| 8. **Invariant phases never degrade** — Phase 0/9 (INV-G1), Phase 5 human checkpoint, Phase 15 citation-audit, Phase 2.5 falsification, Phase 3 DAG gate — these stay MUST regardless of signature. The matrix marks them `source: "invariant"` and the orchestrator MUST refuse to downgrade them even on user override. |
| 9. **Signature absent fallback** — if `domain-signature.json` missing (Phase 1b failed), use v2.7 default modes (all MUST except 1a/11/13/14 OPTIONAL/CONDITIONAL) + WARN `signature_absent_default_modes`. TDAL A dimension flags `missing_inputs: ["domain_learner"]` per contract. |
| 10. **User override trumps signature** — `—mode:11=SKIP` user flag overrides the matrix; logged with `source: "user_override"` in `pipeline-mode-override.json`. But user override CANNOT upgrade an invariant phase (Phase 0/9/etc.) — the orchestrator refuses and surfaces `"phase <N> is invariant, cannot be user-overridden"`. |

## Fallback / Edge Cases

| Condition | Action |
|-----------|--------|
| `domain-signature.json` absent | Use v2.7 defaults; WARN `signature_absent_default_modes`; TDAL A flags missing |
| `evidence_type` unknown (novel domain) | Use v2.7 defaults (all MUST except v2.7-OPTIONAL); WARN `unknown_evidence_type_default_modes`; flag for community contribution (see [`domain-contribution-protocol.md`](domain-contribution-protocol.md)) |
| `reasoning_paradigm` missing | Infer from evidence_type: derivational→formal; correlational/causal/experimental/simulational→empirical; interpretive→interpretive; design→empirical (design problems use empirical row by default) |
| `theory_only` missing | Infer: if evidence_type = derivational AND no data_relevant signal → theory_only=true; otherwise false |
| User overrides invariant phase | Refuse; surface `"phase <N> is invariant"` error; do NOT apply the override |
| Signature and M1 intensity conflict | They are orthogonal — mode from this matrix, intensity from M1; both apply. E.g., Phase 6 mode=MUST + intensity=REDUCED means the phase runs but with reduced sections. |

## Boundaries

- **Mode degradation is orthogonal to intensity adaptation.** This file (M3) sets MUST/CONDITIONAL/OPTIONAL/SKIP; [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) (M1) sets REDUCED/STANDARD/INTENSIFIED. A phase can be MUST+REDUCED (must run, fewer sections) or OPTIONAL+INTENSIFIED (optional but if invoked, intensified). The orchestrator applies both overrides independently.
- **SKIP ≠ OPTIONAL.** OPTIONAL invokes the skill and tolerates failure; SKIP does NOT invoke the skill at all. Only Phase 11 can be SKIP (theory-only); all other phases最低 OPTIONAL.
- **Invariant phases never degrade.** Phase 0/9 (INV-G1), Phase 5 (hash-lock + human checkpoint), Phase 2.5 (falsification gate), Phase 3 (DAG gate), Phase 15 (citation-audit) — these are marked `source: "invariant"` and the orchestrator MUST refuse downgrade even on user override. The invariant list is the non-degradable backbone.
- **The 3-round fallback cap is universal.** Mode degradation does NOT add retry rounds — INTENSIFIED mode has more sections but the same 3-round cap. The anti-deadloop ladder is invariant.
- **The override is auditable.** `pipeline-mode-override.json` is a required artifact emitted at Phase 0; Phase 14 (`/auto-review-loop`) reads it to check whether the mode choices were justified by the signature.
- **Mixed-domain problems take the most stringent mode.** Computational biology (derivational+experimental) gets Phase 11 CONDITIONAL (not SKIP) — the experimental side's figures must appear. Under-verifying either side is the failure mode the stringent-rule prevents.

## Why this is not "hardcoded phase table"

v2.7's Phase Mode Table is 20 rows of human-assigned modes — adding a 21st phase or a new discipline requires editing the orchestrator. v2.8's degradation matrix is:

1. **Signature-driven** — the modes are computed at runtime from the learner's signature, not pre-assigned.
2. **Small finite alphabet** — 3 signature axes (evidence_type × paradigm × theory_only) → 3 row templates (theory-only / empirical / interpretive) covering all scientific domains.
3. **Unknown evidence_type default** — novel domains do not break the pipeline; they fall back to v2.7 defaults and flag for community contribution.
4. **Invariants are explicit** — the matrix marks `source: "invariant"` on non-degradable phases, making the backbone auditable rather than implicit.

Adding a new discipline that fits an existing signature (e.g., a new empirical subfield) requires ZERO orchestrator changes — the matrix already covers it. Adding a genuinely new evidence_type (e.g., a yet-undreamed research paradigm) requires adding ONE row to this matrix — not a new pipeline.

## See Also

- [`../orchestrator/125-problems-pipeline/SKILL.md`](../orchestrator/125-problems-pipeline/SKILL.md) — the 20-phase pipeline (this file replaces the v2.7 static Phase Mode Table)
- [`domain-adaptive-pipeline.md`](domain-adaptive-pipeline.md) — M1 intensity adaptation (orthogonal to this M3 mode adaptation)
- [`confidence-uplift.md`](confidence-uplift.md) — M2 verdict uplift (orthogonal to mode/intensity)
- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL schema (signature-absent fallback flags A dimension)
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — how Phase 1b's signature is consumed (this file is a consumer)
- [`domain-contribution-protocol.md`](domain-contribution-protocol.md) — unknown evidence_type community contribution channel (long-term L1)
