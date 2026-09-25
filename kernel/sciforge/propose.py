"""Evolution proposal generator (S15) — turn run evidence into skill-patch candidates.

The closed RSI loop:
  completed runs (RUNSTATE + events.ndjson + LESSONS + gate_rejected history)
    -> deterministic signals (which phases stall, which gates reject, which
       loopbacks exhaust, where budget-underuse fired)
    -> rule-based patch proposals against skills/*.md text (template mutations)
    -> LLM-generated patches (when providers configured)
    -> EvolutionRun search scores them -> human merge.

Deterministic-first (our own principle): even with no LLM at all, the auditor
emits real, checkable proposals from evidence — the mutation step can later be
refined by model or human, but the SIGNALS come from logs, not vibes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .evolve import Patch


def audit_run(ws: Path) -> dict:
    """Extract evolution signals from one completed (or blocked) run workspace."""
    sig = {"run_id": ws.name, "gate_rejections": {}, "loopbacks": {}, "phase_durations": {},
           "block_reasons": [], "warn_counts": {}}
    ev_file = ws / ".sciforge" / "events.ndjson"
    if ev_file.exists():
        for line in ev_file.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = e["kind"]; ph = e.get("phase", "?")
            if k == "gate_rejected":
                for f in e["payload"].get("failed", []):
                    key = f.get("gate", "?")
                    sig["gate_rejections"][key] = sig["gate_rejections"].get(key, 0) + 1
            elif k == "loopback":
                lid = e["payload"].get("id", "?")
                sig["loopbacks"][lid] = sig["loopbacks"].get(lid, 0) + 1
            elif k == "blocked":
                sig["block_reasons"].append(e["payload"].get("reason_code", "?"))
            elif k == "warn":
                c = e["payload"].get("code", "?")
                sig["warn_counts"][c] = sig["warn_counts"].get(c, 0) + 1
    pp = ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json"
    if pp.exists():
        try:
            sig["phase_durations"] = {k: v.get("duration_s")
                                      for k, v in json.loads(pp.read_text()).get("per_phase", {}).items()}
        except Exception:
            pass
    return sig


def proposals_from_signals(sigs: list[dict], skills_root: Path) -> list[dict]:
    """Rule-based proposals: stall points -> sharpen the responsible skill's gate wording.

    Each proposal = {path, old, new, rationale, evidence}. `old` MUST be verbatim
    existing text (apply_patch enforces); templates pull anchor sentences from the
    target skill so proposals are grounded, not invented.
    """
    # aggregate signals across runs
    agg: dict[str, int] = {}
    for s in sigs:
        for k, n in s["gate_rejections"].items():
            agg["gate:" + k] = agg.get("gate:" + k, 0) + n
        for k, n in s["loopbacks"].items():
            agg["loopback:" + k] = agg.get("loopback:" + k, 0) + n
        for k, n in s["warn_counts"].items():
            agg["warn:" + k] = agg.get("warn:" + k, 0) + n

    out: list[dict] = []
    hot = sorted(agg.items(), key=lambda x: -x[1])[:8]
    for signal, count in hot:
        target, anchor, insert = _map_signal(signal, skills_root)
        if not (target and anchor and insert):
            continue
        out.append({"path": target, "old": anchor, "new": anchor + insert,
                    "rationale": f"RSI: {signal} fired {count}x across {len(sigs)} runs",
                    "evidence": {"signal": signal, "count": count}})
    return out


# signal -> skill file + verbatim anchor + append (never rewrite the instrument)
_SIGNAL_MAP = {
    "gate:validate_verdicts": ("skills/shared-references/output-protocol.md",
                                "## Verdict Schema Enforcement",
                                "\n> RSI note: repeated boundary rejections => produce verdicts via the schema templates in schemas/README.md before requesting the boundary commit.\n"),
    "loopback:L1": ("skills/meta-skills/idea-discovery/SKILL.md",
                    "## MCTS Iteration Protocol",
                    "\n> RSI note: L1 falsification loopbacks frequent => pre-score ideas against counterexample templates in adversarial-falsification before MCTS promotion.\n"),
    "loopback:L8": ("skills/support/leakage-audit/SKILL.md",
                    "# Leakage Audit (SciForge-OSS — Discipline-Agnostic)",
                    "\n> RSI note: L8 method-patch loopbacks frequent => draft the Type-I scan checklist alongside method-registry §3 so leaks are found at registration time, not at audit time.\n"),
    "warn:budget_underuse": ("skills/shared-references/effort-contract.md",
                             "### `lite` (~0.4x tokens)",
                             "\n> RSI note: underuse warnings frequent => when a verdict is open and ≥50% budget remains, dispatch at least one additional falsification probe or seed replication before declaring completion.\n"),
}


def _map_signal(signal: str, skills_root: Path):
    key = signal.split(":", 1)
    if len(key) < 2:
        return None, None, None
    m = _SIGNAL_MAP.get(signal)
    if not m:
        return None, None, None
    rel, anchor, insert = m
    f = skills_root / rel
    if not f.exists():
        return None, None, None
    text = f.read_text()
    if anchor not in text:
        # anchor must move with the file: fall back to first heading line
        hm = re.search(r"^#{1,2} .*$", text, re.M)
        if not hm:
            return None, None, None
        anchor = hm.group(0)
    return rel, anchor, insert
