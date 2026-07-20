# Venue Profiles (SciForge-OSS — Discipline-Agnostic, Single Template)

> **Status**: Single Source of Truth for the OSS paper output format. Consumed by `/paper-writing`, `/paper-compile`.
>
> **Key difference from main SciForge**: OSS uses **one unified template** for all 125 science problems. There are no venue-specific `.cls`/`.sty`/`.bst` files and no per-discipline overlay. The final output is **LaTeX** via the unified `elsarticle` document class. Venue differences (when the human user later targets a specific journal) are limited to `\documentclass` options and `\bibliographystyle{}` choice — and are deferred to submission time, not during drafting.

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
| Page target | **8-15 pages, flexible** — no strict venue limit during drafting |
| Anonymous | No (OSS outputs are researcher-facing, not journal-submission-ready) |
| Figures | Vector PDF preferred; SVG acceptable when AI-direct-generated (see `color-themes.md` for palette contract) |
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

## 3. Page Target

| Category | Page Target | Page Count Rule |
|----------|-------------|----------------|
| **OSS default** (computational / theory_experiment) | **8-15 pages, flexible** | Main body only; refs/appx NOT counted |
| **Theory-only** (pure theory, no experiments) | **4-8 pages** (short) or **15-25 pages** (with full proofs in appendix) | If the problem is a tight derivation, 4-8 pages suffice; if complete proofs are needed, expand to 15-25 |
| Short theoretical note | 4-6 pages | If the problem's answer is a tight derivation |
| Long survey-style | 15-25 pages | If the problem demands a literature-heavy treatment |

The agent picks the length based on the problem's nature and `verification_type`. The `length` parameter on `/paper-writing` accepts `short` / `standard` / `long` and maps to 4-6 / 8-12 / 12-16 pages (standard) or 4-6 / 4-8 / 15-25 (theory-only).

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
