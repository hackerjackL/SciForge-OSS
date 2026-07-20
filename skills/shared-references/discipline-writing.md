# Discipline-Agnostic Writing Guide (SciForge-OSS)

> **Status**: Universal section-by-section writing guidance for all 125 science problems. Used by `/paper-writing` (Section-Specific Guidelines).
>
> **Key difference from main SciForge**: OSS has **no per-discipline writing guides** (no `discipline-writing/{physics,cs-ml,economics,general}.md`). All 125 problems use the **single unified guide below**. The agent's runtime reasoning handles domain-specific conventions (e.g., SI units for physics, regression tables for econ-flavored problems) — NOT a skill overlay.

---

## 1. Unified Section Structure

Every OSS paper draft (via `/paper-writing`) follows this canonical skeleton, loaded from `skills/support/paper-writing/templates/default/main.tex`:

| Section | Purpose | Length hint |
|---------|---------|-------------|
| **Title** | Concise, claim-flavored (not clickbait) | 1 line |
| **Abstract** | Problem → Approach → Key Result → Implication (4 sentences) | 150-250 words |
| **1. Introduction** | Motivation, known gap, this paper's contribution, roadmap | 1-1.5 pages |
| **2. Related Work** | Only verified citations (see `citation-discipline.md`); cluster by approach, not chronology | 0.5-1 page |
| **3. Problem Formalization** | Precise problem statement, notation, assumptions | 0.5-1 page |
| **4. Theory / Method** | Derivation chain (from `/theory-derivation` output), lemmas/theorems, proofs | 2-4 pages |
| **5. Results** | Verification outcomes (from `/logic-verification`), numerical sanity checks (from `/dynamic-sandbox`), figures (from `/unified-plotting`) | 2-4 pages |
| **6. Discussion** | What the result means, limitations, open questions | 0.5-1 page |
| **7. Conclusion** | One-paragraph restatement of contribution + forward look | 0.25 page |
| **References** | `.bib` only from `literature/references.bib` (3-layer-verified) | n/a |
| **Appendix** (optional) | Long proofs, extended numerical tables, code listings | varies |

---

## 2. Universal Writing Principles

### 2.1 Every claim has support

| Claim type | Acceptable support | Unacceptable |
|------------|---------------------|--------------|
| Theoretical claim | A lemma/theorem + proof from `/theory-derivation` output | "It is well-known that..." |
| Numerical claim | A `/dynamic-sandbox` output with preserved code + seed | "Numerical experiments show..." (no code) |
| Literature claim | A `\cite{key}` from the verified `references.bib` | "Previous work has shown..." (no cite) |
| Logical claim | A `/logic-verification` 6-dim audit PASS | "By intuition..." |

### 2.2 Notation hygiene

- **`\input{math_commands}`** from the unified template — never hand-define `\R`, `\E`, `\vx`, etc. in the preamble
- Paper-specific notation goes in a `## Paper-Specific Notation` block at the end of `math_commands.tex` (not in `main.tex`)
- **One symbol = one meaning** throughout the paper. If you overload `\phi` (eigenvector vs scalar field), rename one.
- State the **font convention** once in Section 3: bold = vectors ($\vx$), roman = operators ($\tr$), calligraphic = sets ($\cX$), blackboard bold = number systems ($\R$).

### 2.3 Figure standards (universal)

| Property | Rule |
|----------|------|
| Format | Vector PDF preferred; SVG acceptable when AI-direct-generated |
| Palette | **Morandi** house palette for categorical/semantic colors (see `color-themes.md` Layer 1) |
| Data-encoding colormaps | viridis / magma / plasma for continuous scalar fields (see `color-themes.md` Layer 2) — **never** jet / rainbow / hsv |
| Caption | Self-contained: "Figure N. What + key takeaway. (a) subpanel label. Parameters: ..." |
| Reference | `\cref{fig:label}` (cleveref loaded in unified template) — never hardcoded "Figure 3" |
| Placement | `\begin{figure}[t]` top-of-page for single-column; `[!ht]` only when content demands |
| Code provenance | Every figure preserves its render script + input data (see `output-versioning.md`) |

### 2.4 Equation standards

- Number only equations that are **referenced** later (by `\cref{eq:label}`). Unnumbered for one-off derivations.
- `\cref{eq:label}` for cross-reference — never "as seen in equation (3)".
- Long derivations go in **Appendix**; main text carries only the load-bearing equations.

### 2.5 Table standards

- `booktabs` rules only (`\toprule`, `\midrule`, `\bottomrule`) — no vertical bars, no `\hline`
- Numeric columns right-aligned; text columns left-aligned
- Significance stars (when relevant): `***` p<0.01, `**` p<0.05, `*` p<0.10 — state the convention once in a caption note
- Every table cites its data source in the caption

### 2.6 Citation standards

- **Only** `\cite{key}` (numeric default) or `\citep{}`/`\citet{}` (author-year, if user requests) — never both in one paper
- Every `key` must exist in `literature/references.bib` (3-layer-verified per `citation-discipline.md`)
- **Never** `\cite{forthcoming}`, `\cite{TODO}` — no unverified references
- Reference list is auto-generated from `.bib` via `\bibliography{references}` — never hand-edit the references section

---

## 3. Domain-Specific Conventions (Agent Runtime Judgment, Not Skill Overlay)

The agent applies these conventions at runtime based on the problem's domain — there is **no** per-discipline skill switch:

| If the problem is... | Then apply these conventions (agent judgment, not enforced) |
|----------------------|-------------------------------------------------------------|
| **Physics-flavored** (mechanics, EM, quantum) | SI units stated once; conservation laws referenced; viridis/magma for field plots; scale bars on micrographs; PNV reasoning style in Section 4 (Premise → Numerical method → Verification) |
| **Math-flavored** (analysis, algebra, geometry) | Theorem-Lemma-Proposition environments from unified template; full proofs in main text when < 1 page, else Appendix; counterexample search in Section 5 |
| **CS/ML-flavored** (algorithms, learning theory) | Architecture diagram early in Section 4; ablation table in Section 5; complexity analysis (time/space); reproducibility statement (code + seed + hardware) |
| **Biology/Medicine-flavored** | Mechanism description in Section 4; statistical significance + effect size in Section 5;伦理 statement if human/animal data |
| **Earth/Climate-flavored** | Spatial/temporal resolution stated; uncertainty quantification; baseline period comparison |
| **Social/Behavioral-flavored** | Identification strategy stated (if causal claim); robustness checks; sample selection discussion |
| **Chemistry/Materials-flavored** | Reaction scheme as figure; characterization methods (XRD/SEM/etc.) in Section 4; reproducibility via preserved synthesis protocol |
| **Cross-disciplinary** | Borrow the conventions of each domain relevant to the problem; flag any conflict in Section 6 |

---

## 4. Language

- Default: **English** (universal scientific lingua)
- If the human user passes `language: chinese` to `/125-problems-pipeline`, the entire draft is in Chinese (abstract + body); equations and citations remain in standard LaTeX/math notation
- Never mix languages within a paper

---

## 5. Boundaries

**Never**:
- Reintroduce a `discipline-writing/{physics,cs-ml,economics,general}.md` per-discipline guide. OSS is single-guide by design.
- Hand-define math macros in `main.tex` preamble — use `\input{math_commands}` from the unified template
- Use jet / rainbow / hsv colormaps — they create artificial visual boundaries (see `color-themes.md`)

**Always**:
- Load the unified `templates/default/main.tex` skeleton first, then fill sections — do not hand-write the preamble
- Preserve every figure's render script + input data alongside the PDF
- Run `/citation-audit` on the final draft — every `\cite{key}` must resolve to a verified `.bib` entry

---

## 6. See Also

- [`venue-profiles.md`](venue-profiles.md) — the single elsarticle template spec (no venue families)
- [`writing-principles.md`](writing-principles.md) — general academic writing style (universal, copied from main SciForge)
- [`citation-discipline.md`](citation-discipline.md) — 3-layer anti-hallucination citation verification
- [`color-themes.md`](color-themes.md) — morandi palette + Layer 2 data-encoding colormaps
