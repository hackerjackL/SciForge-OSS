"""Tests for scripts/validate_verdicts.py — the stdlib JSON-Schema-subset
validator for pipeline verdict files.

The module has no package structure, so it is loaded via importlib from
its file path.  SCHEMA_DIR inside the module resolves relative to the
module's own location, so the real schemas in
skills/shared-references/schemas/ are exercised directly (read-only).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VV_PATH = REPO_ROOT / "scripts" / "validate_verdicts.py"

_spec = importlib.util.spec_from_file_location(
    "validate_verdicts_under_test", VV_PATH)
vv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vv)


VALID_REVIEW_STATE = {
    "round": 2,
    "threadId": "t-123",
    "status": "in_progress",
    "difficulty": "hard",
    "last_score": 7.5,
    "last_verdict": "almost",
    "pending_derivations": ["lemma-3"],
    "timestamp": "2026-08-09T10:15:30Z",
    "response_class": [
        {"concern": "baseline missing",
         "response_class": "experiment_redesign"},
    ],
}


def write_json(d: Path, name: str, obj) -> Path:
    p = d / name
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# exit 0 — valid registered artifact
# ---------------------------------------------------------------------------

def test_valid_review_state_exit_0(tmp_path):
    write_json(tmp_path, "REVIEW_STATE.json", VALID_REVIEW_STATE)
    assert vv.main([str(tmp_path)]) == 0


def test_empty_response_class_array_still_valid(tmp_path):
    """Schema allows an empty response_class list (no concerns yet) as
    long as the field exists."""
    data = dict(VALID_REVIEW_STATE, response_class=[])
    write_json(tmp_path, "REVIEW_STATE.json", data)
    assert vv.main([str(tmp_path)]) == 0


# ---------------------------------------------------------------------------
# exit 1 — schema violations
# ---------------------------------------------------------------------------

def test_missing_required_field_exit_1(tmp_path):
    data = {k: v for k, v in VALID_REVIEW_STATE.items()
            if k != "response_class"}
    write_json(tmp_path, "REVIEW_STATE.json", data)
    assert vv.main([str(tmp_path)]) == 1


def test_bad_enum_value_exit_1(tmp_path):
    data = dict(VALID_REVIEW_STATE, status="paused")   # not in enum
    write_json(tmp_path, "REVIEW_STATE.json", data)
    assert vv.main([str(tmp_path)]) == 1


def test_numeric_bound_violation_exit_1(tmp_path):
    data = dict(VALID_REVIEW_STATE, last_score=12)     # maximum is 10
    write_json(tmp_path, "REVIEW_STATE.json", data)
    assert vv.main([str(tmp_path)]) == 1


def test_invalid_json_syntax_exit_1(tmp_path):
    (tmp_path / "REVIEW_STATE.json").write_text("{not json", encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 1


# ---------------------------------------------------------------------------
# exit 2 — usage errors
# ---------------------------------------------------------------------------

def test_nonexistent_dir_exit_2(tmp_path):
    assert vv.main([str(tmp_path / "does-not-exist")]) == 2


def test_no_arguments_exit_2():
    with pytest.raises(SystemExit) as excinfo:
        vv.main([])
    assert excinfo.value.code == 2


# ---------------------------------------------------------------------------
# WARN (exit 0) — unregistered artifacts; --strict flips them to exit 1
# ---------------------------------------------------------------------------

def test_unregistered_json_warn_exit_0(tmp_path):
    write_json(tmp_path, "MYSTERY_VERDICT.json", {"anything": 1})
    assert vv.main([str(tmp_path)]) == 0


def test_unregistered_json_strict_exit_1(tmp_path):
    write_json(tmp_path, "MYSTERY_VERDICT.json", {"anything": 1})
    assert vv.main([str(tmp_path), "--strict"]) == 1


def test_unregistered_txt_warn_exit_0(tmp_path):
    (tmp_path / "NOTES.txt").write_text("hello", encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 0


def test_misfiled_narrative_md_warn_strict_exit_1(tmp_path):
    """v6.0: only PIPELINE_VERDICT_SUMMARY.md may live in verdicts/; any
    other .md is a misfiled narrative (audits/ narratives belong in
    .sciforge/audits/). Default mode WARNs (exit 0), strict blocks."""
    (tmp_path / "AUTO_REVIEW.md").write_text("# narrative", encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 0
    assert vv.main([str(tmp_path), "--strict"]) == 1


def test_pipeline_verdict_summary_md_allowed(tmp_path):
    (tmp_path / "PIPELINE_VERDICT_SUMMARY.md").write_text(
        "# overview", encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 0
    assert vv.main([str(tmp_path), "--strict"]) == 0


# ---------------------------------------------------------------------------
# PROBLEM_HASH.txt sha256 format checks
# ---------------------------------------------------------------------------

def test_problem_hash_valid_lowercase_64hex_exit_0(tmp_path):
    (tmp_path / "PROBLEM_HASH.txt").write_text("a" * 64 + "\n",
                                               encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 0


@pytest.mark.parametrize("content,label", [
    ("A" * 64, "uppercase rejected"),
    ("a" * 64 + "\n" + "b" * 64, "multiple lines rejected"),
    ("a" * 63, "63 chars rejected"),
    ("g" * 64, "non-hex rejected"),
])
def test_problem_hash_invalid_exit_1(tmp_path, content, label):
    (tmp_path / "PROBLEM_HASH.txt").write_text(content + "\n",
                                               encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 1, label


def test_registry_hash_blocked_form_accepted(tmp_path):
    """method-registry SKILL.md 3.5: REGISTRY_HASH.txt may be BLOCKED."""
    (tmp_path / "REGISTRY_HASH.txt").write_text(
        "BLOCKED: incomplete experiment matrix\n", encoding="utf-8")
    assert vv.main([str(tmp_path)]) == 0


# ---------------------------------------------------------------------------
# validator internals (the stdlib JSON-Schema subset)
# ---------------------------------------------------------------------------

def test_type_matches_bool_is_not_int():
    assert vv.type_matches(True, "boolean")
    assert not vv.type_matches(True, "integer")
    assert vv.type_matches(3, "integer")
    assert vv.type_matches(3.5, "number")
    assert not vv.type_matches(3.5, "integer")


def test_lint_schema_rejects_unsupported_keywords():
    errors = vv.lint_schema({"type": "object", "$ref": "#/x"})
    assert any("$ref" in e for e in errors)
    assert vv.lint_schema({"type": "object",
                           "properties": {"a": {"type": "string"}}}) == []


# ---------------------------------------------------------------------------
# v1.7.4 — citation verification-depth disclosure must be internally
# consistent. Claiming 3 layers while reporting Layer 3 unavailable is a
# fabricated audit record, caught mechanically rather than in prose.
# ---------------------------------------------------------------------------

def _citation_errors(**fields):
    data = {"verdict": "PASS"}
    data.update(fields)
    return [e for e in vv.post_checks("CITATION_AUDIT.json", data)
            if "verification_depth" in e or "layers_verified" in e]


def test_claiming_three_layers_while_layer3_unavailable_is_rejected():
    errs = _citation_errors(
        verification_depth="3-layer",
        layers_verified=["arxiv", "crossref", "semantic_scholar"],
        layer3_status="unavailable_rate_limited")
    assert errs and any("contradicts" in e for e in errs)


def test_degraded_depth_may_not_claim_semantic_scholar():
    errs = _citation_errors(
        verification_depth="2-layer-degraded",
        layers_verified=["arxiv", "crossref", "semantic_scholar"],
        layer3_status="unavailable_network")
    assert errs and any("claims semantic_scholar" in e for e in errs)


def test_degraded_depth_still_requires_the_two_mandatory_layers():
    errs = _citation_errors(verification_depth="2-layer-degraded",
                            layers_verified=["crossref"],
                            layer3_status="unavailable_network")
    assert errs and any("two mandatory layers" in e for e in errs)


def test_honest_degraded_disclosure_passes():
    assert _citation_errors(
        verification_depth="2-layer-degraded",
        layers_verified=["arxiv", "crossref"],
        layer3_status="unavailable_rate_limited",
        layer3_detail="HTTP 429 after 3 attempts") == []


def test_genuine_three_layer_passes():
    assert _citation_errors(
        verification_depth="3-layer",
        layers_verified=["arxiv", "crossref", "semantic_scholar"],
        layer3_status="verified") == []


def test_pre_v174_artifact_without_depth_fields_is_untouched():
    """Backward compat: the check only fires when a depth is declared."""
    assert _citation_errors() == []


# ---------------------------------------------------------------------------
# audited_input_hashes must match disk (post-check 2 was inert)
# ---------------------------------------------------------------------------
# The REGISTRY carries an `audit_hashes` flag and the docstring documents the
# field as required, but nothing ever compared the recorded hashes against the
# files. S01 verifies 10/10 and the e2e fixture 6/6, so the mechanism can be
# self-consistent; ML04 verifies 8 of 43 because it re-ran its experiments and
# regenerated its tables without refreshing any audit, and kept five PASSes.

_AUDIT_BASE = {
    "PAPER_CLAIM_AUDIT.json": {
        "verdict": "PASS", "reason_code": "all_numbers_recomputed",
        "summary": "test fixture", "generated_at": "2026-11-16T12:00:00Z"},
    "LEAKAGE_AUDIT.json": {
        "verdict": "PASS", "discipline_context": "general",
        "type_i": {"n_leaky": 0, "n_total": 6, "items": []},
        "type_ii": "NOT_APPLICABLE", "type_iii": "NOT_APPLICABLE",
        "type_iv": {"n_escape": 0, "n_total": 6, "items": []},
        "blockers": [], "recommendations": []},
    "PROOF_AUDIT.json": {
        "audit_skill": "proof-audit", "verdict": "PASS",
        "reason_code": "ok", "summary": "test fixture",
        "trace_path": ".sciforge/audits/x.md", "reviewer_model": "test",
        "reviewer_reasoning": "test", "generated_at": "2026-11-16T12:00:00Z",
        "details": {}},
}


def _sha(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _ws_with_audit(tmp_path, name, inputs, recorded):
    """A workspace whose verdicts/ holds one audit verdict plus its inputs."""
    ws = tmp_path
    vd = ws / ".sciforge" / "verdicts"
    vd.mkdir(parents=True, exist_ok=True)
    for rel, content in inputs.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    data = _AUDIT_BASE[name].copy()
    data["audited_input_hashes"] = recorded
    write_json(vd, name, data)
    return vd / name


def test_matching_audit_hashes_pass(tmp_path):
    """S01's shape: every recorded hash matches the file on disk."""
    inputs = {"results/metrics.json": b'{"a":1}\n',
              "paper/main.tex": b"\\documentclass{article}\n"}
    recorded = {rel: _sha(c) for rel, c in inputs.items()}
    path = _ws_with_audit(tmp_path, "PAPER_CLAIM_AUDIT.json", inputs, recorded)
    status, notes = vv.validate_json_file("PAPER_CLAIM_AUDIT.json", path)
    assert status == "PASS", notes


def test_changed_audit_input_fails(tmp_path):
    """ML04's shape: the file was rewritten after the audit certified it."""
    inputs = {"results/metrics.json": b'{"a":1}\n',
              "paper/main.tex": b"\\documentclass{article}\n"}
    recorded = {rel: _sha(c) for rel, c in inputs.items()}
    path = _ws_with_audit(tmp_path, "PAPER_CLAIM_AUDIT.json", inputs, recorded)
    # rewrite one input, exactly as a table regeneration would
    (tmp_path / "results" / "metrics.json").write_bytes(b'{"a":2}\n')
    status, notes = vv.validate_json_file("PAPER_CLAIM_AUDIT.json", path)
    assert status == "FAIL"
    assert any("no longer match disk" in n for n in notes)
    assert any("results/metrics.json" in n for n in notes)
    assert any("cannot be trusted" in n for n in notes)


def test_sha256_prefix_is_normalised(tmp_path):
    """Recorded hashes may carry a `sha256:` prefix; disk hashes do not.

    Comparing them unnormalised reports every healthy run as stale -- which is
    how this check was very nearly shipped.
    """
    inputs = {"results/metrics.json": b'{"a":1}\n'}
    recorded = {"results/metrics.json": "sha256:" + _sha(inputs["results/metrics.json"])}
    path = _ws_with_audit(tmp_path, "PAPER_CLAIM_AUDIT.json", inputs, recorded)
    status, notes = vv.validate_json_file("PAPER_CLAIM_AUDIT.json", path)
    assert status == "PASS", notes
    assert vv._norm_audit_hash("sha256:" + "ab" * 32) == "ab" * 32
    assert vv._norm_audit_hash("AB" * 32) == "ab" * 32


def test_absent_audited_input_is_not_a_violation(tmp_path):
    """The e2e fixture audits two files its trimmed layout does not carry.

    Reporting absence would warn on every run against a healthy, shipped
    workspace (and against any verdicts-only copy), which trains people to
    ignore warnings -- a false positive by the same standard as a wrong FAIL.
    Only a hash that contradicts the bytes on disk is a violation.
    """
    inputs = {"results/metrics.json": b'{"a":1}\n'}
    recorded = {rel: _sha(c) for rel, c in inputs.items()}
    recorded["METHOD_REGISTRY_SNIPPET.md"] = _sha(b"absent\n")
    path = _ws_with_audit(tmp_path, "LEAKAGE_AUDIT.json", inputs, recorded)
    status, notes = vv.validate_json_file("LEAKAGE_AUDIT.json", path)
    assert status == "PASS", notes


def test_changed_input_fails_even_when_another_is_absent(tmp_path):
    """An absent path must not mask a genuinely changed one."""
    inputs = {"results/metrics.json": b'{"a":1}\n'}
    recorded = {rel: _sha(c) for rel, c in inputs.items()}
    recorded["absent.md"] = _sha(b"absent\n")
    path = _ws_with_audit(tmp_path, "PROOF_AUDIT.json", inputs, recorded)
    (tmp_path / "results" / "metrics.json").write_bytes(b'{"a":2}\n')
    status, notes = vv.validate_json_file("PROOF_AUDIT.json", path)
    assert status == "FAIL"
    assert any("no longer match disk" in n for n in notes)
    assert any("results/metrics.json" in n for n in notes)


def test_non_audit_verdicts_are_unaffected(tmp_path):
    """Only the five audit-family artifacts carry audited_input_hashes; a
    verdict without the REGISTRY flag must not gain a hash check.

    Asserted on the helpers directly rather than through validate_json_file,
    because FAIRNESS.json has its own large required-field set that would only
    add noise to what this test is about.
    """
    fair = {"verdict": "PASS", "audited_input_hashes": {"x": "y"}}
    assert vv.post_checks("FAIRNESS.json", fair, ws_root=tmp_path) == []


def test_end_to_end_exit_code_reflects_stale_audit(tmp_path, capsys):
    """Through main(): a stale audit must make the process exit non-zero."""
    inputs = {"results/metrics.json": b'{"a":1}\n'}
    recorded = {rel: _sha(c) for rel, c in inputs.items()}
    _ws_with_audit(tmp_path, "PAPER_CLAIM_AUDIT.json", inputs, recorded)
    (tmp_path / "results" / "metrics.json").write_bytes(b'{"a":2}\n')
    rc = vv.main([str(tmp_path / ".sciforge" / "verdicts")])
    out = capsys.readouterr().out
    assert rc == 1
    assert "PAPER_CLAIM_AUDIT.json" in out
    assert "no longer match disk" in out
