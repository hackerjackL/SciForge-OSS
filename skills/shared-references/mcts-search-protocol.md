# MCTS Search Protocol — Monte Carlo Tree Search for Idea Exploration

> **Status**: Contract for the MCTS-based idea search algorithm. Consumed by `/idea-creator` Phase 2.5. Works in concert with [`idea-dag-schema.md`](idea-dag-schema.md) (data structure) and [`multi-fidelity-evaluation.md`](multi-fidelity-evaluation.md) (evaluation gates).

This protocol defines how the agent searches the idea DAG using **Monte Carlo Tree Search (MCTS)** with the **UCB (Upper Confidence Bound)** formula. The goal is to balance **exploration** (trying under-visited ideas) and **exploitation** (deepening promising ideas), avoiding both BFS (too slow) and DFS (one-path-to-death) traps.

---

## 1. Why MCTS (Not BFS, Not DFS, Not Greedy)

| Algorithm | Problem in idea search |
|-----------|------------------------|
| **BFS** (Breadth-First) | Explores all ideas at each level before going deeper. Too slow — token budget exhausted before reaching depth. |
| **DFS** (Depth-First) | Follows one idea to the end. Easy to get stuck on a "local trick" — a path that looks good early but is not globally optimal. |
| **Greedy** | Always picks the highest-scoring idea. No exploration — misses "late bloomers" that start mediocre but improve with iteration. |
| **MCTS + UCB** | Balances exploration and exploitation via UCB formula. Under-visited ideas get a exploration bonus that grows over time, forcing the agent to "fall back and retry" old paths. |

---

## 2. UCB Formula

$$UCB(n) = V_{idea}(n) + c \cdot \sqrt{\frac{\ln N_{total}}{n_{visits}(n)}}$$

| Symbol | Meaning | Source |
|--------|---------|--------|
| $V_{idea}(n)$ | Value estimate of idea node $n$. Defined as the highest fidelity score achieved so far (or the low-fidelity score if mid/high not yet evaluated). | Node's `fidelity_scores.{low,mid,high}.score` — pick the highest non-null. |
| $c$ | Exploration constant. Controls how aggressively the agent explores under-visited ideas. Default: $\sqrt{2} \approx 1.414$. Configurable in `search_metadata.exploration_constant_c`. | `search_metadata.exploration_constant_c` |
| $N_{total}$ | Total visits across all nodes in the DAG. | `search_metadata.total_visits` |
| $n_{visits}(n)$ | Number of times node $n$ has been visited (selected for expansion or evaluation). | Node's `visits` field |

### UCB Behavior

| Scenario | UCB behavior | Effect |
|----------|-------------|--------|
| High $V_{idea}$, low $n_{visits}$ | High UCB (both terms large) | Agent prioritizes this promising + under-explored idea |
| High $V_{idea}$, high $n_{visits}$ | Moderate UCB (exploitation term high, exploration term low) | Agent has already explored this; shifts attention elsewhere |
| Low $V_{idea}$, low $n_{visits}$ | Moderate UCB (exploitation low, but exploration bonus grows with $N_{total}$) | **Key anti-local-optima mechanism**: even mediocre ideas get retried as total search grows, preventing death-spiral on a local trick |
| Low $V_{idea}$, high $n_{visits}$ | Low UCB (both terms small) | Agent gives up on this idea — it's been tried enough |

---

## 3. Four-Phase MCTS Cycle

The search runs in iterations. Each iteration consists of four phases:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCTS ITERATION                           │
│                                                             │
│  1. SELECTION         2. EXPANSION       3. SIMULATION     │
│  ┌──────────┐        ┌──────────┐       ┌──────────┐       │
│  │ Start at │        │ Generate │       │ Run      │       │
│  │ root,    │──────► │ mutation │─────► │ multi-   │       │
│  │ pick     │        │ or       │       │ fidelity │       │
│  │ highest  │        │ crossover│       │ eval     │       │
│  │ UCB child│        │ child    │       │          │       │
│  │ down to  │        │ node     │       │          │       │
│  │ leaf     │        │          │       │          │       │
│  └──────────┘        └──────────┘       └────┬─────┘       │
│                                                │             │
│                           4. BACKPROPAGATION   │             │
│                           ┌────────────────────▼──────────┐  │
│                           │ Update V_idea and visits      │  │
│                           │ for the new node and all      │  │
│                           │ ancestors up to root          │  │
│                           └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1: Selection

Starting from each root node, descend through the DAG by repeatedly selecting the child with the highest UCB score. Stop when reaching:
- A leaf node (no children), OR
- A node that has not yet been fully evaluated (state is `low_fidelity` or `mid_fidelity` and can be promoted)

**Selection rule**: At each node, compute UCB for all children. Pick `argmax(UCB(child))`. If there's a tie, pick the one with fewer visits (favor exploration). BLOCKED nodes are excluded from selection (they cannot be expanded until the blocking condition is resolved).

### Phase 2: Expansion

At the selected leaf, generate ONE new child node via one of two operations:

| Operation | When to use | How |
|-----------|-------------|-----|
| **Mutation** | The selected idea has potential but one dimension needs improvement | Modify one aspect: different hyperparameter, different loss function, different assumption, different numerical method |
| **Crossover** | Two ideas each have a complementary strength | Create a Fusion Node combining elements from both parents. The fusion must document which element came from which parent. |

**Expansion rules**:
1. Mutation children must differ from the parent in exactly one dimension (not a random restart).
2. Crossover children must have ≥2 `crossover_parents` and must assess synergy in the low-fidelity gate.
3. Each expansion increments `search_metadata.total_visits` and the new node's `visits`.

### Phase 3: Simulation (Multi-Fidelity Evaluation)

The new child node is evaluated through the multi-fidelity pipeline. See [`multi-fidelity-evaluation.md`](multi-fidelity-evaluation.md) for the full discipline-specific gates.

**Critical**: Simulation starts at `low_fidelity`. The node does NOT automatically proceed to mid/high — it only proceeds if it passes the promotion threshold. This is the core token-saving mechanism.

| Fidelity | Token cost | What happens |
|----------|-----------|--------------|
| Low | Minimal (text reasoning) | Evaluate. If `score ≥ 0.5` → promote to mid. If `score < 0.5` → prune. |
| Mid | Moderate (proxy experiment) | Evaluate ONLY if promoted from low. If `score ≥ 0.65` → promote to high. If `score < 0.65` → prune. |
| High | Full (complete experiment) | Evaluate ONLY if promoted from mid. If `score ≥ 0.75` → `promoted`. If `score < 0.75` → prune. |

### Phase 4: Backpropagation

After simulation, update the node and all its ancestors up to the root(s):

1. **Update `visits`**: Increment `visits` for the new node and every ancestor on the path to root.
2. **Update `V_idea`**: For each ancestor, recompute `V_idea` as `max(fidelity_scores.{low,mid,high}.score)` — the best score in its subtree (not just its own score). This ensures ancestors of a high-scoring descendant get credit.
3. **Update `ucb_score`**: Recompute UCB for all nodes using the new $N_{total}$ and $n_{visits}$.
4. **Update `search_metadata`**: Increment `total_iterations`. Update `best_score` and `best_idea_id` if a new high is found.

---

## 4. Termination Conditions

The search terminates when ANY of the following is true:

| Condition | Threshold | Rationale |
|-----------|-----------|----------|
| `total_iterations >= max_iterations` | Default: 5 | Budget limit. Prevents infinite search. |
| `promoted_ids` has ≥1 idea AND all root ideas have `visits ≥ 3` | At least one winner + adequate exploration | We have a winner and have explored enough. |
| All non-pruned, non-blocked nodes are in `promoted` or `high_fidelity` state | No more to explore | Search space exhausted. BLOCKED nodes (technical failures) are excluded from this check — they do not prevent termination. |
| Experiment budget exhausted | Discipline-specific: cs-ml ≥ 30 GPU-hours, physics ≥ 100 CPU-hours, economics ≥ 15 stat-hours, general ≥ 20 resource-hours | Hard stop to prevent runaway compute costs. Measured by summing mid-fidelity + high-fidelity experiment costs across all iterations. |

**`max_iterations` is configurable per discipline**:

| Discipline | Default `max_iterations` | Rationale |
|-----------|--------------------------|-----------|
| `cs-ml` | 5 | GPU experiments are expensive; 5 iterations give enough exploration without excessive cost. |
| `physics` | 4 | HPC simulations are even more expensive; fewer iterations but deeper per-iteration analysis. |
| `economics` | 6 | Statistical experiments are cheaper; more iterations allow broader exploration of identification strategies. |
| `general` | 4 | Balanced default. |

---

## 5. Pseudo-Code

```python
def mcts_search(dag, discipline, max_iterations=5):
    """Run MCTS search on the idea DAG."""
    for iteration in range(max_iterations):
        # Phase 1: Selection
        selected_leaf = select_leaf(dag)

        # Phase 2: Expansion
        new_node = expand(selected_leaf, dag)

        # Phase 3: Simulation (multi-fidelity evaluation)
        score = evaluate_multi_fidelity(new_node, discipline)
        # Low → Mid → High, with promotion gates at each level

        # Phase 4: Backpropagation
        backpropagate(new_node, score, dag)

        # Check termination
        if should_terminate(dag):
            break

    return dag.search_metadata.best_idea_id


def select_leaf(dag):
    """Descend from root, picking highest-UCB child."""
    current = pick_root_with_highest_ucb(dag)
    while current.children:
        current = max(current.children, key=lambda c: c.ucb_score)
    return current


def expand(leaf, dag):
    """Generate a mutation or crossover child."""
    if should_crossover(leaf, dag):
        partner = find_crossover_partner(leaf, dag)
        child = create_fusion_node(leaf, partner, dag)
    else:
        child = create_mutation(leaf, dag)
    return child


def evaluate_multi_fidelity(node, discipline):
    """Run low → mid → high fidelity gates."""
    # Low fidelity (always run)
    node.fidelity_scores.low = run_low_fidelity(node, discipline)
    if node.fidelity_scores.low.score < 0.5:
        node.state = "pruned"
        return node.fidelity_scores.low.score

    # Mid fidelity (discipline-specific proxy experiment)
    node.fidelity_scores.mid = run_mid_fidelity(node, discipline)
    if node.fidelity_scores.mid.score < 0.65:
        node.state = "pruned"
        return node.fidelity_scores.mid.score

    # High fidelity (full experiment)
    node.fidelity_scores.high = run_high_fidelity(node, discipline)
    if node.fidelity_scores.high.score >= 0.75:
        node.state = "promoted"
        dag.promoted_ids.append(node.id)
    else:
        node.state = "pruned"
    return node.fidelity_scores.high.score


def backpropagate(node, score, dag):
    """Update visits and V_idea up to root."""
    dag.search_metadata.total_visits += 1
    current = node
    while current is not None:
        current.visits += 1
        current.V_idea = max(current.V_idea, score)
        current = get_parent(current, dag)
    recompute_all_ucb(dag)
```

---

## 6. Crossover Partner Selection

Crossover (fusion) is the most powerful operation — it creates genuinely new ideas by combining existing ones. But bad crossovers waste tokens. Rules for selecting a crossover partner:

| Rule | Rationale |
|------|----------|
| Partner must be in a different subtree (no common ancestor within 2 generations) | Avoids inbreeding — combining two variations of the same idea rarely produces novelty. |
| Partner's `V_idea` must be ≥ 0.4 | Don't fuse with a dead idea — but DO allow fusing with a pruned idea if its `pruned_reason` suggests partial value. |
| The fusion must address a specific weakness in the selected leaf | Random fusion is wasteful. The agent must articulate: "idea A has strength X but weakness Y; idea B has strength Y; fusion A+B covers both." |
| Max 1 crossover per iteration | Crossover is expensive (2 parents to evaluate). Limit to 1 per iteration to control cost. |

### Discipline-Aware Crossover Constraints

The universal rules above apply to all disciplines. Additionally, each discipline imposes domain-specific constraints on what dimensions may be fused:

| Discipline | Allowed fusion dimensions | Forbidden fusion | Rationale |
|-----------|--------------------------|-------------------|----------|
| `cs-ml` | Architecture + loss function; module + training strategy; backbone + head | Two fundamentally different task formulations | Architecture/loss fusion is standard ML practice (e.g., ResNet + contrastive loss) |
| `economics` | Methodology + data source; estimator + robustness strategy | Two different identification strategies (e.g., DiD + IV) | Identification strategy is the causal foundation — fusing DiD and IV produces an incoherent design |
| `physics` | Numerical method + geometry; material model + boundary condition | Two incompatible physical assumptions (e.g., paraxial + full-vectorial) | Fused PNV chain must still close (P⟹N⟹V⟹P); incompatible assumptions break closure |
| `general` | Any dimension (agent discretion) | None (agent must justify) | General pipeline has no domain-specific framework to protect |

**Physics-specific**: After crossover, the low-fidelity evaluation MUST verify that the fused PNV chain is structurally complete (each P_i has N_i and V_i). If the chain is broken, the fusion node is immediately pruned without mid/high fidelity evaluation.

---

## 7. Noise Handling (Anti-False-Trick Mechanism)

The user's core concern: "early good signal may be a local false optimum (伪 Trick)." MCTS handles this through two mechanisms:

### 7.1 UCB Exploration Bonus

Even a node with mediocre $V_{idea}$ will see its UCB score rise over time as $N_{total}$ grows. When the agent has visited other nodes many times, an under-visited root idea's exploration term $\sqrt{\ln N_{total} / n_{visits}}$ grows, forcing the agent to "fall back and retry" it. This prevents death-spiral on a local trick.

### 7.2 Mid-Fidelity Trick Detection

At mid-fidelity, if the score **drops more than 30%** from the low-fidelity score, this is flagged as a **suspected false trick**:

```
if mid_score < low_score * 0.7:
    flag as "suspected_false_trick"
    retry mid-fidelity once (with different random seed / subset)
    if retry_score still < low_score * 0.7:
        prune (confirmed false trick)
```

This catches ideas that look good on paper (low-fidelity text reasoning) but fail under proxy experiment (mid-fidelity) — the classic "local trick" the user described.

---

## 8. Parameters Summary

| Parameter | Default | Configurable in | Description |
|-----------|---------|-----------------|-------------|
| `max_iterations` | 5 (cs-ml), 4 (physics), 6 (economics), 4 (general) | `search_metadata.max_iterations` | Max MCTS iterations |
| `exploration_constant_c` | 1.414 ($\sqrt{2}$) | `search_metadata.exploration_constant_c` | UCB exploration weight |
| `min_promote_score` | 0.75 | `search_metadata.min_promote_score` | Minimum high-fidelity score to promote |
| Low→Mid threshold | 0.5 | [`multi-fidelity-evaluation.md`](multi-fidelity-evaluation.md) | Minimum low-fidelity score to promote to mid |
| Mid→High threshold | 0.65 | [`multi-fidelity-evaluation.md`](multi-fidelity-evaluation.md) | Minimum mid-fidelity score to promote to high |
| False-trick drop threshold | 0.30 (30%) | This protocol | Score drop percentage that triggers false-trick detection |
| Max crossover per iteration | 1 | This protocol | Limit fusion operations per iteration |
| Experiment budget | cs-ml: 30 GPU-h, physics: 100 CPU-h, economics: 15 stat-h, general: 20 resource-h | This protocol (Termination Conditions) | Hard compute budget across all MCTS iterations |

---

## 9. Integration with Existing Pipeline

The MCTS search is invoked by `/idea-creator` Phase 2.5. It does NOT replace the existing pilot experiment flow — it enhances it:

| Existing flow (unchanged) | New flow (Phase 2.5) |
|---------------------------|---------------------|
| Phase 2: Generate 8-12 ideas via cross-model review | Phase 2.5: Load 8-12 ideas as DAG root nodes → run MCTS search |
| Phase 2: Pilot top 2-3 ideas (legacy) | Phase 2.5: MCTS replaces pilot — low/mid/high fidelity gates are a superset of pilot |
| Phase 3: Novelty check on top ideas | Phase 3: Novelty check on `promoted_ids` from DAG |

**Fallback**: If `IDEA_DAG.json` is corrupted or MCTS fails, fall back to the legacy pilot flow (top 2-3 ideas, direct pilot experiment). The 4 pipeline orchestrators are unaffected.
