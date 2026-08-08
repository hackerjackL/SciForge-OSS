---
name: invariant-check
version: 1.1.1
description: "Verify INV-G1 problem-anchor freeze (Q-id referenced in every downstream artifact). Phase 9. Invoke before result-to-claim to ensure the question hasn't drifted."
type: reference-skill
role: phase-boundary-verifier
---

# Invariant Check (Phase-Boundary Verifier) — SciForge-OSS

## Quick Reference

- **Purpose**: 阶段边界结构性检查 — 验证文件存在、Q-id 冻结、verdict 有效
- **Input**: refine-logs/FINAL_PROPOSAL.md + 当前阶段产物
- **Output**: INVARIANT_CHECK.json + INVARIANT_CHECK.md
- **Key**: 仅 INV-G1 (PROBLEM_ANCHOR_FREEZE) 活跃；不评估质量，只检查结构完整性

> **Status**: Structural verifier invoked at OSS phase boundaries. **OSS is discipline-agnostic** — only the universal `INV-G1 PROBLEM_ANCHOR_FREEZE` invariant is active. There are no discipline overlays (no `INV-E*` economics, no `INV-C*` cs-ml, no `INV-P*` physics). Copied from main SciForge and trimmed to OSS's single-row design.

## Use When

This skill is invoked by the OSS orchestrator (`/auto-pipeline`) at phase boundaries to verify that load-bearing invariants hold before the next phase begins. It is **not** a user-facing skill — users never invoke `/invariant-check` directly. The orchestrator calls it as a gate between phases.

Typical invocation context (by the orchestrator, not a user):

- Before `/theory-derivation` — verify Problem Anchor is frozen (the original problem statement's Q-id is locked and referenced)
- Before `/logic-verification` — verify Problem Anchor still matches (no drift mid-paper)
- Before `/paper-writing` — verify LEAKAGE_AUDIT verdict is PASS or WARN
- Before `/result-to-claim` — verify Problem Anchor + derivation chain intact

## Job

Act as a **structural verifier** that confirms load-bearing artifacts exist, are well-formed, and carry the expected verdicts. This skill is NOT a reviewer — it does not assess quality, novelty, correctness, or methodology. It only checks structural invariants: does the file exist, does the hash match, does the verdict field contain an allowed value.

The distinction is critical: a reviewer asks "is this good?"; an invariant checker asks "is this present and structurally valid?". Confusing the two leads to either false gates (blocking on quality disagreements that belong in review) or missing gates (letting absent artifacts through because "the content looked fine").

What this skill DOES guarantee:
- The artifacts the next phase depends on exist at their canonical paths
- The Problem Anchor (user-supplied Q-id) is frozen and referenced throughout
- Verdict-carrying artifacts have a verdict in the allowed set

What this skill does NOT do:
- Assess whether the methodology is sound (that is `/leakage-audit`'s job)
- Assess whether claims are supported (that is `/result-to-claim`'s job)
- Assess whether the paper is well-written (that is `/auto-review-loop`'s job)

## Invariant Set (OSS — Single Universal Invariant)

OSS has **one** active invariant. There is no discipline prefix table (main SciForge has `INV-C`/`INV-P`/`INV-E`/`INV-G` prefixes; OSS uses only `INV-G`).

| ID | Name | Trigger | Pass Condition | Fail Action | Rationale |
|----|------|---------|----------------|-------------|-----------|
| `INV-G1` | `PROBLEM_ANCHOR_FREEZE` | Before `/theory-derivation`, before `/logic-verification`, before `/paper-writing`, before `/result-to-claim` | The original problem statement's Q-id (from `the user-supplied research question`, supplied by the human user's prompt) is recorded in `refine-logs/FINAL_PROPOSAL.md` AND referenced in the current phase's working artifact (derivation chain / verification audit / paper draft / claim) | BLOCK — re-anchor to the original Q-id before proceeding | Prevents problem drift mid-paper. Without this, the agent may start solving a different (easier, more familiar) problem than the one the human user supplied. The freeze forces every phase to trace back to the same Q-id. |

**No other invariants are active in OSS.** Main SciForge's `INV-E1~E5` (economics PREREG_HASH / OUTCOME_CLASSIFICATION / LEAKAGE_AUDIT_VERDICT / DATA_SOURCE_CONSISTENCY / ESTIMATOR_VERIFICATION_GATE), `INV-C1~C4` (cs-ml BENCHMARK_PROTOCOL_LOCK / ABLATION_COMPLETENESS / SEED_STRATEGY_LOCK / LEAKAGE_AUDIT_VERDICT), `INV-P1~P5` (physics PNV_SKETCH_HASH / SIMULATION_REPRODUCIBILITY / LEAKAGE_AUDIT_VERDICT / PNV_CHAIN_CLOSURE / TYPE_IV_ESCAPE_CHECK) are all **removed** — they are discipline-specific and OSS has no discipline dispatch.

The universal `LEAKAGE_AUDIT_VERDICT` check (main SciForge had it as INV-E3 / INV-C4 / INV-P3) is handled directly by `/leakage-audit`'s own output in OSS, not as a separate invariant here.

## Required Workspace

The verifier reads from the project root. It does not modify any files except its own output.

**Inputs** (checked, not consumed):
- `refine-logs/FINAL_PROPOSAL.md` — from the orchestrator's Phase 1 (problem understanding); must contain the frozen Q-id
- `audit_report/LEAKAGE_AUDIT.json` — from `/leakage-audit` (for the pre-paper-writing gate)
- Current phase's working artifact (derivation chain / verification audit / paper draft / claim) — path passed by the orchestrator

**Outputs**:
- `audit_report/INVARIANT_CHECK.json` — machine-readable verdict (6-state schema)
- `audit_report/INVARIANT_CHECK.md` — human-readable summary

## Verdict Schema

Each invariant check produces a verdict from the 6-state machine defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md):

| State | Meaning | Orchestrator action |
|-------|---------|---------------------|
| `PASS` | Invariant holds | Proceed to next phase |
| `WARN` | Invariant holds with caveat | Proceed, but log the caveat |
| `FAIL` | Invariant violated | BLOCK — fix before proceeding |
| `NOT_APPLICABLE` | Invariant does not apply in this context | Skip (treat as PASS) |
| `BLOCKED` | Cannot check (prerequisite missing) | BLOCK — fix the prerequisite first |
| `ERROR` | Verifier itself failed | BLOCK — investigate verifier, do not proceed |

The overall verdict for a phase boundary is the **worst** verdict across all triggered checks: `ERROR > BLOCKED > FAIL > WARN > NOT_APPLICABLE > PASS`.

## Output Format

Write to `audit_report/INVARIANT_CHECK.json`:

```json
{
  "timestamp": "2026-07-20T12:00:00Z",
  "phase_boundary": "before-paper-writing",
  "discipline_context": "general",
  "overall_verdict": "PASS",
  "checks": [
    {
      "id": "INV-G1",
      "name": "PROBLEM_ANCHOR_FREEZE",
      "verdict": "PASS",
      "detail": "Q-id SCIMATH-042 frozen in FINAL_PROPOSAL.md and referenced in paper draft Section 1",
      "evidence": "refine-logs/FINAL_PROPOSAL.md Q-id == paper/main.tex Section 1 Q-id reference"
    }
  ]
}
```

Write to `audit_report/INVARIANT_CHECK.md` — a human-readable summary with one section per check, including the verdict, detail, and evidence.

## Audit Workflow

### Step 0: Load DISCIPLINE_CONTEXT

Read `AGENT_DOC.md` for `DISCIPLINE_CONTEXT` block. In OSS, this is **always** `general` (see [`discipline-context.md`](../../shared-references/discipline-context.md)). There is no 4-level fallback — there is only one level. Record `discipline_context: general` in the output JSON for traceability.

### Step 1: Determine Phase Boundary

The orchestrator passes the phase boundary identifier (e.g. `before-theory-derivation`, `before-logic-verification`, `before-paper-writing`, `before-result-to-claim`). The verifier uses this to confirm INV-G1 should trigger (it triggers at all four).

### Step 2: Run INV-G1 Check

1. Check that `refine-logs/FINAL_PROPOSAL.md` exists. If not, verdict = `BLOCKED` (prerequisite missing).
2. Extract the frozen Q-id from `FINAL_PROPOSAL.md` (the `Q-id:` field).
3. Check that the current phase's working artifact (path passed by orchestrator) exists. If not, verdict = `BLOCKED`.
4. Search the working artifact for a reference to the same Q-id. If found, verdict = `PASS`. If the Q-id is absent, verdict = `FAIL` (problem anchor lost). If a *different* Q-id is referenced, verdict = `FAIL` (problem drift — the agent started solving a different problem).
5. **问题内容哈希校验（v5.1 — 源自 CRUX 影子评估失败模式 #3）**: 除了 Q-id 存在性，还校验问题**内容**未被改写。首次冻结时计算 FINAL_PROPOSAL.md 中问题陈述段的 SHA256 写入 `refine-logs/PROBLEM_HASH.txt`；每次 INV-G1 触发时重算并比对。不匹配 → `FAIL (problem_content_rewritten)`。**针对的死法**：CRUX 实验中 agent 早期检测器全部失败后，把目标改写成"证明这类检测器不存在"，然后写了篇负结果论文——"像一个博士生发现假设不成立后，转头改掉了课题名称"。Q-id 没变但问题实质已变，旧版 INV-G1 只查 Q-id 存在性，拦不住这种改写
6. Record the verdict, detail, and evidence.

**改写问题的唯一合法路径**：若负结果确证原问题不可行（toy/full 证据 + KILL-or-PIVOT 判定为 KILL），必须走 `/kill-argument` 杀论证 → 回 Phase 2 **显式换 idea**（新 Q-id、新 FINAL_PROPOSAL、新 PROBLEM_HASH），由 orchestrator 记录 pivot/kill 事件——**禁止**在原 FINAL_PROPOSAL 上就地改写问题措辞来"适配"负结果。就地改写 = `problem_content_rewritten` FAIL；换 idea 重走 = 合法。

### Step 3: Compute Overall Verdict

With only INV-G1 active, the overall verdict = INV-G1's verdict.

### Step 4: Emit Output

Write `audit_report/INVARIANT_CHECK.json` and `audit_report/INVARIANT_CHECK.md`.

### Step 5: Return to Orchestrator

The orchestrator reads `overall_verdict`:
- `PASS` or `WARN` or `NOT_APPLICABLE` → proceed to next phase
- `FAIL` or `BLOCKED` or `ERROR` → halt and report to user

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Protocol](../../shared-references/output-protocol.md)** — versioned writes + MANIFEST logging + output language (merged single source of truth)

## Boundaries

- **Structural, not substantive.** This skill checks file existence, Q-id matching, and verdict parsing. It never assesses methodology quality, claim validity, or paper writing quality.
- **No discipline overlays.** OSS has only INV-G1. Do not reintroduce `INV-E*`/`INV-C*`/`INV-P*` invariants — they are discipline-specific and OSS is discipline-agnostic. If a problem seems to need a discipline-specific invariant (e.g., a physics problem wants PNV_SKETCH_HASH), that's handled by the agent's runtime reasoning in `/theory-derivation` + `/dynamic-sandbox`, NOT by an invariant overlay.
- **Never user-invoked.** Users do not call `/invariant-check`. The orchestrator calls it as a gate. If a user asks for an invariant check, direct them to `/auto-pipeline`.
- **No side effects.** The verifier reads artifacts and writes its own output. It never modifies the artifacts it checks.
- **6-state verdict only.** Do not invent new verdict states. The 6-state machine is defined in [`assurance-contract.md`](../../shared-references/assurance-contract.md) and is the contract with the orchestrator.

## See Also

- [`../shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md) — 6-state verdict schema (PASS/WARN/FAIL/NOT_APPLICABLE/BLOCKED/ERROR)
- [`../shared-references/discipline-context.md`](../../shared-references/discipline-context.md) — OSS single-row (`general`) discipline contract
- [`../leakage-audit/SKILL.md`](../leakage-audit/SKILL.md) — produces LEAKAGE_AUDIT.json (consumed by the pre-paper-writing gate)
- [`../result-to-claim/SKILL.md`](../result-to-claim/SKILL.md) — consumes the INV-G1 freeze before claim gating
