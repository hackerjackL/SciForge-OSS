# Reviewer Independence Protocol

## Core Principle

**Content must reach the reviewer unfiltered. The executor points to
files and sets the review task; the reviewer reads and judges
independently.**

Cross-model adversarial collaboration only works if the reviewer forms
its own assessment from primary artifacts. If the executor pre-digests,
summarizes, or interprets content before passing it to the reviewer, the
reviewer is evaluating the executor's framing — not the actual work.
This re-introduces the correlated blind spots that heterogeneous review
is designed to avoid.

This is the contract that makes "cross-model review" mean something
more than "a second model that agrees with the first one." Without
independence, the reviewer inherits the executor's biases and the
adversarial value is lost.

## What CAN be passed to the reviewer

- **Role / persona** — e.g. "Review as a NeurIPS-level reviewer"
- **Review objective** — e.g. "Evaluate publishability", "Check code
  correctness", "Score 1-10 on clarity"
- **File paths** — let the reviewer read file contents directly
- **Structural metadata** — e.g. "The paper has 8 sections",
  "Experiments are in `experiments/`"
- **Venue constraints** — e.g. "ICLR format, 9-page limit"

## What CANNOT be passed (counts as "subjective interference")

- ❌ Executor's summary or paraphrase of file contents
- ❌ Executor's interpretation of results (e.g. "I think the problem
  is...", "This suggests...")
- ❌ Executor's recommendations or conclusions (e.g. "I suggest
  changing...", "The likely cause is...")
- ❌ Key findings or bullet points extracted by the executor
- ❌ Leading questions (e.g. "Is this publishable?", "Is this trade-off
  reasonable?")
- ❌ Previous review rounds' feedback or critique (let the reviewer
  assess the current state fresh)
- ❌ Executor's description of what was changed since last round (e.g.
  "I fixed X, Y, Z")
- ❌ Statements asserting the current approach's strengths

## Why this matters

| With filtering | Without filtering |
|---|---|
| Reviewer sees executor's framing | Reviewer sees raw artifacts |
| Correlated blind spots persist | Genuinely independent assessment |
| Executor can "coach" favorable review | Review probes real weaknesses |
| Defeats the purpose of cross-model | Achieves adversarial collaboration |

The value of a heterogeneous reviewer is precisely that it does **not**
share the executor's priors. Any executor-supplied framing collapses
the reviewer back toward the executor's viewpoint, which is the failure
mode this protocol exists to prevent.

## Correct pattern

The executor hands the reviewer a task frame plus file paths, then
steps back. The reviewer reads the files itself and forms its own
assessment.

> **Task:** Review the following research project as a senior ML
> reviewer.
>
> **Files to read:**
> - Proposal: `/path/to/PROPOSAL.md`
> - Experiment results: `/path/to/EXPERIMENT_LOG.md`
> - Paper draft: `/path/to/paper/main.tex`
> - Code: `/path/to/src/`
>
> Please read all files yourself and provide a complete review.
> Score 1-10 on: novelty, soundness, clarity, significance.

Note what is absent: no summary of the contribution, no hint about what
the executor thinks is strong or weak, no recap of prior rounds. The
reviewer encounters the work the same way a real program committee
member does.

## Incorrect pattern

The executor pre-digests the work and hands the reviewer a framing to
react to.

> The main contribution is a new loss function that improves by 15%.
> However, I noticed the ablation is incomplete.
> Here's my summary of the key results: [...]
> Please review whether this is publishable.

This is incorrect even when every claim in the framing is true. The
problem is not factual accuracy — it is that the reviewer is now
anchored on the executor's choice of what to look at, what to call the
contribution, and what the open questions are. A reviewer that starts
from the executor's summary will, with high probability, end near the
executor's conclusion.

## When to apply

This protocol applies to **all** cross-model review calls in SciForge:

- `/research-review` — paper review
- `/auto-review-loop` — iterative review
- `/paper-plan` — outline review
- `/paper-write` — section review
- `/paper-figure` — figure quality review
- `/rebuttal` — stress test
- `/meta-optimize` — patch review
- Any skill that sends artifacts to a reviewer

"Cross-model" means the reviewer is a different model instance from the
executor. Even when the same model family is used on both sides, the
reviewer must run in a fresh context with no carry-over of the
executor's reasoning. What makes the review independent is the
information boundary, not the model brand.

## Fresh context and blind review

Two supporting invariants keep independence real:

- **Fresh context** — each new review session starts with a clean
  reviewer context. The reviewer has not seen the executor's working
  notes, intermediate reasoning, or prior failed attempts. Only the
  artifacts explicitly listed in the task frame are in scope.
- **Blind review** — the reviewer does not know which model produced
  the work, what effort level was used, or what the executor's own
  self-assessment was. These would all anchor the review. The reviewer
  judges the work on its merits, not on its provenance.

## Avoiding single-model blind spots

The point of routing review to a different model is that different
model families have different blind spots. A weakness that one model
systematically glosses over may be exactly the weakness another model
flags first. This only delivers value if the reviewer is actually
operating independently — a reviewer fed the executor's framing will
reproduce the executor's blind spots, and the cross-model call becomes
a costly no-op.

## Exception

Multi-round review **within the same review thread** may reference the
reviewer's own previous feedback to check whether an issue was
resolved — but still must not include executor interpretations of that
feedback. The reviewer can remember what it said last round; it must
not be told what the executor thinks about what it said.

Across threads, memory resets. A new review session is a fresh
context — see [`reviewer-routing.md`](reviewer-routing.md) §Reviewer
memory.

## See also

- [`reviewer-routing.md`](reviewer-routing.md) — reviewer backend selection, routing, and memory
- [`effort-contract.md`](effort-contract.md) — reviewer reasoning effort is always maximum, regardless of `effort`
- [`assurance-contract.md`](assurance-contract.md) — 6-state verdict schema used by all reviewers
- [`integration-contract.md`](integration-contract.md) — live integration registry and enforcement layers
