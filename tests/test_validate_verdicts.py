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
