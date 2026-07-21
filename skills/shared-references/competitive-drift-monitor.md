# Competitive Drift Monitor (SciForge-OSS — automated competitor tracking)

> **Status (v2.8 — long-term L3)**: Defines the **automated recurring mechanism** that keeps [`competitive-analysis.md`](competitive-analysis.md) (v2.5 static snapshot) current against the moving target of competitor frameworks (AutoML-for-science, AI-Scientist clones, paper generators). v2.5 took a static comparison; v2.8 schedules recurring drift checks, flags when a competitor closes (or overturns) an OSS differentiator, and triggers a structured update PR — without requiring OSS core team to manually re-survey.
>
> **Core principle**: competitive advantage decays. Every quarter, a competitor could close one of OSS's 4 differentiators (domain adaptation / fantasy prevention / landing confidence / graceful degradation). The drift monitor detects this decay EARLY and triggers update before the differentiator is lost. Static "we lead" claims without monitoring are themselves a form of fantasy.

## Quick Reference

- **Purpose**: 自动定期监测竞品，发现 OSS 差异化优势被追平/反转时触发更新 PR
- **Input**: scheduled trigger (quarterly) + competitor framework release notes / benchmarks / papers
- **Output**: `refine-logs/competitive-drift-report-<YYYYQQ>.json` + update PR if any differentiator decayed
- **Invocation**: quarterly cron OR manual `/competitive-drift-monitor` invoke
- **Key**: 不是"再写一份竞品对比"；是"检测上一次对比的差异点是否仍成立，不成立的触发更新"

## The 4 Differentiators Under Monitor

OSS claims 4 differentiators over competitors (from [`competitive-analysis.md`](competitive-analysis.md) § 一、核心差异化优势):

| # | Differentiator | Failure mode if lost |
|---|----------------|----------------------|
| 1 | **Domain adaptation** — signature-driven auto-adapt vs competitors' manual config | If a competitor ships domain auto-adapt, OSS loses the "唯一实现" claim; reframe to "first implementation" or "broadest evidence-type coverage" |
| 2 | **Fantasy prevention** — 5-gate detection system | If a competitor ships hallucination gating, OSS loses the "独家" claim; reframe to "strictest" or "most-bounded" |
| 3 | **Landing confidence** — TDAL 4-dim joint vs competitors' pass/fail | If a competitor ships multi-dim confidence, OSS loses the "唯一" claim; reframe to "only product-form joint" or "strictest threshold" |
| 4 | **Graceful degradation** — adaptive mode (v2.8 M3) vs competitors' all-or-nothing | If a competitor ships phase degradation, OSS loses the "领先" claim; reframe to "first signature-driven" or "most granular" |

**Each differentiator has a `decay_state`**: `STILL_LEADING` / `CLOSING` / `PARITY` / `OVERTAKEN`. The monitor's job is to compute the state quarterly and trigger update PR when state transitions off `STILL_LEADING`.

## Drift Check Workflow (per quarterly run)

```
Step 1: Load previous snapshot
  → Read the latest competitive-drift-report-<prev QQ>.json
  → If absent (first run): bootstrap from competitive-analysis.md v2.5 snapshot
  → Extract the 4 differentiators + their last-known decay_state + the evidence that justified it

Step 2: Survey competitor releases since last snapshot
  → For each tracked competitor (list below), fetch:
       - release notes / changelog since last snapshot date
       - any published benchmarks or papers
       - any blog posts announcing new features
  → Use /universal-retrieval (Phase 4 meta-skill) for the literature scan
  → Output: competitor-activity-summary.json (per-competitor list of changes)

Step 3: For each of the 4 differentiators, assess decay_state transition
  → Compare OSS's current capability (this is FIXED — OSS v2.8 features) against the competitor activity
  → Apply the transition rubric (below)
  → Output: per-differentiator decay_state + evidence citation

Step 4: Emit competitive-drift-report-<YYYYQQ>.json
  → Full machine-readable report (schema below)
  → AND a human-readable competitive-drift-report-<YYYYQQ>.md summary

Step 5: Trigger update PR if ANY decay_state transitioned off STILL_LEADING
  → Open PR per the Update PR Contract (below)
  → PR updates competitive-analysis.md + bumps the "last reviewed" timestamp
  → If NO transition: log "no drift; OSS still leads on all 4" and close the run

Step 6: Special escalation — if a differentiator transitioned to OVERTAKEN
  → NOT just a competitive-analysis.md update — trigger a strategic review
  → Open issue (not PR) tagged `strategic-risk` for core team prioritization
  → The differentiator may need an OSS counter-feature, not just a reframe
```

## Transition Rubric (locked)

For each differentiator, decay_state transitions are judged against specific evidence:

### Differentiator 1: Domain adaptation

| Competitor signal | Transition |
|-------------------|------------|
| Competitor still requires manual domain config (no change) | `STILL_LEADING` (no transition) |
| Competitor ships "domain templates" but still manual selection | `STILL_LEADING` (no transition; templates ≠ auto-adapt) |
| Competitor ships "domain auto-detect" but only for 1-2 disciplines | `CLOSING` (partial close; OSS covers all evidence_types) |
| Competitor ships "domain auto-detect" for ≥ 3 disciplines with runtime classification | `PARITY` (match on auto-detect; OSS still leads on evidence_type breadth) |
| Competitor ships signature-driven auto-adapt matching OSS's evidence_type alphabet | `OVERTAKEN` (full match; OSS needs new differentiator OR reframe to "first" / "broadest") |

### Differentiator 2: Fantasy prevention

| Competitor signal | Transition |
|-------------------|------------|
| Competitor has no hallucination gating (no change) | `STILL_LEADING` |
| Competitor ships "citation check" (1 gate) | `STILL_LEADING` (OSS has 5 gates) |
| Competitor ships 2-3 gates (citation + logic + maybe novelty) | `CLOSING` |
| Competitor ships 4+ gates including logic + citation + falsifiability | `PARITY` |
| Competitor ships 5+ gates with bounded retry anti-deadloop | `OVERTAKEN` |

### Differentiator 3: Landing confidence (TDAL)

| Competitor signal | Transition |
|-------------------|------------|
| Competitor uses pass/fail binary verdict (no change) | `STILL_LEADING` |
| Competitor ships "confidence score" (single dimension) | `STILL_LEADING` (OSS has 4-dim TDAL) |
| Competitor ships 2-3 dim confidence (e.g., theory + data) | `CLOSING` |
| Competitor ships 4-dim confidence with product formula | `PARITY` |
| Competitor ships > 4-dim or adaptive-dim confidence | `OVERTAKEN` |

### Differentiator 4: Graceful degradation

| Competitor signal | Transition |
|-------------------|------------|
| Competitor uses all-or-nothing pipeline (no change) | `STILL_LEADING` |
| Competitor ships OPTIONAL phases but manual mode | `STILL_LEADING` (OSS v2.8 M3 is signature-driven) |
| Competitor ships CONDITIONAL phases with some auto-detection | `CLOSING` |
| Competitor ships signature-driven mode adaptation | `PARITY` |
| Competitor ships self-repairing pipeline (auto-reroute on phase fail beyond degradation) | `OVERTAKEN` |

## Tracked Competitors (curated list)

| Competitor | Type | Tracking source |
|------------|------|-----------------|
| AI-Scientist (Sakana AI) | Full-loop AI scientist | GitHub releases + arXiv papers |
| ChemCrow / BioCrow | Domain-specific agent | GitHub releases |
| Eureka (NVIDIA) | ML-only research agent | GitHub + blog |
| Paper Bench / PaperQA | Paper generator | GitHub + benchmarks |
| OpenResearch / Devon | General coding agent crossover | GitHub releases |
| Novel competitors | TBD | `/universal-retrieval` scan for "AI scientist" / "automated research" papers since last snapshot |

**The list is not exhaustive** — Step 2's `/universal-retrieval` scan catches novel competitors publishing since the last snapshot. Any new competitor found is added to the list for the next run.

## Report Schema (machine-readable)

`refine-logs/competitive-drift-report-<YYYYQQ>.json`:

```json
{
  "drift_report": {
    "schema_version": "1.0",
    "period": "2026Q3",
    "generated_at": "ISO-8601",
    "previous_snapshot": "competitive-drift-report-2026Q2.json",
    "differentiators": [
      {
        "id": 1,
        "name": "domain_adaptation",
        "previous_state": "STILL_LEADING",
        "current_state": "CLOSING",
        "transition": "STILL_LEADING → CLOSING",
        "evidence": "AI-Scientist v3.2 ships 'domain auto-detect' for ML and chemistry only",
        "evidence_url": "https://github.com/SakanaAI/AI-Scientist/releases/v3.2",
        "oss_still_leads_on": "evidence_type breadth (OSS covers 6; competitor covers 2)",
        "action": "UPDATE_PR",
        "reframe": "From 'only implementation' to 'broadest evidence-type coverage (6 vs 2)'"
      },
      {
        "id": 2,
        "name": "fantasy_prevention",
        "previous_state": "STILL_LEADING",
        "current_state": "STILL_LEADING",
        "transition": "no transition",
        "evidence": "no competitor shipped new gates since 2026Q2",
        "action": "NO_ACTION"
      },
      {
        "id": 3,
        "name": "landing_confidence",
        "previous_state": "STILL_LEADING",
        "current_state": "STILL_LEADING",
        "transition": "no transition",
        "evidence": "competitors still use pass/fail or single-dim score",
        "action": "NO_ACTION"
      },
      {
        "id": 4,
        "name": "graceful_degradation",
        "previous_state": "STILL_LEADING",
        "current_state": "STILL_LEADING",
        "transition": "no transition",
        "evidence": "no competitor shipped degradation mechanism",
        "action": "NO_ACTION"
      }
    ],
    "competitor_activity": [
      {
        "competitor": "AI-Scientist",
        "version": "v3.2",
        "release_date": "2026-08-15",
        "notable_changes": ["domain auto-detect (ML + chemistry)", "improved citation check"]
      },
      {
        "competitor": "Paper Bench",
        "version": "v2.0",
        "release_date": "2026-09-01",
        "notable_changes": ["added 2-dim confidence (theory + data)"]
      }
    ],
    "novel_competitors_found": [],
    "pr_triggered": true,
    "pr_url": "https://github.com/atomgit/SciForge-OSS/pull/42",
    "strategic_risk_escalated": false
  }
}
```

## Update PR Contract

When Step 5 triggers an update PR (any differentiator transitioned off `STILL_LEADING`), the PR MUST:

1. **Update `competitive-analysis.md`** — reframe the decayed differentiator per the `reframe` field; update the comparison table with the new competitor signals; bump the "last reviewed" timestamp at the top of the file.
2. **Cite evidence** — every transition claim in the PR body links to the competitor release notes / paper / benchmark URL. No vague "competitor caught up".
3. **Preserve historical framing** — the previous "OSS leads" claim becomes "OSS led until YYYYQQ; competitor closed in YYYYQQ; OSS still leads on [specific sub-axis]". Honesty about lost ground builds credibility; silently rewriting history breaks it.
4. **NOT invent new differentiators** in the update PR — new differentiators come from OSS feature work (separate PRs), not from competitive-analysis.md edits. The PR only reframes; it does not move goalposts.
5. **Escalate OVERTAKEN to strategic issue** — if any differentiator hit `OVERTAKEN`, the PR body MUST link to a new GitHub issue tagged `strategic-risk` for core team prioritization. The PR reframes; the issue decides whether to counter-build.

**PR SLA**: same as [`domain-contribution-protocol.md`](domain-contribution-protocol.md) — 14-day core team review, 30-day revise window, reject if evidence missing.

## Scheduling

The monitor runs **quarterly** (Q1/Q2/Q3/Q4, first Monday of the quarter). Two invocation paths:

1. **Automated**: cron-style trigger invoking `/competitive-drift-monitor` — emits the report + opens PR if triggered. The PR is DRAFT until core team approves (automated triggers do NOT auto-merge).
2. **Manual**: core team invokes `/competitive-drift-monitor` when a notable competitor release is observed mid-quarter (e.g., Sakana AI ships a major version). Bypasses the schedule; same workflow.

**The automated trigger is the default** — the monitor is NOT a "when we remember" mechanism. v2.5's static competitive-analysis.md became stale precisely because it was not scheduled; v2.8 fixes this by making the recurring run the default.

## Fallback / Edge Cases

| Condition | Action |
|-----------|--------|
| Previous snapshot absent (first run) | Bootstrap from `competitive-analysis.md` v2.5; treat all 4 differentiators as `previous_state: STILL_LEADING` (per the v2.5 claims); assess current_state from competitor activity since v2.5's timestamp |
| `/universal-retrieval` fails (network error) | Use cached competitor release notes from GitHub API (if configured); emit report with `competitor_activity: []` and `confidence: low`; do NOT trigger PR on a blind run |
| Competitor source unavailable (repo deleted / access revoked) | Log `"competitor_unreachable": "<name>"` in the report; skip that competitor for this run; flag for core team to update the tracked list |
| All 4 differentiators `STILL_LEADING` | Emit report with `pr_triggered: false`; close the run; log "no drift; OSS still leads on all 4" — this is the success case, not a failure |
| 2+ differentiators transitioned in one run | Open ONE PR updating all of them together (not 4 PRs); the PR body has a section per differentiator for legible review |
| OVERTAKEN on 2+ differentiators in one run | Escalate as a single strategic-risk issue (not 2); the issue summarizes the combined threat — multiple simultaneous overtakes may indicate a competitor convergence that requires strategic response, not incremental reframes |

## Boundaries

- **The monitor does NOT move goalposts.** It reframes existing differentiators honestly; it does not invent new differentiators to maintain a "we lead" claim. Inventing new differentiators in the update PR is a rejectable offense — new differentiators come from OSS feature work, not competitive-analysis.md edits.
- **The monitor does NOT auto-merge.** Automated triggers open DRAFT PRs; core team review is required. This prevents stale-evidence PRs from silently rewriting competitive claims.
- **Historical honesty is non-negotiable.** "OSS led until YYYYQQ; competitor closed in YYYYQQ; OSS still leads on [sub-axis]" is the required framing — silently rewriting "OSS leads" to "OSS still leads" without acknowledging the close is a rejectable offense.
- **OVERTAKEN escalates to strategic issue, NOT just reframe.** A reframe ("OSS still leads on sub-axis") is honest when the competitor matched but did not exceed; OVERTAKEN means the competitor exceeded, which requires counter-build consideration, not just a reframe.
- **The monitor is itself subject to fantasy prevention.** If `/universal-retrieval` returns no competitor activity for 4 consecutive quarters, that is suspicious — competitors DO release. Log `"suspicious_quiet": true` and flag for core team to manually verify the retrieval is working (do NOT silently report "all STILL_LEADING" on a blind retrieval).
- **The monitor is recurring, not one-shot.** v2.5's failure was treating competitive analysis as a snapshot; v2.8 makes it a quarterly heartbeat. Skipping runs (other than for documented OSS hibernation) is a process failure — the monitor's value is in EARLY drift detection, which erodes if runs are skipped.

## Why this is "automated" monitoring

The protocol is automated in three senses:

1. **Scheduled trigger** — quarterly cron, not "when we remember". The default is recurrence.
2. **Structured workflow** — Steps 1-6 are mechanical; the human judgment is limited to Step 3's decay_state assessment and Step 5's PR review. The retrieval, diff, and PR-skeleton generation are automatable.
3. **Machine-readable reports** — `competitive-drift-report-<YYYYQQ>.json` is structured; the next run reads it as `previous_snapshot`. This makes the monitor cumulative (each run builds on the last) rather than re-surveying from scratch.

The protocol is **not** automated in the sense of auto-merge or auto-reframe — core team review gates every PR. The balance: automated detection, human judgment on response.

## See Also

- [`competitive-analysis.md`](competitive-analysis.md) — v2.5 static snapshot; this L3 monitor keeps it current
- [`domain-contribution-protocol.md`](domain-contribution-protocol.md) — PR SLA contract reused here (14-day review, 30-day revise)
- [`../meta-skills/universal-retrieval/SKILL.md`](../meta-skills/universal-retrieval/SKILL.md) — Phase 4 retrieval (Step 2 competitor scan uses this)
- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — pipeline integration (the monitor is OUTSIDE the 20-phase; it's a recurring meta-process)
- [`../CONTRIBUTING.md`](../../CONTRIBUTING.md) — repo-wide contribution guide (this file is the competitive-monitoring supplement)
