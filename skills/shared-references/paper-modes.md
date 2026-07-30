# Paper Modes (SciForge-OSS — Single Skeleton, Mode Selector)

> **Status (v2.1)**: Single source of truth for the **paper mode selector**. Consumed by `/paper-writing` to pick the section layout, theorem emphasis, figure emphasis, and page target for a run. **Replaces** the old binary `theory-only vs standard` branch with a **5-mode selector** driven by `verification_type` + `evidence_type` from `domain-signature.json`.
>
> **Design contract** (the user's stated requirement): the writing *style* is already discipline-agnostic and adapts at runtime (see `discipline-writing.md`); what was missing was a *template* selector that picks the right section skeleton per problem shape without reintroducing per-discipline template families. This file provides exactly that — **one elsarticle skeleton, five section-layout modes, zero discipline hardcode**.

---

## 1. The Single Skeleton (Unchanged)

All modes draft from the **same** unified `elsarticle [preprint,12pt]` skeleton at `skills/support/paper-writing/templates/default/main.tex`. A mode does **not** swap the document class, the preamble, or `math_commands.tex`. A mode only changes:

1. **Which `sections/*.tex` files exist** (the section set)
2. **Section ordering and labels** (the `\input{...}` chain)
3. **Theorem-environment emphasis** (loaded already; modes emphasize different ones)
4. **Figure emphasis** (data plots vs proof diagrams vs survey tables)
5. **Page target band**

The skeleton's `\input{sections/...}` chain is **rewritten per mode** by the agent at run time — it copies the skeleton, then writes only the section files the chosen mode requires. The preamble stays frozen.

---

## 2. The Five Modes

| Mode | Trigger (signals, not discipline labels) | Shape | Page band |
|------|------------------------------------------|-------|-----------|
| `theory` | `verification_type=theory-only` AND `evidence_type=derivational` | Theorem→Lemma→Proof, no Results section | 4-8 (short) / 15-25 (with full proofs in appendix) |
| `experiment` | `evidence_type=experimental` (clinical/bench/trial) | Methods→Results with stats | 8-15 |
| `computational` | `verification_type=computational` OR `evidence_type=simulational` | Model→Numerical Results with convergence | 8-15 |
| `survey` | `evidence_type=interpretive` AND literature is the primary artifact (review/synthesis problem) | Taxonomy→Detailed Survey→Open Problems | 15-25 |
| `hybrid` | `verification_type=theory+experiment` OR ambiguous/fallback | Theory section + Experiment section combined | 10-18 |

### Mode Selection Logic (deterministic, signal-driven)

The mode is selected at the `/paper-writing` entry from already-frozen signals produced upstream:

```
inputs:
  verification_type   ← from Phase 1 problem decomposition (frozen at Phase 0)
  evidence_type      ← from domain-signature.json (Phase 1b, sole writer)
  literature_is_primary  ← heuristic: literature/references.bib entries ≥ 40 AND idea is synthesis-flavored

mode selection (first match wins):
  if verification_type == theory-only AND evidence_type == derivational       → theory
  elif evidence_type == experimental                                          → experiment
  elif verification_type == computational OR evidence_type == simulational   → computational
  elif evidence_type == interpretive AND literature_is_primary                → survey
  elif verification_type == theory+experiment                                 → hybrid
  else                                                                        → hybrid   (fallback: most general)
```

**Why `hybrid` is the fallback**: it is the most general shape (theory + experiment both present), so when signals are ambiguous it produces a complete paper rather than forcing a premature theory-only or experiment-only cut. The agent may also accept an explicit `mode=` override from the human user; an explicit override wins over the heuristic.

**No discipline label is read.** A physics problem with `evidence_type=simulational` picks `computational`; a physics problem with `evidence_type=derivational` + `verification_type=theory-only` picks `theory`. The mode follows the *problem's evidence shape*, not its field.

---

## 3. Per-Mode Section Layouts

Each mode defines its section set. The agent writes exactly these `sections/*.tex` files and rewrites the `\input{...}` chain in the copied `main.tex` accordingly.

### 3.1 `theory` mode

| File | Section | Emphasis |
|------|---------|----------|
| `sections/0_abstract.tex` | Abstract (Problem→Approach→Key Theorem→Implication) | Theorem-statement-flavored |
| `sections/1_introduction.tex` | Introduction (motivation, gap, contribution, roadmap) | Context integrated, no separate Related Work |
| `sections/2_preliminaries.tex` | Preliminaries (notation, assumptions, definitions, known results) | Sets up notation once |
| `sections/3_main_results.tex` | Main Results (Theorem/Proposition/Lemma statements + proof sketches) | Theorem environments primary |
| `sections/4_proofs.tex` | Proofs (short inline; long → Appendix) | Proof chains |
| `sections/5_discussion.tex` | Discussion (implications, limitations, open problems) | Connections to related work |
| `sections/6_conclusion.tex` | Conclusion | One-paragraph restatement |
| `sections/A_appendix.tex` | Appendix (long proofs, lemmas, extended derivations) | Optional but typical for full proofs |

**No Related Work section.** No Results section (replaced by Main Results + Proofs). Numeric citations (`elsarticle-num`) default.

### 3.2 `experiment` mode

| File | Section | Emphasis |
|------|---------|----------|
| `sections/0_abstract.tex` | Abstract (Problem→Protocol→Key Finding→Implication) | Result-flavored |
| `sections/1_introduction.tex` | Introduction | Motivation + gap + contribution |
| `sections/2_related_work.tex` | Related Work | Clustered by approach |
| `sections/3_problem_formalization.tex` | Problem / Hypothesis Formalization | Hypothesis stated, variables defined |
| `sections/4_methods.tex` | Methods (protocol, materials, power analysis, blinding, exclusion) | Detailed protocol |
| `sections/5_results.tex` | Results (statistical tests, effect sizes, CIs) | Stats tables + figures |
| `sections/6_discussion.tex` | Discussion (endogeneity/limitations/generalizability) | Robustness discussed |
| `sections/7_conclusion.tex` | Conclusion | One paragraph |
| `sections/A_appendix.tex` | Appendix (extended tables, protocol deviations) | Optional |

**Mandatory**: power/size statement in Methods; effect size + CI in Results (not just p-values).

### 3.3 `computational` mode

| File | Section | Emphasis |
|------|---------|----------|
| `sections/0_abstract.tex` | Abstract (Problem→Model→Key Numerical Finding→Implication) | Convergence-flavored |
| `sections/1_introduction.tex` | Introduction | Motivation + gap + contribution |
| `sections/2_related_work.tex` | Related Work | Prior numerical/sim work |
| `sections/3_problem_formalization.tex` | Problem Formalization (governing equations, boundary conditions) | Model stated |
| `sections/4_model.tex` | Model / Numerical Method (discretization, solver, parameters) | Method + parameter choices |
| `sections/5_numerical_results.tex` | Numerical Results (convergence study, mesh/resolution independence, benchmarks) | Convergence tables + field plots |
| `sections/6_discussion.tex` | Discussion (uncertainty quantification, limitations) | UQ stated |
| `sections/7_conclusion.tex` | Conclusion | One paragraph |
| `sections/A_appendix.tex` | Appendix (extended grids, solver details) | Optional |

**Mandatory**: convergence/mesh-independence statement; benchmark against analytical or reference solution when available.

### 3.4 `survey` mode

| File | Section | Emphasis |
|------|---------|----------|
| `sections/0_abstract.tex` | Abstract (Scope→Taxonomy→Key Synthesis→Open Problems) | Synthesis-flavored |
| `sections/1_introduction.tex` | Introduction (scope, why now, methodology of the survey) | Inclusion criteria stated |
| `sections/2_background.tex` | Background (foundational definitions, prior surveys) | Frames the field |
| `sections/3_taxonomy.tex` | Taxonomy (the organizing framework of the field) | The contribution of a survey |
| `sections/4_detailed_survey.tex` | Detailed Survey (clustered by approach, not chronology) | Longest section |
| `sections/5_open_problems.tex` | Open Problems & Future Directions | Actionable, not vague |
| `sections/6_conclusion.tex` | Conclusion | One paragraph |
| `sections/A_appendix.tex` | Appendix (extended comparison tables, glossary) | Optional |

**Mandatory**: inclusion/exclusion criteria in Introduction; a comparison table across approaches in Detailed Survey or Appendix. Author-year citations (`elsarticle-harv`) recommended.

### 3.5 `hybrid` mode

| File | Section | Emphasis |
|------|---------|----------|
| `sections/0_abstract.tex` | Abstract (Problem→Theory→Experiment→Key Finding→Implication) | Both halves |
| `sections/1_introduction.tex` | Introduction | Motivation + gap + contribution |
| `sections/2_related_work.tex` | Related Work | Clustered by approach |
| `sections/3_problem_formalization.tex` | Problem Formalization | Model + hypothesis |
| `sections/4_theory.tex` | Theory / Derivation (lemmas/theorems + proof sketches) | Theory half |
| `sections/5_experiments.tex` | Experiments (protocol + results that test the theory) | Experiment half — MUST connect back to Section 4 claims |
| `sections/6_discussion.tex` | Discussion (theory↔experiment agreement, limitations) | Reconciliation |
| `sections/7_conclusion.tex` | Conclusion | One paragraph |
| `sections/A_appendix.tex` | Appendix (long proofs + extended experiment tables) | Optional |

**Mandatory**: Section 5 MUST explicitly map each experimental result back to a theorem/claim in Section 4 (a `theory↔experiment reconciliation table` is recommended). This is the load-bearing constraint of hybrid mode — without it the two halves are disconnected.

---

## 4. Per-Mode Emphasis Matrix

| Mode | Theorem envs used | Figures emphasis | Tables emphasis | Citation style default |
|------|-------------------|------------------|-----------------|-------------------------|
| `theory` | theorem/lemma/proposition/corollary/definition | Proof-structure diagrams (rare) | (rare) | numeric (`elsarticle-num`) |
| `experiment` | (rare; `assumption` for model assumptions) | Data plots, protocol diagrams | Stats tables (booktabs) | numeric (`elsarticle-num`) |
| `computational` | `definition`/`assumption` for model setup | Field plots (viridis/magma), convergence curves | Convergence + parameter tables | numeric (`elsarticle-num`) |
| `survey` | `definition` for taxonomy terms | Comparison diagrams, taxonomy tree | Large comparison tables | author-year (`elsarticle-harv`) |
| `hybrid` | theorem/lemma + `assumption` | Both proof diagrams and data plots | Reconciliation table + stats | numeric (`elsarticle-num`) |

The theorem environments are **all loaded by the unified skeleton already** — modes only change *which ones the agent actually uses*, not the preamble. No mode adds a new package.

---

## 5. Page Target Bands

| Mode | Short | Standard | Long |
|------|-------|----------|------|
| `theory` | 4-6 | 4-8 | 15-25 (full proofs in appendix) |
| `experiment` | 6-8 | 8-12 | 12-16 |
| `computational` | 6-8 | 8-12 | 12-16 |
| `survey` | 10-12 | 15-20 | 20-25 |
| `hybrid` | 8-10 | 10-14 | 14-18 |

The `/paper-writing` `length` parameter (`short`/`standard`/`long`) selects the band within the mode. Default is `standard`.

---

## 6. Boundaries

- **Never** swap the document class per mode. One skeleton, `elsarticle [preprint,12pt]`, for all five modes.
- **Never** add a new package per mode. The unified preamble already covers theorem envs, math, booktabs, cleveref, graphicx.
- **Never** read a discipline label to pick a mode. The selection reads only `verification_type` + `evidence_type` + the `literature_is_primary` heuristic.
- **Never** run two modes in one paper. Pick one at `/paper-writing` start; keep it throughout. If the problem genuinely splits (half theory, half experiment), pick `hybrid` — do not blend two modes.
- **An explicit human `mode=` override wins** over the heuristic. The agent records the override reason in `PAPER_PLAN.md`.
- **The fallback is `hybrid`**, not `theory` — `hybrid` is the most complete shape and avoids a premature theory-only cut on ambiguous signals.

---

## 7. Relationship to Existing References

| Reference | Relationship |
|-----------|--------------|
| `venue-profiles.md` | Still the single-elsarticle spec (§1 skeleton, citation style, submission-time adaptation). This file adds the **mode selector on top**. `venue-profiles.md` §3 page-target table is superseded by §5 here for mode-aware bands. |
| `discipline-writing.md` | Still the universal section-by-section *writing style* guide. This file defines the *section set* (which sections, which order); `discipline-writing.md` defines *how to write each section*. They compose. |
| `writing-principles.md` | Still the general academic prose principles. Mode-agnostic. |

The old binary `theory-only vs standard` branch in `discipline-writing.md` §1a/§1b is **superseded** by the five modes here. `discipline-writing.md` is updated to defer section-set selection to this file.

---

## 8. See Also

- [`venue-profiles.md`](venue-profiles.md) — single elsarticle template spec (skeleton, citation, submission-time)
- [`discipline-writing.md`](discipline-writing.md) — universal section-by-section writing style
- [`writing-principles.md`](writing-principles.md) — academic writing principles (mode-agnostic)
- [`color-themes.md`](color-themes.md) — morandi palette + viridis/magma data colormaps
- [`citation-discipline.md`](citation-discipline.md) — 3-layer anti-hallucination citation verification
- [`../support/paper-writing/SKILL.md`](../support/paper-writing/SKILL.md) — consumer of this selector
- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — passes verification_type + evidence_type downstream
