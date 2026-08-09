---
name: sciforge-oss
type: skill-package
role: ai-scientist-framework
version: 1.3.0
description: "SciForge-OSS — pure-Skill-driven domain-agnostic automated research framework: any scientific idea → one submission-ready SCI paper. 21-phase DAG single-question loop (idea-discovery → theory-derivation → experiments → logic/leakage audits → paper-writing → compile → cross-model review → citation-audit). v3.4 adds: human_skip=true production-grade checkpoint skipping, per-section figure budget + composite grouping (Composite/Group), LaTeX pipeline leakage scrub gate (8-class regex), Reproducibility + Data Availability statements, domain-expert blind-spot review (BLINDSPOT_CHECK.json), full-code smoke gate (.SMOKE.json), proxy auto-mount + async dataset download. v5.3 adds: verdict schema enforcement (verdicts/ + JSON Schemas + validator), global run-budget ledger (RUN_BUDGET.json), experiment security gate before dispatch, human checkpoint on KILL decisions, true-vector composite figures, /rebuttal skill. v6.0 (1.3.0) adds: literature-first gap chain (broad-wave GAP_REPORT.md + gap-anchored ideation + targeted retrieval waves), evidence_norm domain learning, .sciforge/ two-tier workspace (hidden state layer + delivery layer) with lazy materialization, RUNSTATE long-horizon resume contract, routing-aware N/A verdicts for theory-only/humanities runs, budget-underuse guard. 25 sub-skills; the orchestrator chains them via use_skill. Invoke /sciforge-oss or /auto-pipeline to run the full pipeline."
entry: skills/orchestrator/auto-pipeline/SKILL.md
license: MIT
tags: [ai-scientist, research, latex, open-science, discipline-agnostic]
---

# SciForge-OSS — AI for Scientist Anything

> **A pure-Skill-driven general scientific-intelligence framework**. No `.py` scripts, no bash code blocks, no IDE-specific syntax.
> Any AI agent that can read Markdown (Claude Code, Cursor, Trae, etc.) can consume these skills.

## Package Structure

| Type | Count | Description |
|------|------|------|
| **Orchestrator** | 1 | `/auto-pipeline` — single entry point, 21-phase DAG research loop (v3.0 Phase 5b adds AI 8-dimension EG evaluation) |
| **Meta-Skills** | 8 | general meta-skills: idea-discovery, universal-retrieval, unified-plotting, dynamic-sandbox, dynamic-tooling, domain-learner, domain-signature, novelty-check |
| **Support Skills** | 16 | support skills: paper-writing, paper-compile, quality-gate, auto-review-loop, theory-derivation, **experiment-execution**, logic-verification, result-to-claim, leakage-audit, citation-audit, invariant-check, kill-argument, method-registry, adversarial-falsification, publishability-score, **rebuttal** |
| **Shared References** | 31+ | shared config: skill-config, assurance-contract, effort-contract, color-themes, venue-profiles, **engineering-grounding-contract**, etc. |

## Included Sub-Skills

### Orchestrator
- `/auto-pipeline` — single-question 21-phase DAG research loop (sole entry point; v3.0 Phase 5b AI 8-dimension EG evaluation + Extreme Protocol)

### Meta-Skills
- `/idea-discovery` — MCTS-enhanced research idea generation
- `/universal-retrieval` — literature retrieval + 3-layer anti-hallucination citation verification
- `/unified-plotting` — publication-grade figure rendering (morandi palette)
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
