"""Regressions for wiring a genuinely heterogeneous review panel (v1.7.4).

Each case here blocked the real two-provider panel before it was fixed; all
run offline against stubs so CI needs no gateway and no credentials.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "kernel"))

from sciforge.providers import Providers, _anthropic_text  # noqa: E402
from sciforge import review  # noqa: E402


# ---------------------------------------------------------------------------
# 1. reasoning models: thinking blocks must not contaminate the payload
# ---------------------------------------------------------------------------
def test_thinking_block_does_not_corrupt_json_payload():
    """A live gateway returned [thinking, text]. The old extraction serialised
    every non-text block as json.dumps(b["input"]), emitting a literal {} for
    thinking blocks, so a reviewer's JSON arrived as `{}{...}` and json.loads
    raised "Extra data" — every review would have failed to parse."""
    blocks = [{"type": "thinking", "thinking": "let me reason"},
              {"type": "text", "text": '{"overall": 7}'}]
    text = _anthropic_text(blocks)
    assert text == '{"overall": 7}'
    assert json.loads(text)["overall"] == 7


def test_redacted_thinking_and_unknown_blocks_are_ignored():
    blocks = [{"type": "redacted_thinking", "data": "zz"},
              {"type": "something_new", "payload": 1},
              {"type": "text", "text": "ok"}]
    assert _anthropic_text(blocks) == "ok"


def test_tool_use_input_is_still_serialised():
    """Structured output arrives as tool_use; that path must keep working."""
    assert json.loads(_anthropic_text(
        [{"type": "tool_use", "input": {"x": 1}}])) == {"x": 1}


def test_text_blocks_concatenate_and_empty_is_safe():
    assert _anthropic_text([{"type": "text", "text": "a"},
                            {"type": "text", "text": "b"}]) == "ab"
    assert _anthropic_text([]) == ""
    assert _anthropic_text([None, "junk"]) == ""


# ---------------------------------------------------------------------------
# 2. protocol must be declarable, not inferred from the backend's name
# ---------------------------------------------------------------------------
def _cfg(**backends):
    return {"backends": backends, "roles": {}, "pricing_usd_per_mtok": {}}


def test_named_backend_can_declare_anthropic_protocol():
    """A heterogeneous panel needs several Anthropic-protocol backends under
    distinct names (one per gateway provider id). Name-only inference sent them
    to /chat/completions and they 404'd."""
    p = Providers(config=_cfg(ds={"base_url": "http://x", "protocol": "anthropic"}))
    assert p._protocol("ds") == "anthropic"


def test_protocol_defaults_preserve_existing_configs():
    p = Providers(config=_cfg(anthropic={"base_url": "http://x"},
                              openai={"base_url": "http://y"},
                              ollama={"base_url": "http://z"}))
    assert p._protocol("anthropic") == "anthropic"
    assert p._protocol("openai") == "openai"
    assert p._protocol("ollama") == "openai"


def test_explicit_protocol_overrides_the_name():
    p = Providers(config=_cfg(anthropic={"base_url": "http://x",
                                         "protocol": "openai"}))
    assert p._protocol("anthropic") == "openai"


def test_unknown_protocol_value_falls_back_to_name():
    p = Providers(config=_cfg(weird={"base_url": "http://x", "protocol": "grpc"}))
    assert p._protocol("weird") == "openai"


# ---------------------------------------------------------------------------
# 3. SCIFORGE_MODEL must not flatten a deliberately heterogeneous panel
# ---------------------------------------------------------------------------
def test_sciforge_model_does_not_override_pinned_roles(monkeypatch):
    """The host-reported model is a convenience default. Flattening every role
    onto it silently undid the panel's heterogeneity — the exact
    homogeneous_degraded state the panel exists to escape."""
    monkeypatch.setenv("SCIFORGE_MODEL", "host-model")
    cfg = {"backends": {"a": {"base_url": "http://a", "api_key_env": ""}},
           "roles": {"review": {"backend": "a", "model": "m1", "pinned": True},
                     "adjudication": {"backend": "a", "model": "m2", "pinned": True},
                     "writing": {"backend": "a", "model": "m3"}},
           "pricing_usd_per_mtok": {}}
    p = Providers(config=cfg)
    assert p.model_for("review")["model"] == "m1"
    assert p.model_for("adjudication")["model"] == "m2"
    assert p.model_for("writing")["model"] == "host-model"


def test_sciforge_model_still_applies_when_nothing_is_pinned(monkeypatch):
    monkeypatch.setenv("SCIFORGE_MODEL", "host-model")
    cfg = {"backends": {"a": {"base_url": "http://a"}},
           "roles": {"review": {"backend": "a", "model": "m1"}},
           "pricing_usd_per_mtok": {}}
    assert Providers(config=cfg).model_for("review")["model"] == "host-model"


# ---------------------------------------------------------------------------
# 4. the panel reports real heterogeneity end to end (stubbed transport)
# ---------------------------------------------------------------------------
class _StubProviders:
    """Two distinct backends; records which one each persona actually used."""

    host_mode = False

    def __init__(self):
        self.roles = {"review": {"backend": "alpha", "model": "model-a"},
                      "reasoning": {"backend": "beta", "model": "model-b"},
                      "adjudication": {"backend": "gamma", "model": "model-c"}}
        self.calls = []

    def model_for(self, role):
        return self.roles[role]

    def complete(self, role, system, prompt, **kw):
        from sciforge.providers import CallRecord
        entry = self.roles[role]
        self.calls.append((role, entry["backend"], entry["model"]))
        score = {"review": 7, "reasoning": 3}.get(role, 5)  # real disagreement
        rec = CallRecord(role=role, backend=entry["backend"], model=entry["model"],
                         input_tokens=1, output_tokens=1, cached_tokens=0,
                         latency_s=0.0, cost_usd=0.0, ok=True, retries=0, ts=0.0)
        return json.dumps({"scores": {"soundness": score}, "overall": score,
                           "fatal": [], "kill_arguments": [], "summary": "s"}), rec


def test_two_backend_panel_is_heterogeneous_and_chair_is_distinct():
    p = _StubProviders()
    personas = [{"id": "methods", "role": "review", "bias": "b"},
                {"id": "repro", "role": "reasoning", "bias": "b"}]
    panel = review.review_paper(p, "a manuscript", personas=personas)
    pi = panel["panel_independence"]
    assert pi["status"] == "heterogeneous"
    assert pi["distinct_models"] == 2
    assert pi["distinct_backends"] == 2
    assert pi["adjudicator_distinct"] is True
    assert panel["reviews_n"] == 2 and panel["accepted_n"] == 2
    # the spread comes from two different models, not one model sampled twice
    assert panel["spread"] == 4
    assert {c[1] for c in p.calls} == {"alpha", "beta"}   # chair not yet invoked


def test_same_backend_panel_still_discloses_degradation():
    """The honest fallback must survive: one backend => homogeneous_degraded,
    never a silent claim of independence."""
    p = _StubProviders()
    p.roles["reasoning"] = dict(p.roles["review"])
    personas = [{"id": "a", "role": "review", "bias": "b"},
                {"id": "b", "role": "reasoning", "bias": "b"}]
    pi = review.review_paper(p, "m", personas=personas)["panel_independence"]
    assert pi["status"] == "homogeneous_degraded"
    assert pi["distinct_models"] == 1

# ---------------------------------------------------------------------------
# 5. default personas spread across backends only when the config is heterogeneous
# ---------------------------------------------------------------------------
def _providers_with(role_targets):
    backends = {b: {"base_url": f"http://{b}"} for b, _ in role_targets.values()}
    roles = {r: {"backend": b, "model": m} for r, (b, m) in role_targets.items()}
    return Providers(config={"backends": backends, "roles": roles,
                             "pricing_usd_per_mtok": {}})


def test_default_personas_stay_on_review_when_config_is_homogeneous():
    """The shipped single-backend default must not change behaviour or cost."""
    p = _providers_with({"review": ("a", "m"), "reasoning": ("a", "m"),
                         "grading": ("a", "m"), "adjudication": ("a", "m")})
    ps = review._default_personas(p)
    assert [x["role"] for x in ps] == ["review"] * 3
    assert review.panel_independence(p, ps)["status"] == "homogeneous_degraded"


def test_default_personas_spread_when_backends_differ():
    p = _providers_with({"review": ("a", "m1"), "reasoning": ("b", "m2"),
                         "grading": ("c", "m3"), "adjudication": ("d", "m4")})
    ps = review._default_personas(p)
    assert [x["role"] for x in ps] == ["review", "reasoning", "grading"]
    pi = review.panel_independence(p, ps)
    assert pi["status"] == "heterogeneous"
    assert pi["distinct_models"] == 3
    assert pi["adjudicator_distinct"] is True


def test_chair_role_is_never_used_as_a_reviewer_lens():
    """If adjudication were eligible, the chair would review its own case."""
    p = _providers_with({"review": ("a", "m1"), "adjudication": ("b", "m2")})
    ps = review._default_personas(p)
    assert all(x["role"] != "adjudication" for x in ps)


def test_chair_sharing_a_reviewer_model_is_disclosed():
    p = _providers_with({"review": ("a", "m1"), "reasoning": ("b", "m2"),
                         "grading": ("c", "m3"), "adjudication": ("c", "m3")})
    pi = review.panel_independence(p, review._default_personas(p))
    assert pi["status"] == "heterogeneous"
    assert pi["adjudicator_distinct"] is False


def test_sciforge_providers_env_selects_alternate_config(tmp_path, monkeypatch):
    """Opt-in heterogeneity must not require editing the shipped default."""
    from sciforge.providers import load_config

    alt = tmp_path / "alt.json"
    alt.write_text(json.dumps({"backends": {"z": {"base_url": "http://z"}},
                               "roles": {}}))
    monkeypatch.setenv("SCIFORGE_PROVIDERS", str(alt))
    assert "z" in load_config()["backends"]
