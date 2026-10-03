# SciForge-OSS — Claude Code Project Memory

## What this is
Skill-driven research runtime (v1.5.0): Skill Library (pure Markdown, `skills/`) + Runtime Kernel (`kernel/`, Python ≥3.10 stdlib-only) + RSI evolution. Two modes:
- **Skill mode**: `/auto-pipeline "Q: ..."` — read `skills/orchestrator/auto-pipeline/SKILL.md`, execute the 21-phase DAG in-conversation (pointer-load: load only declared references).
- **Kernel mode**: `node bin/sciforge.js run --workspace ./runs/Q001 --problem "..." --host claude` — the kernel dispatches phase bundles to you and expects a final JSON verdict `{"verdict": "PASS|WARN|FAIL|BLOCKED|NOT_APPLICABLE|ERROR", "artifacts": [...], "notes": "..."}`.

## Hard rules (non-negotiable, gate-checked)
1. INV-G1: the Q-id/problem anchor is frozen at Phase 0; every artifact references it.
2. Mechanical gates run as code (`validate_verdicts.py`, `security_scan.py`, `gap_gate.py`, `leakage_scan.py`, `fairness_gate.py`, `check_figure_embedding.py --require-renderer`, + v1.7.x: `s2_ladder`/`s2_ablation`/`s2_audit`/`integrity_monitor`/`workspace_hygiene`/`figure_style`/`doi_gate`/`completion_gate`/`claim_anchor_gate`/`submission_ready`/`rep_plan_present`) — never skip an audit; a run whose audits are missing is `BLOCKED verdicts_incomplete`.
3. Negative-result discipline: only `polarity: positive` claims enter contributions/abstract; failures go to Limitations or trigger KILL-or-PIVOT. Never package a failure as a contribution.
4. SCI body voice (writing-principles §0.6): zero apologies, zero defensive framing in body text; hedges only as bounded regime statements; Limitations = regime ledger, not confession. `leakage_scan.py` class K enforces this.
5. Every citation passes 3-layer verification (arXiv + CrossRef + Semantic Scholar) — zero fabricated references.
6. Figures only via `scripts/plotting/render_figure.py` (15 engines incl. declarative recipes, Nature A1–A10 audit).
7. 3-round fallback cap per failure type; then BLOCKED + surface to the human.

## Key paths
- Orchestrator: `skills/orchestrator/auto-pipeline/SKILL.md`
- Kernel: `kernel/sciforge/` (`pipeline.py` state machine, `evolve.py` PUCT+MAP-Elites, `review.py` cross-model panel)
- Registered verdicts: `skills/shared-references/schemas/*.schema.json` (22 artifacts incl. FAIRNESS.json)
- v1.7.2 protocol layer: `kernel/sciforge/{nodes,rep,sources,sota,memory}.py` + `skills/shared-references/s2-protocol.md` §10 (node fork / claim anchors / REP / semantic memory / batch sota / sources)
- Gates: `scripts/{validate_verdicts,security_scan,gap_gate,leakage_scan,fairness_gate,ci_check}.py`
- Reproduction: `REPRODUCE.md` · 30-item plan: `EVOLUTION_PLAN.md`

## Gotchas
- Workspace `.sciforge/` dirs are gitignored (exception: `fixtures/e2e_minimal/.sciforge/`).
- Version 1.7.2 is pinned across package.json + CITATION.cff + both READMEs (ci_check enforces).
- Kernel needs Python ≥3.10 (use `.venv/bin/python`); the system python3.9 cannot run it.
- When the kernel dispatches to you (`claude -p`), respond with ONLY the JSON verdict object as your final message.
