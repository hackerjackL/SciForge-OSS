# Output Protocol (SciForge-OSS — Merged)

> **Core**: every output is written in two versions — a timestamped version (history) + a fixed-name version (latest).

## Versioned Writes

1. Write the timestamped file: `{FILENAME}_{YYYYMMDD_HHmmss}.md`
2. Copy to the fixed-name file: `{FILENAME}.md` (overwritten with the latest version)
3. Downstream skills always read the fixed-name file

**Timestamped**: IDEA_REPORT.md, FINAL_PROPOSAL.md, AUTO_REVIEW.md, paper/main.tex, status files
**Not timestamped**: append-only files (findings.md), per-round numbered files (round_N_*.md), .sciforge/MANIFEST.md

## Manifest Records

After every write, append one row to `.sciforge/MANIFEST.md`:

```markdown
| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
| 2026-07-20 14:30 | /idea-discovery | .sciforge/refine-logs/IDEA_CANDIDATES.md | idea-discovery | 12 ideas generated |
```

## Artifact Directory Tree (v6.0 — two-tier split: `.sciforge/` hidden state layer + delivery layer)

**v6.0 design drivers**: (1) long-horizon runs (days, not minutes — cf. CRUX shadow evaluation, arXiv:2607.27191) need durable machine state with an explicit resume contract; (2) a human opening a finished workspace should see ONLY the scientific deliverables — everything that serves the pipeline itself (verdicts, decision-process logs, audit narratives, manifest) lives in ONE hidden directory; (3) `logs/` keeps its plain meaning: experiment/training logs; (4) domains differ — a humanities run must not be cluttered with empty experiment/figure directories.

```
{problem_id}/
├── .sciforge/          ← [hidden state layer] long-horizon resume + verification + audit trail (v6.0)
│   ├── RUNSTATE.json   ←   long-horizon checkpoint, rewritten at every phase boundary (resume contract, v6.0)
│   ├── .sciforge/MANIFEST.md     ←   artifact write audit trail (every write appends one row)
│   ├── .sciforge/APPROVAL_LOG.txt ←  human-checkpoint approval records (method lock, idea selection, KILL confirmation)
│   ├── .sciforge/PIPELINE_STATUS.md ← execution report (the full phase trail)
│   ├── .sciforge/verdicts/       ←   the [unified directory] for all machine-readable pipeline verdicts (flat, fixed names — v5.2 contract unchanged, only the home moved)
│   │   ├── VERIFICATION_ROUTING.json   ← verification routing decision + na_verdicts declaration (Phase 6 entry point)
│   │   ├── PROBLEM_HASH.txt            ← INV-G1 problem-content hash (invariant-check)
│   │   ├── REGISTRY_HASH.txt           ← method hash-lock (method-registry)
│   │   ├── EXPERIMENT_MATRIX.json      ← mandatory experiment matrix (method-registry §3.5)
│   │   ├── EVALUATION_PROTOCOL.json    ← pre-registered evaluation protocol quartet (method-registry §3.6; fair evaluation)
│   │   ├── BUDGET_FLOOR.json           ← exploration budget-floor completion criteria (experiment-execution)
│   │   ├── PROOF_AUDIT.json            ← step-by-step derivation verification (theory-derivation)
│   │   ├── LOGIC_VERIFICATION.json     ← 6-dimension logic audit (logic-verification)
│   │   ├── LEAKAGE_AUDIT.json          ← Type I/IV audit (leakage-audit)
│   │   ├── BLINDSPOT_CHECK.json        ← domain blind-spot audit (auto-review-loop B.2)
│   │   ├── REVIEW_STATE.json           ← review-round state + response_class (auto-review-loop)
│   │   ├── REVIEW_LEDGER.json          ← review-comment ledger (auto-review-loop)
│   │   ├── KILL_ARGUMENT.json          ← kill argument (kill-argument)
│   │   ├── PAPER_CLAIM_AUDIT.json      ← paper-claim consistency (paper-writing self-check)
│   │   ├── LEAKAGE_SCRUB.json          ← LaTeX leakage scrub gate (paper-writing §3.5)
│   │   ├── CITATION_AUDIT.json         ← 3-layer citation verification (citation-audit)
│   │   ├── INVARIANT_CHECK.json        ← invariant-check result (invariant-check; narrative report lives in .sciforge/audits/)
│   │   ├── PUBLISHABILITY_SCORE.json   ← final publishability score (publishability-score)
│   │   ├── RUN_BUDGET.json             ← global run-budget ledger (v5.3: wall_clock/api_cost/pivot_count/ba_used;
│   │   │                                  the orchestrator books entries and checks the caps at every phase boundary;
│   │   │                                  bookkeeping from the old BA_BUDGET.json is merged into this file, BA_BUDGET.json remains as a read-only fallback)
│   │   ├── FIGURE_AUDITS.json          ← all-figure audit summary mirror (unified-plotting; per-figure detail still ships with each figure_audit.json)
│   │   └── PIPELINE_VERDICT_SUMMARY.md ← pipeline verdict overview (rewritten by the orchestrator at every phase boundary; derived document, the only .md allowed inside .sciforge/verdicts/)
│   ├── logs/           ←   [pipeline state stream] (v6.0: pipeline logs only; experiment/training logs live in visible logs/)
│   │   ├── pipeline.log    ← auto-pipeline status stream (the single authoritative status record)
│   │   └── phase_<n>.log   ← per-phase run logs (written by each skill, no longer scattered)
│   ├── .sciforge/refine-logs/    ←   decision-process artifacts (idea-discovery + novelty-check + domain learning)
│   │   ├── IDEA_REPORT.md / IDEA_CANDIDATES.md / IDEA_DAG.json / MCTS_LOG.md
│   │   ├── GAP_ANCHOR_LOG.md  ← gap-anchoring decision per idea (v6.0 gap chain)
│   │   ├── FRONTIER_MAP.json  ← frontier node graph (novelty-check)
│   │   ├── domain-signature.json / domain-signature-hint.json ← domain signature (Phase 1b sole writer; 1a hint)
│   │   ├── FINAL_PROPOSAL.md  ← frozen selected idea
│   │   └── abandoned/<idea_id>/ ← KILL/PIVOT archives of rejected branches
│   ├── audits/         ←   [narrative audit reports] (v6.0 merge of .sciforge/audits/ + .sciforge/audits/ + .sciforge/audits/)
│   │   ├── LOGIC_VERIFICATION.md / LEAKAGE_AUDIT.md / INVARIANT_CHECK.md / Type_I.md … Type_IV.md
│   │   ├── CLAIMS_FROM_RESULTS.md ← 3-fidelity claim gate narrative (result-to-claim)
│   │   ├── AUTO_REVIEW.md         ← cross-model review narrative (auto-review-loop)
│   │   └── CITATION_AUDIT.md      ← 3-layer citation audit narrative (citation-audit)
│   └── tmp/            ←   scratch space (rendering intermediates, debug scripts, download caches); whole directory deleted at wrap-up
├── literature/         ← universal-retrieval artifacts (visible: the verified knowledge base is itself a deliverable)
│   ├── references.bib / landscape_report.md / verified_papers.json / VERIFICATION_LOG.md
│   ├── GAP_REPORT.md   ←   literature gap-mining report, broad-wave output (v6.0 gap chain; every gap carries a gap-id + cited evidence)
│   └── TARGETED_WAVE_LOG.md ← per-idea targeted retrieval waves (append-only, v6.0 gap chain)
├── methods/            ← method-registry artifacts (METHOD_REGISTRY.md / METHOD_BINDING.md / OUTCOME_CLASSIFICATION.md / EVALUATION_PROTOCOL.md)
├── derivations/        ← theory-derivation artifacts (.md documents only; scripts go to code/)
├── code/               ← the [single home] for algorithms and source code (v5.0)
│   ├── derivations/    ←   derivation/symbolic-verification scripts (formerly derivations/*.py, moved here)
│   ├── experiments/    ←   experiment scripts (toy/full/ablation/hyperparameter, incl. group_<name>/)
│   ├── figures/        ←   rendering scripts (render.py / spec.d2 / *.composite.json)
│   └── utils/          ←   shared utility functions
├── experiments/        ← experiment-execution artifacts (RESULT.json/data; scripts go to code/experiments/)
├── logs/               ← [experiment & training logs ONLY] (v6.0: "logs" restored to its plain meaning)
│   ├── experiments/    ←   {experiment_id}.log (stdout/stderr tee) + STATUS.json summary mirror
│   └── checkpoints/    ←   model/training checkpoints of experiment runs
├── figures/            ← unified-plotting artifacts (PDF+SVG deliverables + figure_audit.json per figure; summary verdict mirror .sciforge/verdicts/FIGURE_AUDITS.json)
├── paper/              ← paper-writing + paper-compile artifacts (compiled output and .tex; verdicts go to .sciforge/verdicts/)
└── output/             ← final archive (submission bundle) — the ONLY thing a submission needs
```

**Top-level entry files** (allowed at the `{problem_id}/` root besides the directories above): `README.md` (GitHub-style project README), `AGENT_DOC.md` (Phase-0 config), `PROBLEM.md` (frozen problem statement, INV-G1 anchor), `CLAIMS_FROM_RESULTS.md`, `EXPERIMENT_LOG.md`, `NARRATIVE_REPORT.md` (registered root-level contract artifacts — see `artifact-registry.md`). Everything else belongs in a directory.

### Lazy Materialization (v6.0 — cures "empty folders cluttering domain-diverse runs")

The tree above is a **registry of canonical locations, not a pre-created skeleton**. Directories are created **on first canonical write** and never speculatively:

1. A skill that writes an artifact creates its target directory at write time (`mkdir -p` semantics); no phase pre-creates the tree.
2. Whole subtrees that a run legitimately never touches simply never exist. A theory-only/humanities run has no `experiments/`, `code/experiments/`, `logs/`, or `figures/` — that is CORRECT, not an error to be filled with placeholders.
3. Which verdicts a run will never produce is DECLARED, not guessed: `.sciforge/verdicts/VERIFICATION_ROUTING.json` carries `na_verdicts` (filenames from the .sciforge/verdicts/ table above that the chosen route + declared skips make Not-Applicable). `validate_verdicts.py` reports them as **N/A** instead of pending, and the wrap-up cleanliness audit treats the corresponding absent directories as legitimate. Default declaration sets per route are defined in [`verification-routing.md`](verification-routing.md) §5; the orchestrator copies the applicable set into the routing decision at Phase 6 entry and extends it with later declared skips (e.g., a Phase 11 figure-skip adds `FIGURE_AUDITS.json`).
4. Emptiness rule: because of rule 1 an empty directory can only arise from an aborted write — the wrap-up protocol deletes it (after checking the MANIFEST for a contract reference).

### Two-Tier Split Principles (v6.0)

1. **Delivery layer (visible)**: everything a reviewer/submitter needs — literature, methods, derivations, code, experiments, figures, paper, output, plus experiment logs. Post-paper engagement (submission, rebuttal correspondence) is human territory; the pipeline's job ends at a complete `output/` bundle.
2. **`.sciforge/` (hidden)**: pipeline state, verification verdicts, decision-process trail, manifest, resume checkpoint. Hidden so a delivered workspace reads like a clean GitHub project; durable so a days-long run can resume after any interruption.
3. **.sciforge/verdicts/ contract unchanged from v5.2** — flat, fixed names, one scan reveals the whole pipeline's judgment state. Only its home moved (`.sciforge/verdicts/` → `.sciforge/verdicts/`).
4. **Single status file**: PIPELINE_STATUS events exist only in `.sciforge/logs/pipeline.log`; no stage may create its own PIPELINE_STATUS copy; at summarization time the orchestrator reads the entire `.sciforge/verdicts/` directory to generate the pipeline verdict overview (`.sciforge/verdicts/PIPELINE_VERDICT_SUMMARY.md`, rewritten at every phase boundary).
5. **Migration compatibility (reads fall back, writes never do)**: reads try the v6.0 path first, then the legacy path — `.sciforge/verdicts/` ← `verdicts/`; `.sciforge/logs/` ← `logs/` (pipeline state files); `.sciforge/refine-logs/` ← `refine-logs/`; `.sciforge/audits/` ← `audit_report/` + `review-stage/` + `citation_audit/`; `.sciforge/MANIFEST.md` ← root `MANIFEST.md`. Writes always go to the v6.0 path. A resumed run that finds only legacy paths migrates them into `.sciforge/` at the next boundary (logged as a cleanup event).

## Long-Horizon Resume Contract (v6.0 — RUNSTATE.json)

Runs are long (hours to days) and sessions die. `.sciforge/RUNSTATE.json` is the machine-readable checkpoint that makes interruption survivable:

1. **Written at every phase boundary** (and at forced human checkpoints) by the orchestrator: current phase, last completed boundary, next action, run status, pending human approvals, budget snapshot. Schema: `skills/shared-references/schemas/RUNSTATE.schema.json`.
2. **Resume protocol** (orchestrator startup): if `{problem_id}/.sciforge/RUNSTATE.json` exists with status ≠ `completed` → run `python3 scripts/validate_verdicts.py {problem_id}/.sciforge/verdicts/` to verify state integrity → migrate any legacy-path artifacts (rule 5 above) → resume from `next_action`. A missing/corrupt RUNSTATE with a non-empty .sciforge/verdicts/ directory is itself a WARN (`resume_state_lost`) — resume is still possible from the verdict trail, but the human is told the checkpoint was lost.
3. **Status vocabulary**: `running` / `paused_checkpoint` (awaiting human approval) / `paused_blocked` (BLOCKED verdict, human decision needed) / `completed` / `killed`.

## Verdict Schema Enforcement (v5.3, extended v6.0 — cures "misspelled/omitted fields going unnoticed")

1. **Every verdict JSON must pass schema validation**: the field contract is defined by `skills/shared-references/schemas/<NAME>.schema.json` (draft 2020-12); writers must not misspell or omit required fields; hash files (PROBLEM_HASH.txt / REGISTRY_HASH.txt) must be a single-line lowercase sha256 (64 hex characters)
2. **The orchestrator runs it at every phase boundary and at wrap-up**: `python3 scripts/validate_verdicts.py {problem_id}/.sciforge/verdicts/` — registered files are schema-validated plus cross-field invariants (the 6-state verdict vocabulary of the audit family, audited_input_hashes of audit JSONs); unregistered *.json → WARN; a missing registered file is recorded as pending, or as **N/A** when listed in `VERIFICATION_ROUTING.json` `na_verdicts` (routing-aware expectation, v6.0)
3. **Handling violations**: default mode → WARN (record and continue); `--strict` mode → BLOCKED (treated as FAIL, blocks the current phase boundary)
4. A new verdict must first have its schema added in this directory and be registered in the validator (steps in `skills/shared-references/schemas/README.md`)

**Single-Home Principle (v5.0, paths updated v6.0 — cures "directory chaos + code duplication")**:
1. Every artifact class has a **unique canonical path** (table above); artifacts of the same class written elsewhere → audit WARN, and the writer is responsible for migrating them
2. **Code exists in exactly one place, `code/`**: experiment/derivation/rendering scripts all go into the corresponding subdirectory of `code/`; `derivations/`, `figures/`, `experiments/` hold **only artifacts and documents** (.md/.json/PDF/SVG/data), **never scripts** — this eliminates the "code gets copied into paper/ once more during paper writing" duplication (no code copies inside paper/; code references go only through the Reproducibility statement pointing at `code/`)
3. **Pipeline logs are centralized only in `.sciforge/logs/`**: stages no longer each create their own log files scattered in the root directory; `pipeline.log` is the single authoritative status stream (containing the PIPELINE_STATUS events), and each skill's process logs go to `.sciforge/logs/phase_<n>.log`. **Experiment/training logs** stay visible under `logs/` (their consumers are humans debugging runs, and they belong with the experiment deliverables)
4. Migration compatibility: reads check the new canonical path first and fall back to the old path if not found (backward compatible with old run directories); writes always use the new path

## Path Fallback Rules

On reads, the stage-scoped path is tried first; if not found, fall back to the root-level path (backward compatibility). Writes always use the stage-scoped path. For the v6.0 relocation, see the Two-Tier Split Principles rule 5.

## Workspace Hygiene Contract (v5.2, updated v6.0 — cures "workspace chaos/duplication/junk files")

**Naming conventions (enforced across the whole pipeline)**:
1. **UPPERCASE + underscores** (`CLAIMS_FROM_RESULTS.md`, `REGISTRY_HASH.txt`) for **contract artifacts** (read by downstream skills under a fixed name); **lowercase + hyphens** (`derivation_output.md`-style narrative artifacts) for intra-stage artifacts — "contract files" and "process files" become distinguishable at a glance
2. **Version numbers go into content, never into filenames**: `report_v2.md`, `final_FINAL.tex`, `draft3.py` are forbidden — iterate via versioned writes (see above in this section) and `revision_log.md`; filenames stay stable (downstream consumers reference them by fixed name; renaming breaks the link)
3. **Experiment directories**: `experiments/full/group_<name>/` (name = the group name from the experiment matrix); **forbidden**: semantic-free names like `exp1/`, `test2/`, `new_folder/`
4. **One folder per figure**: `figures/<fig_id>/` (fig_id identical to the LaTeX label) — figure artifacts are never mixed with other artifacts

**Temporary-file ban (hard rules)**:
1. The workspace root directory **allows only** the delivery-layer directories defined in the directory tree + `.sciforge/` + the top-level entry files listed there; any stray `.py`/`.tmp`/`.bak`/`.swp`/`nohup.out`/`core.*`/`*.orig`/`__pycache__/` → deleted or migrated by the wrap-up cleanup protocol
2. **Temporary files go only into `/tmp` or `.sciforge/tmp/`**: debug scripts, rendering intermediates, and download caches are all written to `/tmp` (outside the pipeline) or `.sciforge/tmp/` (whole directory deleted at wrap-up); **never** into the workspace root or stage directories
3. Experiment datasets (downloaded raw data) go into `experiments/data/<dataset_id>/`, not into `code/`, not into the workspace root
4. `nohup.out` / background-process output must always be redirected to `logs/experiments/<experiment_id>.log` (the experiment-execution dispatch command template forces a tee to that path)

**Orphan-artifact governance**:
1. **Orphan = an artifact with no upstream reference**: every stage artifact must be referenced by at least one downstream contract (the MANIFEST's `consumer` field); a MANIFEST entry written with an empty consumer → WARN `orphan_artifact`
2. **Artifacts of rejected branches**: after a KILL/PIVOT, the artifacts of the rejected idea are **not deleted** (audit tracing needs them) but moved en masse into the `.sciforge/refine-logs/abandoned/<idea_id>/` archive — the active workspace keeps only the current idea's artifacts; history stays inspectable but out of the way
3. **Zero tolerance for duplicate artifacts**: the same content present at two paths (e.g., code in both `code/` and `paper/`) → audit FAIL `duplicate_artifact`; symlinks are the only legitimate "same artifact visible in multiple places" mechanism

**Wrap-up cleanup protocol (executed at every phase boundary + at the pipeline end state)**:
1. Scan the workspace: delete `.sciforge/tmp/`, empty directories, `*.pyc`/`__pycache__/`, 0-byte files (keep anything with a contract reference)
2. **Domain-aware check (v6.0)**: absent directories are cross-checked against `VERIFICATION_ROUTING.json` (`route` + `na_verdicts`) — subtrees the route legitimately never produces are recorded as N/A in the verdict summary, NOT flagged and never re-created as empty placeholders
3. Reconcile with the MANIFEST: every active artifact is at its canonical path and has a consumer; violators are migrated/warned (files with content are never silently deleted)
4. Write one cleanup event to `.sciforge/logs/pipeline.log` (what was deleted, what was migrated, what was declared N/A) — the cleanup action itself is auditable
5. Pipeline end state (archive phase): the `output/` submission bundle contains only deliverables (paper PDF + LaTeX sources + figures PDF/SVG + citation bib), **not** intermediate artifacts — verify the checklist file by file before packing

## Stale-State Detection

Default staleness threshold for status files (REVIEW_STATE.json, RUNSTATE.json etc.): 24 hours. When stale, warn the user, who may continue or start over.

## Output Language

Respect the project's language setting (`language=chinese` outputs Chinese, English by default; figures and code comments use English identifiers). The language of the paper body and title follows the language declaration made at pipeline start; languages must not be mixed inside a single deliverable.

---
> **Single source of truth**: output versioning, Manifest records, the artifact directory tree, path fallback, stale-state detection, and language rules are all defined centrally by this file. Each SKILL.md only needs to pointer-load this file (`../../shared-references/output-protocol.md`) instead of inlining duplicated three-line blocks.
