---
name: kill-argument
version: 1.1.2
description: "Adversarial attack-defense self-review: write the single strongest 200-word rejection, then defend point-by-point and surface load-bearing unresolved issues. Phase 14 sub-step. Invoke after stable score, before submission/rebuttal."
type: reference-skill
role: adversarial-attack-defense-reviewer
---

# Kill Argument Exercise: Single-Agent Adversarial Attack-Defense Self-Review

## Quick Reference

- **Purpose**: 压力测试 — 找"如果审稿人要拒这篇，最致命的论点是什么"
- **Input**: derivations/{problem_id}/ + CLAIMS_FROM_RESULTS.md
- **Output**: KILL_ARGUMENT.md + KILL_ARGUMENT.json
- **Key**: 双步自评审 (攻击者→裁决者角色切换)；200 字攻击 memo；3-7 个细化攻击点

Stress-test the headline claims of a research output against the strongest possible rejection argument, then the same agent switches role to defend point-by-point and surface still-unresolved critical issues.

## Use When

Use this skill after standard reviews have settled at a stable score, but before submission or during rebuttal preparation, to surface what the worst-case reviewer paragraph would look like.

Typical prompts:

- "kill argument"
- "adversarial review"
- "hostile review"
- "rebuttal preparation"
- "reviewer-2 simulation"

Most valuable for **theory papers** with ≥5 theorem-class environments where the headline depends on real proof obligations. For empirical papers without theorems, use `/auto-review-loop` instead.

## Job

Run a two-step adversarial self-review: Step 1 (agent switches to "attacker" role) writes the single strongest 200-word rejection memo; Step 2 (agent switches to "adjudicator" role) decomposes the attack into atomic points, classifies each as answered / partially answered / still unresolved based strictly on the current research artifacts, and surfaces the load-bearing critical issues. The non-negotiable goal: force the agent to commit to one damaging line of attack rather than hedge, then honestly triage what the research actually answers.

## Why This Exists

Standard score-based self-reviews (from `/auto-review-loop`) tend to produce **balanced** weakness lists. Each weakness gets ~equal attention, ranked CRITICAL > MAJOR > MINOR. Empirically, this misses one specific failure mode: the **single most damaging argument** a reviewer would write in a rejection paragraph — the one sentence that, if a senior area chair reads it, kills the research.

A balanced reviewer might list "scope-overclaim risk" as MAJOR alongside 3-5 other MAJORs, never quite committing. An adversarial reviewer **must commit**: their entire job is to convince the area chair to reject in 200 words.

This skill runs that adversarial pass deliberately, then forces the same agent (as adjudicator) to defend point-by-point, classify each rejection as already-fixed / partially-fixed / still-unresolved, and surface what's actually load-bearing.

## How This Differs From Other Review Skills

| Skill | What it asks the reviewer | Output |
|-------|---------------------------|--------|
| `/auto-review-loop` | "Score this paper, list weaknesses by severity" | balanced weakness list |
| `/logic-verification` | "Is this theorem actually proved?" | per-step proof obligation audit |
| `/result-to-claim` | "Does the paper report numbers truthfully?" | per-claim evidence verification |
| `/citation-audit` | "Are citations real and used in correct context?" | per-entry KEEP/FIX/REPLACE/REMOVE |
| **`/kill-argument`** | **"Write the single strongest rejection paragraph; then defend it."** | **attack memo + per-point defense + unresolved surfaced** |

This skill is **complementary**, not a replacement. Run after standard reviews when you want to know what the worst-case reviewer paragraph would look like, before camera-ready or rebuttal preparation.

## Configuration

- **ATTACK_LENGTH** = approximately 200 words (do not exceed 250). Single coherent argument, not a list.
- **DEFENSE_DECOMPOSITION** = 3-7 atomic rejection points extracted from the attack memo. Each gets its own classification.
- **CLASSIFICATION** = `answered_by_current_text` / `partially_answered` / `still_unresolved`. (Names chosen so the adjudicator does not assume "fixed" implies prior history of patching — they read the artifacts as a fresh reviewer would.)
- **ROLE_SWITCHING** = mandatory. The agent must explicitly switch roles between "attacker", "defender", and "adjudicator". Never conflate roles.
- **OUTPUT** = `KILL_ARGUMENT.md` (human-readable) + `KILL_ARGUMENT.json` (machine-readable) in the review directory.
- **RENDER_HTML** = `true` (default) — auto-render `KILL_ARGUMENT.md` to HTML after writing the report. Full review gate applies (audit-class artifact). Set `false` to skip.

## Workflow

### Step 1: Discover Research Artifacts

Locate the derivation directory and research artifacts:

- Find the derivation output (`derivations/{problem_id}/derivation_output.md`) — the primary theory/derivation document
- Find the claims file (`CLAIMS_FROM_RESULTS.md`) — validated claims from `/result-to-claim`
- Find the SymPy script (`code/derivations/{problem_id}/derivation.py`) — the executable proof
- Find the verification report (`derivations/{problem_id}/verification_report.md`) — numerical sanity checks
- If a paper draft exists (`paper/main.tex` + `paper/sections/*.tex`), include it as additional context

If no derivation output exists, the skill should still run on `CLAIMS_FROM_RESULTS.md` alone, but the prompt should note this limitation.

### Step 2: Attack Memo — Agent as Attacker

The agent switches to "hostile reviewer" role and writes the strongest possible rejection memo:

- Role: simulating a hostile senior-reviewer-agnostic (mixed top venues across all domains + arXiv level)
- Task: construct the single best argument to reject this research in approximately 200 words; write the worst-case rejection memo a senior area chair would produce after reading the derivation output and claims
- Files to read: derivation output, claims file, SymPy script, verification report; include paper draft if available
- Zero-context constraint: do not consult any prior self-reviews, fix lists, or summaries; this must be a fresh, zero-context adversarial pass

Focus axes (pick the most damaging combination, do not list all):

1. Theorem validity: are central theorems actually proved as stated?
2. Assumption-vs-claim mismatch: does the body silently retreat to a narrower object than the title/abstract advertise?
3. Missing proof obligations: is a fundamental lemma invoked but not proved that the headline depends on?
4. Limit-order ambiguity: are limits composed in a way the paper does not commit to?
5. Claim-vs-evidence gap: is the numerical evidence too narrow to support the breadth of the stated theorem or take-away?
6. Scope overclaim: does the title or abstract sell a result substantially broader than what the body proves?

Constraints:

- Approximately 200 words total (do NOT exceed 250)
- Single argument, not a list — pick the most damaging line of attack and develop it
- Cite specific file:line locations or equation numbers when accusing
- Tone: dispassionate but uncompromising. Do NOT hedge. Do NOT acknowledge mitigations the research might have made elsewhere
- Do NOT reference prior self-review rounds, fix lists, or any context outside the current artifacts

Output: just the rejection memo, nothing else.

Save the attack memo verbatim — both the adjudication step and the human-readable report use it.

### Step 3: Adjudication Memo — Agent as Adjudicator

The agent switches to "adjudicator" role and rules on each attack point:

- Role: an independent area-chair adjudicator examining whether the current research text answers a hostile reviewer's rejection memo
- Task: read the attack point-by-point and rule, from the current source files alone, whether each point stands or falls
- Fresh, zero-context adjudication; do not reference any prior reviews / fix lists

The attack is one continuous argument, but it makes multiple distinct rejection points that must be adjudicated separately. Decompose the attack into its atomic rejection points (3-7 of them), then for each point classify it:

- `answered_by_current_text`: the current research source already mitigates this point (cite specific file:line evidence)
- `partially_answered`: research has some response but not enough to refute the attack as written
- `still_unresolved`: research has no effective response

The label `answered_by_current_text` is intentional — "fixed" implies history of patching and biases toward optimism. The adjudicator reads the artifacts as a reviewer would, with no knowledge of prior round changes.

For each rejection point, output:

```
### Point P_n: <short label>
**Attack claim**: <the specific accusation, ~30 words>
**Verdict**: answered_by_current_text | partially_answered | still_unresolved
**Evidence (or lack of)**: <cite file:line, ~50 words>
**Severity if unresolved**: critical | major | minor
**If unresolved, recommended fix**: <one specific actionable sentence>
```

After per-point analysis, output:

```
## Summary
Total rejection points: N
- answered_by_current_text: X
- partially_answered: Y
- still_unresolved: Z

## Net assessment
<one short paragraph: would this paper survive a senior area-chair read
of the attack memo, given only what is in the current source? Be honest —
if Y or Z > 0 and they hit the headline, say so.>

## Top action items (in priority order, max 3)
1. ...
2. ...
3. ...
```

Constraints:

- Do NOT consult any prior round reviews or fix lists. Adjudication must be made strictly from current research artifacts.
- If the research cannot refute a point, do NOT minimize — keep severity honest.
- If a point reflects an author-chosen position (e.g., conscious title scope decision), classify as `partially_answered` with a note that the position is intentional, AND say whether this position is sustainable under the attack — do NOT auto-grade as `answered_by_current_text` just because it is intentional.
- Be specific. No flattery, no hedging, no rationalizing on the research's behalf.

### Step 4: Write KILL_ARGUMENT.md and KILL_ARGUMENT.json

Compose the human-readable report `KILL_ARGUMENT.md`:

```markdown
# Kill Argument Report — <paper title>

**Date**: <YYYY-MM-DD>
**Reviewer model**: <model + reasoning effort>, fresh threads
**Attack thread**: <thread id 1>
**Adjudicator thread**: <thread id 2>
**Verdict**: <PASS / WARN / FAIL / NOT_APPLICABLE / BLOCKED / ERROR> (`reason_code: <...>`)

## Net assessment

<paragraph from adjudicator memo's "Net assessment">

## Attack memo (verbatim)

> <attack memo from the Attack step>

## Adjudication (per-point)

<copy verbatim from the Adjudication step — uses labels answered_by_current_text / partially_answered / still_unresolved>

## Top action items

<copy from the Adjudication step>

## Recommendation

If P_4 (or whatever still_unresolved critical) is research-level, record
it as a known open problem in the conclusion / limitations. If it is
writing-level, queue for next /auto-paper-improvement-loop round.
```

Compose the machine-readable `KILL_ARGUMENT.json` following the SciForge Audit Artifact Schema ([`shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md)):

```json
{
  "audit_skill": "kill-argument",
  "verdict": "one of: PASS | WARN | FAIL | NOT_APPLICABLE | BLOCKED | ERROR",
  "reason_code": "see verdict mapping below",
  "summary": "one-line summary, ~80 chars",
  "audited_input_hashes": {
    "derivation_output.md": "sha256:<...>",
    "CLAIMS_FROM_RESULTS.md": "sha256:<...>",
    "derivation.py": "sha256:<...>"
  },
  "trace_path": ".sciforge/traces/kill-argument/<date>_run<NN>/",
  "reviewer_model": "<model>",
  "reviewer_reasoning": "xhigh",
  "generated_at": "<UTC ISO-8601>",
  "details": {
    "attack_memo": "<verbatim>",
    "decomposed_points": [
      {
        "id": "P_1",
        "label": "<short label>",
        "attack_claim": "<...>",
        "verdict": "one of: answered_by_current_text | partially_answered | still_unresolved",
        "evidence": "<file:line citation>",
        "severity_if_unresolved": "one of: critical | major | minor",
        "recommended_fix": "<...>"
      }
    ],
    "counts": {
      "answered_by_current_text": 0,
      "partially_answered": 0,
      "still_unresolved": 0
    },
    "net_assessment": "<adjudicator memo's net assessment>",
    "top_action_items": ["...", "...", "..."]
  }
}
```

**Hash inputs** (`audited_input_hashes`): use paper-relative paths, `sha256` of every `.tex` consumed plus `references.bib` and the compiled `main.pdf` if it exists. The verifier rehashes these and flags `STALE` if the user edited the paper after running the audit.

### Verdict Mapping

Every (counts, severity) tuple must hit exactly one row:

| Verdict | reason_code | Trigger |
|---|---|---|
| `FAIL` | `unresolved_critical` | ≥1 `still_unresolved` at `critical` severity |
| `WARN` | `unresolved_major_or_minor` | ≥1 `still_unresolved` at `major` or `minor` severity (and no `critical`) |
| `WARN` | `partial_critical_or_repeated_major` | ≥1 `partially_answered` at `critical`, OR ≥2 `partially_answered` at `major` |
| `PASS` | `defense_survives_with_minor_partial_only` | 0 `still_unresolved`, AND all `partially_answered` are at `minor` severity |
| `PASS` | `defense_survives` | 0 `still_unresolved`, AND 0 `partially_answered` |
| `NOT_APPLICABLE` | `not_theory_or_scope_paper` | Paper has <2 `\begin{theorem\|lemma\|proposition\|corollary}` AND no scope / generality claims in abstract |
| `NOT_APPLICABLE` | `headline_unstable` | Title or abstract changed within the last 2 commits — re-run after headline stabilizes |
| `BLOCKED` | `paper_compile_failed` | Compiled PDF missing AND `main.tex` does not compile clean — adjudication needs source fidelity |
| `BLOCKED` | `source_files_missing` | `main.tex` not found, or no `sec/*.tex` files |
| `ERROR` | `reviewer_api_error` | Reviewer call failed |
| `ERROR` | `decomposition_parse_failed` | Adjudicator thread did not return parseable per-point structure |
| `ERROR` | `trace_save_failed` | Trace directory write failed |

`PASS` requires `still_unresolved == 0`. Any `partially_answered` at `major` or higher → at most `WARN`.

The verdict is computed from the per-point counts; do NOT let the defense thread output the top-level verdict directly (that would let it self-grade). The skill code does the verdict mapping.

### Step 5: Print Summary

To the user:

```
🗡  Kill Argument complete.

  Attack: <one-sentence summary of the rejection thrust>

  Adjudication breakdown:
    answered_by_current_text:   X
    partially_answered:         Y
    still_unresolved:           Z   ← critical: <names>

  Verdict: <PASS / WARN / FAIL / NOT_APPLICABLE / BLOCKED / ERROR>
  Reason:  <reason_code, e.g., defense_survives, unresolved_critical>

  Top action items:
  1. ...
  2. ...
  3. ...

  Full report: KILL_ARGUMENT.md
```

## Output Protocols
> **v5.2 评判产物位置**：本 skill 产出的机读 verdict/hash/审计 JSON 一律写入 `verdicts/`（文件名见 [`output-protocol.md`](../../shared-references/output-protocol.md) 产物目录结构；叙述性报告留在原 stage 目录）。


> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

**Never**:

- Conflate the Attack and Adjudication roles — they must be separate role switches with no memory sharing.
- Carry prior context, fix lists, executor summaries, or improvement-loop logs between roles.
- Let the attack memo exceed 250 words or devolve into a list — force commitment to one damaging line.
- Let the adjudicator minimize — `still_unresolved` is honest if the research has no effective response.
- Auto-grade an author-chosen position as `answered_by_current_text` just because it's intentional.
- Let the adjudicator self-grade the top-level verdict — the skill code maps per-point counts to the verdict.
- Edit research artifacts — the skill is detect-only by direct invocation.

**Always**:

- Use fresh role switches for both Attack and Adjudication.
- Cite specific file:line evidence in both the attack and the adjudication.
- Decompose the attack into 3-7 atomic points.
- Compute the verdict from per-point counts via the verdict mapping table.
- Save traces for both roles per the review tracing protocol.

## When NOT to Use

- Empirical papers without theorems / scope claims — `/auto-review-loop` is more useful. The skill emits `NOT_APPLICABLE` with `reason_code: not_theory_or_scope_paper` in this case.
- Very early drafts where the headline isn't stable yet — fix the headline first. The skill emits `NOT_APPLICABLE` with `reason_code: headline_unstable` if the title or abstract changed within the last 2 commits.
- Papers with ongoing experiments — wait until results stabilize, then run.

## Output Shape

- `KILL_ARGUMENT.md` — human-readable report
- `KILL_ARGUMENT.json` — machine-readable ledger
- `.sciforge/traces/kill-argument/<date>_runNN/` — role-switch traces (Attack memo + Adjudication memo)
- Optional: applied fixes if user explicitly requests; default is **detect-only, do not auto-modify**
- `KILL_ARGUMENT.html` (when `RENDER_HTML = true`, default) — single-file HTML view rendered inline by the agent. Full review gate applies. The `.review.json` sidecar carries the render-fidelity verdict. **Non-blocking**: if rendering fails, log the failure and treat the skill as complete — the HTML view is a convenience, not a prerequisite for the kill-argument verdict.

## Key Rules

- **Fresh role switch per call.** Both Attack and Adjudication use fresh role switches. Attack and Adjudication must not share context.
- **Zero prior context.** Neither role receives prior round reviews, fix lists, executor summaries, or improvement-loop logs.
- **Attack must commit.** Single argument, ~200 words. No "consider also" hedge. The whole value is in forcing the reviewer to pick the most damaging line.
- **Adjudicator must classify, not minimize.** `still_unresolved` is honest if the research has no effective response. Don't downgrade to `partially_answered` unless evidence is real.
- **Author-chosen positions**: mark `partially_answered` with note that the position is intentional, AND say whether the position is sustainable under the attack. Don't auto-grade as `answered_by_current_text` just because it's intentional.
- **Verdict is computed by the skill, not by the adjudicator.** The attack step emits per-point classifications; the skill code maps those to one of the audit verdicts via the table above. Never let the adjudicator self-grade the top-level verdict.
- **Detect-only by direct invocation; can be invoked by `/auto-review-loop` which then merges unresolved findings into its fix list.** When a user runs `/kill-argument` directly, the output is informational and the human decides whether to act. When the skill is invoked from inside the auto-review loop, the loop reads `KILL_ARGUMENT.json`, deduplicates against its existing weakness list, and feeds novel `still_unresolved` points into its fix round — `/kill-argument` itself never edits research artifacts.
