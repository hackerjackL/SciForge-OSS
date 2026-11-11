"""Regression tests for the provider-backed RSI mutator + branch-isolated submit.

Security posture under test (in order of importance):
  3. a provider reply that tries to edit tests/ or kernel/ is MECHANICALLY rejected
     (never merely discouraged in the prompt);
  4. no provider / host_mode degrades to the demo template WITH explicit disclosure;
  5. submit lands on `evolve/<id>` and leaves the base branch untouched;
  1. a clean JSON reply yields a structurally valid Patch;
  2. noise / ambiguous / invalid JSON never crashes and always degrades visibly.

All providers are stubs. No external LLM API, no network, no real-repo git writes
(the branch tests use throwaway `git init` repos under tmp_path).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 10):
    pytest.skip("kernel requires Python >= 3.10", allow_module_level=True)
sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge import evolve_cli  # noqa: E402
from sciforge.evolve import (EvolutionRun, Patch, apply_patch, op_error,  # noqa: E402
                            sanitize_patch, validate_patch)
from sciforge.evolve_cli import (LLMMutator, MutationParseError,  # noqa: E402
                                 _extract_patch_payload, build_mutator,
                                 submit_patch)

SKILL = "skills/demo/SKILL.md"
PARENT = Patch({"ops": [{"path": SKILL, "old": "## Protocol",
                         "new": "## Protocol\n> RSI note: existing."}]})


# ---------------- fixtures / stubs ----------------
class _Rec:
    def __init__(self, **kw):
        self._d = kw

    def as_dict(self):
        return dict(self._d)


class StubProvider:
    """Replays canned replies; records every prompt. Never touches the network."""
    host_mode = False

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    def model_for(self, role):
        return {"backend": "stub", "model": "stub-model"}

    def complete(self, role, system, prompt, **kw):
        self.calls.append({"role": role, "system": system, "prompt": prompt, **kw})
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply, _Rec(role=role, input_tokens=1, output_tokens=1, cost_usd=0.0)


class HostModeProvider:
    host_mode = True


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "skills" / "demo").mkdir(parents=True)
    (root / SKILL).write_text("# Demo Skill\n\n## Protocol\n\nDo the thing.\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (root / "kernel" / "sciforge").mkdir(parents=True)
    (root / "kernel" / "sciforge" / "evolve.py").write_text("# frozen module\n")
    return root


def ok_reply(old="Do the thing.", new="Do the thing.\n> RSI note: add a checkable artifact."):
    return json.dumps({"ops": [{"path": SKILL, "old": old, "new": new,
                                "rationale": "sharpens the instruction"}],
                       "rationale": "turn a stall into a checkable step"})


def demo_fallback():
    return evolve_cli._demo_mutator()


# ---------------- 1. valid JSON -> structurally correct Patch ----------------
def test_llm_mutator_valid_json_yields_patch(tmp_path):
    root = make_repo(tmp_path)
    prov = StubProvider([ok_reply()])
    signals = [{"run_id": "Q900", "gate_rejections": {"validate_verdicts": 3}}]
    inspire = Patch({"ops": [{"path": SKILL, "old": "## Protocol",
                              "new": "## Protocol\n> idea from another island"}]})
    m = LLMMutator(prov, fallback=demo_fallback(), repo_root=root, signals=signals)
    patch = m(PARENT, inspire)

    assert isinstance(patch, Patch)
    assert len(patch["ops"]) == 1
    op = patch["ops"][0]
    assert op["path"] == SKILL and op["old"] == "Do the thing."
    assert "RSI note" in op["new"]
    assert op["rationale"] == "sharpens the instruction"

    res = apply_patch(root, patch, checkout=root)
    assert res["ok"] and res["applied"] == [SKILL]
    assert "checkable artifact" in (root / SKILL).read_text()

    info = m.info()
    assert info["mode"] == "llm" and info["calls"] == 1 and info["fallbacks"] == 0
    assert info["disclosure"] == "llm_ideation_mutation"
    assert info["usage"]["cost_usd"] == 0.0

    # prompt carries role, audit-signal slot, frozen-path rule and the output schema
    call = prov.calls[0]
    assert call["role"] == "ideation"
    assert "AUDIT SIGNALS" in call["prompt"]
    assert "tests/" in call["prompt"] and "FROZEN" in call["prompt"]
    assert '"ops"' in call["prompt"]
    assert call["json_schema"]["required"] == ["ops"]
    assert "## Protocol" in call["prompt"]  # parent + file context are included
    assert "Do the thing." in call["prompt"]  # the verbatim anchor appears in context
    assert "validate_verdicts" in call["prompt"]  # audit signals are included
    assert "INSPIRATION" in call["prompt"] and "another island" in call["prompt"]


def test_llm_mutator_accepts_single_fenced_json_block(tmp_path):
    root = make_repo(tmp_path)
    reply = "Here is my proposal:\n```json\n" + ok_reply() + "\n```\nDone."
    m = LLMMutator(StubProvider([reply]), fallback=demo_fallback(), repo_root=root)
    patch = m(PARENT, None)
    assert patch["ops"][0]["path"] == SKILL
    assert m.info()["fallbacks"] == 0


def test_llm_mutator_accepts_bare_single_op_object(tmp_path):
    root = make_repo(tmp_path)
    reply = json.dumps({"path": SKILL, "old": "Do the thing.",
                        "new": "Do the thing.\n> RSI note: bare object."})
    m = LLMMutator(StubProvider([reply]), fallback=demo_fallback(), repo_root=root)
    patch = m(PARENT, None)
    assert patch["ops"][0]["path"] == SKILL


# ---------------- 2. noise / ambiguity -> disclosed fallback, never a crash ----------------
def test_llm_mutator_noise_falls_back_with_disclosure(tmp_path):
    root = make_repo(tmp_path)
    m = LLMMutator(StubProvider(["Sure! I would improve the protocol by making it better."]),
                   fallback=demo_fallback(), repo_root=root, attempts=2)
    patch = m(PARENT, None)

    assert isinstance(patch, Patch)
    assert patch["ops"] and all(op["path"].startswith("skills/") for op in patch["ops"])
    info = m.info()
    assert info["fallbacks"] == 1
    assert info["disclosure"] == "llm_ideation_mutation_with_demo_fallback:parse_failure"
    assert info["last_error"]


def test_llm_mutator_ambiguous_objects_retry_then_fall_back(tmp_path):
    """Two distinct patch objects in one reply must NOT be 'last JSON wins'."""
    root = make_repo(tmp_path)
    a = json.dumps({"ops": [{"path": SKILL, "old": "Do the thing.",
                             "new": "Do the thing. Variant A."}]})
    b = json.dumps({"ops": [{"path": SKILL, "old": "Do the thing.",
                             "new": "Do the thing. Variant B."}]})
    prov = StubProvider([a + "\n" + b, a + "\n" + b])
    m = LLMMutator(prov, fallback=demo_fallback(), repo_root=root, attempts=2)
    patch = m(PARENT, None)

    assert len(prov.calls) == 2  # one strict retry, then fallback
    assert m.info()["fallbacks"] == 1
    assert "Variant A" not in json.dumps(patch) and "Variant B" not in json.dumps(patch)


def test_llm_mutator_provider_error_falls_back(tmp_path):
    root = make_repo(tmp_path)
    m = LLMMutator(StubProvider([RuntimeError("no key for backend")]),
                   fallback=demo_fallback(), repo_root=root)
    patch = m(PARENT, None)
    assert patch["ops"]
    info = m.info()
    assert info["fallbacks"] == 1
    assert info["disclosure"].endswith(":provider_error")


def test_extract_payload_explicit_errors():
    with pytest.raises(MutationParseError) as e:
        _extract_patch_payload("")
    assert e.value.reason == "empty_reply"
    with pytest.raises(MutationParseError) as e:
        _extract_patch_payload("no json at all")
    assert e.value.reason == "no_patch_json"
    with pytest.raises(MutationParseError) as e:
        _extract_patch_payload('```json\n{"ops": []}\n```\n```json\n{"ops": []}\n```')
    assert e.value.reason == "ambiguous_json_blocks"


# ---------------- 3. SECURITY: frozen paths / traversal are mechanically rejected ----------------
def test_llm_mutator_mechanically_rejects_frozen_paths(tmp_path):
    """The most important test: prompt discipline is not the boundary."""
    root = make_repo(tmp_path)
    reply = json.dumps({"ops": [
        {"path": "tests/test_x.py", "old": "def test_x(): pass",
         "new": "def test_x(): assert True  # weakened"},
        {"path": "kernel/sciforge/evolve.py", "old": "# frozen module",
         "new": "# disabled guard"},
        {"path": "scripts/ci_check.py", "old": "x", "new": "y"},
        {"path": "skills/shared-references/schemas/x.schema.json", "old": "a", "new": "b"},
        {"path": SKILL, "old": "Do the thing.",
         "new": "Do the thing.\n> RSI note: legitimate."},
    ]})
    m = LLMMutator(StubProvider([reply]), fallback=demo_fallback(), repo_root=root)
    patch = m(PARENT, None)

    paths = [op["path"] for op in patch["ops"]]
    assert paths == [SKILL]  # only the legitimate op survives
    assert validate_patch(patch) == []
    reasons = [r["reason"] for r in m.rejected]
    assert reasons.count("frozen_path") == 4
    assert all(not p.startswith(("tests/", "kernel/", "scripts/")) for p in paths)

    res = apply_patch(root, patch, checkout=root)
    assert res["ok"] and res["applied"] == [SKILL]
    assert (root / "tests" / "test_x.py").read_text() == "def test_x(): pass\n"
    assert (root / "kernel" / "sciforge" / "evolve.py").read_text() == "# frozen module\n"
    assert m.info()["rejected_ops"] == 4


def test_llm_mutator_all_frozen_ops_fall_back_to_safe_patch(tmp_path):
    root = make_repo(tmp_path)
    reply = json.dumps({"ops": [
        {"path": "tests/test_x.py", "old": "def test_x(): pass", "new": "def test_x(): pass  # x"},
        {"path": "kernel/sciforge/evolve.py", "old": "# frozen module", "new": "# x"},
    ]})
    m = LLMMutator(StubProvider([reply]), fallback=demo_fallback(), repo_root=root, attempts=1)
    patch = m(PARENT, None)
    assert patch["ops"] and all(op["path"].startswith("skills/") for op in patch["ops"])
    assert m.info()["fallbacks"] == 1
    assert m.info()["disclosure"].endswith(":parse_failure")


def test_llm_mutator_rejects_traversal_and_absolute_paths(tmp_path):
    root = make_repo(tmp_path)
    reply = json.dumps({"ops": [
        {"path": "skills/../../kernel/sciforge/evolve.py", "old": "# frozen module", "new": "# x"},
        {"path": "/etc/passwd", "old": "root", "new": "hacked"},
        {"path": "skills/demo/../demo/SKILL.md", "old": "Do the thing.", "new": "Do the thing."},
        {"path": SKILL, "old": "Do the thing.", "new": "Do the thing.\n> RSI note: safe."},
    ]})
    m = LLMMutator(StubProvider([reply]), fallback=demo_fallback(), repo_root=root)
    patch = m(PARENT, None)
    assert [op["path"] for op in patch["ops"]] == [SKILL]
    assert [r["reason"] for r in m.rejected].count("unsafe_path") == 3


def test_sanitize_patch_reason_codes(tmp_path):
    root = make_repo(tmp_path)
    bad = Patch({"ops": [
        "not-a-dict",
        {"path": SKILL, "old": "x"},
        {"path": "tests/x.py", "old": "a", "new": "b"},
        {"path": "../outside.md", "old": "a", "new": "b"},
        {"path": SKILL, "old": "", "new": "b"},
        {"path": SKILL, "old": "same", "new": "same"},
        {"path": "skills/demo/missing.md", "old": "a", "new": "b"},
        {"path": SKILL, "old": "not in the file", "new": "b"},
    ]})
    clean, rejected = sanitize_patch(bad, root=root)
    assert clean["ops"] == []
    reasons = [r["reason"] for r in rejected]
    assert reasons == ["malformed_op", "malformed_op", "frozen_path", "unsafe_path",
                       "empty_anchor", "no_change", "missing_file", "anchor_not_found"]
    assert validate_patch({"ops": "nope"})[0]["reason"] == "ops_not_list"
    assert op_error({"path": SKILL, "old": "Do the thing.", "new": "x"}, root=root) is None


def test_evolution_run_guards_every_mutator_output(tmp_path, monkeypatch):
    """Defense in depth: even a broken/injected mutator cannot evaluate frozen edits."""
    import sciforge.evolve as evolve_mod

    root = make_repo(tmp_path)
    # Same wiring as run_evolve_cli: apply/revert resolve against the scratch tree.
    monkeypatch.setattr(evolve_mod, "apply_patch",
                        lambda ws, patch, checkout=None: apply_patch(ws, patch, checkout=root))
    monkeypatch.setattr(evolve_mod, "revert_patch", lambda ws, applied: None)
    seed = Patch({"ops": [{"path": SKILL, "old": "Do the thing.",
                           "new": "Do the thing.\n> RSI note: seed."}]})

    class FrozenMutator:
        def __call__(self, parent, inspire):
            return Patch({"ops": [
                {"path": "tests/test_x.py", "old": "def test_x(): pass", "new": "x"},
                {"path": "kernel/sciforge/evolve.py", "old": "# frozen module", "new": "x"},
            ]})

    class SepDomain:
        name = "sep"

        def score(self, patch):
            good = not any("CORRUPT" in o["new"] for o in patch["ops"])
            return {"score": 0.9 if good else 0.1}

    er = EvolutionRun(root, SepDomain(), FrozenMutator(), algorithm="puct", budget=1,
                      seed_patch=seed)
    out = er.run()
    assert out["status"] == "done"
    events = Path(er.events_path).read_text()
    assert "mutation_guarded" in events and "frozen_path" in events
    # the stripped-empty candidate is hard-zeroed by apply_patch, never a free 1.0
    assert any(r.get("score") == 0.0 for r in er.results)


# ---------------- 4. no key / host_mode -> demo + explicit disclosure ----------------
def test_build_mutator_host_mode_degrades_and_discloses():
    mut, info = build_mutator(providers=HostModeProvider())
    assert callable(mut) and info["mode"] == "demo_template"
    assert info["degraded"] is True
    assert info["disclosure"] == "demo_template:host_mode"
    patch = mut(PARENT, None)
    assert patch["ops"] and all(op["path"].startswith("skills/") for op in patch["ops"])


def test_build_mutator_no_provider_degrades_and_discloses(monkeypatch):
    def boom():
        raise RuntimeError("import exploded")

    monkeypatch.setattr(evolve_cli, "_default_providers", boom)
    mut, info = build_mutator(providers=None)
    assert callable(mut) and info["mode"] == "demo_template"
    assert info["disclosure"] == "demo_template:no_provider"
    assert "import exploded" in info["reason"]


def test_build_mutator_forced_demo_env(monkeypatch):
    monkeypatch.setenv("SCIFORGE_EVOLVE_MUTATOR", "demo")
    mut, info = build_mutator(providers=StubProvider([ok_reply()]))
    assert callable(mut) and info["mode"] == "demo_template"
    assert info["disclosure"] == "demo_template:forced_by_env"


def test_build_mutator_real_provider_path(tmp_path):
    root = make_repo(tmp_path)
    mut, info = build_mutator(providers=StubProvider([ok_reply()]), repo_root=root)
    assert isinstance(mut, LLMMutator)
    assert info["mode"] == "llm" and info["disclosure"] == "llm_ideation_mutation"
    assert mut(PARENT, None)["ops"][0]["path"] == SKILL


# ---------------- 5. submit lands on a branch, never on the base branch ----------------
def _init_repo(root: Path) -> str:
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, check=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    git("symbolic-ref", "HEAD", "refs/heads/master")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return git("rev-parse", "HEAD").stdout.strip()


def _make_extension(tmp_path: Path, ops, *, status="PENDING_HUMAN_MERGE",
                    run_id="evo_test") -> tuple[Path, Path]:
    ws = tmp_path / "ws"
    ext = ws / ".sciforge" / "skill-extensions" / run_id
    ext.mkdir(parents=True)
    (ext / "patch.json").write_text(json.dumps(ops))
    (ext / "meta.json").write_text(json.dumps({
        "run_id": run_id, "score": 0.8, "held_out": 0.75, "status": status}))
    return ws, ext


def _ok_ops():
    return [{"path": SKILL, "old": "Do the thing.",
             "new": "Do the thing.\n> RSI note: landed on a branch."}]


def _git_ok(root, *args):
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True)


@pytest.fixture
def submit_env(tmp_path, monkeypatch):
    root = make_repo(tmp_path)
    base = _init_repo(root)
    monkeypatch.setattr(evolve_cli, "REPO_ROOT", root)
    monkeypatch.setattr(evolve_cli, "_run_ci_check",
                        lambda _root: subprocess.CompletedProcess([], 0, "ci ok", ""))
    return root, base


def test_submit_creates_branch_and_leaves_master_untouched(tmp_path, submit_env, capsys):
    root, base = submit_env
    ws, ext = _make_extension(tmp_path, _ok_ops())

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id="evo_test", direct=False))
    out = json.loads(capsys.readouterr().out)

    assert rc == 0 and out["status"] == "branch_ready"
    assert out["branch"] == "evolve/evo_test"
    assert out["base_branch"] == "master" and out["base_commit"] == base
    assert "merge_command" in out and "git merge --no-ff evolve/evo_test" == out["merge_command"]
    assert "diffstat" in out and SKILL in out["diffstat"]
    assert out["changed_files"] == [SKILL]

    # base branch did not move and its working tree is clean + unchanged
    assert _git_ok(root, "rev-parse", "master").stdout.strip() == base
    assert _git_ok(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "master"
    assert "RSI note" not in (root / SKILL).read_text()
    assert _git_ok(root, "status", "--porcelain").stdout.strip() == ""

    # the branch exists and carries exactly one reviewable commit
    assert _git_ok(root, "rev-parse", "--verify", "refs/heads/evolve/evo_test").returncode == 0
    on_branch = _git_ok(root, "show", "evolve/evo_test:skills/demo/SKILL.md").stdout
    assert "landed on a branch" in on_branch
    assert _git_ok(root, "rev-list", "--count", f"{base}..evolve/evo_test").stdout.strip() == "1"

    meta = json.loads((ext / "meta.json").read_text())
    assert meta["status"] == "BRANCH_READY" and meta["branch"] == "evolve/evo_test"


def test_submit_direct_is_explicit_opt_in(tmp_path, submit_env, capsys):
    root, base = submit_env
    ws, ext = _make_extension(tmp_path, _ok_ops())

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id="evo_test", direct=True))
    out = json.loads(capsys.readouterr().out)

    assert rc == 0 and out["status"] == "merged"
    assert _git_ok(root, "rev-parse", "master").stdout.strip() != base
    assert "landed on a branch" in (root / SKILL).read_text()
    assert json.loads((ext / "meta.json").read_text())["status"] == "MERGED"


def test_submit_allows_untracked_files(tmp_path, submit_env, capsys):
    """Untracked notes must not block a landing; the commit is path-scoped."""
    root, _ = submit_env
    (root / "NOTES.txt").write_text("scratch notes\n")
    ws, _ = _make_extension(tmp_path, _ok_ops())

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id="evo_test", direct=False))
    out = json.loads(capsys.readouterr().out)

    assert rc == 0 and out["status"] == "branch_ready"
    assert out["changed_files"] == [SKILL]
    assert _git_ok(root, "show", "--name-only", "--format=",
                   "evolve/evo_test").stdout.strip() == SKILL


def test_submit_refuses_dirty_worktree(tmp_path, submit_env, capsys):
    root, base = submit_env
    (root / SKILL).write_text("# dirty\n")
    ws, _ = _make_extension(tmp_path, _ok_ops())

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id="evo_test", direct=False))
    out = json.loads(capsys.readouterr().out)

    assert rc == 1 and out["status"] == "rejected" and out["reason"] == "dirty_worktree"
    assert _git_ok(root, "rev-parse", "master").stdout.strip() == base
    assert _git_ok(root, "rev-parse", "--verify", "refs/heads/evolve/evo_test").returncode != 0


def test_submit_rejects_frozen_patch_before_git(tmp_path, submit_env, capsys):
    root, base = submit_env
    ws, _ = _make_extension(tmp_path, [
        {"path": "tests/test_x.py", "old": "def test_x(): pass", "new": "def test_x(): pass"}])

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id="evo_test", direct=False))
    out = json.loads(capsys.readouterr().out)

    assert rc == 1 and out["status"] == "rejected" and out["reason"] == "invalid_patch"
    assert out["detail"][0]["reason"] == "frozen_path"
    assert _git_ok(root, "rev-parse", "master").stdout.strip() == base
    assert _git_ok(root, "rev-parse", "--verify", "refs/heads/evolve/evo_test").returncode != 0


def test_submit_ci_failure_rolls_back_branch(tmp_path, submit_env, monkeypatch, capsys):
    root, base = submit_env
    monkeypatch.setattr(evolve_cli, "_run_ci_check",
                        lambda _root: subprocess.CompletedProcess([], 1, "", "ci broke"))
    ws, _ = _make_extension(tmp_path, _ok_ops())

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id="evo_test", direct=False))
    out = json.loads(capsys.readouterr().out)

    assert rc == 1 and out["status"] == "rolled_back"
    assert _git_ok(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "master"
    assert "RSI note" not in (root / SKILL).read_text()
    assert _git_ok(root, "rev-parse", "--verify", "refs/heads/evolve/evo_test").returncode != 0


def test_submit_branch_name_is_sanitized(tmp_path, submit_env, capsys):
    root, _ = submit_env
    weird = "weird id; rm -rf"
    ws, ext = _make_extension(tmp_path, _ok_ops(), run_id=weird)

    rc = submit_patch(SimpleNamespace(workspace=ws, run_id=weird, direct=False))
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["branch"].startswith("evolve/weird-id-rm")
    assert re.fullmatch(r"evolve/[A-Za-z0-9._-]+", out["branch"])