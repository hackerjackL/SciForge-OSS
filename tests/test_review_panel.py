"""Regression tests for the review-panel independence audit (H1) and the
citation-integrity rubric wording (H2).

Fully offline: providers are duck-typed stubs, no network and no real LLM call.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge import review  # noqa: E402

PAPER = "\\section{Introduction} We claim X and cite [1]."
CONFIG_PATH = REPO_ROOT / "kernel" / "config" / "providers.json"


def _roles(**overrides):
    base = {
        "default": {"backend": "anthropic", "model": "claude-opus-4-8"},
        "review": {"backend": "anthropic", "model": "claude-opus-4-8"},
        "adjudication": {"backend": "anthropic", "model": "claude-opus-4-8"},
        "grading": {"backend": "anthropic", "model": "claude-opus-4-8"},
        "writing": {"backend": "anthropic", "model": "claude-opus-4-8"},
    }
    base.update(overrides)
    return base


class _Rec:
    def __init__(self, role, backend, model):
        self.role, self.backend, self.model = role, backend, model

    def as_dict(self):
        return {"role": self.role, "backend": self.backend, "model": self.model,
                "input_tokens": 1, "output_tokens": 1, "cached_tokens": 0,
                "latency_s": 0.0, "cost_usd": 0.0, "ok": True, "retries": 0,
                "ts": 0.0}


class StubProviders:
    """Duck-typed Providers: routing config + deterministic completion."""

    def __init__(self, roles=None, host_mode=False, overall=7.0, fail=False):
        self.roles = roles if roles is not None else _roles()
        self.host_mode = host_mode
        self.overall = overall
        self.fail = fail
        self.calls = []

    def model_for(self, role):
        entry = self.roles.get(role) or self.roles.get("default")
        if not entry:
            raise KeyError(role)
        return entry

    def complete(self, role, system, prompt, **kw):
        if self.fail:
            raise RuntimeError("stub failure")
        self.calls.append(role)
        entry = self.model_for(role)
        if role == "adjudication":
            payload = {"decision": "MAJOR_REVISION", "surviving_fatal": [],
                       "reasoning": "stub", "confidence": 0.5}
        else:
            payload = {"scores": {"soundness": self.overall}, "overall": self.overall,
                       "fatal": [], "kill_arguments": [], "summary": "stub"}
        return json.dumps(payload), _Rec(role, entry["backend"], entry["model"])


class _BareProviders:
    """No role config, no model_for: routing cannot be resolved."""

    host_mode = False

    def __init__(self):
        self.calls = []

    def complete(self, role, system, prompt, **kw):
        self.calls.append(role)

        class _U:
            def as_dict(self):
                return {}

        return ('{"scores": {}, "overall": 7.0, "fatal": [], '
                '"kill_arguments": [], "summary": "s"}', _U())


# ---------------- H1: negative case — one model, three lenses ----------------

def test_shipped_default_config_is_homogeneous_degraded():
    """NEGATIVE: review/adjudication/grading share one model in the shipped
    config, so the panel must say homogeneous_degraded (distinct_models == 1)
    and warn loudly — never present itself as a multi-model panel."""
    cfg = json.loads(CONFIG_PATH.read_text())
    p = StubProviders(roles=cfg["roles"])
    panel = review.review_paper(p, PAPER)
    ind = panel["panel_independence"]

    assert ind["status"] == "homogeneous_degraded"
    assert ind["reason_code"] == "same_model"
    assert ind["distinct_models"] == 1
    assert ind["distinct_backends"] == 1
    assert len(ind["reviewers"]) == 3
    assert {r["id"] for r in ind["reviewers"]} == {"methods", "novelty", "repro"}
    assert all(r["backend"] == "anthropic"
               and r["model"] == "claude-opus-4-8" for r in ind["reviewers"])
    assert ind["adjudicator_distinct"] is False
    assert ind["adjudicator_shared_with"] == ["methods", "novelty", "repro"]
    # conspicuous top-level disclosure, not buried in the nested doc
    assert panel["independence_warning"]
    assert "DEGRADED" in panel["independence_warning"]
    assert set(panel["disclosures"]) == {"panel_independence_degraded",
                                         "adjudicator_not_distinct"}
    assert panel["adjudicator_disclosure"]
    assert "SELF-ADJUDICATION" in panel["adjudicator_disclosure"]
    assert p.calls == ["review", "review", "review"]


def test_unresolved_routing_is_never_called_heterogeneous():
    """NEGATIVE: unknown routing must degrade, not claim independence."""
    p = _BareProviders()
    panel = review.review_paper(p, PAPER)
    ind = panel["panel_independence"]
    assert ind["status"] == "homogeneous_degraded"
    assert ind["reason_code"] == "routing_unresolved"
    assert ind["distinct_models"] == 1
    assert "UNVERIFIED" in panel["independence_warning"]
    assert len(p.calls) == 3          # panel still runs, only the claim degrades


# ---------------- H1: positive case — real heterogeneous routing -------------

def test_heterogeneous_panel_reports_distinct_counts():
    """POSITIVE: distinct backend/model per reviewer role => heterogeneous."""
    roles = _roles(
        review={"backend": "anthropic", "model": "claude-opus-4-8"},
        grading={"backend": "openai", "model": "gpt-x"},
        writing={"backend": "ollama", "model": "llama-y"},
        adjudication={"backend": "google", "model": "gemini-z"},
    )
    personas = [
        {"id": "methods", "role": "review", "bias": "methods"},
        {"id": "novelty", "role": "grading", "bias": "novelty"},
        {"id": "repro", "role": "writing", "bias": "repro"},
    ]
    p = StubProviders(roles=roles)
    panel = review.review_paper(p, PAPER, personas=personas)
    ind = panel["panel_independence"]
    assert ind["status"] == "heterogeneous"
    assert ind["reason_code"] == "distinct_models"
    assert ind["distinct_models"] == 3
    assert ind["distinct_backends"] == 3
    assert [(r["backend"], r["model"]) for r in ind["reviewers"]] == [
        ("anthropic", "claude-opus-4-8"), ("openai", "gpt-x"),
        ("ollama", "llama-y")]
    assert ind["adjudicator_distinct"] is True
    assert ind["adjudicator_shared_with"] == []
    assert panel["independence_warning"] is None
    assert panel["disclosures"] == []
    assert "adjudicator_disclosure" not in panel
    assert p.calls == ["review", "grading", "writing"]


def test_heterogeneous_panel_with_self_adjudicating_chair_is_disclosed():
    """POSITIVE for the panel, NEGATIVE for the chair: panel is heterogeneous
    but the adjudicator shares reviewer 'methods' model => disclose."""
    roles = _roles(
        review={"backend": "anthropic", "model": "claude-opus-4-8"},
        grading={"backend": "openai", "model": "gpt-x"},
        writing={"backend": "ollama", "model": "llama-y"},
        adjudication={"backend": "anthropic", "model": "claude-opus-4-8"},
    )
    personas = [
        {"id": "methods", "role": "review", "bias": "methods"},
        {"id": "novelty", "role": "grading", "bias": "novelty"},
        {"id": "repro", "role": "writing", "bias": "repro"},
    ]
    panel = review.review_paper(StubProviders(roles=roles), PAPER, personas=personas)
    ind = panel["panel_independence"]
    assert ind["status"] == "heterogeneous"
    assert ind["adjudicator_distinct"] is False
    assert ind["adjudicator_shared_with"] == ["methods"]
    assert panel["independence_warning"] and "adjudicator" in panel["independence_warning"].lower()
    assert panel["disclosures"] == ["adjudicator_not_distinct"]
    assert "SELF-ADJUDICATION" in panel["adjudicator_disclosure"]


def test_call_record_routing_overrides_static_config():
    """POSITIVE: the model reported by the real call (gateway/override) is what
    the audit records, not the stale role config."""
    class _Gateway(StubProviders):
        def complete(self, role, system, prompt, **kw):
            self.calls.append(role)
            payload = {"scores": {"soundness": 7}, "overall": 7.0, "fatal": [],
                       "kill_arguments": [], "summary": "stub"}
            return json.dumps(payload), _Rec(role, "gateway", "routed-model")

    p = _Gateway(roles=_roles(
        review={"backend": "anthropic", "model": "configured-model"}))
    ind = review.review_paper(p, PAPER)["panel_independence"]
    assert ind["status"] == "homogeneous_degraded"
    assert {r["model"] for r in ind["reviewers"]} == {"routed-model"}
    assert {r["backend"] for r in ind["reviewers"]} == {"gateway"}
    assert {r["source"] for r in ind["reviewers"]} == {"call_record"}


# ---------------- H1: host mode ---------------------------------------------

def test_host_mode_is_explicit_and_never_calls_out():
    """NEGATIVE/environment: no usable provider => explicit host_mode status,
    REVIEW_FAILED (kernel cannot run the panel), zero completion attempts."""
    p = StubProviders(host_mode=True)
    panel = review.review_paper(p, PAPER)
    ind = panel["panel_independence"]
    assert ind["status"] == "host_mode"
    assert ind["reason_code"] == "host_mode"
    assert ind["distinct_models"] == 1
    assert panel["verdict"] == "REVIEW_FAILED"
    assert panel["reason_code"] == "host_mode"
    assert panel["independence_warning"]
    assert "HOST MODE" in panel["independence_warning"]
    assert "panel_host_mode" in panel["disclosures"]
    assert p.calls == []


def test_none_providers_is_host_mode_not_a_crash():
    panel = review.review_paper(None, PAPER)
    assert panel["panel_independence"]["status"] == "host_mode"
    assert panel["verdict"] == "REVIEW_FAILED"


# ---------------- H1: adjudicate()/adjudicate_cross() disclosure ------------

def test_adjudicate_without_independence_is_backward_compatible():
    out = review.adjudicate([{"overall": 7, "fatal": []},
                             {"overall": 8, "fatal": []}])
    assert out["verdict"] == "ACCEPT"
    assert "panel_independence" not in out
    assert "independence_warning" not in out


def test_adjudicate_embeds_independence_and_warning():
    p = StubProviders()
    ind = review.panel_independence(p)
    out = review.adjudicate([{"overall": 7, "fatal": []},
                             {"overall": 8, "fatal": []}], independence=ind)
    assert out["panel_independence"]["status"] == "homogeneous_degraded"
    assert out["independence_warning"]
    assert set(out["disclosures"]) == {"panel_independence_degraded",
                                       "adjudicator_not_distinct"}
    assert "SELF-ADJUDICATION" in out["adjudicator_disclosure"]


def test_adjudicate_cross_discloses_self_adjudication():
    p = StubProviders()
    panel = {"adjudication_needed": True, "verdict": "ADJUDICATE_REQUIRED",
             "fatal": ["claim X"], "panel_independence": review.panel_independence(p)}
    out = review.adjudicate_cross(p, panel, PAPER, "claims")
    assert out["adjudicated"] is True
    assert out["decision"] == "MAJOR_REVISION"
    assert out["adjudicator_distinct"] is False
    assert out["adjudicator_shared_with"] == ["methods", "novelty", "repro"]
    assert "SELF-ADJUDICATION" in out["adjudicator_disclosure"]


def test_adjudicate_cross_distinct_chair_has_no_disclosure():
    roles = _roles(adjudication={"backend": "openai", "model": "gpt-x"})
    p = StubProviders(roles=roles)
    panel = {"adjudication_needed": True, "verdict": "ADJUDICATE_REQUIRED",
             "fatal": ["claim X"], "panel_independence": review.panel_independence(p)}
    out = review.adjudicate_cross(p, panel, PAPER, "claims")
    assert out["adjudicator"] == {"role": "adjudication", "backend": "openai",
                                  "model": "gpt-x", "source": "role_config",
                                  "resolved": True}
    assert out["adjudicator_distinct"] is True
    assert out["adjudicator_disclosure"] is None


def test_adjudicate_cross_non_needed_panel_still_reports_chair():
    p = StubProviders()
    panel = {"adjudication_needed": False, "verdict": "ACCEPT",
             "panel_independence": review.panel_independence(p)}
    out = review.adjudicate_cross(p, panel, PAPER, "claims")
    assert out["adjudicated"] is False
    assert out["decision"] == "ACCEPT"
    assert out["adjudicator_distinct"] is False
    assert out["adjudicator_disclosure"]


# ---------------- H2: rubric wording ----------------------------------------

def test_citation_integrity_axis_is_not_bound_to_layer_count():
    axis = {name: (w, q) for name, w, q in review.RUBRIC_AXES}
    weight, question = axis["citation_integrity"]
    assert weight == 0.10
    low = question.lower()
    assert "3-layer" not in low and "three-layer" not in low
    assert "verified reference" in low
    assert "disclosed" in low


def test_shipped_providers_json_documents_panel_independence():
    cfg = json.loads(CONFIG_PATH.read_text())
    comment = cfg["comment"].lower()
    assert "homogeneous_degraded" in comment
    assert "heterogeneous" in comment
    assert "adjudication" in comment and "review" in comment
    for role in ("review", "adjudication", "grading"):
        assert cfg["roles"][role]["backend"] and cfg["roles"][role]["model"]