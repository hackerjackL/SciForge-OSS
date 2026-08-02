---
name: paper-compile
version: 0.1.0
description: "Compile LaTeX (elsarticle) to submission-ready PDF with zero-warnings policy + anti-deadloop escalation + table/figure overflow checks. v3.4 Step 1.5 pipeline-leakage scrub gate consumer (refuses to compile if LEAKAGE_SCRUB.json missing/FAIL, defense-in-depth re-scan). Phase 13. Invoke after paper-writing to produce main.pdf."
type: reference-skill
role: latex-compiler
---

# Paper Compile: LaTeX to Submission-Ready PDF (SciForge-OSS)

## Quick Reference

- **Purpose**: LaTeX 编译 paper/main.tex → main.pdf，零警告零报错
- **Input**: paper/main.tex + paper/sections/*.tex + literature/references.bib
- **Output**: main.pdf + compile.log + COMPILE_REPORT.json
- **Key**: 反死循环阶梯 (3 attempt per-warning → BLOCKED)；submission 级编译

> **Status**: LaTeX compiler for the unified `elsarticle` template. Enforces zero-warnings zero-errors at submission level. Copied from main SciForge and trimmed to OSS's single-template, discipline-agnostic design.
>
> **Key OSS difference**: No per-venue page limit table. OSS uses a single unified page target (8-15 pages main body, flexible). No `TARGET_VENUE` switching — every output drafts in `elsarticle [preprint,12pt]` with `elsarticle-num.bst` (numeric default).

## Use When

Use this skill when the user wants to compile a LaTeX paper into a PDF, diagnose build errors, or verify submission readiness.

Typical prompts:
- "编译论文"
- "compile paper"
- "build PDF"
- "生成PDF"
- "fix compile errors"

## Job

Compile the LaTeX paper in `paper/` into a submission-ready PDF, auto-fix any compilation errors, enforce a zero-warnings policy, verify page count against the OSS unified target, and confirm submission readiness. The output is a clean `main.pdf` plus a compilation report.

## Required Workspace

- `paper/main.tex` — master LaTeX file (must exist, copied from `skills/support/paper-writing/templates/default/main.tex`)
- `paper/references.bib` — bibliography (should exist, 3-layer-verified per `citation-discipline.md`)
- `paper/sections/*.tex` — section sources (should exist)
- `paper/figures/` — figure assets (PDF preferred; SVG acceptable when AI-direct-generated)

## Configuration

- **Compiler** (default: `latexmk`) — LaTeX build tool. Handles multi-pass compilation (pdflatex + bibtex + pdflatex × 2) automatically.
- **Engine** (default: `pdflatex`) — LaTeX engine. Options: `pdflatex` (default), `xelatex` (for CJK / custom fonts), `lualatex`.
- **Max compile attempts** (default: `3`) — Maximum attempts to fix errors and recompile.
- **Zero warnings policy** (default: `true`) — ALL LaTeX output must be warning-free. Overfull/underfull hbox, undefined references, citation warnings, and font embedding warnings must ALL be resolved before declaring success.
- **Paper dir** (default: `paper/`) — Directory containing LaTeX source files.
- **Max pages** (default: `15`) — OSS unified page limit. Main body = first page through end of Conclusion section. References and appendix are NOT counted. The `length` parameter on `/paper-writing` (`short`/`standard`/`long`) maps to 4-6 / 8-12 / 12-16 pages; this skill verifies the actual compile against the chosen target.

## Workflow

### Step 1: Verify Prerequisites

Check that the compilation environment is ready. Verify the LaTeX toolchain (`pdflatex`, `latexmk`, `bibtex`) is installed; if not, provide installation guidance appropriate to the platform (macOS: MacTeX/BasicTeX; Ubuntu: `texlive-full`; conda: `texlive-core`; Windows: MiKTeX/TeX Live).

Verify all required files exist:
- `paper/main.tex` (must exist)
- `paper/references.bib` (should exist)
- `paper/sections/*.tex` (should exist)
- `paper/figures/*.pdf` or `paper/figures/*.svg` (should exist)

### Step 1.5: Pipeline-Leakage Scrub Gate Check (v3.3 — MANDATORY hard wall)

> **Why this exists**: `/paper-writing` Step 3.5 writes `paper/LEAKAGE_SCRUB.json` after scrubbing all internal pipeline paths/jargon/identifiers from the LaTeX. This step is the **consumer** of that gate — compile REFUSES to run if the scrub didn't pass. Without this check, a paper with `\path{derivations/Q-HARM-001/derivation.py}` or "INV-G1 freeze verified" or "Morandi palette" in the body would compile into a PDF that a reviewer desk-rejects on sight as an AI pipeline dump. Two real test runs (Q-HARM-001, Q-SGD-BS-GAP) shipped exactly this leakage and compiled clean PDFs — the compile had no defense.

**Procedure**:
1. Read `paper/LEAKAGE_SCRUB.json`. If it does NOT exist → the paper-writing skill never ran its Step 3.5 scrub gate. This is a contract violation: **BLOCKED**, `reason_code: leakage_scrub_gate_not_run`. Do NOT compile. Surface to the human: "paper-writing did not run the pipeline-leakage scrub gate (Step 3.5); the manuscript may contain internal paths/jargon/identifiers. Re-run /paper-writing before compiling."
2. If `LEAKAGE_SCRUB.json` exists but `status != "PASS"` (e.g., `FAIL` with `hits_remaining > 0`) → **BLOCKED**, `reason_code: pipeline_leakage_not_scrubbed`, listing the `classes_seen` and `hits_remaining`. Do NOT compile. The manuscript still contains leakage that a reviewer would catch.
3. If `status == "PASS"` (zero hits remaining) → proceed to Step 2 (compile).
4. **Defense-in-depth re-scan** (even when PASS): before compiling, re-grep `paper/main.tex` + `paper/sections/*.tex` + `paper/math_commands.tex` for the 8 leakage classes defined in `/paper-writing` Step 3.5 (internal paths, phase jargon, audit verdicts, pipeline identifiers, rendering-pipeline captions, internal config, draft comments, frontmatter leak). If the re-scan finds hits the scrub missed (e.g., the scrub gate ran before a later edit re-introduced leakage), **BLOCKED** with the specific hits — do not trust the PASS stamp alone, re-verify against the actual file contents. Write any newly-found hits to `paper/LEAKAGE_SCRUB.json` as `defense_in_depth_hits` and refuse compile.
5. On PASS + clean re-scan → write `paper/LEAKAGE_SCRUB_VERIFIED.json` (`{"verified_at":"<ISO>","re_scan_hits":0,"compile_allowed":true}`) and proceed to Step 2.

**Boundaries**:
- This check is a **hard wall** — there is no `WARN` downgrade, no "compile anyway and flag it". A paper that has not passed the scrub gate does not compile, full stop. The zero-warnings compile policy is downstream of this gate: a clean compile of a leaky manuscript is a failure, not a success.
- The re-scan is **defense-in-depth**, not redundant: it catches leakage re-introduced by a human or agent edit *after* the scrub gate ran (e.g., a late edit added `\path{experiments/...}` to the appendix). Trust the file contents, not the stamp.

### Step 2: First Compilation Attempt

Clean previous build artifacts (`latexmk -C`), then run a full compilation with `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`, capturing the output to `compile.log`.

### Step 3: Error Diagnosis and Auto-Fix

If compilation fails, read `compile.log` and fix common errors:

**Missing packages** (`! LaTeX Error: File 'somepackage.sty' not found.`)
- Install via `tlmgr install somepackage` or remove the `\usepackage` if unused.

**Undefined references** (`LaTeX Warning: Reference 'fig:xyz' on page 3 undefined`)
- Check `\label{fig:xyz}` exists in the correct figure environment.

**Missing figures** (`! LaTeX Error: File 'figures/fig1.pdf' not found.`)
- Check if the file exists with a different extension (.svg vs .pdf). Update the `\includegraphics` path.

**Citation undefined** (`LaTeX Warning: Citation 'smith2024' undefined`)
- Add the missing entry to `references.bib` (must be 3-layer-verified first) or fix the citation key.

**`[VERIFY]` markers in text**
- Search for `[VERIFY]` markers left by `/paper-writing`. These indicate unverified citations or facts. Resolve the correct information or flag to the user.

**Overfull hbox** (`Overfull \hbox (12.5pt too wide) in paragraph at lines 42--45`)
- **MUST FIX (zero warnings policy)**. If severe (>20pt), rephrase the text or adjust figure width. If minor (5-20pt), use `\sloppy`, adjust `\tolerance`, break the line manually, or reduce figure width to `\dimexpr\linewidth-5pt`. Never leave overfull hbox warnings.

**Underfull hbox** (`Underfull \hbox (badness 3012) in paragraph at lines 50--52`)
- **MUST FIX (zero warnings policy)**. Rephrase the text to fill the line better, or add `\raggedright` for specific paragraphs.

**Duplicate label** (`LaTeX Warning: There were multiply-defined labels.`)
- Find and rename duplicate `\label{}` entries. Each label must be unique.

**BibTeX errors** (`I was expecting a ',' or a '}'---line 15 of references.bib`)
- Fix BibTeX syntax (missing comma, unmatched braces, special characters in title).

**`\crefname` undefined for custom theorem types**
- Ensure `\crefname{assumption}{Assumption}{Assumptions}` and similar are in the preamble after `\newtheorem{assumption}`.

### Step 4: Iterative Fix Loop

For each attempt (up to `Max compile attempts`):
1. Compile the paper.
2. If success, break.
3. Parse errors from `compile.log`.
4. Apply the auto-fix from Step 3.
5. Recompile.

For each error: read the message from `compile.log`, locate the source file and line number, apply the fix, recompile.

**Stuck after 2 attempts?** A cross-model reviewer can independently read the LaTeX source and `compile.log` to spot issues the host agent missed (conflicting packages, encoding problems, subtle macro errors).

### Step 5: Post-Compilation Checks

After successful compilation, verify the output:
- `main.pdf` exists and is > 100KB (not empty/corrupt).
- Total page count is reasonable (`pdfinfo main.pdf | grep Pages`).
- **Zero warnings** — no LaTeX warnings remain in `compile.log` (overfull hbox, underfull hbox, undefined refs, etc.).
- No "??" in the PDF (undefined references — grep the log).
- No "[?]" in the PDF (undefined citations — grep the log).
- Figures are rendered (not missing image placeholders).
- All figures from `figures/` are referenced in the paper text.

**Visual review (automated):** If the compiled PDF exists, read it directly to check visual presentation:
- Figure quality: readable labels, legible text, distinguishable colors (morandi palette — see `color-themes.md`).
- Layout: no orphaned section headers, no awkward page breaks.
- Figures appear near their first text reference (not pages away).
- Tables: aligned columns, consistent decimal precision.
- No overfull content visibly extending past margins.

### Step 5.5: Table and Figure Overflow Check

After visual review, explicitly verify table and figure boundaries:

**Table overflow check**:
- Parse `paper/main.tex` and `paper/sections/*.tex` for all `tabular`/`tabularx`/`longtable` environments
- Verify each table's declared width (e.g., `\textwidth`, `\columnwidth`) does not exceed the physical page width
- Check for tables using absolute widths (e.g., `p{15cm}`) that may exceed page limits
- **Verdict**: `FAIL` if any table column specification exceeds `\textwidth` without explicit `\resizebox` wrapper

**Figure overflow check**:
- Parse `paper/main.tex` and `paper/sections/*.tex` for all `\includegraphics` commands
- Verify each `\includegraphics` width parameter does not exceed `\textwidth` (single column) or `\textwidth` (spanning)
- Check for figures with no width parameter (may overflow at native resolution)
- **Verdict**: `WARN` if any `\includegraphics` has no width parameter; `FAIL` if declared width exceeds `\textwidth`

**Cross-reference integrity check**:
- Verify every `\label{fig:*}` has at least one `\ref{fig:*}` or `\cref{fig:*}` in the text
- Verify every `\label{tab:*}` has at least one `\ref{tab:*}` or `\cref{tab:*}` in the text
- Verify no `\ref{}` points to a non-existent label
- **Verdict**: `FAIL` if any figure/table has no text reference; `WARN` if any `\ref{}` target is undefined

### Step 6: Page Count Verification

**CRITICAL**: Verify paper fits within Max pages (OSS unified default: 15).

**OSS page count rule**: Main body = first page through end of Conclusion section. References and appendix are NOT counted.

**Precise check**: Extract text from the PDF and locate where Conclusion ends vs References begin. If Conclusion ends mid-page and References start on the same page, the main body is that page number (e.g., if both are on page 9, main body = ~8.5 pages).

If over limit:
- Identify which sections are longest.
- Suggest specific cuts (move proofs to appendix, compress tables, tighten writing).
- Report: "Main body is X pages (limit: Max pages). Suggestion: move [specific content] to appendix."

### Step 6.5: Stale File Detection

Check for orphaned section files not referenced by `main.tex`. Find all `.tex` files in `sections/` and check which are `\input`'ed by `main.tex`. Warn about any unreferenced files.

This prevents confusion from leftover files when section structure changes (e.g., old `5_conclusion.tex` left behind after restructuring to 7 sections).

### Step 7: Submission Readiness

- **Anonymous**: no author names, affiliations, or self-citations that reveal identity (unless the human user explicitly requested attribution).
- **Page limit**: main body within Max pages (to end of Conclusion).
- **Font embedding**: all fonts embedded in PDF (`pdffonts main.pdf` — all should show "yes").
- **No supplementary mixed in**: appendix clearly after `\newpage\appendix`.
- **File size**: reasonable (< 50MB, < 10MB preferred).
- **No `[VERIFY]` markers**: search the PDF text for leftover markers.

### Step 8: Output Summary

Produce a compilation report:

- **Status**: SUCCESS / FAILED
- **PDF**: `paper/main.pdf`
- **Pages**: X (main body to Conclusion) + Y (references) + Z (appendix)
- **Within page limit**: YES/NO (Max pages = N)
- **Errors fixed**: list of auto-fixed issues
- **Warnings remaining**: list of non-critical warnings (should be empty under zero warnings policy)
- **Undefined references**: 0
- **Undefined citations**: 0
- **Next steps**: visual inspection of PDF, run `/paper-writing` to fix content issues, submit to venue (if human requests submission-time adaptation per `venue-profiles.md`).

## Common OSS Template Requirements

All OSS outputs use the unified `elsarticle` template:

| Property | Value |
|----------|-------|
| Document class | `\documentclass[preprint,12pt]{elsarticle}` |
| Bibliography style | `\bibliographystyle{elsarticle-num}` (numeric, default) |
| Citation command | `\cite{key}` (elsarticle native numeric) |
| Alt (if user requests) | `\bibliographystyle{elsarticle-harv}` + `\citep{}`/`\citet{}` (author-year) — never mix |
| Page target | 8-15 pages main body, flexible (short=4-6, standard=8-12, long=12-16) |

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **Never delete the user's source files** — only modify to fix errors.
- **Keep `compile.log`** — useful for debugging.
- **Don't suppress warnings** — FIX all warnings, do not just report them. The zero warnings policy requires active resolution.
- **Zero warnings is the goal** — if warnings remain after Max compile attempts, continue fixing until zero. Never declare success with remaining warnings.
- **Escalation path (anti-deadloop)** — "continue fixing until zero" is bounded by a hard escalation ladder. Do NOT loop on the same warning for more than 2 attempts:
  1. **Attempt 1**: apply the standard fix for the warning type (overfull → split equation / rephrase; undefined ref → check `\label`; duplicate label → rename; etc.).
  2. **Attempt 2**: if the same warning persists, escalate the fix — e.g. for overfull, switch to `\sloppy` locally or reduce font; for undefined ref, search the entire `paper/` tree for the missing label; for citation warnings, re-run DBLP/CrossRef fetch.
  3. **Attempt 3 (BLOCKED)**: if the same warning STILL persists after a different fix attempt, emit `COMPILE_REPORT.json` with `verdict: BLOCKED, reason_code: unresolved_warning_<type>, attempts: 3` and surface to the user with the exact warning text, the attempted fixes, and a recommendation (manual fix needed / venue style limitation / waive with explicit approval). **Do NOT silently retry past attempt 3** — that is the deadloop trap.
  - The 3-attempt cap applies per-warning, not per-compile. A compile with 5 distinct warnings gets up to 15 fix attempts total before BLOCKED, not 3.
  - Only the user can waive a warning past attempt 3; the skill never self-waives.
- **If LaTeX is not installed**, provide clear installation instructions rather than failing silently.
- **Font embedding is critical** — submission venues reject PDFs with non-embedded fonts.
- **Figure verification** — ALL figures in `figures/` must be referenced in the paper text. Unreferenced figures are a structural issue.
- **Figure format** — vector PDF preferred; SVG acceptable when AI-direct-generated (see `color-themes.md` for morandi palette contract).

## Output Shape

The compilation produces:

1. **Compiled PDF** — `paper/main.pdf` (submission-ready, zero warnings)
2. **Compilation log** — `paper/compile.log` (retained for debugging)
3. **Compilation report** — status, page count, errors fixed, warnings remaining, submission readiness checklist
