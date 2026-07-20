# Discipline Context Contract (SciForge-OSS — Discipline-Agnostic)

> **Status**: Contract for the OSS skill chain. **OSS is discipline-agnostic by design** — there are no 4 parallel pipelines, no per-discipline overlay, no `DISCIPLINE_CONTEXT` block. All 125 science problems are processed by the **same single pipeline** (`/125-problems-pipeline`) using the **same universal meta-skills**.

> **Key difference from main SciForge**: Main SciForge has 4 parallel pipelines (economics / cs-ml / physics / general) each with its own discipline overlay, reviewer persona, and framework (AIM / SOTA / PNV / none). OSS has **none of these** — the 4 meta-skills (sandbox / tooling / retrieval / plotting) + 4 support skills (theory-derivation / logic-verification / paper-writing / auto-review-loop) are universal and do NOT switch behavior by discipline. This file exists only to document that **no discipline dispatch is needed** and to point migrated skills (which may still reference `DISCIPLINE_CONTEXT` from their main-SciForge origin) at a canonical "no-op" stub.

---

## 1. Why OSS Has No DISCIPLINE_CONTEXT

The 125 science problems span 10+ domains (physics, CS, biology, math, earth science, medicine, engineering, social science, chemistry, general). Hard-coding per-discipline skill behavior (like main SciForge's 4 overlays × 16 overlay files = 64 files) would:

1. **Bloat the skill count** — defeating the OSS "4 meta-skills + universal support" design principle
2. **Force a clustering decision** — which 10 domains collapse into which N buckets? Any choice is arbitrary and loses information
3. **Not match the problem distribution** — many of the 125 problems are cross-disciplinary (e.g., "AI for drug discovery" spans CS + BIO + CHE); a single discipline label would misroute them

Instead, OSS uses **discipline-agnostic meta-skills** that handle any domain via runtime tooling (the agent writes domain-specific code on-the-fly in `/dynamic-sandbox`, not via pre-coded skill branches).

---

## 2. The "No-Op" DISCIPLINE_CONTEXT Stub

Migrated skills (copied from main SciForge and trimmed) may still reference `DISCIPLINE_CONTEXT.discipline` in their prose. For OSS, this field is **always**:

```yaml
DISCIPLINE_CONTEXT:
  discipline: general    # always — OSS has no discipline dispatch
  sub_discipline: null   # not used
  target_venue: null     # OSS outputs to unified elsarticle preprint, no venue targeting
```

**Fallback contract** (simplified from main SciForge's 4-level):

```
DISCIPLINE_CONTEXT  →  general   (single level — there is no other discipline)
```

There is **never** a silent fall-back to `cs-ml` (the main SciForge trap) because there is no `cs-ml` branch in OSS. Every skill behaves as `general` unconditionally.

---

## 3. Mapping Table (OSS — Single Row)

| Discipline | Framework | Reviewer Persona | Novelty Venues | Source Priorities | Problem Anchor Schema | Idea-Fit Overlay |
|-----------|-----------|------------------|----------------|-------------------|----------------------|------------------|
| `general` (always) | none (universal reasoning) | senior-reviewer-agnostic (inlined in `/auto-review-loop`) | mixed (top venues across all domains + arXiv) | default priority 1-6 (arXiv → S2 → CrossRef → PubMed → Web → OpenAlex) | default (problem / hypothesis / method / claim) | none (base 6-dimensional profiling) |

This is a **single-row collapse** of main SciForge's 4-row table. Migrated skills that consumed specific columns (e.g., `/research-lit` consumed Source Priorities) now consume only the `general` row's values.

---

## 4. What Main SciForge Discipline-Specific Features Are REMOVED in OSS

| Main SciForge feature | OSS status | Reason |
|----------------------|------------|--------|
| AIM Sketch (economics) | Removed | Economics-specific identification-strategy framework; OSS has no econ pipeline |
| SOTA-targeted sketch (cs-ml) | Removed | CS-specific benchmark binding; OSS has no benchmark binding phase |
| PNV Sketch (physics) | Removed as a **framework**; physics problems handled by `/theory-derivation` + `/dynamic-sandbox` like any other | The PNV (Physical-Numerical-Verification) reasoning style is still *useful* for physics problems, but it's applied by the agent's runtime judgment, not enforced by a skill overlay |
| economics 14-class leakage audit | Removed | DiD/IV/RDD-specific; OSS uses universal Type I-IV escape check |
| cs-ml SOTA Gate | Removed | Benchmark-binding gate; OSS has no experiment/benchmark phase |
| physics Type IV Empirical Escape | Preserved as a **universal** check (any problem where V≠P, i.e., the verification contradicts the premise) | Generalized beyond physics — any discipline can have a "verification escapes premise" failure |
| INV-C1/C2/C3 (cs-ml benchmark binding) | Removed | CS-specific |
| INV-P1~P5 (physics PNV hash) | Generalized to INV-G1 (PROBLEM_ANCHOR_FREEZE) only — the universal invariant | OSS keeps only the problem-anchor freeze, not domain-specific invariants |
| INV-E1~E5 (economics estimator verification) | Removed | Economics-specific |
| econometrics-tools Phase 9 Estimator Verification | Removed | Economics-specific |
| Per-discipline recency windows (6/12/18 months) | Collapsed to **12 months** universal | No discipline dispatch |
| Per-discipline compute framing (GPU/CPU/stat hours) | Collapsed to **"moderate compute, resource-agnostic"** | OSS sandbox handles any compute type at runtime |

---

## 5. Boundaries

**Never**:
- Reintroduce a `discipline` dispatch in an OSS skill. If a migrated skill's prose references "if discipline=economics", **delete that branch** and keep only the `general` path.
- Create per-discipline overlay files (`overlays/economics.md`, etc.). OSS has no overlay directory.
- Hardcode a domain-specific reviewer persona (e.g., "senior-ml-reviewer"). OSS uses only `senior-reviewer-agnostic`.

**Always**:
- Treat every 125-problem run as `discipline=general`.
- Let the agent's runtime reasoning (in `/theory-derivation`, `/dynamic-sandbox`) handle domain-specific methodology — NOT a skill overlay.

---

## 6. See Also

- [`venue-profiles.md`](venue-profiles.md) — OSS single-template (elsarticle) spec, no venue families
- [`idea-dag-schema.md`](idea-dag-schema.md) — DAG structure (discipline-agnostic, same as main SciForge)
- [`mcts-search-protocol.md`](mcts-search-protocol.md) — MCTS search (discipline-agnostic; `max_iterations` default 4, no per-discipline variant)
- [`multi-fidelity-evaluation.md`](multi-fidelity-evaluation.md) — 3-fidelity filter (OSS uses `general` row only: text reasoning → minimal test → full test)
- [`assurance-contract.md`](assurance-contract.md) — PASS/WARN/FAIL/ERROR schema (universal)
