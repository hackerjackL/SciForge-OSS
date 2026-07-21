# Engineering Grounding Contract — AI-Development Feasibility Axis

> **Status (v3.0 — AI perspective rewrite)**: Contract for the **Engineering Grounding (EG)** axis, the 6th axis in the idea pre-screen. Defines how OSS evaluates whether an **AI agent** can implement an idea — write code, run experiments, produce results — **not** whether a human engineering team can build it.
>
> **Core principle**: Innovation without implementability is a gamble. This axis quantifies the gamble from the **AI's perspective** — how many interaction rounds, how much compute, how complex the code, what dependencies exist, and how to mitigate the risk. It does NOT simplify ideas — it only labels, routes, and produces mitigation plans.

---

## 1. Why AI Perspective (Not Human Engineering)

| Misconception | Correction |
|--------------|-----------|
| EG measures "human team feasibility" | EG measures **AI agent feasibility** — the AI writing code, running experiments, and producing research outputs |
| EG measures "months of human labor" | EG measures **AI interaction rounds** — how many iterative cycles the AI needs to get from idea → working code → verified results |
| EG measures "talent availability" | **Not applicable** — AI is the implementer, not humans |
| EG measures "economic sustainability / commercial viability" | **Not applicable** — OSS is research-only, not commercial |

**Core question of EG**: "Can the AI agent, within its capabilities, implement this idea? How many rounds? How much code? What dependencies? What if the core trick is false?"

---

## 2. The 8 Sub-Dimensions (AI Perspective, Domain-Agnostic)

Every idea candidate is scored on 8 sub-dimensions. For humanities/social-science domains where code/experiment is not needed, relevant sub-dimensions are marked `NOT_APPLICABLE` (automatic 10/10, no penalty).

| # | Sub-dimension | What it measures | 0 (BLOCKED) | 5 (CONSTRAINED) | 10 (READY) | N/A handling |
|---|---------------|-----------------|-------------|-----------------|------------|-------------|
| 1 | **Compute Footprint** | AI 写代码、跑实验需要多少 compute | > 10× OSS sandbox budget (e.g., > 1000 GPU-h) | 1-10× sandbox budget | ≤ sandbox budget | Humanities theory-only: N/A (auto 10) |
| 2 | **Dependency Chain** | AI 能否自动获取/安装依赖（数据集、库、工具、仪器驱动） | ≥ 3 个依赖 AI 无法自动获取 | 1-2 个需辅助 | 全自动可用 | All domains: always applicable |
| 3 | **AI Dev Cycle** | AI 从 idea 到跑出可复现结果需要多少轮交互 | > 24 轮交互 | 6-24 轮 | ≤ 6 轮 | Humanities theory-only: N/A (auto 10) |
| 4 | **Reproducibility Risk** | 核心 trick 假后 AI 需要重写多少代码 | > 50% 概率 trick 假 → 全盘重写 | 20-50% 重写 | < 20% 重写 | All domains: always applicable |
| 5 | **Capital Cost** | AI 是否需要采购专有数据、付费 API、设备 | 需新基建/新采购 | 需采购但市售 | 仅用现有资源 | Humanities theory-only: N/A (auto 10) |
| 6 | **Code Complexity** | AI 实现此 idea 的代码复杂度——代码量、深度、多模块协同 | > 5000 行代码或跨 5+ 模块 | 1000-5000 行 | ≤ 1000 行 | Humanities theory-only: N/A (auto 10) |
| 7 | **Temporal Maturity** | AI 当前能力能否实现此 idea——依赖的技术/工具链当前是否就绪 | 当前 AI 能力完全做不到 | 需等 3-6 个月工具链成熟 | 现在就能做 | All domains: always applicable |
| 8 | **Regulatory Readiness** | idea 涉及的数据合规、伦理审批、出口管制是否影响 AI 执行 | 监管明文禁止 | 灰色地带，需审批 | 无限制 | All domains: always applicable |

### N/A Rule

If a sub-dimension is NOT_APPLICABLE for the domain, it scores **10/10** and does not penalize the average. The agent must explicitly state why it's N/A (e.g., "Compute Footprint: NOT_APPLICABLE — pure theoretical humanities problem, no compute needed"). This prevents "N/A as escape hatch" — every N/A must be justified.

### AI Dev Cycle Scoring Detail

| Score | AI Interaction Rounds | Scenario | Example |
|-------|----------------------|----------|---------|
| 0 | > 24 | AI 需要完整 pipeline 24 次以上迭代才能收敛 | 反复调参、反复修 BUG、反复换工具链 |
| 3 | 13-24 | AI 需要大量调试 | 代码量大、依赖链长、频繁报错 |
| 5 | 6-12 | AI 中等量级调试 | 核心代码 1-2 次写对，但实验验证需多次 |
| 8 | 3-5 | AI 快速实现 | 代码量小，一次写对，少量调试 |
| 10 | ≤ 2 | AI 几乎一次搞定 | 极简 idea，纯理论推导无需代码 |

---

## 3. EG Axis Tier Classification

```
eg_average = average of all non-N/A sub-dimensions (0-10 scale)

eg_average ≥ 6.0  →  READY        idea enters MCTS normally
eg_average 3.0-5.9 →  CONSTRAINED  idea enters MCTS, tagged `engineering_constrained`
eg_average < 3.0   →  HEAVY        idea enters MCTS, tagged `engineering_heavy`
≥ 3 sub-dimensions = 0  →  BLOCKED  idea rejected at pre-screen
```

### BLOCKED Rule

**≥ 3 sub-dimensions = 0** → BLOCKED. This is stricter than the old "any 1 = 0" rule, because a single dimension being extreme (e.g., AI Dev Cycle = 0 but everything else is fine) should not kill an idea. Only when 3+ dimensions are simultaneously impossible (e.g., "AI can't do it + no compute + code impossible") is the idea truly un-implementable.

**Exception**: If a sub-dimension is NOT_APPLICABLE, it can never be 0.

### Non-Elimination Rule (HEAVY / CONSTRAINED / 1-2 sub-dimensions = 0)

HEAVY, CONSTRAINED, and ideas with 1-2 sub-dimensions = 0 are **NOT eliminated**. They proceed through the full pipeline. The EG tier only affects:

1. The idea carries a visible `engineering_grounding` label in `IDEA_CANDIDATES.md` and `IDEA_DAG.json`
2. The novelty-check composite score includes EG as a small weight (see §5)
3. Every HEAVY/CONSTRAINED idea produces an `ENGINEERING_GROUNDING.md` report (see §4)
4. Ideas with 1-2 sub-dimensions = 0 produce an **AI Mitigation Plan** (see §4.1)
5. The human sees the EG score at the Phase 3→4 forced checkpoint

---

## 4. Engineering Grounding Report (ENGINEERING_GROUNDING.md)

Every idea with EG tier CONSTRAINED or HEAVY produces a report. READY ideas may produce a simplified version.

### Report Schema

```markdown
## IDEA-{id} Engineering Grounding Report

### 8-Dimension Scores
| Sub-dimension | Score (0-10) | Tier | Notes |
|---------------|-------------|------|-------|
| Compute Footprint | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. GPU-h or CPU-h; N/A reason if N/A} |
| Dependency Chain | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {list of unready deps} |
| AI Dev Cycle | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. AI interaction rounds} |
| Reproducibility Risk | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {risk % + key assumption} |
| Capital Cost | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. cost; N/A reason if N/A} |
| Code Complexity | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {est. lines of code + modules} |
| Temporal Maturity | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {AI capability readiness} |
| Regulatory Readiness | {0-10} | BLOCKED/CONSTRAINED/HEAVY/READY | {regulatory status} |
| **EG Average** | **{avg}** | **{OVERALL TIER}** | |

### AI Engineering Path (AI 开发路线)
- Stage 1 ({rounds range}): {cheapest possible AI implementation — write minimal code to falsify the core trick}
- Stage 2 ({rounds range}): {scaled AI implementation — 10% compute, limited data, partial code}
- Stage 3 ({rounds range}): {full AI implementation — complete code, full experiment, verified results}

### Downside Protection (trick 假的下行保护)
- If trick falsified at Stage 1 → loss = {rounds} (bounded, minimal)
- If falsified at Stage 2 → loss = {rounds} + {compute cost}
- If falsified at Stage 3 → loss = {rounds} + {full cost}
- **Recommendation**: {e.g., "Allocate Stage 1 rounds first. Do not commit Stage 2-3 until Stage 1 passes."}

### AI Engineering Path 自动出图

Phase 5b 完成后，自动调用 `/unified-plotting` 以 `ai-dev-path` 图表类型产出一张 **PDF 矢量图** `figures/engineering-path/ENGINEERING_GROUNDING_PATH.pdf`，内容为三段式 AI 开发路线时间轴：

```
Stage 1 (0-3 rounds) ───[risk: trick falsified]─── Stage 2 (3-9 rounds) ───[risk: scaled gate fail]─── Stage 3 (9-18 rounds)
       ↓ loss: 3 rounds                                   ↓ loss: 9 rounds + compute                              ↓ loss: 18 rounds + full
       [invest first]                                      [only if Stage 1 passes]                                [only if Stage 2 passes]
```

输出格式：**PDF**（矢量图，质量高于 SVG）。LaTeX 源码保留以支持可复现。
```

### 4.1 AI Mitigation Plan (for 1-2 sub-dimensions = 0)

If 1-2 sub-dimensions score 0 (but not ≥ 3, so not BLOCKED), the report MUST include a mitigation plan:

```markdown
### AI Mitigation Plan（AI 视角的缓解方案）
- **Extreme sub-dimension(s)**: [list of sub-dimensions with score = 0]
- **Mitigation option A**: 拆 idea 为 N 个子任务，每个可独立实现 → 降低 AI Dev Cycle
- **Mitigation option B**: 等工具链成熟（Temporal Maturity = 5，3 个月后有新工具可用）
- **Mitigation option C**: 用 simpler proxy 替代（降低 Code Complexity）
- **Mitigation option D**: 找替代数据集/API（降低 Dependency 或 Capital Cost）
- **Recommendation**: [e.g., "Option A 最可行——拆后 AI Dev Cycle 从 > 24 轮降至 8 轮，EG 子维升 5 分"]
```

### Engineering Path Design Principles

1. **Stage 1 is always the cheapest possible AI falsification** — write minimal code to test the core trick on OSS sandbox regime, or on a tiny dataset, or on a simplified model. The goal is to kill the idea as early as possible if it's false.
2. **Stage 2 is a scaled AI gate** — 10% compute, limited data, partial implementation. If the idea survives Stage 1 but fails Stage 2, the AI has spent moderate rounds.
3. **Stage 3 is the full AI implementation** — only invest AI rounds if Stages 1 and 2 both passed.
4. The stages are **not** the same as OSS pipeline phases. OSS pipeline runs the full theory derivation. The AI engineering path is a separate, round-based implementation plan for the AI agent.

---

## 5. Integration with Novelty-Check Composite Score

The novelty-check composite score formula is **updated** to include EG as a minor weight:

```
score = novelty × 0.45 + feasibility × 0.25 + relevance × 0.15 + engineering_grounding × 0.15
```

**EG normalization**: EG score fed into the composite formula is `eg_average / 10` (normalized to 0-1 scale). If all sub-dimensions are N/A (pure humanities theory), EG = 1.0 (no penalty).

---

## 6. Integration with Adversarial Falsification

The existing Phase 5 (Computational Feasibility) is **split** into two independent sub-phases:

| Phase | Name | What it evaluates | Independence |
|-------|------|-------------------|-------------|
| **Phase 5a** | OSS Sandbox Feasibility (unchanged) | Can the idea be run in OSS sandbox (SymPy + numpy)? | Independent |
| **Phase 5b** | AI Engineering Grounding Estimate (NEW) | AI perspective — 8-dimension EG evaluation | **Runs even if Phase 5a BLOCKED** (sandbox≠engineering) |

Phase 5b produces the `ENGINEERING_GROUNDING.md` report. It runs AFTER Phase 5a, but is **independent** — even if Phase 5a BLOCKED the idea, Phase 5b still executes. Phase 5b only skips if the idea is purely theoretical (no code/experiment needed).

---

## 7. Integration with Result-to-Claim

The existing `Grounding Confidence` in `result-to-claim` is **split**:

| Component | Source | What it reports |
|-----------|--------|-----------------|
| **OSS Sandbox Grounding** (unchanged) | Phase 5a result, re-computed in Phase 10 | Confidence that OSS derivation is correct |
| **AI Engineering Grounding** (NEW) | Inherited from Phase 5b; NOT re-computed | AI-perspective feasibility projection from idea stage |

The Phase 10 `Grounding Confidence` score becomes:
```
grounding_confidence = 0.6 × oss_sandbox_grounding + 0.4 × ai_engineering_grounding
```

The EG component is **inherited** from the idea stage, not re-computed.

---

## 8. Artifact Registration

| Artifact | Path | Producer | Consumers | Schema |
|----------|------|----------|-----------|--------|
| `ENGINEERING_GROUNDING.md` | refine-logs/ | Phase 5b (adversarial-falsification) | Phase 3→4 human checkpoint, novelty-check, result-to-claim, auto-review-loop | This contract |

---

## 9. Domain Applicability

| Domain | Sub-dimensions applicable | N/A dimensions |
|--------|--------------------------|---------------|
| **理工科** (CS/ML/Physics/Chem/Bio/Engineering/Medicine) | All 8 | None |
| **人文** (Philosophy/History/Literature/Law) | 4: Dependency Chain, AI Dev Cycle, Reproducibility Risk, Temporal Maturity, Regulatory Readiness | Compute Footprint, Capital Cost, Code Complexity (if theory-only) |
| **社科** (Economics/Sociology/Psychology/Education) | 6-8: All but Compute Footprint and Capital Cost may be N/A | Depends on whether quantitative analysis is needed |
| **数学/理论物理** (pure theory) | 4: Dependency Chain, Reproducibility Risk, Temporal Maturity, Regulatory Readiness | Compute Footprint, Capital Cost, Code Complexity, AI Dev Cycle (if no code needed) |

---

## 10. Boundaries

- **EG does NOT replace Tractability.** Both axes exist in parallel. Tractability = OSS sandbox feasibility. EG = AI implementation feasibility.
- **EG does NOT simplify ideas.** A HEAVY idea proceeds to full theory derivation. The EG report only labels and routes, never modifies the idea content.
- **N/A must be justified.** Every NOT_APPLICABLE annotation requires an explicit reason. "N/A as escape hatch" is forbidden.
- **EG is domain-agnostic.** The 8 sub-dimensions and N/A rules apply to all domains uniformly.
- **EG is NOT a compute budget for OSS.** The `effort-contract` budget (cs-ml 30 GPU-h etc.) remains OSS's internal search budget. EG's Compute Footprint measures the idea's AI implementation cost, which is 30-100× larger.

---

## 11. See Also

- [`idea-discovery/SKILL.md`](../meta-skills/idea-discovery/SKILL.md) — consumes EG axis at pre-screen
- [`idea-dag-schema.md`](idea-dag-schema.md) — node schema with EG fields
- [`novelty-check/SKILL.md`](../meta-skills/novelty-check/SKILL.md) — composite score with EG weight
- [`adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — Phase 5b EG estimate
- [`result-to-claim/SKILL.md`](../support/result-to-claim/SKILL.md) — inherits EG from Phase 5b
- [`auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — orchestrator quality gate
- [`competitive-analysis.md`](competitive-analysis.md) — marks EG as "已实施"