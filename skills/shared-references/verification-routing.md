# Verification Routing Contract (SciForge-OSS — Experiment-First by Default)

> **Status (v1.0)**: The routing contract that decides "how this paper gets verified". Field feedback (v5.0): the old pipeline defaulted every paper to symbolic/theoretical derivation first, with experiments serving only as supplementary verification — for problems that have data and are computable, this is **putting the cart before the horse**, and symbolic verification itself was judged "meaningless". This contract moves verification routing **upfront to the Phase 6 entry**: decide the route first, then choose the verification chain.

## 1. Routing rules (entry-point decision, decided once and final)

At the Phase 6 (theory-derivation / experiment-execution) entry, read `evidence_type` from `.sciforge/refine-logs/domain-signature.json` plus the problem's own computability signals, route per the table below, and write to `.sciforge/verdicts/VERIFICATION_ROUTING.json` (canonical location since v5.2 — `.sciforge/verdicts/` since v6.0; pre-v6.0 fallback `verdicts/`):

| Route | Trigger condition | Verification chain |
|------|---------|--------|
| **experiment-first (default)** | `evidence_type` ∈ {correlational, causal_inference, simulational, empirical, experimental}, or the problem involves datasets/training/simulation/empirical work | `/experiment-execution` as primary verification: toy quick verification (~20 rounds scale) → main experiment → mandatory experiment matrix (method-registry §3). `/theory-derivation` **is demoted to optional auxiliary** (only followed when the method has derivable structure and the derivation can guide implementation; lack of derivation does not block) |
| **theory-only (exception)** | `evidence_type = derivational` and the problem has **no data and no executable computation** (pure mathematical proofs, some humanities/philosophical argumentation, conceptual theory construction) | `/theory-derivation` (engine=sympy or manual) as primary verification + `/logic-verification`; no experiment is run, but toy-level numerical sanity checks (when feasible) are still encouraged |
| **hybrid (explicit declaration)** | The paper's contribution depends on both theoretical results and experimental verification (e.g., "theorem + algorithm" style work) | Theory derivation and experiments advance in parallel; both are primary verifications; `verification_type = theory+experiment` |

**Decision discipline**:
1. **experiment-first by default** — when in doubt, route by experiment, because the vast majority of papers "have something that can be run"
2. theory-only must satisfy the **double condition** (derivational ∧ no executable computation); satisfying only one still routes to experiment-first
3. The routing result is written to `.sciforge/verdicts/VERIFICATION_ROUTING.json` (core three fields: route/evidence_type/reason; v6.0 adds the `na_verdicts` declaration — §5); downstream skills read it only, never modify it
4. Data-less humanities/social-science problems → theory-only is legitimate ("when there is nothing, there is simply no way"); but as long as collectable data or simulatable objects exist, experiment-first takes priority

## 2. Verification forms under experiment-first

1. **Toy quick verification** (idea level): small scale (~20 rounds of training / 1-10% of data / synthetic data with known effects) verifies "is this idea heading in the right direction" — this is a **life-or-death verdict for the idea**, not a paper experiment
2. **Main experiment** (paper level): executed per the mandatory experiment matrix in method-registry §3 (main experiment + baseline comparison + ablation + hyperparameters + sensitivity)
3. **Theory auxiliary** (optional): when derivable structure exists, supplement with theoretical analysis, placed in a Theory subsection of the main text or in an appendix; full-step SymPy verification is **not required** — hand derivation + numerical cross-checking suffices

## 3. Relationships with each skill

- `/auto-pipeline` invokes this contract at the Phase 6 entry to complete routing, then dispatches
- `/theory-derivation`: accepts the `route` field — when invoked under experiment-first it runs in auxiliary mode (non-blocking, does not enforce full-step SymPy)
- `/experiment-execution`: the primary-verification executor under experiment-first / hybrid
- `/method-registry`: checks the completeness of the mandatory experiment matrix before hash-locking (under experiment-first / hybrid routes)
- `/paper-writing` (via [`paper-modes.md`](paper-modes.md)): reads `VERIFICATION_ROUTING.json` to choose the section layout (experiment mode preferred) — `paper-modes` is a shared reference document, not a standalone OSS skill

## 5. Routing-aware verdict expectation: `na_verdicts` (v6.0)

A run's route decides which verdicts it will **legitimately never produce**. The orchestrator declares this at Phase 6 entry by writing `na_verdicts` (a list of registered verdict filenames from the `.sciforge/verdicts/` table in `output-protocol.md`) into `VERIFICATION_ROUTING.json`. `scripts/validate_verdicts.py` then reports absent declared files as **N/A** instead of pending, and the wrap-up cleanliness audit treats the corresponding absent directories as legitimate (lazy materialization — no empty placeholders for humanities/theory runs).

**Default declaration sets** (copied verbatim into `na_verdicts` at Phase 6 entry):

| Route | Default `na_verdicts` | Rationale |
|-------|----------------------|-----------|
| experiment-first (default) | `[]` (empty) | every registered verdict is expected; theory-derivation still emits PROOF_AUDIT (NOT_APPLICABLE when no derivable structure) |
| hybrid | `[]` (empty) | both verification chains run; all verdicts expected |
| theory-only | `["EXPERIMENT_MATRIX.json", "EVALUATION_PROTOCOL.json", "BUDGET_FLOOR.json", "REGISTRY_HASH.txt"]` | no experiment phases (6b/6c skipped), no mandatory matrix → no hash-lock; the exploration budget floor is an experiment gate |

**Extension rule**: `na_verdicts` only grows, never shrinks — any later declared skip appends to it (the orchestrator rewrites the routing file's `na_verdicts` field, leaving route/evidence_type/reason untouched):

- Phase 11 figure-skip ("No figures needed") → append `FIGURE_AUDITS.json`
- KILL→restart with a changed route is a NEW routing decision (new phase-boundary write), not a silent edit

A file declared N/A that IS produced anyway is a routing/production inconsistency (validator WARN). This mechanism is what keeps a humanities run's verdict summary honest ("14 pass, 4 na" instead of "14 pass, 4 pending") and its workspace free of empty experiment/figure directories.

## 6. See Also

- [`methodology-and-context-contract.md`](methodology-and-context-contract.md) — sufficiency stopping rule
- [`../support/experiment-execution/SKILL.md`](../support/experiment-execution/SKILL.md) — experiment execution (toy→full + background scheduling)
- [`../support/theory-derivation/SKILL.md`](../support/theory-derivation/SKILL.md) — theory derivation (auxiliary mode)
- [`../support/method-registry/SKILL.md`](../support/method-registry/SKILL.md) — mandatory experiment matrix
