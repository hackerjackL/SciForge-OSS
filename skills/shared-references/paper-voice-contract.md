# Paper Voice Contract — submission-grade prose discipline (v1.7.1)

> **Source**: distilled from Google's PaperOrchestra (arXiv:2604.05018,
> `google-research/paper-orchestra`, Apache-2.0) — the multi-agent writing
> framework ScientistTwo itself uses — plus the measured 86-paper disclosure
> pattern ([`SCIENTISTTWO_DISCLOSURE_ANALYSIS.md`](../../docs/SCIENTISTTWO_DISCLOSURE_ANALYSIS.md)).
> We port the *rules*, not their code. This contract binds Step 2 of
> `/paper-writing`; the self-check and the review panel score against it.
> The failure class it kills: "engineering report" voice — process narration,
> unanchored claims, vague citation etiquette, captions that describe the
> pipeline instead of the science.

## 1. Claim discipline (CRITICAL EVALUATION RULE)

1. **No beat/SOTA claim without a logged comparison.** "outperforms X",
   "state of the art", "beats baseline Y" are legal ONLY if the experiment
   artifacts contain a direct comparison to X under the stated protocol
   (traceable to `RESULT.json`/metrics files). Otherwise the sentence is
   rewritten to what IS supported.
2. **Every number traces to an artifact.** Section text is written from the
   machine-readable results ("use the exact values"); a number not present in
   any artifact is a fabrication — delete it. Stated gains must equal the
   recomputed gain (s2_audit already enforces the arithmetic; this is the
   prose-side twin).
3. **Concurrent-work rule.** Papers published after the study's knowledge
   cutoff are cited as *concurrent work* — never as the baseline you beat or
   the gap you filled (you could not have known them).
4. **Qualified-hedging is precision, not weakness.** Regime statements
   ("within σ=30 noise, at n≤1200") replace global claims; this is the SCI
   body voice (§0.6 writing-principles) with a concrete test: every universal
   quantifier must have a visible scope.

## 2. Section templates (bullet-locked)

- **Abstract** (≤250 words, ≥8 distinct numbers, ≥1 explicit %/points):
  `context → problem → "We introduce/present X" (method protagonist, first
  sentence) → key results as quantified bullets → positive positioning close`.
  No citations, no equations, no failure narration (rule 2b of paper-writing;
  99% of the S2 corpus opens with the method).
- **Introduction**: macro hook → gap (verbatim from `FRONTIER_GAP.md`, never
  improvised) → contributions list (all `polarity: positive`; each item with
  its evidence pointer) → roadmap sentence.
- **Related Work**: 2–4 methodology clusters, each cluster = {what the line
  of work does → its limitation *with citation* → bridge to our method};
  grouped citations ("Several methods [a,b,c] propose…"), never one-paper-
  per-sentence name-dropping; every cited work read from its abstract — the
  sentence must say what THAT paper contributes, not just its name.
- **Results**: tables in `booktabs` style; every table/figure appears before
  the Conclusion; each numeric cell matches the artifact to the digit.

## 3. Citation obligation (EXHAUSTIVE)

Every named dataset, optimizer, metric, model architecture, statistical
test, and software tool gets a citation (or a version statement) at first
use. Unnamed borrowing ("a standard bootstrap") is how reviewers find
sloppiness. The bib source is the 3-layer-verified list only — a missing
verification is dropped with disclosure, never guessed.

## 4. Figure/table caption discipline

1. Caption describes the SCIENCE in the image (what varies, what each
   series/panel means, the takeaway), never the rendering pipeline
   (no "palette", "renderer", "16:9", "render.py") and never the audit
   machinery.
2. Caption must not contain the word "Figure"/"Table" (LaTeX supplies the
   number) and must not be markdown.
3. **Visual fidelity**: the caption must match what is actually drawn —
   before finalizing, re-read each rendered figure and delete/rewrite any
   interpretive clause the image does not support ("do not hallucinate
   interpretations that contradict the visual evidence").
4. Error bars/CI bands must be defined in the caption (±1 SD? 95% CI? over
   seeds?) — an undefined whisker is a reject-on-sight marker.
5. Figures are generated from the archived machine-readable results by code
   (recipe path), and the caption is written AFTER the figure exists — never
   a caption describing a figure that changed.

## 5. Negative vocabulary list (delete on sight)

Flowery intensifiers (`meticulously`, `comprehensive`, `novel` as a
self-label, `significantly` without a test), colloquial summary openers
("In this paper, we basically…"), defensive framing ("although limited…",
"we admit…"), pipeline jargon (`gate`, `verdict`, `boundary`, `Phase 6c`,
`ledger` — except in the reproducibility statement), and failure-voice
protagonists per paper-writing rule 2b. The tone anchor: **dense, objective,
technical**.

## 6. Reviewer-facing scoring (anti-inflation, for the panel + self-review)

The review panel scores on the frozen rubric with PaperOrchestra's
anti-inflation anchors — a self-score that ignores them is invalid:

| Band | Anchor |
|---|---|
| 0–20 | unacceptable: claims unsupported, numbers missing |
| 30–44 | weak: main claim partially supported, presentation rough |
| **45–70** | **default band** — most honest self-assessments live here |
| 71–84 | solid: all headline claims traced, clear positioning |
| 85–92 | strong: + novel instrument or surprising established result |
| 93–100 | exceptional: "changes my thinking" tier — requires evidence on EVERY axis |

Rules: >85 requires per-axis justification (a paper that merely "did
everything right" caps at 84); a pure list of correct-but-uninspired work
caps at 70; verbosity/length never raises a score. This is the calibration
`CALIBRATION.json` anchors against — raw panel scores without the band
discipline are the number-theater the S2 anchor design exists to kill.

## 7. Refinement loop with rollback (auto-review-loop binding)

Each revision round must (a) state which weaknesses it addresses, (b) be
re-scored, and (c) **ROLL BACK if the score drops** — a rewrite that lowers
the reviewer score is worse than no rewrite. Answers to reviewer questions
fold into the body at their natural position, never as a letter-style
appendix; requests for experiments with no data path are dropped silently
(not answered with promises).

## See Also

- paper-writing rule 2b / self-check 12b (S2 disclosure voice — the corpus
  measurement this contract operationalizes)
- writing-principles §0.5/§0.6 (anti-AIGC, SCI body voice)
- figure-layout-contract / figure-quality-contract (rendering side)
- docs/SCIENTISTTWO_DISCLOSURE_ANALYSIS.md (evidence base)
