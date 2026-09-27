"""Subset→Full-Set experiment ladder + 3-state Critic (ScientistTwo §3.2).

The core engineering pattern we copy verbatim from ScientistTwo:

    baseline reproduction (subset) -> implement idea -> Critic three-state
    {BAD: discard | GOOD: promote to full-set | Engineer: tune <=2 rounds}
    -> full-set re-verification -> promote only on full-set pass

Why kernel code and not prose: their paper reports the ladder as the thing
that stopped them from shipping noise (a candidate must beat the reproduced
baseline on the FULL set, not just look good on a subset). Prose advice does
not survive contact with a low-capability model; a boundary gate does.

Machine artifact: `.sciforge/audits/S2_LADDER.json` (schema documented in
skills/shared-references/s2-protocol.md). The 6c boundary gate
(`scripts/s2_ladder_gate.py`) refuses the boundary when the ladder is
missing (while experiment results exist), still ENGINEER/BAD, over the
engineer cap, or when the full-set improvement is not strict.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SCHEMA_VERSION = "1.0"
STATES = ("BAD", "GOOD", "ENGINEER")
MAX_ENGINEER_ROUNDS = 2
AUDIT_REL = Path(".sciforge") / "audits" / "S2_LADDER.json"

# tolerance for the stated relative-gain arithmetic (rounding of printed values)
GAIN_TOLERANCE_PCT = 0.15


def relative_gain(baseline: float, candidate: float, direction: str = "maximize") -> float:
    """Signed relative improvement in percent (positive = better)."""
    b = float(baseline)
    c = float(candidate)
    if b == 0:
        # zero baseline: absolute difference is the only honest scale
        delta = (c - b) if direction == "maximize" else (b - c)
        return 100.0 * delta
    raw = (c - b) / abs(b) * 100.0
    return raw if direction == "maximize" else -raw


def is_improvement(baseline: float, candidate: float, direction: str = "maximize") -> bool:
    """Strictly better? (ties are NOT improvements — ScientistTwo's rule.)"""
    b, c = float(baseline), float(candidate)
    return c > b if direction == "maximize" else c < b


def decide(baseline: float, candidate: float, direction: str = "maximize",
           min_gain: float = 0.0) -> str:
    """The 3-state Critic, deterministic and mechanical.

    - strictly better beyond the margin  -> GOOD (promote to full-set)
    - equal / within margin (>= 0 floor) -> ENGINEER (tune, <=2 rounds)
    - worse                              -> BAD (discard)
    """
    gain = relative_gain(baseline, candidate, direction)
    if gain > max(min_gain, 0.0):
        return "GOOD"
    if gain >= 0.0:
        return "ENGINEER"  # tie / below margin: tune, <=2 rounds
    return "BAD"


def validate(doc: dict) -> list[str]:
    """Structural + semantic problems in an S2_LADDER document (empty = OK)."""
    problems: list[str] = []
    if not isinstance(doc, dict):
        return ["ladder is not a JSON object"]
    if doc.get("schema_version") not in (None, SCHEMA_VERSION):
        problems.append(f"unknown schema_version {doc.get('schema_version')!r}")

    subset = doc.get("subset") or {}
    fullset = doc.get("fullset") or {}
    critic = doc.get("critic") or {}
    metric = doc.get("metric") or {}

    if not subset:
        problems.append("subset stage missing (baseline reproduction never ran)")
    if not fullset:
        problems.append("fullset stage missing (full-set verification never ran)")

    state = critic.get("state")
    if state not in STATES:
        problems.append(f"critic.state must be one of {STATES}, got {state!r}")
    rounds = critic.get("engineer_rounds")
    if not isinstance(rounds, int) or rounds < 0:
        problems.append("critic.engineer_rounds must be a non-negative integer")
    elif rounds > MAX_ENGINEER_ROUNDS:
        problems.append(
            f"engineer_rounds={rounds} exceeds the ScientistTwo cap of "
            f"{MAX_ENGINEER_ROUNDS} (tuning budget exhausted => BLOCKED, not promote)")

    direction = metric.get("direction", "maximize")
    if direction not in ("maximize", "minimize"):
        problems.append(f"metric.direction must be maximize|minimize, got {direction!r}")

    fv = (fullset.get("candidate") or {}).get("value")
    bv = (fullset.get("baseline") or {}).get("value")

    if state == "GOOD":
        # the load-bearing claim: GOOD is only earned on the FULL set
        if fv is None or bv is None:
            problems.append("critic=GOOD but fullset baseline/candidate values missing "
                            "(promotion without full-set evidence)")
        elif not is_improvement(bv, fv, direction):
            problems.append(
                f"critic=GOOD but fullset candidate {fv} does not strictly beat "
                f"baseline {bv} (direction={direction})")
        if fullset.get("verified") is not True:
            problems.append("critic=GOOD but fullset.verified is not true")

    # arithmetic honesty: stated relative gain must match the full-set numbers
    stated = doc.get("relative_gain_pct")
    if stated is not None and fv is not None and bv is not None:
        expected = relative_gain(bv, fv, direction)
        if abs(expected - float(stated)) > GAIN_TOLERANCE_PCT:
            problems.append(
                f"relative_gain_pct stated {stated} != recomputed {round(expected, 4)} "
                f"(arithmetic inconsistency — reward-hacking class)")
    if not (doc.get("problem_id") or doc.get("run_id")):
        problems.append("problem_id/run_id missing (INV-G1 anchor required)")
    return problems


def load(ws: Path) -> dict | None:
    """Read the ladder from its canonical (or legacy) locations."""
    for base in (Path(ws) / ".sciforge" / "audits",
                 Path(ws) / "experiments",
                 Path(ws) / "results"):
        p = base / "S2_LADDER.json"
        if p.exists():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError:
                return {"_unreadable": str(p)}
    return None


def experiment_markers(ws: Path) -> dict[str, int]:
    """Counts of real experiment evidence (for SKIP-vs-FAIL gate semantics)."""
    root = Path(ws)
    counts = {"subset": 0, "full": 0, "any": 0}
    for stage in ("subset", "full", "toy"):
        d = root / "experiments" / stage
        if d.is_dir():
            n = sum(1 for _ in d.rglob("RESULT.json")) + \
                sum(1 for _ in d.rglob("STATUS.json")) + \
                sum(1 for _ in d.rglob("DISPATCH.json"))
            if stage in counts:
                counts[stage] = n
            counts["any"] += n
    # legacy single-dir layouts
    if (root / "experiments").is_dir():
        counts["any"] = max(counts["any"],
                            sum(1 for _ in (root / "experiments").rglob("RESULT.json")))
    return counts


def evaluate(ws: Path) -> tuple[str, dict | None, list[str]]:
    """Gate entry: -> (status, doc, problems). status in PASS|FAIL|SKIP."""
    markers = experiment_markers(ws)
    doc = load(ws)
    if doc is None:
        if markers["any"]:
            return "FAIL", None, [
                "experiment results exist but S2_LADDER.json is absent — the "
                "Subset→Full-Set ladder (ScientistTwo §3.2) was skipped"]
        return "SKIP", None, ["no experiment stage reached (ladder not applicable)"]
    if doc.pop("_unreadable", None):
        return "FAIL", None, ["S2_LADDER.json is not valid JSON"]
    problems = validate(doc)
    return ("FAIL" if problems else "PASS"), doc, problems
