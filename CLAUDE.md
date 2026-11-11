# SciForge-OSS — Claude Code Project Memory

## What this is
Skill-driven research runtime (v1.7.4): Skill Library (pure Markdown, `skills/`) + Runtime Kernel (`kernel/`, Python ≥3.10 stdlib-only) + RSI evolution. Two modes:
- **Skill mode**: `/auto-pipeline "Q: ..."` — read `skills/orchestrator/auto-pipeline/SKILL.md`, execute the 26-node DAG in-conversation (pointer-load: load only declared references).
- **Kernel mode**: `node bin/sciforge.js run --workspace ./runs/Q001 --problem "..." --host claude` — the kernel dispatches phase bundles to you and expects a final JSON verdict `{"verdict": "PASS|WARN|FAIL|BLOCKED|NOT_APPLICABLE|ERROR", "artifacts": [...], "notes": "..."}`.

## Hard rules (non-negotiable, gate-checked)
1. INV-G1: the Q-id/problem anchor is frozen at Phase 0; every artifact references it.
2. Mechanical gates run as code (`validate_verdicts.py`, `security_scan.py`, `gap_gate.py`, `leakage_scan.py`, `fairness_gate.py`, `check_figure_embedding.py --require-renderer`, + v1.7.x: `s2_ladder`/`s2_ablation`/`s2_audit`/`integrity_monitor`/`workspace_hygiene`/`figure_style`/`doi_gate`/`completion_gate`/`claim_anchor_gate`/`submission_ready`/`rep_plan_present`) — never skip an audit; a run whose audits are missing is `BLOCKED verdicts_incomplete`.
   - **Mode B (kernel) gate-checks every item above**: `Kernel.commit_boundary()` (`kernel/sciforge/gates.py`) rejects the boundary on any FAIL/BLOCKED/PENDING.
   - **Mode A (skills-only) gate-checks none of them mechanically** — the agent must invoke the scripts. `rep_plan_present` and `claim_anchor_gate` are structurally unavailable in Mode A (`REP.json` / `NODES.json` are kernel-produced; the gates SKIP), and `inv_g1` has no frozen reference to compare against. `fairness_gate`'s cross-validation layer likewise cannot run without kernel-produced evidence (a ledger with no co-located raw evidence is `scope=ledger_only`). The other Mode B boundary gates (security_scan at 6b/6c, dep_gate, integrity_monitor, smoke_gate, s2_ladder, s2_ablation, arb_verify, figure embedding/style, fantasy_gate, leakage_scan, citation_support, doi_gate, fairness_gate, submission_ready, wrap_up_gates) exist as scripts but run only if the agent calls them.
   - Run `python3 scripts/gate_all.py <workspace>` at every Mode A boundary for one aggregated report with an explicit `UNPROTECTED` list; full matrix: `skills/orchestrator/auto-pipeline/SKILL.md` §"Mode A vs Mode B: Guarantee Matrix".
3. Negative-result discipline: only `polarity: positive` claims enter contributions/abstract; failures go to Limitations or trigger KILL-or-PIVOT. Never package a failure as a contribution.
4. SCI body voice (writing-principles §0.6): zero apologies, zero defensive framing in body text; hedges only as bounded regime statements; Limitations = regime ledger, not confession. `leakage_scan.py` class K enforces this.
5. Every citation passes multi-layer verification: arXiv existence + CrossRef DOI/metadata are mandatory; Semantic Scholar fuzzy match is Layer 3 and runs whenever reachable (send `SEMANTIC_SCHOLAR_API_KEY`/`S2_API_KEY` as `x-api-key` when configured). When Layer 3 is unavailable (429/quota, network, no credentials), the audit MUST degrade to two layers and disclose it in `CITATION_AUDIT.json` (`verification_depth: "2-layer-degraded"` + `layers_verified` + `layer3_status` + `layer3_detail`; full vocabulary in `skills/shared-references/schemas/CITATION_AUDIT.schema.json`) — claiming 3 layers that did not run is a fabricated audit record. Zero fabricated references.
6. Figures only via `scripts/plotting/render_figure.py` (15 engines incl. declarative recipes, Nature A1–A11 audit).
7. 3-round fallback cap per failure type; then BLOCKED + surface to the human.

## Key paths
- Orchestrator: `skills/orchestrator/auto-pipeline/SKILL.md`
- Kernel: `kernel/sciforge/` (`pipeline.py` state machine, `evolve.py` PUCT+MAP-Elites, `review.py` cross-model panel)
- Registered verdicts: `skills/shared-references/schemas/*.schema.json` (22 registered verdict schemas incl. FAIRNESS.json, plus RUNSTATE.schema.json)
- v1.7.2 protocol layer: `kernel/sciforge/{nodes,rep,sources,sota,memory}.py` + `skills/shared-references/s2-protocol.md` §10 (node fork / claim anchors / REP / semantic memory / batch sota / sources)
- Gates: `scripts/{validate_verdicts,security_scan,gap_gate,leakage_scan,fairness_gate,ci_check}.py`; Mode A batch entry: `scripts/gate_all.py`
- Reproduction: `REPRODUCE.md` · 30-item plan: `EVOLUTION_PLAN.md`

## Gotchas
- Workspace `.sciforge/` dirs are gitignored (exception: `fixtures/e2e_minimal/.sciforge/`).
- Version 1.7.4 is pinned across package.json + CITATION.cff + both READMEs + all 29 SKILL.md frontmatters (ci_check enforces the first four).
- Kernel needs Python ≥3.10 (use `.venv/bin/python`); the system python3.9 cannot run it. If `.venv/bin/python` is a broken symlink (e.g. after removing the interpreter it pointed at), `scripts/ci_check.py`'s environment leg reports it with a fix command.
- When the kernel dispatches to you (`claude -p`), respond with ONLY the JSON verdict object as your final message.
- **`events.ndjson` is hash-chained (v1.7.4)**: every event carries `prev_hash` + `hash`. Editing or appending to it by hand breaks the chain, and `recover()` then refuses to rebuild the run (`paused_blocked`, `reason_code=event_log_integrity_broken`). Never hand-edit an event log, and never regenerate `fixtures/e2e_minimal/.sciforge/events.ndjson` by hand — drive the real `Kernel` with `host="mock"` and copy the output. Pre-v1.7.4 chainless logs are accepted as `legacy`.
- Run flags (`human_skip`, `test_mode`) are read from the append-only `run_started` event, **not** from RUNSTATE.json — editing the snapshot cannot self-approve a human checkpoint.
- **Never run `scripts/gate_all.py` (or `s2_audit`/`integrity_monitor`) directly against `fixtures/e2e_minimal`**: they write side-effect artifacts (`AUDIT_TRAIL.json`, `INTEGRITY_MONITOR.json`) into the checked-in fixture. `tests/test_e2e_smoke.py` asserts the fixture stays clean, and `.gitignore` excludes those two names. Copy the fixture to a tmp dir first.
- The review panel's independence is disclosed, not enforced: with the shipped `providers.json` (review/adjudication/grading all on one model) `REVIEW_PANEL.json.panel_independence.status` is `homogeneous_degraded`. Point those roles at different backends to get `heterogeneous`.
