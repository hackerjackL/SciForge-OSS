# Venue Profiles (SciForge-OSS — Single Template, Content-Focused)

> **Status**: Single Source of Truth for the OSS paper output format. Consumed by `/paper-writing`, `/paper-compile`. OSS uses **one unified `elsarticle` template** for all 125 science problems. There are no venue-specific `.cls`/`.sty`/`.bst` files and no per-discipline overlay. The final output is **LaTeX** via the unified `elsarticle` document class.
>
> **Scope boundary (explicit — what is NOT our job)**: OSS produces a **content-complete, citation-verified, logic-verified, code-reproducible** preprint-grade manuscript. The following are **the human senior researcher's responsibility, NOT ours** — OSS deliberately does not constrain them:
> - **Journal template / `.cls` selection** (Nature/PRL/IEEE/ACM/Cell) — the human swaps to the target journal's class at submission time; OSS gives them clean elsarticle source to port.
> - **Figure palette micro-tuning** (the single morandi+viridis house style is fixed; the human can recolor at submission).
> - **Page-limit strict conformance** (OSS targets 8-15 flexible; the human trims to the venue's exact limit).
> - **Anonymization / double-blind** (OSS outputs are researcher-facing; the human anonymizes if the venue requires).
> - **IRB / ethics / human-subjects / animal-subjects** approval statements.
> - **DOI automation, Zenodo/OSF archival, public data deposition**.
> - **Pre-registration (AEA/OSF/AsPredicted)**, **ORCID**, **CRediT author-contribution**, **COI** statements.
>
> **What IS our job (content + code rigor — the focus of this v3.2 upgrade)**: every claim has support; every citation is real (3-layer anti-hallucination); every conclusion is logic-verified; experiment code is leakage-audited + dry-run-gated; the contribution is honestly positioned against the current research frontier; the reviewer-independence layer breaks domain blind spots. These are the content/code quality bars that determine whether a senior researcher can *use* the draft — and they are what v3.2 strengthens.
>
> **v2.1 — Mode selector on top of the single skeleton**: the section *set* (which sections, which order, theorem/figure emphasis, page band) is chosen by a **5-mode selector** (`theory`/`experiment`/`computational`/`survey`/`hybrid`) driven by `verification_type` + `evidence_type` from `domain-signature.json`. One skeleton, one document class, five section-layout modes, zero discipline hardcode. See [`paper-modes.md`](paper-modes.md).

---

## 1. The Single Template: `elsarticle` (preprint)

All 125 science problems draft in the **same** LaTeX skeleton:

| Property | Value |
|----------|-------|
| Document class | `\documentclass[preprint,12pt]{elsarticle}` |
| Bibliography style | `\bibliographystyle{elsarticle-num}` (numeric citations, default) |
| Citation command | `\cite{key}` (elsarticle native numeric) |
| Bibliography style (alt) | `\bibliographystyle{elsarticle-harv}` (author-year, if the human user requests it for a humanities-style problem) |
| Citation command (alt) | `\citep{key}` / `\citet{key}` (elsarticle native author-year) |
| Page target | **8-15 pages, flexible** — no strict venue limit during drafting (human trims at submission) |
| Anonymous | No (OSS outputs are researcher-facing; human anonymizes if venue requires) |
| Figures | Vector PDF preferred; SVG acceptable when AI-direct-generated (see `color-themes.md` for the fixed house palette) |
| Math | `amsmath`, `amssymb`, `amsthm`, `mathtools` + shared `math_commands.tex` |
| Theorems | `theorem`/`proposition`/`lemma`/`corollary`/`definition`/`assumption`/`remark` environments |
| Section structure | Title → Abstract → Introduction → Problem Formalization → Theory/Method → Results → Discussion → Conclusion → References → Appendix |

**Hard rule**: Never invoke the standalone `natbib` or `cite` packages directly. elsarticle provides both numeric and author-year citation natively. Mixing the two families in one paper is forbidden.

---

## 2. The Unified Template Skeleton

Located at `skills/support/paper-writing/templates/default/main.tex` (copied from main SciForge's unified template). The skeleton provides:

- `\documentclass[preprint,12pt]{elsarticle}` preamble
- Math + typography package loads
- Theorem environments
- `\input{math_commands}` for shared notation
- `\begin{frontmatter}` ... `\end{frontmatter}` block (title, authors, abstract, keywords)
- `\input{sections/...}` for each section
- `\bibliographystyle{elsarticle-num}` + `\bibliography{references}`
- `\appendix` block

The agent **copies this skeleton** to the working directory and fills in the section files. It does NOT hand-write the preamble.

---

## 3. Page Target (mode-aware — see `paper-modes.md` §5)

The page target is **no longer a single table here** — it is mode-aware. The mode (`theory`/`experiment`/`computational`/`survey`/`hybrid`) is selected at `/paper-writing` entry per [`paper-modes.md`](paper-modes.md) §2, then the `length` parameter (`short`/`standard`/`long`) picks the band within that mode.

| Mode | Short | Standard | Long |
|------|-------|----------|------|
| `theory` | 4-6 | 4-8 | 15-25 (full proofs in appendix) |
| `experiment` | 6-8 | 8-12 | 12-16 |
| `computational` | 6-8 | 8-12 | 12-16 |
| `survey` | 10-12 | 15-20 | 20-25 |
| `hybrid` | 8-10 | 10-14 | 14-18 |

Page counts are main body only; refs/appx not counted. The superseded single-table form is retained below for historical reference only — prefer the mode-aware table above.

| Category (legacy) | Page Target | Page Count Rule |
|----------|-------------|----------------|
| **OSS default** (computational / theory_experiment) | **8-15 pages, flexible** | Main body only; refs/appx NOT counted |
| **Theory-only** (pure theory, no experiments) | **4-8 pages** (short) or **15-25 pages** (with full proofs in appendix) | If the problem is a tight derivation, 4-8 pages suffice; if complete proofs are needed, expand to 15-25 |

---

## 4. Citation Style

| Style | When | Command | Bib style |
|-------|------|---------|-----------|
| **Numeric (default)** | All STEM problems — physics, CS, math, engineering, earth science | `\cite{key}` | `elsarticle-num` |
| **Author-year (optional)** | When the human user requests it for a problem with a humanities/social-science framing | `\citep{key}`, `\citet{key}` | `elsarticle-harv` |

**Never mix** numeric and author-year in one paper. Pick one at `paper-writing` start and keep it.

---

## 5. Submission-Time Venue Adaptation (Deferred)

When the human user **later** wants to submit the OSS output to a specific journal, the adaptation is minimal and **deferred to submission time**, not drafting:

| Change | How |
|--------|-----|
| Page limit | Trim or expand sections per the target journal's guide-for-authors |
| Bibliography style | Switch `\bibliographystyle{elsarticle-num}` → the journal's required `.bst` (e.g., `elsarticle-harv` for economics, or the journal's own) |
| Document class options | Adjust `\documentclass` options (e.g., `[final]` for camera-ready, or the journal's mandated class) |
| Cover letter / supplementary | Add per journal requirements — outside the LaTeX draft |

This deferred-adaptation approach is why OSS does **not** maintain a Venue → Template Family mapping table (unlike main SciForge's 10+ family table). There is only one family: `elsarticle`.

---

## 6. Adding a New Problem-Specific Convention

If a 125-problem run needs a convention not in the unified template (e.g., a specific theorem environment for a math problem, or a chemistry reaction scheme):

1. Add it to the run's local `main.tex` preamble (not to the unified template skeleton)
2. Document the convention in the run's `PAPER_PLAN.md`
3. Do NOT modify the unified `templates/default/main.tex` skeleton — it stays discipline-agnostic

---

## See Also

- [`writing-principles.md`](writing-principles.md) — academic writing style guide (universal)
- [`citation-discipline.md`](citation-discipline.md) — 3-layer anti-hallucination citation verification protocol
- [`color-themes.md`](color-themes.md) — morandi palette + Layer 2 data-encoding colormaps
- [`assurance-contract.md`](assurance-contract.md) — PASS/WARN/FAIL/ERROR verdict schema
