"""Cross-model review panel (S20/S21) — replaces single-agent role-rotation prose.

Lesson from AI-Scientist v2 (real reviewers) + EvoScientist (multi-agent) + CRUX
(independence): a paper is reviewed by N reviewers on DIFFERENT backends/models,
each in an independent context (they do not see each other's output), scoring
against the same frozen rubric. Disagreement (variance) routes to an adjudicator.
When only one provider is configured (host mode), reviewers degrade to N
independent host-agent sessions with fresh context — still better than one.

Output = REVIEW_PANEL.json (feeds REVIEW_STATE.json + the kill-argument gate).
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

RUBRIC_AXES = (
    ("main_experiment_logic", 0.30, "Does the central experiment actually test the headline claim? Any uncontrolled confound that flips the conclusion?"),
    ("evidence_sufficiency", 0.20, "Are claims backed at >= numerical fidelity? Negative results in Limitations, not contributions?"),
    ("novelty_positioning", 0.15, "Is the delta vs prior work stated and defended against the closest citation?"),
    ("soundness", 0.15, "Derivation/compile/logic: any step the audit machinery did not actually verify?"),
    ("clarity_reproducibility", 0.10, "Could a peer rerun it from the repo artifacts?"),
    ("citation_integrity", 0.10, "Every cited claim traceable to a 3-layer-verified reference?"),
)


def _rubric_text() -> str:
    return "\n".join(f"- {name} (w={w}): {q}" for name, w, q in RUBRIC_AXES)


def review_paper(providers, paper_text: str, *, personas: list[dict] | None = None) -> dict:
    """Independent multi-model blind review. personas = [{id, role_model, bias}] ."""
    personas = personas or _default_personas(providers)
    reviews = []
    for p in personas:
        system = ("You are an independent senior reviewer. Do NOT soften; do not see other reviews.\n"
                  "Score each axis 0-10 against the frozen rubric, then a weighted overall.\n"
                  + _rubric_text() +
                  f"\nYour reviewer lens: {p['bias']}")
        prompt = ("Manuscript to review:\n<<<BEGIN\n" + paper_text[:60000] + "\n<<<END\n"
                  "Reply ONLY JSON: {\"scores\": {axis: number}, \"overall\": number, "
                  "\"fatal\": [str], \"kill_arguments\": [str], \"summary\": str}")
        try:
            text, rec = providers.complete(p.get("role", "review"), system, prompt,
                                           temperature=0.2)
            d = json.loads(_jsonobj(text))
            d["reviewer"] = p["id"]
            d["usage"] = rec.as_dict()
            reviews.append(d)
        except Exception as e:
            reviews.append({"reviewer": p["id"], "error": str(e), "scores": {}, "overall": None})
    return adjudicate(reviews)


def _default_personas(providers) -> list[dict]:
    # three lenses: methods hawk, novelty hawk, reproducibility hawk (bias-forced diversity)
    return [
        {"id": "methods", "role": "review", "bias": "Attacked methods, statistics, confounds above all."},
        {"id": "novelty", "role": "review", "bias": "Attacked novelty, delta vs closest prior work, overclaiming."},
        {"id": "repro", "role": "review", "bias": "Attacked reproducibility, missing details, citation integrity."},
    ]


def adjudicate(reviews: list[dict]) -> dict:
    """Aggregate + compute disagreement; >=1 fatal or spread>4 triggers kill-argument check."""
    ok = [r for r in reviews if r.get("overall") is not None]
    scores = [r["overall"] for r in ok]
    fatals = [f for r in ok for f in r.get("fatal", [])]
    kills = [k for r in ok for k in r.get("kill_arguments", [])]
    spread = (max(scores) - min(scores)) if len(scores) >= 2 else 0
    verdict = "REVISE"
    if not ok:
        verdict = "REVIEW_FAILED"
    elif not fatals and min(scores) >= 6:
        verdict = "ACCEPT"
    elif fatals or spread >= 4:
        verdict = "ADJUDICATE_REQUIRED"
    return {"verdict": verdict, "reviews_n": len(reviews), "accepted_n": len(ok),
            "overall": round(statistics.mean(scores), 2) if scores else None,
            "spread": round(spread, 2), "fatal": fatals, "kill_arguments": kills,
            "adjudication_needed": verdict == "ADJUDICATE_REQUIRED",
            "per_reviewer": {r.get("reviewer", f"#{i}"): {"overall": r.get("overall"), "fatal": len(r.get("fatal", []))} for i, r in enumerate(reviews)}}


def adjudicate_cross(provider, panel: dict, paper_text: str, claims: str) -> dict:
    """S21: a DIFFERENT model than any reviewer resolves the disagreement.
    It sees the conflicting reviews, not the raw manuscript alone."""
    if not panel.get("adjudication_needed"):
        return {"adjudicated": False, "decision": panel["verdict"]}
    system = ("You are the chair adjudicator. Reviewers disagreed or flagged fatal issues. "
              "Resolve: does any FATAL claim survive scrutiny, or is it a false positive? "
              "You may consult the manuscript and claims.")
    prompt = ("Reviewer panel JSON:\n" + json.dumps(panel, indent=1) +
              "\n\nHeadline claims:\n" + claims[:8000] +
              "\n\nManuscript (excerpt):\n" + paper_text[:40000] +
              "\n\nReply ONLY JSON: {\"decision\": \"ACCEPT|MAJOR_REVISION|REJECT_KILL\", "
              "\"surviving_fatal\": [str], \"reasoning\": str, \"confidence\": number}")
    try:
        text, rec = provider.complete("adjudication", system, prompt, temperature=0.1)
        d = json.loads(_jsonobj(text))
        d["adjudicated"] = True
        d["usage"] = rec.as_dict()
        return d
    except Exception as e:
        return {"adjudicated": False, "error": str(e), "decision": "MAJOR_REVISION"}


def _jsonobj(raw: str) -> str:
    """First score-bearing complete JSON object (models often emit an empty
    shell {} before the real payload, and wrap it in prose)."""
    objs = []
    i = 0
    while i < len(raw):
        if raw[i] == "{":
            depth = 0
            for j in range(i, len(raw)):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        objs.append(raw[i:j + 1]); i = j; break
        i += 1
    for o in objs:
        if '"overall"' in o or '"decision"' in o or '"score"' in o:
            return o
    return objs[0] if objs else raw
