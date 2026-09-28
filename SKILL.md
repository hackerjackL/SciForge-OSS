---
name: sciforge-oss
type: skill-package
role: ai-scientist-framework
version: 1.7.1
description: "SciForge — Skill-driven universal research runtime (v1.7.1: ScientistTwo parity + AAR anti-Goodhart layer — subset→full-set experiment ladder with 3-state Critic as a 6c boundary gate, 5–6-plan ablation ledger + strict AblCritic at phase 10, score<8 rebuttal loop + Meta-Review {ACCEPT|REFINE}, anchor-calibrated review scores, reward-hacking + method↔code parity completeness audit at wrap-up, exploration-guaranteed idea evolution, CPU-only bench/s2demo in the ScientistTwo mold). Knowledge layer: pure-Markdown Skill Library (21-phase DAG, 27 sub-skills, 31+ contracts, any scientific idea → submission-ready SCI paper). v1.6.0 made evidence verifiable (kernel-enforced security scan, TDAL joint confidence, fantasy 5-gate, Arb certified intervals, sentence-level citation support, SMOKE gate, injection sanitizer, rate limiter, dual-timer). v1.5.0 added the split: *what to do* stays in Markdown; *how it is enforced* moves into the optional kernel/ (Python >= 3.10, stdlib-only): code state machine (phasegraph.json), event-sourced resume (kill -9 recoverable), mechanical gates in the control flow (validate_verdicts/security_scan/gap_gate/leakage_scan figure+compile gates — silent gate-skipping is structurally impossible), HITL checkpoints as data, role-tiered providers with real token accounting, sandbox experiment dispatch (Seatbelt/bwrap), worker pool, cross-model review panel with adjudication, headless serve daemon — and the RSI evolution layer (PUCT + MAP-Elites search over SKILL.md patches, three-shard held-out scoring, pre-flight probe, scorer freeze, human merge through full CI with auto-rollback). Two modes: A) skills-only — any Markdown agent runs /auto-pipeline as before; B) skills+kernel — sciforge run --host claude|codex. Absorbs openJiuwen/ScienceDiscovery + AI-Scientist v2 + EvoScientist + DeepScientist + STORM + ScientistTwo (arXiv:2609.19644) lessons. Headless-first: macOS/Linux, Docker included, no UI anywhere."
entry: skills/orchestrator/auto-pipeline/SKILL.md
license: PolyForm-Noncommercial-1.0.0
tags: [ai-scientist, research, latex, open-science, discipline-agnostic, runtime-kernel, rsi, auto-research]
---

# SciForge — AI for Scientist Anything

> **A Skill-driven universal research runtime**: Skill Library (pure Markdown) + Runtime Kernel (`kernel/`, code-enforced control) + RSI evolution layer.
> The skills keep the original spirit — no IDE-specific syntax, any Markdown-capable agent (Claude Code, Cursor, Trae, Codex…) consumes them directly via `/auto-pipeline`. The kernel is the optional control plane that makes gate-skipping impossible, crash-recovery automatic, cost real, and the skill library self-improving. See [README](README.md) "Runtime kernel" + "RSI" sections and `EVOLUTION_PLAN.md`.
>
> **Scope (v1.4.0, honest)**: the *method* is domain-agnostic; the *capability envelope* is **code-runnable science** — anything executable as code/data/literature on a machine or GPU cluster (numerical/symbolic sim, ML/stats, causal inference, web-search-augmented humanities). Domains whose core evidence needs proprietary/GUI-bound solvers (commercial CFD, COMSOL, optical bench software) or wet-lab hardware are out of scope **unless** reducible to a scriptable pipeline. See README "Scope & capability boundary".

## Package Structure

| Type | Count | Description |
|------|------|------|
| **Orchestrator** | 1 | `/auto-pipeline` — single entry point, 21-phase DAG research loop (v3.0 Phase 5b adds AI 8-dimension EG evaluation) |
| **Meta-Skills** | 8 | general meta-skills: idea-discovery, universal-retrieval, unified-plotting, dynamic-sandbox, dynamic-tooling, domain-learner, domain-signature, novelty-check |
| **Support Skills** | 18 | support skills: paper-writing, paper-compile, quality-gate, auto-review-loop, theory-derivation, **experiment-execution**, **experiment-ladder** (v1.7), **ablation-planner** (v1.7), logic-verification, result-to-claim, leakage-audit, citation-audit, invariant-check, kill-argument, method-registry, adversarial-falsification, publishability-score, **rebuttal** |
| **Shared References** | 31+ | shared config: skill-config, assurance-contract, effort-contract, color-themes, venue-profiles, **engineering-grounding-contract**, **s2-protocol** (v1.7 ScientistTwo parity), etc. |
| **Runtime Kernel (v1.7.0)** | 18 modules + s2 package | `kernel/sciforge/`: pipeline (state machine) · state (events+RUNSTATE) · gates · approvals · execution · providers · review · evolve (PUCT/MAP-Elites) · propose · skills_pack · litcache · proxy · memory · golden · daemon · bundle · cli · **s2/** (ladder · ideas · ablation · reviewloop · calibration · audit — ScientistTwo parity); configs in `kernel/config/` |

## Included Sub-Skills

### Orchestrator
- `/auto-pipeline` — single-question 21-phase DAG research loop (sole entry point; v3.0 Phase 5b AI 8-dimension EG evaluation + Extreme Protocol)

### Meta-Skills
- `/idea-discovery` — MCTS-enhanced research idea generation
- `/universal-retrieval` — literature retrieval + 3-layer anti-hallucination citation verification
- `/unified-plotting` — publication-grade figure rendering (dopamine palette, CVD-verified)
- `/dynamic-sandbox` — lightweight numerical verification sandbox (Python/NumPy)
- `/dynamic-tooling` — dynamic tool authoring and registration
- `/domain-learner` — auto-learn domain properties from the literature
- `/domain-signature` — domain signature tagging
- `/novelty-check` — novelty detection

### Support Skills
- `/paper-writing` — paper writing with the unified `elsarticle` template
- `/paper-compile` — LaTeX compile with zero warnings and zero errors
- `/quality-gate` — pre-writing hard gate
- `/auto-review-loop` — cross-model adversarial review iteration
- `/experiment-execution` — toy experiments (foreground gate) + full experiments (background dispatch) [v2.0]
- `/experiment-ladder` — subset→full-set ladder + 3-state Critic (writes S2_LADDER.json, gated at 6c) [v1.7.0]
- `/ablation-planner` — 5–6 component ablation plans + strict AblCritic (writes ABLATION_LEDGER.json, gated at phase 10) [v1.7.0]
- `/theory-derivation` — SymPy symbolic derivation and machine verification
- `/logic-verification` — 6-dimension logic-consistency audit
- `/result-to-claim` — 3-fidelity claim gate
- `/leakage-audit` — Type I/IV leakage audit
- `/citation-audit` — final 3-layer citation verification
- `/invariant-check` — INV-G1 invariant verification
- `/kill-argument` — anti-self-deception argument
- `/method-registry` — methodology registry (mandatory human approval)
- `/adversarial-falsification` — adversarial falsification
- `/publishability-score` — 6-dimension final publishability evaluation
- `/rebuttal` — point-by-point rebuttal letter after rejection (v5.3)

## Quick Start

```bash
# After importing this package into an AI agent that supports SKILL.md:
"Run the full research on Q015: the origin and evolution of the universe"
"Solve Q042: efficient energy storage"
"run the full pipeline on Q001"
```

## Design Principles

- **Domain-agnostic**: no discipline knowledge preset
- **Single-question execution**: one Q-id per invocation
- **3 fidelities**: symbolic / numerical / qualitative
- **Experiment-friendly**: toy gate on CPU; full experiments background-dispatched (GPU optional, auto-detected); agent-authored scripts pass the v5.3 security gate before dispatch
- **Unified template**: single `elsarticle` LaTeX template
