"""Cross-model review panel (S20/S21).

Design contract: N reviewers, each in an independent context (they never see
each other's output), score the same frozen rubric; disagreement (variance)
routes to an adjudicator.

What this module actually guarantees: CONTEXT independence is enforced here
(one completion per reviewer, no shared history). MODEL independence is a
property of the role mapping in kernel/config/providers.json, so it is
measured, never assumed. Every panel carries ``panel_independence`` with each
reviewer's resolved (backend, model), the distinct-model count, the
adjudicator's target, and a status:

- ``heterogeneous``: reviewers resolve to >= 2 distinct (backend, model)
  targets — a genuine multi-model panel;
- ``homogeneous_degraded``: reviewers share one model (or their routing
  cannot be resolved) — the panel is one model sampled under N bias lenses,
  so score variance reflects sampling noise rather than independent reviewer
  disagreement, and the adjudicator may be resolving its own disagreement.
  This is disclosed loudly in ``independence_warning``; it is never silently
  accepted as independent;
- ``host_mode``: no usable provider, so the kernel does not run the panel;
  the host agent runs N fresh-context sessions, which are context-independent
  but share one host model.

The shipped providers.json maps the review, adjudication and grading roles to
the SAME backend/model, so the default panel is ``homogeneous_degraded``
until the operator maps those roles to distinct backends/models.

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
    ("citation_integrity", 0.10, "Is every cited claim traceable to a real, verified reference, and is any missing verification layer explicitly disclosed? Partial verification is acceptable only when the gap is disclosed; silent overclaiming is a failure."),
)


def _rubric_text() -> str:
    return "\n".join(f"- {name} (w={w}): {q}" for name, w, q in RUBRIC_AXES)


# Anti-inflation anchors (v1.7.1, from PaperOrchestra autoraters): a self-
# score outside the band discipline is invalid. The default honest paper lives
# at 45-70; >85 requires per-axis evidence; "did everything right" caps at 84.
BAND_RULES = (
    "Scoring band discipline (anti-inflation): 45-70 is the DEFAULT band for "
    "honest competent work; 71-84 solid (all headline claims traced + clear "
    "positioning); >85 requires per-axis justification and a novel instrument "
    "or surprising established result; a paper that merely 'did everything "
    "right' caps at 84; verbosity never raises a score.")


# Panel-independence vocabulary (machine-readable in REVIEW_PANEL.json).
INDEPENDENCE_HETEROGENEOUS = "heterogeneous"
INDEPENDENCE_HOMOGENEOUS_DEGRADED = "homogeneous_degraded"
INDEPENDENCE_HOST_MODE = "host_mode"

_HOST_TARGET = {"backend": "host", "model": "host", "source": "host_mode",
                "resolved": True}


def _providers_host_mode(providers) -> bool:
    """Host mode as reported by Providers; None/dict handled conservatively."""
    if providers is None:
        return True
    if isinstance(providers, dict):
        if "host_mode" in providers:
            return bool(providers.get("host_mode"))
        return not providers.get("backends")
    return bool(getattr(providers, "host_mode", False))


def _target_for(providers, role: str) -> dict:
    """Resolve the (backend, model) a role actually routes to.

    Prefers Providers.model_for (which honors SCIFORGE_MODEL overrides), falls
    back to the raw roles mapping, and reports ``unknown`` rather than
    guessing when routing cannot be resolved.
    """
    if _providers_host_mode(providers):
        return dict(_HOST_TARGET, role=role)
    entry = None
    if isinstance(providers, dict):
        roles = providers.get("roles") or {}
    else:
        roles = getattr(providers, "roles", None) or {}
        model_for = getattr(providers, "model_for", None)
        if callable(model_for):
            try:
                entry = model_for(role)
            except Exception:
                entry = None
    if not isinstance(entry, dict) or not entry:
        entry = roles.get(role) or roles.get("default") or {}
    backend = entry.get("backend") if isinstance(entry, dict) else None
    model = entry.get("model") if isinstance(entry, dict) else None
    resolved = bool(backend) and bool(model)
    return {"role": role,
            "backend": backend or "unknown",
            "model": model or "unknown",
            "source": "role_config" if resolved else "unresolved",
            "resolved": resolved}


def _independence_disclosure(status: str, reason: str, reviewers: list[dict],
                             adjudicator: dict, shared: list[str]) -> str | None:
    """Human-readable, top-level disclosure; None means genuinely independent."""
    if status == INDEPENDENCE_HOST_MODE:
        return ("HOST MODE: no usable provider backend; the kernel does not run "
                "the review panel. Host-agent review sessions have fresh contexts "
                "but share one host model, so independence is contextual, not "
                "model-level.")
    n = len(reviewers)
    adj = f"{adjudicator.get('backend', 'unknown')}/{adjudicator.get('model', 'unknown')}"
    parts: list[str] = []
    if status == INDEPENDENCE_HOMOGENEOUS_DEGRADED:
        if reason == "routing_unresolved":
            parts.append("PANEL INDEPENDENCE UNVERIFIED: reviewer model routing could "
                         "not be resolved from the provider configuration; the panel "
                         "is treated as degraded and independence is never silently "
                         "assumed.")
        elif reason == "single_reviewer":
            parts.append("PANEL INDEPENDENCE DEGRADED: only one reviewer; a single "
                         "opinion is not a panel.")
        elif reason == "no_reviewers":
            parts.append("PANEL INDEPENDENCE DEGRADED: no reviewers resolved.")
        else:
            b = reviewers[0].get("backend", "unknown") if reviewers else "unknown"
            m = reviewers[0].get("model", "unknown") if reviewers else "unknown"
            parts.append(f"PANEL INDEPENDENCE DEGRADED: all {n} reviewers resolve to "
                         f"the same model ({b}/{m}); they differ only by bias prompt, "
                         "so panel-score variance reflects sampling noise, not "
                         "independent reviewer disagreement.")
    if shared:
        parts.append(f"The chair adjudicator ({adj}) is the same model as "
                     f"reviewer(s) {', '.join(shared)}, so it would adjudicate its "
                     "own disagreement.")
    elif not adjudicator.get("resolved", False):
        parts.append("Adjudicator routing could not be resolved; its independence "
                     "from the reviewers is unverified.")
    if parts:
        parts.append("For a genuinely heterogeneous panel, map DISTINCT "
                     "backend/model pairs under roles.review and "
                     "roles.adjudication in kernel/config/providers.json.")
    return " ".join(parts) if parts else None


def _build_independence(reviewers: list[dict], adjudicator: dict, *,
                        host_mode: bool) -> dict:
    """Derive counts/status/disclosure from resolved reviewer targets."""
    pairs = [(r.get("backend", "unknown"), r.get("model", "unknown"))
             for r in reviewers]
    distinct_models = len(set(pairs))
    distinct_backends = len({b for b, _ in pairs})
    adj_pair = (adjudicator.get("backend", "unknown"),
                adjudicator.get("model", "unknown"))
    shared = [r.get("id", f"#{i}") for i, r in enumerate(reviewers)
              if (r.get("backend"), r.get("model")) == adj_pair]
    all_resolved = all(r.get("resolved", False) for r in reviewers)
    adjudicator_distinct = bool(all_resolved
                                and adjudicator.get("resolved", False)
                                and not host_mode and not shared)
    if host_mode:
        status, reason = INDEPENDENCE_HOST_MODE, "host_mode"
    elif not reviewers:
        status, reason = INDEPENDENCE_HOMOGENEOUS_DEGRADED, "no_reviewers"
    elif not all_resolved:
        status, reason = INDEPENDENCE_HOMOGENEOUS_DEGRADED, "routing_unresolved"
    elif len(reviewers) == 1:
        status, reason = INDEPENDENCE_HOMOGENEOUS_DEGRADED, "single_reviewer"
    elif distinct_models >= 2:
        status, reason = INDEPENDENCE_HETEROGENEOUS, "distinct_models"
    else:
        status, reason = INDEPENDENCE_HOMOGENEOUS_DEGRADED, "same_model"
    return {
        "schema_version": "1.0",
        "status": status,
        "reason_code": reason,
        "distinct_models": distinct_models,
        "distinct_backends": distinct_backends,
        "reviewers": reviewers,
        "adjudicator": adjudicator,
        "adjudicator_distinct": adjudicator_distinct,
        "adjudicator_shared_with": shared,
        "disclosure": _independence_disclosure(status, reason, reviewers,
                                               adjudicator, shared),
    }


def panel_independence(providers, personas: list[dict] | None = None) -> dict:
    """Mechanical independence audit of the panel about to run.

    Given the personas and the provider role mapping, resolve every reviewer's
    and the adjudicator's actual (backend, model) and report the distinct-model
    count plus a status in {heterogeneous, homogeneous_degraded, host_mode}.
    Embedded in REVIEW_PANEL.json as ``panel_independence``; review_paper
    refreshes it with the backend/model each real call reports.
    """
    personas = personas or _default_personas(providers)
    host = _providers_host_mode(providers)
    reviewers = []
    for p in personas:
        role = p.get("role", "review")
        t = _target_for(providers, role)
        reviewers.append({"id": p.get("id", f"reviewer_{len(reviewers) + 1}"),
                          "role": role,
                          "backend": t["backend"], "model": t["model"],
                          "source": t["source"], "resolved": t["resolved"]})
    return _build_independence(reviewers, _target_for(providers, "adjudication"),
                               host_mode=host)


def review_paper(providers, paper_text: str, *, personas: list[dict] | None = None) -> dict:
    """Independent-context blind review. personas = [{id, role, bias}].

    Context independence is enforced; model independence is detected and
    disclosed via ``panel_independence`` (see module docstring).
    """
    personas = personas or _default_personas(providers)
    independence = panel_independence(providers, personas)
    if _providers_host_mode(providers):
        # The kernel cannot call an LLM here; the host agent must run the
        # panel. Report that explicitly instead of emitting N synthetic errors.
        panel = adjudicate([], independence=independence)
        panel["reason_code"] = "host_mode"
        panel["notes"] = independence.get("disclosure")
        return panel
    reviews = []
    for p in personas:
        system = ("You are an independent senior reviewer. Do NOT soften; do not see other reviews.\n"
                  "Score each axis 0-10 against the frozen rubric, then a weighted overall.\n"
                  + _rubric_text() + "\n" + BAND_RULES +
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
    # The backend/model each real call reports wins over the configured
    # target (SCIFORGE_MODEL overrides, gateway rewrites, failover).
    planned = {r["id"]: r for r in independence["reviewers"]}
    observed = []
    for p, rev in zip(personas, reviews):
        base = planned.get(p["id"], {})
        usage = rev.get("usage") or {}
        backend = usage.get("backend") or base.get("backend") or "unknown"
        model = usage.get("model") or base.get("model") or "unknown"
        observed.append({
            "id": p["id"], "role": p.get("role", "review"),
            "backend": backend, "model": model,
            "source": "call_record" if usage.get("backend") else base.get("source", "unresolved"),
            "resolved": backend != "unknown" and model != "unknown",
        })
    independence = _build_independence(observed, independence["adjudicator"],
                                       host_mode=False)
    return adjudicate(reviews, independence=independence)


def _default_personas(providers) -> list[dict]:
    """Three lenses: methods hawk, novelty hawk, reproducibility hawk.

    Bias-forced diversity alone only varies the prompt. If the config actually
    maps other review-capable roles to different (backend, model) pairs, spread
    the lenses across them so the panel gains real model independence without
    the caller hand-writing personas. When every candidate role resolves to the
    same target — the shipped single-backend default — all three stay on
    `review`, so existing behaviour and costs are unchanged.
    """
    lenses = [
        ("methods", "Attacked methods, statistics, confounds above all."),
        ("novelty", "Attacked novelty, delta vs closest prior work, overclaiming."),
        ("repro", "Attacked reproducibility, missing details, citation integrity."),
    ]
    # `adjudication` is deliberately excluded: the chair must stay distinct
    # from every reviewer, so it can never double as a reviewer lens.
    candidates = ["review", "reasoning", "grading"]
    seen: dict[tuple, str] = {}
    roles: list[str] = []
    for role in candidates:
        t = _target_for(providers, role)
        if not t["resolved"]:
            continue
        key = (t["backend"], t["model"])
        if key in seen:
            continue
        seen[key] = role
        roles.append(role)
    if len(roles) < 2:
        roles = ["review"]
    return [{"id": lid, "role": roles[i % len(roles)], "bias": bias}
            for i, (lid, bias) in enumerate(lenses)]


def adjudicate(reviews: list[dict], *, independence: dict | None = None) -> dict:
    """Aggregate + compute disagreement; >=1 fatal or spread>4 triggers kill-argument check.

    ``independence`` (from :func:`panel_independence`) is embedded verbatim and,
    when the panel is homogeneous or the chair shares a reviewer model, a
    top-level warning/disclosure is attached — degraded independence must be
    visible without digging into nested fields.
    """
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
    out = {"verdict": verdict, "reviews_n": len(reviews), "accepted_n": len(ok),
           "overall": round(statistics.mean(scores), 2) if scores else None,
           "spread": round(spread, 2), "fatal": fatals, "kill_arguments": kills,
           "adjudication_needed": verdict == "ADJUDICATE_REQUIRED",
           "per_reviewer": {r.get("reviewer", f"#{i}"): {"overall": r.get("overall"), "fatal": len(r.get("fatal", []))} for i, r in enumerate(reviews)}}
    if independence is not None:
        out["panel_independence"] = independence
        out["independence_warning"] = independence.get("disclosure")
        codes = []
        status = independence.get("status")
        if status == INDEPENDENCE_HOMOGENEOUS_DEGRADED:
            codes.append("panel_independence_degraded")
        elif status == INDEPENDENCE_HOST_MODE:
            codes.append("panel_host_mode")
        if not independence.get("adjudicator_distinct", False):
            codes.append("adjudicator_not_distinct")
        out["disclosures"] = codes
        if not independence.get("adjudicator_distinct", False):
            adj = independence.get("adjudicator") or {}
            shared = independence.get("adjudicator_shared_with") or []
            out["adjudicator_disclosure"] = (
                "SELF-ADJUDICATION RISK: the chair adjudicator "
                f"({adj.get('backend', 'unknown')}/{adj.get('model', 'unknown')}) "
                "is not a distinct model from every reviewer"
                + (f" (shares a model with: {', '.join(shared)})" if shared else "")
                + "; disagreement resolved by the same model that produced it is "
                  "weaker evidence than a cross-model adjudication.")
    return out


def _chair_meta(provider, panel: dict) -> dict:
    """Chair-routing metadata + self-adjudication disclosure for S21."""
    ind = panel.get("panel_independence") if isinstance(panel, dict) else None
    reviewers = list((ind or {}).get("reviewers") or [])
    if not reviewers:
        reviewers = panel_independence(provider, None)["reviewers"]
    adj = _target_for(provider, "adjudication")
    shared = [r.get("id") for r in reviewers
              if (r.get("backend"), r.get("model")) == (adj["backend"], adj["model"])]
    host = _providers_host_mode(provider)
    distinct = bool(adj.get("resolved", False) and not host and not shared)
    if distinct:
        disclosure = None
    elif host:
        disclosure = ("HOST MODE: adjudication would run on the same host model as "
                      "the reviewers; the self-adjudication caveat applies.")
    elif shared:
        disclosure = (f"SELF-ADJUDICATION: the chair adjudicator "
                      f"({adj['backend']}/{adj['model']}) is the same model as "
                      f"reviewer(s) {', '.join(shared)}; resolving a disagreement "
                      "with the same model that produced it weakens the evidential "
                      "value of the adjudication. Configure roles.adjudication to a "
                      "different backend/model.")
    else:
        disclosure = ("ADJUDICATOR INDEPENDENCE UNVERIFIED: adjudicator routing could "
                      "not be resolved; treated as not distinct from the reviewers.")
    return {"adjudicator": {"role": "adjudication", "backend": adj["backend"],
                            "model": adj["model"], "source": adj["source"],
                            "resolved": adj["resolved"]},
            "adjudicator_distinct": distinct,
            "adjudicator_shared_with": shared,
            "adjudicator_disclosure": disclosure}


def adjudicate_cross(provider, panel: dict, paper_text: str, claims: str) -> dict:
    """S21: a DIFFERENT model than any reviewer resolves the disagreement.

    The intent is cross-model adjudication; whether it actually is cross-model
    is mechanically checked and disclosed (``adjudicator_distinct`` +
    ``adjudicator_disclosure``), never assumed."""
    chair = _chair_meta(provider, panel)
    if not panel.get("adjudication_needed"):
        return {"adjudicated": False, "decision": panel["verdict"], **chair}
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
        d.update(chair)
        return d
    except Exception as e:
        return {"adjudicated": False, "error": str(e), "decision": "MAJOR_REVISION",
                **chair}


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
