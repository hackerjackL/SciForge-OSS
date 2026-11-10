"""End-to-end smoke test for the SciForge-OSS pipeline structure (P2-12).

The 26 pipeline nodes are LLM-executed skills — there is no orchestrator
binary to run — so this test validates the STRUCTURE that makes a run
possible, on the minimal fixture in ``fixtures/e2e_minimal/``:

  a. the toy experiment is real, deterministic, and passes the Phase 6b toy
     gate (RESULT.json ``status=PASS`` + ``core_claim_validated=true``);
  b. the mock verdict set is a complete, schema-valid pipeline trail:
     ``scripts/validate_verdicts.py`` exits 0 with zero FAIL / zero WARN;
  c. the hash pins are real: PROBLEM_HASH.txt is the sha256 of PROBLEM.md
     and REGISTRY_HASH.txt is the sha256 of METHOD_REGISTRY_SNIPPET.md;
  d. the workspace stage directories match the tree in
     skills/shared-references/output-protocol.md exactly (both directions);
  e. skills/orchestrator/auto-pipeline/SKILL.md documents the same
     node set as kernel/config/phasegraph.json (guards against silent drops);
  f. the v1.7.2 machine-artifact layer is attached to the fixture, in the exact
     shape the kernel writes it: events.ndjson (event-sourced history, one L1
     loopback), nodes/NODES.json (content-addressed experiment node),
     nodes/CLAIM_ANCHORS.json (resolved claim -> node), audits/REP.json
     (compiled run plan + fallback conditions). These turn the mechanism gates
     (claim_anchor_gate, rep_plan_present, loopback budget) from SKIP into
     real executions on the fixture.

Authorities (read-only; this test never modifies them):
  - workspace tree:  skills/shared-references/output-protocol.md
  - verdict schemas: skills/shared-references/schemas/
  - phase DAG:       skills/orchestrator/auto-pipeline/SKILL.md

CI wiring (scripts/ci_check.py / .workflow/) intentionally NOT touched
here; that happens in a later pass. Runtime target: well under 10 s.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "fixtures" / "e2e_minimal"
SCIFORGE_DIR = FIXTURE_DIR / ".sciforge"
MOCK_VERDICTS = SCIFORGE_DIR / "verdicts"
RUNSTATE = SCIFORGE_DIR / "RUNSTATE.json"
TOY_SCRIPT = FIXTURE_DIR / "toy_experiment" / "run_toy.py"
VALIDATOR = REPO_ROOT / "scripts" / "validate_verdicts.py"
SCHEMA_DIR = REPO_ROOT / "skills" / "shared-references" / "schemas"
OUTPUT_PROTOCOL = REPO_ROOT / "skills" / "shared-references" / "output-protocol.md"
PIPELINE_SKILL = REPO_ROOT / "skills" / "orchestrator" / "auto-pipeline" / "SKILL.md"

# Authoritative phase topology. Read from phasegraph.json instead of pinning a
# prose count: the DAG has grown before (21 -> 26) and will grow again, so a
# hardcoded number would immediately rot.
PHASEGRAPH = REPO_ROOT / "kernel" / "config" / "phasegraph.json"
EXPECTED_PHASE_IDS = [p["id"] for p in json.loads(PHASEGRAPH.read_text())["phases"]]
EXPECTED_PHASE_COUNT = len(EXPECTED_PHASE_IDS)

# Top-level directories under {problem_id}/ (v6.0 two-tier split). Authority:
# the tree block in skills/shared-references/output-protocol.md (section
# "Artifact Directory Tree", v6.0). Hidden state layer (.sciforge) + delivery
# layer. test_output_protocol_tree_matches_hardcoded_dirs keeps both in sync.
EXPECTED_STAGE_DIRS = frozenset({
    ".sciforge",
    "refine-logs",
    "literature",
    "methods",
    "derivations",
    "src",
    "experiments",
    "logs",
    "figures",
    "paper",
    "output",
})

# Complete verdict set written by the end of a pipeline run (15 JSON
# verdicts + 2 hash artifacts), per the verdicts/ tree in
# output-protocol.md and the REGISTRY in scripts/validate_verdicts.py.
EXPECTED_VERDICT_FILES = frozenset({
    "REVIEW_STATE.json",
    "KILL_ARGUMENT.json",
    "CITATION_AUDIT.json",
    "PUBLISHABILITY_SCORE.json",
    "VERIFICATION_ROUTING.json",
    "EXPERIMENT_MATRIX.json",
    "EVALUATION_PROTOCOL.json",
    "BUDGET_FLOOR.json",
    "LEAKAGE_AUDIT.json",
    "LOGIC_VERIFICATION.json",
    "PROOF_AUDIT.json",
    "BLINDSPOT_CHECK.json",
    "PAPER_CLAIM_AUDIT.json",
    "LEAKAGE_SCRUB.json",
    "INVARIANT_CHECK.json",
    "REVIEW_LEDGER.json",
    "RUN_BUDGET.json",
    "FIGURE_AUDITS.json",
    "EVALUATION_REVIEW.json",
    "FAIRNESS.json",
    "QUALITY_GATE.json",
    "PAPER_COMPILE.json",
    "PROBLEM_HASH.txt",
    "REGISTRY_HASH.txt",
})

# v1.7.2 machine artifacts, in the exact paths/shapes the kernel writes them
# (kernel/sciforge/{state,nodes,rep}.py). They make the mechanism gates real
# on this fixture instead of permanently SKIPping.
EVENTS_LOG = SCIFORGE_DIR / "events.ndjson"
NODE_REGISTRY = SCIFORGE_DIR / "nodes" / "NODES.json"
CLAIM_ANCHORS = SCIFORGE_DIR / "nodes" / "CLAIM_ANCHORS.json"
REP_PLAN = SCIFORGE_DIR / "audits" / "REP.json"
CLAIMS_FROM_RESULTS = SCIFORGE_DIR / "audits" / "CLAIMS_FROM_RESULTS.md"
FIXTURE_EXPERIMENT_RESULT = (FIXTURE_DIR / "experiments" / "toy" / "main"
                             / "RESULT.json")


def _kernel_modules():
    """Import the kernel on 3.10+; skip cleanly on the repo's system 3.9."""
    if sys.version_info < (3, 10):
        pytest.skip("kernel requires Python >= 3.10 (X | Y syntax)")
    kernel_dir = str(REPO_ROOT / "kernel")
    if kernel_dir not in sys.path:
        sys.path.insert(0, kernel_dir)
    from sciforge import nodes, rep, state  # noqa: PLC0415
    from sciforge.pipeline import Kernel  # noqa: PLC0415
    return nodes, rep, state, Kernel


def run_toy(outdir: Path) -> dict:
    """Run the toy experiment into `outdir` and return its RESULT.json."""
    proc = subprocess.run(
        [sys.executable, str(TOY_SCRIPT), str(outdir)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, (
        f"run_toy.py exited {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    result_path = outdir / "RESULT.json"
    assert result_path.is_file(), f"RESULT.json not written to {outdir}"
    return json.loads(result_path.read_text(encoding="utf-8"))


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# (a) toy experiment: real, passing, deterministic
# ---------------------------------------------------------------------------

def test_toy_experiment_passes_toy_gate(tmp_path):
    """auto-pipeline Phase 6b gate: RESULT.json status=PASS +
    core_claim_validated=true (auto-pipeline SKILL.md, Quality Gates 6b)."""
    result = run_toy(tmp_path / "toy_run")
    assert result["status"] == "PASS"
    assert result["core_claim_validated"] is True
    assert result["seeds_used"] == 3
    # fixture is designed to pass: recommendation must advance the pipeline
    assert result["recommendation"] == "PROCEED_TO_FULL"


def test_toy_experiment_is_deterministic(tmp_path):
    """Fixed seeds => byte-stable science: two runs agree on every metric
    (execution_time_seconds is the only field allowed to differ)."""
    first = run_toy(tmp_path / "run_1")
    second = run_toy(tmp_path / "run_2")
    for field in ("metrics", "result_summary", "status", "seeds_used"):
        assert first[field] == second[field], f"field {field!r} not stable"


# ---------------------------------------------------------------------------
# (b) mock verdict set: complete + schema-valid via validate_verdicts.py
# ---------------------------------------------------------------------------

def test_fixture_verdict_set_is_complete():
    """The fixture pins the artifact contract: exactly one file per
    registered end-of-pipeline verdict (no extras, none missing)."""
    present = {p.name for p in MOCK_VERDICTS.iterdir() if p.is_file()}
    extra = present - EXPECTED_VERDICT_FILES
    assert not extra, f"unexpected files in mock_verdicts/: {sorted(extra)}"
    assert present == EXPECTED_VERDICT_FILES


def test_mock_verdicts_pass_validator(tmp_path):
    """scripts/validate_verdicts.py must exit 0 with zero FAIL / WARN on
    the copied verdict set (schema contracts pinned by the fixture)."""
    verdicts_dir = tmp_path / "Q001" / ".sciforge" / "verdicts"
    shutil.copytree(MOCK_VERDICTS, verdicts_dir)

    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(verdicts_dir)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, (
        f"validate_verdicts.py exited {proc.returncode}\n{proc.stdout}"
    )
    summary = re.search(
        r"Summary: (\d+) pass, (\d+) fail, (\d+) warn, (\d+) pending, (\d+) na",
        proc.stdout,
    )
    assert summary, f"no Summary line in validator output:\n{proc.stdout}"
    n_pass, n_fail, n_warn, _n_pending, n_na = map(int, summary.groups())
    assert n_fail == 0, f"validator reported FAILs:\n{proc.stdout}"
    assert n_warn == 0, f"validator reported WARNs:\n{proc.stdout}"
    assert n_na == 0, f"hybrid fixture expects no N/A verdicts:\n{proc.stdout}"
    assert n_pass == len(EXPECTED_VERDICT_FILES), (
        f"expected {len(EXPECTED_VERDICT_FILES)} validated artifacts, "
        f"got {n_pass}:\n{proc.stdout}"
    )


# ---------------------------------------------------------------------------
# (c) hash pins are real (recomputable from the frozen inputs)
# ---------------------------------------------------------------------------

def test_problem_hash_matches_problem_md():
    """INV-G1: PROBLEM_HASH.txt = sha256 of the frozen PROBLEM.md bytes."""
    recorded = (MOCK_VERDICTS / "PROBLEM_HASH.txt").read_text(encoding="utf-8")
    assert recorded.strip() == sha256_of(FIXTURE_DIR / "PROBLEM.md")
    assert re.fullmatch(r"[0-9a-f]{64}\n?", recorded), (
        "PROBLEM_HASH.txt must be single-line lowercase sha256 hex"
    )


def test_registry_hash_matches_registry_snippet():
    """Method hash-lock: REGISTRY_HASH.txt = sha256 of the locked Section 3
    snippet (stand-in for METHOD_REGISTRY.md Section 3)."""
    recorded = (MOCK_VERDICTS / "REGISTRY_HASH.txt").read_text(encoding="utf-8")
    snippet = FIXTURE_DIR / "methods" / "METHOD_REGISTRY_SNIPPET.md"
    assert recorded.strip() == sha256_of(snippet)
    assert re.fullmatch(r"[0-9a-f]{64}\n?", recorded), (
        "REGISTRY_HASH.txt must be single-line lowercase sha256 hex"
    )


# ---------------------------------------------------------------------------
# (b2) RUNSTATE checkpoint + routing-aware N/A (v6.0)
# ---------------------------------------------------------------------------

def test_runstate_checkpoint_matches_schema():
    """The fixture's long-horizon checkpoint validates against
    RUNSTATE.schema.json (v6.0 resume contract; checked here, not by
    validate_verdicts.py — see schemas/README.md non-verdict schemas)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("vv_for_runstate", VALIDATOR)
    vv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vv)

    schema = json.loads((SCHEMA_DIR / "RUNSTATE.schema.json").read_text(encoding="utf-8"))
    assert vv.lint_schema(schema) == [], "RUNSTATE schema uses unsupported keywords"
    runstate = json.loads(RUNSTATE.read_text(encoding="utf-8"))
    errors = vv.validate_against(runstate, schema)
    assert errors == [], f"fixture RUNSTATE.json violates its schema: {errors}"
    assert runstate["status"] in (
        "running", "paused_checkpoint", "paused_blocked", "completed", "killed"
    )


def test_theory_only_routing_reports_na_not_pending(tmp_path):
    """v6.0 routing-aware expectation: a theory-only run declares the four
    experiment-gated verdicts N/A (verification-routing.md §5); the validator
    reports them N/A, not pending, and exits 0."""
    verdicts_dir = tmp_path / "Q002" / ".sciforge" / "verdicts"
    shutil.copytree(MOCK_VERDICTS, verdicts_dir)

    na_set = ["EXPERIMENT_MATRIX.json", "EVALUATION_PROTOCOL.json",
              "BUDGET_FLOOR.json", "REGISTRY_HASH.txt", "FAIRNESS.json"]
    for name in na_set:
        (verdicts_dir / name).unlink()
    routing = json.loads((verdicts_dir / "VERIFICATION_ROUTING.json").read_text(encoding="utf-8"))
    routing["route"] = "theory-only"
    routing["na_verdicts"] = na_set
    (verdicts_dir / "VERIFICATION_ROUTING.json").write_text(
        json.dumps(routing, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(verdicts_dir)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, f"validator exited {proc.returncode}\n{proc.stdout}"
    summary = re.search(
        r"Summary: (\d+) pass, (\d+) fail, (\d+) warn, (\d+) pending, (\d+) na",
        proc.stdout,
    )
    assert summary, f"no Summary line:\n{proc.stdout}"
    n_pass, n_fail, n_warn, n_pending, n_na = map(int, summary.groups())
    assert n_fail == 0 and n_warn == 0, proc.stdout
    assert n_na == 5, f"expected 5 N/A verdicts, got {n_na}:\n{proc.stdout}"
    assert n_pending == 0, f"declared-N/A verdicts leaked into pending:\n{proc.stdout}"
    assert n_pass == len(EXPECTED_VERDICT_FILES) - 5  # 5 N/A on theory-only (incl. FAIRNESS)


def test_na_declared_but_present_warns(tmp_path):
    """Routing/production inconsistency: a file declared N/A that IS produced
    must WARN (default mode: exit 0 with the warning recorded)."""
    verdicts_dir = tmp_path / "Q003" / ".sciforge" / "verdicts"
    shutil.copytree(MOCK_VERDICTS, verdicts_dir)
    routing = json.loads((verdicts_dir / "VERIFICATION_ROUTING.json").read_text(encoding="utf-8"))
    routing["na_verdicts"] = ["EXPERIMENT_MATRIX.json"]
    (verdicts_dir / "VERIFICATION_ROUTING.json").write_text(
        json.dumps(routing, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(verdicts_dir)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout
    assert re.search(r"EXPERIMENT_MATRIX\.json\s+WARN", proc.stdout), (
        f"declared-N/A-but-present file did not WARN:\n{proc.stdout}"
    )


# ---------------------------------------------------------------------------
# (d) workspace structure vs output-protocol.md (drift in either direction)
# ---------------------------------------------------------------------------

def test_workspace_skeleton_builds_expected_stage_dirs(tmp_path):
    """Building the {problem_id}/ skeleton per output-protocol.md yields
    exactly the expected stage directories."""
    problem_root = tmp_path / "Q001"
    for name in sorted(EXPECTED_STAGE_DIRS):
        (problem_root / name).mkdir(parents=True)
    built = {p.name for p in problem_root.iterdir() if p.is_dir()}
    assert built == set(EXPECTED_STAGE_DIRS)


def _output_protocol_tree_block() -> str:
    """Extract the fenced workspace-tree block containing {problem_id}/."""
    text = OUTPUT_PROTOCOL.read_text(encoding="utf-8")
    for block in re.findall(r"```[^\n]*\n(.*?)\n```", text, re.DOTALL):
        if "{problem_id}/" in block:
            return block
    raise AssertionError(
        "no fenced tree block containing '{problem_id}/' found in "
        "output-protocol.md — directory layout contract moved?"
    )


def test_output_protocol_tree_matches_hardcoded_dirs():
    """Both drift directions are caught:
    - a hardcoded dir missing from output-protocol.md => fixture is stale;
    - a new dir in output-protocol.md not hardcoded here => update the list.
    Authority is output-protocol.md (see its tree block)."""
    block = _output_protocol_tree_block()
    # top-level entries start at column 0 with the tree branch glyphs;
    # nested entries are indented behind '|', so this matches only depth 0
    top_level = set(re.findall(r"^[├└]──\s*([A-Za-z0-9_.-]+)/", block, re.M))
    assert top_level, f"no stage directories parsed from tree block:\n{block}"

    missing_in_doc = EXPECTED_STAGE_DIRS - top_level
    assert not missing_in_doc, (
        f"hardcoded stage dirs missing from output-protocol.md tree: "
        f"{sorted(missing_in_doc)}"
    )
    new_in_doc = top_level - EXPECTED_STAGE_DIRS
    assert not new_in_doc, (
        f"output-protocol.md tree has stage dirs not in EXPECTED_STAGE_DIRS "
        f"(update the test): {sorted(new_in_doc)}"
    )


# ---------------------------------------------------------------------------
# (e) phase-topology guard: auto-pipeline documents the phasegraph node set
# ---------------------------------------------------------------------------

def test_pipeline_skill_documents_expected_phase_graph():
    """The orchestrator doc must track phasegraph.json, not a prose count.

    A silent phase drop/renumber fails here; growing the DAG only requires
    updating phasegraph.json and the doc table, not this test's number.
    """
    text = PIPELINE_SKILL.read_text(encoding="utf-8")

    # Quick Reference states the current node count.
    m = re.search(r"^## Quick Reference\n(.*?)^## ", text, re.M | re.S)
    assert m, "auto-pipeline SKILL.md lost its Quick Reference section"
    quick_ref = m.group(1)
    count = re.search(r"(\d+)\s*[- ]\s*(?:node|phase)", quick_ref, re.I)
    assert count, f"no node-count statement in Quick Reference:\n{quick_ref}"
    assert int(count.group(1)) == EXPECTED_PHASE_COUNT, (
        f"Quick Reference documents {count.group(1)} nodes, expected "
        f"{EXPECTED_PHASE_COUNT} from phasegraph.json"
    )

    # H1 title states the same count.
    title = next(line for line in text.splitlines() if line.startswith("# "))
    assert re.search(rf"\b{EXPECTED_PHASE_COUNT}-Node\b", title, re.I), (
        f"title no longer says '{EXPECTED_PHASE_COUNT}-Node': {title!r}"
    )

    # The Phase Mode Table must contain exactly the phasegraph node ids.
    documented = set(re.findall(r"^\|\s*([0-9]+(?:\.[0-9]+)?[a-z]*):", text, re.M))
    expected = {str(pid) for pid in EXPECTED_PHASE_IDS}
    missing = expected - documented
    extra = documented - expected
    assert not missing and not extra, (
        f"Phase Mode Table drifts from phasegraph.json: "
        f"missing={sorted(missing)}, extra={sorted(extra)}"
    )


# ---------------------------------------------------------------------------
# (f) v1.7.2 machine artifacts: events / nodes / claim anchors / REP plan
#
# Until v1.7.3 the fixture carried only the final verdict set, so every gate
# backed by the v1.7.2 mechanisms (claim anchors, REP plan presence, loopback
# budgets counted from the event log) reported SKIP on it and their artifact
# shapes were never exercised. These tests pin the kernel-written shapes.
# ---------------------------------------------------------------------------

def test_fixture_ships_v172_machine_artifacts():
    """All six machine artifacts exist and the event stream is kernel-shaped."""
    for path in (EVENTS_LOG, NODE_REGISTRY, CLAIM_ANCHORS, REP_PLAN,
                 CLAIMS_FROM_RESULTS, FIXTURE_EXPERIMENT_RESULT):
        assert path.is_file(), f"missing v1.7.2 machine artifact: {path}"

    events = [json.loads(line) for line in
              EVENTS_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert events, "events.ndjson is empty"
    # EventLog emits strictly increasing seq starting at 1; replay relies on it.
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    for event in events:
        assert set(event) >= {"seq", "ts", "phase", "kind", "payload"}
        assert isinstance(event["payload"], dict)
        assert float(event["ts"]) > 0
    # A completed run commits every phase's boundary exactly once, except the
    # re-entered phase in the recorded L1 loopback (phase 2).
    committed = [e["payload"]["phase"] for e in events
                 if e["kind"] == "boundary_committed"]
    assert set(committed) == set(EXPECTED_PHASE_IDS)
    assert committed.count("2") == 2
    loopbacks = [e for e in events if e["kind"] == "loopback"]
    assert len(loopbacks) == 1
    assert loopbacks[0]["payload"]["id"] == "L1"
    assert loopbacks[0]["payload"]["target"] == "2"
    assert loopbacks[0]["payload"]["rep_fallback"] == "PASS"


def test_fixture_rep_plan_executes_and_passes():
    """rep_plan_present: a real compiled plan (26 objectives, fallbacks)."""
    nodes_mod, rep_mod, _state, _Kernel = _kernel_modules()
    plan = rep_mod.check_plan(FIXTURE_DIR)
    # PASS, never SKIP: phase 1 actually ran in the fixture's history.
    assert plan["status"] == "PASS"
    assert plan["objectives"] == EXPECTED_PHASE_COUNT
    assert plan["fallbacks"] >= 1
    rep_doc = json.loads(REP_PLAN.read_text(encoding="utf-8"))
    assert rep_doc["schema_version"] == "1.0"
    assert len(rep_doc["objectives"]) == EXPECTED_PHASE_COUNT
    assert "2.5" in rep_doc["fallbacks"]  # the L1 loopback's phase
    # declared fallback is consumable; an off-plan recovery is a violation
    assert rep_mod.fallback_consumed(FIXTURE_DIR, "2.5", "L1")["status"] == "PASS"
    assert rep_mod.fallback_consumed(FIXTURE_DIR, "1b", "L1")["status"] == "FAIL"


def test_fixture_nodes_and_claim_anchors_are_hash_stable():
    """NODES.json holds content-addressed nodes; anchors resolve without drift."""
    nodes_mod, _rep, _state, _Kernel = _kernel_modules()
    registry = nodes_mod.load(FIXTURE_DIR)
    assert registry["schema_version"] == "1.0"
    assert registry["nodes"], "node registry is empty"
    for node in registry["nodes"]:
        assert re.fullmatch(r"n\d{3}", node["id"])
        assert node["kind"] and node["phase"] and node["reexec_cmd"]
        assert node["outputs_sha"], "node records no output hashes"
        for rel, expected in node["outputs_sha"].items():
            actual = nodes_mod.sha256_file(FIXTURE_DIR / rel)
            assert actual == expected, f"node output hash drifted: {rel}"

    anchors = nodes_mod.load_anchors(FIXTURE_DIR)
    assert anchors, "claim anchors are empty"
    assert all(a["resolved"] is True for a in anchors)
    assert all(a["node_id"] for a in anchors)
    assert nodes_mod.verify_anchors(FIXTURE_DIR) == []


def test_fixture_claim_anchor_gate_executes_and_passes():
    """claim_anchor_gate leaves SKIP and validates the fixture's real chain."""
    _kernel_modules()  # 3.10+ guard: the gate script imports kernel nodes.py
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "claim_anchor_gate.py"),
         str(FIXTURE_DIR)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "claim_anchor PASS" in proc.stdout
    assert "SKIP" not in proc.stdout


def test_fixture_event_log_reconstructs_loopback_budget(tmp_path):
    """A Kernel recovers the L1 round count from events, not from memory."""
    _nodes, _rep, state_mod, Kernel = _kernel_modules()
    copy = tmp_path / "Q001"
    shutil.copytree(FIXTURE_DIR, copy)
    kernel = Kernel(copy)
    assert kernel._round_count("L1") == 1
    # a completed run is terminal: recovery must not restart or mutate it
    assert state_mod.recover(state_mod.EventLog(copy), state_mod.RunState(copy),
                             copy) == "completed"


def test_fixture_s2_gates_execute_and_pass(tmp_path):
    """Adding the experiment record obliges the S2 gate battery: the ladder,
    the ablation ledger and the completeness audit must execute and PASS on a
    copy of the fixture (they used to SKIP when no experiment existed)."""
    _kernel_modules()
    copy = tmp_path / "Q001"
    shutil.copytree(FIXTURE_DIR, copy)
    cases = (("s2_ladder_gate.py", "s2_ladder PASS"),
             ("s2_ablation_gate.py", "s2_ablation PASS"),
             ("s2_audit.py", "s2_audit PASS"))
    for script, marker in cases:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / script), str(copy)],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 0, f"{script}:\n{proc.stdout}{proc.stderr}"
        assert marker in proc.stdout, f"{script}:\n{proc.stdout}"
        assert "SKIP" not in proc.stdout.splitlines()[0], proc.stdout
    # s2_audit's side effect lands in the copy, never in the checked-in fixture
    assert (copy / ".sciforge" / "audits" / "AUDIT_TRAIL.json").exists()
    assert not (FIXTURE_DIR / ".sciforge" / "audits" / "AUDIT_TRAIL.json").exists()
