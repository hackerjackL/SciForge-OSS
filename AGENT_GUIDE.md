# SciForge-OSS Agent Guide

> **Status**: The single entry orchestrator for OSS is `/auto-pipeline`. It executes a complete 26-node DAG research loop on **one** problem supplied by the human user's prompt. **OSS does NOT auto-iterate over all problems** — each invocation = one Q-id = one complete pipeline run end-to-end.
>
> **All-domain support**: SciForge-OSS is not restricted to any discipline. Physics, mathematics, computer science, medicine, economics, education, materials science, earth science, atmospheric science, astronomy, chemistry, engineering, sensors, optoelectronics — any scientific domain can use it.

---

## Two consumption modes (v1.5.0)

This guide is the entry for **Mode A**. Since v1.5.0 the repo splits *knowledge* (Markdown, this guide) from *control* (code, `kernel/`):

| Mode | Who runs the loop | How you (the agent) participate | Guarantees |
|------|------------------|--------------------------------|------------|
| **A — skills-only (host agent)** | **You** read this guide + the phase `SKILL.md`s and execute `/auto-pipeline` turn by turn | Full autonomy; you are the orchestrator | Gates are advisory: the scripts exist and the contracts require them, but you must invoke them. Two gate families cannot run at all — claim anchors and REP-plan compliance — because their inputs (`NODES.json`, `REP.json`) are produced only by the kernel. Run `python3 scripts/gate_all.py <workspace>` for the full battery; it reports those two as `UNPROTECTED`. |
| **B — runtime kernel** | `kernel/` Python state machine (`sciforge run --host claude\|codex`) dispatches you **per phase** | You receive a pointer-load bundle (`.sciforge/refine-logs/phase_<id>.bundle.md`) and return a JSON verdict; the kernel enforces every gate and refuses to advance past a failure | Every gate is enforced inside `commit_boundary()`, boundaries are event-sourced and resumable, HITL checkpoints and the 3-round cap are code, token cost is measured |

In Mode B you never have to remember the contracts — the kernel recites the hard constraints into your bundle at every boundary, runs the validators, and blocks bad transitions. Everything below still describes the DAG semantics you execute in either mode.

### Guarantee matrix (v1.7.3)

The DAG is identical across modes; the enforcement strength is not. **Enforced** means a failed gate blocks the state transition. **Advisory** means the script exists and the contract requires it, but skipping it does not mechanically stop the run. **Not in force** means the input artifact is produced only by the kernel, so the check SKIPs or has nothing to inspect. Every row is verifiable in `kernel/config/phasegraph.json`, `kernel/sciforge/gates.py`, and the named script.

| Gate / mechanism (source) | Mode B — kernel | Mode A — skills-only |
|---|---|---|
| Verdict schema validation ([`scripts/validate_verdicts.py`](scripts/validate_verdicts.py)) | Enforced at every boundary; `--strict` from phase 5; `--strict --require-complete` at wrap-up | Advisory; `gate_all.py` runs it |
| REP plan + off-plan loopback detection ([`kernel/sciforge/rep.py`](kernel/sciforge/rep.py)) | Enforced: compiled at phase 1, `check_plan` on every boundary from phase 2. A fired loopback's `fallback_consumed` result is recorded in the event log — an off-plan loopback is recorded, not blocked | Not in force: nothing compiles `REP.json`; `gate_all.py` reports `rep_plan_present` as UNPROTECTED |
| Node registry + claim anchors ([`kernel/sciforge/nodes.py`](kernel/sciforge/nodes.py), [`scripts/claim_anchor_gate.py`](scripts/claim_anchor_gate.py)) | Enforced: nodes auto-registered after 6b/6c/10, claims anchored after 10, gate run at wrap-up (16) | Not in force: `NODES.json` is never written, so the gate SKIPs; `gate_all.py` reports UNPROTECTED whenever claims or experiment evidence exist |
| Node fork / resume from a node (`sciforge fork`) | Available (`nodes.fork`) | Not available |
| Method registry hash lock (`REGISTRY_HASH.txt`) | Enforced at 5 by the `hash` gate (missing/BLOCKED/malformed refuses the boundary) | Advisory: the method-registry skill writes it; `gate_all.py` validates the file in either canonical location |
| INV-G1 problem anchor (`PROBLEM_HASH.txt`) | Enforced at 9 by `hash_match` against the `problem_hash` frozen in RUNSTATE | Partly protected: the invariant-check skill writes the hash file, but RUNSTATE carries no frozen reference by default, so `gate_all.py` reports `inv_g1` as UNPROTECTED unless the workspace records one |
| Security scan of agent scripts ([`scripts/security_scan.py`](scripts/security_scan.py)) | Enforced at 6b/6c over `src/**/*.py` + `experiments/**/*.py`; a BLOCKED-class finding refuses the boundary | Advisory; `gate_all.py` runs the same scan |
| Dependency allowlist ([`scripts/dep_gate.py`](scripts/dep_gate.py)) | Enforced at 6b/6c | Advisory; `gate_all.py` |
| Pre-execution integrity monitor ([`kernel/sciforge/s2/monitor.py`](kernel/sciforge/s2/monitor.py), [`scripts/s2_integrity_gate.py`](scripts/s2_integrity_gate.py)) | Enforced at 6b/6c; the semantic D1 tier runs only when a provider gateway is configured | Advisory: the CLI runs the deterministic D2/D3 core; D1 needs `--strict-llm` and configured providers (`gate_all.py --integrity-llm`) |
| Smoke gate ([`scripts/smoke_gate.py`](scripts/smoke_gate.py)) | Enforced at 6c | Advisory; `gate_all.py` |
| Subset→full ladder ([`scripts/s2_ladder_gate.py`](scripts/s2_ladder_gate.py)) | Enforced at 6c | Advisory; `gate_all.py` |
| Ablation ledger ([`scripts/s2_ablation_gate.py`](scripts/s2_ablation_gate.py)) | Enforced at 10 | Advisory; `gate_all.py` |
| Certified-interval claims ([`scripts/arb_verify.py`](scripts/arb_verify.py)) | Enforced at 10 | Advisory; `gate_all.py` |
| TDAL score ([`scripts/tdal_compute.py`](scripts/tdal_compute.py)) | Not a gate: the kernel never invokes it | Not a gate; `gate_all.py` reports it as INFO |
| Figure embedding + renderer audit ([`scripts/check_figure_embedding.py`](scripts/check_figure_embedding.py)) | Enforced at 11 | Advisory; `gate_all.py` |
| Figure presentation ([`scripts/figure_style_gate.py`](scripts/figure_style_gate.py)) | Enforced at 11 | Advisory; `gate_all.py` |
| Quality-gate marker (`QUALITY_GATE.json`) | Enforced at 12 (a missing marker FAILs the boundary) | Advisory: the agent must write the marker; `gate_all.py` checks presence |
| Fantasy-prevention ([`scripts/fantasy_gate.py`](scripts/fantasy_gate.py)) | Enforced at 12 | Advisory; `gate_all.py` |
| Pipeline-leakage scrub ([`scripts/leakage_scan.py`](scripts/leakage_scan.py)) | Enforced at 13 (classes A–L, writes `LEAKAGE_SCRUB.json`) | Advisory; `gate_all.py` |
| Compile audit (`PAPER_COMPILE.json` + `LEAKAGE_SCRUB.json`) | Enforced at 13; compile warnings are hard only under `discipline=strict`, disclosed under balanced/lean | Advisory: the agent must write the marker; `gate_all.py` re-checks the same conditions |
| Citation-audit marker (`CITATION_AUDIT.json`) | Enforced at 15 | Advisory; `gate_all.py` checks presence |
| Sentence-level citation support ([`scripts/citation_support.py`](scripts/citation_support.py)) | Enforced at 15 | Advisory; `gate_all.py` |
| DOI resolution ([`scripts/doi_gate.py`](scripts/doi_gate.py)) | Enforced at 15 (network resolution; unresolved entries are dropped) | Advisory; `gate_all.py` (`--offline` is structure-only and weaker) |
| Fairness ledger ([`scripts/fairness_gate.py`](scripts/fairness_gate.py)) | Enforced at 15.5 (exit 3 = no ledger → SKIP). Cross-validation of split hashes / seed counts / budget against raw evidence is always in force, because RUNSTATE and the event log exist | Advisory; `gate_all.py`. With no co-located raw evidence (`scope=ledger_only`) the cross-validation layer cannot run, so `gate_all.py` reports UNPROTECTED instead of PASS |
| Submission readiness ([`scripts/submission_ready.py`](scripts/submission_ready.py)) | Enforced at 15.5: READY/MINOR_REV pass (exit 0); MAJOR_REV (exit 1 → WARN) **and** NOT_READY (exit 2 → FAIL) both block the boundary, since WARN is not in the pass set {PASS, SKIP, NOT_APPLICABLE} | Same tiers; `gate_all.py` fails on both MAJOR_REV and NOT_READY so the two modes cannot disagree about submittability |
| Wrap-up completeness (`s2_audit`, `workspace_hygiene`, `completion_gate`, `claim_anchor`) | Enforced at 16 (`wrap_up_gates`) | Advisory; `gate_all.py` |
| Single-entry mechanical audit ([`scripts/sciforge_audit.py`](scripts/sciforge_audit.py)) | Not part of `commit_boundary` — the wrap-up `pipeline_audit` entry is deferred to the host; runnable via `sciforge gate wrapup` | Advisory; `gate_all.py` |
| Hard-constraint re-injection at every boundary ([`kernel/sciforge/bundle.py`](kernel/sciforge/bundle.py)) | Enforced: every phase bundle ends with a verbatim recitation computed from live state | Not present: constraints live in the SKILL contracts and shared references |
| Human checkpoints (idea pick, method approval, KILL) | Code: `Approvals`, `APPROVAL_LOG.txt`, RUNSTATE `paused_checkpoint` | Prose: the agent writes the same records and honors `human_skip` / `test_mode` |
| 3-round fallback cap | Code: counted from the event log (`Kernel._round_count`) | Prose: the agent counts |
| Run budget ledger (`RUN_BUDGET.json`) | Code: `init_budget` / `accrue` / `breach` at boundaries | Prose: the agent writes and checks the ledger |
| Event-sourced resume | Code: `events.ndjson` replay (`state.recover`) | Prose: `RUNSTATE.json` is the only cursor |

**Using Mode A with the strongest available assurance.** Run `python3 scripts/gate_all.py <workspace>` at every phase boundary; it runs every gate that applies, preserves each gate's own SKIP / NOT_APPLICABLE semantics (theory-only routes are not failed by experiment gates), and prints an `UNPROTECTED` list naming the guarantees that are not in force. If a run needs claim-anchor protection or REP-plan compliance, use Mode B — `gate_all.py` cannot create those guarantees, it only reports their absence. `gate_all.py` is a `scripts/` tool: the Markdown skills remain executable without a Python environment, at the lower assurance level above.

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
| **Orchestrator** | `/auto-pipeline` | Single entry — 26-node DAG research loop on one problem (EG at Phase 2.5b) |
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

## The 26-Node DAG Loop

```
Phase  0: load problem (freeze Q-id — INV-G1 anchor)
Phase  1: problem understanding & decomposition (compiles REP.json)
Phase 1a: /domain-signature (OPTIONAL fast-path hint)
Phase 1b: /domain-learner (MUST, sole writer of domain-signature.json)
Phase 4broad: /universal-retrieval — broad literature wave + GAP_REPORT.md (MUST)
Phase  2: /idea-discovery [DAG branching] — 4 perspectives + MCTS iteration
Phase 2.5: /adversarial-falsification — assumption/counterexample/literature attacks
Phase 2.5b: engineering-grounding (EG) — 8-dimension AI feasibility report
Phase  3: /novelty-check [DAG gate] — 4-axis + frontier + collision audit
    └ Forced human checkpoint: pick the final idea
Phase 4targeted: /universal-retrieval — targeted waves per survivor
Phase  5: /method-registry — method binding + hash lock + forced human approval
    └ Forced human checkpoint: approve the method registry
Phase  6: /verification-routing — experiment-first (default) / theory-only / hybrid
Phase 6a: /theory-derivation [ROUTED] — SymPy derivation + step-by-step verification
Phase 6b: /experiment-execution --stage=toy [ROUTED] — idea life-or-death gate
Phase 6c: /experiment-execution --stage=full --background [ROUTED] — full matrix
Phase  7: /leakage-audit — Type I logic leaks + Type IV escape audit
Phase  8: /logic-verification — 6-dimension / 20-category audit
Phase  9: /invariant-check — INV-G1 problem-anchor freeze
Phase 10: /result-to-claim — 3-fidelity claim gate + TDAL + ablation ledger
Phase 11: /unified-plotting — publication figures (MUST)
Phase 12: /paper-writing — elsarticle template + pipeline-leakage scrub
Phase 13: /paper-compile — zero-warning zero-error compile (MUST)
Phase 14: /auto-review-loop — cross-model review + kill-argument (MUST)
Phase 15: /citation-audit — 3-layer citation + DOI audit
Phase 15.5: /publishability-score — 6-dimension publishability gate
Phase 16: final assembly + artifact archival
```
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

The orchestrator runs the full 26-node loop. Forced human checkpoints after Phase 3 (pick the final idea, before 4targeted) and after Phase 5 (approve the method registry, before verification routing).

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

But the **canonical** workflow is the full 26-node orchestrator loop — partial runs are for debugging only and do not produce a complete artifact chain.

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
- [`skills/orchestrator/auto-pipeline/SKILL.md`](skills/orchestrator/auto-pipeline/SKILL.md) — the 26-node DAG loop orchestrator
- [`skills/shared-references/`](skills/shared-references/) — the shared contract layer (discipline-agnostic)