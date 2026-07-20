# Skill Config — Centralized Public Knobs

SciForge skills accept a shared set of **public knobs** that control runtime behavior: depth, audit strictness, iteration counts, rendering, human-in-the-loop gates. Historically each skill re-declared these knobs in its own Configuration section, with subtle drift across skills (`MAX_ROUNDS=4` here, `MAX_ROUNDS=6` there; `EFFORT=balanced` mapping to different defaults). This file is the **single source of truth** for knob names, allowed values, defaults, and precedence.

> **Rule of thumb**: if a knob appears in two or more skills' Configuration sections, it MUST be defined here. Skills reference this file via `[Skill Config](../shared-references/skill-config.md)` and only declare skill-specific overrides locally.

## Why this file exists

Three recurring drift bugs:

1. **`MAX_ROUNDS` semantic drift.** `auto-review-loop` defaulted to 4 rounds; `economics-empirical-pipeline` raised it to 6 for econ; `auto-paper-improvement-loop` defaulted to 2. Users passed `— max-rounds: 3` expecting one meaning and got three.
2. **`EFFORT` mapping drift.** `paper-writing` mapped `balanced → draft` assurance; `auto-review-loop` mapped `balanced → 3-4 rounds`; `econometrics-tools` had no effort axis at all. Same word, three behaviors.
3. **`ASSURANCE` vs `EFFORT` conflation.** Users reported `effort: beast` runs that silently skipped mandatory audits because the two axes were entangled. The fix split them — but only `paper-writing` honored the split.

Centralizing eliminates drift: each knob is defined once here, referenced by every skill, and overrides are explicit per skill.

## Registered Public Knobs

### `EFFORT` — depth/cost axis

| Value | Tokens | Wall-clock | Implied `ASSURANCE` | Use case |
|---|---|---|---|---|
| `lite` | ~0.4x | ~0.5x | `draft` | Quick exploration, budget users |
| `balanced` (DEFAULT) | 1x | 1x | `draft` | Normal research workflow |
| `max` | ~2.5x | ~2x | `submission` | Serious submission prep |
| `beast` | ~5-8x | ~3-4x | `submission` | Top-venue final sprint |

**Hard invariants** (NEVER changed by effort): reviewer reasoning effort (always maximum), DBLP/CrossRef citation verification (always on), reviewer independence (always on), experiment integrity (always on), mandatory audit emission (always — see `assurance-contract.md`).

**Per-skill numeric knobs derived from EFFORT**: see `effort-contract.md` Section "Per-Skill Profiles". Skills may override individual dimensions (e.g., `effort: beast` with `review_rounds: 3`) — see Precedence below.

### `ASSURANCE` — audit strictness axis (independent of EFFORT)

| Value | Behavior | Default mapping |
|---|---|---|
| `draft` (DEFAULT) | Audits run only if content detector matches; silent-skip allowed; missing artifacts non-blocking | `lite` / `balanced` |
| `submission` | All mandatory audits must emit 6-state verdict; silent-skip forbidden; Phase 6 verifier blocks Final Report on FAIL/BLOCKED/ERROR/STALE | `max` / `beast` |

**Override**: user may pass `— effort: balanced, assurance: submission` to get normal depth with strict audits, or `— effort: beast, assurance: draft` for max depth with no audit gate (legal but discouraged for real submissions).

**6-state verdict vocabulary**: `PASS` / `WARN` / `FAIL` / `NOT_APPLICABLE` / `BLOCKED` / `ERROR`. See `assurance-contract.md` for semantics and state machine.

### `MAX_ROUNDS` — iteration cap per skill

Each skill declares its own default in its Configuration section, but the **canonical values** are:

| Skill | lite | balanced | max | beast | Notes |
|---|---|---|---|---|---|
| `/auto-review-loop` | 2 | 4 | 6 | 8+ (until converged) | Positive threshold: score ≥6/10 or verdict contains accept/sufficient/ready |
| `/auto-review-loop` (econ variant, `REVIEWER_PROMPT_VARIANT=senior-econ-editor`) | 3 | 5 | 6 | 8+ | Economics review is longer; +1 round vs default |
| `/auto-paper-improvement-loop` | 1 | 2 | 3 | 5 | |
| `/research-refine` | 3 | 5 | 7 | 10+ | |
| `/research-refine-pipeline` | 3 | 5 | 7 | 10+ | Idea-confirmed gate at Phase 0 (Problem Anchor freeze) |

**Override**: user may pass `— max-rounds: N` to cap any of these. Skills must respect the cap.

### `REVIEWER_PROMPT_VARIANT` — discipline-specific reviewer persona

| Value | When to use | Defined in |
|---|---|---|
| `default-ml` (DEFAULT) | ML/AI papers, NeurIPS/ICML/ICLR/CVPR/ACL | `/auto-review-loop/SKILL.md` Prompt Template |
| `senior-econ-editor` | Economics papers, AER/QJE/JPE/Econometrica/RES/JFE/JF | `/economics-empirical-pipeline/SKILL.md` Phase 7 |
| `senior-physics-editor` | Physics papers, Nature Photonics/PRL/Optica | `/physics-pipeline/SKILL.md` (Active — used by physics-pipeline Phase 7, PNV chain + Nature Physics/PRL/Optica review standards) |
| `general-cross-discipline` (reserved) | Interdisciplinary / Pipeline D | `/idea-discovery/SKILL.md` (default fallback) |

**`/auto-review-loop` MUST honor this knob.** When the caller passes `— reviewer-prompt-variant: senior-econ-editor`, the loop replaces its default ML reviewer prompt with the econ variant verbatim. The variant defines: editorial framework (AIM chain / 14-class rejection ledger for econ; PNV chain for physics), files the reviewer must read first, scoring rubric, brutally-honest enforcement areas.

### `HUMAN_CHECKPOINT` — pause-at-phase-boundary gate

| Value | Behavior |
|---|---|
| `false` (DEFAULT) | Fully autonomous; pause only on hard gate failure |
| `true` | Pause at every phase boundary for user approval |
| `phase-list` (e.g., `2,4,8`) | Pause only at listed phases |

**Applies to**: pipeline orchestrators (`/economics-empirical-pipeline`, `/research-pipeline`, `/physics-pipeline`, `/idea-discovery`, `/paper-writing`). Sub-skills inherit the value from the orchestrator via `AGENT_DOC.md`.

### `AUTO_PROCEED` — auto-continue between phases (within a skill)

| Value | Behavior |
|---|---|
| `true` (DEFAULT) | Auto-continue between phases of the same skill |
| `false` | Pause after each phase, wait for user approval |

**Difference from `HUMAN_CHECKPOINT`**: `HUMAN_CHECKPOINT` is cross-skill (pipeline-level); `AUTO_PROCEED` is intra-skill (phase-level within one skill). Both can be true independently.

### `RENDER_HTML` — auto-render markdown reports to single-file HTML

| Value | Behavior |
|---|---|
| `true` (DEFAULT) | After writing the audit/report markdown, invoke `/render-html` for a readable HTML view |
| `false` | Skip HTML rendering; markdown + JSON are canonical |

**Applies to**: all audit skills (`/paper-claim-audit`, `/citation-audit`, `/proof-checker`, `/kill-argument`, `/leakage-audit`), `/result-to-claim`, `/auto-review-loop`. Read from `AGENT_DOC.md` if set; otherwise default `true`.

**Non-blocking**: HTML render failure (helper missing, reviewer unavailable) MUST NOT block the parent skill. The JSON + MD verdict files are canonical; HTML is convenience.

### `DATA_SOURCE` — real vs synthetic data flag (economics)

| Value | Behavior |
|---|---|
| `real` (DEFAULT) | Downstream may use "empirical evidence", "policy implications", "welfare analysis" language |
| `synthetic` | Downstream MUST use "simulation suggests", "numerical analysis indicates" language; MUST NOT claim "empirical evidence" or "policy implications" |

**Emitted by**: `/data-acquisition` at source (mandatory — provenance signal at acquisition time); also re-emitted by `/experiment-bridge` Phase 1.5.

**Enforced by**: `/experiment-bridge` Phase 1.5 (blocks overclaiming in experiment plan), `/result-to-claim` (blocks overclaiming in claim verdict), `/paper-write` Step 0.5 (blocks overclaiming in LaTeX prose), `/paper-figure` Step 5.5 (annotates figures with "(Synthetic Data)" if synthetic).

### `TARGET_VENUE` — journal/conference target

| Family | Examples | Page limit (main body) |
|---|---|---|
| ML conferences | ICLR, NeurIPS, ICML, CVPR, ACL, AAAI | 8-9 pages (refs/appx NOT counted) |
| IEEE journals | IEEE Transactions, Letters | 12-14 pages ALL (refs counted) |
| IEEE conferences | ICC, GLOBECOM, INFOCOM, ICASSP | 5-8 pages ALL (refs counted) |
| Elsevier | AI, Pattern Recognition, KBS | variable |
| Finance Top-3 | JFE, JF, RFS | 12-14 pages (refs NOT counted) |
| Economics Top-5 | AER, QJE, JPE, Econometrica, RES | 30-40 pages (refs NOT counted) |
| NBER Working Papers | NBER WP | 30-40 pages (refs NOT counted) |

**Affects**: citation format (`elsarticle-num.bst` numeric for CS/ML/physics/engineering; `elsarticle-harv.bst` author-year for economics/finance), section structure (economics = institutional background + theoretical framework + robustness + welfare), mandatory sections (economics = Mechanism + Welfare). All venues use `elsarticle` as the unified document class.

### `SUB_DISCIPLINE` (economics only) — sub-discipline within economics

| Value | Default venue | Methodology class |
|---|---|---|
| `applied-micro` (DEFAULT) | AER/QJE/JPE | Applied Micro (Empirical) |
| `macro` | JME / AEJ Macro | Macro / Structural |
| `finance` | JFE / JF / RFS | Empirical Finance |
| `econometric-theory` | Econometrica | Econometric Theory |
| `experimental` | AER / AEJ Applied | Experimental Economics |
| `structural-io` | AER / JPE / RAND | Structural IO |

### `MAX_RETRIES` — phase-level retry cap for stagnation detection

The `quality-gate` Phase 1 (Stagnation Detection) reads `RETRY_COUNTERS` from `AGENT_DOC.md` and compares per-phase retry counts against `MAX_RETRIES`. When a phase exceeds `MAX_RETRIES`, the quality gate triggers stagnation and recommends abandon + human review.

| Phase | Default MAX_RETRIES | Notes |
|-------|---------------------|-------|
| `method_registry` | 3 | Method binding/registry lock attempts |
| `leakage_audit` | 3 | Leakage audit retry limit |
| `experiment_bridge` | 5 | Experiment execution retry (higher tolerance for infra failures) |
| `result_to_claim` | 3 | Result-to-claim classification retry |
| `idea_refinement` | 3 | Idea refinement/development loop retry |

**Override**: Set `MAX_RETRIES` in `AGENT_DOC.md` under a `RETRY_COUNTERS` block to customize per-phase limits. The `quality-gate` reads `AGENT_DOC.md` → `RETRY_COUNTERS` → `MAX_RETRIES` with the above defaults as fallback.

## Precedence

Knob precedence, from highest to lowest:

1. **Explicit per-skill override** (e.g., `— max-rounds: 3` passed to `/auto-review-loop`)
2. **Explicit dimension override** (e.g., `— review-rounds: 3`)
3. **Overall effort level** (e.g., `— effort: beast`)
4. **Skill default** (declared in skill's Configuration section, must match this file)
5. **Global default** (declared here)

For the `ASSURANCE` axis, precedence is independent:

1. **Explicit `assurance` directive**
2. **Effort-implied default** (lite/balanced → `draft`; max/beast → `submission`)
3. **Skill default** (`draft`)

## How to read these knobs in a skill

Each skill's Configuration section declares only **skill-specific overrides** and references this file for the rest:

```markdown
## Configuration

- **EFFORT** = `balanced` — see [Skill Config](../shared-references/skill-config.md) for the 4 levels and derived knobs
- **MAX_ROUNDS** = 4 (default); 6 when `REVIEWER_PROMPT_VARIANT=senior-econ-editor`; see Skill Config for full table
- **Skill-specific knob** — [description unique to this skill]
```

Skills must NOT re-declare the canonical values from this file; they reference it. Skills must NOT invent new knob names that overlap semantically with the ones here (e.g., don't invent `ITERATIONS` when `MAX_ROUNDS` exists).

## Transparency

Every skill should print its active knob configuration at the start of its work, including: active EFFORT, derived MAX_ROUNDS / paper count / idea count, active ASSURANCE, active REVIEWER_PROMPT_VARIANT, and a reminder that reviewer reasoning effort stays at maximum regardless:

```
effort: max — papers=25, ideas=16, rounds=6 | reviewer reasoning: maximum (always)
assurance: submission | reviewer-prompt-variant: senior-econ-editor | render-html: true
```

## See Also

- [`effort-contract.md`](effort-contract.md) — full per-skill EFFORT profile tables
- [`assurance-contract.md`](assurance-contract.md) — ASSURANCE axis full contract
- [`artifact-registry.md`](artifact-registry.md) — load-bearing artifacts SSoT
- [`integration-contract.md`](integration-contract.md) — 5-component cross-skill integration contract
