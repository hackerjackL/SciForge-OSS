# SciForge-OSS Agent Guide

> **Status**: The single entry orchestrator for OSS is `/auto-pipeline`. It executes a complete 21-phase DAG research loop on **one** problem supplied by the human user's prompt. **OSS does NOT auto-iterate over all problems** — each invocation = one Q-id = one complete pipeline run end-to-end.
>
> **All-domain support**: SciForge-OSS is not restricted to any discipline. Physics, mathematics, computer science, medicine, economics, education, materials science, earth science, atmospheric science, astronomy, chemistry, engineering, sensors, optoelectronics — any scientific domain can use it.

---

## Two consumption modes (v1.5.0)

This guide is the entry for **Mode A**. Since v1.5.0 the repo splits *knowledge* (Markdown, this guide) from *control* (code, `kernel/`):

| Mode | Who runs the loop | How you (the agent) participate | Guarantees |
|------|------------------|--------------------------------|------------|
| **A — skills-only (host agent)** | **You** read this guide + the phase `SKILL.md`s and execute `/auto-pipeline` turn by turn | Full autonomy; you are the orchestrator | gates are advisory (you self-run `scripts/*`) — the original behavior |
| **B — runtime kernel** | `kernel/` Python state machine (`sciforge run --host claude\|codex`) dispatches you **per phase** | You receive a pointer-load bundle (`.sciforge/refine-logs/phase_<id>.bundle.md`) and return a JSON verdict; the kernel enforces every gate and refuses to advance past a failure | mechanical gates, event-sourced resume, HITL as code, real token cost |

In Mode B you never have to remember the contracts — the kernel recites the hard constraints into your bundle at every boundary, runs the validators, and blocks bad transitions. Everything below still describes the DAG semantics you execute in either mode.

## Quick Start

### Solve one problem

```
"Help me fully research Q015: the origin and evolution of the universe"
"Solve Q042"
"run the full pipeline on Q001"
"Research an economics model: welfare maximization under perfect competition"
"Analyze this material science problem: high-temperature superconductor mechanism"
```

The human user supplies the specific problem. OSS does **not** auto-search any problem index. Each invocation processes exactly one problem.

### Available skills

| Type | Skill | Role |
|------|-------|------|
| **Orchestrator** | `/auto-pipeline` | Single entry — 21-phase DAG research loop on one problem (v2.9 + Phase 5b EG) |
| **Meta-skill** | `/idea-discovery` | Generate + pre-screen 8-12 idea candidates via MCTS (4 rounds) |
| **Meta-skill** | `/universal-retrieval` | Literature survey + 3-layer anti-hallucination citation verification |
| **Meta-skill** | `/unified-plotting` | Render publication-quality figures (dopamine palette + Layer 2 data colormaps) |
| **Meta-skill** | `/dynamic-sandbox` | Lightweight numerical sanity checks (Python/numpy, no GPU) |
| **Meta-skill** | `/dynamic-tooling` | On-the-fly tooling for the sandbox |
| **Meta-skill** | `/domain-learner` | Learns the domain signature from literature (sole writer, v2.8) |
| **Meta-skill** | `/domain-signature` | Rule-based signature hint (optional fast-path, v2.8) |
| **Meta-skill** | `/novelty-check` | 4-dim novelty evaluation + collision audit (v5.0) |
| **Support** | `/experiment-execution` | Toy experiment (foreground) + full experiment (background dispatch) [v2.0] |
| **Support** | `/method-registry` | Build + hash-lock the method registry (forced human approval) |
| **Support** | `/theory-derivation` | SymPy symbolic derivation + step-by-step machine verification |
| **Support** | `/leakage-audit` | Type I logic gap + Type IV empirical escape audit (universal) |
| **Support** | `/logic-verification` | 6-dim logical consistency audit (cross-model adversarial review) |
| **Support** | `/invariant-check` | INV-G1 PROBLEM_ANCHOR_FREEZE verification at phase boundaries |
| **Support** | `/result-to-claim` | 3-fidelity claim gate (symbolic / numerical / qualitative) |
| **Support** | `/quality-gate` | Hard gate at the final pre-writing boundary (universal QF-G* + SD-G*) |
| **Support** | `/paper-writing` | Compose the paper in the unified `elsarticle` template |
| **Support** | `/paper-compile` | Compile LaTeX → PDF (zero warnings zero errors, anti-deadloop) |
| **Support** | `/auto-review-loop` | Autonomous iterative improvement via cross-model reviewer |
| **Support** | `/citation-audit` | Final 3-layer citation verification on the paper draft |
| **Support** | `/kill-argument` | Anti-self-deception exercise (kill your own argument) |
| **Support** | `/adversarial-falsification` | Phase 2.5 falsification gate (hypothesis scoring + counterexamples) |
| **Support** | `/publishability-score` | 6-dim final publishability evaluation (v2.2) |
| **Support** | `/rebuttal` | Point-by-point rebuttal letter after rejection (v5.3) |

---

## The 21-Phase DAG Loop

```
Phase  0: load problem (freeze Q-id — INV-G1 anchor)
Phase  1: problem understanding & decomposition (built-in reasoning)
Phase  2: /idea-discovery [DAG branching] — 4-perspective ideas (theoretical/computational/qualitative/empirical) + MCTS iteration
Phase  2.5: /adversarial-falsification [falsification gate] — hypothesis scoring + counterexample construction + literature adversarial check
Phase  3: /novelty-check [DAG gate] — 4-dim evaluation + elimination
    ─── Forced human checkpoint: pick the final idea ───
Phase  4: /universal-retrieval — literature survey + 3-layer anti-hallucination
Phase  5: /method-registry — method binding + hash lock + forced human approval
    ─── Forced human checkpoint: approve the method registry ───
Phase  5b: engineering-grounding evaluation [v2.9] — 5-dim EG axis weighted by domain signature
Phase  6: /theory-derivation — SymPy symbolic derivation + step-by-step machine verification
Phase  6b: /experiment-execution (toy) [CONDITIONAL] — v2.0 toy experiment (theory-only → SKIP)
Phase  6c: /experiment-execution (full+bg) [CONDITIONAL] — v2.0 full-experiment background dispatch (theory-only → SKIP)
Phase  7: /leakage-audit — Type I logic leaks + Type IV escape audit
Phase  8: /logic-verification — 6-dim logical consistency audit
Phase  9: /invariant-check — INV-G1 problem-anchor freeze verification
Phase 10: /result-to-claim — 3-fidelity claim gate
Phase 11: /unified-plotting — academic figures (optional, dopamine palette + Layer 2)
Phase 12: /paper-writing — single elsarticle template writing
Phase 13: /paper-compile — LaTeX compile with zero warnings, zero errors
Phase 14: /auto-review-loop — cross-model review + kill-argument anti-self-deception
Phase 15: /citation-audit — final 3-layer citation verification
Phase 16: final assembly + artifact archival
```

### Fallback contract (bounded 3 rounds)

Each phase with a ↻ arrow falls back on failure to the relevant prior phase, bounded to 3 rounds per failure-type:

```
Round 1: apply the standard fix
Round 2: escalate the fix approach
Round 3 (BLOCKED): emit reason_code + surface to the human user
         ─ do NOT silently retry past round 3
```

Only the human user can waive a failure past round 3; the orchestrator never self-waives.

### Forced human checkpoints (2)

1. **Phase 3 → Phase 4**: the human picks the final idea from the MCTS-promoted survivors. The agent cannot self-select.
2. **Phase 5 → Phase 6**: the human approves the method registry (Section 3 hash lock). The agent cannot self-approve.

These checkpoints are non-negotiable. The pipeline halts until the human confirms.

Additionally (v5.3): the **KILL checkpoint** is ON by default — when a kill argument is produced before idea regeneration (loop-back rows L5/L7/L9/L11/L13), the orchestrator pauses for human confirmation. Delegate it with `human_skip=true` (all checkpoints) or `kill_checkpoint=false` (this one only); confirmations are recorded in `.sciforge/APPROVAL_LOG.txt`.

---

## Key Contracts (OSS — discipline-agnostic, single-row)

OSS is **discipline-agnostic by design**. There is no DISCIPLINE_CONTEXT block with 4-level fallback (economics / cs-ml / physics / general). Every invocation uses `discipline: general` unconditionally. See [`skills/shared-references/discipline-context.md`](skills/shared-references/discipline-context.md).

| Contract | Purpose | OSS status |
|----------|---------|------------|
| `idea-dag-schema.md` | DAG node schema (Phase 2) | Copied from main SciForge (discipline-agnostic) |
| `mcts-search-protocol.md` | MCTS iteration protocol (Phase 2) | Copied from main SciForge (UCB1 + bounded rounds) |
| `multi-fidelity-evaluation.md` | 3-fidelity filter (Phase 10) | Copied from main SciForge (OSS uses `general` row only) |
| `citation-discipline.md` | 3-layer anti-hallucination citation verification | Copied from main SciForge (universal) |
| `assurance-contract.md` | 6-state verdict schema (PASS/WARN/FAIL/NOT_APPLICABLE/BLOCKED/ERROR) | Copied from main SciForge (universal) |
| `output-manifest.md` + `output-versioning.md` | Product structure + versioning | Copied from main SciForge (universal) |
| `reviewer-independence.md` + `reviewer-routing.md` + `review-tracing.md` | Cross-model reviewer contracts | Copied from main SciForge (universal) |
| `effort-contract.md` | Effort level definitions (lite/balanced/max/beast) | Copied from main SciForge (universal) |
| `engineering-grounding-contract.md` | **NEW v2.9** — 5-dimension EG axis for real-world engineering feasibility | OSS new (discipline-agnostic) |
| `writing-principles.md` | Academic writing style | Copied from main SciForge (universal) |
| `skill-config.md` | Skill metadata schema | Copied from main SciForge (universal) |
| `venue-profiles.md` | **Single** unified `elsarticle` template spec (no venue families) | OSS rewritten (discipline-agnostic) |
| `venue-checklists.md` | **Single** universal pre-submission checklist (no per-venue lists) | OSS rewritten (discipline-agnostic) |
| `discipline-context.md` | OSS single-row (`general`) discipline contract | OSS rewritten (no 4-level fallback) |
| `discipline-writing.md` | Universal section-by-section writing guide (no per-discipline guides) | OSS rewritten (discipline-agnostic) |
| `color-themes.md` | Dopamine palette v3.0 (Layer 1, CVD-verified) + viridis/magma/cividis (Layer 2) | Carried from OSS (already discipline-agnostic) |
| `artifact-registry.md` + `output-protocol.md` | Artifact contracts + the single-authority workspace tree (.sciforge/verdicts/ unified) | OSS v5.2/v5.3 governance |
| `schemas/` + `scripts/validate_verdicts.py` | JSON Schemas + validator for every machine-readable verdict | OSS v5.3 (schema enforcement) |
| `verification-routing.md` | experiment-first / theory-only / hybrid routing contract | OSS v5.0 |

### Removed from OSS (discipline-specific, not applicable)

| Contract | Why removed |
|----------|-------------|
| `discipline-templates/` (cs-ml / economics / elsevier / physics / general) | Venue-specific templates — OSS uses single unified `elsarticle` template |
| `experiment-integrity.md` + `experiment-result-schema.md` | Superseded — OSS experiments (toy + full, v2.0) are governed by `experiment-execution/SKILL.md` (RESULT.json / DISPATCH.json contracts + v5.3 security gate) |
| `plugin-router.md` | Main SciForge's research-plugins routing — OSS doesn't use the plugins layer |
| `wiki-helper-resolution.md` | Main SciForge's wiki-enrich specific — OSS doesn't use it |

---

## Key Design Differences vs Main SciForge

| Aspect | Main SciForge | SciForge-OSS |
|--------|---------------|--------------|
| **Disciplines** | 4 parallel pipelines (economics / cs-ml / physics / general) | 1 universal pipeline (always `general`) — any domain |
| **Frameworks** | AIM (econ) / SOTA (cs-ml) / PNV (physics) / none (general) | None — agent's runtime reasoning handles domain-specific methodology |
| **Reviewer personas** | senior-econ-editor / senior-ml-reviewer / senior-physics-editor / senior-reviewer-agnostic | senior-reviewer-agnostic only |
| **Overlays** | 16 overlay files (4 skills × 4 disciplines) | None — no discipline dispatch |
| **Templates** | 10+ venue families (NeurIPS / ICLR / PRL / AER / etc.) | Single unified `elsarticle` template |
| **Experiments** | Full empirical pipeline (GPU training, benchmark binding, SOTA gate) | **Toy + Full experiments** — toy foreground gate, full background dispatch [v2.0] |
| **Verification paths** | Implicit — assumes code/experiment available | Explicit — four selectable paths: theory-only / computational / theory+experiment / qualitative |
| **Problem source** | N/A | No bundled problem index — the human user supplies the research question (Q-id) per run |
| **Figures** | Python pipeline mandatory (matplotlib/seaborn) | Python pipeline for data plots; AI-direct SVG allowed for simple diagrams (dopamine palette still enforced) |
| **Fidelity ladder** | 5-fidelity (text / symbolic / minimal / empirical / full) | 3-fidelity (symbolic / numerical / qualitative) — no empirical, no full |
| **Invariants** | INV-E1~E5 (econ) + INV-C1~C4 (cs-ml) + INV-P1~P5 (physics) + INV-G1 (general) | INV-G1 only (PROBLEM_ANCHOR_FREEZE) — universal |
| **Leakage audit** | Type I + II + III + IV (with 14-class econ / 14-class cs-ml / 10-class physics pitfall checklists) | Type I (universal) + Type IV (universalized beyond physics) — Type II/III NOT_APPLICABLE |
| **Quality floor** | QF-E* / QF-C* / QF-P* / QF-G* (per-discipline) | QF-G1~G9 only (universal) |
| **Self-deception guard** | SD-E* / SD-C* / SD-P* / SD-G* (per-discipline) | SD-G1~G5 only (universal) |

---

## Invocation Patterns

### Solve one problem (default)

```
"Help me fully research Q015: the origin and evolution of the universe"
"Solve a math problem: prove the Riemann Hypothesis implications"
"Analyze this economics model: general equilibrium under incomplete markets"
```

The orchestrator runs the full 21-phase loop. Forced human checkpoints at Phase 3→4 (pick final idea) and Phase 5→6 (approve method registry).

### Resume from checkpoint (v6.0 RUNSTATE contract)

Long runs survive interruptions structurally, not by memory: the orchestrator rewrites `{problem_id}/.sciforge/RUNSTATE.json` at every phase boundary and human checkpoint (current phase / last completed boundary / next action / status / pending approvals / budget snapshot — schema: `skills/shared-references/schemas/RUNSTATE.schema.json`). On startup the orchestrator runs the resume protocol (output-protocol.md §Long-Horizon Resume Contract): if a non-completed RUNSTATE exists it verifies the verdict trail (`scripts/validate_verdicts.py`), migrates any legacy-path artifacts into `.sciforge/`, and resumes from `next_action`. A human resuming explicitly can still say:

```
"continue the research on Q015 — I have already picked idea 2"
"resume Q042 — method registry approved, proceed to theory derivation"
```

### Partial run (debugging)

The user can invoke individual skills directly for debugging (bypassing the orchestrator):

```
"/theory-derivation on the Q015 derivation plan"
"/logic-verification on derivations/Q015/derivation_output.md"
"/paper-compile paper/main.tex"
```

But the **canonical** workflow is the full 21-phase orchestrator loop — partial runs are for debugging only and do not produce a complete artifact chain.

---

## Boundaries

- **Single-question execution only.** Each invocation = one problem. Do NOT auto-iterate over all problems.
- **No discipline branch.** One universal pipeline. The agent's runtime reasoning handles domain-specific methodology.
- **INV-G1 is non-negotiable.** The problem anchor is frozen at Phase 0 and referenced in every downstream phase.
- **Forced human checkpoints at Phase 3→4 and Phase 5→6.** The agent cannot self-select or self-approve.
- **3-round fallback limit is hard.** Do not exceed 3 rounds on the same failure type.
- **The orchestrator never executes research.** It delegates to the corresponding skill.
- **No bundled problem bank.** SciForge-OSS is a fully autonomous research skill: the human supplies one research question (any domain, any count) and the pipeline runs end-to-end on it.

---

## See Also

- [`README.md`](README.md) — project overview + skill catalog + comparison with main SciForge
- Problem input: the human user's prompt (Q-id + problem statement); no problem index file ships with the repo
- [`skills/orchestrator/auto-pipeline/SKILL.md`](skills/orchestrator/auto-pipeline/SKILL.md) — the 21-phase DAG loop orchestrator
- [`skills/shared-references/`](skills/shared-references/) — the shared contract layer (discipline-agnostic)