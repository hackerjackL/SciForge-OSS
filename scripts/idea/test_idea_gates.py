#!/usr/bin/env python3
"""Unit tests for SciForge-OSS P1 (failed-ideas memory) + P2 (Type-A gate).

Run: python -m pytest scripts/idea/test_idea_gates.py -v
     (or: python3 scripts/idea/test_idea_gates.py  — pytest-free runner)
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from failed_ideas_memory import add_idea, check_idea, prompt_injection  # noqa: E402
from type_a_gate import run_type_a  # noqa: E402


# --------------------------------------------------------------------------- #
# P1 — failed-ideas memory
# --------------------------------------------------------------------------- #
def test_p1_add_and_check_reject():
    with tempfile.TemporaryDirectory() as td:
        corpus = os.path.join(td, "failed_ideas.json")
        add_idea("IDEALSM1", "use label smoothing on small MLP to reduce overfitting",
                 "toy gate failed", corpus)
        r = check_idea("use label smoothing on small MLP to reduce overfitting (reworded variant)",
                       corpus, threshold=0.78)
        assert r["verdict"] == "REJECT", r
        assert r["similarity"] > 0.78, r


def test_p1_unrelated_passes():
    with tempfile.TemporaryDirectory() as td:
        corpus = os.path.join(td, "failed_ideas.json")
        add_idea("IDEALSM1", "use label smoothing on small MLP to reduce overfitting",
                 "toy gate failed", corpus)
        r = check_idea("causal inference with instrumental variables on panel data",
                       corpus, threshold=0.78)
        assert r["verdict"] == "PASS", r


def test_p1_prompt_injection_contains_banner():
    with tempfile.TemporaryDirectory() as td:
        corpus = os.path.join(td, "failed_ideas.json")
        add_idea("IDEALSM1", "use label smoothing on small MLP", "toy failed", corpus)
        inj = prompt_injection("generate new idea", 5, corpus)
        assert "[failed-ideas prompt injection]" in inj


# --------------------------------------------------------------------------- #
# P2 — Type-A objective hard gate (0 LLM cost)
# --------------------------------------------------------------------------- #
def test_p2_ok_idea_passes():
    idea = {"id": "I1", "requires_gpu_gb": 8.0,
            "requires_packages": ["numpy", "json"],
            "data_required": True, "data_sources": ["local:data/"],
            "code_snippet": "import numpy as np\nprint(np.array([1]))"}
    r = run_type_a(idea, gpu_total_gb=24.0)
    assert r["verdict"] == "PASS", r
    assert r["llm_cost"] == 0


def test_p2_bad_idea_fails_all_checks():
    idea = {"id": "I2", "requires_gpu_gb": 96.0,
            "requires_packages": ["torch", "nonexistent_pkg_xyz"],
            "data_required": True, "data_sources": [],
            "code_snippet": "def broken(:\n    pass"}
    r = run_type_a(idea, gpu_total_gb=24.0)
    assert r["verdict"] == "FAIL", r
    assert "gpu_oom_estimated" in r["fail_reasons"]
    assert "missing_data_source" in r["fail_reasons"]
    assert "missing_dependency" in r["fail_reasons"]
    assert "code_syntax_error" in r["fail_reasons"]


def test_p2_zero_llm_cost_always():
    idea = {"id": "I3", "requires_gpu_gb": 0, "requires_packages": [],
            "data_required": False, "data_sources": [],
            "code_snippet": "x = 1"}
    r = run_type_a(idea)
    assert r["llm_cost"] == 0


# --------------------------------------------------------------------------- #
# pytest-free runner
# --------------------------------------------------------------------------- #
def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
