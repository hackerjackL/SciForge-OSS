"""ARC-Bench rubric scorer (v1.8.0 evaluation).

Three agents self-assessing in prose give three incomparable answers. This
scorer turns per-leaf verdicts into one auditable number. The properties that
matter: weights come from the official rubric (an assessor cannot inflate its
score), `partial` is not rounded up, and must_pass artifact requirements are
reported separately rather than averaged into the rubric percentage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import bench_score as bs  # noqa: E402


def _run(tmp_path: Path, weights=(40.0, 30.0, 30.0), must_pass=True) -> Path:
    run = tmp_path / "T01"
    b = run / "results" / "benchmark"
    b.mkdir(parents=True)
    leaves = [{"id": f"leaf{i}", "weight": w, "requirements": f"req {i}",
               "task_category": "Code Development" if i == 0 else "Result Analysis"}
              for i, w in enumerate(weights)]
    rubric = {"id": "root", "weight": 1,
              "sub_tasks": [{"id": "grp", "weight": 1, "sub_tasks": leaves}]}
    (b / "ARC_RUBRIC.json").write_text(json.dumps(rubric))
    task = {"id": "T01", "domain": "ml", "requirements": json.dumps([
        {"id": "req_results_json", "must_pass": must_pass, "description": "canonical results"},
        {"id": "req_hypotheses_supported_flags", "must_pass": True, "description": "flags"},
        {"id": "req_optional_figure", "must_pass": False, "description": "figure"},
    ])}
    (b / "ARC_TASK.json").write_text(json.dumps(task))
    return run


def _results(run: Path, *, details="coverage 0.9482 at n=100 with MC SE 0.0031 across five seeds") -> None:
    (run / "results.json").write_text(json.dumps({
        "primary_metric": 0.9482, "metric_key": "primary_metric",
        "metrics": {"a": 0.9, "b": 0.8},
        "hypotheses": {h: {"supported": True, "details": details}
                       for h in ("h1", "h2", "h3")},
        "summary": "a summary",
    }))


# ---------------------------------------------------------------------------
# weights come from the rubric, not the assessor
# ---------------------------------------------------------------------------
def test_weights_are_taken_from_rubric_not_assessment(tmp_path):
    run = _run(tmp_path)
    a = {"leaf0": {"verdict": "met", "weight": 999},   # assessor tries to inflate
         "leaf1": {"verdict": "met"}, "leaf2": {"verdict": "met"}}
    res = bs.score(run, a)
    assert res["total_weight"] == 100.0
    assert res["score_pct"] == 100.0


def test_partial_earns_half_not_full(tmp_path):
    run = _run(tmp_path)
    res = bs.score(run, {"leaf0": {"verdict": "partial"},
                         "leaf1": {"verdict": "met"},
                         "leaf2": {"verdict": "met"}})
    assert res["earned_weight"] == 80.0     # 20 + 30 + 30
    assert res["score_pct"] == 80.0


def test_missing_leaf_counts_as_unmet(tmp_path):
    run = _run(tmp_path)
    res = bs.score(run, {"leaf0": {"verdict": "met"}})
    assert res["score_pct"] == 40.0


def test_unknown_verdict_is_unmet_not_crash(tmp_path):
    run = _run(tmp_path)
    res = bs.score(run, {"leaf0": {"verdict": "probably-fine"}})
    assert res["leaves"][0]["verdict"] == "unmet"
    assert res["score_pct"] == 0.0


def test_weights_need_not_sum_to_one_hundred(tmp_path):
    """Measured on the real rubrics: Q05 sums to 82 and B01 to 105. The score
    must normalise by the actual total, not assume 100."""
    run = _run(tmp_path, weights=(41.0, 41.0))      # total 82
    res = bs.score(run, {"leaf0": {"verdict": "met"}, "leaf1": {"verdict": "met"}})
    assert res["total_weight"] == 82.0
    assert res["score_pct"] == 100.0


def test_leaf_extraction_flattens_nested_tree(tmp_path):
    run = _run(tmp_path)
    assert len(bs.leaves(bs.load_rubric(run))) == 3


# ---------------------------------------------------------------------------
# must_pass is reported separately, never averaged into the rubric score
# ---------------------------------------------------------------------------
def test_must_pass_missing_results_is_unmet_even_with_full_rubric(tmp_path):
    run = _run(tmp_path)                     # no results.json written
    res = bs.score(run, {f"leaf{i}": {"verdict": "met"} for i in range(3)})
    assert res["score_pct"] == 100.0         # rubric can be perfect
    hard = {r["id"]: r["status"] for r in res["must_pass"]}
    assert hard["req_results_json"] == "unmet"   # while a hard requirement fails


def test_hypothesis_details_need_a_number(tmp_path):
    run = _run(tmp_path)
    _results(run, details="the robust target clearly improves coverage stability")
    res = bs.score(run, {})
    h = next(r for r in res["must_pass"] if r["id"] == "req_hypotheses_supported_flags")
    assert h["status"] == "unmet"
    assert "no_number" in h["detail"]


def test_hypothesis_details_need_forty_chars(tmp_path):
    run = _run(tmp_path)
    _results(run, details="cov 0.95")
    res = bs.score(run, {})
    h = next(r for r in res["must_pass"] if r["id"] == "req_hypotheses_supported_flags")
    assert h["status"] == "unmet"
    assert "details<40" in h["detail"]


def test_valid_results_pass_both_hard_checks(tmp_path):
    run = _run(tmp_path)
    _results(run)
    res = bs.score(run, {})
    assert all(r["status"] == "met" for r in res["must_pass"])


def test_optional_requirements_are_not_reported_as_hard(tmp_path):
    run = _run(tmp_path)
    _results(run)
    ids = {r["id"] for r in bs.score(run, {})["must_pass"]}
    assert "req_optional_figure" not in ids


def test_unverifiable_requirement_is_unchecked_not_passed(tmp_path):
    """Anything needing judgement must not silently read as satisfied."""
    run = _run(tmp_path)
    b = run / "results" / "benchmark"
    task = json.loads((b / "ARC_TASK.json").read_text())
    task["requirements"] = json.dumps([
        {"id": "req_width_tradeoff_writeup", "must_pass": True, "description": "prose"}])
    (b / "ARC_TASK.json").write_text(json.dumps(task))
    _results(run)
    r = bs.score(run, {})["must_pass"][0]
    assert r["status"] == "unchecked"


def test_by_category_aggregates(tmp_path):
    run = _run(tmp_path)
    res = bs.score(run, {"leaf0": {"verdict": "met"},
                         "leaf1": {"verdict": "unmet"},
                         "leaf2": {"verdict": "met"}})
    assert res["by_category"]["Code Development"]["pct"] == 100.0
    assert res["by_category"]["Result Analysis"]["pct"] == 50.0


def test_template_lists_every_leaf(tmp_path):
    run = _run(tmp_path)
    tpl = bs.template(run)
    assert set(tpl) == {"leaf0", "leaf1", "leaf2"}
    assert all(v["verdict"] == "unmet" for v in tpl.values())