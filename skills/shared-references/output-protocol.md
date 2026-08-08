# Output Protocol (SciForge-OSS — Merged)

> **Core**: every output is written in two versions — a timestamped version (history) + a fixed-name version (latest).

## Versioned Writes

1. Write the timestamped file: `{FILENAME}_{YYYYMMDD_HHmmss}.md`
2. Copy to the fixed-name file: `{FILENAME}.md` (overwritten with the latest version)
3. Downstream skills always read the fixed-name file

**Timestamped**: IDEA_REPORT.md, FINAL_PROPOSAL.md, AUTO_REVIEW.md, paper/main.tex, status files
**Not timestamped**: append-only files (findings.md), per-round numbered files (round_N_*.md), MANIFEST.md

## Manifest Records

After every write, append one row to `MANIFEST.md`:

```markdown
| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
| 2026-07-20 14:30 | /idea-discovery | refine-logs/IDEA_CANDIDATES.md | idea-discovery | 12 ideas generated |
```

## Artifact Directory Tree (v5.2 — unified verdicts in verdicts/ + centralized logs in logs/ + single home in code/)

```
{problem_id}/
├── refine-logs/        ← idea-discovery + novelty-check artifacts (decision-style documents)
├── literature/         ← universal-retrieval artifacts
├── methods/            ← method-registry artifacts (METHOD_REGISTRY.md/METHOD_BINDING.md)
├── derivations/        ← theory-derivation artifacts (.md documents only; scripts go to code/)
├── code/               ← the [single home] for algorithms and source code (v5.0)
│   ├── derivations/    ←   derivation/symbolic-verification scripts (formerly derivations/*.py, moved here)
│   ├── experiments/    ←   experiment scripts (toy/full/ablation/hyperparameter, incl. group_<name>/)
│   ├── figures/        ←   rendering scripts (render.py / spec.d2 / *.composite.json)
│   └── utils/          ←   shared utility functions
├── verdicts/           ← the [unified directory] for all pipeline verdict artifacts (new in v5.2)
│   ├── VERIFICATION_ROUTING.json   ← verification routing decision (Phase 6 entry point)
│   ├── PROBLEM_HASH.txt            ← INV-G1 problem-content hash (invariant-check)
│   ├── REGISTRY_HASH.txt           ← method hash-lock (method-registry)
│   ├── EXPERIMENT_MATRIX.json      ← mandatory experiment matrix (method-registry §3.5)
│   ├── BUDGET_FLOOR.json           ← exploration budget-floor completion criteria (experiment-execution)
│   ├── PROOF_AUDIT.json            ← step-by-step derivation verification (theory-derivation)
│   ├── LOGIC_VERIFICATION.json     ← 6-dimension logic audit (logic-verification)
│   ├── LEAKAGE_AUDIT.json          ← Type I/IV audit (leakage-audit)
│   ├── BLINDSPOT_CHECK.json        ← domain blind-spot audit (auto-review-loop B.2)
│   ├── REVIEW_STATE.json           ← review-round state + response_class (auto-review-loop)
│   ├── REVIEW_LEDGER.json          ← review-comment ledger (auto-review-loop)
│   ├── KILL_ARGUMENT.json          ← kill argument (kill-argument)
│   ├── PAPER_CLAIM_AUDIT.json      ← paper-claim consistency (paper-writing self-check)
│   ├── LEAKAGE_SCRUB.json          ← LaTeX leakage scrub gate (paper-writing §3.5)
│   ├── CITATION_AUDIT.json         ← 3-layer citation verification (citation-audit)
│   ├── INVARIANT_CHECK.json        ← invariant-check result (invariant-check; narrative report lives in audit_report/)
│   ├── PUBLISHABILITY_SCORE.json   ← final publishability score (publishability-score)
│   ├── RUN_BUDGET.json             ← global run-budget ledger (v5.3: wall_clock/api_cost/pivot_count/ba_used;
│   │                                  the orchestrator books entries and checks the caps at every phase boundary;
│   │                                  bookkeeping from the old BA_BUDGET.json is merged into this file, BA_BUDGET.json remains as a read-only fallback)
│   ├── FIGURE_AUDITS.json          ← all-figure audit summary mirror (unified-plotting; per-figure detail still ships with each figure_audit.json)
│   └── PIPELINE_VERDICT_SUMMARY.md ← pipeline verdict overview (rewritten by the orchestrator at every phase boundary; derived document, the only .md allowed inside verdicts/)
├── logs/               ← the [central directory] for all pipeline logs (v5.0)
│   ├── pipeline.log    ←   auto-pipeline status stream (the single authoritative status record)
│   ├── phase_<n>.log   ←   per-phase run logs (written by each skill, no longer scattered)
│   └── experiments/    ←   experiment STATUS.json summary mirror
├── audit_report/       ← [narrative reports] from logic-verification + leakage-audit (.md; machine-readable verdicts go to verdicts/)
├── figures/            ← unified-plotting artifacts (PDF+SVG deliverables + figure_audit.json per figure; summary verdict mirror verdicts/FIGURE_AUDITS.json)
├── experiments/        ← experiment-execution artifacts (RESULT.json/data; scripts go to code/experiments/)
├── paper/              ← paper-writing + paper-compile artifacts (compiled output and .tex; verdicts go to verdicts/)
├── review-stage/       ← [narrative artifacts] from auto-review-loop (AUTO_REVIEW.md; machine-readable verdicts go to verdicts/)
├── citation_audit/     ← [narrative report] from citation-audit (machine-readable verdicts go to verdicts/)
└── output/             ← final archive (submission bundle)
```

**Unified Verdict Principles (v5.2 — cures "scattered verdict files that are hard to trace")**:
1. **All machine-readable verdicts go to `verdicts/`**: every `*.json` verdict / hash / audit conclusion is written to `verdicts/` (filenames are fixed as in the table above; no stage prefixes, no nested subdirectories — one flat directory, and a single scan reveals the verdict state of the entire pipeline)
2. **Narrative reports stay in their original stage directories**: long human-readable reports (AUTO_REVIEW.md, audit narratives, citation reports) do not move; only machine-readable verdicts migrate
3. **Single status file**: `PIPELINE_STATUS.json` exists only in `logs/` (event stream); no stage may create its own PIPELINE_STATUS copy; at summarization time the orchestrator reads the entire `verdicts/` directory to generate the pipeline verdict overview (`verdicts/PIPELINE_VERDICT_SUMMARY.md`, rewritten at every phase boundary)
4. Migration compatibility: reads check `verdicts/` first and fall back to the old stage path if not found; writes always go to `verdicts/`

## Verdict Schema Enforcement (v5.3 — cures "misspelled/omitted fields going unnoticed")

1. **Every verdict JSON must pass schema validation**: the field contract is defined by `skills/shared-references/schemas/<NAME>.schema.json` (draft 2020-12); writers must not misspell or omit required fields; hash files (PROBLEM_HASH.txt / REGISTRY_HASH.txt) must be a single-line lowercase sha256 (64 hex characters)
2. **The orchestrator runs it at every phase boundary and at wrap-up**: `python3 scripts/validate_verdicts.py {problem_id}/verdicts/` — registered files are schema-validated plus cross-field invariants (the 6-state verdict vocabulary of the audit family, audited_input_hashes of audit JSONs); unregistered *.json → WARN; a missing registered file is only recorded as pending, not an error
3. **Handling violations**: default mode → WARN (record and continue); `--strict` mode → BLOCKED (treated as FAIL, blocks the current phase boundary)
4. A new verdict must first have its schema added in this directory and be registered in the validator (steps in `skills/shared-references/schemas/README.md`)

**Single-Home Principle (v5.0 — cures "directory chaos + code duplication")**:
1. Every artifact class has a **unique canonical path** (table above); artifacts of the same class written elsewhere → audit WARN, and the writer is responsible for migrating them
2. **Code exists in exactly one place, `code/`**: experiment/derivation/rendering scripts all go into the corresponding subdirectory of `code/`; `derivations/`, `figures/`, `experiments/` hold **only artifacts and documents** (.md/.json/PDF/SVG/data), **never scripts** — this eliminates the "code gets copied into paper/ once more during paper writing" duplication (no code copies inside paper/; code references go only through the Reproducibility statement pointing at `code/`)
3. **Logs are centralized only in `logs/`**: stages no longer each create their own log files scattered in the root directory; `pipeline.log` is the single authoritative status stream (containing the PIPELINE_STATUS events), and each skill's process logs go to `logs/phase_<n>.log`
4. Migration compatibility: reads check the new canonical path first and fall back to the old path if not found (backward compatible with old run directories); writes always use the new path

## Path Fallback Rules

On reads, the stage-scoped path is tried first; if not found, fall back to the root-level path (backward compatibility). Writes always use the stage-scoped path.

## Workspace Hygiene Contract (v5.2 — cures "workspace chaos/duplication/junk files")

**Naming conventions (enforced across the whole pipeline)**:
1. **UPPERCASE + underscores** (`CLAIMS_FROM_RESULTS.md`, `REGISTRY_HASH.txt`) for **contract artifacts** (read by downstream skills under a fixed name); **lowercase + hyphens** (`derivation_output.md`-style narrative artifacts) for intra-stage artifacts — "contract files" and "process files" become distinguishable at a glance
2. **Version numbers go into content, never into filenames**: `report_v2.md`, `final_FINAL.tex`, `draft3.py` are forbidden — iterate via versioned writes (see above in this section) and `revision_log.md`; filenames stay stable (downstream consumers reference them by fixed name; renaming breaks the link)
3. **Experiment directories**: `experiments/full/group_<name>/` (name = the group name from the experiment matrix); **forbidden**: semantic-free names like `exp1/`, `test2/`, `new_folder/`
4. **One folder per figure**: `figures/<fig_id>/` (fig_id identical to the LaTeX label) — figure artifacts are never mixed with other artifacts

**Temporary-file ban (hard rules)**:
1. The workspace root directory **allows only** the 14 directories defined in the directory tree + the `refine-logs/` entry file; any stray `.py`/`.tmp`/`.bak`/`.swp`/`nohup.out`/`core.*`/`*.orig`/`__pycache__/` → deleted or migrated by the wrap-up cleanup protocol
2. **Temporary files go only into `/tmp` or `logs/tmp/`**: debug scripts, rendering intermediates, and download caches are all written to `/tmp` (outside the pipeline) or `logs/tmp/` (whole directory deleted at wrap-up); **never** into the workspace root or stage directories
3. Experiment datasets (downloaded raw data) go into `experiments/data/<dataset_id>/`, not into `code/`, not into the workspace root
4. `nohup.out` / background-process output must always be redirected to `logs/experiments/<experiment_id>.log` (the experiment-execution dispatch command template forces a tee to that path)

**Orphan-artifact governance**:
1. **Orphan = an artifact with no upstream reference**: every stage artifact must be referenced by at least one downstream contract (the MANIFEST's `consumer` field); a MANIFEST entry written with an empty consumer → WARN `orphan_artifact`
2. **Artifacts of rejected branches**: after a KILL/PIVOT, the artifacts of the rejected idea are **not deleted** (audit tracing needs them) but moved en masse into the `refine-logs/abandoned/<idea_id>/` archive — the active workspace keeps only the current idea's artifacts; history stays inspectable but out of the way
3. **Zero tolerance for duplicate artifacts**: the same content present at two paths (e.g., code in both `code/` and `paper/`) → audit FAIL `duplicate_artifact`; symlinks are the only legitimate "same artifact visible in multiple places" mechanism

**Wrap-up cleanup protocol (executed at every phase boundary + at the pipeline end state)**:
1. Scan the workspace: delete `logs/tmp/`, empty directories, `*.pyc`/`__pycache__/`, 0-byte files (keep anything with a contract reference)
2. Reconcile with the MANIFEST: every active artifact is at its canonical path and has a consumer; violators are migrated/warned (files with content are never silently deleted)
3. Write one cleanup event to `logs/pipeline.log` (what was deleted, what was migrated) — the cleanup action itself is auditable
4. Pipeline end state (Phase 17 archive): the `output/` submission bundle contains only deliverables (paper PDF + LaTeX sources + figures PDF/SVG + citation bib), **not** intermediate artifacts — verify the checklist file by file before packing

## Stale-State Detection

Default staleness threshold for status files (REVIEW_STATE.json etc.): 24 hours. When stale, warn the user, who may continue or start over.

## Output Language

Respect the project's language setting (`language=chinese` outputs Chinese, English by default; figures and code comments use English identifiers). The language of the paper body and title follows the language declaration made at pipeline start; languages must not be mixed inside a single deliverable.

---
> **Single source of truth**: output versioning, Manifest records, the artifact directory tree, path fallback, stale-state detection, and language rules are all defined centrally by this file. Each SKILL.md only needs to pointer-load this file (`../../shared-references/output-protocol.md`) instead of inlining duplicated three-line blocks.
