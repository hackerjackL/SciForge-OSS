---
name: theory-derivation
version: 1.1.1
description: "SymPy symbolic derivation with step-by-step machine verification; theory-only path uses engine=manual. Phase 6. Invoke after method-registry to derive and verify the theoretical result."
type: support-skill
role: theory-builder-and-symbolic-verifier
---

# Theory Derivation (SciForge-OSS — Merged formula-derivation + theory-derivation)

## Quick Reference

- **Purpose**: SymPy 符号推导 + 逐步机器验证；理论-only 模式用 engine=manual
- **Input**: refine-logs/FINAL_PROPOSAL.md (selected idea + assumptions)
- **Output**: code/derivations/{problem_id}/derivation.py + derivation_output.md + verification_report.md
- **Key**: 每步 SymPy 验证；3 种模式 (derive/verify/simplify)；理论-only 标记 [not machine-verified]

> **Status**: Bridges verbal reasoning and mathematical rigor. **OSS merges main SciForge's `formula-derivation`** (research theory-line construction — build the derivation package, freeze the invariant object, classify steps) **into this skill** (SymPy symbolic verification — derive / verify / simplify / solve with machine-checked steps). **OSS is discipline-agnostic** — no physics SI-units enforcement, no economics estimator-verification, no cs-ml convergence-rate framing. The universal derivation package schema + SymPy verification applies to every problem.

## Use When

Use this skill when the AI scientist needs to:
1. **Build a derivation package** — structure and derive research formulas, organize assumptions, turn scattered equations into a coherent derivation, rewrite theory notes into a paper-ready formula document
2. **Symbolically verify** — perform symbolic computation, check if a derivation is mathematically correct, solve equations / DEs symbolically

Typical prompts:
- "推导这个公式" / "verify this mathematical derivation"
- "perform symbolic integration" / "solve this differential equation symbolically"
- "build a theory line" / "organize assumptions"
- "把说明文档变成可写进论文的公式文档"
- "这几段公式之间逻辑不通"

**Use `/logic-verification` only after the exact claim is fixed, the assumptions are stable, and the notation is settled.** This skill is for the upstream construction + symbolic verification phase.

## Job

Build an **honest derivation package, not a fake polished theorem story.** Produce exactly one of:
1. A coherent derivation package for the original target, with every nontrivial step machine-verified by SymPy
2. A reframed derivation package with corrected object / assumptions / scope, with SymPy verification
3. A blocker report explaining why the current notes cannot yet support a coherent derivation

The non-negotiable goal: **coherence matters more than elegance. Never fabricate a coherent derivation if the object, assumptions, or scope do not support one. Every step is SymPy-verified.** Prefer reframing the derivation over overclaiming.

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | enum | `derive` | `derive` (new derivation) / `verify` (check existing) / `simplify` (transform) |
| `engine` | enum | `sympy` | `sympy` or `manual` (no symbolic engine, pure reasoning — use only when SymPy unavailable) |
| `output_format` | enum | `latex` | `latex` / `unicode` / `asciimath` |
| `max_steps` | int | `50` | Maximum derivation steps before halting |
| `show_intermediate` | bool | `true` | Show all intermediate steps in the report |
| `tolerance` | float | `1e-10` | Numerical tolerance for equality verification |
| `DEFAULT_DERIVATION_DOC` | path | `DERIVATION_PACKAGE.md` | Default target file when user does not specify one |
| `STATUS` | enum | — | `COHERENT AS STATED` / `COHERENT AFTER REFRAMING` / `NOT YET COHERENT` |

## Inputs

Extract and normalize:
- The target phenomenon, formula, relation, or theory line
- The intended role of the derivation: exact identity / algebra, proposition / local theorem, approximation, or mechanism interpretation
- Explicit assumptions
- Notation and definitions
- Any user-provided formula chain, sketch, messy notes, or current draft
- Nearby local theory files if the request points to them
- Desired output style if specified: internal alignment note, paper-style theory draft, or blocker report
- **The frozen Q-id** (from `refine-logs/FINAL_PROPOSAL.md`, verified by INV-G1) — every derivation must reference this Q-id

If the target, object, notation, or assumptions are ambiguous, state the exact interpretation being used before deriving anything.

## Workflow

### Step 1: Gather Derivation Context

Determine the target derivation file with this priority:
1. A file path explicitly specified by the user
2. A derivation draft already referenced in local notes
3. `DERIVATION_PACKAGE.md` in the project root as the default target

Read the relevant local context: the chosen target derivation file (if it already exists), and any local theory notes, formula drafts, appendix notes, or files explicitly mentioned by the user. Extract: target formula / theory goal, current formula chain, assumptions, notation, known blockers, desired output mode.

Also read `refine-logs/FINAL_PROPOSAL.md` to recover the frozen Q-id and the selected idea's framing + assumptions (from `/idea-discovery`). The derivation must be consistent with the selected idea.

### Step 2: Freeze the Target

State explicitly:
- What is being explained, derived, or supported
- Whether the immediate goal is identity / algebra, proposition, approximation, or interpretation
- What the derivation is expected to output in the end
- The Q-id this derivation serves (frozen — INV-G1 problem anchor)

Do not start symbolic manipulation before this is fixed.

### Step 3: Choose the Invariant Object

Identify the single quantity or conceptual object that should organize the derivation. Typical possibilities: objective / utility / loss; total cost / energy / welfare; conserved quantity / state variable; expected metric / effective rate / effective cost.

If the current notes start from a narrower quantity, decide explicitly whether it is the true top-level object, a proxy, a local slice, or an approximation. Do not let a convenient proxy silently replace the actual conceptual object.

### Step 4: Normalize Assumptions and Notation

Restate: all assumptions, all symbols, regime boundaries or special cases, and which quantities are fixed, adaptive, or state dependent.

Identify: hidden assumptions, undefined notation, scope ambiguities, and whether the current formula chain already mixes exact steps with approximations.

Preserve the user's original notation unless a cleanup is necessary for coherence. If a cleaner internal formulation is adopted, keep it as a derivation device rather than silently replacing the user's target.

### Step 5: Classify the Derivation Steps

For every nontrivial step, determine whether it is:
- **identity** — exact algebraic reformulation
- **proposition** — a claim requiring conditions
- **approximation** — model simplification or surrogate
- **interpretation** — prose-level meaning of a formula

Never merge these categories without signaling the transition. If one part is only interpretive, do not present it as if it were mathematically proved.

### Step 6: Build a Derivation Map

Choose a derivation strategy, for example:
- definition → substitution → simplification
- primitive law → intermediate variable → target expression
- global quantity → perturbation → decomposition
- exact model → approximation → interpretable closed form
- general dynamic object → simplified slice → local theorem → return to general case

Then write a derivation map:
- target formula or theory line
- required intermediate identities or lemmas
- which assumptions each nontrivial step uses
- where approximations enter
- where special-case and general-case regimes diverge or collapse

If the derivation needs a decomposition, derive it from the chosen global quantity. Do not make a split appear magically from one local variable itself.

### Step 7: Symbolic Verification (SymPy)

**Construct the SymPy representation:**
- Define symbols with appropriate assumptions (real, positive, complex, integer, nonnegative)
- Define known constants and functions
- Write premises as SymPy equations
- Write target expression as SymPy expression

**Execute derivation (mode-dependent):**

`mode: derive` — from premises apply symbolic transforms:
- Simplify expressions
- Expand, factor, collect
- Solve equations and systems
- Perform symbolic integration / differentiation
- Apply series expansions
- Generate step-by-step derivation with intermediate results

`mode: verify` — accept the stated derivation and:
- Independently re-derive each step in SymPy
- Check intermediate expression equality (with `tolerance`)
- Verify the final result satisfies the premises
- Report any divergence with exact symbolic diff

`mode: simplify` — transform expressions:
- Apply trig identities
- Rationalize denominators
- Factor polynomials
- Convert to canonical form

**Every nontrivial step is SymPy-verified.** The SymPy script is preserved alongside the derivation document (see Output Shape) for reproducibility.

### Step 8: Final Verification

Before finishing the target derivation file, verify:
- The target is explicit
- The invariant object is stable across the derivation
- Every assumption used is stated
- Each formula step is correctly labeled as identity / proposition / approximation / interpretation
- The derivation does not silently switch objects
- Special cases and general cases still belong to one theory line
- Boundaries and non-claims are stated
- **SymPy verification PASSED for every step** (the SymPy script ran without `TODO` / `gap` / hand-waved markers)
- The Q-id from Step 2 is referenced in the derivation document header (INV-G1 freeze)

If the derivation still lacks a coherent object, stable assumptions, or an honest path from premises to result, downgrade the status and write a blocker report instead of forcing a clean story.

### Step 9: Generate the Derivation Report

Write the structured derivation document (see Required File Structure below) AND the SymPy script:

```python
# code/derivations/{problem_id}/derivation.py
# SymPy script for Q-id {Q-id}
# Every step in DERIVATION_PACKAGE.md is verified by this script.
import sympy as sp
# [the full derivation script]
```

### Step 10: Notify Downstream

- `/dynamic-sandbox` → if numerical verification of the symbolic result is needed, pass the SymPy script + parameters
- `/logic-verification` → after derivation completes, verify its 6-dim logical consistency
- `/leakage-audit` → audit the derivation chain for Type I logic gaps + Type IV empirical escape
- `/result-to-claim` → gate what claims the derivation supports (3-fidelity ladder)

## Required File Structure

Write the target derivation file using this structure:

```md
# Derivation Package

**Q-id**: [frozen — from refine-logs/FINAL_PROPOSAL.md]
**Generated**: [date]
**Status**: COHERENT AS STATED / COHERENT AFTER REFRAMING / NOT YET COHERENT

## Target
[what is being derived or explained]

## Invariant Object
[top-level quantity organizing the derivation]

## Assumptions
- ...

## Notation
- ...

## Derivation Strategy
[chosen route and why]

## Derivation Map
1. Target depends on ...
2. Intermediate step A uses ...
3. Approximation enters at ...

## Main Derivation (SymPy-verified)
Step 1. ... [identity / proposition / approximation / interpretation]
  - SymPy check: `sp.simplify(...)` → PASS
Step 2. ...
  - SymPy check: `sp.Eq(...).subs(...)` → PASS
...

## Remarks and Interpretation
- ...

## Boundaries and Non-Claims
- ...

## Open Risks
- ...

## SymPy Script
[reference to code/derivations/{problem_id}/derivation.py]
```

## Output Modes

### If the derivation is coherent as stated
Write the full structure above with a clean derivation package + SymPy verification log.

### If the notes are close but not coherent yet
Write: the exact mismatch; the corrected invariant object, assumption, or scope; and the reframed derivation package.

### If the derivation cannot be made coherent honestly
Write:
- `Status: NOT YET COHERENT`
- The exact blocker: missing object, unstable assumptions, notation conflict, unsupported approximation, or theorem-level claim without enough conditions
- What extra assumption, reframe, or intermediate derivation would be needed

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **Never fabricate a coherent derivation** if the object, assumptions, or scope do not support one. Prefer reframing over overclaiming.
- **Every nontrivial step is SymPy-verified.** Do not hand-wave a step that SymPy could check. If SymPy is unavailable (`engine: manual`), flag every step as `[not machine-verified]` in the report.
- **Separate assumptions, identities, propositions, approximations, and interpretations.** Never merge these categories without signaling the transition.
- **Keep one invariant object** across special and general cases whenever possible.
- **Treat simplified constant-parameter cases as analysis slices**, not as the conceptual main object.
- **If uncertainty remains, mark it explicitly in `Open Risks**; do not hide it in polished prose.
- **Coherence matters more than elegance.**
- **Do not write directly into paper sections or appendix `.tex` files** unless the user explicitly asks for that target.
- **Reference the frozen Q-id** in the derivation document header (INV-G1 problem anchor freeze).
- **No discipline-specific enforcement.** Do not reintroduce physics SI-units enforcement, economics estimator-verification, or cs-ml convergence-rate framing. The universal derivation package schema + SymPy verification applies to every problem.

## Output Shape

The final output is:
1. `derivations/{problem_id}/premises.md` — starting assumptions (frozen Q-id referenced)
2. `code/derivations/{problem_id}/derivation.py` — executable SymPy script (every step machine-verified)
3. `derivations/{problem_id}/derivation_output.md` — rendered derivation report (the structure above)
4. `derivations/{problem_id}/verification_report.md` — verification results (boundary / dimensional / limiting cases / numerical sanity)
5. `DERIVATION_PACKAGE.md` (or user-specified target) — the paper-ready formula document

The chat response after writing is brief: status, whether the target survived unchanged or had to be reframed, and what file was updated.

## See Also

- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../shared-references/output-manifest.md`](../../shared-references/output-manifest.md) — product structure contract
- [`../logic-verification/SKILL.md`](../logic-verification/SKILL.md) — 6-dim logical consistency audit (downstream)
- [`../leakage-audit/SKILL.md`](../leakage-audit/SKILL.md) — Type I + Type IV audit (downstream)
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — 3-fidelity claim gate (downstream)
