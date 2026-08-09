# Project Architecture Contract (SciForge-OSS — GitHub-Style, Clean Workspace)

> **Status (v3.0, aligned with output-protocol.md v6.0 two-tier split)**: The single source of truth for the directory layout of EVERY project run — whether the entry was `/auto-pipeline` or a partial/manual skill invocation. Enforces a clean, GitHub-open-source-project-style structure from Phase 0 to wrap-up, so the workspace is inspectable, reproducible, and never accumulates cruft. Pipeline state lives hidden in `.sciforge/`; the visible tree holds only scientific deliverables; directories materialize lazily on first write (output-protocol.md §Lazy Materialization).
>
> **Why this exists**: the user's mandate — "Every project opened like this, from the very start of the auto pipeline to the very end, must have a crystal-clear architecture — very much like a GitHub open-source project; the architecture must be clear. Even when a human does not start from auto-pipeline, the entire workspace is still guaranteed to be clean, tidy, and clear." Without an explicit contract, runs scatter files arbitrarily, leave orphan artifacts, and become unreviewable.

---

## 1. The Standard Project Layout

Every run (auto-pipeline OR partial) produces artifacts under this fixed tree at the project root:

```
{project_root}/                          ← one project = one root dir (the Q-id or a slug)
├── README.md                             ← GitHub-style project README (Phase 0, updated through wrap-up)
├── PROBLEM.md                            ← frozen Q-id + problem statement (Phase 0, INV-G1 anchor)
├── AGENT_DOC.md                          ← Phase-0 config (discipline / venue / methodology / gates)
│
├── .sciforge/                            ← [hidden state layer — v6.0] pipeline state, verification, audit trail
│   ├── RUNSTATE.json                     ← long-horizon resume checkpoint (rewritten at every boundary)
│   ├── MANIFEST.md                       ← every artifact logged here as it is produced
│   ├── PIPELINE_STATUS.md                ← execution report (phase trail)
│   ├── APPROVAL_LOG.txt                  ← human-checkpoint + test_mode bypass log
│   ├── verdicts/                         ← all machine-readable verdicts (flat, fixed names — see output-protocol.md)
│   ├── logs/                             ← pipeline state stream: pipeline.log + phase_<n>.log
│   ├── refine-logs/
│   │   ├── IDEA_CANDIDATES.md / IDEA_DAG.json / MCTS_LOG.md / GAP_ANCHOR_LOG.md
│   │   ├── ENGINEERING_GROUNDING.md      ← EG report (Phase 2.5b)
│   │   ├── FRONTIER_MAP.json             ← frontier node graph (Phase 3)
│   │   ├── FINAL_PROPOSAL.md             ← the selected idea + verification_type (frozen)
│   │   └── domain-signature.json         ← domain signature (Phase 1b, sole writer)
│   └── audits/                           ← narrative audit reports
│       ├── LOGIC_VERIFICATION.md / LEAKAGE_AUDIT.md / INVARIANT_CHECK.md (narratives)
│       ├── CLAIMS_FROM_RESULTS.md        ← 3-fidelity claim gate narrative (Phase 10)
│       ├── AUTO_REVIEW.md                ← cross-model review narrative (Phase 14)
│       └── CITATION_AUDIT.md             ← 3-layer citation audit narrative (Phase 15)
│
├── literature/
│   ├── landscape_report.md               ← literature survey (broad wave)
│   ├── references.bib                    ← verified BibTeX (cumulative across waves)
│   ├── GAP_REPORT.md                     ← gap-mining report, gap-id anchored (v6.0 gap chain)
│   ├── TARGETED_WAVE_LOG.md              ← per-idea targeted retrieval waves (v6.0 gap chain)
│   ├── verified_papers.json              ← structured metadata
│   ├── VERIFICATION_LOG.md               ← per-paper verification status
│   ├── FILTER_CHAIN_AUDIT.json           ← screening-chain completeness audit
│   └── .pending/                         ← background literature queries (if proxy timed out)
│
├── methods/
│   ├── METHOD_REGISTRY.md                ← 8-section registry (Phase 5)
│   ├── METHOD_BINDING.md                 ← derived binding (Phase 5)
│   ├── OUTCOME_CLASSIFICATION.md         ← primary/secondary outcomes (Phase 5)
│   └── EVALUATION_PROTOCOL.md            ← pre-registration quartet narrative (Phase 5)
│
├── derivations/
│   └── {problem_id}/
│       ├── premises.md                   ← frozen assumptions (Phase 6)
│       ├── derivation_output.md          ← derivation report (Phase 6)
│       └── verification_report.md        ← SymPy verification (Phase 6)
│
├── code/                                 ← [single home] for all scripts (v5.0, unchanged)
│   ├── derivations/                      ←   derivation/symbolic-verification scripts
│   ├── experiments/                      ←   experiment scripts (toy/full/ablation/hyperparameter)
│   ├── figures/                          ←   rendering scripts
│   └── utils/
│
├── experiments/                          ← experiment execution layer (deliverables: results + data)
│   ├── toy/session_{timestamp}/          ← toy_experiment.py + RESULT.json + experiment_plan.json
│   ├── full/group_<name>/                ← per-matrix-group results (RESULT.json / data)
│   └── data/<dataset_id>/                ← downloaded raw data
│
├── logs/                                 ← [experiment & training logs ONLY — v6.0]
│   ├── experiments/{experiment_id}.log   ← stdout/stderr tee of each run
│   └── checkpoints/                      ← model/training checkpoints
│
├── figures/                              ← unified-plotting output (PDF+SVG)
│   ├── FIGURE_INDEX.md                   ← all generated figures index
│   └── {figure_name}/
│       ├── output.pdf / output.svg       ← deliverable pair
│       └── figure_audit.json             ← per-figure audit detail
│
├── paper/
│   ├── main.tex                          ← master LaTeX (unified elsarticle skeleton)
│   ├── math_commands.tex                 ← shared notation (from template)
│   ├── references.bib                    ← symlink/copy from literature/references.bib
│   ├── sections/                         ← mode-selected section files (paper-modes §3)
│   ├── figures/                          ← symlinks to ../figures/{name}/output.pdf
│   ├── main.pdf                          ← compiled PDF (zero-warnings)
│   ├── compile.log                       ← LaTeX compile log
│   └── COMPILE_REPORT.json               ← compile status
│
└── output/                               ← final assembled products (archive phase)
    ├── PAPER.md                          ← markdown version (if format=markdown/both)
    ├── PAPER.pdf                         ← copy of paper/main.pdf
    └── ARTIFACT_MANIFEST.json            ← full artifact inventory + hashes
```

---

## 2. README.md (GitHub-Style, Mandatory)

Every project root has a `README.md` (created at Phase 0, updated through Phase 16) that makes the project self-describing — a human landing on the dir knows what it is without reading code.

**README.md required sections**:
```markdown
# {Q-id}: {Problem title}

> Generated by SciForge-OSS auto-pipeline. Started {ISO-8601}. Status: {in-progress|completed|blocked}.

## Problem
{One-paragraph problem statement, frozen at Phase 0}

## Key Result
{One-sentence headline result, filled at Phase 10/16 — "pending" until then}

## Pipeline Status
- verification_type: {theory-only|computational|theory+experiment|qualitative}
- mode: {theory|experiment|computational|survey|hybrid}
- test_mode: {true|false}
- checkpoints_bypassed: {true|false} (if test_mode)

## Directory Layout
See [`project-architecture-contract.md`](./project-architecture-contract.md) § "Required Workspace" for the full canonical tree (this template section is copied into each run's `PIPELINE_STATUS.md`; the link resolves to the contract file itself when viewed in-tree).

## How to Reproduce
1. {entry command that produced this run}
2. {key dependencies — python version, latex, d2, mihomo}

## Artifacts
- Final paper: `output/PAPER.pdf`
- Compiled LaTeX: `paper/main.pdf`
- Figures: `figures/` (PDF+SVG dual)
- Full experiment: `experiments/full/` (if run)
```

The README is UPDATED at each phase boundary (not just written once) — the "Key Result" and "Pipeline Status" sections are filled as the pipeline progresses.

---

## 3. MANIFEST.md (Artifact Inventory, Appended Per-Phase)

Every artifact produced is appended to `.sciforge/MANIFEST.md` as it is created (per the Output Manifest Protocol). The manifest is the single index — a reviewer scans it to see what exists.

**MANIFEST.md format**:
```markdown
# Artifact Manifest — {Q-id}

| Phase | Artifact | Path | Status | Hash (optional) |
|-------|----------|------|--------|-----------------|
| 0 | PROBLEM.md | problem/PROBLEM.md | frozen | sha256:... |
| 2 | IDEA_CANDIDATES.md | .sciforge/refine-logs/IDEA_CANDIDATES.md | done | |
| 4 | references.bib | literature/references.bib | verified (N entries) | |
| 6 | derivation_output.md | derivations/{id}/derivation_output.md | machine-verified | |
| 6b | RESULT.json | experiments/toy/session_*/RESULT.json | PASS | |
| 13 | main.pdf | paper/main.pdf | zero-warnings, X pages | |
| 16 | PAPER.pdf | output/PAPER.pdf | final | sha256:... |
```

---

## 4. Workspace Hygiene Rules (Apply to ALL Entries, Not Just auto-pipeline)

The contract applies whether the entry was `/auto-pipeline` (full 21-phase run) OR a partial/manual skill invocation (e.g., a human running `/theory-derivation` alone for debugging). Rules:

1. **One project = one root dir.** Never scatter artifacts across the filesystem. If a human invokes a skill without a project root, the skill creates `{cwd}/{slug}/` first and writes there.
2. **No orphan files at the root.** Only the top-level entry files (`README.md`, `PROBLEM.md`, `AGENT_DOC.md`, and the registered root contract artifacts — `CLAIMS_FROM_RESULTS.md`, `EXPERIMENT_LOG.md`, `NARRATIVE_REPORT.md`) live at the root. All other artifacts go in a named subdirectory; pipeline state goes in `.sciforge/`.
3. **No orphan subdirectories.** Every subdirectory must contain at least one artifact logged in `MANIFEST.md`. Empty dirs are deleted.
4. **No leftover intermediates.** Build artifacts (`*.aux`, `*.bbl`, `*.log` except `compile.log`, `*.out`) go in `paper/.build/` (gitignored-equivalent) — NOT scattered in `paper/`. `compile.log` is the only log retained at `paper/compile.log`.
5. **Symlinks for shared assets.** `paper/references.bib` and `paper/figures/*.pdf` are symlinks to `literature/references.bib` and `figures/*/output.pdf` — single source of truth, no duplication.
6. **Stale-file detection (Phase 6.5 of paper-compile already).** Any `.tex` in `sections/` not `\input`'ed by `main.tex` is flagged. Same for any figure in `figures/` not referenced in the paper.
7. **Partial-run hygiene.** If a human runs `/theory-derivation` alone (no full pipeline), the skill STILL creates the project tree (`derivations/{id}/`, appends to `MANIFEST.md`) — partial runs do not produce flat-file clutter.

---

## 5. Cleanliness Audit (Phase 16 — Final Assembly)

At Phase 16 (final assembly), the orchestrator runs a cleanliness audit before declaring COMPLETED:

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| README.md exists with all required sections | all sections filled | partial | missing |
| MANIFEST.md lists every produced artifact | complete | <3 missing | >3 missing |
| No orphan files at root (beyond the 4 allowed) | only 4 root files | 1-2 extra | >2 extra |
| No empty subdirectories | none | 1 empty | >1 empty |
| paper/ has only main.tex + sections/ + figures/ + main.pdf + compile.log + COMPILE_REPORT.json (+ .build/) | clean | 1 stray | >1 stray |
| All figures referenced in paper | all referenced | 1 unreferenced | >1 unreferenced |
| Symlinks valid (references.bib, figures) | all resolve | 1 broken | >1 broken |

Verdict: all-PASS → COMPLETED; any WARN → COMPLETED with warnings logged; any FAIL → BLOCKED (re-clean before declaring done).

---

## 6. Boundaries

- **The project root is the single source of truth.** No artifacts outside it. No absolute paths in artifacts that break portability (use relative paths within the project).
- **README.md is mandatory, not optional.** A project without a README is not "clean" — it is incomplete.
- **MANIFEST.md is appended, never overwritten.** Each phase adds its row; no phase deletes prior rows.
- **Partial runs obey the same hygiene.** A `/theory-derivation` invocation alone still creates the tree — no flat-file clutter.
- **The cleanliness audit is a Phase 16 gate.** A run is not COMPLETED until the audit passes (or WARNs with logged reasons).
- **No hidden files except `.sciforge/` (the v6.0 hidden state layer — durable, part of the run record), `.build/` (LaTeX intermediates) and `.pending/` (background literature).** `.build/` and `.pending/` are gitignored-equivalent and not part of the deliverable.

---

## 7. See Also

- [`output-manifest.md`](output-manifest.md) — the per-artifact manifest protocol (this contract defines the project-level structure)
- [`output-versioning.md`](output-versioning.md) — timestamped-first-then-fixed-name file protocol
- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — the orchestrator that enforces this structure
- [`figure-quality-contract.md`](figure-quality-contract.md) — the `figures/` subdirectory dual-output contract
