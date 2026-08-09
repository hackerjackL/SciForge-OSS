---
name: publishability-score
description: "Final publishability scoring across dim1-first-axis + multi-dim. Phase 15.5. Invoke after citation-audit for the go/no-go submission verdict."
type: support-skill
role: paper-publishability-assessor
version: 1.3.0
---
> **v5.2 verdict artifact location**: all machine-readable verdict/hash/audit JSON produced by this skill goes into `.sciforge/verdicts/` (filenames: see the artifact directory structure in [`output-protocol.md`](../../shared-references/output-protocol.md); narrative reports stay in their original stage directory).


# Publishability Score (SciForge-OSS — Final Paper Quality Assessment)

> **Status (v2.2)**: New support skill. The final paper-quality gate after Phase 14 (auto-review-loop) and Phase 15 (citation-audit). Produces a structured **publishability score** that tells the human whether the paper is (a) submission-ready, (b) "missing only some experiments" (the user's target — main experiments are in place, only cross/supplementary experiments needed), or (c) fundamentally flawed (main experiment logic NOT in place — supplementary experiments won't save it, "no mean").
>
> **Core principle (user mandate)**: "The PDFs and LaTeX we generate also need a final standalone score, because we must at least verify that our paper is, e.g., possibly publishable with only certain experiments missing. But when I say those experiments are missing, the main experiments must be solidly in place. If the experiment logic is not in place, then no amount of cross-experiments or supplementary experiments will mean anything. We do not do anything no-mean." → The score's **primary axis is "main-experiment-logic-in-place"**. If that fails, the paper is NOT publishable regardless of how many supplementary experiments could be added. Only when main-experiment-logic passes does the "missing-supplementary-experiments" verdict make sense.

## Quick Reference

- **Purpose**: give the final paper a structured publishability score
- **Input**: `paper/main.pdf` + `paper/main.tex` + `experiments/` + `.sciforge/audits/` + `.sciforge/audits/CLAIMS_FROM_RESULTS.md` + `.sciforge/PIPELINE_STATUS.md`
- **Output**: `.sciforge/verdicts/PUBLISHABILITY_SCORE.json` + `.sciforge/audits/PUBLISHABILITY_SCORE.md` (human-readable narrative)
- **Key**: 6-dimension scoring; **main-experiment-logic-in-place** is the primary axis; distinguish "missing supplementary experiments" vs "main logic not in place (no mean)"

## Use When

Invoke after Phase 16 (final assembly) completes, or when a human wants to assess the publishability of a finished paper.

Typical prompts:
- "score this paper"
- "is this publishable?"
- "assess publishability"
- "what experiments are missing?"

## Job

Read the paper + all experiment artifacts + audit reports; output a structured publishability score that tells the human explicitly:
1. Whether this paper is currently publishable (submission-ready)
2. If not publishable, whether it is "only missing supplementary experiments" (main experiments in place; supplementing suffices) or "main experiment logic not in place" (no amount of supplementing helps = no mean)
3. What exactly is missing (if "only missing supplementary experiments", list the missing supplementary/cross experiments)

Non-negotiable goals:
1. **Main-experiment-logic-in-place is the primary axis** — if main experiment logic FAILs, total score capped at 0.4 (regardless of how good the other dimensions are), and verdict = NOT_PUBLISHABLE_NO_MEAN (not "missing experiments" but "logic not in place")
2. **Scoring must be honest** — no inflation for appearances; a paper whose main experiment logic is not in place cannot PASS just because the writing is good
3. **Distinguish the two kinds of unpublishable** — "missing supplementary experiments" (SUPPLEMENTARY_GAPS) vs "main logic not in place" (MAIN_LOGIC_FAILURE); the human's next action is completely different for each
4. **Scores must be traceable** — every dimension score carries 1-2 sentences of rationale + evidence file paths

## The 6-Dimension Score

| Dimension | Weight | Full Score | What to Assess | FAIL Condition (0 for this dimension) |
|------|------|------|--------|----------------------|
| **1. Main-Experiment-Logic-in-Place** | **primary axis** | 1.0 | Do the main experiments answer the paper's core claim? Is the experiment design logically closed with the claim? Do the main results support the core conclusion? | Main experiments missing / main experiment design unrelated to the claim / main results contradict the core conclusion |
| 2. Theoretical Rigor | 0.15 | 1.0 | Are the derivations correct? Does symbolic/machine verification pass? Are the assumptions stated? | Fatal error in derivation / not machine-verified while the claim asserts machine verification |
| 3. Empirical Completeness | 0.20 | 1.0 | Are main experiments + ablations + robustness + baseline comparisons complete? Is there a SOTA comparison? | No ablation / no baseline / no robustness (but main logic in place → this is SUPPLEMENTARY_GAPS, not MAIN_LOGIC_FAILURE) |
| 4. Writing Quality | 0.15 | 1.0 | Structure clear? Claims supported? Citations real? Figures clear? Zero compile warnings? | Compile warnings unfixed / citations unverified / figures unreadable |
| 5. Novelty & Contribution | 0.15 | 1.0 | New contribution relative to existing literature? novelty-check PASS? Duplicate work avoided? | Duplicates existing work / novelty-check FAIL |
| 6. Reproducibility | 0.15 | 1.0 | Code/data/seed/hardware retained? Experiments re-runnable? Figures have render scripts? | No render script / no seed / cannot re-run |

**Weight notes**: dimension 1 is the primary axis (not counted in the 0.15 average; it gates instead); dimensions 2-6 are 0.15 each, summing to 0.75; the remaining 0.25 is modulated by dimension 1.

**v6.0 evidence-norm calibration**: the evidence-strength dimension is scored against the discipline's `evidence_norm_profile` (`.sciforge/refine-logs/domain-signature.json` — sample_size_norm / control_design_norm / effect_reporting_norm / negative_result_norm; wiring per `domain-signature-consumer.md`): claims meeting the exemplar-venue bar score full, each unmet norm deducts per the rubric, and `negative_result_norm` decides whether a negative-result framing is publishable as-is or must carry a power analysis. Unknown norm → conservative default bar + `evidence_norm_missing` note in the score report. Formula:
```
total = 0.25 * dim1 + 0.15*(dim2+dim3+dim4+dim5+dim6)   # if dim1=0 then total ≤ 0.25*0 + 0.75 = 0.75, but see the hard cap below
hard_cap_if_main_logic_fail: if dim1 == 0 → total capped at 0.4 (NOT_PUBLISHABLE_NO_MEAN), regardless of dim2-6
```

## Verdict Tiers

| Verdict | total Range | dim1 | Meaning | Human Next Step |
|---------|-----------|------|------|-----------|
| **SUBMISSION_READY** | ≥ 0.80 | ≥ 0.8 | Main experiment logic in place + all dimensions strong | Ready to submit (after adapting via venue-profiles) |
| **SUPPLEMENTARY_GAPS** | 0.55–0.79 | ≥ 0.7 | Main experiment logic in place, but missing some supplementary/cross experiments (dimension 3 < 0.8) | Add experiments per the missing list, then publishable |
| **NEEDS_MAJOR_REVISION** | 0.40–0.54 | ≥ 0.5 | Main experiment logic largely in place but needs major revision (design/baselines/ablations) | Major-revise the main experiments, then re-assess |
| **NOT_PUBLISHABLE_NO_MEAN** | ≤ 0.40 | < 0.5 | **Main experiment logic not in place** — supplementary experiments are meaningless | Do not add experiments; rethink the idea/experiment design |

**Key distinction**: `SUPPLEMENTARY_GAPS` (publishable, missing supplementary) vs `NOT_PUBLISHABLE_NO_MEAN` (not publishable, main logic not in place) imply completely different next steps for the human. The former says "add X experiments and it is publishable"; the latter says "no amount of added experiments helps — redesign". This is exactly the user's emphasis: "do not do anything no-mean".

## Workflow

### Step 1: Load All Artifacts

Read:
- `paper/main.pdf` + `paper/main.tex` + `paper/sections/*.tex` (the paper itself)
- `paper/COMPILE_REPORT.json` (compile status, zero warnings?)
- `experiments/toy/RESULT.json` + `experiments/full/STATUS.json` + `experiments/full/EXPERIMENT_RESULTS.json` (experiment results)
- `CLAIMS_FROM_RESULTS.md` (claim gating, repo root)
- `.sciforge/audits/LOGIC_VERIFICATION.json` + `.sciforge/audits/LEAKAGE_AUDIT.json` (logic/leakage audit)
- `.sciforge/audits/REVIEW_REPORT.md` + `.sciforge/audits/KILL_ARGUMENT.md` (Phase 14 review)
- `literature/FILTER_CHAIN_AUDIT.json` (literature chain)
- `.sciforge/refine-logs/FINAL_PROPOSAL.md` (core claim freeze)
- `.sciforge/PIPELINE_STATUS.md` (pipeline execution report)

### Step 2: Score Dimension 1 (Main-Experiment-Logic) — GATING

This is the primary axis; score it first. Answer 4 sub-questions (each yes=0.25):
1. **Do the main experiments exist?** — `experiments/` has toy PASS + full completed? (`theory-only` path: the derivation is the "main experiment"; assess whether the derivation answers the claim)
2. **Does the main experiment design answer the core claim?** — Do the experiment's success_criteria align with the core claim in `FINAL_PROPOSAL.md`? Not measuring an unrelated metric?
3. **Do the main results support the core conclusion?** — Do the data direction + significance in `RESULT.json`/`EXPERIMENT_RESULTS.json` align with the paper's core conclusion? (toy PASS + full agree = strong support; toy PASS + full disagree = weak support)
4. **Is the experiment logic closed (claim→design→results→conclusion, no leaps)?** — Does every claim in `CLAIMS_FROM_RESULTS.md` have experimental evidence + no FATAL/CRITICAL in `LOGIC_VERIFICATION.json`?

dim1 = sum(yes) * 0.25. **If dim1 < 0.5 → verdict = NOT_PUBLISHABLE_NO_MEAN directly, skip to Step 4 (skipping detailed dim2-6 scoring is acceptable, due to the hard cap).**

### Step 3: Score Dimensions 2-6

- **dim2 theoretical rigor**: `derivation_output.md` machine verification PASS? `verification_report.md`? Assumptions `premises.md` stated? → 0/0.5/1.0
- **dim3 empirical completeness**: main experiments ✓ + ablation? + robustness? + baseline comparisons? + SOTA? (-0.2 per missing item, min 0) → note: low dim3 but high dim1 = SUPPLEMENTARY_GAPS
- **dim4 writing quality**: `COMPILE_REPORT.json` zero warnings? All citations verified (`FILTER_CHAIN_AUDIT.json` PASS)? Figures readable (Nature floor)? Structure clear? → 0.25 each
- **dim5 novelty**: `novelty_report.json` PASS? `KILL_ARGUMENT.md` not killed? New contribution relative to `landscape_report.md`? → 0/0.5/1.0
- **dim6 reproducibility**: `render.py`/`spec.d2` retained? Seed stated? `input_data.json` retained? Full experiment re-runnable? → 0.25 each

### Step 4: Compute Total + Verdict

```
total = 0.25*dim1 + 0.15*(dim2+dim3+dim4+dim5+dim6)
if dim1 < 0.5: total = min(total, 0.4); verdict = NOT_PUBLISHABLE_NO_MEAN
elif dim3 < 0.8 and dim1 >= 0.7 and total < 0.8: verdict = SUPPLEMENTARY_GAPS
elif total >= 0.80: verdict = SUBMISSION_READY
elif total >= 0.55: verdict = SUPPLEMENTARY_GAPS  (main logic OK, some gaps)
elif total >= 0.40: verdict = NEEDS_MAJOR_REVISION
else: verdict = NOT_PUBLISHABLE_NO_MEAN
```

### Step 5: Missing-Experiments Manifest (if SUPPLEMENTARY_GAPS)

If verdict = SUPPLEMENTARY_GAPS, list the missing supplementary/cross experiments (the most useful output for the human):
- **Ablation experiment** (if dim3 lacks ablation): remove component X, verify Y drops
- **Robustness experiment** (if missing): different seeds/configs/data subsets
- **Baseline comparison** (if missing): compare against [specific baseline] from `landscape_report.md`
- **SOTA comparison** (if missing): compare against [specific SOTA]
- **Cross experiment** (if applicable): cross-domain/cross-dataset validation of generalization
- **Statistical significance** (if missing): more seeds + confidence intervals

Tag each item with `priority: high|medium|low` + `estimated_effort: hours`. This is the human's actionable list.

### Step 6: Output

Write `PUBLISHABILITY_SCORE.json` + `PUBLISHABILITY_SCORE.md` (human-readable). Place under `output/`.

## Output Schema (`PUBLISHABILITY_SCORE.json`)

```json
{
  "q_id": "...",
  "scored_at": "ISO-8601",
  "verdict": "SUBMISSION_READY | SUPPLEMENTARY_GAPS | NEEDS_MAJOR_REVISION | NOT_PUBLISHABLE_NO_MEAN",
  "total_score": 0.72,
  "dimensions": {
    "main_experiment_logic": {"score": 1.0, "rationale": "...", "evidence": ["experiments/full/EXPERIMENT_RESULTS.json", "CLAIMS_FROM_RESULTS.md"]},
    "theoretical_rigor": {"score": 0.9, "rationale": "...", "evidence": ["derivations/.../verification_report.md"]},
    "empirical_completeness": {"score": 0.4, "rationale": "main experiments✓ ablation✗ robustness✗ baselines✗", "evidence": ["experiments/"]},
    "writing_quality": {"score": 0.9, "rationale": "zero warnings✓ citations✓", "evidence": ["paper/COMPILE_REPORT.json"]},
    "novelty_contribution": {"score": 0.8, "rationale": "...", "evidence": [".sciforge/refine-logs/novelty_report.json"]},
    "reproducibility": {"score": 0.9, "rationale": "render.py✓ seed42✓", "evidence": ["figures/"]}
  },
  "main_logic_gating": {"dim1_score": 1.0, "gating_triggered": false, "cap_applied": null},
  "missing_experiments": [
    {"type": "ablation", "description": "remove the label-smoothing term, verify val-loss rises", "priority": "high", "estimated_effort_hours": 4},
    {"type": "baseline", "description": "compare against standard CE baseline (partially done)", "priority": "high", "estimated_effort_hours": 2},
    {"type": "robustness", "description": "5 seeds + CI", "priority": "medium", "estimated_effort_hours": 6}
  ],
  "human_next_action": "submit after adding the 3 supplementary experiments (~12 hours total); main experiment logic already in place",
  "benchmark_ready": false,
  "notes": "..."
}
```

## Boundaries

- **Main-experiment-logic-in-place is the primary axis (hard cap)**. dim1 < 0.5 → total score hard-capped at 0.4 + verdict = NOT_PUBLISHABLE_NO_MEAN. Not raised by good writing/complete citations.
- **Honest scoring**. No inflation for appearances. A paper whose main experiment logic is not in place is no-mean no matter how good the writing.
- **Distinguish the verdicts**. SUPPLEMENTARY_GAPS (missing supplementary, publishable) vs NOT_PUBLISHABLE_NO_MEAN (main logic not in place, adding experiments meaningless) — this is the most useful distinction for the human.
- **Missing-experiments list must be actionable**. Each item has type/description/priority/effort; the human can execute it directly.
- **Does not replace Phase 14 auto-review-loop**. This skill is the final score after Phase 14; it consumes Phase 14's `REVIEW_REPORT.md` as input for dim4/dim5.
- **benchmark-ready flag**. The user will later chase benchmark leaderboards — `benchmark_ready: true` only when verdict = SUBMISSION_READY and dim1=1.0 and dim3≥0.8.

## See Also

- [`../orchestrator/auto-pipeline/SKILL.md`](../../orchestrator/auto-pipeline/SKILL.md) — Phase 16 invokes this skill
- [`../auto-review-loop/SKILL.md`](../auto-review-loop/SKILL.md) — Phase 14; this skill consumes its output
- [`../citation-audit/SKILL.md`](../citation-audit/SKILL.md) — Phase 15; this skill consumes its output
- [`../../shared-references/project-architecture-contract.md`](../../shared-references/project-architecture-contract.md) — `output/` directory structure
