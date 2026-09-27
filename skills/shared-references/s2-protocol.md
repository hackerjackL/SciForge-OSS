# S2 Protocol — ScientistTwo Parity Layer (v1.7.0)

> **Authority**: this document is the knowledge-layer mirror of the *code* in
> `kernel/sciforge/s2/`. Where prose and code disagree, the code wins — every
> rule below is enforced by a kernel module, a boundary gate, or the bench
> harness; none of it is advisory.
>
> **Source being replicated**: *ScientistTwo: Pioneering the Human Knowledge
> Frontier with Autonomous AI* (arXiv:2609.19644, Google Cloud AI Research +
> Waterloo, 2026-09-17). Their harness is closed; this is a faithful
> re-implementation of their load-bearing mechanisms as open code.

## 0. Why we replicate this

Their measured result (86/107 real conference problems, +25.2% over human
SOTA, 91.9% acceptance under ScholarPeer) rests on four mechanisms our v1.6
pipeline *described in prose but did not enforce*:

1. a **subset→full-set experiment ladder** with a three-state critic,
2. **exploration-guaranteed idea evolution** (no local-optimum collapse),
3. **monotone component ablation** before any claim,
4. **score-driven rebuttal + meta-review** against a *human-anchored* scale.

v1.7 turns all four into kernel code + boundary gates.

## 1. Mechanism ↔ implementation map

| ScientistTwo (paper) | Our implementation | Enforced at |
|---|---|---|
| Limitation Extractor ⇄ Verifier (≤16 rounds) | phase 1/1b/4broad + `gap_gate` (pre-existing) | phase 4b boundary |
| Seed Idea Generator + Novelty Checker | `s2/ideas.rank_seeds` + phase 2/3 (pre-existing) | phase 3 boundary |
| Idea Evolution + **exploration guarantee** | `s2/ideas.evolution_input` / `next_exploration_seed`; kernel attaches `exploration_seed` to every idea-regeneration loopback event | loopback L1/L3/L11/L13 event log + `KILL_DECISIONS.jsonl` |
| **Subset→Full-Set ladder + 3-state Critic** {Bad\|Good\|Engineer ≤2} | `s2/ladder.py` (`decide`, `validate`) → `.sciforge/audits/S2_LADDER.json` | **6c boundary gate `s2_ladder`** (`scripts/s2_ladder_gate.py`) |
| Component Ablation (5–6 plans) + AblCritic {Good\|Refine}, strict improvement | `s2/ablation.py` (`ablcritic`, `validate`) → `.sciforge/audits/ABLATION_LEDGER.json` | **phase-10 boundary gate `s2_ablation`** (`scripts/s2_ablation_gate.py`) |
| Manuscript + review score < 8 ⇒ Rebuttal (≤2 rounds, real supplementary experiments) | `s2/reviewloop.py` (`needs_rebuttal`, `seed_rebuttal_plan`, `meta_review`), threshold env `SCIFORGE_REVIEW_THRESHOLD` (default **8.0**) | kernel `_native_review` writes `REBUTTAL_PLAN.json` + `REVIEW_STATE.meta_review`; boundary floor stays `last_score ≥ 6` (L10 unchanged) |
| Meta-Review {Accept\|Refine} | `s2/reviewloop.meta_review` — ACCEPT iff calibrated score ≥ threshold AND no fatals; else REFINE/PENDING_REBUTTAL | `.sciforge/audits/REVIEW_PANEL.json` + `REVIEW_STATE.json` |
| Human-anchored score scale (accepted-paper mean 6.2) | `s2/calibration.py` OLS anchor fit → `.sciforge/audits/CALIBRATION.json`; `overall_calibrated` drives rebuttal/meta | `_native_review` |
| Completeness audit: reward-hacking + **method↔code line parity** + recompute | `s2/audit.py` → `.sciforge/audits/AUDIT_TRAIL.json` | **wrap-up gate** (phase 16) via `scripts/s2_audit.py` |
| Benchmark (107 conference problems, +25.2% metric) | `bench/s2demo/` — 4 CPU tasks, same ladder/critic code, relative-gain reporting, rubric + human anchor | `bench/s2demo/run.py` (exit 0 = all PROMOTED) |
| Cost transparency ($3765 / 2–3 days per paper) | `RUN_BUDGET.json` + per-arm timings in bench reports | budget breach gates (pre-existing) |

## 2. The ladder contract (phase 6b → 6c)

```
baseline reproduction (subset)  →  implement candidate  →  Critic:
    BAD       → discard (loopback per L5/L7; never promoted)
    ENGINEER  → tune again, ≤ 2 rounds total (s2/ladder.MAX_ENGINEER_ROUNDS)
    GOOD      → run FULL set
full-set re-verification: candidate must STRICTLY beat baseline (ties fail)
```

Machine rules (all in `s2/ladder.validate`, run by the 6c gate):

- experiment evidence exists but `S2_LADDER.json` absent ⇒ **FAIL** (ladder skipped);
- `critic.state ∈ {BAD, GOOD, ENGINEER}`; GOOD requires `fullset.verified=true`
  and strict improvement (direction-aware);
- `engineer_rounds ≤ 2` — tuning budget exhaustion is BLOCKED, never a silent promote;
- stated `relative_gain_pct` must match the recomputed value within 0.15 pp
  (arithmetic inconsistency = reward-hacking class);
- no experiments at all ⇒ **SKIP** (theory-only route is unaffected).

## 3. The ablation contract (phase 10)

- planner emits **5–6 plans** (`SCIFORGE_ABLATION_MIN/MAX` env overrides for
  micro-runs), each `{id, component, hypothesis, metric}`;
- every executed result carries `decision ∈ {GOOD, REFINE}` decided by
  `ablcritic(prev, new)`: **GOOD iff strictly better**, else REFINE (old state kept);
- `current_best` must equal the best GOOD outcome — a regressed or hand-edited
  ledger FAILs (monotonicity);
- experiment evidence exists but `ABLATION_LEDGER.json` absent ⇒ **FAIL**
  (claims without ablation); no experiments ⇒ SKIP.

## 4. The review contract (phase 14)

Two thresholds, deliberately distinct:

| Threshold | Value | Meaning |
|---|---|---|
| boundary floor | 6.0 | legacy L10 contract: `REVIEW_STATE.last_score ≥ 6` to cross phase 14 |
| **S2 rebuttal bar** | 8.0 (`SCIFORGE_REVIEW_THRESHOLD`) | below it a rebuttal is REQUIRED: `REBUTTAL_PLAN.json` written with one supplementary task per panel fatal/kill-argument |

- rebuttal rounds are capped at **2** (`MAX_REBUTTAL_ROUNDS`); supplementary
  tasks must be *executed* and backfilled — wording-only responses are
  `round_invalid` (anti-shrinkage, pre-existing);
- `meta_review`: **ACCEPT** iff calibrated score ≥ threshold and zero fatals;
  `PENDING_REBUTTAL` while rounds remain; **REFINE** otherwise (= method
  changes + ablations rerun + re-enter, exactly their §3.6 loop).

## 5. Anchor calibration

Before a raw panel score means anything, fit the scale on known-quality papers:

```jsonc
// .sciforge/audits/CALIBRATION.json
{ "anchors": [{"id": "known-paper-1", "panel_score": 5.1, "reference_score": 6.2}, ...],
  "method": "ordinary_least_squares", "a": ..., "b": ..., "usable": true }
```

`calibrated = clamp(a + b·raw, 0, 10)`; degenerate fits (b ≤ 0) fall back to
identity with `usable:false` — an unusable calibration never silently rescales.

## 6. The completeness audit (phase 16)

`s2/audit.py` (wired as wrap-up gate `s2_audit`):

1. **gain arithmetic** — every stated gain re-derived from its components;
2. **split discipline** — `EVALUATION_PROTOCOL` must declare held-out/split/seed
   once experiments exist (silent resubstitution is the cheapest reward hack);
3. **method↔code parity** — machine tokens in the method section (backticked /
   snake_case / camelCase) must land in `src/` + `experiments/` code at ≥ 80%;
   unmatched tokens are listed as the classic "method describes machinery that
   does not exist" surface; reverse direction (code functions never mentioned)
   is reported for information.

SKIP is only legitimate when no experiment claims exist.

## 7. The demo bench (`bench/s2demo/`)

Four numpy-only synthetic tasks in the ARC-Bench / ScientistTwo mold —
structured briefing + rubric + human anchor + baseline + ladder. The harness
imports the **production** `s2/ladder.py`, so the bench and the 6c gate are
one contract with two consumers. See `bench/s2demo/README.md`.

## 8. Hard rules (recitation candidates)

1. No promotion without full-set evidence — subset wins are hypotheses, not results.
2. Engineer rounds ≤ 2; exhaustion is BLOCKED, not a quiet promote.
3. Ablation is mandatory before claims: 5–6 plans, strict AblCritic, monotone ledger.
4. Score < 8 ⇒ real supplementary experiments, ≤ 2 rebuttal rounds; no wording-only rounds.
5. Score scale is anchored: calibrate on known-quality papers before judging.
6. Stated gains must equal recomputed gains; method tokens must exist in code.
7. Every idea-regeneration loopback carries an unexplored seed id.
