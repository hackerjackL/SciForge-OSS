---
name: auto-review-loop
version: 1.3.2
description: "Iterative self-review (review→fix→re-review) with role-switch + v3.2 Phase B.2 domain-expert blind-spot review (wired into explicit ordered chain A→B.1→B.2→C) + kill-argument anti-self-deception. v3.4 STOP CONDITION uses effective_score=min(Phase C raw, B.2 cap) — a fatal blind-spot caps at 5, blocks false 'ready'. Writes BLINDSPOT_CHECK.json. Phase 14. Invoke to improve the draft until score≥6 or MAX_ROUNDS."
type: reference-skill
role: autonomous-review-loop-orchestrator
---

# Auto Review Loop (SciForge-OSS — Structured Self-Review Mode)

## Quick Reference

- **Purpose**: automated iterative review loop (review → fix → re-review) using role-switch self-review
- **Input**: research artifacts (derivation_output.md + CLAIMS_FROM_RESULTS.md)
- **Output**: AUTO_REVIEW.md + REVIEW_STATE.json + updated artifacts
- **Key**: single-agent role switching (researcher → reviewer → defender → adjudicator); round cap 3; fidelity gate

> **Status**: Autonomous iterative improvement via structured self-review. **OSS uses single-agent self-review** — the same agent switches roles between "researcher" and "senior reviewer" to provide adversarial critique. There is no external cross-model reviewer requirement. **OSS is discipline-agnostic** — only the universal `senior-reviewer-agnostic` persona is active. No statistical gatekeeping (economics p-value), no SOTA gate (cs-ml), no PNV chain integrity (physics). Copied from main SciForge and adapted to OSS's single-agent architecture.
>
> **v3.2 — Domain-expert blind-spot pass (content-quality fix)**: a single-LLM self-review has a systematic blind spot: the same model family tends to miss the *same class* of domain-specific failure on every pass (e.g. an LLM reviewing a causal-inference paper reliably under-checks instrument validity; reviewing a PDE paper reliably under-checks boundary conditions). A real domain-expert reviewer would special-case these. v3.2 adds a **Domain-Expert Blind-Spot Review** sub-step (see §Domain-Expert Blind-Spot Pass below) that uses [`domain-failure-modes.md`](../../shared-references/domain-failure-modes.md) as a **forced checklist** keyed off the domain signature's `evidence_type` — the agent must explicitly check each known failure mode for its domain and mark it checked/NA/unresolved, independent of the general score-based review. This catches the class of weaknesses that the generic LLM reviewer structurally under-weights, and is the single biggest content-quality lever for reaching a senior-researcher-usable draft.

## Use When

Use this skill when the user wants autonomous iterative improvement of research work via structured self-review.

Typical prompts:
- "Auto review loop"
- "Review until it passes"
- "Autonomous iterative improvement"
- "Iterate review → fix → re-review until ready"
- "auto review loop"
- "Keep reviewing until score is good enough"

## Job

Autonomously iterate: review → implement fixes → re-review, until the structured self-review gives a positive assessment (score ≥ 6/10) or MAX_ROUNDS is reached. The non-negotiable goal: **never hide weaknesses to game a positive score — implement fixes BEFORE re-reviewing, document everything, and exhaust multiple solution paths before conceding any reviewer concern.**

## Required Workspace

Create or maintain a workspace named `.sciforge/audits/` for all review outputs. Create the directory if it does not exist.

Key artifacts produced:
- `.sciforge/audits/AUTO_REVIEW.md` — cumulative review log
- `.sciforge/verdicts/REVIEW_STATE.json` — checkpoint state for recovery
- `.sciforge/audits/REVIEWER_MEMORY.md` — reviewer's persistent memory (hard / nightmare only)
- `CLAIMS_FROM_RESULTS.md` — generated at termination via `/result-to-claim` (if available)

Key artifacts consumed (read from upstream):
- `derivations/{problem_id}/derivation_output.md` — derivation results summary produced by `/theory-derivation` (primary input)
- `CLAIMS_FROM_RESULTS.md` — validated claims from `/result-to-claim`
- `findings.md` — prior findings (compact mode)
- `refine-logs/FINAL_PROPOSAL.md` — pre-registered primary outcomes (for fidelity gatekeeping)

## Configuration

These knobs shape loop behavior. Treat them as defaults; the user may override any of them in natural language. See [`shared-references/skill-config.md`](../../shared-references/skill-config.md) for centralized knob definitions.

- **Max rounds** — 4. Stop after 4 rounds even if not positive.
- **Positive threshold** — score ≥ 6/10, or verdict contains "accept", "sufficient", "ready for submission".
- **Reasoning effort** — always maximum (`xhigh`).
- **Self-review difficulty** (default: medium) — controls how adversarial the self-review is:
  - `medium`: standard structured self-review. The agent reads the artifacts and applies a structured review checklist.
  - `hard`: adds **Reviewer Memory** (the agent tracks its own previous suspicions across rounds) + **Debate Protocol** (the agent rebuts its own review points).
  - `nightmare`: everything in `hard` + the agent independently re-derives the key claims from scratch (cannot trust its own prior work) + **Adversarial Verification** (the agent independently checks if derivations match claims).
- **Human checkpoint** (default: off) — when on, pause after each round's review to let the user see the score and provide custom modification instructions before fixes are implemented. When off, the loop runs fully autonomously.
- **Compact** (default: off) — when on, read compact files (`findings.md`) instead of parsing full logs on session recovery, and append key findings to `findings.md` after each round.
- **Fidelity gatekeeping** (default: on) — enforce the 3-fidelity ladder requirements before allowing positive assessment. Blocks overclaiming on qualitative-only results. See [`/result-to-claim`](../result-to-claim/SKILL.md) for the ladder.
- **Fidelity threshold** — `numerical` (default). A primary claim must reach at least numerical fidelity for a positive assessment. Configurable to `symbolic` (stricter) or `qualitative` (lenient).
- **HTML render** (default: on) — auto-render `.sciforge/audits/AUTO_REVIEW.md` to HTML on loop termination. Non-blocking: if rendering fails, log and continue.

**Nightmare + manual reviewer incompatibility**: If difficulty is `nightmare`, the agent must have access to the derivation scripts and raw numerical outputs. If only summary text is available, STOP with: "difficulty: nightmare requires the agent to independently re-derive key claims from raw artifacts. Use difficulty: hard, or provide access to derivation scripts."

## State Persistence (Compact Recovery)

Long-running loops may hit the context window limit, triggering automatic compaction. To survive this, persist state to `.sciforge/verdicts/REVIEW_STATE.json` after each round.

State fields:
- `round` — current round number
- `threadId` — reviewer thread ID for round continuity
- `status` — `in_progress` / `completed`
- `difficulty` — `medium` / `hard` / `nightmare`
- `last_score` — most recent score
- `last_verdict` — most recent verdict
- `pending_derivations` — list of derivations still running
- `timestamp` — ISO 8601

**Write this file at the end of every Phase E** (after documenting the round). Overwrite each time — only the latest state matters.

**On completion** (positive assessment or max rounds), set `status: completed` so future invocations don't accidentally resume a finished loop.

## Output Protocols
> **v5.2 verdict artifact location**: all machine-readable verdict/hash/audit JSON produced by this skill goes into `.sciforge/verdicts/` (filenames: see the artifact directory layout in [`output-protocol.md`](../../shared-references/output-protocol.md); narrative reports stay in their original stage directory).


> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Workflow

### Initialization

1. **Check for `.sciforge/verdicts/REVIEW_STATE.json`** (fall back to `./REVIEW_STATE.json` for legacy projects):
   - If neither path exists: **fresh start**.
   - If it exists AND `status` is `completed`: **fresh start** (previous loop finished normally).
   - If it exists AND `status` is `in_progress` AND `timestamp` is older than 24 hours: **fresh start** (stale state from a killed / abandoned run — delete the file and start over).
   - If it exists AND `status` is `in_progress` AND `timestamp` is within 24 hours: **resume**.
     - Read the state file to recover `round`, `threadId`, `last_score`, `pending_derivations`.
     - Read `.sciforge/audits/AUTO_REVIEW.md` to restore full context of prior rounds.
     - If `pending_derivations` is non-empty, check if they have completed.
     - Resume from the next round (round = saved round + 1).
     - Log: "Recovered from context compaction. Resuming at Round N."
2. Read project narrative documents, memory files, and any prior review documents. **When `COMPACT = true` and compact files exist**: read `findings.md` instead of full `.sciforge/audits/AUTO_REVIEW.md` and raw logs — saves context window.
3. Read recent derivation results (check `derivations/{problem_id}/`).
4. Identify current weaknesses and open TODOs from prior reviews.
5. Initialize round counter = 1 (unless recovered from state file).
6. Create / update `.sciforge/audits/AUTO_REVIEW.md` with header and timestamp.

### Loop (repeat up to MAX_ROUNDS)

**The per-round execution order is FIXED and top-to-bottom — the agent MUST execute Phase A → Phase B.1 → Phase B.2 → Phase C → Phase D in this exact sequence each round. Skipping any phase (especially the buried B.2 sub-step) is a contract violation. The round's final score is `effective_score = min(Phase A raw score, B.2 cap)` (see STOP CONDITION).**

1. **Phase A — Structured Self-Review** (generic 6-axis checklist, produces raw score + weakness list)
2. **Phase B.1 — Fidelity Gate** (3-fidelity ladder on primary outcomes)
3. **Phase B.2 — Domain-Expert Blind-Spot Review** (v3.2, MANDATORY — see below; produces `BLINDSPOT_CHECK.json` + score cap)
4. **Phase B.5/B.6** (only if difficulty ≥ hard — memory + debate)
5. **Phase C — Implement Fixes** (merge Phase A weaknesses + B.2 unresolved blind-spots into one fix list)
6. **Phase D — Wait for background derivations** (if any dispatched)

> **v3.2 hard-wiring note (the runtime bug this fixes)**: in the prior structure, Phase B.2 was a **buried subsection** between B.1 and B.5 — the agent read the numbered Phase A→B.1→B.5→C chain and **silently skipped B.2** because it was not in the explicit execution list. Two real test runs (Q-HARM-001 theory, Q-SGD-BS-GAP computational) confirmed this: both produced `.sciforge/audits/AUTO_REVIEW.md` + the review ledger but **NO `BLINDSPOT_CHECK.json`** — Phase B.2 never ran, yet `.sciforge/PIPELINE_STATUS.md` claimed "all 8 blind-spot items passed" with zero backing artifact. This is the same orphan-artifact bug class as the v3.2 frontier gap. The fix is structural: B.2 is now step 3 of the explicit ordered loop, not a buried subsection. The `BLINDSPOT_CHECK.json` file is the load-bearing evidence — a round that completes without writing it is invalid regardless of the score it claims.

#### Phase A: Structured Self-Review

**Role switching (OSS — universal):** The agent switches its own role from "researcher" to "senior reviewer". The `{reviewer_persona}` is always `senior-reviewer-agnostic` — applied to every problem. There is no discipline-specific persona.

**Structured Review Checklist** (applied by the agent in reviewer role):

The agent re-reads all research artifacts (derivation output, claims, verification reports) and applies the following checklist systematically:

1. **Technical Correctness** — Are the derivations mathematically sound? Are all assumptions stated? Are there hidden gaps?
2. **Logical Structure** — Does the argument flow coherently? Are there logical jumps?
3. **Completeness** — Are all necessary components present? Are boundary cases considered?
4. **Claim-Evidence Match** — Does every claim have supporting evidence (derivation, verification, or citation)?
5. **Scope Calibration** — Is the claim scope appropriate for the evidence scope?
6. **Fidelity Gate** — Are primary outcomes at ≥ numerical fidelity? (See Phase B.1)

**Output format:**

```text
## Self-Review Report — Round N/MAX_ROUNDS

### Score: X/10

### Verdict: ready / almost / not ready

### Critical Weaknesses (ranked by severity)
1. [Weakness] — [location] — [minimum fix]
2. ...

### Minor Issues
1. [Issue] — [location] — [suggested fix]

### Strengths
1. [Strength]
2. ...

### Self-Reviewer Notes
[Free-form commentary, suspicions, what to track next round]
```

**Key rule**: The agent must re-read the artifacts from scratch — do NOT rely on memory of having written them. If in doubt, re-read the source files.

##### Hard — Structured Self-Review + Reviewer Memory

Same as medium, but **prepend Reviewer Memory** to the self-review:

```text
## Self-Review Report — Round N/MAX_ROUNDS

### Reviewer Memory (persistent across rounds)
[Paste full contents of REVIEWER_MEMORY.md here]

IMPORTANT: You have memory from prior rounds. Check whether your
previous suspicions were genuinely addressed or merely sidestepped.
Be skeptical of convenient omissions in your own work.

### Score: X/10
### Verdict: ready / almost / not ready
### Critical Weaknesses (ranked by severity)
...
### Memory Update
List any new suspicions, unresolved concerns, or patterns to track.
```

##### Nightmare — Independent Re-Derivation

The agent independently re-derives the key claims from scratch, without looking at its own prior derivation scripts. Then compares the results.

**Prompt**: Same as hard, but add:
```
## Independent Re-Derivation
Before scoring, independently re-derive the key claim(s) from first principles.
Do NOT look at your prior derivation scripts. Write fresh SymPy code.
Then compare the new result with the original. Report ANY discrepancy.
```

**Key difference**: In nightmare mode, the agent cannot trust its own prior work — it must re-derive from scratch. This catches unconscious assumptions and hidden errors.

#### Phase B: Parse Assessment

**CRITICAL: Save the FULL self-review output** verbatim. Do NOT discard or summarize — the raw text is the primary record.

Then extract structured fields:
- **Score** (numeric 1-10)
- **Verdict** ("ready" / "almost" / "not ready")
- **Action items** (ranked list of fixes)

**LOOP-COMPLETION DISCIPLINE (v1.4.0 — anti-premature-surrender)**: one invocation of this skill covers the ENTIRE loop: rounds continue until the STOP CONDITION fires OR MAX_ROUNDS (default 4) is exhausted. Ending the loop after an early round with `effective_score < 6` while rounds remain is a CONTRACT VIOLATION (premature surrender — the CRUX shadow evaluation's agents declared "I'm done" with hours and budget still on the clock; the structural interceptor treats an under-budget `not_ready` finalization the same way: the next boundary or the eval gate rejects it). A low round score means FIX AND RE-REVIEW, not finalize.

**STOP CONDITION**: If `effective_score >= 6` AND verdict contains "ready" or "almost" → stop loop, document final state. **v3.2 — `effective_score` not raw score**: the score used for the stop condition is the **min of (Phase C raw score, B.2 cap)**, NOT the raw Phase C score alone. A raw 7/10 that hides a fatal unresolved domain blind-spot (B.2 cap = 5) is `effective_score = 5` → does NOT stop, must fix the blind-spot first. This closes the gap where the generic Phase C review could declare "ready" while a fatal endogeneity / boundary-condition / straw-man failure (B.2) was never addressed.

**Anti-Shrinkage Protocol (v5.1 — from CRUX shadow-evaluation failure mode #2)**:

**Background** (arXiv:2607.27191): over a dozen rounds of self-review and external review never produced a single accept, yet the agent's response strategy was always **narrowing conclusions, adding disclaimers, switching to softer phrasing** — "when facing criticism it only knows how to 'shrink', never how to 'change'". Many fatal flaws later flagged by human experts had already been written up by AI reviews, yet never triggered a real change.

**Mandatory rules** (activate when `effective_score` fails to improve for ≥2 consecutive rounds, or the verdict is reject-class for ≥2 consecutive rounds):

1. **Wording-only fixes are forbidden as responses**: under consecutive-reject status the following actions do **not** count as fixes — adding disclaimers, softening claim wording, changing "we show" to "we suggest", shrinking claim scope, stacking caveats in Limitations. These are the signature death modes of the CRUX-experiment agents
2. **Only three substantive response classes are allowed** (written to the `response_class` field of `REVIEW_STATE.json`, mapped one-to-one to review concerns):

| Response class | Action | Destination |
|--------|------|------|
| **Experiment redesign** | review flags evidence gaps (underpowered / missing baseline / missing ablation) → back to `/experiment-execution` to run/rerun the missing entries of the mandatory experiment matrix | Phase 6 rollback |
| **PIVOT** | review flags a path-level method flaw → back to Phase 5 to swap method and re-register (budget inherits experiment-execution's PIVOT ≤2 cap) | Phase 5 rollback |
| **KILL** | review flags that the core assumption does not hold → `/kill-argument` kill argument → back to Phase 2 for a new idea | Phase 2 rollback |

3. **A round consisting solely of wording fixes is a FAIL**: if a round's entire fix list is wording-class (`response_class` all `wording`) → the round is invalid (`round_invalid: true`), does not consume MAX_ROUNDS budget but must be redone with a substantive response
4. **3 consecutive rounds without a substantive response** → forced KILL path (`/kill-argument`) — the endgame of "a dozen rounds of shrinking without changing" is not a paper, it is cutting losses
5. **Audit hook**: `REVIEW_STATE.json` records `response_class ∈ {experiment_redesign, pivot, kill, wording}` for every concern of every round; `/paper-writing` reads it — if the response_class of the last 2 rounds before the final draft is all `wording` → FAIL (`reason_code: shrinkage_only_response`)

#### Phase B.1: Fidelity Gatekeeping (Universal — replaces economics p-value gate and cs-ml SOTA gate)

**Apply the 3-fidelity ladder** to primary outcomes (see [`/result-to-claim`](../result-to-claim/SKILL.md) for the ladder):

1. **Read `refine-logs/FINAL_PROPOSAL.md`** to identify which outcomes are **pre-specified primary outcomes**. Outcomes not pre-specified are automatically classified as "secondary".

2. **Parse derivation/verification results** from `derivations/{problem_id}/` directory. For each outcome, determine:
   - Is it a **primary outcome** (pre-specified)? Or a **secondary outcome** (mechanism test, robustness check)?
   - What is its **fidelity level**? `symbolic` (full SymPy proof) / `numerical` (sanity check confirms) / `qualitative` (only "looks right")

3. **Apply fidelity gate (on PRIMARY outcomes only)**, using the configured `FIDELITY_THRESHOLD` (default: `numerical`):
   - Primary outcome at ≥ threshold fidelity → **SUPPORTS** positive assessment
   - Primary outcome below threshold fidelity → **BLOCKS** positive assessment — must reframe as "suggests" or "consistent with", NOT "supported" or "proven"
   - Qualitative-only primary outcomes → **REJECT** "supported"/"proven" claim language

4. **Handle secondary outcomes (NOT used in gate)**:
   - Secondary outcomes at any fidelity: report in mechanism/robustness section.
   - **NEVER** use secondary outcomes to reject a claim supported by primary outcomes.

5. **Enforce scope transparency**:
   - If the derivation only holds in a limited regime: MUST qualify the claim with the regime.
   - If a counterexample was found: MUST flag — the claim is falsified for that regime.

6. **Reframe claims based on PRIMARY outcome fidelity**:
   - All primary outcomes at ≥ threshold → "supported" / "proven" (if symbolic) — positive assessment ALLOWED
   - Some primary outcomes below threshold → "partial" — block positive assessment, reframe
   - All primary outcomes below threshold → "preliminary" / "suggests" — block positive assessment

**This gate is MANDATORY and cannot be skipped. The gate operates on PRIMARY outcomes (pre-specified) only, NOT on all outcomes.**

#### Phase B.2: Domain-Expert Blind-Spot Review (v3.2 — MANDATORY, all difficulties)

> **Why this exists (honest gap)**: a single-LLM self-review has a *systematic*, not random, blind spot — the same model family tends to under-check the *same class* of domain-specific failure on every pass. An LLM reviewing a causal-inference paper reliably under-checks instrument validity; reviewing a PDE paper reliably under-checks boundary conditions; reviewing an interpretive paper reliably under-checks straw-man. A *human* domain expert would special-case exactly these. The generic score-based review (Phase C) cannot fix this because it reviews against a universal checklist, not a domain-specific one. This phase closes that gap by forcing a **domain-specific failure-mode checklist** derived from the domain signature's `evidence_type`.

**Runs on EVERY round, all difficulties (medium/hard/nightmare) — it is NOT gated behind difficulty like Phase B.5/B.6.** This is the single biggest content-quality lever; it cannot be opt-in.

**Inputs**:
- `refine-logs/domain-signature.json` (from Phase 1b `/domain-learner`) — read `evidence_type` + `methodology_profile`
- [`domain-failure-modes.md`](../../shared-references/domain-failure-modes.md) — the canonical failure-mode catalog, keyed by `evidence_type`
- The research artifacts under review this round (`derivations/`, `CLAIMS_FROM_RESULTS.md`, `paper/sections/*.tex`)

**Procedure**:
1. **Select the failure-mode row** for this run's `evidence_type` from `domain-failure-modes.md`:
   - `causal_inference` → endogeneity / omitted_variable_bias / reverse_causality / selection_bias / measurement_error / simultaneity / attrition_bias / publication_bias
   - `experimental` → no_placebo / no_blinding / insufficient_power / multiple_testing / regression_to_mean / confounding_by_indication / lead_time_bias
   - `correlational` → spurious_correlation / ecological_fallacy / simpson_paradox / survivorship_bias / confirmation_bias
   - `derivational` → hidden_assumption / circular_reasoning / quantifier_error / division_by_zero / limit_order_error / dimensional_error / boundary_condition_error
   - `simulational` → numerical_instability / convergence_failure / discretization_error / parameter_tuning_bias / seed_dependence
   - `interpretive` → cherry_picking / anecdotal_evidence / straw_man / ad_hoc_hypothesis / equivocation
   - If the signature has a secondary `evidence_type` (e.g. `theory+experiment`), union the two rows.
2. **For each failure mode in the row**, the reviewer (still the same agent, fresh role switch per [`reviewer-independence.md`](../../shared-references/reviewer-independence.md)) must produce one of three verdicts, with **file:line evidence** for `unresolved`:
   - `checked_clear` — the artifacts explicitly address this failure mode (e.g. a DWH test for endogeneity is present and passes) → no action.
   - `not_applicable` — this failure mode does not apply to this problem (e.g. `no_placebo` for a pure-theory paper) → record the reason in one clause.
   - `unresolved` — the failure mode applies but the artifacts do NOT address it → **add to this round's fix list as a MAJOR (or CRITICAL if the failure-mode catalog marks it `fatal`)**, independent of the generic Phase C weakness list.
3. **Write `.sciforge/verdicts/BLINDSPOT_CHECK.json`** (v6.0: machine-readable verdict → verdicts/ directory; single fixed-name file **overwritten with the latest round** — a flat fixed-name file holds one JSON document, so per-round history is recorded in AUTO_REVIEW.md, not appended here):
   ```json
   {"round":N,"evidence_type":"<x>","failure_modes_checked":[
     {"mode":"endogeneity","verdict":"checked_clear","evidence":"methods/METHOD_REGISTRY.md:42 DWH p=0.31"},
     {"mode":"reverse_causality","verdict":"unresolved","evidence":"missing","severity":"fatal","added_to_fix_list":true},
     {"mode":"no_placebo","verdict":"not_applicable","reason":"pure theory, no treatment arm"}
   ],"unresolved_count":1,"fatal_unresolved":1}
   ```
4. **Severity propagation**: any `unresolved` failure mode whose catalog severity is `fatal` forces this round's review to **cap the top-level score at 5/10** (below the 6/10 positive threshold) regardless of how well the generic Phase C review scored it — a fatal domain blind spot is submission-blocking, and a 6+ score that hides a fatal endogeneity gap is dishonest. `severe` unresolved caps at 6; `checked_clear`/`not_applicable` impose no cap. The cap is recomputed each round; once the fix lands and the mode re-checks `checked_clear`, the cap lifts.

**Boundaries**:
- This phase is **additive to, not a replacement for**, Phase B.1 (fidelity gate) and Phase C (generic review). Run all three; the score is the min of (Phase C score, B.2 cap).
- The failure-mode row is **selected by `evidence_type` only** — never by a discipline label. No economics/physics hardcode.
- If `domain-signature.json` is missing (Phase 1b failed), this phase **WARNs and falls back to the `derivational` row** (the most general: hidden_assumption / circular_reasoning / quantifier_error) — it never silently skips. The WARN is recorded in `.sciforge/verdicts/BLINDSPOT_CHECK.json` (`fallback_reason: signature_missing`); when no fallback occurs, OMIT the `fallback_reason` key entirely (never write `null`).
- Failure modes LEARNED from `domain-signature.json` (beyond the catalog) are checked with severity `learned` — they impose NO score cap (caps belong to catalog severities only: fatal→5, severe→6), but every `unresolved` learned mode still joins the fix list.
- `unresolved` findings feed the fix list exactly like Phase C weaknesses — they are not informational-only. The loop must attempt a fix (bounded 2 solution paths before conceding, per the "Exhaust before surrendering" rule).
- A `fatal` unresolved that survives MAX_ROUNDS surfaces to the human as `BLOCKED, reason_code: unresolved_domain_blindspot_<mode>` — it is never self-waived.

#### Phase B.5: Self-Reviewer Memory Update (hard + nightmare only)

**Skip entirely if self-review difficulty is `medium`.**

After parsing the assessment, update `REVIEWER_MEMORY.md` in the project root:

```markdown
# Reviewer Memory

## Round 1 — Score: X/10
- **Suspicion**: [what the reviewer flagged]
- **Unresolved**: [concerns not yet addressed]
- **Patterns**: [recurring issues the reviewer noticed]

## Round 2 — Score: X/10
- **Previous suspicions addressed?**: [yes/no for each, with reviewer's judgment]
- **New suspicions**: [...]
- **Unresolved**: [carried forward + new]
```

**Rules**:
- Append each round, never delete prior rounds (audit trail).
- If the reviewer's response includes a "Memory update" section, copy it verbatim.
- This file is passed back to the reviewer in the next round's Phase A — it is the reviewer's persistent memory.

#### Phase B.6: Self-Debate Protocol (hard + nightmare only)

**Skip entirely if self-review difficulty is `medium`.**

After the self-review assessment, the agent switches role to "defender" and gets a chance to **rebut** its own review points.

**Step 1 — Agent as Defender:**

For each weakness the self-review identified, the agent writes a structured response:

```markdown
### Rebuttal to Weakness #1: [title]
- **Accept / Partially Accept / Reject**
- **Argument**: [why this criticism might be invalid, already addressed, or based on a misunderstanding]
- **Evidence**: [point to specific SymPy script, numerical check, or prior round fixes]
```

Rules for the defense:
- Must be honest — do NOT fabricate evidence or misrepresent derivations.
- Can point out factual errors in the self-review (misread proof, wrong metric, etc.).
- Can argue a weakness is out of scope or would require unreasonable effort.
- Maximum 3 rebuttals per round (pick the most impactful to contest).

**Step 2 — Agent as Adjudicator:**

Switch back to "adjudicator" role and rule on each rebuttal:

```
- SUSTAINED (defense is valid, withdraw this weakness)
- OVERRULED (original criticism stands, explain why)
- PARTIALLY SUSTAINED (revise the weakness to a narrower scope)
```

Then update the score if any weaknesses were withdrawn.

**Step 3 — Update score and action items** based on the ruling:
- SUSTAINED weaknesses: remove from action items.
- OVERRULED: keep as-is.
- PARTIALLY SUSTAINED: revise scope.

Append the full debate transcript to `.sciforge/audits/AUTO_REVIEW.md` under the round's entry.

#### Human Checkpoint (if enabled)

**Skip this step entirely if `HUMAN_CHECKPOINT = false`.**

When `HUMAN_CHECKPOINT = true`, present the review results and wait for user input:

```text
Round N/MAX_ROUNDS review complete.

Score: X/10 — [verdict]
Top weaknesses:
1. [weakness 1]
2. [weakness 2]
3. [weakness 3]

Suggested fixes:
1. [fix 1]
2. [fix 2]
3. [fix 3]

Options:
- Reply "go" or "continue" → implement all suggested fixes
- Reply with custom instructions → implement your modifications instead
- Reply "skip 2" → skip fix #2, implement the rest
- Reply "stop" → end the loop, document current state
```

Wait for the user's response. Parse their input:
- **Approval** ("go", "continue", "ok", "proceed"): proceed to Phase C with all suggested fixes.
- **Custom instructions** (any other text): treat as additional / replacement guidance for Phase C. Merge with reviewer suggestions where appropriate.
- **Skip specific fixes** ("skip 1,3"): remove those fixes from the action list.
- **Stop** ("stop", "enough", "done"): terminate the loop, jump to Termination.

#### Phase C: Implement Fixes (if not stopping)

For each action item (highest priority first):
1. **Derivation changes**: Write / modify SymPy scripts, attempt the symbolic proof for a qualitative-only outcome.
2. **Run numerical sanity checks**: Deploy to sandbox (CPU, Python), parameter sweeps, counterexample searches.
3. **Analysis**: Run verification, collect results, update figures / tables.
4. **Documentation**: Update project notes and review document.

Prioritization rules:
- Skip fixes requiring excessive compute (flag for manual follow-up).
- Skip fixes requiring external data not available.
- Prefer reframing / analysis over new derivations when both address the concern.
- Always implement fidelity upgrades (cheap, high impact — e.g., attempt the symbolic proof for a numerical-only outcome).

#### Phase D: Wait for Results

If derivations/checks were launched:
- Monitor running SymPy scripts / sandbox jobs for completion.
- Collect results from `derivations/{problem_id}/`.
- **Derivation quality check** — verify the SymPy chain completed without gaps; verify numerical sanity checks used independent parameters.

#### Phase E: Document Round

Append to `.sciforge/audits/AUTO_REVIEW.md`:

```markdown
## Round N (timestamp)

### Assessment (Summary)
- Score: X/10
- Verdict: [ready/almost/not ready]
- Key criticisms: [bullet list]

### Self-Review Raw Response

<details>
<summary>Click to expand full self-review response</summary>

[Paste the COMPLETE raw self-review output here — verbatim, unedited.
This is the authoritative record. Do NOT truncate or paraphrase.]

</details>

### Self-Debate Transcript (hard + nightmare only)

<details>
<summary>Click to expand debate</summary>

**Defense Argument:**
[paste rebuttal]

**Adjudicator Ruling:**
[paste ruling — SUSTAINED / OVERRULED / PARTIALLY SUSTAINED for each]

**Score adjustment**: X/10 → Y/10

</details>

### Actions Taken
- [what was implemented/changed]

### Results
- [derivation outcomes, if any]

### Status
- [continuing to round N+1 / stopping]
- Difficulty: [medium/hard/nightmare]
```

**Write `.sciforge/verdicts/REVIEW_STATE.json`** with current round, score, verdict, and any pending derivations.

**Append to `findings.md`** (when `COMPACT = true`): one-line entry per key finding this round:
```markdown
- [Round N] [positive/negative/unexpected]: [one-sentence finding] (fidelity: qualitative → numerical)
```

Increment round counter → go to Phase E.5.

#### Phase E.5: Write Review Ledger

After documenting each round, update `.sciforge/verdicts/REVIEW_LEDGER.json` (machine-readable verdict — it lives in the verdicts/ directory like every other machine-readable verdict, NOT in audits/). This is the authoritative machine-readable record for downstream skills (`/citation-audit`, `/paper-writing` Phase 0.5, external verifier `scripts/verifiers/verify_review_ledger.sh`).

**Format** (single JSON object, latest state overwrites — NOT a JSONL stream; the round history lives in `details.rounds[]`, schema: `schemas/REVIEW_LEDGER.schema.json`):

```json
{
  "audit_skill": "auto-review-loop",
  "verdict": "PASS",
  "reason_code": "score_above_threshold",
  "summary": "2 review rounds; final score 7 >= 6; loop finalized.",
  "generated_at": "2026-07-20T14:30:00Z",
  "details": {
    "rounds": [
      {
        "round": 1,
        "timestamp": "2026-07-20T14:30:00Z",
        "score": 5,
        "verdict": "almost",
        "phase": "documented",
        "key_criticisms": ["Missing symbolic proof for outcome O3", "No counterexample search for regime |λ|>1"],
        "action_items": ["Attempted SymPy proof for O3 (success)", "Ran counterexample sweep for |λ|>1 (none found)"],
        "statistical_gate": {"data_type": "synthetic", "status": "PASS"},
        "blockers_remaining": ["Full regime verification for |λ|>1"]
      },
      {
        "round": 2,
        "timestamp": "2026-07-20T15:10:00Z",
        "score": 7,
        "verdict": "ready",
        "phase": "finalized",
        "final_score": 7,
        "final_verdict": "ready",
        "total_rounds": 2
      }
    ]
  }
}
```

**Envelope fields**: `audit_skill` / top-level `verdict` (6-state: PASS/WARN/FAIL/NOT_APPLICABLE/BLOCKED/ERROR) / `reason_code` / `summary` / `generated_at` — rewritten at every update.

**Per-round fields** (each entry of `details.rounds[]`):
- `round` (int): round number (1-indexed)
- `timestamp` (string): ISO 8601 UTC
- `score` (number): reviewer score this round
- `verdict` (string): review-loop vocabulary `ready` / `almost` / `not_ready` (NOT the 6-state envelope vocabulary)
- `phase` (string): `documented` (work rounds) or `finalized` (the termination entry)
- `key_criticisms` (string[]): top reviewer concerns
- `action_items` (string[]): fixes implemented this round (documented rounds)
- `statistical_gate` (object, optional): `data_type` + gate status for empirical claims
- `blockers_remaining` (string[], optional): unresolved issues
- `fidelity_delta` (object, optional): fidelity level changes per outcome

At termination, append one final `details.rounds[]` entry with `phase: "finalized"` carrying `final_score`, `final_verdict`, and `total_rounds` (no `action_items` needed), and set the envelope's top-level `verdict`/`summary` accordingly.

### Termination

When loop ends (positive assessment or max rounds):
1. Update `.sciforge/verdicts/REVIEW_STATE.json` with `status: completed`.
2. Write final summary to `.sciforge/audits/AUTO_REVIEW.md`.
3. Update project notes with conclusions.
4. **Write method / derivation description** to `.sciforge/audits/AUTO_REVIEW.md` under a `## Method Description` section — a concise 1-2 paragraph description of the final derivation, its structure, and the verification chain. This serves as input for `/unified-plotting` in the figure generation phase.
5. **Generate claims from results** — invoke `/result-to-claim` to convert derivation results from `.sciforge/audits/AUTO_REVIEW.md` into structured paper claims. Output: `CLAIMS_FROM_RESULTS.md`. This bridges the review phase → paper-writing phase so `/paper-writing` can directly use validated claims. If `/result-to-claim` is not available, skip silently.
6. If stopped at max rounds without positive assessment:
   - List remaining blockers.
   - Estimate effort needed for each.
   - Suggest whether to continue manually or pivot.
7. **Render HTML view** (if `RENDER_HTML = true`, default): the agent renders the cumulative review log to HTML inline within the pipeline (if convenient; no `/render-html` in OSS). **Non-blocking**: if rendering fails, log the error and continue. Skip if `RENDER_HTML = false`.

## Boundaries

**Never**:
- Hide weaknesses to game a positive score. Honesty is non-negotiable.
- Promise to fix without implementing. Implement fixes BEFORE re-reviewing.
- Fabricate BibTeX or citations. Use the DBLP → CrossRef → `[VERIFY]` chain. Do NOT generate BibTeX from memory.
- Give up on a self-review concern after one attempt. **Exhaust before surrendering** — before marking any concern as "cannot address": (1) try at least 2 different solution paths, (2) for derivation issues, attempt a weaker version or an alternative argument, (3) for numerical issues, adjust parameters or try a different sanity check, (4) only then concede narrowly and bound the damage.
- Silently skip writing `.sciforge/verdicts/REVIEW_LEDGER.json` at termination — the ledger is mandatory regardless of outcome.
- Override a fidelity gate `BLOCK` with a positive top-level verdict — the gate is a hard override.

**Always**:
- Use maximum reasoning effort for every self-review call.
- Be honest — include negative results and failed derivations.
- If a derivation takes > 30 minutes, launch it and continue with other fixes while waiting.
- Document EVERYTHING — the review log should be self-contained.
- Update project notes after each round, not just at the end.
- Update `.sciforge/verdicts/REVIEW_LEDGER.json` at the end of every round (Phase E.5) and finalize at termination — the ledger is the authoritative machine-readable record for downstream skills.

## Output Shape

The final `.sciforge/audits/AUTO_REVIEW.md` contains:
1. **Header** — direction, date, max rounds, difficulty
2. **Round-by-round entries** — for each round: assessment summary, reviewer raw response (verbatim in `<details>`), debate transcript (if hard / nightmare), actions taken, results, status
3. **Final summary** — final score, verdict, remaining blockers (if any)
4. **Method Description** — concise 1-2 paragraph description of the final derivation for downstream paper illustration

`CLAIMS_FROM_RESULTS.md` (if generated at termination) contains structured paper claims validated by the loop's results.

## Structured Self-Review Template for Round 2+

For rounds 2+, the agent switches back to "senior reviewer" role and re-reads the updated artifacts:

```text
[Round N update]

Since your last self-review, the following fixes were implemented:
1. [Action 1]: [result]
2. [Action 2]: [result]
3. [Action 3]: [result]

Updated results table:
[paste fidelity levels per outcome]

Now, as senior reviewer, re-read the updated artifacts and re-assess:
1. Score this work 1-10 for a top venue
2. Were the remaining concerns from the previous round addressed?
3. Are there new weaknesses introduced by the fixes?
4. State clearly: is this READY for submission? Yes/No/Almost
```

## Self-Review Record Keeping

The self-review output is the primary record. No external routing or tracing is needed — the agent's own review process is self-contained.

## See Also

- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/reviewer-routing.md`](../../shared-references/reviewer-routing.md) — cross-model reviewer routing
- [`../shared-references/review-tracing.md`](../../shared-references/review-tracing.md) — forensic review trace policy
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — 3-fidelity claim gate (consumed at termination)
- [`../kill-argument/SKILL.md`](../kill-argument/SKILL.md) — anti-self-deception exercise; **R7: defined as an adversarial sub-step of this skill** (invoked at hard/nightmare difficulty for the executor's role-switch attack), not an independent parallel gate
