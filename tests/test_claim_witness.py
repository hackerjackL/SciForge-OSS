"""Tests for scripts/claim_witness.py — the universal-claim witness gate.

Why this exists: three ARC-Bench runs shipped manuscripts whose machine-readable
artifacts were exact and whose PROSE overclaimed. ML18 asserted "the standard
deviation over replicates never exceeds a third of the pooled gap in any cell"
when 11 of 36 exceed it, and "the ordering of the four conditions is unchanged
across the whole range" when its own Table 5 shows them swapping. Q07 asserted
"every trained model covers all ten classes" while one cell predicts 9. No grep
can catch these: the claims are number-free relational assertions whose numbers
live in LaTeX macros, and a regex over "all/every/never" has ~25% precision —
it fires on design statements that are true by construction.

So the gate does not judge the prose. It enumerates candidates and requires the
host to register a witness for each, then re-derives that witness from the
artifact. The design rests on one observation: an agent that writes a false
universal does not know it is false, so it registers the claim honestly with
expected=true — and the re-derivation refutes it.

These tests pin that mechanism, plus the two shapes it must NOT get wrong: a
true claim must pass, and an unregistered candidate must WARN rather than FAIL
(the gate's recall is broad on purpose, and punishing it would fail healthy
runs).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (REPO_ROOT / "scripts", REPO_ROOT / "kernel"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import claim_witness as cw          # noqa: E402


# ---------------------------------------------------------------------------
# workspace builders
# ---------------------------------------------------------------------------

def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "Q001"
    (ws / "paper" / "sections").mkdir(parents=True)
    (ws / "results").mkdir(parents=True)
    (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    return ws


def _section(ws: Path, name: str, text: str) -> None:
    (ws / "paper" / "sections" / name).write_text(text, encoding="utf-8")


def _artifact(ws: Path, rel: str, doc) -> None:
    p = ws / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding="utf-8")


def _witness(ws: Path, sentence: str, **fields) -> None:
    entry = {"sha256": cw._sha(sentence), "kind": "empirical"}
    entry.update(fields)
    path = ws / ".sciforge" / "verdicts" / "CLAIM_WITNESS.json"
    doc = {"witnesses": [entry]}
    path.write_text(json.dumps(doc), encoding="utf-8")


# ---------------------------------------------------------------------------
# candidate enumeration
# ---------------------------------------------------------------------------

def test_candidates_come_from_empirical_sections_only(tmp_path):
    """A protocol statement in the method must not become a candidate."""
    ws = _ws(tmp_path)
    _section(ws, "3_method.tex",
             "Every condition is evaluated on identical stratified splits and "
             "the same fitted base model, so the comparison is paired.")
    _section(ws, "5_results.tex",
             "The ordering of the four conditions is unchanged across the "
             "whole range of bin counts examined here.")
    cands = cw._prose(ws)
    assert len(cands) == 1, cands
    assert cands[0][0] == "5_results.tex"


def test_generated_tables_are_not_scanned(tmp_path):
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex", "plain prose without any universal claim here.")
    _section(ws, "tab3_body.tex", "all cells exceed every threshold by 1.0\\\\")
    _section(ws, "numbers.tex", "\\newcommand{\\AllCells}{all cells exceed}\n")
    assert cw._prose(ws) == []


# ---------------------------------------------------------------------------
# the path resolver — real artifacts need all three selector shapes
# ---------------------------------------------------------------------------

def test_resolver_handles_nested_dict_fanout():
    doc = {"cells": {"a": {"conditions": {"x": {"ece_std": 1.0},
                                          "y": {"ece_std": 2.0}}},
                     "b": {"conditions": {"x": {"ece_std": 3.0}}}}}
    got = cw._numbers(cw._resolve(doc, "cells[*].conditions[*].ece_std"))
    assert got == [1.0, 2.0, 3.0], got


def test_resolver_handles_prefix_selection_over_flattened_keys():
    """binning_table flattens condition and bin count into one key."""
    doc = {"binning_table": {"platt__b10": 0.038, "temperature__b10": 0.041,
                             "platt__b15": 0.047, "temperature__b15": 0.044}}
    assert cw._numbers(cw._resolve(doc, "binning_table[platt__*]")) == \
        [0.038, 0.047]
    assert cw._numbers(cw._resolve(doc, "binning_table[temperature__*]")) == \
        [0.041, 0.044]


def test_resolver_returns_none_for_a_missing_path():
    assert cw._resolve({"a": 1}, "nope") is None
    assert cw._resolve({"a": {"b": 1}}, "a.c") is None


# ---------------------------------------------------------------------------
# the mechanism: an honest false registration is refuted
# ---------------------------------------------------------------------------

def test_false_universal_is_refuted(tmp_path):
    """The ML18 shape: the agent believes "negative at every size" and registers
    it; the data contain one positive value."""
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering against Platt scaling is negative at every sample "
             "size examined in the calibration-size sweep here.")
    _artifact(ws, "results/metrics.json", {
        "calibration_size_table": {
            "wine__svm__n100": {"isotonic_minus_platt": -0.0007},
            "wine__svm__n50": {"isotonic_minus_platt": 0.0023},
            "wine__svm__n25": {"isotonic_minus_platt": -0.0094}}})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/metrics.json",
             field="calibration_size_table[*].isotonic_minus_platt",
             check="all_negative", expected=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc
    assert doc["refuted"] == 1
    assert any("refuted by its own evidence" in f for f in doc["failures"])


def test_true_universal_is_verified(tmp_path):
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering against Platt scaling is negative at every sample "
             "size examined in the calibration-size sweep here.")
    _artifact(ws, "results/metrics.json", {
        "calibration_size_table": {
            "wine__svm__n100": {"isotonic_minus_platt": -0.0007},
            "wine__svm__n50": {"isotonic_minus_platt": -0.0023},
            "wine__svm__n25": {"isotonic_minus_platt": -0.0094}}})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/metrics.json",
             field="calibration_size_table[*].isotonic_minus_platt",
             check="all_negative", expected=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "PASS", doc
    assert doc["verified"] == 1


def test_two_field_ratio_claim_is_refuted(tmp_path):
    """"std never exceeds a third of the gap" is a per-element ratio, not a
    single scalar bound."""
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The dispersion across replicates never exceeds a third of the "
             "pooled gap in any of the evaluated cells here.")
    _artifact(ws, "results/metrics.json", {"cells": {
        "a": {"conditions": {"p": {"ece_std": 0.001, "ece_mean": 0.05}}},
        "b": {"conditions": {"p": {"ece_std": 0.077, "ece_mean": 0.05}}}}})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/metrics.json",
             field="cells[*].conditions[*].ece_std",
             field_b="cells[*].conditions[*].ece_mean",
             check="all_le_ratio", expected=1 / 3)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc
    assert doc["refuted"] == 1


def test_two_field_sign_change_is_refuted(tmp_path):
    """"the ordering is unchanged" — the difference must not change sign."""
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering of the four conditions is unchanged across the "
             "whole range of bin counts examined here.")
    _artifact(ws, "results/metrics.json", {"binning_table": {
        "platt__b10": 0.0384, "temperature__b10": 0.0407,
        "platt__b15": 0.0474, "temperature__b15": 0.0438}})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/metrics.json",
             field="binning_table[platt__*]",
             field_b="binning_table[temperature__*]",
             check="diff_all_negative", expected=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc


def test_glob_artifact_spans_groups(tmp_path):
    """"every trained model" spans one RESULT.json per group; picking one file
    would let the false group escape unregistered."""
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The predicted-class histogram of every trained model covers all "
             "ten classes in the evaluation split here.")
    for g, vals in (("mps_chi8", [10, 10]), ("mps_chi16", [10, 9])):
        _artifact(ws, f"experiments/full/{g}/RESULT.json", {
            "cells": [{"n_distinct_predicted_classes": v} for v in vals]})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="experiments/full/*/RESULT.json",
             field="cells[*].n_distinct_predicted_classes",
             check="min_ge", expected=10)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc
    assert doc["refuted"] == 1


# ---------------------------------------------------------------------------
# what must NOT fail
# ---------------------------------------------------------------------------

def test_unregistered_candidate_warns_not_fails(tmp_path):
    """The gate's recall is broad on purpose; a claim nobody registered is
    unverifiable, not false."""
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering of the four conditions is unchanged across the "
             "whole range of bin counts examined here.")
    doc = cw.check(ws)
    assert doc["verdict"] == "WARN", doc
    assert doc["unregistered"] == 1
    assert doc["refuted"] == 0


def test_protocol_disposition_needs_no_verification(tmp_path):
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "Every reported quantity remains a deterministic optimum of the "
             "programme and none is sampled anywhere here.")
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, kind="protocol", note="design statement")
    doc = cw.check(ws)
    assert doc["verdict"] == "PASS", doc
    assert doc["protocol"] == 1


def test_witness_pointing_at_a_missing_artifact_fails(tmp_path):
    """A witness that cannot be checked is not a pass."""
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering of the four conditions is unchanged across the "
             "whole range of bin counts examined here.")
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/nonexistent.json",
             field="x", check="all_negative", expected=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc


def test_unsupported_check_is_a_failure_not_a_pass(tmp_path):
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering of the four conditions is unchanged across the "
             "whole range of bin counts examined here.")
    _artifact(ws, "results/metrics.json", {"a": [1, 2, 3]})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/metrics.json", field="a",
             check="vibrates_appropriately", expected=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc
    assert any("not in the supported vocabulary" in f for f in doc["failures"])


def test_mismatched_two_field_lengths_fail(tmp_path):
    ws = _ws(tmp_path)
    _section(ws, "5_results.tex",
             "The ordering of the four conditions is unchanged across the "
             "whole range of bin counts examined here.")
    _artifact(ws, "results/metrics.json", {
        "binning_table": {"platt__b10": 0.038, "platt__b15": 0.047,
                          "temperature__b10": 0.041}})
    sentence = cw._prose(ws)[0][1]
    _witness(ws, sentence, artifact="results/metrics.json",
             field="binning_table[platt__*]",
             field_b="binning_table[temperature__*]",
             check="diff_all_negative", expected=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "FAIL", doc
    assert any("correspond element-wise" in f for f in doc["failures"])


def test_no_paper_means_no_candidates(tmp_path):
    ws = tmp_path / "empty"
    (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    doc = cw.check(ws)
    assert doc["verdict"] == "PASS", doc
    assert doc["candidates"] == 0
