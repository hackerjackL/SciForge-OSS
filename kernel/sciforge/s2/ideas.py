"""Seed ideas + idea evolution with the exploration guarantee (ScientistTwo §3.3).

Two mechanisms copied:

1. Seed ranking — ideas are generated then ranked by novelty (their novelty
   score + search check); only high-novelty seeds advance. Here: a
   deterministic ranker over {novelty, feasibility, evidence} scores so the
   ordering is reproducible and testable; the LLM generation stays host-side.

2. Exploration guarantee — each evolution round force-mixes >=1 *unexplored*
   seed into the candidate pool ("防止局部最优"). Without this, evolution
   over its own history converges onto whatever worked once. The kernel
   enforces it at loopback time: whenever a loopback targets idea
   regeneration (phases 2/5), `next_exploration_seed()` is attached to the
   loopback event, so the re-entered ideation phase receives a seed it has
   never evaluated — auditable in the event log, not in model memory.

Machine artifact: `.sciforge/audits/IDEA_EVOLUTION.json` (append-style
round ledger: explored seed ids + mixed seeds per round).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

AUDIT_REL = Path(".sciforge") / "audits" / "IDEA_EVOLUTION.json"


def rank_seeds(seeds: list[dict]) -> list[dict]:
    """Deterministic novelty-first ranking (stable ties by id).

    Each seed: {"id", "novelty": 0-1, "feasibility": 0-1, "evidence": 0-1}
    Missing scores default to 0 — an unscored seed never outranks a scored one.
    """
    def key(s: dict):
        return (-(float(s.get("novelty", 0) or 0)),
                -(float(s.get("feasibility", 0) or 0)),
                -(float(s.get("evidence", 0) or 0)),
                str(s.get("id", "")))
    return sorted(seeds, key=key)


def exploration_mix(seeds: list[dict], explored_ids: set[str],
                    min_new: int = 1) -> list[dict]:
    """The exploration guarantee: the round's pool starts with >=min_new
    UNEXPLORED seeds, then the rest by rank. Returns the mixed pool (dicts)."""
    ranked = rank_seeds(seeds)
    fresh = [s for s in ranked if str(s.get("id", "")) not in explored_ids]
    known = [s for s in ranked if str(s.get("id", "")) in explored_ids]
    forced = fresh[:max(0, int(min_new))]
    rest = [s for s in fresh if s not in forced]
    return forced + rest + known


def summarize_trace(trace: list[dict]) -> str:
    """History digest for the evolution prompt: successes AND failures
    (ScientistTwo feeds the full trace — a dead end is data)."""
    lines = []
    for t in trace or []:
        rid = t.get("id") or t.get("idea_id") or "?"
        outcome = t.get("outcome") or t.get("state") or "unknown"
        why = str(t.get("reason") or t.get("note") or "")[:200]
        lines.append(f"- {rid}: {outcome}" + (f" — {why}" if why else ""))
    return "\n".join(lines) or "(empty trace)"


def evolution_input(seeds: list[dict], trace: list[dict],
                    explored_ids: set[str] | None = None,
                    round_index: int = 1, min_new: int = 1) -> dict:
    """Assemble the idea-evolution payload the host phase-2 consumes."""
    explored = set(explored_ids or ())
    if not explored:
        explored = {str(t.get("id") or t.get("idea_id"))
                    for t in (trace or []) if t.get("id") or t.get("idea_id")}
    mixed = exploration_mix(seeds, explored, min_new=min_new)
    return {
        "schema_version": "1.0",
        "round": round_index,
        "history_trace": summarize_trace(trace),
        "explored_ids": sorted(explored),
        "exploration_pool": [{"id": s.get("id"), "forced_new": str(s.get("id", "")) not in explored}
                             for s in mixed],
        "guarantee": f">={min_new} unexplored seed(s) force-mixed into this round",
    }


def load(ws: Path) -> dict:
    p = Path(ws) / AUDIT_REL
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"schema_version": "1.0", "rounds": [], "explored_ids": []}


def save(ws: Path, doc: dict) -> Path:
    p = Path(ws) / AUDIT_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return p


def record_round(ws: Path, pool: list[dict], seeds: list[dict],
                 trace: list[dict], round_index: int | None = None) -> dict:
    """Append one evolution round to the ledger (explored ids accumulate)."""
    doc = load(ws)
    rounds = doc.get("rounds", [])
    idx = round_index if round_index is not None else len(rounds) + 1
    explored_before = set(doc.get("explored_ids", []))
    payload = evolution_input(seeds, trace, explored_before, round_index=idx)
    new_ids = [str(s.get("id", "")) for s in pool]
    rounds.append({"ts": time.time(), **payload, "mixed_ids": new_ids})
    doc.update({"rounds": rounds,
                "explored_ids": sorted(explored_before | set(new_ids))})
    save(ws, doc)
    return doc


def next_exploration_seed(ws: Path) -> str | None:
    """Kernel hook at loopback time: the id of the highest-ranked seed that
    has never been explored — or None when the ledger declares no candidates.
    Attaching this to the loopback event makes the exploration guarantee a
    logged, replayable fact instead of an instruction the model may drop."""
    doc = load(ws)
    seeds = doc.get("seed_candidates") or []
    if not seeds:
        return None
    explored = set(doc.get("explored_ids", []))
    fresh = [s for s in rank_seeds(seeds) if str(s.get("id", "")) not in explored]
    return str(fresh[0].get("id")) if fresh else None
