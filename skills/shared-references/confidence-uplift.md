# Confidence Uplift Mechanisms (SciForge-OSS — from evaluate to improve)

> **Status (v2.8 — mid-term M2)**: Defines three **proactive** mechanisms that **raise** the TDAL joint confidence, complementing [`domain-adaptation-contract.md`](domain-adaptation-contract.md) which only **evaluates** it. v2.7 stops at "this claim is WEAK"; v2.8 adds "here is how to make it MODERATE or STRONG". The uplift is invoked when TDAL verdict ≤ WEAK, OR when the orchestrator proactively wants to push a MODERATE toward STRONG.
>
> **Core principle**: TDAL measures landing confidence. Uplift mechanisms **target the weakest dimension** and either strengthen it (within scope) or expand the scope to hedge it (alternative paths). The uplift is a **bounded, auditable loop** — not infinite polish. Three levers: assumption strength analysis (tighten T), alternative path analysis (hedge A/D), progressive verification (lift T incrementally).

## Quick Reference

- **Purpose**: 从"评估置信度"升级为"提高置信度"——三机制主动拉升 TDAL
- **Input**: CLAIMS_FROM_RESULTS.md (TDAL verdict + weakest_dimension) from Phase 10
- **Output**: refine-logs/confidence-uplift-plan.json (uplift actions + expected lift + budget)
- **Invocation**: verdict ≤ WEK → MUST invoke; verdict MODERATE + weakest_dimension identifiable → SHOULD invoke; verdict STRONG → skip
- **Key**: 上限是 bounded uplift loop (≤ 3 rounds per mechanism); 不能把 UNSUPPORTED 强拖到 STRONG——UNSUPPORTED 触发 BLOCK 后 uplift 走人工审批通道

## Three Mechanisms

### Mechanism 1: Assumption Strength Analysis (tighten T dimension)

**Target**: TDAL `theoretical` dimension (T) when weakest_dimension = `theoretical` OR T < 0.7.

**Logic**: Every theoretical derivation rests on assumptions. Stronger (more restrictive) assumptions are easier to verify but apply to narrower scope; weaker (more permissive) assumptions apply broadly but are harder to ground. The uplift finds the **optimal strength point**: tighten assumptions to where the proof closes, without narrowing scope below the problem's actual claim.

**Workflow**:

```
Step 1: Enumerate the derivation's assumptions (from Phase 6 premises.md)
        → For each: classify current strength {weak|medium|strong}
        → Current strength is judged by how restrictive the assumption is

Step 2: For each assumption blocking the proof (Phase 6 SymPy FAIL or PARTIAL):
        → Generate 3 strength variants:
            variant_s: stronger version (more restrictive) — does the proof close?
            variant_m: medium version (current) — current state
            variant_w: weaker version (less restrictive) — broader scope, proof definitely fails
        → Run SymPy on variant_s first; if closes → record the scope reduction

Step 3: Compute strength-scope tradeoff per assumption:
        strength_score = proof_closes ? 1.0 : 0.0  (does SymPy succeed)
        scope_score    = fraction of problem claim still covered by the tightened assumption
        optimal_score  = strength_score × scope_score  (maximize)

Step 4: Pick the variant with highest optimal_score:
        → If variant_s closes AND scope_score ≥ 0.5: adopt variant_s, document scope reduction
        → If variant_s closes AND scope_score < 0.5: do NOT adopt; flag as "scope loss too severe"
        → If no variant closes: record fundamental_gap, escalate to Mechanism 2 (alternative path)

Step 5: Re-run Phase 6 with tightened assumptions; recompute T dimension
        → Expected lift: T goes from FAIL (0.0) to PARTIAL (0.5) or PASS (1.0) for the affected component
        → TDAL joint uplift estimated: ΔT × D × A × L (downstream unchanged)
```

**Worked example**:

```
Problem: convergence of an iterative scheme on Banach spaces
Phase 6 SymPy FAIL on the original assumption "operator is arbitrary bounded"
Step 1: assumption = "operator is arbitrary bounded" — current strength = weak
Step 2: variants:
    variant_s: "operator is compact + contraction" → SymPy closes (PASS)
    variant_m: "operator is arbitrary bounded" → FAIL (current)
    variant_w: "operator is linear" → SymPy FAIL (broader but proof still fails)
Step 3: variant_s strength_score = 1.0, scope_score = 0.7 (compact+contraction ⊂ bounded; still covers most practical uses)
        optimal_score = 1.0 × 0.7 = 0.7
Step 4: variant_s scope_score 0.7 ≥ 0.5 → adopt
Step 5: re-run Phase 6 with "operator is compact + contraction"
        T component sympy_derivation: 0.0 → 1.0; T dimension: 0.4×1.0 + 0.3×1.0 + 0.3×1.0 = 1.0
        TDAL joint uplift: 1.0×0.725×0.80×0.755 = 0.436 (vs 0.0×... = 0.0 before — major lift)

Scope caveat (mandatory in paper):
    "We establish convergence for compact contraction operators on Banach spaces. The result for arbitrary bounded operators remains a conjecture; the tightened assumption covers most practical iterative schemes but excludes adversarial constructions."
```

**Budget**: ≤ 3 rounds (one per blocking assumption; if more than 3 blocking assumptions, take the 3 with highest scope_score potential). 3 rounds exhausted without proof closure → escalate to Mechanism 2.

### Mechanism 2: Alternative Path Analysis (hedge A/D dimensions)

**Target**: TDAL `domain_adaptation` (A) or `data_availability` (D) when weakest_dimension is one of these AND Mechanism 1 cannot tighten T further.

**Logic**: If the primary assumption/path fails to ground, identify alternative paths that arrive at the same conclusion under different assumptions. Each alternative path hedges the failure mode — if any one alternative survives falsification, the claim is grounded modulo "the conclusion holds under at least one of {primary, alt-1, alt-2, alt-3}". This raises A (domain fit broadens) or D (data alternatives broaden) without faking the primary path.

**Workflow**:

```
Step 1: Identify the failing/weak component in A or D dimension
        → A weak: domain_learner confidence < 0.7 OR seed_paper_match < 0.5
        → D weak: ouroboros_report score < 0.5 OR oss_data_check = DATA_LIMITED

Step 2: Generate 2-3 alternative paths:
        For A weak:
            alt-1: alternative methodological tradition in the same domain
                   (e.g., primary = DiD; alt-1 = IV; alt-2 = RDD; alt-3 = synthetic control)
            alt-2: alternative paradigm interpretation
                   (e.g., primary = empirical; alt-2 = simulational validation via synthetic data)
            alt-3: meta-analytic path
                   (combine with literature's existing estimates rather than derive from scratch)
        For D weak:
            alt-1: alternative dataset for the same variable
                   (e.g., primary = CPS; alt-1 = PSID; alt-2 = ACS; alt-3 = synthetic data)
            alt-2: proxy variable for missing variable
                   (e.g., missing "industry detail" → proxy "industry aggregate")
            alt-3: simulation-based validation when no real data
                   (synthetic data sweep, clearly flagged as theoretical)

Step 3: For each alternative path, run falsification (Phase 2.5) lightweight:
        → does alt-k survive the same failure mode that weakened the primary?
        → score: survives = 1.0; weakened = 0.5; falsified = 0.0

Step 4: Compute hedge uplift:
        hedge_score = max(primary_score, alt-1_survival, alt-2_survival, alt-3_survival)
        improvement = hedge_score - primary_score
        → If improvement ≥ 0.2: adopt the surviving alternative path; re-run downstream phases on it
        → If improvement < 0.2: all alternatives weak too; flag as "no alternative path; fundamental grounding limit"

Step 5: Re-run Phase 6/10 on the alternative path; recompute A or D dimension
        → Expected lift: A or D component score rises by improvement
        → TDAL joint uplift: T × ΔD × A × L (or T × D × ΔA × L)

Step 6: Frame the claim as "disjunctive":
        "The conclusion holds under at least one of {primary, alt-k}. Primary path faces [failure mode]; alternative path alt-k survives via [alternative assumption]."
        → This is NOT inflation — it is honest scope expansion. The paper MUST enumerate the alternatives and which survived.
```

**Worked example (D weak)**:

```
Problem: causal effect of minimum wage on employment
Phase 10 TDAL: D = 0.5×0.3 + 0.3×0.5 + 0.2×0.0 = 0.300 (ouroboros found CPS partly available, oss check DATA_LIMITED, theory-only false)
weakest_dimension = data_availability, T = 0.85 STRONG, A = 0.80 STRONG, L = 0.755
joint = 0.85 × 0.30 × 0.80 × 0.755 = 0.154 → UNSUPPORTED

Mechanism 2 Step 2: alternative datasets
    alt-1: PSID (Panel Study of Income Dynamics) — survives (different panel, has employment + wage)
    alt-2: ACS (American Community Survey) — survives (cross-sectional, larger N but no panel)
    alt-3: synthetic data sweep — survives (clearly flagged as theoretical validation only)

Step 3: alt-1 survival = 1.0, alt-2 = 0.7 (no panel = weaker causal identification), alt-3 = 0.5 (synthetic only)

Step 4: hedge_score = max(0.3, 1.0, 0.7, 0.5) = 1.0; improvement = 0.7 ≥ 0.2 → adopt alt-1 (PSID)

Step 5: re-run Phase 4/10 on PSID; Ouroboros called on PSID; new overall_score = 0.82
        D = 0.5×0.82 + 0.3×1.0 + 0.2×0.0 = 0.710
        joint = 0.85 × 0.710 × 0.80 × 0.755 = 0.364 → WEAK (still not publishable but lifted from UNSUPPORTED)

Step 6: paper frames: "CPS data was partly available (3 of 5 variables); we validated the identification strategy on PSID as an alternative panel. The causal estimate is grounded on PSID; CPS-specific replications are left to future work."

Continue to Mechanism 3 for further lift (0.364 → push toward MODERATE 0.5).
```

**Budget**: ≤ 3 rounds (one per alternative path; if all 3 alternatives fail, no further Mechanism 2 escalation — Mechanism 3 is the last lever).

### Mechanism 3: Progressive Verification (incremental T lift)

**Target**: TDAL `theoretical` (T) when full proof is too ambitious but partial proofs are achievable. **Last-resort lever** — invoked after Mechanism 1 exhausted AND Mechanism 2 cannot hedge.

**Logic**: Do NOT attempt to verify the entire theory at once. Verify the **core assumption** first → if it passes, the claim is "half-grounded" (≈ 60% landing per the v2.7路线图 estimate). Then incrementally verify extensions. Each increment lifts T by a discrete step.

**Workflow**:

```
Step 1: Decompose the theory into verification tiers:
        tier-0 (core): the assumption without which the entire theory collapses
        tier-1 (extension-1): first additional assumption required for the main result
        tier-2 (extension-2): second additional assumption
        tier-N (full): all assumptions; corresponds to the full claim

Step 2: Run Phase 6 on tier-0 alone:
        → SymPy on tier-0 premises only → target outcome
        → If tier-0 closes: record tier-0 grounded; ΔT = scope(tier-0) × weight
        → If tier-0 fails: the core is ungrounded; mechanism cannot help — escalate to BLOCK

Step 3: For each subsequent tier k (1, 2, ..., up to budget):
        → Add tier-k premises to the running set
        → Re-run Phase 6; if closes → tier-k grounded, ΔT += scope(tier-k) × weight
        → If fails at tier-k → stop progressive verification at tier-(k-1); record tier-k as conjectural

Step 4: Compute progressive T:
        T_progressive = Σ(tier-k grounded × scope(tier-k) × weight) for k = 0..K_grounded
        T_progressive replaces T in TDAL recomputation, but with a flag: "progressively verified to tier-K"

Step 5: Frame the claim as "progressively grounded":
        "We establish [tier-0 grounded] rigorously. We then extend to [tier-1 grounded] under [tier-1 assumption]. Beyond tier-K the result remains conjectural; the extensions are supported by numerical consistency but not symbolic proof."
        → Paper structure: Main theorem (tier-0) → Extension theorem (tier-1) → Conjecture (tier-K+1 and beyond)
```

**Worked example**:

```
Problem: stability of a numerical scheme for a class of PDEs
Phase 6 full proof FAIL — too many coupled assumptions.
Mechanism 1 exhausted (tightest assumption still leaves proof gap).
Mechanism 2 not applicable (this is T weak, not A/D).

Mechanism 3 Step 1: tiers
    tier-0 (core): scheme is stable for linear advection-diffusion (decoupled)
    tier-1: extends to nonlinear advection (semi-implicit treatment)
    tier-2: extends to coupled reaction-diffusion (full original claim)

Step 2: Phase 6 on tier-0 → SymPy PASS; T contribution = 0.6 × 1.0 = 0.6 (scope 0.6)
Step 3: Phase 6 on tier-1 → SymPy PARTIAL (needs one more assumption); T contribution = 0.2 × 0.5 = 0.1
        Phase 6 on tier-2 → SymPy FAIL; stop at tier-1; record tier-2 conjectural

Step 4: T_progressive = 0.6 + 0.1 = 0.7
        TDAL joint = 0.7 × 0.725 × 0.80 × 0.755 = 0.306 → WEAK (lifted from UNSUPPORTED 0.0)

Step 5: paper:
    Main Theorem (tier-0): "We prove stability for linear advection-diffusion."
    Extension Theorem (tier-1): "We extend stability to nonlinear advection under [assumption]."
    Conjecture (tier-2): "We conjecture extension to coupled reaction-diffusion; supported by numerical experiments but not symbolically proven."
```

**Budget**: ≤ 3 tiers (tier-0 + tier-1 + tier-2). Tier-0 failure → immediate BLOCK (core ungrounded). Tier-3+ → out of budget; the result is what it is.

## Uplift Loop Bounding

The three mechanisms form a **bounded uplift loop** — not infinite polish:

```
Phase 10 emits TDAL verdict
    ↓
verdict ≤ WEAK → invoke uplift
    ↓
Round 1: Mechanism 1 (Assumption Strength) — tightens T
    ↓ re-run Phase 6 + Phase 10 → recompute TDAL
    → STRONG/MODERATE: stop, success
    → still WEAK: Round 2
    ↓
Round 2: Mechanism 2 (Alternative Path) — hedges A or D
    ↓ re-run Phase 4/6/10 on alternative → recompute TDAL
    → STRONG/MODERATE: stop, success
    → still WEAK: Round 3
    ↓
Round 3: Mechanism 3 (Progressive Verification) — incremental T
    ↓ re-run Phase 6 progressively → recompute TDAL
    → STRONG/MODERATE: stop, success
    → still WEAK/UNSUPPORTED: STOP — record final TDAL, escalate to human
    ↓
Human checkpoint: human may waive further (the 3-round cap is hard; only human can waive)
                  OR accept WEAK verdict with paper framed as "preliminary"
                  OR pivot to a different idea (Phase 2 survivor)
```

**Budget cross-mechanism**: 3 rounds total (one per mechanism), NOT 3 per mechanism. Mechanism 1's internal budget (3 blocking assumptions) is the per-round sub-budget; the macro uplift loop is 3 rounds across mechanisms.

**Hard floor**: UNSUPPORTED after Round 3 → BLOCK paper-writing. The uplift cannot drag UNSUPPORTED to STRONG by sheer retry — if all three mechanisms fail to lift past WEAK, the claim is genuinely not publishable and the human must decide.

## Output Schema

`refine-logs/confidence-uplift-plan.json` (emitted before Round 1, updated each round):

```json
{
  "uplift_plan": {
    "schema_version": "1.0",
    "invoked_at": "ISO-8601",
    "trigger_verdict": "one of: WEAK | UNSUPPORTED | MODERATE",
    "initial_tdal": {},
    "weakest_dimension": "one of: theoretical | data_availability | domain_adaptation | literature_support",
    "rounds": [
      {
        "round": 1,
        "mechanism": "assumption_strength",
        "target_dimension": "theoretical",
        "actions": [
          {
            "assumption_id": "A1",
            "current_strength": "weak",
            "variant_s": "operator is compact + contraction",
            "variant_s_proof": "PASS",
            "scope_score": 0.7,
            "adopted": true
          }
        ],
        "tdal_after": {},
        "verdict_after": "MODERATE",
        "stopped": true
      }
    ],
    "final_tdal": {},
    "final_verdict": "MODERATE",
    "total_uplift": "+0.20",
    "human_waived": false,
    "escalated_to_human": false
  }
}
```

## Boundaries

- **Uplift is not inflation.** Every lifted dimension MUST have a corresponding scope caveat or alternative-path enumeration in the paper. Lifting T by tightening assumptions reduces scope — the paper MUST say so. Lifting D by alternative dataset — the paper MUST cite the alternative, not the primary. Lifting T progressively — the paper MUST distinguish theorem vs extension vs conjecture.
- **The 3-round cross-mechanism cap is hard.** No silent retry past Round 3. Only the human can waive — and a waiver is logged in `human_waived: true` with the waiving reason.
- **UNSUPPORTED after Round 3 → BLOCK.** No amount of uplift drags UNSUPPORTED to publishable. The mechanisms raise the *confidence*; they do not fabricate evidence.
- **Mechanism order is fixed (1 → 2 → 3).** Mechanism 1 is cheapest (re-run Phase 6 only); Mechanism 2 re-runs Phase 4 too; Mechanism 3 re-runs Phase 6 multiple times. Escalate cost monotonically.
- **Mixed mechanisms NEVER combine within one round.** Round 1 is Mechanism 1 only; Round 2 is Mechanism 2 only; Round 3 is Mechanism 3 only. This keeps the audit trail legible.
- **Literature Support (L) dimension is NOT upliftable directly.** L weak means the literature does not support the claim — the only fix is more retrieval (Phase 4 rerun) or reframing. The uplift mechanisms target T/A/D; L weakness triggers a Phase 4 rerun flag, not an uplift mechanism.
- **The uplift is auditable.** `confidence-uplift-plan.json` is a required artifact; Phase 14 (`/auto-review-loop`) reads it to check whether the uplift was honest (scope caveats present in paper) or inflated (scope caveats missing).

## When NOT to invoke uplift

| Condition | Action |
|-----------|--------|
| verdict = STRONG | Skip uplift entirely — nothing to improve |
| verdict = MODERATE but TDAL already surfaced in paper with caveats | Skip — MODERATE is publishable; only invoke if user requests "push to STRONG" |
| verdict = UNSUPPORTED and weakest_dimension = `literature_support` | Skip uplift; trigger Phase 4 literature rerun instead |
| verdict = UNSUPPORTED and Mechanism 1 Round 1 confirms tier-0/core ungrounded | Skip Rounds 2/3 — BLOCK immediately, the core is broken |
| User manually declines uplift | Honor the decline; log in `human_waived: true`; surface the un-lifted TDAL to paper |

## See Also

- [`domain-adaptation-contract.md`](domain-adaptation-contract.md) — TDAL 4-dim schema (what uplift raises)
- [`../support/result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — Phase 10 producer of TDAL (uplift trigger)
- [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) — Phase 6 (re-run by Mechanism 1 and 3)
- [`../meta-skills/universal-retrieval/SKILL.md`](../meta-skills/universal-retrieval/SKILL.md) — Phase 4 (re-run by Mechanism 2 alternative-path)
- [`../support/adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — Phase 2.5 (alternative path survival check)
- [`../orchestrator/125-problems-pipeline/SKILL.md`](../orchestrator/125-problems-pipeline/SKILL.md) — uplift loop integration into the 20-phase pipeline
