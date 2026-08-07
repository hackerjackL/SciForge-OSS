# SciForge-OSS Agent Guide

> **Status**: The single entry orchestrator for OSS is `/auto-pipeline`. It executes a complete 21-phase DAG research loop on **one** problem supplied by the human user's prompt. **OSS does NOT auto-iterate over all problems** — each invocation = one Q-id = one complete pipeline run end-to-end.
>
> **全领域支持**: SciForge-OSS 不限定任何学科领域。物理学、数学、计算机科学、医学、经济学、教育学、材料科学、地球科学、大气科学、天文学、化学、工程、传感器、光电——任何科学领域均可使用。

---

## Quick Start

### Solve one problem

```
"帮我完整研究 Q015：宇宙的起源与演化"
"Solve Q042"
"run the full pipeline on Q001"
"研究一个经济学模型：完全竞争市场下的福利最大化"
"Analyze this material science problem: high-temperature superconductor mechanism"
```

The human user supplies the specific problem. OSS does **not** auto-search any problem index. Each invocation processes exactly one problem.

### Available skills

| Type | Skill | Role |
|------|-------|------|
| **Orchestrator** | `/auto-pipeline` | Single entry — 21-phase DAG research loop on one problem (v2.9 + Phase 5b EG) |
| **Meta-skill** | `/idea-discovery` | Generate + pre-screen 8-12 idea candidates via MCTS (4 rounds) |
| **Meta-skill** | `/universal-retrieval` | Literature survey + 3-layer anti-hallucination citation verification |
| **Meta-skill** | `/unified-plotting` | Render publication-quality figures (morandi palette + Layer 2 data colormaps) |
| **Meta-skill** | `/dynamic-sandbox` | Lightweight numerical sanity checks (Python/numpy, no GPU) |
| **Meta-skill** | `/dynamic-tooling` | On-the-fly tooling for the sandbox |
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

---

## The 17-Phase DAG Loop

```
Phase  0: 加载问题（冻结 Q-id — INV-G1 锚点）
Phase  1: 问题理解与分解（内置推理）
Phase  2: /idea-discovery [DAG 分支] — 3 视角 idea + MCTS 迭代
Phase  2.5: /adversarial-falsification [证伪门控] — 假设评分 + 反例构造 + 文献对抗
Phase  3: /novelty-check [DAG 门控] — 4 维评估 + 淘汰
    ─── Forced human checkpoint: pick the final idea ───
Phase  4: /universal-retrieval — 文献调研 + 3 层防幻觉
Phase  5: /method-registry — 方法绑定 + hash 锁 + 强制人类审批
    ─── Forced human checkpoint: approve the method registry ───
Phase  6: /theory-derivation — SymPy 符号推导 + 逐步机器验证
Phase  6b: /experiment-execution (toy) [CONDITIONAL] — v2.0 玩具实验 (theory-only → SKIP)
Phase  6c: /experiment-execution (full+bg) [CONDITIONAL] — v2.0 全量实验后台调度 (theory-only → SKIP)
Phase  7: /leakage-audit — Type I 逻辑漏洞 + Type IV 逃逸审计
Phase  8: /logic-verification — 6 维度逻辑一致性审计
Phase  9: /invariant-check — INV-G1 问题锚点冻结验证
Phase 10: /result-to-claim — 3 保真度 claim 门控
Phase 11: /unified-plotting — 学术图表（可选，莫兰迪色系 + Layer 2）
Phase 12: /paper-writing — elsarticle 单模板写作
Phase 13: /paper-compile — LaTeX 零警告零报错编译
Phase 14: /auto-review-loop — 跨模型评审 + kill-argument 反自欺
Phase 15: /citation-audit — 最终引用 3 层验证
Phase 16: 最终组装 + 产物归档
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
| `color-themes.md` | Morandi palette (Layer 1) + viridis/magma data colormaps (Layer 2) | Carried from OSS (already discipline-agnostic) |

### Removed from OSS (discipline-specific, not applicable)

| Contract | Why removed |
|----------|-------------|
| `discipline-templates/` (cs-ml / economics / elsevier / physics / general) | Venue-specific templates — OSS uses single unified `elsarticle` template |
| `experiment-integrity.md` + `experiment-result-schema.md` | OSS has no experiments |
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
| **Verification paths** | Implicit — assumes code/experiment available | Explicit — theory-only / computational / theory+experiment 三路可选 |
| **Problem source** | N/A | No bundled problem index — the human user supplies the research question (Q-id) per run |
| **Figures** | Python pipeline mandatory (matplotlib/seaborn) | Python pipeline for data plots; AI-direct SVG allowed for simple diagrams (morandi palette still enforced) |
| **Fidelity ladder** | 5-fidelity (text / symbolic / minimal / empirical / full) | 3-fidelity (symbolic / numerical / qualitative) — no empirical, no full |
| **Invariants** | INV-E1~E5 (econ) + INV-C1~C4 (cs-ml) + INV-P1~P5 (physics) + INV-G1 (general) | INV-G1 only (PROBLEM_ANCHOR_FREEZE) — universal |
| **Leakage audit** | Type I + II + III + IV (with 14-class econ / 14-class cs-ml / 10-class physics pitfall checklists) | Type I (universal) + Type IV (universalized beyond physics) — Type II/III NOT_APPLICABLE |
| **Quality floor** | QF-E* / QF-C* / QF-P* / QF-G* (per-discipline) | QF-G1~G9 only (universal) |
| **Self-deception guard** | SD-E* / SD-C* / SD-P* / SD-G* (per-discipline) | SD-G1~G5 only (universal) |

---

## Invocation Patterns

### Solve one problem (default)

```
"帮我完整研究 Q015：宇宙的起源与演化"
"Solve a math problem: prove the Riemann Hypothesis implications"
"Analyze this economics model: general equilibrium under incomplete markets"
```

The orchestrator runs the full 21-phase loop. Forced human checkpoints at Phase 3→4 (pick final idea) and Phase 5→6 (approve method registry).

### Resume from checkpoint

If a prior run halted at a forced human checkpoint or a BLOCKED fallback, the orchestrator can resume from the last completed phase:

```
"继续 Q015 的研究 — 我已经选了 idea 2"
"resume Q042 — method registry approved, proceed to theory derivation"
```

### Partial run (debugging)

The user can invoke individual skills directly for debugging (bypassing the orchestrator):

```
"/theory-derivation on the Q015 derivation plan"
"/logic-verification on derivations/Q015/derivation_output.md"
"/paper-compile paper/main.tex"
```

But the **canonical** workflow is the full 21-phase orchestrator loop — partial runs are for debugging only and do not produce a complete artifact chain.

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
- [`skills/orchestrator/auto-pipeline/SKILL.md`](skills/orchestrator/auto-pipeline/SKILL.md) — the 21-phase DAG loop orchestrator
- [`skills/shared-references/`](skills/shared-references/) — the shared contract layer (discipline-agnostic)