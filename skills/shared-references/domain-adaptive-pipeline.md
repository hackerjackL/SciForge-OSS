# Domain Adaptive Pipeline (SciForge-OSS — evidence_type-driven Phase intensity)

> **Status (v2.8 — mid-term M1, v1.0.0 — cross-link to M3)**: Defines how the orchestrator dynamically adjusts **Phase 5 (method-registry) / Phase 6 (theory-derivation) / Phase 11 (unified-plotting)** **intensity** (REDUCED/STANDARD/INTENSIFIED/REPLACED/SKIPPED) based on the `evidence_type` + `reasoning_paradigm` written to `refine-logs/domain-signature.json` by `/domain-learner` (Phase 1b). This file adapts **intensity**; the orthogonal companion [`pipeline-adaptive-degradation.md`](pipeline-adaptive-degradation.md) (M3) adapts **mode** (MUST/CONDITIONAL/OPTIONAL/SKIP). The two files are independent — read either depending on which axis the orchestrator is configuring.
>
> **Core principle**: One universal 20-phase pipeline shape; **intensity** adapts per signature. The pipeline structure (phase order, fallback contract, 3-round cap) is invariant — only the per-phase emphasis, budget, and gate strictness adapt. This avoids both the "hardcoded discipline branch" anti-pattern (main SciForge's 4 parallel pipelines) and the "uniform strength" anti-pattern (v2.7's all-MUST).

## Quick Reference

- **Purpose**: Phase 5/6/11 强度按 evidence_type/paradigm 动态调整，实现真通用而非硬编码分支
- **Input**: refine-logs/domain-signature.json (`evidence_type`, `reasoning_paradigm`) from Phase 1b
- **Output**: per-phase `intensity_override` block written to PIPELINE_STATUS.md before Phase 5 starts
- **Key**: 结构不变（20-phase 顺序锁、3 轮回退、契约都保留），只调强度/emphasis/budget/gate strictness

## Adaptive Override Table (locked)

The orchestrator reads `signature.evidence_type` + `signature.reasoning_paradigm` and applies the override BEFORE launching the phase. Missing fields → default (no override).

### Phase 5 — /method-registry intensity

| evidence_type | paradigm | intensity | emphasis | budget | human checkpoint |
|--------------|----------|-----------|----------|--------|------------------|
| `derivational` (math/proof) | formal | **REDUCED** | hash-lock only; skip experimental design sections | 1 round, ≤ 200 words | YES (still mandatory per INV) — but checkpoint scope narrowed to "is the proof strategy sound?" |
| `correlational` / `causal_inference` | empirical | **STANDARD** | full 8-section registry, identification strategy emphasized | 2 rounds, ≤ 600 words | YES (full scope) |
| `experimental` (medicine/bio) | empirical | **INTENSIFIED** | full registry + preregistration-style protocol spec + sample-size justification | 3 rounds, ≤ 1200 words | YES (full scope + protocol review) |
| `simulational` (physics/climate) | empirical | **STANDARD** | full registry, numerical-method emphasized over identification | 2 rounds, ≤ 600 words | YES |
| `interpretive` (humanities/law) | interpretive | **REDUCED** | argument-structure registry; skip statistical identification sections | 1 round, ≤ 300 words | YES — checkpoint scope: "is the interpretive frame sound?" |

**Intensity meaning**:
- REDUCED = the phase runs but with fewer required sections; non-applicable sections emit `NOT_APPLICABLE` instead of FAIL. The hash-lock + human checkpoint are NEVER removed (INV non-negotiable).
- STANDARD = the v2.7 default behavior; full registry.
- INTENSIFIED = additional required sections beyond v2.7 default; stricter gate.

### Phase 6 — /theory-derivation intensity

| evidence_type | paradigm | intensity | engine | verification strictness | output mark |
|--------------|----------|-----------|--------|-------------------------|-------------|
| `derivational` | formal | **INTENSIFIED** | `engine=sympy` mandatory; `engine=manual` ONLY if SymPy fails AND human approves | symbolic required (no qualitative fallback) | `[machine-verified]` or `[not machine-verified — human-approved manual]` |
| `correlational` / `causal_inference` | empirical | **STANDARD** | SymPy for theoretical model + numerical sanity sweep for identification | symbolic for theory; numerical for ID strategy | `[machine-verified]` where SymPy ran |
| `experimental` | empirical | **REDUCED** | `engine=manual` acceptable by default; SymPy optional for theoretical mechanism | qualitative + numerical OK; symbolic NOT required | `[not machine-verified]` acceptable for primary outcome (fidelity gate = numerical) |
| `simulational` | empirical | **STANDARD** | SymPy for equations + numerical sweep for stability/convergence | symbolic for core equations; numerical for regime map | `[machine-verified]` for equations |
| `interpretive` | interpretive | **REPLACED** → textual-analysis | `engine=manual` only; SymPy NOT applicable | argument coherence check replaces symbolic verification | `[interpretive-verified]` |

**Phase 6 REPLACED caveat (interpretive only)**: the orchestrator does NOT skip Phase 6 — it runs `/theory-derivation` in `interpretive_mode` where the "derivation" is argument reconstruction, not SymPy. The phase boundary and fallback contract still apply; the gate logic changes from "symbolic proof complete" to "argument coherent + counter-evidence addressed". See [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) § Interpretive Mode (added v2.8).

### Phase 11 — /unified-plotting intensity

| evidence_type | paradigm | intensity | figure types | color compliance | data heatmap |
|--------------|----------|-----------|--------------|------------------|--------------|
| `derivational` | formal | **SKIPPED** (NOT_APPLICABLE) | — | — | — |
| `correlational` / `causal_inference` | empirical | **STANDARD** | line/scatter/bar/heatmap + identification-diagram (DiD/RDD schematic) | Morandi (mandatory) | Layer 2 (mandatory for primary outcome) |
| `experimental` | empirical | **INTENSIFIED** | STANDARD + forest-plot (effect-size meta) + CONSORT flow diagram + dose-response | Morandi (mandatory) | Layer 2 (mandatory) + per-subgroup |
| `simulational` | empirical | **STANDARD** + regime-map | line/scatter/heatmap + parameter-regime-map + stability-basin | Morandi (mandatory) | Layer 2 (mandatory) + regime overlay |
| `interpretive` | interpretive | **REPLACED** → concept-map | concept-map (argument structure) + timeline (if historical) + quote-network | Morandi (mandatory) | NOT_APPLICABLE (no quantitative data heatmap) |

**Phase 11 REPLACED caveat (interpretive only)**: `/unified-plotting` runs in `concept-map_mode` — outputs a Mermaid/Graphviz argument-structure diagram instead of quantitative figures. The color theme (Morandi) still applies. Layer 2 data heatmap is `NOT_APPLICABLE`.

## Override Application Protocol

The orchestrator executes the following BEFORE Phase 5 launches (after Phase 1b completes and writes `domain-signature.json`):

```
Step 1: Read refine-logs/domain-signature.json
Step 2: Extract signature.evidence_type + signature.reasoning_paradigm
        (If file absent → Phase 1b failed; apply default = STANDARD for all three phases; flag reduced TDAL A dimension)
Step 3: Look up the override row in each table above (Phase 5 / Phase 6 / Phase 11)
Step 4: If signature has mixed evidence_types (e.g., computational_biology = derivational + experimental):
        → apply the MOST INTENSE override across the mix (intensified wins over standard wins over reduced)
        → this ensures mixed-domain problems do not under-verify either side
Step 5: Emit refine-logs/pipeline-intensity-override.json (machine-readable, before Phase 5)
        {
          "intensity_override": {
            "applied_at": "2026-07-21T10:00:00Z",
            "source_signature": "refine-logs/domain-signature.json",
            "evidence_type": "experimental",
            "reasoning_paradigm": "empirical",
            "phase_5": {"intensity": "INTENSIFIED", "emphasis": "...", "budget": "..."},
            "phase_6": {"intensity": "REDUCED", "engine": "...", "verification": "..."},
            "phase_11": {"intensity": "INTENSIFIED", "figure_types": ["forest_plot", "consort", "..."]}
          }
        }
Step 6: Forward the override block to each adapted skill via the phase invocation prompt
        (the orchestrator's delegation prompt to /method-registry /theory-derivation /unified-plotting
         MUST include the intensity_override JSON so the skill adapts accordingly)
Step 7: Log the override in PIPELINE_STATUS.md (transparency — the intensity choice is auditable)
```

## Override Schema (machine-readable)

```json
{
  "intensity_override": {
    "schema_version": "1.0",
    "applied_at": "ISO-8601 timestamp",
    "source_signature": "refine-logs/domain-signature.json",
    "evidence_type": "string (from signature)",
    "reasoning_paradigm": "string (from signature)",
    "mixed_evidence_types": ["list if signature has >1 evidence_type, null otherwise"],
    "phase_5": {
      "intensity": "REDUCED|STANDARD|INTENSIFIED",
      "emphasis": "string",
      "budget_rounds": "int",
      "budget_words": "int",
      "human_checkpoint_scope": "string"
    },
    "phase_6": {
      "intensity": "REDUCED|STANDARD|INTENSIFIED|REPLACED",
      "engine_mode": "sympy|manual|sympy+numerical|interpretive_mode",
      "verification_strictness": "string",
      "output_mark": "string"
    },
    "phase_11": {
      "intensity": "SKIPPED|STANDARD|INTENSIFIED|REPLACED",
      "figure_types": ["list"],
      "color_compliance": "Morandi|NOT_APPLICABLE",
      "data_heatmap": "Layer2|NOT_APPLICABLE|per_subgroup"
    }
  }
}
```

## Fallback / Edge Cases

| Condition | Action |
|-----------|--------|
| `domain-signature.json` absent (Phase 1b failed) | Apply `STANDARD` to all three phases; TDAL A dimension flagged with `missing_inputs: ["domain_learner"]` per contract |
| `evidence_type` not in override table (unknown novel domain) | Apply `STANDARD` (safe default) + WARN log `unknown_evidence_type` for community contribution (see [`domain-contribution-protocol.md`](domain-contribution-protocol.md)) |
| `reasoning_paradigm` missing but `evidence_type` present | Infer paradigm from evidence_type (derivational→formal; correlational/causal/experimental/simulational→empirical; interpretive→interpretive) |
| Mixed evidence_types with conflicting intensities | Most intense wins (INTENSIFIED > STANDARD > REDUCED > SKIPPED; REPLACED is applied only when ALL types in the mix are the replaced-domain) |
| User override (`—paradigm: formal`) | User override trumps signature; emit override with `source: "user_override"` not `source_signature` |

## Boundaries

- **Pipeline structure is invariant.** The 20-phase order, the 3-round fallback cap, the human checkpoints (Phase 3→4, Phase 5→6), the INV-G1 freeze — NONE of these change with intensity. Only per-phase emphasis/budget/gate-strictness adapts.
- **REDUCED never means SKIPPED for Phase 5/6.** Even `derivational` problems run Phase 5 (hash-lock + human checkpoint on proof strategy) and Phase 6 (SymPy attempt; `manual` only on SymPy fail). Only Phase 11 can be `SKIPPED` (derivational) or `REPLACED` (interpretive).
- **INTENSIFIED never removes the 3-round cap.** More sections and stricter gates yes; more retry rounds no — the anti-deadloop ladder is universal.
- **The override is auditable.** `pipeline-intensity-override.json` is a required artifact; the orchestrator MUST NOT silently apply intensity without emitting it. Phase 14 (`/auto-review-loop`) reads it to check whether the intensity choice was justified by the signature.
- **Mixed-domain problems intensify, not average.** Computational biology (derivational + experimental) gets the INTENSIFIED override for both Phase 5 and Phase 6 — the proof side and the experiment side each get full rigor. Averaging would under-verify both.
- **User override trumps signature.** If the human supplies `—paradigm: interpretive` on a problem the learner classified as `empirical`, the user override wins and is logged with `source: "user_override"`.

## Why this is not "hardcoded discipline branch"

Main SciForge has 4 parallel pipelines (economics / cs-ml / physics / general) each with its own framework and reviewer persona. That is hardcoded discipline branching — adding a 5th discipline means adding a 5th pipeline.

This adaptive pipeline is **structurally different**:
1. **One pipeline shape** — 20 phases, invariant order, universal fallback contract. No "economics pipeline" or "physics pipeline".
2. **Intensity is data-driven** — the learner (Phase 1b) writes the signature; the orchestrator reads it and applies the override table. No human pre-classifies the discipline.
3. **The override table is evidence-type-based, not discipline-based** — `derivational` covers math + theoretical CS + logic; `experimental` covers medicine + bio + psychology; `interpretive` covers humanities + law + education. Adding a new discipline that fits an existing evidence_type requires ZERO orchestrator changes.
4. **Unknown evidence_types default to STANDARD** — the pipeline does not break on a novel domain; it runs the v2.7 default behavior and flags for community contribution.

The override table is therefore a **small finite alphabet** (5 evidence_types × 3 phases = 15 cells) that covers all scientific domains via the learner's runtime classification. This is the structural sense in which OSS is "通用" (universal) without "硬编码" (hardcoding).

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — the 20-phase pipeline (Phase 5/6/11 boundaries)
- [`domain-signature-consumer.md`](domain-signature-consumer.md) — how Phase 1b's signature is consumed downstream
- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL A dimension (domain adaptation confidence)
- [`discipline-paradigm.md`](discipline-paradigm.md) — 4 research paradigms (formal/empirical/interpretive/design)
- [`../support/method-registry/SKILL.md`](../support/method-registry/SKILL.md) — Phase 5 (intensity consumer)
- [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) — Phase 6 (intensity consumer + interpretive_mode)
- [`../meta-skills/unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) — Phase 11 (intensity consumer + concept-map_mode)
- [`domain-contribution-protocol.md`](domain-contribution-protocol.md) — unknown evidence_type community contribution channel (long-term L1)
