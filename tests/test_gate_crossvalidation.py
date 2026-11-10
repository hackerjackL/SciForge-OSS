"""v1.7.3 gate cross-validation regressions.

Three v1.6-era gates trusted agent-authored claims with no contact with raw
evidence. These tests pin the upgrade:

  * fairness_gate — a pretty FAIRNESS_LEDGER.json that contradicts seed counts,
    split hashes or compute budgets on disk must FAIL; a ledger that reconciles
    must PASS; a ledger-only workspace (raw run elsewhere) stays PASS (N/A).
  * smoke_gate — a .SMOKE.json claiming PASS is re-executed in the sandbox; a
    non-zero exit / traceback / timeout / stale script hash must FAIL; an
    unexecutable legacy record must WARN (never silently PASS).
  * submission_ready — the final tier runs the strict DOI gate ONLINE by
    default; a dead DOI or a title-mismatched DOI is a hard failure; an
    offline/unreachable environment is disclosed (doi_online_unverified) and
    caps READY at MINOR_REV instead of passing silently.

Both polarities are covered for every gate: a truthful fixture passes, a
fabricated one fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (REPO_ROOT / "scripts", REPO_ROOT / "kernel"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import fairness_gate as fg          # noqa: E402
import smoke_gate as sg             # noqa: E402
import submission_ready as sr       # noqa: E402
from sciforge import litcache       # noqa: E402


# ---------------------------------------------------------------------------
# fairness gate
# ---------------------------------------------------------------------------
def _fairness_ws(tmp_path: Path, *, seed_claim: int = 3,
                 split_claim: str | None = None, budget_s: float = 45,
                 wall_s: float = 120) -> tuple[Path, str]:
    ws = tmp_path
    (ws / "methods").mkdir()
    (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    (ws / "logs").mkdir()
    (ws / "data").mkdir()
    split_file = ws / "data" / "split_manifest.json"
    split_file.write_text('{"train": [0, 1, 2], "test": [3]}')
    split_hash = hashlib.sha256(split_file.read_bytes()).hexdigest()

    (ws / ".sciforge" / "verdicts" / "EXPERIMENT_MATRIX.json").write_text(json.dumps({
        "budget_scale": "lite", "locked_hash": split_hash, "problem_id": "Q1",
        "groups": [{"name": "main", "hypothesis": "h",
                    "script": "code/experiments/full/run.py",
                    "estimated_minutes": 0.1, "background": False,
                    "subagents": 0, "seeds": [42, 43, 44]}]}))
    (ws / ".sciforge" / "verdicts" / "EVALUATION_PROTOCOL.json").write_text(json.dumps({
        "schema_version": "1.0", "generated_at": "2026-01-01T00:00:00Z",
        "split_hash": split_hash, "metrics_locked": [{"metric_name": "acc"}]}))
    (ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json").write_text(json.dumps({
        "schema_version": "1.0", "run_id": "Q1",
        "started_at": "2026-01-01T00:00:00Z", "wall_clock_seconds": wall_s,
        "api_cost_usd": 1.0, "pivot_count": 0, "ba_rounds_used": 0,
        "ba_rounds_max": 2, "per_phase": {"6c": {"duration_seconds": 90}},
        "limits": {"wall_clock_seconds_max": 43200, "api_cost_usd_max": 10,
                   "pivot_count_max": 2}}))
    for seed in (42, 43, 44):
        (ws / "logs" / f"main_s{seed}_1.STATUS.json").write_text(json.dumps({
            "run_id": f"main_s{seed}_1", "group": "main", "seed": seed,
            "state": "done", "duration_s": 30}))
    claim = split_claim or split_hash
    (ws / "methods" / "FAIRNESS_LEDGER.json").write_text(json.dumps({
        "budget_unit": "seconds",
        "comparisons": [{
            "table_id": "main", "methods": ["ours", "baseline"],
            "seed_count": seed_claim, "mean_std_reported": True,
            "effect_size_reported": True, "ci_reported": True,
            "multiple_comparison_control": "bh",
            "budget_per_method": {"ours": budget_s, "baseline": budget_s},
            "split_hash_per_method": {"ours": claim, "baseline": claim}}]}))
    return ws, split_hash


def _fairness_verdict(ws: Path) -> dict:
    return json.loads((ws / ".sciforge" / "verdicts" / "FAIRNESS.json").read_text())


def test_fairness_truthful_ledger_passes(tmp_path: Path):
    ws, _ = _fairness_ws(tmp_path)
    assert fg.main([str(ws), "--write-verdict"]) == 0
    doc = _fairness_verdict(ws)
    assert doc["verdict"] == "PASS"
    assert doc["evidence_crossvalidation"]["scope"] == "run"
    assert doc["evidence_crossvalidation"]["verdict"] == "PASS"
    assert doc["checks"]["evidence_crossvalidation"] == "PASS"


def test_fairness_fabricated_seed_count_fails(tmp_path: Path):
    """The ledger claims 5 seeds; only 3 independent traces exist => FAIL."""
    ws, _ = _fairness_ws(tmp_path, seed_claim=5)
    assert fg.main([str(ws), "--write-verdict"]) == 2
    doc = _fairness_verdict(ws)
    assert doc["verdict"] == "FAIL"
    assert "seed_count_unsupported" in doc["evidence_crossvalidation"]["reason_codes"]


def test_fairness_split_hash_mismatch_fails(tmp_path: Path):
    """Two declarations disagree (protocol vs ledger) => FAIL, not WARN."""
    ws, split_hash = _fairness_ws(tmp_path, split_claim="b" * 64)
    assert split_hash != "b" * 64
    assert fg.main([str(ws), "--write-verdict"]) == 2
    doc = _fairness_verdict(ws)
    assert "split_hash_mismatch" in doc["evidence_crossvalidation"]["reason_codes"]
    assert doc["comparisons"][0]["crossvalidation"]["split"]["status"] == "FAIL"


def test_fairness_split_contradicts_single_manifest_fails(tmp_path: Path):
    """One real split manifest exists; the claimed frozen hash is not its
    sha256 => the split lock claim is contradicted by the data file."""
    ws, _ = _fairness_ws(tmp_path, split_claim="c" * 64)
    (ws / ".sciforge" / "verdicts" / "EVALUATION_PROTOCOL.json").unlink()
    # the manifest remains on disk as the single split artifact
    assert fg.main([str(ws), "--write-verdict"]) == 2
    doc = _fairness_verdict(ws)
    assert "split_hash_mismatch" in doc["evidence_crossvalidation"]["reason_codes"]


def test_fairness_unreconcilable_split_warns_not_fails(tmp_path: Path):
    """Nothing on disk declares a split; the claim is disclosed as WARN."""
    ws, _ = _fairness_ws(tmp_path, split_claim="c" * 64)
    # remove the protocol declaration and the split manifest -> no evidence hash
    (ws / ".sciforge" / "verdicts" / "EVALUATION_PROTOCOL.json").unlink()
    (ws / "data" / "split_manifest.json").unlink()
    assert fg.main([str(ws), "--write-verdict"]) == 0
    doc = _fairness_verdict(ws)
    assert doc["verdict"] == "WARN"
    assert "split_hash_unverifiable" in doc["evidence_crossvalidation"]["reason_codes"]


def test_fairness_budget_beyond_wallclock_fails(tmp_path: Path):
    """Claimed per-method budget (3600s) exceeds the whole run (120s) => FAIL."""
    ws, _ = _fairness_ws(tmp_path, budget_s=3600, wall_s=120)
    assert fg.main([str(ws), "--write-verdict"]) == 2
    doc = _fairness_verdict(ws)
    assert "budget_exceeds_run_wallclock" in \
        doc["evidence_crossvalidation"]["reason_codes"]


def test_fairness_ledger_only_workspace_stays_pass(tmp_path: Path):
    """Backward compat / no false positive: a deepen ledger with no co-located
    raw evidence is N/A, not a failure (the run may live in another workspace)."""
    (tmp_path / "methods").mkdir()
    (tmp_path / "methods" / "FAIRNESS_LEDGER.json").write_text(json.dumps({
        "comparisons": [{
            "table_id": "t1", "methods": ["a", "b"], "seed_count": 5,
            "mean_std_reported": True, "effect_size_reported": True,
            "ci_reported": True, "multiple_comparison_control": "bh",
            "budget_per_method": {"a": 100, "b": 100}}]}))
    assert fg.main([str(tmp_path), "--write-verdict"]) == 0
    doc = _fairness_verdict(tmp_path)
    assert doc["verdict"] == "PASS"
    assert doc["evidence_crossvalidation"]["scope"] == "ledger_only"
    assert doc["evidence_crossvalidation"]["verdict"] == "N_A"


def test_fairness_theory_only_skips(tmp_path: Path):
    assert fg.main([str(tmp_path)]) == 3


# ---------------------------------------------------------------------------
# smoke gate — real re-execution + staleness
# ---------------------------------------------------------------------------
def _smoke_ws(tmp_path: Path, script_src: str, *, record_hash: bool = True,
              write_script: bool = True, smoke_result: str = "PASS",
              recorded_sha: str | None = None) -> Path:
    group = tmp_path / "experiments" / "full" / "g1"
    group.mkdir(parents=True)
    script = group / "run.py"
    if write_script:
        script.write_text(script_src)
    sha = hashlib.sha256(script.read_bytes()).hexdigest() if write_script else ""
    smoke = {"experiment_id": "g1", "smoke_scale": "1-step",
             "smoke_result": smoke_result, "fail_code": None,
             "fix_attempts": 0, "status_row_written": True,
             "executed_at": "2026-11-11T00:00:00Z",
             "script": "experiments/full/g1/run.py"}
    if record_hash:
        smoke["script_sha256"] = recorded_sha or sha
    (group / "g1.SMOKE.json").write_text(json.dumps(smoke))
    (group / "DISPATCH.json").write_text(json.dumps(
        {"script": "experiments/full/g1/run.py"}))
    (group / "STATUS.json").write_text('{"state": "done"}')
    return tmp_path


_FAKE_SANDBOX = lambda ws: ["/usr/bin/env"]  # test stand-in for a sandbox wrapper


def test_smoke_real_execution_passes(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'print("smoke ok")\n')
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "PASS", doc
    assert doc["executed"] == 1
    assert doc["groups"][0]["execution"]["returncode"] == 0


def test_smoke_nonzero_exit_fails(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'import sys\nsys.exit(3)\n')
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert "smoke_nonzero_exit" in doc["reason_codes"]


def test_smoke_traceback_fails_even_with_exit_zero(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'print("Traceback (most recent call last):")\n')
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert "smoke_traceback" in doc["reason_codes"]


def test_smoke_timeout_fails(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'import time\ntime.sleep(5)\n')
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX, timeout=0.2)
    assert doc["verdict"] == "FAIL"
    assert "smoke_timeout" in doc["reason_codes"]


def test_smoke_stale_hash_fails(tmp_path: Path):
    """The script mutated after the smoke; the recorded content hash differs."""
    ws = _smoke_ws(tmp_path, 'print("v2")\n', recorded_sha="d" * 64)
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert "stale_smoke_script_hash_mismatch" in doc["reason_codes"]


def test_smoke_hashless_record_warns(tmp_path: Path):
    """Legacy .SMOKE.json without a content hash cannot prove provenance."""
    ws = _smoke_ws(tmp_path, 'print("ok")\n', record_hash=False)
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "WARN"
    assert "smoke_no_script_hash" in doc["reason_codes"]


def test_smoke_missing_script_fails_not_passes(tmp_path: Path):
    """A declared-but-absent script proves nothing: no hash to check, nothing to
    execute. Because the `script` path is agent-supplied, a nonexistent path is
    indistinguishable from a fabricated one — so this is FAIL, not a WARN the
    boundary waves through. The disclosure reason is still reported."""
    ws = _smoke_ws(tmp_path, "print(1)\n", write_script=False)
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert "smoke_script_missing" in doc["reason_codes"]
    assert "smoke_no_positive_evidence" in doc["reason_codes"]
    assert sg.main([str(ws), "--json"]) == 2  # FAIL blocks the boundary


def test_smoke_unbound_record_cannot_ride_the_boundary(tmp_path: Path):
    """Bypass probe: a record that names no script at all, with DISPATCH.json
    empty, used to reach `smoke_unbound_to_script` as a WARN (exit 0) — so an
    agent could cross 6c having executed nothing. Zero evidence now FAILs."""
    group = tmp_path / "experiments" / "full" / "g1"
    group.mkdir(parents=True)
    (group / "g1.SMOKE.json").write_text(json.dumps({
        "experiment_id": "g1", "smoke_result": "PASS", "status_row_written": True}))
    (group / "DISPATCH.json").write_text("{}")
    (group / "STATUS.json").write_text('{"state": "done"}')
    doc = sg.check(tmp_path, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert doc["executed"] == 0
    assert sg.main([str(tmp_path), "--json"]) == 2


def test_smoke_sandbox_unavailable_warns_not_passes(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'print("ok")\n')
    doc = sg.check(ws, sandbox_wrap=lambda _ws: None, allow_unsandboxed=False)
    assert doc["verdict"] == "WARN"
    assert "sandbox_unavailable" in doc["reason_codes"]
    assert doc["executed"] == 0


def test_smoke_unsandboxed_execution_is_disclosed(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'print("ok")\n')
    doc = sg.check(ws, sandbox_wrap=lambda _ws: None, allow_unsandboxed=True)
    assert doc["verdict"] == "WARN"
    assert "executed_unsandboxed" in doc["reason_codes"]
    assert doc["executed"] == 1


def test_smoke_missing_artifact_fails(tmp_path: Path):
    group = tmp_path / "experiments" / "full" / "g1"
    group.mkdir(parents=True)
    (group / "DISPATCH.json").write_text("{}")
    (group / "STATUS.json").write_text('{"state": "done"}')
    doc = sg.check(tmp_path, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert "missing_smoke" in doc["reason_codes"]


def test_smoke_skip_before_dispatch(tmp_path: Path):
    doc = sg.check(tmp_path)
    assert doc["verdict"] == "SKIP"


def test_smoke_one_file_cannot_cover_two_dispatched_groups(tmp_path: Path):
    ws = _smoke_ws(tmp_path, 'print("ok")\n')
    other = tmp_path / "experiments" / "full" / "g2"
    other.mkdir()
    (other / "DISPATCH.json").write_text("{}")
    (other / "STATUS.json").write_text('{"state": "done"}')
    doc = sg.check(ws, sandbox_wrap=_FAKE_SANDBOX)
    assert doc["verdict"] == "FAIL"
    assert any("no g2.SMOKE.json" in p for p in doc["groups"][1]["problems"])


# ---------------------------------------------------------------------------
# submission_ready — strict DOI at the final tier
# ---------------------------------------------------------------------------
def _bib_ws(tmp_path: Path, entries: str) -> Path:
    (tmp_path / "literature").mkdir()
    (tmp_path / "literature" / "references.bib").write_text(entries)
    return tmp_path


def _good_resolver(_doi, timeout=20):
    return "@article{x, title={Something Real About Widgets}}"


def _mismatch_resolver(_doi, timeout=20):
    return "@article{x, title={Entirely Different Subject Matter}}"


def _dead_resolver(_doi, timeout=20):
    return None


def test_doi_online_resolves_and_passes(tmp_path: Path):
    ws = _bib_ws(tmp_path,
                 "@article{a2024, title={Something Real About Widgets}, "
                 "doi={10.1000/xyz}}\n")
    audit = sr._online_doi_audit(ws, budget_s=5, resolver=_good_resolver,
                                 probe=lambda: True)
    assert audit["mode"] == "online"
    assert audit["hard"] == []
    assert audit["stats"]["online"]["resolved"] == 1


def test_doi_online_title_mismatch_fails(tmp_path: Path):
    """A resolving DOI for the WRONG paper is the citation-hallucination case."""
    ws = _bib_ws(tmp_path,
                 "@article{a2024, title={Something Real About Widgets}, "
                 "doi={10.1000/xyz}}\n")
    audit = sr._online_doi_audit(ws, budget_s=5, resolver=_mismatch_resolver,
                                 probe=lambda: True)
    assert audit["mode"] == "online"
    assert any("title disagrees" in p for p in audit["hard"])


def test_doi_online_dead_doi_fails(tmp_path: Path):
    """Self-reported DOI that does not resolve => hard failure (NOT_READY)."""
    ws = _bib_ws(tmp_path,
                 "@article{a2024, title={Something Real About Widgets}, "
                 "doi={10.1000/xyz}}\n")
    audit = sr._online_doi_audit(ws, budget_s=5, resolver=_dead_resolver,
                                 probe=lambda: True)
    assert audit["mode"] == "online"
    assert audit["hard"] and any("does not resolve" in p for p in audit["hard"])


def test_doi_network_down_discloses_instead_of_hard_failing(tmp_path: Path):
    """Unreachable network: unresolved DOIs are disclosed, not blamed on the
    author — but the tier is capped, never silently READY."""
    ws = _bib_ws(tmp_path,
                 "@article{a2024, title={Something Real About Widgets}, "
                 "doi={10.1000/xyz}}\n")

    def offline_resolver(doi, timeout=20):
        raise OSError("network unreachable")

    audit = sr._online_doi_audit(ws, budget_s=5, resolver=offline_resolver,
                                 probe=lambda: False)
    assert audit["mode"] == "offline_degraded"
    assert audit["hard"] == []
    assert "doi_online_verification_incomplete" in audit["disclosures"]
    assert sr._cap_tier_for_doi("READY", audit) == "MINOR_REV"
    assert sr._cap_tier_for_doi("MAJOR_REV", audit) == "MAJOR_REV"


def test_doi_explicit_offline_discloses_and_caps_tier(tmp_path: Path):
    ws = _bib_ws(tmp_path,
                 "@article{a2024, title={Something Real About Widgets}, "
                 "doi={10.1000/xyz}}\n")
    audit = sr._online_doi_audit(ws, offline=True)
    assert audit["mode"] == "offline"
    assert audit["hard"] == []  # DOI presence is satisfied; resolution deferred
    assert "doi_online_unverified" in audit["disclosures"]
    assert sr._cap_tier_for_doi("READY", audit) == "MINOR_REV"


def test_doi_offline_missing_doi_is_still_hard(tmp_path: Path):
    ws = _bib_ws(tmp_path, "@article{b2024, title={No Doi Here}}\n")
    audit = sr._online_doi_audit(ws, offline=True)
    assert audit["mode"] == "offline"
    assert any("missing DOI" in p for p in audit["hard"])


def test_doi_cache_avoids_second_network_call(tmp_path: Path):
    ws = _bib_ws(tmp_path,
                 "@article{a2024, title={Something Real About Widgets}, "
                 "doi={10.1000/xyz}}\n")
    db = tmp_path / "cache.sqlite3"
    litcache.put("10.1000/xyz", True,
                 {"bibtex": "@article{x, title={Something Real About Widgets}}",
                  "title": "Something Real About Widgets"},
                 kind="doi", db=db)

    # No resolver injection: the litcache hit must satisfy the gate without a
    # network call (a miss would try doi.org and the assertions below fail).
    audit = sr._online_doi_audit(ws, db=db, budget_s=5, probe=lambda: True)
    assert audit["mode"] == "online"
    assert audit["hard"] == []
    assert audit["stats"]["cache_hits"] == 1
    assert audit["stats"]["network_failures"] == 0


def _submission_ws(tmp_path: Path, bib: str) -> Path:
    """Minimal workspace whose non-DOI hard items are stubbed in the test."""
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.pdf").write_bytes(b"%PDF-1.4\n/Count 5\n%%EOF\n")
    (tmp_path / "paper" / "main.tex").write_text(
        "\\begin{abstract}" + ("word " * 200) + "1 2 3 4 5 6 7 8"
        "\\end{abstract}\n\\section{Introduction}\\section{Method}")
    (tmp_path / "literature").mkdir()
    (tmp_path / "literature" / "references.bib").write_text(bib)
    (tmp_path / ".sciforge").mkdir()
    return tmp_path


def test_submission_ready_integrates_doi_hard_failure(tmp_path: Path, monkeypatch):
    """A self-reported DOI that cannot be resolved is a HARD item at the final
    tier (NOT_READY), not a soft note."""
    ws = _submission_ws(tmp_path,
                        "@article{a2024, title={Something Real About Widgets}, "
                        "doi={10.1000/xyz}}\n")
    monkeypatch.setattr(sr, "_run", lambda *a, **k: 0)
    import subprocess
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    doc = sr.check(ws, doi_resolver=_dead_resolver,
                   doi_probe=lambda: True, doi_budget_s=5)
    assert doc["tier"] == "NOT_READY"
    assert any("doi gate fails" in h for h in doc["hard"])


def test_submission_ready_discloses_offline_doi(tmp_path: Path, monkeypatch):
    ws = _submission_ws(tmp_path,
                        "@article{a2024, title={Something Real About Widgets}, "
                        "doi={10.1000/xyz}}\n")
    monkeypatch.setattr(sr, "_run", lambda *a, **k: 0)
    import subprocess
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    doc = sr.check(ws, offline=True)
    # offline is a disclosure, never a silent pass; the tier can't be READY
    assert doc["doi_verification"]["mode"] == "offline"
    assert "doi_online_unverified" in doc["disclosures"]
    assert doc["tier"] in ("MINOR_REV", "MAJOR_REV")