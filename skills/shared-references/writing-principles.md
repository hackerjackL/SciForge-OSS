# Writing Principles (SciForge-OSS — Condensed)

> **Core**: A paper is a short, rigorous, evidence-backed technical story. Every section serves the same core contribution.
>
> **v2.2.1 Publication grade and anti-engineering-report tone (hard user requirement)**: The paper must reach Nature / Science / Cell / major-sub-journal regular-issue / Q1 top SCI level — **not an engineering report, not a technical report, not an experiment log**. Discrimination test: if a passage reads like a step-by-step log of "we did X, then did Y, the output was Z", that is engineering-report tone, **forbidden**. A Nature-grade paper tells a **scientific story**: motivation → gap → insight → evidence → implication, and every paragraph carries narrative progression rather than step records. Prose must flow with rise and fall, alternating long and short sentences; the introduction hooks the reader, the discussion is honest but forceful. Page limits are never an excuse to degenerate into an engineering report — when over the page cap, compress redundancy, move figures into the appendix, tighten expressions; **never** sacrifice the prose-grade to hit a page count.

## 0. Per-Discipline Style Contract (v2.2.1 — a different style for every discipline)

Paper prose style **must adapt to the discipline** — same template skeleton, different prose flesh. Violating discipline style = one form of engineering-report tone.

| Discipline family | Style traits | Opening hook | Taboos (degenerate into an engineering report) |
|--------|---------|---------|-------------------------|
| **Humanities / social sciences / history / philosophy** | Narrative, interpretive, argument-driven; long sentences unfold the case, quotations serve as anchors; the author's stance is clear but not dogmatic | A paradox, a tension in the historical record, an unresolved interpretive dispute | Run-on "date-event-conclusion" listings; a stance-free objective-summary tone |
| **CS / ML / algorithms** | A clear method-results-ablation skeleton, but every section carries a "why designed this way" insight; complexity analysis is skeleton, not decoration | An unsolved capability boundary + the paper's insight that breaks through it | Pile-ups of architecture diagrams with no narrative; "we used technique X" with no motivation |
| **Physics / mathematics / theory** | Derivation-centered, theorem-lemma-proof chains; minimal and rigorous, every symbol defined; the results section is theorem statements, not an experiment log | A counterintuitive physical/mathematical fact + the paper giving its mechanism | Splitting a derivation into "step 1... step N" engineering tone; substituting an experiment log for a proof |
| **Medicine / biology / clinical** | A causal chain of mechanism → hypothesis → validation → clinical implication; statistics rigorous but in service of the mechanism narrative; ethics statements in place | A clinical pain point + the paper's mechanistic answer | Pure cohort description with no mechanism; listing p-values with no effect sizes and no clinical implication |
| **Materials / chemistry / engineering** | Structure-property relationships at the center; the synthesis-characterization-performance-mechanism quartet told as a discovery story | A materials-performance bottleneck + the paper's structural answer | Pure process-parameter tables with no scientific insight; "we measured XRD/SEM" with no problem driving it |
| **Earth / climate / astronomy** | Scale and process as the narrative axis; the observation-model-mechanism triad; uncertainty stated honestly rather than as a weakness | A cross-scale phenomenon + the paper connecting micro and macro | Pile-ups of data figures with no earth-science narrative; raw time-series listings |
| **Economics / social-science econometrics** | Identification strategy as the narrative core; theory → empirics → counterfactuals → policy implications; tables serve the causal story | The identification challenge of a causal question + the paper's strategy | Pure regression tables with no identification narrative; "we ran DiD" with no parallel-trends argument |

**Enforcement rule**: `/paper-writing` in Step 1 reads the `evidence_type` + `writing_style` fields of `domain-signature.json`, picks the style family from the table above, and writes it into the `writing_style` field of `PAPER_PLAN.md`. The whole manuscript follows that family's style. **Cross-disciplinary topics** (e.g., computational social science) pick the dominant family's style and state explicitly in Discussion §6 the conventions borrowed from secondary families.

## 0.5 Anti-AIGC Human-Voice Contract (v5.2)

**Field feedback**: the paper must not read as if written by AI — AIGC voice is a "not written by a human" signal that reviewers spot at a glance (it is a different disease from "engineering-report tone": report tone is **structure** that reads like a log, AI voice is **wording** that reads like a machine). This section gives a machine-checkable blacklist + positive human-voice traits + self-check hooks.

**AI-voice blacklist (any occurrence deducts self-check points; replace item by item)**:

| Class | English AI voice (typical) | Chinese AI voice (typical) | Human-voice replacement direction |
|------|-------------------|-------------------|-------------|
| Empty emphasis | "It is worth noting that", "Importantly,", "Notably," stacked at paragraph openings | Chinese stock openers equivalent to "it is worth noting that", "it should be pointed out that", "it is worth mentioning that" | State facts directly; let the evidence itself carry the emphasis |
| All-purpose verbs | "leverage", "utilize", "harness", "delve into", "facilitate" | Chinese equivalents of "utilize" (repeated in every paragraph), "empower", "boost", "delve into" | Use discipline-precise verbs (train / bound / identify / fit / define) |
| Over-embellishment | "comprehensive", "novel", "cutting-edge", "state-of-the-art" (when unsupported by citations) | Chinese equivalents of "comprehensive", "innovative", "pioneering", "of great significance" | Be specific: say newer than what, and new in what respect (SOTA only when citation-backed) |
| Structure-ese | "Firstly...Secondly...Finally..." mechanical enumeration running through the whole text; every paragraph isomorphic (claim sentence + three elaboration sentences + wrap-up sentence) | Chinese equivalents of "first... then... finally...", "on the one hand... on the other hand..." | Vary paragraph lengths (burstiness); reserve enumeration for genuinely parallel items |
| Balance-ese | Uninformative hedging of the "While X has advantages, it also has limitations" kind | The Chinese "although... but..." formula mushing every paragraph into a compromise | Take a clear stance: criticize where criticism is due, endorse where endorsement is due, with evidence |
| Punctuation-ese | ≥2 dash-parentheticals per paragraph; parallel semicolon chains; em-dash abuse | Dense em-dash insertions and stacked semicolon parallels (the fullwidth forms in Chinese prose) | ≤5 dashes across the whole text; delete any parenthetical that can be deleted |
| Summary-ese | "In summary, ..." at the end of every section restating the section's own content | Chinese equivalents of "to sum up", "in conclusion" recited at the end of every section | End sections by pointing to the logical step into the next section; no restating |

**Positive human-voice traits (paper-writing self-checks against these; each missing item deducts points)**:
1. **Sentence-length variance (burstiness)**: 5 consecutive sentences with too-low length variance (all 15-25 words) → AI-voice signal; human writing alternates long and short sentences (short sentences land conclusions, long sentences lay out arguments)
2. **Specificity density**: at least one concrete anchor per paragraph (number / citation / symbol / figure or table reference) — paragraphs of vague generalities are a breeding ground for AI voice
3. **Stance traces**: the Introduction and Discussion contain explicit "we argue / we reject" stance sentences (with evidence) — the hallmark of AI voice is stance-less smoothness
4. **Correct discipline jargon**: use discipline terms with their **in-discipline meaning** (per the §0 style family), not generic senses — "robust" means different things in CS and statistics; using it correctly is what makes writing human
5. **Citations woven into the narrative**: citations are load-bearing walls of the argument ("X proved..., but assumption Y does not hold, therefore..."), not decorative stacking ("see [1-15] for related work")

**Paper style vs report style discrimination test** (run on one sampled paragraph per section):
- **Report-style traits** (forbidden): organized by time/step order ("we first did A, then did B"); isolated description with nothing to compare against; results as bare numbers with no interpretation; methods as bare configurations with no motivation
- **Paper-style traits** (required): organized by argument logic ("to answer Q we need evidence E, because..."); every result has a comparison and an interpretation; every design choice has a motivation; every section advances the same story
- Test: replace the paragraph's subject "we" with "this paper argues" — if it no longer reads, it is report style (in paper style the subject is the argument itself, not the operator)

**Discipline-convention adaptation** (the §0 style families' "human voice" made concrete):
- **Humanities / social sciences**: first-person stance allowed ("the author argues" forms per the discipline's conventions); quotations must carry page numbers; arguments may contain interpretive inference (label the inference level); forcing a science-style "results-discussion" skeleton onto the paper is forbidden
- **CS / ML**: the contribution list may be enumerated, but each item must carry an evidence pointer; hyperparameter tables in the body narrative are forbidden (put them in a table/appendix)
- **Mathematics / theory**: the definition-lemma-theorem-proof chain is human voice itself; "we propose a theorem"-style empty claims are forbidden (theorems must be stated in full)
- **Medicine / biology**: mechanism narratives must carry statistical evidence; ethics/data-availability statements in place are the compliance markers of a "human author" in this field
- **Economics / econometrics**: the parallel-trends/exogeneity argument for the identification strategy is the core of human voice in this field — skipping identification arguments and reporting coefficients directly = AI voice

**Self-check hooks** (additions to the `/paper-writing` Step 5 self-check list; results written into the `aigc_scan` field of `.sciforge/verdicts/PAPER_CLAIM_AUDIT.json`):
1. Blacklist scan: count phrases of each AI-voice class from the table above across the whole text; any class ≥3 occurrences → WARN; any class ≥6 occurrences → FAIL (`reason_code: aigc_phrasing`), then replace item by item and rescan
2. Sentence-length variance spot check: sample 10 consecutive sentences per section and compute the sentence-length standard deviation; sections with std < 5 words → WARN (`sentence_monotony`)
3. Report-style spot check: run the discrimination test on one sampled paragraph per section; report-style paragraph → WARN (`report_style`); Introduction or Discussion entirely in report style → FAIL
4. Dash/parenthetical count: > 5 dashes across the whole text → WARN

## Narrative principles

- The core contribution must be statable in one sentence; otherwise the framework has not converged
- Every section serves the same story, rather than starting a second one
- Experiments / related work / discussion support the main claim, rather than being independent mini-papers

**One-sentence contribution test**: if you cannot write a sentence like the following, the framework is too loose:
- "We prove that X converges under assumption Y"
- "We show that method A improves B by 15% on benchmark C"

## Time allocation

- Abstract / introduction / figures / everything else ≈ 25% effort each
- Reviewer reading order: title → abstract → introduction → Figure 1 → the rest
- If the first two pages are unclear, nobody sees the highlights later on

## Abstract (5-sentence formula)

1. What was achieved
2. Why the problem matters and is hard
3. How it is solved
4. What evidence supports it
5. What number/result the reader should remember

**Bad opening**: the first sentence could be pasted onto any paper → delete it

## Introduction structure

- **Paragraph 1**: broad context + problem definition
- **Paragraph 2**: known approaches and their limitations
- **Paragraph 3**: our method + core contribution
- **Paragraph 4**: roadmap of the paper

**Bad introduction**: no concrete contribution on page 1 → lose the reader

## Sentence-level clarity

- Subject-verb-object structure, subject at the start of the sentence
- Avoid "it is known that", "it has been shown that"
- One idea per sentence
- Follow long sentences with short ones to create rhythm

## Mathematical writing

- Define every symbol once; do not overload
- Number only equations that are referenced
- Keep only key derivation steps in the body; long derivations go to the appendix
- Theorems must have explicit assumptions + a proof or a citation

## Figure and table design

- Vector graphics (PDF/SVG), not raster
- Morandi palette (Layer 1) or viridis/magma data heatmaps (Layer 2)
- Self-contained captions: Figure N. content + key takeaway + (a)(b) panel notes
- Keep the rendering script + input data for every figure

## Common mistakes

- Related work written as a pile-up of papers → cluster by topic, not by chronology
- Dishonest discussion → must state what the results do not prove
- Unverified citations → every citation passes the 3-layer anti-hallucination verification
- Overclaiming → the claim scope must match the evidence scope

## Pre-submission checklist

- Abstract of 4-5 sentences containing concrete numbers/results
- Concrete contribution on page 1 of the introduction
- Every claim backed by \cite{} or \cref{eq:}
- No undefined symbols
- All citations exist in references.bib and are verified
- No \cite{TODO}, \cite{forthcoming}
- Morandi palette or Layer 2 data heatmap
- Limitations stated honestly in the Discussion
