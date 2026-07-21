# Discipline-Agnostic Writing Guide (SciForge-OSS)

> **Status**: Universal section-by-section writing guidance for all science problems. **Domain-adaptive** — the writing style adapts based on the domain signature extracted by `/domain-signature`. Used by `/paper-writing` (Section-Specific Guidelines).
>
> **Key difference from main SciForge**: OSS has **no per-discipline writing guides** (no `discipline-writing/{physics,cs-ml,economics,general}.md`). Instead, the domain signature automatically selects the appropriate writing conventions. The agent's runtime reasoning handles domain-specific details (e.g., SI units for physics, regression tables for econ-flavored problems) — NOT a skill overlay.

---

## 0. Domain-Adaptive Writing

The domain signature (from `/domain-signature`) automatically selects writing conventions. The table below shows how the signature affects writing:

| Domain Signature Signal | Effect on Writing |
|------------------------|-------------------|
| `evidence_type: causal_inference` | Emphasis on identification strategy, robustness checks, endogeneity discussion |
| `evidence_type: derivational` | Theorem-Lemma-Proof structure, formal notation, minimal prose |
| `evidence_type: experimental` | Methods section with detailed protocol, results with statistical tests |
| `evidence_type: simulational` | Model description, parameter choices, convergence analysis |
| `evidence_type: interpretive` | Argument structure, counter-argument handling, evidence weighting |
| `writing_style: empirical_economics` | AER-style: theory → empirical strategy → results → discussion |
| `writing_style: physical_sciences` | PRL-style: concise, results-first, methods at end |
| `writing_style: formal_math` | Theorem → Lemma → Proof → Corollary chain |
| `citation_format: author_year` | Use `\citep{}`/`\citet{}` (elsarticle-harv) |
| `citation_format: numeric` | Use `\cite{}` (elsarticle-num) |

### Signature-Driven Writing Rules

```markdown
## Domain-Adaptive Rules

### If evidence_type = "causal_inference" (经济学/社科/流行病学)
- Section 4 must include "Identification Strategy" subsection
- Section 5 must include "Robustness Checks" subsection
- Discuss endogeneity, selection bias, and reverse causality
- Use author-year citations (elsarticle-harv)

### If evidence_type = "derivational" (数学/理论物理/理论CS)
- Section 4 is "Main Results" with Theorem-Lemma-Proposition environments
- Section 5 is "Proofs" (short proofs inline, long proofs in Appendix)
- No "Results" section — replaced by theorem statements
- Use numeric citations (elsarticle-num)

### If evidence_type = "experimental" (医学/生物学/心理学)
- Section 4 is "Methods" with detailed protocol
- Section 5 is "Results" with statistical tests
- Include power analysis, blinding status, exclusion criteria
- Use numeric citations (elsarticle-num)

### If evidence_type = "simulational" (物理/气候/工程)
- Section 4 is "Model" with governing equations
- Section 5 is "Simulation Results" with convergence analysis
- Include parameter choices, grid resolution, uncertainty quantification
- Use numeric citations (elsarticle-num)

### If evidence_type = "interpretive" (人文/社科/法学)
- Section 4 is "Argument" with claim-evidence-counterargument structure
- Section 5 is "Analysis" with evidence weighting
- Discuss alternative interpretations explicitly
- Use author-year citations (elsarticle-harv)
```

---

## 1. Unified Section Structure

The section structure depends on `verification_type` (set by the orchestrator based on the problem type).

### 1a. Standard Structure (computational / theory_experiment)

Every OSS paper draft with numerical or experimental verification follows this canonical skeleton:

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

### 1b. Theory-Only Structure (theory_only)

For pure theory problems (no experiments, no numerical verification), use this structure:

| Section | Purpose | Length hint |
|---------|---------|-------------|
| **Title** | Descriptive, theorem-focused (not clickbait) | 1 line |
| **Abstract** | Problem → Approach → Key Theorem → Implication (4 sentences) | 150-250 words |
| **1. Introduction** | Motivation, known gap, this paper's contribution, roadmap | 1-1.5 pages |
| **2. Preliminaries** | Notation, assumptions, definitions, known results | 1-2 pages |
| **3. Main Results** | Theorem/Proposition/Lemma statements with proof sketches | 2-4 pages |
| **4. Proofs** | Full derivations (short proofs inline, long proofs in Appendix) | 2-6 pages |
| **5. Discussion** | Implications, limitations, open problems, connections to related work | 0.5-1 page |
| **6. Conclusion** | One-paragraph restatement of contribution + forward look | 0.25 page |
| **References** | `.bib` only from `literature/references.bib` (3-layer-verified) | n/a |
| **Appendix** (optional) | Long proofs, lemmas, extended derivations | varies |

**Key differences from standard structure:**
- No "Related Work" section — context is integrated into Introduction and Discussion
- No "Results" section — replaced by "Main Results" (theorem statements) and "Proofs"
- "Preliminaries" replaces "Problem Formalization" — sets up notation and assumptions
- Proofs are the core contribution, not verification results

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
- If the human user passes `language: chinese` to `/auto-pipeline`, the entire draft is in Chinese (abstract + body); equations and citations remain in standard LaTeX/math notation
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
