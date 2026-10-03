"""ScientistTwo parity layer tests (v1.7.0).

Covers the six s2 modules, the three gate scripts (via gates.check dispatch),
the review-loop integration inside pipeline._native_review, the exploration
guarantee hook in apply_loopback, and a CPU smoke of bench/s2demo (skipped
when numpy is absent).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if sys.version_info < (3, 10):
    pytest.skip("kernel requires Python >= 3.10", allow_module_level=True)

sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge import gates  # noqa: E402
from sciforge.pipeline import Kernel  # noqa: E402
from sciforge.s2 import ablation, audit, calibration, ideas, ladder, reviewloop  # noqa: E402


# ---------------- ladder ----------------

def test_ladder_three_state_critic():
    assert ladder.decide(0.5, 0.6) == "GOOD"
    assert ladder.decide(0.5, 0.5) == "ENGINEER"   # tie is not a win
    assert ladder.decide(0.6, 0.5) == "BAD"
    assert ladder.decide(0.6, 0.5, "minimize") == "GOOD"
    assert ladder.decide(1.4, 1.5, "minimize") == "BAD"
    # margin: strictly beyond min_gain only
    assert ladder.decide(1.0, 1.001, min_gain=0.1) == "ENGINEER"
    assert ladder.decide(1.0, 1.5, min_gain=0.1) == "GOOD"


def _good_ladder_doc(**over):
    doc = {"schema_version": "1.0", "problem_id": "Q1",
           "metric": {"name": "acc", "direction": "maximize"},
           "subset": {"n": 100, "baseline": {"value": 0.4}, "candidate": {"value": 0.5}},
           "critic": {"state": "GOOD", "engineer_rounds": 0, "rationale": "ok"},
           "fullset": {"n": 400, "verified": True,
                       "baseline": {"value": 0.4}, "candidate": {"value": 0.6}},
           "relative_gain_pct": 50.0}
    doc.update(over)
    return doc


def test_ladder_validate_good_passes():
    assert ladder.validate(_good_ladder_doc()) == []


def test_ladder_validate_rejects_bad_states():
    d = _good_ladder_doc(critic={"state": "GOOD", "engineer_rounds": 3})
    assert any("engineer_rounds" in p for p in ladder.validate(d))

    d = _good_ladder_doc(fullset={"n": 400, "verified": False,
                                  "baseline": {"value": 0.4},
                                  "candidate": {"value": 0.6}})
    assert any("verified" in p for p in ladder.validate(d))

    # full-set tie while claiming GOOD — the subset-fluke class
    d = _good_ladder_doc(fullset={"n": 400, "verified": True,
                                  "baseline": {"value": 0.6},
                                  "candidate": {"value": 0.6}},
                         relative_gain_pct=0.0)
    assert any("does not strictly beat" in p for p in ladder.validate(d))

    # arithmetic tampering
    d = _good_ladder_doc(relative_gain_pct=99.0)
    assert any("arithmetic" in p for p in ladder.validate(d))

    d = _good_ladder()
    d.pop("problem_id")
    assert any("INV-G1" in p for p in ladder.validate(d))


def _good_ladder():
    return _good_ladder_doc()


def test_ladder_evaluate_skip_fail_pass(tmp_path: Path):
    # no experiments, no ladder -> SKIP
    status, doc, probs = ladder.evaluate(tmp_path)
    assert status == "SKIP" and doc is None

    # experiments without ladder -> FAIL
    run = tmp_path / "experiments" / "full" / "e1"
    run.mkdir(parents=True)
    (run / "RESULT.json").write_text('{"status": "PASS"}')
    status, doc, probs = ladder.evaluate(tmp_path)
    assert status == "FAIL" and doc is None and probs

    # ladder present and valid -> PASS
    lad = tmp_path / ".sciforge" / "audits"
    lad.mkdir(parents=True)
    (lad / "S2_LADDER.json").write_text(json.dumps(_good_ladder()))
    status, doc, probs = ladder.evaluate(tmp_path)
    assert status == "PASS" and probs == []


def test_ladder_gate_script_exit_codes(tmp_path: Path):
    r = gates.check(tmp_path, {"check": "command", "cmd": "s2_ladder"}, "6c")
    assert r["status"] == "SKIP"
    run = tmp_path / "experiments" / "full" / "e1"
    run.mkdir(parents=True)
    (run / "RESULT.json").write_text('{"status": "PASS"}')
    r = gates.check(tmp_path, {"check": "command", "cmd": "s2_ladder"}, "6c")
    assert r["status"] == "FAIL"


# ---------------- ideas / exploration guarantee ----------------

def test_rank_and_exploration_mix_forces_unexplored():
    seeds = [{"id": "s1", "novelty": 0.2},
             {"id": "s2", "novelty": 0.9},
             {"id": "s3", "novelty": 0.5}]
    ranked = ideas.rank_seeds(seeds)
    assert [s["id"] for s in ranked] == ["s2", "s3", "s1"]
    pool = ideas.exploration_mix(seeds, {"s2"}, min_new=1)
    # an unexplored seed must lead the pool even when a hotter explored one exists
    assert pool[0]["id"] in ("s1", "s3")
    assert pool[0]["id"] != "s2"


def test_evolution_input_records_guarantee():
    seeds = [{"id": "a", "novelty": 0.9}, {"id": "b", "novelty": 0.4}]
    trace = [{"id": "a", "outcome": "failed", "reason": "no separation"}]
    payload = ideas.evolution_input(seeds, trace, {"a"}, round_index=2)
    assert payload["round"] == 2
    assert "failed" in payload["history_trace"]
    assert any(p["id"] == "b" and p["forced_new"] for p in payload["exploration_pool"])


def test_kernel_loopback_carries_exploration_seed(tmp_path: Path):
    from sciforge.pipeline import PhaseGraph, Verdict
    k = Kernel(tmp_path)
    k.start("Q-EVO", "x", "lite", host="manual")
    # seed candidates with one unexplored
    audits = tmp_path / ".sciforge" / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    (audits / "IDEA_EVOLUTION.json").write_text(json.dumps({
        "schema_version": "1.0",
        "seed_candidates": [{"id": "fresh-seed", "novelty": 0.9},
                            {"id": "stale-seed", "novelty": 0.1}],
        "explored_ids": ["stale-seed"], "rounds": []}))
    lb = {"id": "L3", "on": "FAIL", "target": "3", "budget": 1}
    k.graph.phases["2"]["loopback"] = lb
    target = k.apply_loopback("2", Verdict("FAIL", notes="no survivor"))
    assert target == "3"
    events = [e for e in k.log.replay() if e["kind"] == "loopback"]
    assert events and events[-1]["payload"].get("exploration_seed") == "fresh-seed"
    ledger = (tmp_path / "results" / "KILL_DECISIONS.jsonl").read_text()
    assert '"exploration_seed": "fresh-seed"' in ledger


# ---------------- ablation ----------------

def test_ablcritic_strict_rule():
    assert ablation.ablcritic(1.0, 1.1) == "GOOD"
    assert ablation.ablcritic(1.0, 1.0) == "REFINE"   # tie keeps old state
    assert ablation.ablcritic(1.0, 0.9) == "REFINE"
    assert ablation.ablcritic(None, 0.5) == "GOOD"     # first measurement
    assert ablation.ablcritic(1.1, 1.0, "minimize") == "GOOD"


def _ledger(**over):
    doc = {"schema_version": "1.0", "problem_id": "Q1",
           "metric": {"name": "acc", "direction": "maximize"},
           "plans": [{"id": f"A{i}", "component": f"c{i}", "hypothesis": "h",
                      "metric": "acc", "status": "executed"} for i in range(1, 6)],
           "results": [{"plan": "A1", "prev_value": 1.0, "new_value": 0.4,
                        "decision": "REFINE"}],
           "current_best": 1.0}
    doc.update(over)
    return doc


def test_ablation_validate():
    assert ablation.validate(_ledger()) == []
    # plan count out of range
    assert any("out of range" in p for p in ablation.validate(_ledger(plans=_ledger()["plans"][:3])))
    # decision violating the strict rule
    bad = _ledger(results=[{"plan": "A1", "prev_value": 1.0, "new_value": 0.9,
                            "decision": "GOOD"}])
    assert any("violates the strict rule" in p for p in ablation.validate(bad))
    # monotonicity: current_best regressed below best GOOD
    mono = _ledger(results=[{"plan": "A1", "prev_value": 0.5, "new_value": 0.9,
                             "decision": "GOOD"}], current_best=0.5)
    assert any("monotone" in p for p in ablation.validate(mono))


def test_ablation_gate_script(tmp_path: Path):
    r = gates.check(tmp_path, {"check": "command", "cmd": "s2_ablation"}, "10")
    assert r["status"] == "SKIP"
    run = tmp_path / "experiments" / "full" / "e1"
    run.mkdir(parents=True)
    (run / "RESULT.json").write_text('{"status": "PASS"}')
    r = gates.check(tmp_path, {"check": "command", "cmd": "s2_ablation"}, "10")
    assert r["status"] == "FAIL"
    audits = tmp_path / ".sciforge" / "audits"
    audits.mkdir(parents=True)
    (audits / "ABLATION_LEDGER.json").write_text(json.dumps(_ledger()))
    r = gates.check(tmp_path, {"check": "command", "cmd": "s2_ablation"}, "10")
    assert r["status"] == "PASS"


# ---------------- review loop ----------------

def test_rebuttal_threshold_and_meta_review(monkeypatch):
    monkeypatch.delenv("SCIFORGE_REVIEW_THRESHOLD", raising=False)
    assert reviewloop.threshold() == 8.0
    assert reviewloop.needs_rebuttal(7.9) is True
    assert reviewloop.needs_rebuttal(8.0) is False
    assert reviewloop.needs_rebuttal(None) is False

    meta = reviewloop.meta_review(8.5, {"fatal": []}, 0)
    assert meta["decision"] == "ACCEPT"
    meta = reviewloop.meta_review(7.0, {"fatal": []}, 0)
    assert meta["decision"] == "PENDING_REBUTTAL"
    meta = reviewloop.meta_review(7.0, {"fatal": []}, 2)
    assert meta["decision"] == "REFINE"          # 2 rounds exhausted
    meta = reviewloop.meta_review(9.0, {"fatal": ["x"]}, 0)
    assert meta["decision"] == "REFINE"          # score OK but fatal survives

    # env override (last, so it cannot leak into the meta assertions above)
    monkeypatch.setenv("SCIFORGE_REVIEW_THRESHOLD", "7.0")
    assert reviewloop.threshold() == 7.0
    assert reviewloop.needs_rebuttal(7.5) is False


def test_seed_rebuttal_plan_has_tasks_and_cap():
    panel = {"fatal": ["claim unsupported"], "kill_arguments": ["baseline missing"]}
    plan = reviewloop.seed_rebuttal_plan(panel, 6.5, round_no=1)
    assert plan["max_rounds"] == reviewloop.MAX_REBUTTAL_ROUNDS
    assert len(plan["tasks"]) == 2
    assert {t["source"] for t in plan["tasks"]} == {"fatal", "kill_argument"}
    empty = reviewloop.seed_rebuttal_plan({"fatal": [], "kill_arguments": []}, 5.0)
    assert empty["tasks"][0]["source"] == "score_gap"


# ---------------- calibration ----------------

def test_calibration_fit_and_apply():
    doc = calibration.fit([
        {"id": "p1", "panel_score": 5.0, "reference_score": 4.0},
        {"id": "p2", "panel_score": 7.0, "reference_score": 6.5},
        {"id": "p3", "panel_score": 6.0, "reference_score": 5.2},
    ])
    assert doc["usable"] is True and doc["n"] == 3
    cal = calibration.apply(doc, 6.0)
    assert 0.0 <= cal <= 10.0 and abs(cal - 5.25) < 0.35

    # degenerate: anti-correlated anchors -> identity fallback, flagged
    bad = calibration.fit([
        {"id": "p1", "panel_score": 5.0, "reference_score": 8.0},
        {"id": "p2", "panel_score": 7.0, "reference_score": 4.0},
    ])
    assert bad["usable"] is False
    assert calibration.apply(bad, 6.6) == 6.6      # never silently rescale

    # single anchor -> identity, unusable
    one = calibration.fit([{"id": "p1", "panel_score": 5.0, "reference_score": 6.2}])
    assert one["usable"] is False


def test_calibration_roundtrip_persistence(tmp_path: Path):
    doc = calibration.fit([{"id": "a", "panel_score": 4.0, "reference_score": 3.0},
                           {"id": "b", "panel_score": 8.0, "reference_score": 7.0}])
    calibration.save(tmp_path, doc)
    loaded = calibration.load(tmp_path)
    assert loaded and loaded["usable"]
    score, cdoc = calibration.calibrate(tmp_path, 6.0)
    assert cdoc and score is not None


# ---------------- audit ----------------

def _audit_ws(tmp_path: Path) -> Path:
    run = tmp_path / "experiments" / "full" / "e1"
    run.mkdir(parents=True)
    (run / "RESULT.json").write_text(json.dumps({"status": "PASS"}))
    audits = tmp_path / ".sciforge" / "audits"
    audits.mkdir(parents=True)
    (audits / "S2_LADDER.json").write_text(json.dumps(_good_ladder()))
    (tmp_path / ".sciforge" / "verdicts").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sciforge" / "verdicts" / "EVALUATION_PROTOCOL.json").write_text(
        json.dumps({"split": "held-out test, seed 0"}))
    return tmp_path


def test_audit_gain_arithmetic_and_split(tmp_path: Path):
    ws = _audit_ws(tmp_path)
    hacking = audit.reward_hacking_scan(ws)
    assert hacking["checks"]["gain_arithmetic"]["status"] == "PASS"
    assert hacking["checks"]["split_discipline"]["status"] == "PASS"
    # tamper with the stated gain
    lad = json.loads((ws / ".sciforge" / "audits" / "S2_LADDER.json").read_text())
    lad["relative_gain_pct"] = 499.0
    (ws / ".sciforge" / "audits" / "S2_LADDER.json").write_text(json.dumps(lad))
    assert audit.reward_hacking_scan(ws)["checks"]["gain_arithmetic"]["status"] == "FAIL"


def test_audit_method_code_parity(tmp_path: Path):
    ws = _audit_ws(tmp_path)
    (ws / "src").mkdir()
    (ws / "src" / "impl.py").write_text(
        "def gradient_accumulation_step(x):\n    return x\n")
    (ws / "methods").mkdir()
    (ws / "methods" / "METHOD_REGISTRY.md").write_text(
        "Method: we call `gradient_accumulation_step` every batch and then "
        "a `mystery_nonexistent_widget` for calibration.")
    rep = audit.method_code_parity(ws)
    assert rep["status"] == "FAIL"                 # 1/2 tokens matched < 0.8
    assert "mystery_nonexistent_widget" in rep["unmatched"]
    # add the missing symbol -> PASS
    (ws / "src" / "impl.py").write_text(
        "def gradient_accumulation_step(x):\n    return x\n"
        "def mystery_nonexistent_widget():\n    pass\n")
    rep = audit.method_code_parity(ws)
    assert rep["status"] == "PASS" and rep["ratio"] >= 0.8


def test_audit_full_run_writes_trail(tmp_path: Path):
    ws = _audit_ws(tmp_path)
    doc = audit.run_full_audit(ws)
    assert doc["overall"] == "PASS"
    trail = json.loads((ws / ".sciforge" / "audits" / "AUDIT_TRAIL.json").read_text())
    assert trail["overall"] == "PASS"


def test_wrap_up_gates_include_s2_audit(tmp_path: Path):
    # no experiments at all => s2 audit SKIPs, wrap-up not blocked by it
    (tmp_path / ".sciforge").mkdir()
    r = gates.wrap_up_gates(tmp_path)
    assert r["checks"]["s2_completeness_audit"]["status"] == "SKIP"


# ---------------- native review integration ----------------

def test_native_review_writes_rebuttal_and_meta(tmp_path: Path, monkeypatch):
    k = Kernel(tmp_path)
    k.start("B8S2", "x", "lite", host="manual")

    class StubP:
        host_mode = False

        def complete(self, role, system, prompt, **kw):
            class U:
                def as_dict(self):
                    return {}
            return ('{"scores": {"main_experiment_logic": 6}, "overall": 7.0, '
                    '"fatal": ["claim X unsupported"], "kill_arguments": [], '
                    '"summary": "s"}', U())

    monkeypatch.setattr(k, "providers", lambda: StubP())
    monkeypatch.delenv("SCIFORGE_REVIEW_THRESHOLD", raising=False)
    k.rs.data["current_phase"] = "14"
    v = k._native_review()
    assert v.v in ("PASS", "WARN", "FAIL")

    panel = json.loads((tmp_path / ".sciforge" / "audits" / "REVIEW_PANEL.json").read_text())
    assert panel["rebuttal_required"] is True          # 7.0 < 8.0
    assert panel["rebuttal_threshold"] == 8.0
    assert panel["meta_review"]["decision"] in ("PENDING_REBUTTAL", "REFINE")
    plan = json.loads((tmp_path / ".sciforge" / "audits" / "REBUTTAL_PLAN.json").read_text())
    assert plan["round"] == 1 and plan["tasks"]

    rs = json.loads((tmp_path / ".sciforge" / "verdicts" / "REVIEW_STATE.json").read_text())
    assert rs["rebuttal_required"] is True
    assert rs["meta_review"]["decision"] in ("PENDING_REBUTTAL", "REFINE")
    assert rs["last_score"] == 7.0


def test_native_review_accept_above_threshold(tmp_path: Path, monkeypatch):
    k = Kernel(tmp_path)
    k.start("B8S2B", "x", "lite", host="manual")

    class StubP:
        host_mode = False

        def complete(self, role, system, prompt, **kw):
            class U:
                def as_dict(self):
                    return {}
            return ('{"scores": {"soundness": 8}, "overall": 8.4, "fatal": [], '
                    '"kill_arguments": [], "summary": "ok"}', U())

    monkeypatch.setattr(k, "providers", lambda: StubP())
    k.rs.data["current_phase"] = "14"
    v = k._native_review()
    panel = json.loads((tmp_path / ".sciforge" / "audits" / "REVIEW_PANEL.json").read_text())
    assert panel["rebuttal_required"] is False
    assert panel["meta_review"]["decision"] == "ACCEPT"
    assert not (tmp_path / ".sciforge" / "audits" / "REBUTTAL_PLAN.json").exists()


# ---------------- bench smoke ----------------

def test_bench_discovers_four_tasks():
    bench = REPO_ROOT / "bench" / "s2demo"
    tasks = sorted(p.parent.name for p in (bench / "tasks").glob("*/task.py"))
    assert len(tasks) == 4
    assert any(t.startswith("T1") for t in tasks)


def test_bench_all_tasks_promoted(tmp_path: Path):
    pytest.importorskip("numpy", reason="bench requires numpy")
    import importlib.util

    run_py = REPO_ROOT / "bench" / "s2demo" / "run.py"
    spec = importlib.util.spec_from_file_location("s2bench_run", run_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for task_dir in mod.discover_tasks():
        rep = mod.run_task(task_dir, None, tmp_path)
        assert rep["ladder_valid"], f"{task_dir.name}: {rep['ladder_problems']}"
        assert rep["verdict"] == "PROMOTED", (
            f"{task_dir.name} not promoted: {rep['splits']}")
        assert rep["relative_gain_pct"] > 0
        # reports written
        stem = f"{task_dir.name}__candidate"
        assert (tmp_path / f"{stem}.report.json").exists()
        assert (tmp_path / f"{stem}.S2_LADDER.json").exists()
        # the written ladder validates against the production validator
        doc = json.loads((tmp_path / f"{stem}.S2_LADDER.json").read_text())
        assert ladder.validate(doc) == []


# ---------------- v1.7.1 hardening: discipline tiers, monitor D2, hygiene,
# ---------------- figure style, strict DOI ----------------

def test_monitor_d2_prose_no_longer_flags(tmp_path: Path):
    from sciforge.s2 import monitor
    prose = ("# evaluate on the held-out split\n"
             "assert coverage > 0.9  # held-out leg only\n")
    assert monitor.scan_code(prose, ["main"]) == []
    # identifier/path forms still flag
    bad = 'p = Path(HOLDOUT_DIR) / "held_out" / "scores.json"\n'
    assert any(v["desiderata"] == "D2" for v in monitor.scan_code(bad, ["main"]))
    bad2 = 'with open("/eval_private/main.json") as f: ...\n'
    assert any(v["desiderata"] == "D2" for v in monitor.scan_code(bad2, ["main"]))


def test_discipline_tiers_and_compile_warnings(tmp_path: Path):
    from sciforge import gates as g
    (tmp_path / ".sciforge" / "verdicts").mkdir(parents=True)
    (tmp_path / ".sciforge" / "RUNSTATE.json").write_text(json.dumps(
        {"data": {"flags": {"discipline": "lean"}}}))
    assert g.discipline(tmp_path) == "lean"
    assert g.cosmetic_hard(tmp_path) is False
    (tmp_path / ".sciforge" / "verdicts" / "PAPER_COMPILE.json").write_text(
        json.dumps({"status": "PASS", "warnings": 3}))
    r = g.check(tmp_path, {"check": "command", "cmd": "compile_audit"}, "13")
    assert r["status"] == "PASS" and r.get("warnings_disclosed") == 3
    # strict keeps warnings hard
    (tmp_path / ".sciforge" / "RUNSTATE.json").write_text(json.dumps(
        {"data": {"flags": {"discipline": "strict"}}}))
    r = g.check(tmp_path, {"check": "command", "cmd": "compile_audit"}, "13")
    assert r["status"] == "FAIL"


def test_workspace_hygiene_gate(tmp_path: Path):
    (tmp_path / ".sciforge").mkdir()
    (tmp_path / "compile_attempt3.log").write_text("x")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / "README.md").write_text("# idx")
    r = gates.check(tmp_path, {"check": "command", "cmd": "workspace_hygiene"}, "16")
    assert r["status"] == "FAIL"
    (tmp_path / "compile_attempt3.log").unlink()
    (tmp_path / "src" / "__pycache__").rmdir()
    (tmp_path / "src" / "run.py").write_text("# code")  # no empty dirs left
    r = gates.check(tmp_path, {"check": "command", "cmd": "workspace_hygiene"}, "16")
    assert r["status"] == "PASS"


def test_figure_style_gate(tmp_path: Path):
    paper = tmp_path / "paper"
    paper.mkdir()
    # figure float BEFORE its first citation => FAIL
    (paper / "main.tex").write_text(
        "\\begin{figure}\\includegraphics{figures/a/output.pdf}"
        "\\label{fig:a}\\end{figure}\nSee \\ref{fig:a} later.\n"
        "\\includegraphics{figures/b/preview.png}\n")
    (tmp_path / "figures").mkdir()
    import subprocess as _sp
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "figure_style_gate.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 2 and "BEFORE" in p.stdout and "raster" in p.stdout
    # fixed: citation first, vector only, 3 recipe kinds
    (paper / "main.tex").write_text(
        "As shown in \\ref{fig:a}, ...\n"
        "\\begin{figure}\\includegraphics{figures/a/output.pdf}"
        "\\label{fig:a}\\end{figure}\n")
    for kind in ("bar-grouped", "line-comparison", "scatter-fit"):
        d = tmp_path / "figures" / kind
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.recipe.json").write_text(json.dumps({"recipe": kind}))
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "figure_style_gate.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout


def test_doi_gate_structure(tmp_path: Path):
    lit = tmp_path / "literature"
    lit.mkdir()
    (lit / "references.bib").write_text(
        "@article{a2024, title={Something Real}, doi={10.1000/xyz}, }\n"
        "@article{b2024, title={No Doi Here}, }\n")
    import subprocess as _sp
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "doi_gate.py"),
                 str(tmp_path), "--offline"], capture_output=True, text=True)
    assert p.returncode == 2 and "missing DOI" in p.stdout
    (lit / "references.bib").write_text(
        "@article{a2024, title={Something Real}, doi={10.1000/xyz}, }\n"
        "@book{c1990, title={Classical}, no_doi_classical={yes}, }\n")
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "doi_gate.py"),
                 str(tmp_path), "--offline"], capture_output=True, text=True)
    assert p.returncode == 0 and "classical no-DOI" in p.stdout
    # DOI-free venue (JMLR) with official url + declaration is honest; arXiv
    # without a DOI is NOT (arXiv mints 10.48550 DOIs)
    (lit / "references.bib").write_text(
        "@article{j2011, title={Sklearn}, url={https://jmlr.org/papers/v12/x.html}, }\n")
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "doi_gate.py"),
                 str(tmp_path), "--offline"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
    (lit / "references.bib").write_text(
        "@article{arx2024, title={Preprint}, url={https://arxiv.org/abs/2401.00001}, }\n")
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "doi_gate.py"),
                 str(tmp_path), "--offline"], capture_output=True, text=True)
    assert p.returncode == 2 and "missing DOI" in p.stdout


# ---------------- v1.7.1 P1: completion gate, sota driver, memory wiring ----------------

def test_completion_gate_catches_lying_report(tmp_path: Path):
    import subprocess as _sp
    (tmp_path / ".sciforge" / "verdicts").mkdir(parents=True)
    (tmp_path / ".sciforge" / "RUNSTATE.json").write_text(
        json.dumps({"status": "running", "current_phase": "10"}))
    (tmp_path / ".sciforge" / "verdicts" / "PIPELINE_VERDICT_SUMMARY.md").write_text(
        "All phases complete. Paper at paper/main.pdf (18 pages).")
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "completion_gate.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 2 and "missing on disk" in p.stdout


def test_sota_driver_promotes_and_plateaus(tmp_path: Path):
    from sciforge import sota
    (tmp_path / ".sciforge" / "verdicts").mkdir(parents=True)
    (tmp_path / ".sciforge" / "verdicts" / "SOTA_TARGET.json").write_text(json.dumps({
        "problem": "t", "direction": "maximize",
        "benchmarks": [{"name": "acc", "baseline": 0.36, "optimum": 1.0}],
        "budget": {"max_iterations": 4, "plateau_rounds": 2}}))
    r1 = sota.record_iteration(tmp_path, "v1", {"acc": {"score": 0.9, "ci": [0.88, 0.92]}})
    assert r1["promoted"] and r1["closed"]["acc"] > 0.8
    r2 = sota.record_iteration(tmp_path, "v2", {"acc": {"score": 0.5, "ci": [0.48, 0.52]}})
    assert not r2["promoted"]
    st = sota.status(tmp_path)
    assert st["plateau"] == 1 and st["best"]["variant"] == "v1"
    # regression gate: significant drop invalidates even a positive headline leg
    r3 = sota.record_iteration(tmp_path, "v3",
                               {"acc": {"score": 0.2, "ci": [0.19, 0.21]}})
    assert not r3["valid"] and any("regression_gate" in x for x in r3["invalid_reasons"])


def test_memory_index_uses_readable_fields(tmp_path: Path):
    from sciforge import memory as mem
    run = tmp_path / "R1"
    (run / "output").mkdir(parents=True)
    (run / "output" / "LESSONS.json").write_text(json.dumps({
        "run_id": "R1",
        "code_errors": [{"error": "take_along_axis axis bug on (m,1,n)",
                         "fix": "squeeze before indexing",
                         "lesson": "smoke gate catches shape defects"}]}))
    n = mem.build_index(tmp_path, tmp_path / "idx.jsonl")
    assert n == 1
    hits = mem.query(tmp_path / "idx.jsonl", "shape defect caught by smoke gate", k=1)
    assert hits and "smoke gate" in hits[0]["text"]


def test_submission_ready_tiering(tmp_path: Path):
    import subprocess as _sp
    # minimal NOT_READY: no pdf, no verdicts
    (tmp_path / ".sciforge").mkdir()
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "submission_ready.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 2 and "NOT_READY" in p.stdout


# ---------------- v1.7.2: nodes/fork, claim anchors, semantic memory,
# ---------------- batch sota, REP, sources ----------------

def test_nodes_fork_and_anchor_drift(tmp_path: Path):
    from sciforge import nodes as nd
    src = tmp_path / "runA"
    (src / "src").mkdir(parents=True)
    (src / "src" / "exp.py").write_text("print(1)\n")
    (src / "experiments").mkdir(parents=True)
    (src / "experiments" / "RESULT.json").write_text('{"v": 1}')
    n = nd.record_node(src, kind="full", phase="6c",
                       code=[src / "src" / "exp.py"],
                       inputs=[src / "experiments"],
                       outputs=[src / "experiments" / "RESULT.json"],
                       reexec_cmd="python src/exp.py", claim_ids=["C1"])
    assert n["id"] == "n001" and n["outputs_sha"]
    nd.anchor_claims(src, [{"claim_id": "C1", "node_id": "n001",
                            "tex_file": "paper/main.tex", "line": 10,
                            "resolved": True, "evidence_refs": []}])
    assert nd.verify_anchors(src) == []
    # drift: result edited after anchoring => anchor invalid
    (src / "experiments" / "RESULT.json").write_text('{"v": 2}')
    assert any("drifted" in p for p in nd.verify_anchors(src))
    # fork seeds a new workspace at the node's phase with reexec hook
    out = tmp_path / "runB"
    r = nd.fork(src, "n001", out)
    assert r["ok"] and r["resume_phase"] == "6c"
    assert (out / "experiments" / "RESULT.json").exists()
    rs = json.loads((out / ".sciforge" / "RUNSTATE.json").read_text())
    assert rs["data"]["forked_from"]["node"] == "n001"


def test_semantic_memory_harvests_positive_claims(tmp_path: Path):
    from sciforge import memory as mem
    run = tmp_path / "R1"
    (run / ".sciforge" / "audits").mkdir(parents=True)
    (run / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md").write_text(
        "## C1 — fidelity numerical — polarity positive — to: abstract\n"
        "linear family ceiling 0.645 on generator G at full split.\n\n"
        "## C2 — fidelity numerical — polarity negative — to: none\n"
        "this failed idea must NOT become a fact.\n")
    facts = mem.harvest_facts(run)
    assert len(facts) == 1 and facts[0]["claim_id"] == "C1"
    assert facts[0]["hash"].startswith("sha256:")
    n = mem.build_semantic_index(tmp_path, tmp_path / "facts.jsonl")
    assert n == 1
    hits = mem.query_facts(tmp_path / "facts.jsonl", "linear ceiling generator", k=1)
    assert hits and "0.645" in hits[0]["text"]


def test_sota_batch_returns_k_distinct_priors(tmp_path: Path):
    from sciforge import sota
    (tmp_path / ".sciforge" / "verdicts").mkdir(parents=True)
    (tmp_path / ".sciforge" / "verdicts" / "SOTA_TARGET.json").write_text(json.dumps({
        "problem": "p", "benchmarks": [{"name": "m", "baseline": 0.0, "optimum": 1.0}]}))
    batch = sota.next_variants(tmp_path, "p", k=3)
    assert len(batch) == 3
    assert [b["batch_index"] for b in batch] == [0, 1, 2]


def test_rep_compile_and_offplan_loopback(tmp_path: Path):
    from sciforge import rep
    from sciforge.pipeline import PhaseGraph
    g = PhaseGraph()
    r = rep.compile_rep(tmp_path, g)
    assert any(o["phase"] == "6c" for o in r["objectives"])
    assert "2" in r["fallbacks"]  # L3 loopback declared on phase 2
    assert rep.check_plan(tmp_path)["status"] == "PASS"
    fb = rep.fallback_consumed(tmp_path, "2", "L3")
    assert fb["status"] == "PASS"
    off = rep.fallback_consumed(tmp_path, "99", "LX")
    assert off["status"] == "FAIL" and "OFF-PLAN" in off["note"]


def test_sources_poll_dedup(tmp_path: Path):
    from sciforge import sources as src
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"id": "t1", "topic": "problem one"}\n'
                      '{"id": "t2", "topic": "problem two"}\n')
    reg = [{"id": "bench", "kind": "jsonl", "path": str(topics),
            "fields": {"problem": "topic", "id": "id"}, "poll_s": 0, "seen": []}]
    src.save_registry(tmp_path, reg)
    new, updated = src.poll_all(tmp_path)
    assert len(new) == 2
    new2, _ = src.poll_all(tmp_path)   # second poll: dedup by seen
    assert new2 == []


# ---------------- v1.7.2 adversarial-review fixes ----------------

def test_auto_register_production_nodes(tmp_path: Path):
    from sciforge import nodes as nd
    exp = tmp_path / "experiments" / "full" / "e1"
    exp.mkdir(parents=True)
    (exp / "RESULT.json").write_text('{"status": "PASS"}')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "run.py").write_text("x")
    regs = nd.auto_register(tmp_path, phase="6c")
    assert len(regs) == 1
    assert regs[0]["outputs_sha"] and regs[0]["reexec_cmd"]
    # idempotent: second call registers nothing new
    assert nd.auto_register(tmp_path, phase="6c") == []


def test_auto_anchor_claims_matches_cited_artifacts(tmp_path: Path):
    from sciforge import nodes as nd
    exp = tmp_path / "experiments" / "full" / "e1"
    exp.mkdir(parents=True)
    (exp / "RESULT.json").write_text('{"status": "PASS"}')
    nd.auto_register(tmp_path, phase="10")
    audits = tmp_path / ".sciforge" / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    (audits / "CLAIMS_FROM_RESULTS.md").write_text(
        "## C1 — fidelity numerical — polarity positive — to: abstract\n"
        "accuracy 0.99 measured in experiments/full/e1/RESULT.json.\n\n"
        "## C2 — fidelity numerical — polarity negative — to: none\n"
        "failed arm.\n")
    anchors = nd.auto_anchor_claims(tmp_path)
    assert len(anchors) == 1 and anchors[0]["claim_id"] == "C1"
    assert anchors[0]["resolved"] is True
    assert nd.verify_anchors(tmp_path) == []


def test_claim_anchor_gate_strict_citation_forms(tmp_path: Path):
    import subprocess as _sp
    exp = tmp_path / "experiments" / "full" / "e1"
    exp.mkdir(parents=True)
    (exp / "RESULT.json").write_text('{"status": "PASS"}')
    from sciforge import nodes as nd
    nd.auto_register(tmp_path, phase="10")
    (tmp_path / ".sciforge" / "audits").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md").write_text(
        "## C1 — fidelity numerical — polarity positive — to: abstract\n"
        "in experiments/full/e1/RESULT.json.\n")
    nd.auto_anchor_claims(tmp_path)
    (tmp_path / "paper").mkdir()
    # figure-panel letter "C1 panel" must NOT count as a claim citation:
    # with EMPTY anchors it would FAIL if the regex over-counted C1
    nd.anchor_claims(tmp_path, [])
    (tmp_path / "paper" / "main.tex").write_text("Figure shows C1 panel at top.\n")
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "claim_anchor_gate.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 0, f"bare C1 panel must not be a citation: {p.stdout}"
    # real anchor citation resolves
    nd.auto_anchor_claims(tmp_path)
    (tmp_path / "paper" / "main.tex").write_text("As established in (C1), ...\n")
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "claim_anchor_gate.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 0 and "PASS" in p.stdout
    # cited but unanchored -> FAIL
    nd.anchor_claims(tmp_path, [])
    p = _sp.run([sys.executable, str(REPO_ROOT / "scripts" / "claim_anchor_gate.py"),
                 str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 2 and "not anchored" in p.stdout


def test_rep_lives_outside_verdicts_dir(tmp_path: Path):
    from sciforge import rep
    from sciforge.pipeline import PhaseGraph
    r = rep.compile_rep(tmp_path, PhaseGraph())
    assert (tmp_path / ".sciforge" / "audits" / "REP.json").exists()
    assert not (tmp_path / ".sciforge" / "verdicts" / "REP.json").exists()
    assert r["discipline"] in ("strict", "balanced", "lean")


def test_gates_discipline_default_is_strict(tmp_path: Path):
    from sciforge import gates
    (tmp_path / ".sciforge").mkdir()
    assert gates.discipline(tmp_path) == "strict"
    (tmp_path / ".sciforge" / "RUNSTATE.json").write_text(
        json.dumps({"data": {"flags": {"discipline": "lean"}}}))
    assert gates.discipline(tmp_path) == "lean"
