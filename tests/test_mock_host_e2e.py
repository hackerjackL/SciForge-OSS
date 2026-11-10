"""End-to-end state-machine harness for the 26-node DAG (v1.7.3).

``tests/test_e2e_smoke.py`` validates the STRUCTURE of a finished run; it never
executes the kernel's state machine, so loopbacks (L1-L13 budgets), gate
rejection retries, checkpoints, crash recovery and the v1.7.2 mechanism
boundaries had no automated end-to-end coverage.

This module drives the REAL ``Kernel`` through all 26 phases with a **scripted
mock host** (``Kernel._dispatch_mock`` — no LLM, no subprocess host). The mock
host writes the artifacts a phase would produce and returns the verdict a host
would return; every kernel gate, boundary, loopback and recovery path is the
production code. The artifact "canned answers" reuse the checked-in
``fixtures/e2e_minimal`` verdict set (the canonical complete trail), patched
where a run-specific value is required (route, review score, evidence hashes).

Covered:
  1. happy path 0 -> 16 under the hybrid route (all 26 nodes), completed
     status, ``validate_verdicts --strict --require-complete`` and the full
     wrap-up battery PASS;
  2. loopback L1 (phase 2.5) rewinds to phase 2, the budget is counted from
     ``events.ndjson`` (a fresh Kernel sees the same count), exhaustion blocks
     the run, and each loopback consumed its REP-declared fallback;
  3. a persistently failing boundary gate is retried exactly 3 rounds and then
     blocks (``unresolved_<phase>_gate``) — regression for the v1.7.3 counter
     fix (the cap previously never incremented);
  4. process death: ``recover()`` replays the log, reports the dangling
     boundary, and the run resumes at the exact phase (no re-run of committed
     boundaries);
  5. v1.7.2 mechanisms are really produced: NODES.json (hash-stable nodes),
     CLAIM_ANCHORS.json (resolved claim -> node), REP.json (plan + fallback
     contract), and the kernel-side quarantine of gate telemetry files.

Run: ``.venv/bin/python -m pytest tests/test_mock_host_e2e.py -q``
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if sys.version_info < (3, 10):
    pytest.skip("kernel requires Python >= 3.10 (X | Y syntax)", allow_module_level=True)

sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge import gates, nodes, rep, state  # noqa: E402
from sciforge.pipeline import Kernel  # noqa: E402

FIXTURE = REPO_ROOT / "fixtures" / "e2e_minimal"
FIXTURE_VERDICTS = FIXTURE / ".sciforge" / "verdicts"
TOY_SRC = (FIXTURE / "toy_experiment" / "run_toy.py").read_text()
PHASE_IDS = [p["id"] for p in json.loads(
    (REPO_ROOT / "kernel" / "config" / "phasegraph.json").read_text())["phases"]]

RUN_ID = "MOCK-Q001"
PROBLEM = ("Does the sample mean have lower sampling variance than the sample "
           "median for n=21 i.i.d. N(0,1) draws?")
OFFLINE_ENV = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_BASE_URL",
               "OPENAI_BASE_URL", "SCIFORGE_MODEL")


def _offline_env(mp: pytest.MonkeyPatch) -> None:
    """Force Providers() into host_mode so no gate can reach the network.

    The integrity monitor (6b/6c) is fail-closed on its optional LLM tier; a
    developer machine with API keys would otherwise make this harness
    environment-dependent (observed: HTTP 404 => REJECT => boundary blocked).
    """
    for key in OFFLINE_ENV:
        mp.delenv(key, raising=False)


class HostModeProviders:
    host_mode = True


def _verdict(name: str, **patch) -> dict:
    doc = json.loads((FIXTURE_VERDICTS / name).read_text())
    doc.update(patch)
    return doc


_H = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
SPLIT_HASH = _H("mock-data-split-v1")

# The 6c smoke gate re-executes the declared slice inside the sandbox, so the
# harness has to ship a real script that really runs — a smoke record with no
# script behind it proves nothing and the gate now fails it (v1.7.3
# positive-evidence rule). `--max-steps` keeps the re-run bounded.
SMOKE_SCRIPT = 'import sys\nprint("smoke slice ok", sys.argv[1:])\n'
SMOKE_SCRIPT_SHA = _H(SMOKE_SCRIPT)

METHOD_MD = """# Method registry — MOCK-Q001

## Section 3 — Method Selection (locked)

Estimator X is the sample mean and estimator Y is the sample median. The study
uses n = 21, three fixed seeds, and 400 Monte Carlo trials per seed. The
decision rule requires the variance of the mean to be lower than the variance
of the median per seed and pooled.

LOCKED — post-approval this section is immutable.
"""

GAP_MD = """# Gap report — MOCK-Q001

## GAP-1
Smith 2023 reports that the small-sample variance ordering remains untested at
n = 21; no study measured the ratio at this sample size. [@smith2023]

## GAP-2
Doe 2024 finds inconsistent rankings for n < 30; the discrepancy cannot be
explained by the asymptotic approximation. [@doe2024]
"""

CLAIMS_MD = """# Claims from results — MOCK-Q001

## C1 — variance ordering (polarity positive)
The sample mean has lower sampling variance than the sample median on every
seed; evidence: experiments/toy/main/RESULT.json and
experiments/full/RESULT.json (pooled ratio 0.637).

## C2 — heavy-tail behaviour (polarity negative)
The heavy-tail variant was not established; recorded as a limitation only.
"""


def _result(stage: str) -> dict:
    return {
        "experiment_id": f"mock_{stage}",
        "stage": stage,
        "status": "PASS",
        "core_claim_tested": "sample mean variance below sample median variance",
        "core_claim_validated": True,
        "result_summary": {"primary_metric": {
            "metric_name": "variance_ratio", "metric_value": 0.637,
            "threshold": "< 1.0", "passed": True}},
        "metrics": {"variance_ratio": 0.637},
        "group": "main",
        "seeds": [42, 43, 44],
        "data_split_hash": SPLIT_HASH,
        "duration_seconds": 0.2,
        "seeds_used": 3,
        "recommendation": "PROCEED_TO_FULL",
    }


# Component ablation ledger: 5 plans + a monotone AblCritic ledger (minimize).
ABLATION = {
    "schema_version": "1.0", "problem_id": RUN_ID,
    "metric": {"name": "error", "direction": "minimize"},
    "plans": [{"id": f"A{i}", "component": f"component{i}",
               "hypothesis": "removal hurts", "metric": "error",
               "status": "executed"} for i in range(1, 6)],
    "results": [{"plan": f"A{i}", "prev_value": p, "new_value": n,
                 "decision": "GOOD"}
                for i, (p, n) in enumerate(
                    [(0.90, 0.80), (0.80, 0.78), (0.78, 0.76),
                     (0.76, 0.74), (0.74, 0.72)], start=1)],
    "current_best": 0.72,
}

# Subset->full ladder: GOOD only on strict full-set improvement.
LADDER = {
    "schema_version": "1.0", "problem_id": RUN_ID,
    "metric": {"name": "variance_ratio", "direction": "minimize"},
    "subset": {"baseline": {"value": 1.0}, "candidate": {"value": 0.70}},
    "fullset": {"baseline": {"value": 1.0}, "candidate": {"value": 0.637},
                "verified": True},
    "critic": {"state": "GOOD", "engineer_rounds": 0},
    "relative_gain_pct": 36.3,
}

PDF = ("%PDF-1.4\n"
       "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
       "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 5 >>\nendobj\n"
       "%%EOF\n")

FIG_KINDS = ("bar-grouped", "line-comparison", "scatter-fit",
             "bar-grouped", "line-comparison", "scatter-fit", "bar-grouped")

PAPER = r"""\documentclass{article}
\title{Sampling Variance of the Mean and the Median at Small Sample Size}
\author{Anonymous}
\begin{document}
\maketitle

\begin{abstract}
We compare two estimators of the population mean of a Gaussian distribution at
sample size $n=21$: the sample mean and the sample median. Across $3$ fixed
seeds and $400$ Monte Carlo trials per seed, the empirical variance of the mean
is $0.637$ times the variance of the median, inside the known-answer band
around $2/\pi \approx 0.637$. The per-seed ratio stays below $1.0$ in all $3$
cases, with pooled values of $0.641$, $0.635$, and $0.636$. A closed-form check
gives $1/21 \approx 0.0476$ for the variance of the mean and $(\pi/2)/21
\approx 0.0748$ for the asymptotic variance of the median. These $8$ quantities
agree with the Monte Carlo direction and bound the claim to the stated regime.
The comparison is deliberately narrow: one sample size, one distributional
family, and one decision rule fixed before execution. We report every seed
separately rather than only the pooled average, so the direction of the effect
can be checked without aggregation. The closed forms are used only as a sanity
band around $2/\pi \approx 0.637$, not as a substitute for the simulation.
Within this regime the ordering is stable, the empirical spread is small, and
the analytic and simulated ratios agree to within $0.006$ in absolute value.
\end{abstract}

\section{Introduction}
The sample mean and the sample median are classical estimators of location.
We ask whether the mean has lower sampling variance at $n=21$ under Gaussian
sampling. Table~\ref{tab:main} summarises the design, and Claim (C1) records
the tested statement. Figure~\ref{fig:f1} shows the sampling schematic.

\section{Related Work}
Standard asymptotic theory gives the variance of the mean and the variance of
the median for Gaussian data. We use those closed forms only as a sanity band.

\section{Method}
We draw independent samples and compute both estimators on every trial. The
decision rule compares variances per seed and pooled. Figure~\ref{fig:f2}
shows the flow, Figure~\ref{fig:f3} the estimator geometry, Figure~\ref{fig:f4}
the trial schedule, Figure~\ref{fig:f5} the seed layout, Figure~\ref{fig:f6}
the variance decomposition, and Figure~\ref{fig:f7} the ratio band.
Table~\ref{tab:main} lists the constants.

\section{Experimental Setup}
Each seed contributes $400$ trials with $n=21$ draws. All constants are fixed
before execution.

\section{Results}
The empirical ratio remains below one on every seed. Table~\ref{tab:main}
reports the per-seed values and the pooled estimate.

\section{Conclusion}
Within the stated regime, the mean has lower sampling variance than the median
at this sample size.

\begin{table}
\caption{Constants and pooled ratio.}\label{tab:main}
\begin{tabular}{ll}
seeds & 3 \\
trials & 400 \\
\end{tabular}
\end{table}

\begin{figure}
\includegraphics{figures/f1/output}
\caption{Sampling schematic.}\label{fig:f1}
\end{figure}
\begin{figure}
\includegraphics{figures/f2/output}
\caption{Estimator flow.}\label{fig:f2}
\end{figure}
\begin{figure}
\includegraphics{figures/f3/output}
\caption{Estimator geometry.}\label{fig:f3}
\end{figure}
\begin{figure}
\includegraphics{figures/f4/output}
\caption{Trial schedule.}\label{fig:f4}
\end{figure}
\begin{figure}
\includegraphics{figures/f5/output}
\caption{Seed layout.}\label{fig:f5}
\end{figure}
\begin{figure}
\includegraphics{figures/f6/output}
\caption{Variance decomposition.}\label{fig:f6}
\end{figure}
\begin{figure}
\includegraphics{figures/f7/output}
\caption{Ratio band.}\label{fig:f7}
\end{figure}

\section*{References}
Classical treatments of order statistics and location estimators.

\section*{Data and Code Availability}
The generator and the analysis script accompany this manuscript as
released source files.

\section*{Funding}
This work received no external funding.

\end{document}
"""


def _figure_files() -> dict:
    out = {}
    for i, kind in enumerate(FIG_KINDS, start=1):
        out[f"figures/f{i}/output.pdf"] = PDF
        out[f"figures/f{i}/figure_audit.json"] = {"verdict": "PASS"}
        out[f"figures/f{i}/latex_include.tex"] = (
            f"\\includegraphics{{figures/f{i}/output}}\n")
        out[f"figures/f{i}/spec.recipe.json"] = {"recipe": kind}
    return out


def scenario() -> dict:
    """Phase -> fake-host response (verdict + artifacts the phase produces).

    Files are written BEFORE the boundary gates run, so every gate sees the
    real artifact shape it would see from a host agent.
    """
    return {
        "1a": {"verdict": "PASS", "files": {
            ".sciforge/refine-logs/domain-signature.json": {
                "domain_profile": {"evidence_type": "empirical"},
                "methodology_profile": {
                    "suggested_verification_type": "theory+experiment"}}}},
        "1b": {"verdict": "PASS", "files": {
            "literature/GAP_REPORT.md": GAP_MD,
            ".sciforge/refine-logs/FINAL_PROPOSAL.json": {
                "verification_type": "theory+experiment",
                "assumptions": [
                    {"text": "i.i.d. Gaussian sampling", "reasonability": 8},
                    {"text": "variance estimated from 400 trials",
                     "reasonability": 7}]}}},
        "4broad": {"verdict": "PASS"},
        "2": {"verdict": "PASS"},
        "2.5": {"verdict": "PASS", "files": {
            ".sciforge/refine-logs/FALSIFICATION_RECORD.json": {
                "counterexamples": [{"id": "c1", "result": "survived"}],
                "overall_outcome": "SURVIVE"}}},
        "2.5b": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/KILL_ARGUMENT.json": _verdict("KILL_ARGUMENT.json"),
            ".sciforge/verdicts/BLINDSPOT_CHECK.json":
                _verdict("BLINDSPOT_CHECK.json")}},
        "3": {"verdict": "PASS"},
        "4targeted": {"verdict": "PASS"},
        "5": {"verdict": "PASS", "files": {
            "methods/METHOD_REGISTRY.md": METHOD_MD,
            ".sciforge/verdicts/REGISTRY_HASH.txt": _H(METHOD_MD) + "\n"}},
        "6a": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/PROOF_AUDIT.json": _verdict("PROOF_AUDIT.json"),
            "derivations/derivation_output.md":
                "# Derivation\n\n"
                "Var(mean) = sigma^2/n; Var(median) ~ (pi/2) sigma^2/n.\n"}},
        "6b": {"verdict": "PASS", "files": {
            "experiments/toy/main/RESULT.json": _result("toy"),
            "src/run_toy.py": TOY_SRC,
            ".sciforge/verdicts/EXPERIMENT_MATRIX.json":
                _verdict("EXPERIMENT_MATRIX.json"),
            ".sciforge/verdicts/EVALUATION_PROTOCOL.json":
                _verdict("EVALUATION_PROTOCOL.json")}},
        "6c": {"verdict": "PASS", "files": {
            "experiments/full/run_full.py": SMOKE_SCRIPT,
            "experiments/full/RESULT.json": _result("full"),
            "experiments/full/STATUS.json": {
                "state": "done", "budget_floor": {"satisfied": True},
                "group": "baseline_analytic", "seeds": [42, 43, 44],
                "data_split_hash": SPLIT_HASH, "duration_seconds": 0.1},
            "experiments/full/full.SMOKE.json": {
                "experiment_id": "full", "smoke_scale": "1-step",
                "smoke_result": "PASS", "fail_code": None, "fix_attempts": 0,
                "status_row_written": True,
                "script": "experiments/full/run_full.py",
                "script_sha256": SMOKE_SCRIPT_SHA,
                "smoke_args": ["--max-steps", "1"],
                "executed_at": "2026-11-11T00:00:00Z", "duration_seconds": 1},
            ".sciforge/audits/S2_LADDER.json": LADDER,
            ".sciforge/verdicts/BUDGET_FLOOR.json":
                _verdict("BUDGET_FLOOR.json")}},
        "7": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/LEAKAGE_AUDIT.json":
                _verdict("LEAKAGE_AUDIT.json")}},
        "8": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/LOGIC_VERIFICATION.json":
                _verdict("LOGIC_VERIFICATION.json")}},
        "10": {"verdict": "PASS", "files": {
            ".sciforge/audits/CLAIMS_FROM_RESULTS.md": CLAIMS_MD,
            ".sciforge/audits/ABLATION_LEDGER.json": ABLATION}},
        "11": {"verdict": "PASS", "files": {
            "paper/main.tex": PAPER,
            ".sciforge/verdicts/FIGURE_AUDITS.json":
                _verdict("FIGURE_AUDITS.json"),
            **_figure_files()}},
        "12": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/QUALITY_GATE.json":
                _verdict("QUALITY_GATE.json"),
            ".sciforge/verdicts/PAPER_CLAIM_AUDIT.json":
                _verdict("PAPER_CLAIM_AUDIT.json")}},
        "13": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/PAPER_COMPILE.json":
                _verdict("PAPER_COMPILE.json"),
            "paper/main.pdf": PDF,
            "paper/appendix.pdf": PDF}},
        "14": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/REVIEW_STATE.json":
                _verdict("REVIEW_STATE.json", last_score=8.2),
            ".sciforge/verdicts/REVIEW_LEDGER.json":
                _verdict("REVIEW_LEDGER.json"),
            ".sciforge/verdicts/EVALUATION_REVIEW.json":
                _verdict("EVALUATION_REVIEW.json")}},
        "15": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/CITATION_AUDIT.json":
                _verdict("CITATION_AUDIT.json")}},
        "15.5": {"verdict": "PASS", "files": {
            ".sciforge/verdicts/PUBLISHABILITY_SCORE.json":
                _verdict("PUBLISHABILITY_SCORE.json"),
            "methods/FAIRNESS_LEDGER.json": {"comparisons": [{
                "table_id": "main", "methods": ["ours", "baseline"],
                "seed_count": 3, "mean_std_reported": True,
                "effect_size_reported": True, "ci_reported": True,
                "multiple_comparison_control": "bh",
                "budget_unit": "s",
                "budget_per_method": {"ours": "1s", "baseline": "1s"},
                "group_per_method": {"ours": "main",
                                     "baseline": "baseline_analytic"},
                "split_hash_per_method": {"ours": SPLIT_HASH,
                                          "baseline": SPLIT_HASH},
                "hparam_budget_per_method": {"ours": 10, "baseline": 10},
                "metric_definitions": {"ours": "ratio",
                                       "baseline": "ratio"}}]},
            "remove": [".sciforge/verdicts/DOI_GATE.json"]}},
    }


def _install_script(ws: Path, script: dict) -> Path:
    hostdir = ws / ".sciforge" / "host"
    hostdir.mkdir(parents=True, exist_ok=True)
    path = hostdir / "mock_script.json"
    path.write_text(json.dumps(script, indent=1))
    return path


def _start(ws: Path, **flags) -> Kernel:
    k = Kernel(ws)
    k.start(RUN_ID, PROBLEM, "lite", host="mock", human_skip=True, **flags)
    k._providers = HostModeProviders()  # phase 14 must not take a native panel
    return k


@pytest.fixture(scope="module")
def happy_run(tmp_path_factory):
    """One full 0 -> 16 run under the hybrid route, shared read-only."""
    mp = pytest.MonkeyPatch()
    _offline_env(mp)
    try:
        ws = tmp_path_factory.mktemp("mock-happy")
        k = _start(ws)
        _install_script(ws, scenario())
        result = k.run(max_steps=200)
        yield ws, k, result
    finally:
        mp.undo()


def test_happy_path_completes_every_phase(happy_run):
    ws, k, result = happy_run
    assert result["status"] == "done" and result["phase"] == "16"
    assert k.rs.status == "completed"
    events = k.log.replay()
    committed = [e["payload"]["phase"] for e in events
                 if e["kind"] == "boundary_committed"]
    assert sorted(committed) == sorted(PHASE_IDS)
    assert len(committed) == 26 and len(set(committed)) == 26
    assert not [e for e in events if e["kind"] in ("gate_rejected", "loopback",
                                                   "blocked")]
    # the run-level human_skip flag must hold for BOTH checkpoints (idea-pick
    # at 3 and method-approval at 5); the second one used to block because the
    # flag was only consulted while no approval log existed.
    log = (ws / ".sciforge" / "APPROVAL_LOG.txt").read_text()
    assert "checkpoint=idea-pick human_skip=True" in log
    assert "checkpoint=method-approval human_skip=True" in log


def test_wrap_up_gates_pass_on_completed_run(happy_run):
    ws, k, _ = happy_run
    validation = gates.validate_verdicts(ws, strict=True, require_complete=True)
    assert validation["status"] == "PASS", validation["output"][-2000:]
    cli = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_verdicts.py"),
         str(ws / ".sciforge" / "verdicts"), "--strict", "--require-complete"],
        capture_output=True, text=True)
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert "24 pass, 0 fail, 0 warn, 0 pending, 0 na" in cli.stdout
    wrap = gates.wrap_up_gates(ws)
    assert wrap["status"] == "PASS", json.dumps(wrap, indent=1)[-3000:]
    for name, check in wrap["checks"].items():
        assert check["status"] in ("PASS", "SKIP"), (name, check)
    assert wrap["checks"]["completion_truth"]["status"] == "PASS"
    assert wrap["checks"]["claim_anchors"]["status"] == "PASS"
    assert wrap["checks"]["figures"]["status"] == "PASS"


def test_v172_mechanisms_are_really_executed(happy_run):
    ws, k, _ = happy_run
    vd = ws / ".sciforge" / "verdicts"

    # D1: every experiment RESULT.json became a hash-stable node.
    registry = nodes.load(ws)
    assert len(registry["nodes"]) == 2
    for node in registry["nodes"]:
        assert re.fullmatch(r"n\d{3}", node["id"])
        assert node["reexec_cmd"]
        assert node["status"] == "pass"
        assert node["outputs_sha"]
        for rel, sha in node["outputs_sha"].items():
            assert nodes.sha256_file(ws / rel) == sha, f"node output drifted: {rel}"
    registered = [e["payload"] for e in k.log.replay()
                  if e["kind"] == "nodes_registered"]
    assert any(p["n"] >= 1 for p in registered)

    # D5: claims anchored at phase 10, and the anchor still resolves.
    anchors = nodes.load_anchors(ws)
    assert anchors and all(a["resolved"] is True for a in anchors)
    assert anchors[0]["claim_id"] == "C1"
    assert nodes.verify_anchors(ws) == []
    assert any(p["anchored"] >= 1 for p in registered)

    # D4: phase 1 compiled the plan; loopback fallbacks are declared.
    plan = rep.check_plan(ws)
    assert plan["status"] == "PASS"
    assert plan["objectives"] == 26
    assert rep.fallback_consumed(ws, "2.5", "L1")["status"] == "PASS"
    # off-plan recovery is a contract violation, not a silent pass
    assert rep.fallback_consumed(ws, "1b", "L1")["status"] == "FAIL"

    # kernel-produced mechanism verdicts are present and registered
    for name in ("INVARIANT_CHECK.json", "LEAKAGE_SCRUB.json",
                 "FAIRNESS.json", "RUN_BUDGET.json"):
        assert (vd / name).exists(), name

    # Gate telemetry must not poison the strict verdicts/ dir: the kernel
    # quarantines the two unregistered files the gate scripts emit.
    assert not (vd / "DOI_GATE.json").exists()
    assert not (vd / "SUBMISSION_READY.json").exists()
    audits = ws / ".sciforge" / "audits"
    assert (audits / "DOI_GATE.json").exists()
    assert (audits / "SUBMISSION_READY.json").exists()


def test_loopback_budget_is_counted_from_the_event_log(tmp_path, monkeypatch):
    _offline_env(monkeypatch)
    ws = tmp_path / "loopback"
    k = _start(ws)
    _install_script(ws, {"*": {"verdict": "PASS"},
                         "2.5": {"verdict": "FAIL"}})
    (ws / "literature").mkdir()
    (ws / "literature" / "GAP_REPORT.md").write_text(GAP_MD)

    result = k.run(max_steps=80)
    events = k.log.replay()
    loopbacks = [e for e in events if e["kind"] == "loopback"]
    assert [e["payload"]["round"] for e in loopbacks] == [1, 2, 3]
    assert all(e["payload"]["id"] == "L1" for e in loopbacks)
    assert all(e["payload"]["target"] == "2" for e in loopbacks)
    # each fired loopback matched a REP-declared fallback condition
    assert all(e["payload"]["rep_fallback"] == "PASS" for e in loopbacks)
    assert k._round_count("L1") == 3
    assert result["status"] == "blocked" and result["reason"] == "loopback exhausted"
    assert k.rs.status == "paused_blocked"
    assert k.rs.data["reason_code"] == "unresolved_2.5_fail"
    assert any(e["kind"] == "loopback_exhausted" for e in events)
    # the budget is reconstructed from events.ndjson, never from process memory
    assert Kernel(ws)._round_count("L1") == 3
    # decision-level provenance survives the block
    ledger = ws / "results" / "KILL_DECISIONS.jsonl"
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(records) == 3 and all(r["loopback"] == "L1" for r in records)
    assert [r["budget_left"] for r in records] == [2, 1, 0]


def test_gate_rejection_blocks_after_three_retry_rounds(tmp_path, monkeypatch):
    _offline_env(monkeypatch)
    ws = tmp_path / "gatecap"
    k = _start(ws)
    _install_script(ws, {"*": {"verdict": "PASS"}})
    assert k.step()["status"] == "advanced"  # 0 -> 1
    assert k.step()["status"] == "advanced"  # 1 -> 1a
    # Jump to phase 2 WITHOUT literature/GAP_REPORT.md: its file gate must fail.
    k.rs.update(phase="2")
    k.rs.write()
    results = [k.step() for _ in range(4)]
    assert [r["status"] for r in results] == [
        "gate_fail", "gate_fail", "gate_fail", "blocked"]
    assert results[-1]["reason"] == "gate 3-round cap"
    assert k.rs.status == "paused_blocked"
    assert k.rs.data["reason_code"] == "unresolved_2_gate"
    events = k.log.replay()
    retries = [e for e in events if e["kind"] == "gate_retry"]
    assert [e["payload"]["round"] for e in retries] == [1, 2, 3]
    rejected = [e for e in events if e["kind"] == "gate_rejected"]
    assert len(rejected) == 4
    failed = [g["gate"] for e in rejected for g in e["payload"]["failed"]]
    assert any("GAP_REPORT" in name for name in failed)
    # the cap is also reconstructed from the log (crash-safe)
    assert Kernel(ws)._gate_retry_count("2") == 3


def test_crash_recovery_resumes_at_the_exact_boundary(tmp_path, monkeypatch):
    _offline_env(monkeypatch)
    ws = tmp_path / "crash"
    k = _start(ws)
    _install_script(ws, scenario())
    for _ in range(4):
        assert k.step()["status"] == "advanced"
    assert k.rs.data["current_phase"] == "4broad"

    # Simulate process death mid-phase, with an uncommitted (dangling) boundary.
    k.log.emit("4broad", "phase_done", {"phase": "4broad", "verdict": "PASS"})
    state.release_lock(ws)

    k2 = Kernel(ws)
    k2._providers = HostModeProviders()
    k2.start(RUN_ID, PROBLEM, "lite", host="mock", human_skip=True)
    recovered = [e for e in k2.log.replay() if e["kind"] == "recovered"]
    assert recovered, "recover() must record the crash replay"
    assert recovered[-1]["payload"]["dangling_boundaries"] == ["4broad"]
    assert k2.rs.data["current_phase"] == "4broad"

    assert k2.run(max_steps=100)["status"] == "done"
    assert k2.rs.status == "completed"
    committed = [e["payload"]["phase"] for e in k2.log.replay()
                 if e["kind"] == "boundary_committed"]
    assert sorted(committed) == sorted(PHASE_IDS)
    assert len(committed) == 26 and len(set(committed)) == 26
    # exact continuation: no already-committed phase is re-entered after the
    # recovery marker, and the first phase entered is the crash point.
    seen_recovery = False
    reentered = []
    for event in k2.log.replay():
        if event["kind"] == "recovered":
            seen_recovery = True
        elif seen_recovery and event["kind"] == "phase_entered":
            reentered.append(event["phase"])
    assert reentered[0] == "4broad"
    assert not ({"0", "1", "1a", "1b"} & set(reentered))


def test_mock_adapter_rejects_path_escape(tmp_path, monkeypatch):
    _offline_env(monkeypatch)
    ws = tmp_path / "escape"
    k = _start(ws)
    _install_script(ws, {"*": {"verdict": "PASS",
                               "files": {"../escaped.txt": "x"}}})
    verdict = k._dispatch_mock("1a", k.graph.phases["1a"], ws / "bundle.md")
    assert verdict.v == "ERROR" and "file error" in verdict.notes
    assert not (tmp_path / "escaped.txt").exists()


def test_mock_adapter_consumes_scripted_list_per_visit(tmp_path, monkeypatch):
    _offline_env(monkeypatch)
    ws = tmp_path / "list"
    k = _start(ws)
    _install_script(ws, {"1a": [{"verdict": "PASS", "notes": "first"},
                                {"verdict": "WARN", "notes": "second"}]})
    seen = [k._dispatch_mock("1a", k.graph.phases["1a"], ws / "b.md").v
            for _ in range(3)]
    assert seen == ["PASS", "WARN", "WARN"]