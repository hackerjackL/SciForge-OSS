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

## 4b. Internal-term substitution table (v1.7.1, leakage class L)

The manuscript never names SciForge machinery. Where the pipeline's internal
vocabulary would otherwise leak, use the scientific equivalent:

| internal term (class L hit) | write instead |
|---|---|
| regime ledger | scope of validity / validity regime |
| promotion gate / three-state critic | pre-registered promotion rule |
| engineer rounds | tuning rounds (pre-registered budget) |
| integrity monitor / s2 audit | (omit; describe the check itself, e.g. "the comparison is paired on identical streams") |
| phase N / gate exit / verdict file | (omit entirely) |
| our/the/run workspace | the run artifacts / the released code |

`leakage_scan.py` class L enforces this mechanically at the compile boundary;
the table exists so writers never meet the gate for the first time at phase 13.

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

## 8. Claim mode: `sota` vs `attribution` (v1.7.1, kernel flag `claim_mode`)

The run declares ONE mode at phase 0; it changes what a refuted hypothesis
means, and the writing follows:

- **`claim_mode=sota`** — the paper's thesis is that the method WINS.
  A refuted core hypothesis is therefore an **idea-level failure**: it must
  have triggered KILL-or-PIVOT upstream (L5/L7/L11), and if it survived to
  writing the run is mis-routed — return to `/experiment-execution`, do not
  write. The manuscript contains **no failure narrative**: discarded arms
  appear only as *process evidence* (ablation rows, design-space tables,
  "the promotion gate rejected candidate C because …" in Methods), never as
  headline sentences. Exception: papers whose contribution IS a two-sided
  finding (a method that wins on axis A and loses on axis B by design) —
  declare that in the contributions at phase 0 and both sides are then
  positive claims.
- **`claim_mode=attribution`** — the thesis is a measurement ("how much does
  X contribute?"). A measured null IS the positive result; write it in
  discovery voice per paper-writing rule 2b (instrument + established fact),
  never in failure voice.

Either mode: the DATA is never hidden (full grids ship in results/ and the
appendix); only the *narrative protagonist* changes. Selective reporting of
numbers stays a gate failure in both modes.

## 9. Canonical manuscript shape (v1.7.1)

Fixed section order, no extras in the body:

```
Abstract → 1 Introduction → 2 Related Work → 3 Method →
4 Experimental Setup → 5 Results and Analysis → 6 Conclusion →
References → Data and Code Availability → Funding
```

- `Data and Code Availability` and `Funding` are written as short placeholders
  when unknown ("Data and code will be released upon acceptance." / "The
  authors declare no funding." — the user's instruction: write `no`/blank,
  never invent).
- **Appendix is a SEPARATE LaTeX file compiled to its own PDF**
  (`paper/appendix.tex` → `appendix.pdf`); extended tables, extra robustness,
  proofs live there. The body cites it ("Appendix A, separate file") and never
  inlines it. Body length budget follows the declared tier (short 6–9 /
  standard ≤12 / long ≤15) WITHOUT a trim loopback: over-band is a WARN with
  a disclosure line, not a rewrite cycle (the negative-optimization tax).
- No reviewer-facing apparatus in the manuscript: no "we thank the
  reviewers", no response-letter residue, no over-explanation of the
  pipeline. One sentence of setup where a reader needs it; everything else
  is evidence.

## 10. Native-voice polish (v1.7.1)

Final pass before compile, in this order: (a) delete every sentence that
only restates a previous one (redundancy is the #1 AI tell); (b) convert
nominalizations to verbs where the verb is stronger; (c) vary sentence length
deliberately (burstiness check from writing-principles §0.5); (d) read each
paragraph aloud once — if it sounds like a template, rewrite the middle
sentence; (e) terminology consistency table (one term per concept, defined
once at first use). The target register is a native-speaking domain expert
writing for peers: dense, plain, confident, zero filler.

## See Also

- paper-writing rule 2b / self-check 12b (S2 disclosure voice — the corpus
  measurement this contract operationalizes)
- writing-principles §0.5/§0.6 (anti-AIGC, SCI body voice)
- figure-layout-contract / figure-quality-contract (rendering side)
- docs/SCIENTISTTWO_DISCLOSURE_ANALYSIS.md (evidence base)
