"""Phase bundle builder — pointer-load + constraint re-injection (S01/S04).

methodology-and-context-contract.md says: a phase loads ONLY its own SKILL.md
+ declared references; everything else is a path. CRUX failure mode #5 says:
hard constraints get forgotten over long runs unless re-injected verbatim at
every boundary. The kernel solves both mechanically: every phase prompt IS a
freshly built bundle file (small, pointer-only) whose tail is the verbatim
hard-constraint recitation computed from live state (routing, budgets, matrix,
kill/BA counters) — nothing is left to the model's memory.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def hard_constraints(ws: Path, budget: dict) -> list[str]:
    """Verbatim recitation from live state (kernel reads, never the model)."""
    out: list[str] = []
    vp = ws / ".sciforge" / "verdicts"
    routing = _load(vp / "VERIFICATION_ROUTING.json")
    if routing:
        out.append(f"verification route = {routing.get('route')} (evidence_type={routing.get('evidence_type')})")
        out.append(f"na_verdicts (legitimately absent verdicts) = {routing.get('na_verdicts', [])}")
    bf = _load(vp / "BUDGET_FLOOR.json")
    if bf:
        out.append(f"exploration budget_floor.satisfied = {bf.get('satisfied')} "
                   f"(completion may not be declared before it is true)")
    matrix = _load(vp / "EXPERIMENT_MATRIX.json")
    if matrix:
        groups = [g.get("group") or g.get("name") for g in matrix.get("groups", matrix if isinstance(matrix, list) else [])]
        out.append(f"mandatory experiment matrix groups = {groups}")
    lim = budget.get("limits", {})
    out.append(
        f"RUN_BUDGET: wall {budget.get('wall_clock_seconds', 0)}s/{lim.get('wall_clock_seconds_max')}s | "
        f"cost ${budget.get('api_cost_usd', 0)}/${lim.get('api_cost_usd_max')} | "
        f"pivot {budget.get('pivot_count', 0)}/{lim.get('pivot_count_max')} | "
        f"BA {budget.get('ba_rounds_used', 0)}/{budget.get('ba_rounds_max')}")
    out.append("3-round fallback cap per failure type; exhaustion => BLOCKED, never silent retry")
    out.append("negative-result discipline: failed claims route to Limitations, never to contributions")
    out.append("every citation must pass 3-layer verification (citation-discipline.md); zero fabricated refs")
    out.append("figures only via scripts/plotting/render_figure.py (no bypass); PDF+PNG dual output")
    out.append(f"INV-G1 anchor hash = {budget.get('_problem_hash', 'unset')} — do not drift the Q-id")
    return out


def build(ws: Path, phase: dict, budget: dict, inputs_hint: dict | None = None) -> Path:
    """Write .sciforge/refine-logs/phase_<id>.bundle.md; return its path."""
    pid = phase["id"]
    p = ws / ".sciforge" / "refine-logs" / f"phase_{pid.replace('.', '_')}.bundle.md"
    lines = [
        f"# SciForge phase bundle — {pid}: {phase['name']}",
        f"built_by=kernel@{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} mode=pointer-load",
        "",
        "## Task",
        f"Execute phase {pid} per the skill contract at `{phase.get('skill') or '(kernel-native)'}`.",
        "Read the skill file first; load only its declared references; produce the listed artifacts.",
        "",
        "## Required outputs (machine-checked at boundary)",
        json.dumps({"produces": phase.get("produces", []), "gate": phase.get("gate")},
                   indent=2),
        "",
        "## Hard constraints (re-injected verbatim — obey ALL, they are gate-checked)",
    ]
    lines += [f"- {c}" for c in hard_constraints(ws, budget)]
    if inputs_hint:
        from .sanitize import sanitize_external, is_suspicious
        dirty = [(k, v) for k, v in inputs_hint.items() if v]
        # v1.6: hints can embed remote-sourced snippets (gap digests, reviewer
        # comments). Neutralize authority tags before they reach the model.
        lines += ["", "## Input pointers (paths, not contents)",
                  *[f"- {k}: {sanitize_external(str(v))}" for k, v in dirty]]
        for k, v in dirty:
            tags = is_suspicious(str(v))
            if tags:
                lines.append(f"- [integrity] input '{k}' carried harness-like tags "
                             f"{tags} — neutralized; investigate the upstream source")
    lines += ["", "## Return contract",
              'Report a single JSON object: {"verdict": "PASS|WARN|FAIL|BLOCKED|NOT_APPLICABLE",'
              ' "artifacts": ["rel/paths"], "notes": "...", "cost_usd": <host-reported optional>}']
    p.write_text("\n".join(lines) + "\n")
    return p


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None
