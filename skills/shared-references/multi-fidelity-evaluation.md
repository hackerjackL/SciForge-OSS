# Multi-Fidelity Evaluation Contract — Three-Layer Filter for Idea Screening

> **Status**: Contract for the three-layer multi-fidelity evaluation system. Consumed by `/idea-creator` Phase 2.5 (DAG-Based Idea Search). Works with [`idea-dag-schema.md`](idea-dag-schema.md) (DAG structure) and [`mcts-search-protocol.md`](mcts-search-protocol.md) (search algorithm).

This contract defines the **three fidelity gates** that filter ideas from cheap text reasoning to expensive full experiments. The goal is to **minimize token and compute waste** by pruning bad ideas early, while **catching "late bloomers"** that look mediocre initially but improve with iteration.

---

## 1. The Core Problem: Noisy Rewards and False Tricks

The user's pain point: "early good signal may be a local false optimum (伪 Trick)."

In reinforcement learning, this is called **noisy reward** or **delayed reward**. In idea search, it manifests as:

| Failure mode | Description | Example |
|--------------|-------------|---------|
| **False trick** | An idea looks great in text reasoning and initial proxy experiment, but fails under full training. | A loss function that reduces training loss fast but overfits; a numerical method that converges on coarse mesh but diverges on fine mesh. |
| **Late bloomer** | An idea looks mediocre initially but improves significantly with more training / refinement. | A complex architecture that needs >50 epochs to show advantage; an identification strategy that needs larger sample to show significance. |
| **Dead end** | An idea is fundamentally flawed — no amount of iteration will fix it. | A physical assumption that violates conservation law; an identification strategy with collinear instruments. |

**Multi-fidelity evaluation solves all three** by progressively investing more resources only in ideas that pass each gate.

---

## 2. Three-Layer Filter

```
    8-12 candidate ideas (from /idea-creator Phase 2)
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │  LOW FIDELITY (text reasoning, ~0 token cost)        │
    │  • Data insight matching                             │
    │  • Cross-model feasibility review                    │
    │  • Discipline-specific assumption check              │
    │  • Prune ~50% (reject score < 0.5)                   │
    └──────────────────────────┬───────────────────────────┘
                               │ promote (score ≥ 0.5)
                               ▼
    ┌──────────────────────────────────────────────────────┐
    │  MID FIDELITY (proxy experiment, moderate cost)      │
    │  • Discipline-specific proxy: 10% data / 3-10 epoch  │
    │    / coarse mesh / simplified model                  │
    │  • Compare against baseline trend                    │
    │  • False-trick detection (score drop > 30%)          │
    │  • Prune ~60% (reject score < 0.65)                  │
    └──────────────────────────┬───────────────────────────┘
                               │ promote (score ≥ 0.65)
                               ▼
    ┌──────────────────────────────────────────────────────┐
    │  HIGH FIDELITY (full experiment, full cost)          │
    │  • Complete training / full simulation / full sample │
    │  • Strict ablation study                             │
    │  • Convergence / robustness check                    │
    │  • Promote top performers (score ≥ 0.75)             │
    └──────────────────────────┬───────────────────────────┘
                               │ promote (score ≥ 0.75)
                               ▼
                        PROMOTED IDEAS
                   (ready for /novelty-check)
```

### Filter Yields

| Gate | Input | Output | Yield | Cumulative yield |
|------|-------|--------|-------|------------------|
| Low fidelity | 8-12 ideas | ~4-6 ideas | ~50% | ~50% |
| Mid fidelity | 4-6 ideas | ~2-3 ideas | ~40% | ~20% |
| High fidelity | 2-3 ideas | ~1-2 ideas | ~50% | ~10% |
| **Total** | 8-12 ideas | 1-2 promoted | — | **~10-15%** |

This means: out of 8-12 candidate ideas, only 1-2 survive to full novelty check. The other 90% are pruned at low or mid fidelity, saving massive token and compute costs.

---

## 3. Discipline-Specific Evaluation

Each discipline has its own evaluation method at each fidelity level. The **DAG + MCTS framework is universal**, but the **evaluation content is discipline-specific**.

### 3.1 CS/ML (Pipeline B)

| Fidelity | Evaluation method | Token cost | Compute cost | Pass threshold |
|----------|-------------------|------------|-------------|----------------|
| **Low** | Text reasoning: data insight matching (5-axis idea-fit), cross-model feasibility review, SOTA gap analysis. "Can this idea plausibly beat the baseline on this data?" | Minimal (text only) | None | `score ≥ 0.5` |
| **Mid** | **Proxy experiment: train for 3-10 epochs on 10% data subset.** Compare convergence trend against baseline at the same point. If the idea's validation loss is lower than baseline's at epoch 10, it's promising. If higher, it's a false trick. | Moderate (code generation + 10% training) | ~0.5-2 GPU-hours | `score ≥ 0.65` |
| **High** | Full training: complete training run with all epochs, full dataset, proper hyperparameter tuning. Ablation study: remove the novel component and verify performance drops. | Full (complete training + ablation) | ~4-24 GPU-hours | `score ≥ 0.75` |

**Mid-fidelity scoring formula (cs-ml)**:
```
mid_score = 0.5 * trend_score + 0.3 * gradient_health + 0.2 * resource_efficiency

trend_score = 1.0 if idea_val_loss < baseline_val_loss at epoch 10
            = 0.5 if idea_val_loss ≈ baseline (within 5%)
            = 0.0 if idea_val_loss > baseline by >5%

gradient_health = 1.0 if gradients are stable (no NaN, no explosion)
                = 0.5 if mild instability (correctable with gradient clipping)
                = 0.0 if severe instability (NaN, explosion)

resource_efficiency = 1.0 if GPU memory < 80% of baseline
                   = 0.5 if ≈ baseline
                   = 0.0 if >120% of baseline (too expensive)
```

**False-trick detection**: If `mid_score < low_score * 0.7`, flag as suspected false trick. Retry once with different 10% subset. If still fails, prune.

### 3.2 Physics (Pipeline C)

| Fidelity | Evaluation method | Token cost | Compute cost | Pass threshold |
|----------|-------------------|------------|-------------|----------------|
| **Low** | Text reasoning: PNV chain completeness check (Physical assumption → Numerical method → Verification). Physical validity of synthetic data. Conservation law check. "Does this physical model make sense?" | Minimal | None | `score ≥ 0.5` |
| **Mid** | **Proxy experiment: run on coarse mesh / simplified geometry.** Verify that the physical assumption holds at reduced resolution. Check convergence trend — if the solution diverges on coarse mesh, it will diverge on fine mesh too. | Moderate (code generation + coarse simulation) | ~2-4 CPU-hours | `score ≥ 0.65` |
| **High** | Full simulation: complete mesh resolution, full boundary conditions, convergence study (mesh independence). Benchmarking against analytical or experimental reference. | Full (complete simulation + convergence study) | ~16-48 CPU-hours | `score ≥ 0.75` |

**Mid-fidelity scoring formula (physics)**:
```
mid_score = 0.4 * convergence_trend + 0.4 * physical_validity + 0.2 * stability

convergence_trend = 1.0 if solution converges on coarse mesh
                  = 0.5 if converges with relaxation
                  = 0.0 if diverges

physical_validity = 1.0 if conservation laws satisfied on coarse mesh
                  = 0.5 if minor violation (correctable with finer mesh)
                  = 0.0 if severe violation (fundamental flaw)

stability = 1.0 if CFL condition satisfied and time-stepping stable
          = 0.5 if marginal stability
          = 0.0 if instability
```

**False-trick detection**: If a method converges on coarse mesh but violates conservation laws, it's a numerical artifact (false trick). Retry with finer mesh. If conservation still violated, prune.

### 3.3 Economics (Pipeline A)

| Fidelity | Evaluation method | Token cost | Compute cost | Pass threshold |
|----------|-------------------|------------|-------------|----------------|
| **Low** | Text reasoning: AIM chain completeness check (Theoretical assumptions → Identification assumptions → Testable implications → Methodology map). Identification strategy feasibility. "Can this identification strategy recover the causal parameter?" | Minimal | None | `score ≥ 0.5` |
| **Mid** | **Proxy experiment: run on 10% sample with simplified model.** Check if the sign of the estimate matches theoretical prediction. Check if first-stage F-stat > 10 (for IV). Check if parallel trends hold on subsample (for DiD). | Moderate (code generation + 10% regression) | ~0.5-1 stat-hour | `score ≥ 0.65` |
| **High** | Full estimation: complete sample, proper standard errors (clustering, robust), robustness checks (placebo, Oster bound, alternative specifications). Replication package readiness. | Full (complete estimation + robustness) | ~2-4 stat-hours | `score ≥ 0.75` |

**Mid-fidelity scoring formula (economics)**:
```
mid_score = 0.3 * sign_match + 0.3 * identification_strength + 0.2 * precision + 0.2 * specification_stability

sign_match = 1.0 if estimate sign matches theoretical prediction
           = 0.0 if opposite sign (red flag)

identification_strength = 1.0 if first-stage F > 10 (IV) or parallel trends hold (DiD)
                        = 0.5 if marginal (F ≈ 10, weak trends)
                        = 0.0 if weak (F < 10, trends violated)

precision = 1.0 if standard error < 0.5 * estimate magnitude
          = 0.5 if standard error ≈ estimate
          = 0.0 if standard error > estimate (insignificant)

specification_stability = 1.0 if estimate stable across 2-3 alternative specs on subsample
                        = 0.5 if moderate variation
                        = 0.0 if sign flips across specs
```

**False-trick detection**: If the estimate sign flips across alternative specifications on the 10% subsample, it's a specification-driven artifact (false trick). Retry with different 10% subsample. If sign still flips, prune.

### 3.4 General (Pipeline D)

| Fidelity | Evaluation method | Token cost | Compute cost | Pass threshold |
|----------|-------------------|------------|-------------|----------------|
| **Low** | Text reasoning: data insight matching, cross-model feasibility review, problem-hypothesis-method-claim completeness. "Is this idea worth testing?" | Minimal | None | `score ≥ 0.5` |
| **Mid** | **Proxy experiment: simplified verification.** Run a minimal test that captures the core claim. This is discipline-agnostic — the agent decides what constitutes a "minimal test" based on the idea's nature. | Moderate | varies | `score ≥ 0.65` |
| **High** | Full experiment: complete test with proper controls, replication. | Full | varies | `score ≥ 0.75` |

**Mid-fidelity scoring formula (general)**:
```
mid_score = 0.4 * core_claim_support + 0.3 * reproducibility + 0.3 * effect_size

core_claim_support = 1.0 if proxy test supports the core claim
                   = 0.5 if ambiguous
                   = 0.0 if contradicts

reproducibility = 1.0 if result stable across 2 runs with different seeds
                = 0.5 if moderate variation
                = 0.0 if high variation

effect_size = 1.0 if effect size > 0.5 * expected
            = 0.5 if effect size ≈ 0.3 * expected
            = 0.0 if effect size negligible
```

---

## 4. Promotion Gates Summary

| Gate | From → To | Threshold | Rationale |
|------|-----------|-----------|-----------|
| Gate 1 | Low → Mid | `score ≥ 0.5` | Eliminate ideas that fail even text-level feasibility. ~50% pruned. |
| Gate 2 | Mid → High | `score ≥ 0.65` | Eliminate false tricks that fail proxy experiment. ~60% pruned. |
| Gate 3 | High → Promoted | `score ≥ 0.75` | Only ideas that survive full experiment are promoted. ~50% pruned. |

**Asymmetric gates**: The thresholds are deliberately increasing (0.5 → 0.65 → 0.75). This reflects the increasing cost of each level — we want to be more selective at higher fidelity because each step costs 10x more.

---

## 5. False-Trick Detection (Cross-Discipline)

The user's core concern is "false tricks" — ideas that look good early but fail later. Each discipline has its own false-trick signature:

| Discipline | False-trick signature | Detection method | Action |
|-----------|----------------------|-------------------|--------|
| **CS/ML** | Training loss drops fast but validation loss diverges | Compare idea vs baseline validation loss at epoch 10 | Retry with different 10% subset; if still fails, prune |
| **Physics** | Solution converges on coarse mesh but violates conservation laws | Check conservation on coarse mesh | Retry with finer mesh; if still violated, prune |
| **Economics** | Estimate sign flips across alternative specifications | Run 2-3 alternative specs on 10% subsample | Retry with different subsample; if sign still flips, prune |
| **General** | Effect size is an artifact of random seed | Run with 2 different seeds | Retry with third seed; if not stable, prune |

**Universal rule**: If `mid_score < low_score * 0.7` (30% drop), flag as suspected false trick and retry once. If retry still fails, prune.

---

## 6. Resource Budget per Discipline

| Discipline | Low cost | Mid cost | High cost | Total for 5 iterations |
|-----------|---------|---------|----------|----------------------|
| CS/ML | ~0 token | ~1-2 GPU-hours per idea | ~4-24 GPU-hours per idea | ~30-130 GPU-hours |
| Physics | ~0 token | ~2-4 CPU-hours per idea | ~16-48 CPU-hours per idea | ~100-280 CPU-hours |
| Economics | ~0 token | ~0.5-1 stat-hour per idea | ~2-4 stat-hours per idea | ~15-55 stat-hours |
| General | ~0 token | varies | varies | varies |

**Cost control**: The MCTS `max_iterations` parameter (see [`mcts-search-protocol.md`](mcts-search-protocol.md)) limits total iterations. The multi-fidelity gates ensure that only ~10-15% of ideas reach high fidelity, so the total cost is bounded.

---

## 7. Integration with Data Insight

The `/ouroboros-data-insight` skill produces a 5-axis idea-fit verdict that feeds into the **low-fidelity** evaluation:

| Axis | Used in | Question answered |
|------|---------|-------------------|
| Scale | Low fidelity (all disciplines) | Is the dataset large enough for this idea's method? (e.g., IV needs N ≫ 1000) |
| Quality | Low fidelity (all disciplines) | Is the data clean enough for this idea? (e.g., staggered DiD needs clean treatment timing) |
| Drift Risk | Low fidelity (economics, cs-ml) | Are there distributional shifts that undermine this idea? |
| Density | Low fidelity (physics, cs-ml) | Is there enough signal density for this method? |
| Structure | Low fidelity (all disciplines) | Does the data structure match the idea's assumptions? |

**Hard filter**: If any axis is `BLOCKED`, the idea is pruned at low fidelity without further evaluation. If any axis is `CONSTRAINED`, the idea's low-fidelity score is capped at 0.6 (cannot be promoted to mid without addressing the constraint).

---

## 8. Fallback Behavior

If the multi-fidelity evaluation fails (e.g., proxy experiment code won't compile, data subset unavailable), the idea is **not pruned** — it is marked as `BLOCKED` and the MCTS search continues with other ideas. The `BLOCKED` idea can be retried in a later iteration if the blocking condition is resolved.

This ensures that technical failures (not idea failures) do not cause premature pruning.

**BLOCKED nodes and MCTS termination**: BLOCKED nodes are excluded from UCB selection (they cannot be expanded). They also do NOT prevent termination condition 3 ("all non-pruned, non-blocked nodes are in promoted or high_fidelity state") from being satisfied. If all explorable ideas are either promoted, high_fidelity, or pruned, the search terminates even if BLOCKED nodes remain. The BLOCKED ideas are reported in `IDEA_DAG.json` with their blocking reason for potential future retry.
