# Idea DAG Schema — Single Source of Truth

> **Status**: Contract for the Idea DAG data structure. Consumed by `/idea-creator` Phase 2.5 (DAG-Based Idea Search). Produces `idea-stage/IDEA_DAG.json`.

This schema defines a **Directed Acyclic Graph (DAG)** for storing the idea search space. Each node represents an Idea's state (including its sketch, fidelity scores, and UCB value). Edges represent iteration (Mutation) or combination (Crossover). The DAG structure captures the evolutionary history of ideas — which ideas were derived from which, and which were combined to form fusion ideas.

---

## 1. Why DAG (Not Tree, Not Graph, Not Hypergraph)

| Structure | Why not | DAG advantage |
|-----------|---------|---------------|
| **Binary tree** | A node can only have one parent. Ideas "hybridize" (idea A + idea B → idea C), requiring multiple parents. | A DAG node can have multiple `parent_ids` (mutation lineage) and multiple `crossover_parents` (fusion lineage). |
| **General graph** | Time has direction. Ideas evolve forward — version 2.0 cannot become the "ancestor" of version 1.0. No cycles exist in causal experiment lines. | DAG = directed + acyclic. The acyclic constraint enforces temporal causality. |
| **Hypergraph** | Hyperedges can connect multiple nodes simultaneously, but traversal and pruning complexity is extremely high. | A "Fusion Node" in the DAG (a node with multiple `crossover_parents`) is a flat replacement for a hyperedge — same semantics, simpler algorithms. |

**Conclusion**: DAG is the optimal abstraction. Nodes = idea states. Edges = mutation (iteration) or crossover (combination). Fusion nodes (multiple crossover parents) replace hyperedges.

---

## 2. JSON Schema

The DAG is persisted as `idea-stage/IDEA_DAG.json` with the following structure:

```json
{
  "schema_version": "1.1",
  "idea_dag": {
    "nodes": [
      {
        "id": "idea_001",
        "parent_ids": [],
        "crossover_parents": [],
        "idea_title": "Lightweight attention via low-rank decomposition",
        "idea_sketch": "<discipline-specific sketch: AIM / SOTA-targeted / PNV / default>",
        "discipline": "cs-ml",
        "state": "low_fidelity",
        "fidelity_scores": {
          "low": {
            "verdict": "promising",
            "score": 0.72,
            "reason": "Data insight supports low-rank decomposition; cross-model reviewer agrees feasibility.",
            "evaluated_at": "2026-07-06T10:00:00Z"
          },
          "mid": null,
          "high": null
        },
        "ucb_score": 0.85,
        "visits": 3,
        "data_fit_flags": {
          "scale": "supported",
          "quality": "supported",
          "drift_risk": "constrained",
          "density": "supported",
          "structure": "supported"
        },
        "engineering_grounding": {
          "compute_footprint": {"score": 2, "tier": "HEAVY", "notes": "> 1000 GPU-h estimated"},
          "dependency_chain": {"score": 4, "tier": "CONSTRAINED", "notes": "2 deps not ready: proprietary dataset D3, custom ASIC"},
          "team_year_estimate": {"score": 3, "tier": "HEAVY", "notes": "≈ 18 person-months"},
          "reproducibility_risk": {"score": 4, "tier": "CONSTRAINED", "notes": "≈ 35% chance trick false"},
          "capital_cost": {"score": 8, "tier": "READY", "notes": "uses existing cluster"},
          "eg_average": 4.2,
          "eg_tier": "CONSTRAINED"
        },
        "children": ["idea_005", "idea_008"],
        "edge_types": {
          "idea_005": "mutation",
          "idea_008": "crossover"
        },
        "created_at": "2026-07-06T10:00:00Z",
        "last_updated": "2026-07-06T12:00:00Z",
        "pruned_reason": null
      }
    ],
    "edges": [
      {"from": "idea_001", "to": "idea_005", "type": "mutation"},
      {"from": "idea_002", "to": "idea_008", "type": "crossover"},
      {"from": "idea_001", "to": "idea_008", "type": "crossover"}
    ],
    "root_ids": ["idea_001", "idea_002", "idea_003"],
    "promoted_ids": [],
    "pruned_ids": ["idea_004"],
    "search_metadata": {
      "total_visits": 15,
      "total_iterations": 3,
      "max_iterations": 5,
      "best_score": 0.92,
      "best_idea_id": "idea_008",
      "exploration_constant_c": 1.414,
      "min_promote_score": 0.75
    }
  }
}
```

---

## 3. Node States and Transitions

```
                    ┌─────────────────────────────────────────────────┐
                    │                                                 │
                    ▼                                                 │
    ┌─────────────────────┐    promote (score ≥ 0.5)    ┌────────────┴──────┐
    │   low_fidelity      │ ──────────────────────────► │  mid_fidelity     │
    │   (text reasoning)  │                             │  (proxy experim.) │
    └─────────────────────┘                             └────────┬──────────┘
           │                                                     │
           │ reject (score < 0.5)                        promote  │ (score ≥ 0.65)
           │                                                     ▼
           ▼                                           ┌─────────────────────┐
    ┌─────────────────────┐                           │  high_fidelity      │
    │     pruned          │                           │  (full experiment)  │
    │  (dead end, logged) │                           └────────┬────────────┘
    └─────────────────────┘                                    │
                                               promote (score │ ≥ 0.75)
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │     promoted        │
                                                    │  (ready for Phase 3)│
                                                    └─────────────────────┘
                                                               │
                                               reject (score   │ < 0.75)
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │     pruned          │
                                                    │  (dead end, logged) │
                                                    └─────────────────────┘
```

### State Definitions

| State | Meaning | Next Action |
|-------|---------|-------------|
| `low_fidelity` | Text-only reasoning + data insight matching. Cheapest evaluation. | Promote to mid if `score ≥ 0.5`; prune if `score < 0.5` |
| `mid_fidelity` | Proxy experiment (discipline-specific: 10% data / 3-10 epoch / coarse mesh / simplified model). | Promote to high if `score ≥ 0.65`; prune if `score < 0.65` |
| `high_fidelity` | Full experiment (complete training / full simulation / full sample). | Promote if `score ≥ 0.75`; prune if `score < 0.75` |
| `promoted` | Passed all three fidelity gates. Ready for Phase 3 (deep novelty check). | Forward to `/novelty-check` |
| `pruned` | Eliminated at some fidelity gate. Dead end logged for future reference. | Record `pruned_reason`; never re-evaluate (but may be a crossover parent) |

### Important: Pruned ideas are NOT deleted

Pruned ideas remain in the DAG as **dead ends**. Their `pruned_reason` is recorded so the agent does not regenerate similar ideas. However, a pruned idea can still be a `crossover_parent` — a dead idea's partial insight may combine with another idea to form a viable fusion.

---

## 4. Edge Types

| Edge type | Meaning | Example |
|-----------|---------|---------|
| `mutation` | Iterative refinement of a parent idea. The child modifies one aspect of the parent (e.g., different hyperparameter, different loss function, different assumption). | idea_001 (low-rank attention) → idea_005 (low-rank + sparsity constraint) |
| `crossover` | Fusion of two or more parent ideas. The child combines elements from multiple parents. This is the DAG equivalent of a hypergraph hyperedge. | idea_001 (low-rank attention) + idea_002 (contrastive loss) → idea_008 (low-rank contrastive attention) |

### Fusion Node Rules

A node with ≥2 entries in `crossover_parents` is a **Fusion Node**. Rules:
1. A fusion node must document which element came from which parent in its `idea_sketch`.
2. A fusion node's `low_fidelity` evaluation must explicitly assess whether the combination is synergistic or antagonistic.
3. If a fusion node is pruned, both parents' `children` lists still record the fusion attempt (to avoid re-fusing the same pair).

---

## 5. UCB Score Semantics

The `ucb_score` field on each node is used by the MCTS selection phase to decide which node to expand next. See [`mcts-search-protocol.md`](mcts-search-protocol.md) for the full formula and search algorithm.

```
UCB = V_idea + c * sqrt(ln(N_total) / n_idea)
```

- `V_idea`: The node's current value estimate (highest fidelity score achieved so far, or low-fidelity score if mid/high not yet evaluated).
- `c`: Exploration constant (default `sqrt(2) ≈ 1.414`).
- `N_total`: Total visits across all nodes in the DAG (`search_metadata.total_visits`).
- `n_idea`: This node's visit count (`visits`).

**Key property**: Even a node with mediocre `V_idea` will see its UCB score rise over time as `N_total` grows and `n_idea` stays constant. This forces the agent to "fall back and retry" old ideas instead of getting stuck on a local trick — the core anti-local-optima mechanism.

---

## 6. Data Fit Flags (Optional, Discipline-Aware)

The `data_fit_flags` field on each node records the data axis alignment from the low-fidelity evaluation (sourced from `/ouroboros-data-insight` 5-axis idea-fit verdict). This field is **optional** — it is populated when `DATA_INSIGHT_REPORT.md` exists and the low-fidelity evaluation runs.

| Field | Values | Meaning |
|-------|--------|--------|
| `scale` | `supported` / `constrained` / `blocked` | Is the dataset large enough for this idea's method? |
| `quality` | `supported` / `constrained` / `blocked` | Is the data clean enough? |
| `drift_risk` | `supported` / `constrained` / `blocked` | Are there distributional shifts? |
| `density` | `supported` / `constrained` / `blocked` | Is there enough signal density? |
| `structure` | `supported` / `constrained` / `blocked` | Does data structure match assumptions? |

**Hard filter rule**: If any axis is `blocked`, the idea is pruned at low fidelity. If any axis is `constrained`, the low-fidelity score is capped at 0.6.

**Purpose**: Enables post-hoc analysis of WHY an idea was pruned ("pruned because data scale was blocked" vs "pruned because the method was flawed"). Also prevents re-generating ideas that are fundamentally data-incompatible.

---

## 7. Discipline-Aware Sketch

The `idea_sketch` field carries discipline-specific content per `DISCIPLINE_CONTEXT.discipline`:

| Discipline | Sketch format | Source |
|-----------|---------------|--------|
| `economics` | AIM Sketch (T/I/P/M — Theoretical assumptions / Identification assumptions / Testable implications / Methodology map) | [`discipline-context.md`](discipline-context.md) |
| `cs-ml` | SOTA-targeted (baseline / target metric / contribution type) | [`discipline-context.md`](discipline-context.md) |
| `physics` | PNV Sketch (P/N/V — Physical assumption / Numerical method / Verification) | [`discipline-context.md`](discipline-context.md) |
| `general` | Default (problem / hypothesis / method / claim) | [`discipline-context.md`](discipline-context.md) |

---

## 8. Artifact Registration

`idea-stage/IDEA_DAG.json` is a registered artifact in [`artifact-registry.md`](artifact-registry.md):

| Artifact | Path | Producer | Consumers | Schema |
|----------|------|----------|-----------|--------|
| `IDEA_DAG.json` | idea-stage/ | `/idea-creator` Phase 2.5 | `/idea-creator` (self-consumed across MCTS iterations), `/novelty-check` (reads promoted ideas), `/research-review` (reads promoted ideas for review) | This schema (v1.0) |

---

## 9. Fallback Behavior

If `IDEA_DAG.json` does not exist or is corrupted, `/idea-creator` falls back to the legacy pilot experiment flow (Phase 2 pilot top 2-3 ideas). The DAG search is an enhancement layer, not a hard dependency — the 4 pipeline orchestrators remain unaffected.

---

## 10. Version Compatibility

The `schema_version` field in `IDEA_DAG.json` follows semantic versioning:

| Change type | Version bump | Compatibility rule |
|-------------|-------------|-------------------|
| Add optional field (e.g., `data_fit_flags` in v1.1) | Minor (1.0 → 1.1) | Backward compatible — consumers MUST ignore unknown fields |
| Add required field or change field semantics | Major (1.x → 2.0) | Breaking — requires migration; old DAGs are treated as corrupted (fallback to legacy flow) |
| Remove field | Major | Breaking — never remove fields in minor versions |

**Current version**: 1.0. The `data_fit_flags` field added in this revision is **optional** — existing v1.0 DAGs without it remain valid. Consumers check `schema_version` and apply the appropriate parsing rules.
