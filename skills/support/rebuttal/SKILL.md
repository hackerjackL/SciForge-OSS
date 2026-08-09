---
name: rebuttal
version: 1.3.1
description: "Point-by-point rebuttal / appeal letter generator: after a rejection or a review round, classify every reviewer point (experiment_redesign / pivot / kill / wording), concede what must be conceded, respond with evidence, and emit exact manuscript changes. Output: paper/REBUTTAL_LETTER.md. Invoke after reviews land or a rejection letter arrives."
type: reference-skill
role: rebuttal-letter-writer
---

# Rebuttal Letter: Point-by-Point Response to Reviews or Rejection

## Quick Reference

- **Purpose**: turn reviews (or a rejection letter) into a point-by-point rebuttal/appeal letter with evidence-backed responses and exact manuscript changes
- **Input**: .sciforge/audits/AUTO_REVIEW.md + .sciforge/verdicts/REVIEW_STATE.json + .sciforge/verdicts/REVIEW_LEDGER.json + paper/main.tex (+ optional pasted rejection letter)
- **Output**: paper/REBUTTAL_LETTER.md (+ .sciforge/MANIFEST.md entry)
- **Key**: classify each point via `response_class`; quote → concede where warranted → evidence-backed response → exact manuscript change; never claim new experiments without ledger/matrix evidence

## Use When

Use this skill after a paper receives reviews (internal `/auto-review-loop` rounds or external peer review) or after an outright rejection, when the user wants a structured, point-by-point rebuttal or appeal letter.

Typical prompts:

- "write the rebuttal"
- "respond to the reviews"
- "draft an appeal letter"
- "point-by-point response"
- "rebuttal"

## Job

Collect every reviewer point from the review artifacts, classify each with the anti-shrinkage `response_class` vocabulary, and produce a single rebuttal letter in which every point receives: verbatim quote → concession where warranted → evidence-backed response → exact manuscript change. The non-negotiable goal: **every claim of new evidence in the letter must be traceable to a registered artifact — a rebuttal is a legal brief, not a promise.**

## Inputs

- `.sciforge/audits/AUTO_REVIEW.md` — narrative review log (per-round criticisms, debate transcripts)
- `.sciforge/verdicts/REVIEW_STATE.json` — machine-readable round state; carries `response_class` per concern (v5.2 path; read fallback `.sciforge/verdicts/REVIEW_STATE.json`)
- `.sciforge/verdicts/REVIEW_LEDGER.json` — per-round ledger (`details.rounds[]`: score, verdict, action_items, debate_rulings, statistical_gate) (v5.2 path; read fallback `.sciforge/verdicts/REVIEW_LEDGER.json`)
- `paper/main.tex` (+ `paper/sections/*.tex`) — the manuscript the responses quote and change
- **Optional**: a rejection letter or external reviewer report pasted by the user — when present, it is the primary point source; internal review artifacts are secondary context.

If no review points can be recovered from any source, stop with: "No review points found — run `/auto-review-loop` first or paste the reviewer report / rejection letter."

## Method

### Step 1: Collect and Number the Points

Extract every atomic reviewer point (external report, or the union of the latest rounds' `key_criticisms` / action items in the ledger). Number them `R1, R2, ...` and quote each verbatim. Do not paraphrase the accusation — the area chair compares quotes against the original.

### Step 2: Classify Each Point (`response_class`)

Reuse the anti-shrinkage vocabulary from `REVIEW_STATE.json` (see [`../auto-review-loop/SKILL.md`](../auto-review-loop/SKILL.md), Anti-Shrinkage Protocol). Every point gets exactly one class:

| response_class | Reviewer says | Rebuttal posture |
|---|---|---|
| `experiment_redesign` | evidence gap (power, missing baseline, missing ablation) | cite completed matrix cells from `.sciforge/verdicts/EXPERIMENT_MATRIX.json` / `EXPERIMENT_LOG.md`, or commit to the exact run and label it **pending** — never as done |
| `pivot` | method-level flaw | explain the method change already made or proposed, with the affected sections |
| `kill` | core assumption false | if the kill argument stands, concede the claim's scope; if refuted, present the refutation with derivation/citation evidence |
| `wording` | presentation/clarity | concede and give the exact rewording; a letter made only of `wording` responses inherits the `shrinkage_only_response` FAIL — flag it to the user |

### Step 3: Draft the Per-Point Response

For every point, in order:

1. **Quote** — the reviewer's sentence(s), verbatim, blockquoted.
2. **Concession** — concede factual errors and valid criticisms explicitly ("We agree; the original text was wrong/unclear..."). Never concede a load-bearing claim without evidence forcing it.
3. **Response** — evidence-backed rebuttal: cite `paper/sections/*.tex` line/section, derivation output, `CLAIMS_FROM_RESULTS.md`, `EXPERIMENT_LOG.md`, or verified citations. No evidence → do not contest; concede or scope down instead.
4. **Manuscript change** — exact location (section + label/line) and a diff-like block:

```
Section 4.2 (Evidence), after line 12:
- old: "our method outperforms all baselines"
+ new: "our method outperforms the three tabulated baselines (Table 2); comparison with [X] is left to future work"
```

### Step 4: Tone Rules

- No sarcasm, no irritation, no "as the reviewer should have noticed".
- No capitulation on load-bearing claims without evidence forcing the concession.
- Concede factual errors explicitly and thank the reviewer for the catch.
- Disagree with evidence, not with the reviewer; every disagreement names the artifact that settles it.

### Step 5: Rounds and Stress Tests

Effort follows [`../../shared-references/effort-contract.md`](../../shared-references/effort-contract.md) (Writing & Rebuttal table): `rebuttal | draft rounds` = 1 / 2 / 3 / 5 and `rebuttal | stress tests` = 0-1 / 1 / 2 / 3 for lite / balanced / max / beast. A stress test = re-read the drafted letter as a hostile reviewer and mark any response that would not survive.

**Max contested points per round: 3** — when contesting (rather than conceding), pick at most 3 points per draft round to argue back, the most impactful ones. This mirrors the `/auto-review-loop` Self-Debate Protocol ("Maximum 3 rebuttals per round — pick the most impactful to contest"); conceding is unlimited, contesting is rationed.

## Gate (anti-fantasy)

The letter MUST NOT claim new experiments, results, or numbers were produced unless evidence exists in `.sciforge/verdicts/EXPERIMENT_MATRIX.json` (cell completed) or `EXPERIMENT_LOG.md` (run logged) — see [`../../shared-references/fantasy-prevention.md`](../../shared-references/fantasy-prevention.md). Any promised-but-unrun work must be labeled **planned / pending** with its matrix cell ID. A draft containing an unsupported "we have since run..." claim is rejected by this skill before writing the output file.

## Artifact contract

Output is `paper/REBUTTAL_LETTER.md`, produced per the versioned-write protocol of [`../../shared-references/output-protocol.md`](../../shared-references/output-protocol.md):

1. Write timestamped copy `paper/REBUTTAL_LETTER_{YYYYMMDD_HHmmss}.md` (history).
2. Copy to fixed-name `paper/REBUTTAL_LETTER.md` (downstream reads the fixed name).
3. Append a row to `.sciforge/MANIFEST.md` (Timestamp | /rebuttal | paper/REBUTTAL_LETTER.md | rebuttal | description + consumer).

Registered relationships in the [Artifact Registry](../../shared-references/artifact-registry.md): this skill consumes `.sciforge/audits/AUTO_REVIEW.md` + `.sciforge/verdicts/REVIEW_STATE.json` (both list `/rebuttal` as consumer) and `.sciforge/verdicts/REVIEW_LEDGER.json`; `paper/REBUTTAL_LETTER.md` is the narrative deliverable of this skill (stage directory `paper/`, fixed name).

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Letter Skeleton

```markdown
# Rebuttal — <paper title> (<venue / round>)

We thank the reviewers for ... . Below we respond point-by-point;
manuscript changes are quoted as diffs and highlighted in the revision.

## Reviewer 1 / Round N

### R1: <short label>
> <verbatim quote>

**Concession / response.** ...

**Manuscript change.** Section X.Y: `- old` / `+ new`

...
```

## Boundaries

**Never**:

- Claim completed experiments, numbers, or citations that no registered artifact backs (Gate above).
- Paraphrase the reviewer's accusation instead of quoting it.
- Let a draft consisting only of `wording`-class responses pass without flagging `shrinkage_only_response` to the user.
- Edit `paper/main.tex` or any research artifact — the letter *describes* changes; applying them is `/paper-writing`'s job unless the user explicitly asks.
- Exceed 3 contested points per draft round.

**Always**:

- Number and quote every point verbatim.
- Classify every point with exactly one `response_class`.
- Concede factual errors explicitly.
- Run the versioned write + MANIFEST append for the output file.
- Re-check the Gate immediately before writing the final copy.

## When NOT to Use

- No reviews and no rejection letter exist yet — run `/auto-review-loop` first.
- The review demands a KILL-level response to the core claim — run [`../kill-argument/SKILL.md`](../kill-argument/SKILL.md) first; if the kill argument stands, the correct output is scope revision, not rebuttal.
- Camera-ready stage with accepted paper — there is nothing to rebut.

## Output Shape

- `paper/REBUTTAL_LETTER_{timestamp}.md` — versioned history copy
- `paper/REBUTTAL_LETTER.md` — fixed-name latest copy (the deliverable)
- `.sciforge/MANIFEST.md` — one appended row for the write

## Key Rules

- **Quote, then answer.** Every point: verbatim quote → concession → evidence-backed response → exact manuscript change. Missing any segment = unfinished point.
- **Evidence or concede.** A response without an artifact citation is a `wording` response in disguise; either find the evidence or concede.
- **Pending ≠ done.** Planned work is labeled pending with its matrix cell; only logged runs may be asserted as done.
- **Rationed contesting.** Max 3 contested points per round (auto-review-loop debate protocol); everything else is conceded or scoped down.
- **The letter is auditable.** `audited_input_hashes`-style discipline: every factual assertion in the letter names the file it came from.
