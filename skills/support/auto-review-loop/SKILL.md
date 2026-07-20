---
name: auto-review-loop
type: reference-skill
role: autonomous-review-loop-orchestrator
---

# Auto Review Loop (SciForge-OSS — Discipline-Agnostic)

> **Status**: Autonomous iterative improvement via a cross-model reviewer. **OSS is discipline-agnostic** — there is no economics persona / no cs-ml persona / no physics persona. Only the universal `senior-reviewer-agnostic` persona is active. No statistical gatekeeping (economics p-value), no SOTA gate (cs-ml), no PNV chain integrity (physics). Copied from main SciForge and trimmed to OSS's single-row design.

## Use When

Use this skill when the user wants autonomous iterative improvement of research work via a cross-model reviewer.

Typical prompts:
- "Auto review loop"
- "Review until it passes"
- "Autonomous iterative improvement"
- "Iterate review → fix → re-review until ready"
- "自动评审循环"
- "Keep reviewing until score is good enough"

## Job

Autonomously iterate: review → implement fixes → re-review, until the external reviewer gives a positive assessment (score ≥ 6/10) or MAX_ROUNDS is reached. The non-negotiable goal: **never hide weaknesses to game a positive score — implement fixes BEFORE re-reviewing, document everything, and exhaust multiple solution paths before conceding any reviewer concern.**

## Required Workspace

Create or maintain a workspace named `review-stage/` for all review outputs. Create the directory if it does not exist.

Key artifacts produced:
- `review-stage/AUTO_REVIEW.md` — cumulative review log
- `review-stage/REVIEW_STATE.json` — checkpoint state for recovery
- `review-stage/REVIEWER_MEMORY.md` — reviewer's persistent memory (hard / nightmare only)
- `CLAIMS_FROM_RESULTS.md` — generated at termination via `/result-to-claim` (if available)

Key artifacts consumed (read from upstream):
- `refine-logs/DERIVATION_RESULTS.md` — derivation results summary produced by `/theory-derivation` (primary input)
- `findings.md` — prior findings (compact mode)
- `refine-logs/DERIVATION_PLAN.md` — pre-registered primary outcomes (for fidelity gatekeeping)

## Configuration

These knobs shape loop behavior. Treat them as defaults; the user may override any of them in natural language. See [`shared-references/skill-config.md`](../shared-references/skill-config.md) for centralized knob definitions.

- **Max rounds** — 4. Stop after 4 rounds even if not positive.
- **Positive threshold** — score ≥ 6/10, or verdict contains "accept", "sufficient", "ready for submission".
- **External reviewer model** — the cross-model reviewer used for review. Should be a different model family from the host agent.
- **Reasoning effort** — always maximum (`xhigh`).
- **Reviewer difficulty** (default: medium) — controls how adversarial the reviewer is:
  - `medium`: standard cross-model review. The host agent controls what context the reviewer sees.
  - `hard`: adds **Reviewer Memory** (the reviewer tracks its own suspicions across rounds) + **Debate Protocol** (the host agent can rebut, the reviewer rules).
  - `nightmare`: everything in `hard` + the external reviewer reads the repo directly (the host agent cannot filter what the reviewer sees) + **Adversarial Verification** (the reviewer independently checks if derivations match claims).
- **Human checkpoint** (default: off) — when on, pause after each round's review to let the user see the score and provide custom modification instructions before fixes are implemented. When off, the loop runs fully autonomously.
- **Compact** (default: off) — when on, read compact files (`findings.md`) instead of parsing full logs on session recovery, and append key findings to `findings.md` after each round.
- **Fidelity gatekeeping** (default: on) — enforce the 3-fidelity ladder requirements before allowing positive assessment. Blocks overclaiming on qualitative-only results. See [`/result-to-claim`](../result-to-claim/SKILL.md) for the ladder.
- **Fidelity threshold** — `numerical` (default). A primary claim must reach at least numerical fidelity for a positive assessment. Configurable to `symbolic` (stricter) or `qualitative` (lenient).
- **HTML render** (default: on) — auto-render `review-stage/AUTO_REVIEW.md` to HTML on loop termination. Non-blocking: if rendering fails, log and continue.

**Nightmare + manual reviewer incompatibility**: If the reviewer backend is `manual` and difficulty is `nightmare`, STOP with: "difficulty: nightmare requires the external reviewer to read the repo directly and is not compatible with manual reviewer. Use difficulty: hard, or switch to a backend that supports repo access."

## State Persistence (Compact Recovery)

Long-running loops may hit the context window limit, triggering automatic compaction. To survive this, persist state to `review-stage/REVIEW_STATE.json` after each round.

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

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Workflow

### Initialization

1. **Check for `review-stage/REVIEW_STATE.json`** (fall back to `./REVIEW_STATE.json` for legacy projects):
   - If neither path exists: **fresh start**.
   - If it exists AND `status` is `completed`: **fresh start** (previous loop finished normally).
   - If it exists AND `status` is `in_progress` AND `timestamp` is older than 24 hours: **fresh start** (stale state from a killed / abandoned run — delete the file and start over).
   - If it exists AND `status` is `in_progress` AND `timestamp` is within 24 hours: **resume**.
     - Read the state file to recover `round`, `threadId`, `last_score`, `pending_derivations`.
     - Read `review-stage/AUTO_REVIEW.md` to restore full context of prior rounds.
     - If `pending_derivations` is non-empty, check if they have completed.
     - Resume from the next round (round = saved round + 1).
     - Log: "Recovered from context compaction. Resuming at Round N."
2. Read project narrative documents, memory files, and any prior review documents. **When `COMPACT = true` and compact files exist**: read `findings.md` instead of full `review-stage/AUTO_REVIEW.md` and raw logs — saves context window.
3. Read recent derivation results (check `results/sympy/`, `results/sandbox/`).
4. Identify current weaknesses and open TODOs from prior reviews.
5. Initialize round counter = 1 (unless recovered from state file).
6. Create / update `review-stage/AUTO_REVIEW.md` with header and timestamp.

### Loop (repeat up to MAX_ROUNDS)

#### Phase A: Review

**Persona resolution (OSS — universal):** The `{reviewer_persona}` and `{venue_level}` placeholders in the prompt templates below are resolved as follows. OSS has **one** persona — `senior-reviewer-agnostic` — applied to every 125-problem run. There is no DISCIPLINE_CONTEXT table (main SciForge switches between senior-econ-editor / senior-ml-reviewer / senior-physics-editor / senior-reviewer-agnostic).

| OSS (always) | reviewer_persona | venue_level |
|--------------|------------------|-------------|
| `general` | senior-reviewer-agnostic | mixed top venues across all domains + arXiv |

**Never** switch to a discipline-specific persona. OSS is discipline-agnostic by design.

##### Medium (default) — Standard Cross-Model Review

Send comprehensive context to the external reviewer with maximum reasoning effort.

Prompt content:
```text
[Round N/MAX_ROUNDS of autonomous review loop]

[Full research context: frozen Q-id, claims, derivation chain, numerical sanity checks, known weaknesses]
[Changes since last round, if any]

Please act as a senior-reviewer-agnostic (mixed top venues across all domains + arXiv level).

1. Score this work 1-10 for a top venue
2. List remaining critical weaknesses (ranked by severity)
3. For each weakness, specify the MINIMUM fix (additional derivation, numerical check, or reframing)
4. State clearly: is this READY for submission? Yes/No/Almost

Be brutally honest. If the work is ready, say so clearly.
```

If this is round 2+, send the follow-up on the same reviewer thread (reusing the saved thread ID).

##### Hard — Cross-Model Review + Reviewer Memory

Same as medium, but **prepend Reviewer Memory** to the prompt.

Prompt content:
```text
[Round N/MAX_ROUNDS of autonomous review loop]

## Your Reviewer Memory (persistent across rounds)
[Paste full contents of REVIEWER_MEMORY.md here]

IMPORTANT: You have memory from prior rounds. Check whether your
previous suspicions were genuinely addressed or merely sidestepped.
The author (host agent) controls what context you see — be skeptical
of convenient omissions.

[Full research context, changes since last round...]

Please act as a senior-reviewer-agnostic (mixed top venues level).
1. Score this work 1-10 for a top venue
2. List remaining critical weaknesses (ranked by severity)
3. For each weakness, specify the MINIMUM fix
4. State clearly: is this READY for submission? Yes/No/Almost
5. Memory update: List any new suspicions, unresolved concerns,
   or patterns you want to track in future rounds.

Be brutally honest. Actively look for things the author might be hiding.
```

##### Nightmare — External Reviewer Reads Repo Directly

The external reviewer autonomously reads the repository. The host agent does NOT control what the reviewer sees — the reviewer explores freely.

Prompt content:
```text
You are an adversarial senior-reviewer-agnostic (mixed top venues level).
This is Round N/MAX_ROUNDS of an autonomous review loop.

## Your Reviewer Memory (persistent across rounds)
[Paste full contents of REVIEWER_MEMORY.md]

## Instructions
You have FULL READ ACCESS to this repository. The author (host agent) does NOT
control what you see — explore freely. Your job is to find problems the
author might hide or downplay.

DO THE FOLLOWING:
1. Read the SymPy derivation scripts, numerical sanity check results (JSON/CSV), and logs YOURSELF
2. Verify that reported theorems match what's actually proven in the sympy logs
3. Check if numerical sanity checks use parameters independent from the symbolic proof's assumptions (not circular)
4. Look for cherry-picked regimes, missing counterexample searches, or suspicious parameter choices
5. Read NARRATIVE_REPORT.md or review-stage/AUTO_REVIEW.md for the author's claims — then verify each against code

OUTPUT FORMAT:
- Score: X/10
- Verdict: ready / almost / not ready
- Verified claims: [which claims you independently confirmed]
- Unverified/false claims: [which claims don't match the derivations or results]
- Weaknesses (ranked): [with MINIMUM fix for each]
- Memory update: [new suspicions and patterns to track next round]

Be adversarial. Trust nothing the author tells you — verify everything yourself.
```

**Key difference**: In nightmare mode, the external reviewer independently reads SymPy scripts, result files, and logs. The host agent cannot filter or curate what the reviewer sees. This is the closest analog to a real hostile reviewer who reads your actual paper + supplementary materials.

#### Phase B: Parse Assessment

**CRITICAL: Save the FULL raw response** from the external reviewer verbatim. Do NOT discard or summarize — the raw text is the primary record.

Then extract structured fields:
- **Score** (numeric 1-10)
- **Verdict** ("ready" / "almost" / "not ready")
- **Action items** (ranked list of fixes)

**STOP CONDITION**: If score >= 6 AND verdict contains "ready" or "almost" → stop loop, document final state.

#### Phase B.1: Fidelity Gatekeeping (Universal — replaces economics p-value gate and cs-ml SOTA gate)

**Apply the 3-fidelity ladder** to primary outcomes (see [`/result-to-claim`](../result-to-claim/SKILL.md) for the ladder):

1. **Read `refine-logs/DERIVATION_PLAN.md`** to identify which outcomes are **pre-specified primary outcomes**. Outcomes not pre-specified are automatically classified as "secondary".

2. **Parse derivation/verification results** from `results/` directory. For each outcome, determine:
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

#### Phase B.5: Reviewer Memory Update (hard + nightmare only)

**Skip entirely if reviewer difficulty is `medium`.**

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

#### Phase B.6: Debate Protocol (hard + nightmare only)

**Skip entirely if reviewer difficulty is `medium`.**

After parsing the review, the host agent gets a chance to **rebut**.

**Step 1 — Host Agent Rebuttal:**

For each weakness the reviewer identified, the host agent writes a structured response:

```markdown
### Rebuttal to Weakness #1: [title]
- **Accept / Partially Accept / Reject**
- **Argument**: [why this criticism is invalid, already addressed, or based on a misunderstanding]
- **Evidence**: [point to specific SymPy script, numerical check, or prior round fixes]
```

Rules for the host agent's rebuttal:
- Must be honest — do NOT fabricate evidence or misrepresent derivations.
- Can point out factual errors in the review (reviewer misread proof, wrong metric, etc.).
- Can argue a weakness is out of scope or would require unreasonable effort.
- Maximum 3 rebuttals per round (pick the most impactful to contest).

**Step 2 — Reviewer Rules on Rebuttal:**

Send the host agent's rebuttal back to the reviewer (on the same thread) for a ruling.

Prompt content:
```text
The author rebuts your review:

[paste host agent's rebuttal]

For each rebuttal, rule:
- SUSTAINED (author's argument is valid, withdraw this weakness)
- OVERRULED (your original criticism stands, explain why)
- PARTIALLY SUSTAINED (revise the weakness to a narrower scope)

Then update your score if any weaknesses were withdrawn.
```

For nightmare mode, the reviewer independently verifies the host agent's evidence claims — reads the SymPy scripts / result files referenced. Does NOT take the host agent's word for it.

**Step 3 — Update score and action items** based on the ruling:
- SUSTAINED weaknesses: remove from action items.
- OVERRULED: keep as-is.
- PARTIALLY SUSTAINED: revise scope.

Append the full debate transcript to `review-stage/AUTO_REVIEW.md` under the round's entry.

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
- Collect results from `results/sympy/` and `results/sandbox/`.
- **Derivation quality check** — verify the SymPy chain completed without gaps; verify numerical sanity checks used independent parameters.

#### Phase E: Document Round

Append to `review-stage/AUTO_REVIEW.md`:

```markdown
## Round N (timestamp)

### Assessment (Summary)
- Score: X/10
- Verdict: [ready/almost/not ready]
- Key criticisms: [bullet list]

### Reviewer Raw Response

<details>
<summary>Click to expand full reviewer response</summary>

[Paste the COMPLETE raw response from the external reviewer here — verbatim, unedited.
This is the authoritative record. Do NOT truncate or paraphrase.]

</details>

### Debate Transcript (hard + nightmare only)

<details>
<summary>Click to expand debate</summary>

**Host Agent Rebuttal:**
[paste rebuttal]

**Reviewer Ruling:**
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

**Write `review-stage/REVIEW_STATE.json`** with current round, threadId, score, verdict, and any pending derivations.

**Append to `findings.md`** (when `COMPACT = true`): one-line entry per key finding this round:
```markdown
- [Round N] [positive/negative/unexpected]: [one-sentence finding] (fidelity: qualitative → numerical)
```

Increment round counter → go to Phase E.5.

#### Phase E.5: Write Review Ledger

After documenting each round, append to `review-stage/REVIEW_LEDGER.json`. This is the authoritative machine-readable record for downstream skills (`/citation-audit`, `/paper-writing` Phase 0.5, external verifier).

**Format** (JSONL, one object per line):
```json
{
  "round": 1,
  "timestamp": "2026-07-20T14:30:00Z",
  "score": 7,
  "verdict": "almost",
  "key_criticisms": ["Missing symbolic proof for outcome O3", "No counterexample search for regime |λ|>1"],
  "actions_taken": ["Attempted SymPy proof for O3 (success)", "Ran counterexample sweep for |λ|>1 (none found)"],
  "fidelity_delta": {"O3": "qualitative → symbolic"},
  "blockers_remaining": ["Full regime verification for |λ|>1"],
  "phase": "documented"
}
```

**Fields**:
- `round` (int): round number (1-indexed)
- `timestamp` (string): ISO 8601 UTC
- `score` (int): reviewer score this round
- `verdict` (string): `ready` / `almost` / `not_ready`
- `key_criticisms` (string[]): top reviewer concerns
- `actions_taken` (string[]): fixes implemented
- `fidelity_delta` (object): fidelity level changes per outcome (optional)
- `blockers_remaining` (string[]): unresolved issues (optional)
- `phase` (string): `documented` (per-round) or `finalized` (at termination)

At termination, append one final entry with `phase: "finalized"` and `final_score`, `final_verdict`, and `total_rounds`.

### Termination

When loop ends (positive assessment or max rounds):
1. Update `review-stage/REVIEW_STATE.json` with `status: completed`.
2. Write final summary to `review-stage/AUTO_REVIEW.md`.
3. Update project notes with conclusions.
4. **Write method / derivation description** to `review-stage/AUTO_REVIEW.md` under a `## Method Description` section — a concise 1-2 paragraph description of the final derivation, its structure, and the verification chain. This serves as input for `/unified-plotting` in the figure generation phase.
5. **Generate claims from results** — invoke `/result-to-claim` to convert derivation results from `review-stage/AUTO_REVIEW.md` into structured paper claims. Output: `CLAIMS_FROM_RESULTS.md`. This bridges the review phase → paper-writing phase so `/paper-writing` can directly use validated claims. If `/result-to-claim` is not available, skip silently.
6. If stopped at max rounds without positive assessment:
   - List remaining blockers.
   - Estimate effort needed for each.
   - Suggest whether to continue manually or pivot.
7. **Render HTML view** (if `RENDER_HTML = true`, default): invoke `/render-html` on the cumulative review log. **Non-blocking**: if rendering fails, log the error and continue. Skip if `RENDER_HTML = false`.

## Boundaries

**Never**:
- Hide weaknesses to game a positive score. Honesty is non-negotiable.
- Promise to fix without implementing. Implement fixes BEFORE re-reviewing.
- Fabricate BibTeX or citations. Use the DBLP → CrossRef → `[VERIFY]` chain. Do NOT generate BibTeX from memory.
- Give up on a reviewer concern after one attempt. **Exhaust before surrendering** — before marking any concern as "cannot address": (1) try at least 2 different solution paths, (2) for derivation issues, attempt a weaker version or an alternative argument, (3) for numerical issues, adjust parameters or try a different sanity check, (4) only then concede narrowly and bound the damage.
- Silently skip writing `review-stage/REVIEW_LEDGER.json` at termination — the ledger is mandatory regardless of outcome.
- Override a fidelity gate `BLOCK` with a positive top-level verdict — the gate is a hard override.
- Switch to a discipline-specific persona (senior-econ-editor / senior-ml-reviewer / senior-physics-editor). OSS uses only `senior-reviewer-agnostic`.

**Always**:
- Use maximum reasoning effort for every external reviewer call.
- Save the reviewer thread ID from round 1 and reuse the same thread for later rounds.
- Be honest — include negative results and failed derivations.
- If a derivation takes > 30 minutes, launch it and continue with other fixes while waiting.
- Document EVERYTHING — the review log should be self-contained.
- Update project notes after each round, not just at the end.
- Append to `review-stage/REVIEW_LEDGER.json` at the end of every round (Phase E.5) and finalize at termination — the ledger is the authoritative machine-readable record for downstream skills.

## Output Shape

The final `review-stage/AUTO_REVIEW.md` contains:
1. **Header** — direction, date, max rounds, difficulty
2. **Round-by-round entries** — for each round: assessment summary, reviewer raw response (verbatim in `<details>`), debate transcript (if hard / nightmare), actions taken, results, status
3. **Final summary** — final score, verdict, remaining blockers (if any)
4. **Method Description** — concise 1-2 paragraph description of the final derivation for downstream paper illustration

`CLAIMS_FROM_RESULTS.md` (if generated at termination) contains structured paper claims validated by the loop's results.

## Prompt Template for Round 2+

Send the follow-up on the same reviewer thread (reusing the saved thread ID):

```text
[Round N update]

Since your last review, we have:
1. [Action 1]: [result]
2. [Action 2]: [result]
3. [Action 3]: [result]

Updated results table:
[paste fidelity levels per outcome]

Please re-score and re-assess. Are the remaining concerns addressed?
Same format: Score, Verdict, Remaining Weaknesses, Minimum Fixes.
```

## Reviewer Routing

External reviewer routing, backend selection, and per-CLI registration examples are documented in [`shared-references/reviewer-routing.md`](../shared-references/reviewer-routing.md).

## Review Tracing

After each external reviewer call, save the trace following [`shared-references/review-tracing.md`](../shared-references/review-tracing.md) (forensic policy; never silently skip). Respect the `trace` parameter (default: `full`).

## See Also

- [`../shared-references/discipline-context.md`](../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/reviewer-routing.md`](../shared-references/reviewer-routing.md) — cross-model reviewer routing
- [`../shared-references/review-tracing.md`](../shared-references/review-tracing.md) — forensic review trace policy
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — 3-fidelity claim gate (consumed at termination)
- [`../kill-argument/SKILL.md`](../kill-argument/SKILL.md) — anti-self-deception exercise (complementary)
