---
name: adversarial-falsification
type: support-skill
role: idea-falsification-auditor
---

# Adversarial Falsification (SciForge-OSS — Idea Stress Test)

## Quick Reference

- **Purpose**: 5 维度证伪攻击 (假设评分→反例→文献对抗→类比→可行性) 确保 idea 不是"假 trick"
- **Input**: IDEA_CANDIDATES.md (from /idea-discovery)
- **Output**: 每个 idea 的 SURVIVE/WEAKENED/FALSIFIED 判定
- **Key**: 强制证伪 — 先试图杀死 idea，再试图证明它

> **Status**: Rigorous falsification check on every idea BEFORE it enters the derivation pipeline. **OSS forces the agent to try to disprove each idea before trying to prove it.** This prevents "fake tricks" — ideas that look good on paper but are built on unrealistic assumptions.
>
> The core insight: **it's easier to spot why an idea is wrong than to prove it's right.** Most scientific progress comes from falsification, not verification.

## Use When

Use this skill immediately after `/idea-discovery` produces candidate ideas, before `/novelty-check` filters them. Applied to every candidate idea that passed the 5-axis pre-screen.

Typical prompts:
- "Falsify this idea"
- "Stress test these assumptions"
- "Kill the weakest ideas"
- "Find the hidden failure modes"
- "证伪这些 idea"

## Job

For each candidate idea, execute 5 attack vectors to find its weakest point. The non-negotiable goal: **every idea that survives to the derivation phase has been explicitly stress-tested and no obvious falsification was found.**

## Workflow

### Phase 0: Load Domain Signature & Failure Modes

Read `refine-logs/domain-signature.json` (from Phase 1a `/domain-signature`) to auto-load domain-specific failure modes:

1. Read the domain signature → extract `failure_mode_profile.common_failures`
2. Query `shared-references/domain-failure-modes.md` for matching failure modes
3. Add them to the attack vectors for this falsification run
4. If no signature exists, use universal failure modes only

```json
{
  "signature_loaded": true,
  "domain_failure_modes": ["endogeneity", "omitted_variable_bias", "reverse_causality"],
  "failure_mode_source": "domain-failure-modes.md#causal_inference",
  "universal_failure_modes": ["hidden_assumption", "circular_reasoning", "quantifier_error"]
}
```

### Phase 1: Assumption Attack

For each assumption the idea depends on, score its reasonability:

```markdown
## Assumption Attack — IDEA-{id}

| Assumption | Reasonability (0-10) | If violated, impact | Evidence |
|-----------|---------------------|--------------------|----------|
| A1: [assumption] | [0-10] | fatal/severe/minor | [literature support] |
| A2: [assumption] | [0-10] | fatal/severe/minor | [literature support] |
| ... | | | |

**Fatal assumptions**: [count] — if any fatal assumption has reasonability < 5, flag idea as WEAK
**Assumption health score**: [average of all scores]
```

### Phase 2: Counterexample Construction

Try to construct a counterexample that would falsify the idea:

- If the idea claims a theorem, try to find a case where it fails
- If the idea predicts a relationship, try to find a scenario where it doesn't hold
- If the idea requires certain conditions, try to find realistic conditions where they're violated

```markdown
## Counterexample Attack — IDEA-{id}

**Most likely failure mode**: [one sentence]
**Constructed counterexample**: [specific scenario]
**Does the counterexample exist in literature?**: yes/no/unknown
**If yes**: [citation]
**Verdict**: idea survives / idea weakened / idea falsified
```

### Phase 3: Literature Adversarial Search

Search the literature specifically for evidence AGAINST the idea:

- Search for papers that found the opposite result
- Search for known limitations of the proposed method
- Search for failed attempts at similar approaches

```markdown
## Literature Adversarial Search — IDEA-{id}

**Supporting evidence found**: [count] papers
**Contradicting evidence found**: [count] papers
**Evidence balance**: supports / neutral / contradicts
**Key contradicting paper**: [citation] — [one sentence summary]
```

### Phase 4: Analogy Mapping

Map the idea to analogous problems in other domains and estimate prior success probability:

```markdown
## Analogy Mapping — IDEA-{id}

**Domain**: [domain]
**Problem type**: [type]
**Analogous problem in domain X**: [description]
**Success rate of analogous problems**: [low/medium/high]
**Relevance of analogy**: [0-10]
**Adjusted prior**: [low/medium/high]
```

### Phase 5: Computational Feasibility

Estimate minimum resources needed and whether OSS can provide them:

```markdown
## Computational Feasibility — IDEA-{id}

**Min compute needed**: [CPU-hours / GPU-hours / none]
**Min data needed**: [size / type]
**Available in OSS sandbox?**: yes/partial/no
**If partial**: [workaround]
**If no**: [recommendation to scope down or reject]
```

### Phase 6: Data Availability Check

Check whether the required data exists and is accessible. This prevents "data-less theories" — ideas that are theoretically sound but impossible to verify because no data exists.

```markdown
## Data Availability Check — IDEA-{id}

### Required Data Inventory
| Data Item | Type | Publicly Available? | Expected Source |
|-----------|------|-------------------|-----------------|
| D1: [data item] | [time series / matrix / text / ...] | yes / partial / no | [source] |
| D2: [data item] | [time series / matrix / text / ...] | yes / partial / no | [source] |

### Data Availability Score
- **Publicly available**: [X]%
- **Needs application**: [Y]%
- **Not available**: [Z]%

### Data Gap Impact
- **If D1 unavailable**: fatal / severe / minor — [explanation]
- **If D2 unavailable**: fatal / severe / minor — [explanation]

### Recommendations
- **If data availability < 50%**: Mark as HIGH RISK — theory may be unverifiable
- **If any fatal data gap**: Suggest re-scoping to use only available data
- **If all data available**: Proceed with confidence
- **If no data needed (theory-only)**: N/A — theory-only problems skip this check
```

### Data Availability Verdict

| Condition | Verdict |
|-----------|---------|
| Data availability ≥ 80% AND no fatal gaps | DATA_READY |
| Data availability 50-80% OR 1-2 severe gaps | DATA_LIMITED — must scope down |
| Data availability < 50% OR any fatal gap | DATA_BLOCKED — must find alternative data or reframe as theory-only |
| Theory-only problem | N/A (skip check)

## Output

### Per-idea verdict

```json
{
  "idea_id": "IDEA-003",
  "assumption_health": 6.5,
  "has_counterexample": false,
  "evidence_balance": "supports",
  "prior_probability": "medium",
  "oss_feasible": true,
  "overall_verdict": "SURVIVE",
  "remaining_risk": "Assumption A3 is weak (score 4/10) — if violated, result may not hold"
}
```

### Verdict mapping

| Condition | Verdict |
|-----------|---------|
| Assumption health ≥ 6 AND no counterexample AND evidence supports | SURVIVE |
| Assumption health 4-6 OR counterexample found | WEAKENED — must re-express idea to fix |
| Assumption health < 4 OR evidence contradicts | FALSIFIED — reject immediately |

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `strictness` | enum | `normal` | `relaxed` (pass if uncertain), `normal`, `strict` (falsify unless clearly safe) |
| `max_attack_vectors` | int | `5` | Number of attack vectors to execute (1-5) |
| `require_literature_search` | bool | `true` | Whether to search literature for contradicting evidence |

## Boundaries

- **Never skip falsification.** Every idea must be stress-tested before entering derivation.
- **Falsification is not rejection.** A WEAKENED idea can be re-expressed and re-tested.
- **Be honest about assumptions.** If an assumption is clearly unrealistic, say so — don't rationalize.
- **Search for contradiction, not confirmation.** The default should be skepticism, not acceptance.

## See Also

- [`../idea-discovery/SKILL.md`](../../meta-skills/idea-discovery/SKILL.md) — produces the ideas this skill tests
- [`../novelty-check/SKILL.md`](../../meta-skills/novelty-check/SKILL.md) — downstream filter after falsification
- [`../method-registry/SKILL.md`](../method-registry/SKILL.md) — consumes falsification results for assumption registry
- [`../kill-argument/SKILL.md`](../kill-argument/SKILL.md) — complementary adversarial exercise (post-paper, not pre-idea)