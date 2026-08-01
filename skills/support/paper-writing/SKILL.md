---
name: paper-writing
description: "Compose the academic paper from research artifacts via unified elsarticle template + 5-mode selector + v3.2 frontier-gap-consuming Introduction. Phase 12. Invoke when research artifacts are ready to assemble the manuscript."
type: support-skill
role: paper-composer
---

# Paper Writing (SciForge-OSS — Unified elsarticle Template, Discipline-Agnostic)

## Quick Reference

- **Purpose**: 从研究产物组装学术论文 (LaTeX)，统一 elsarticle 模板
- **Input**: 研究产物 (derivation_output.md + CLAIMS_FROM_RESULTS.md + figures/)
- **Output**: paper/main.tex + paper/sections/*.tex + paper/PAPER_PLAN.md
- **Key**: v2.1 五模式选择器 (theory/experiment/computational/survey/hybrid)；verification_type 驱动（见 [paper-modes.md](../../shared-references/paper-modes.md)）

> **Status**: Composes the final academic paper from research artifacts. **OSS uses a single unified `elsarticle` template** (copied from main SciForge's `templates/default/`) — no venue-specific templates, no per-discipline writing guides. **OSS is discipline-agnostic** — the universal section-by-section writing guide in [`discipline-writing.md`](../../shared-references/discipline-writing.md) applies to every run.
>
> **Key OSS difference from main SciForge**: main SciForge has 10+ venue families (NeurIPS / ICLR / PRL / AER / etc.) each with its own page limit, bibliography style, anonymization rule. OSS has **one** template (`elsarticle [preprint,12pt]` + `elsarticle-num.bst`) applied to every output. Venue-specific adaptation is deferred to submission time (see [`venue-profiles.md`](../../shared-references/venue-profiles.md)), not drafting.
>
> **v2.1 — Mode selector on top of the single skeleton**: instead of the old binary `theory-only vs standard` branch, `/paper-writing` now selects one of **five section-layout modes** (`theory` / `experiment` / `computational` / `survey` / `hybrid`) at entry, driven by the `verification_type` + `evidence_type` signals already produced upstream. One skeleton, one document class, five section sets, zero discipline hardcode. See [`paper-modes.md`](../../shared-references/paper-modes.md).

## Use When

Use this skill when the AI scientist has completed the research process (problem understanding, literature survey, theory derivation, logic verification) and needs to write a structured academic paper or report.

Typical prompts:
- "写论文" / "write the paper"
- "generate the final report" / "compose the research output"
- "produce the academic manuscript"

## Job

Accept research artifacts (problem definition, literature survey, theory derivation, verification results, figures) and compose a complete academic paper with:
1. Title and abstract
2. Introduction (motivation, related work, gap, contribution)
3. Problem formalization
4. Theory / derivation / method
5. Results and analysis (theoretical results, verification)
6. Discussion
7. Conclusion
8. References (only from verified sources)

The non-negotiable goals:
1. **Every claim has support** — either a citation to verified literature OR a derivation/verification artifact
2. **Every citation is real** — only use papers from `literature/references.bib` verified list
3. **The paper is self-contained** — a reader with general scientific literacy should understand it
4. **No hallucinated content** — all equations, numbers, and claims trace to research artifacts
5. **The unified `elsarticle` template is loaded** — never hand-write the preamble; copy from `templates/default/main.tex`

## Required Workspace

The paper directory (default `paper/`):
- `paper/main.tex` — master LaTeX file (copied from `skills/support/paper-writing/templates/default/main.tex` on first run)
- `paper/references.bib` — bibliography (from `/universal-retrieval`, 3-layer-verified)
- `paper/sections/*.tex` — section sources
- `paper/figures/` — figure assets (from `/unified-plotting`)
- `paper/math_commands.tex` — shared notation (copied from the unified template)

**Inputs consumed** (read from upstream skills):
- `refine-logs/FINAL_PROPOSAL.md` — the frozen Q-id + selected idea (from `/idea-discovery`)
- `refine-logs/FRONTIER_GAP.md` — **v3.2** frontier baseline + delta claim + why-not-before (from `/novelty-check`) — feeds the Introduction's contribution-positioning paragraphs directly; if absent, Introduction must flag `[needs-frontier-positioning]` rather than fabricate one
- `refine-logs/FRONTIER_MAP.json` — **v3.2** frontier node graph (from `/novelty-check`) — lets the Introduction cite the specific SOTA nodes the idea advances beyond
- `literature/landscape_report.md` — literature survey (from `/universal-retrieval`)
- `literature/references.bib` — verified citations (from `/universal-retrieval`)
- `derivations/{problem_id}/derivation_output.md` — derivation results (from `/theory-derivation`)
- `audit_report/LOGIC_VERIFICATION.md` — verification results (from `/logic-verification`)
- `audit_report/LEAKAGE_AUDIT.md` — leakage audit (from `/leakage-audit`)
- `CLAIMS_FROM_RESULTS.md` — validated claims (from `/result-to-claim` or `/auto-review-loop`)
- `figures/FIGURE_INDEX.md` — generated figures (from `/unified-plotting`)

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | enum | `latex` | `latex` (unified elsarticle template) / `markdown` (plain markdown, if LaTeX unavailable) / `both` |
| `style` | enum | `academic` | `academic` (standard), `report` (technical report), `review` (survey) |
| `length` | enum | `standard` | `short` (4-6 pages main body), `standard` (8-12 pages), `long` (12-16 pages) — see [`venue-profiles.md`](../../shared-references/venue-profiles.md) |
| `language` | enum | `english` | `english` or `chinese` (equations + citations stay in standard LaTeX/math notation either way) |
| `include_abstract` | bool | `true` | Whether to include the abstract |
| `include_appendix` | bool | `false` | Whether to include a detailed appendix (long proofs, extended tables, code listings) |
| `citation_style` | enum | `numeric` | `numeric` (default — `\cite{}`, `elsarticle-num.bst`) / `author-year` (if user requests — `\citep{}`/`\citet{}`, `elsarticle-harv.bst`). Never mix in one paper. |
| `verification_type` | enum | `auto` | `auto` (auto-detect from idea-discovery) OR one of the **canonical tokens** from [paper-modes.md §2a](../../shared-references/paper-modes.md): `theory-only` / `computational` / `theory+experiment`. The mode selector reads this token verbatim — do NOT use legacy aliases (`theory_only`, `theory_experiment`). |

## Workflow

### Step 0: Load Domain Signature & Configure Style

Read `refine-logs/domain-signature.json` (from Phase 1b `/domain-learner` — the SOLE writer; Phase 1a `/domain-signature` only writes the optional `domain-signature-hint.json` prior, see [auto-pipeline §Domain Signature Propagation](../../orchestrator/auto-pipeline/SKILL.md)) to auto-configure writing style:

```json
{
  "signature_consumed": true,
  "writing_style": "empirical_economics",
  "citation_format": "author_year",
  "section_structure": "theory → empirical_strategy → results → robustness"
}
```

If the signature exists, the following parameters are auto-set (user can override):
- `style` ← from `writing_profile.style`
- `citation_style` ← from `writing_profile.citation_format`
- `section_structure` ← from `evidence_type` (see consumer protocol)

If no signature exists, use default behavior (no domain adaptation).

### Step 0b: Load the Unified Template

On first run, copy the unified template skeleton to the working directory:
```
paper/
├── main.tex                    ← copied from skills/support/paper-writing/templates/default/main.tex
├── math_commands.tex           ← copied from the unified template
├── references.bib              ← symlink or copy from literature/references.bib
├── sections/
│   ├── 01_introduction.tex
│   ├── 02_related_work.tex
│   ├── 03_problem_formalization.tex
│   ├── 04_theory.tex
│   ├── 05_results.tex
│   ├── 06_discussion.tex
│   └
│   └
└── figures/                    ← symlink or copy from figures/
```

The `main.tex` preamble is **frozen** — do NOT hand-edit it. The unified template provides:
- `\documentclass[preprint,12pt]{elsarticle}` — the unified document class
- Math + typography package loads (amsmath, amssymb, amsthm, mathtools, cleveref, booktabs)
- Theorem environments (theorem / proposition / lemma / corollary / definition / assumption / remark)
- `\input{math_commands}` for shared notation
- `\begin{frontmatter}` ... `\end{frontmatter}` block (title, authors, abstract, keywords)
- `\input{sections/...}` for each section
- `\bibliographystyle{elsarticle-num}` + `\bibliography{references}`
- `\appendix` block

### Step 1: Plan the Paper Structure

Read all research artifacts and design the paper structure. Write `paper/PAPER_PLAN.md`.

**v2.1 — Mode-selected section set.** Determine the mode first per [`paper-modes.md`](../../shared-references/paper-modes.md) §2 (read the canonical `verification_type` token + `evidence_type` from `domain-signature.json`). Then use the section set for that mode from `paper-modes.md` §3. Do NOT hand-pick sections here — the mode fully determines which `sections/*.tex` files to write.

**v3.1 — 全学科写作 Adapter 分发器（P5/Phase 6）**: mode 决定 section 骨架，**学科 Adapter 决定写作风格与强制槽位**。对 `domain-signature.json` + 问题文本做学科识别（关键词评分），取用对应 Adapter 契约：

| Adapter | 语气 | 强制槽位 |
|---------|------|----------|
| **STEM** | 被动语态、客观克制、定量精确（单位/误差棒） | derivation_log, verification_evidence |
| **Med/Bio** | 对照实验框架、显著性显式、临床转化相关 | statistical_significance, ethics_statement, data_compliance, limitations |
| **Humanities/SS** | 概念演变辨析、史料/文献推演、定性论证框架 | source_chain, concept_definition, interpretive_scope_boundary |

执行协议：写每个 section 前先取 Adapter 契约；`forced_slots` 缺失 → 该 section 回退重写；`forbidden` 表述出现 → 重写。Adapter 判定为规则化（关键词评分），不引入额外 LLM 调用。

**R6 收敛声明 (v2.3)**: 遗留的 `theory`/`standard` 完整版式已从本文件移除——`paper-modes.md` §3 是**唯一的** section-set 权威源（`theory`→§3.1，`experiment`/`computational`/`hybrid`→§3.2/§3.3/§3.5，`survey`→§3.4）。读取该契约文件即可获得完整 section 列表，本 skill 不再内嵌任何版式副本，避免双源漂移。

**Default** (`verification_type=auto`): run the mode selector — when ambiguous it returns `hybrid` (the most general shape), per `paper-modes.md` §2.

Reference the frozen Q-id in the plan header (INV-G1 problem anchor freeze).

### Step 2: Write Each Section

Follow [`discipline-writing.md`](../../shared-references/discipline-writing.md) for the universal section-by-section writing guide. Summary:

**Title:**
- Descriptive, not flashy
- Contains the key technical term
- ≤ 20 words

**Abstract:**
- Context → Problem → Approach → Result → Implication
- No citations (self-contained)
- No unnecessary equations

**Introduction:**
- Start with the broad scientific context
- Narrow to the specific problem
- State the gap clearly
- List contributions explicitly
- End with the paper structure roadmap

> **v3.2 — Introduction MUST consume `FRONTIER_GAP.md` (the gap is not improvised)**: the "State the gap clearly" + "List contributions" bullets are no longer agent-improvised. They are sourced verbatim from `refine-logs/FRONTIER_GAP.md` (Phase 3 `/novelty-check`): the frontier-baseline paragraph → Introduction §1 (context+problem); the falsifiable delta claim → Introduction contributions list; the 3 why-not-before reasons → Introduction "why this is timely" paragraph. If `FRONTIER_GAP.md` is absent, the Introduction MUST emit the marker `[needs-frontier-positioning]` at each of those 3 points and the paper verdict is downgraded to `WARN` (`frontier_positioning_missing: true` in `PAPER_PLAN.md`) — the agent NEVER fabricates a frontier baseline or delta from memory (that is the exact hallucination the 3-layer citation discipline forbids, and the exact "empty AI Intro" failure mode v3.2 exists to eliminate). The `FRONTIER_MAP.json` node graph lets the Introduction cite the specific SOTA nodes by key — `\cite{smith2024}` for the baseline, not "prior work".

**Related Work:**
- Group by theme, not by paper
- Only cite verified papers from `references.bib`
- Distinguish clearly from your approach
- No "prior work is limited" without evidence

**Problem Formalization:**
- Formal definition (variables, constraints, objective)
- Connect to the 125-problem context (Q-id)
- State assumptions clearly

**Theory / Derivation:**
- Present the derivation from `/theory-derivation` output
- Key equations with explanatory text
- Reference the derivation script for reproducibility
- Include only intermediate results that aid understanding

**Results:**
- Present the logic audit results from `/logic-verification`
- Show consistency checks, contradiction checks, fallacy scans
- Include numerical sanity checks if applicable
- Include figures from `/unified-plotting` if they aid understanding

**Discussion:**
- Interpret the results
- Honestly discuss limitations (especially any WARN verdicts from `/leakage-audit` or `/result-to-claim`)
- Compare with alternative approaches
- Suggest future work

**Conclusion:**
- Restate the contribution
- Summarize the key finding
- End with a forward-looking statement

**References:**
- Only papers from `literature/references.bib` (3-layer-verified)
- Use consistent citation format (`\cite{}` for numeric, `\citep{}`/`\citet{}` for author-year — never mix)
- Every reference must be cited in the body
- Auto-generated from `.bib` via `\bibliography{references}` — never hand-edit the references section

### Step 3: Cross-Reference Check

After writing, verify:
1. **Every citation in the body** has a corresponding entry in `references.bib`
2. **Every reference** is cited at least once in the body
3. **Every figure** is referenced in the body with `\cref{fig:label}` (never hardcoded "Figure 3")
4. **Every equation** with a `\label{eq:}` is referenced via `\cref{eq:label}`
5. **No citations outside the verified list** — no `\cite{TODO}`, no `\cite{forthcoming}`
6. **The Q-id** appears in the paper (usually Section 1 or the abstract context) — INV-G1 freeze

### Step 4: Generate Output

Write the complete paper:
- **LaTeX** (default): fill in `paper/sections/*.tex` from the unified template skeleton; the master `paper/main.tex` is already in place
- **Markdown** (if `format=markdown` or `format=both`): write `output/PAPER.md` with proper formatting (headings, math, figures, citations)
- **PDF**: defer to `/paper-compile` for the actual compile (this skill does NOT compile — it only produces the LaTeX source)

### Step 5: Self-Review

Before declaring the draft ready, perform a self-review:
1. **Structure** — does the paper follow the planned structure?
2. **Clarity** — is the writing clear and precise?
3. **Completeness** — are all sections present with substantive content?
4. **Integrity** — does every claim have a citation or artifact support?
5. **Citations** — are all citations real and correctly formatted?
6. **Template compliance** — is the unified `elsarticle` template used? No hand-written preamble? No `revtex`/`optica`/`IEEEtran`?
7. **Citation style consistency** — numeric OR author-year, not mixed?

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **Always load the unified `elsarticle` template.** Never hand-write the preamble. Never use `revtex`/`optica`/`IEEEtran`/`iclr`/`icml`/`neurips` document classes — OSS has one template only.
- **Never mix citation styles.** Pick numeric (`\cite{}`) OR author-year (`\citep{}`/`\citet{}`) at the start and keep it throughout.
- **Only verified citations.** Every `\cite{key}` must resolve to a `references.bib` entry that passed the 3-layer verification (see [`citation-discipline.md`](../../shared-references/citation-discipline.md)). No `\cite{TODO}`, no `\cite{forthcoming}`, no fabricated references.
- **Every claim has support.** Either a `\cite{}` to verified literature OR a `\cref{eq:}`/`\cref{fig:}` to a derivation/verification artifact. No unsupported assertions.
- **No venue-specific adaptation during drafting.** Venue adaptation (page limit trim, bibliography style switch, cover letter) is deferred to submission time per [`venue-profiles.md`](../../shared-references/venue-profiles.md). During drafting, use the unified template with the unified page target.
- **This skill does NOT compile.** Producing the PDF is `/paper-compile`'s job. This skill only produces the LaTeX source.
- **No discipline-specific writing guide.** Do not reintroduce physics SI-units / economics regression-table / cs-ml ablation-table specific guides. The universal guide in [`discipline-writing.md`](../../shared-references/discipline-writing.md) applies to every problem; the agent's runtime reasoning handles domain-specific conventions.

## Output Shape

The final output is:
1. `paper/PAPER_PLAN.md` — the paper structure plan (with frozen Q-id in header)
2. `paper/main.tex` — the master LaTeX file (unified template, frozen preamble)
3. `paper/math_commands.tex` — shared notation (from the unified template)
4. `paper/sections/*.tex` — the 7-9 section sources
5. `paper/references.bib` — the verified bibliography (from `/universal-retrieval`)
6. `paper/figures/` — the figure assets (from `/unified-plotting`)
7. `output/PAPER.md` (if `format=markdown` or `format=both`) — the markdown version

## Composing With Other Skills

```
/idea-discovery (produces FINAL_PROPOSAL.md with frozen Q-id)
    → /universal-retrieval (produces references.bib + landscape_report.md)
    → /theory-derivation (produces derivation_output.md)
    → /logic-verification (produces LOGIC_VERIFICATION.md)
    → /leakage-audit (produces LEAKAGE_AUDIT.md)
    → /result-to-claim (produces CLAIMS_FROM_RESULTS.md)
    → /unified-plotting (produces figures/)
    → /paper-writing                ← you are here
        → /paper-compile (compiles main.tex → main.pdf)
        → /auto-review-loop (cross-model review of the draft)
        → /citation-audit (final 3-layer citation verification)
```

## See Also

- [`../shared-references/venue-profiles.md`](../../shared-references/venue-profiles.md) — the single elsarticle template spec (no venue families)
- [`../shared-references/discipline-writing.md`](../../shared-references/discipline-writing.md) — universal section-by-section writing guide
- [`../shared-references/writing-principles.md`](../../shared-references/writing-principles.md) — academic writing style (universal)
- [`../shared-references/citation-discipline.md`](../../shared-references/citation-discipline.md) — 3-layer anti-hallucination citation verification
- [`../shared-references/color-themes.md`](../../shared-references/color-themes.md) — morandi palette (Layer 1) + viridis/magma data colormaps (Layer 2)
- [`../paper-compile/SKILL.md`](../paper-compile/SKILL.md) — compiles the LaTeX source this skill produces
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
