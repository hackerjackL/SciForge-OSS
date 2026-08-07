# Venue Checklists (SciForge-OSS — Discipline-Agnostic, Single Template)

> **Status**: Pre-submission readiness checks for OSS papers. Used near the end of `/paper-writing` and during the final checks in `/paper-compile`.
>
> **Key difference from main SciForge**: OSS has **no per-venue checklists** (no NeurIPS-specific / IEEE-specific / PRL-specific / AER-specific lists). All science problems draft in the **unified `elsarticle` template** (see `venue-profiles.md`). This file provides a **single universal checklist** applied to every OSS output. Venue-specific adaptations (if the human user later targets a specific journal) are deferred to submission time, not drafting.

---

## 1. When to Read

- Read once when `/paper-writing` starts the draft — sets the universal requirements to keep in mind
- Read again before locking the outline — verify section structure matches the unified template
- Read again during `/paper-compile` final submission-readiness compile — verify zero warnings/zero errors

---

## 2. Universal Requirements (All Problems)

Across every OSS output, the following are usually expected:

- **anonymous submission** unless the human user explicitly requests author attribution (OSS outputs are researcher-facing drafts, not camera-ready)
- **references and appendices** outside the main page budget (8-15 pages main body, refs/appx NOT counted)
- **enough derivation detail for reproduction** — every theorem/lemma carries a proof or a pointer to the Appendix proof; every numerical claim has preserved code + seed
- **honest limitations and scope boundaries** — Section 6 (Discussion) must surface what the result does NOT prove, not just what it does
- **clear mapping from claims to evidence** — every claim in Abstract/Introduction maps to a Section 4 (Theory) or Section 5 (Results) item
- **3-layer-verified citations only** — every `\cite{key}` resolves to an entry in `literature/references.bib` that passed the arXiv → CrossRef → Semantic Scholar verification (see `citation-discipline.md`)

---

## 3. The Single Unified Checklist

Apply this checklist to every OSS paper draft, regardless of the problem it addresses.

### 3.1 Structure checklist

- [ ] Title is claim-flavored and concise (not clickbait, not overly hedged)
- [ ] Abstract has 4 sentences: Problem → Approach → Key Result → Implication (150-250 words)
- [ ] Section 1 (Introduction) states the known gap and this paper's contribution in the first 1.5 pages
- [ ] Section 2 (Related Work) clusters by approach, not chronology; only verified citations
- [ ] Section 3 (Problem Formalization) states notation, assumptions, the precise problem
- [ ] Section 4 (Theory/Method) carries the derivation chain from `/theory-derivation` output
- [ ] Section 5 (Results) carries verification outcomes from `/logic-verification` + numerical sanity from `/dynamic-sandbox` + figures from `/unified-plotting`
- [ ] Section 6 (Discussion) states limitations honestly
- [ ] Section 7 (Conclusion) is one paragraph restating contribution + forward look
- [ ] References auto-generated from `references.bib` (never hand-edited)
- [ ] Appendix (optional) carries long proofs, extended tables, code listings

### 3.2 LaTeX checklist (unified `elsarticle` template)

- [ ] `\documentclass[preprint,12pt]{elsarticle}` — the unified template is loaded
- [ ] `\input{math_commands}` — shared notation loaded, no hand-defined macros in preamble
- [ ] `\bibliographystyle{elsarticle-num}` (default) OR `\bibliographystyle{elsarticle-harv}` (if user requested author-year) — never both
- [ ] `\cite{}` (numeric) OR `\citep{}`/`\citet{}` (author-year) — never mix in one paper
- [ ] `\cref{eq:label}` / `\cref{fig:label}` for cross-reference — cleveref loaded after hyperref
- [ ] Theorem environments from unified template: `theorem`/`proposition`/`lemma`/`corollary`/`definition`/`assumption`/`remark`
- [ ] Every `\cite{key}` resolves to a verified `references.bib` entry

### 3.3 Figure checklist (universal — morandi palette)

- [ ] Every figure is vector (PDF) or SVG (when AI-direct-generated) — never raster PNG for publication
- [ ] Categorical/semantic colors use **morandi** house palette (see `color-themes.md` Layer 1, chroma C* ≤ 25)
- [ ] Continuous scalar fields use **viridis / magma / plasma** (see `color-themes.md` Layer 2) — never jet / rainbow / hsv
- [ ] Every figure caption is self-contained: "Figure N. What + key takeaway. (a) subpanel. Parameters: ..."
- [ ] Every figure preserves its render script + input data (see `output-versioning.md`)
- [ ] `\begin{figure}[t]` for single-column; `[!ht]` only when content demands

### 3.4 Equation checklist

- [ ] Only equations referenced later are numbered (`\cref{eq:label}`); one-off derivations unnumbered
- [ ] Long derivations in Appendix; main text carries only load-bearing equations
- [ ] One symbol = one meaning throughout; no overloading (if `\phi` is eigenvector, don't also use it for scalar field)

### 3.5 Table checklist

- [ ] `booktabs` rules only (`\toprule`, `\midrule`, `\bottomrule`) — no vertical bars, no `\hline`
- [ ] Numeric columns right-aligned; text columns left-aligned
- [ ] Significance stars (when relevant): `***` p<0.01, `**` p<0.05, `*` p<0.10 — convention stated once in a caption note
- [ ] Every table cites its data source in the caption

### 3.6 Citation checklist (3-layer anti-hallucination)

- [ ] Every `key` in `\cite{key}` exists in `literature/references.bib`
- [ ] `.bib` entries all carry the `verification_status: verified` tag from `/universal-retrieval`
- [ ] No `\cite{forthcoming}`, `\cite{TODO}`, `\cite{arxiv:TODO}` — no unverified references
- [ ] Run `/citation-audit` on the final draft — every cite re-resolves to a live arXiv/CrossRef/S2 source

### 3.7 Compile checklist (`/paper-compile` — zero warnings zero errors)

- [ ] `latexmk -C` clean, then full compile — no stale `.aux`/`.bbl` artifacts
- [ ] **Zero warnings, zero errors** at `assurance=submission` (see `assurance-contract.md`)
- [ ] Overfull hbox in main body / appendix / bibliography — all fixed (no exemption at submission)
- [ ] Undefined references (`??` in PDF) — all resolved
- [ ] Missing bibliography entries — all resolved
- [ ] Anti-deadloop: if a warning persists after 3 fix attempts (per-warning), emit `COMPILE_REPORT.json` with `verdict: BLOCKED, reason_code: unresolved_warning_<type>, attempts: 3` and surface to the human user — do NOT silently retry past attempt 3

### 3.8 Logic checklist (universal invariant)

- [ ] **INV-G1 PROBLEM_ANCHOR_FREEZE** — every claim in the paper traces back to the original problem statement (user-supplied Q-id). No drift to a different problem mid-paper.
- [ ] No unsupported assertion — every claim has a `\cref{eq:}`, `\cref{fig:}`, or `\cite{}` support
- [ ] No verification-premise contradiction (universalized Type IV escape check) — if the verification (Section 5) contradicts the premise (Section 3), this is a fatal error, not a "discussion point"

---

## 4. Submission-Time Venue Adaptation (Deferred, Optional)

If the human user **later** wants to submit the OSS output to a specific journal, apply these adaptations at submission time — NOT during drafting:

| Target venue type | Adaptation | When |
|---------------------|------------|------|
| Specific journal (PRL, NeurIPS, AER, etc.) | Check the journal's guide-for-authors; trim/expand to page limit; switch `\bibliographystyle{}` if required; add cover letter | After OSS draft is complete and human-validated |
| Conference (ICLR, CVPR, etc.) | Apply conference anonymization; trim to page limit; add reproducibility checklist if required | After OSS draft is complete |
| arXiv preprint | No adaptation — OSS output is already arXiv-compatible (elsarticle preprint) | Direct upload |

**Never** maintain a Venue → Checklist mapping table (main SciForge has 10+ venue-specific lists). OSS has one universal checklist above; venue-specific additions are deferred to the human's submission-time judgment.

---

## 5. Boundaries

**Never**:
- Reintroduce a per-venue checklist (NeurIPS-specific / IEEE-specific / PRL-specific / AER-specific). OSS is single-checklist by design.
- Use `revtex4-2`, `optica`, `IEEEtran`, or any other non-elsarticle document class during drafting. Submission-time class switch is the human's call, not the agent's.
- Use `\pacs{}`, `showpacs`, or other revtex-specific commands — they don't exist in elsarticle.

**Always**:
- Draft in the unified `elsarticle` template from `skills/support/paper-writing/templates/default/main.tex`
- Apply the universal checklist above to every OSS output
- Run `/citation-audit` + `/paper-compile` (submission-level) before declaring the draft ready

---

## 6. See Also

- [`venue-profiles.md`](venue-profiles.md) — the single elsarticle template spec (no venue families)
- [`discipline-writing.md`](discipline-writing.md) — universal section-by-section writing guide
- [`citation-discipline.md`](citation-discipline.md) — 3-layer anti-hallucination citation verification protocol
- [`color-themes.md`](color-themes.md) — morandi palette (Layer 1) + viridis/magma data colormaps (Layer 2)
- [`assurance-contract.md`](assurance-contract.md) — PASS/WARN/FAIL/ERROR verdict schema
