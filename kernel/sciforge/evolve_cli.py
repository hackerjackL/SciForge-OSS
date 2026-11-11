"""`sciforge-kernel evolve` / `submit` / `daily` wiring (S15/S17/S19).

Pipeline per evolution round:
 1. collect completed/blocked run archives -> audit signals
 2. deterministic proposals + optional provider-generated proposals
 3. build Domain: GateDomain(ci/tests/golden verdict completeness) x JudgeDomain
    with frozen rubric; three-shard golden split (test held out)
 4. EvolutionRun (puct | openevolve) search under budget — mutated by the
    provider-backed ideation mutator when a key/gateway exists, else by the demo
    template WITH an explicit `demo_template:<reason>` disclosure
 5. winner -> skill-extensions/<run_id>/ (S14 writable area, never the frozen tree)
 6. `sciforge-kernel submit` lands the winner on an isolated `evolve/<id>` branch
    for human review (direct-to-current-branch only via explicit opt-in)
 7. `daily` digests evolution state as plain text (printable/pushable anywhere)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from .evolve import (EvolutionRun, GateDomain, HybridDomain, JudgeDomain, Patch,
                     apply_patch, editable, op_error, split_shards, validate_patch)
from .propose import audit_run, proposals_from_signals

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "kernel" / "config" / "evolve.json"


def _load_config() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    return {}


def _evo_workspace(cfg: dict) -> Path:
    """Scratch search checkout. Env > evolve.json > /tmp default (backward compatible)."""
    return Path(os.environ.get("SCIFORGE_EVO_WORKSPACE")
                or cfg.get("evo_workspace", "/tmp/sciforge-evo"))


def _demo_mutator(rng_seed: int = 7):
    """Template mutation: vary the RSI-note append wording across proposals.

    This is the FALLBACK path, not the primary one: `build_mutator` wires the
    provider-backed LLMMutator whenever a usable key/gateway exists and degrades
    here only with an explicit `demo_template:<reason>` disclosure. It remains
    the no-key guarantee (and the injection point used by tests) so the search
    loop can always run.
    """
    variants = ["", " Track the fire-rate of this signal in LESSONS.json; when it repeats, escalate.",
                " Add a machine-checkable artifact requirement next to the note.",
                " Cap the escalation at 2 repeats to avoid contract bloat.",
                ""]
    state = {"i": 0, "seed": rng_seed}

    def mut(parent: Patch, inspire) -> Patch:
        i = state["i"] % len(variants)
        state["i"] += 1
        ops = []
        for op in parent["ops"]:
            note = variants[i]
            if note and op["new"].endswith("\n"):
                ops.append(dict(op, new=op["new"] + note))
            elif note:
                ops.append(dict(op, new=op["new"] + "\n" + note))
            else:
                ops.append(dict(op, new=op["new"].replace("\n " + (variants[(i - 1) % len(variants)]).strip(), "")))
        return Patch({"ops": ops})
    return mut


# ---------------- provider-backed mutator (the real RSI mutation operator) ----------------
# Contract (verified against evolve.py): mutator(parent: Patch, inspire) -> Patch,
# where `inspire` is the MAP-Elites inspiration candidate (None under PUCT).
#
# Safety model: the prompt TELLS the model the rules; `evolve.op_error` /
# `sanitize_patch` ENFORCE them. Prompt text is never the boundary — a skill file
# can contain injected instructions, and the model can simply disobey. Every op
# is validated against FROZEN_PREFIXES + path normalization before it can be
# evaluated, and EvolutionRun._mutate re-validates every mutator's output.

_ROLE = "ideation"
_MAX_CONTEXT_CHARS = 1400
_MAX_OPS = 3

_MUTATOR_SYSTEM = (
    "You are the mutation operator of a recursive self-improvement loop over "
    "SciForge's research skill library. The library is pure Markdown playbooks "
    "(skills/**.md); a patch is a list of verbatim text replacements. Propose ONE "
    "semantic improvement that turns an observed failure into a sharper, "
    "machine-checkable instruction. Never weaken an audit, gate, schema, citation "
    "requirement, or the negative-result discipline. Return ONLY a JSON object."
)

_OPS_SCHEMA = {
    "type": "object",
    "properties": {
        "ops": {"type": "array", "items": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "old": {"type": "string"},
                           "new": {"type": "string"}, "rationale": {"type": "string"}},
            "required": ["path", "old", "new"]}},
        "rationale": {"type": "string"},
    },
    "required": ["ops"],
}


class MutationParseError(ValueError):
    """Provider reply did not yield a mechanically valid patch payload."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


def _balanced_objects(raw: str):
    """Yield every balanced top-level-candidate {...} span, in text order."""
    i = 0
    while i < len(raw):
        if raw[i] == "{":
            depth = 0
            for j in range(i, len(raw)):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        yield raw[i:j + 1]
                        i = j
                        break
        i += 1


def _extract_patch_payload(raw: str) -> dict:
    """Strict JSON extraction from provider text.

    Deliberately stricter than pipeline._parse_verdict_json's host-stdout
    heuristic (which takes the last JSON object and is forgeable by echoed
    output). Rules here:
      1. exactly one fenced block -> parse it; several distinct blocks -> AMBIGUOUS;
      2. whole reply parses as one object -> use it;
      3. balanced-object scan -> require exactly ONE distinct object that looks
         like a patch (has "ops" or path/old/new). Several distinct candidates
         -> AMBIGUOUS, never "pick the last one".
    Ambiguity is an error: the caller retries with a stricter instruction and
    finally falls back to the demo mutator with explicit disclosure.
    """
    text = (raw or "").strip()
    if not text:
        raise MutationParseError("empty_reply")
    blocks = [b.strip() for b in re.findall(r"```(?:json|JSON)?\s*\n?(.*?)```", text, re.S)
              if b.strip()]
    if len(blocks) > 1:
        raise MutationParseError("ambiguous_json_blocks", f"{len(blocks)} fenced blocks")
    if blocks:
        try:
            d = json.loads(blocks[0])
        except json.JSONDecodeError as e:
            raise MutationParseError("invalid_fenced_json", str(e)[:200]) from e
        if isinstance(d, dict):
            return d
        raise MutationParseError("payload_not_object")
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return d
    except json.JSONDecodeError:
        pass
    uniq: dict[str, dict] = {}
    for span in _balanced_objects(text):
        try:
            d = json.loads(span)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        if "ops" in d or all(k in d for k in ("path", "old", "new")):
            uniq[json.dumps(d, sort_keys=True, ensure_ascii=False)] = d
    if len(uniq) == 1:
        return next(iter(uniq.values()))
    if len(uniq) > 1:
        raise MutationParseError("ambiguous_ops_objects", f"{len(uniq)} distinct candidates")
    raise MutationParseError("no_patch_json", text[:160])


class LLMMutator:
    """Provider-backed semantic mutator with mechanical guard + disclosed fallback.

    `info()` is the disclosure surface: mode, disclosure code, fallback count,
    rejected-op count, last error. It is written into the CLI output, the
    extension meta.json, and the run's NDJSON event trail.
    """

    def __init__(self, providers, *, fallback, repo_root: Path | None = None,
                 signals: list[dict] | None = None, role: str = _ROLE,
                 attempts: int = 2, max_ops: int = _MAX_OPS):
        self.providers = providers
        self.fallback = fallback
        self.repo_root = Path(repo_root) if repo_root else REPO_ROOT
        self.signals = signals or []
        self.role = role
        self.attempts = max(1, attempts)
        self.max_ops = max_ops
        self.calls = 0
        self.fallbacks = 0
        self.rejected: list[dict] = []
        self.usage: list[dict] = []
        self.last_error: str | None = None
        self.last_fallback_reason: str | None = None
        self.disclosure = "llm_ideation_mutation"

    # -- disclosure -----------------------------------------------------
    def info(self) -> dict:
        try:
            model = self.providers.model_for(self.role).get("model")
        except Exception:
            model = None
        return {"mode": "llm", "role": self.role, "model": model,
                "calls": self.calls, "fallbacks": self.fallbacks,
                "rejected_ops": len(self.rejected),
                "degraded": self.fallbacks > 0,
                "disclosure": self.disclosure,
                "last_fallback_reason": self.last_fallback_reason,
                "last_error": (self.last_error or "")[-300:] or None,
                "usage": self.usage[-1] if self.usage else None}

    # -- prompt ---------------------------------------------------------
    def _context_for(self, path: str, anchor: str) -> str:
        f = self.repo_root / path
        try:
            content = f.read_text()
        except OSError:
            return "(file unreadable)"
        idx = content.find(anchor)
        if idx < 0:
            return content[:_MAX_CONTEXT_CHARS]
        lo = max(0, idx - _MAX_CONTEXT_CHARS // 3)
        hi = min(len(content), idx + len(anchor) + _MAX_CONTEXT_CHARS)
        prefix = "...(truncated) " if lo else ""
        suffix = " ...(truncated)" if hi < len(content) else ""
        return prefix + content[lo:hi] + suffix

    def _build_prompt(self, parent: Patch, inspire) -> str:
        L = ["AUDIT SIGNALS extracted from completed runs (gate rejections, loopbacks,"
             " warnings; counts are real):",
             json.dumps(self.signals[-3:], ensure_ascii=False)[:2000] or "[]", ""]
        L.append("PARENT CANDIDATE (the current best patch lineage; improve on it):")
        parent_ops = [op for op in (parent.get("ops") or []) if isinstance(op, dict)][:self.max_ops]
        if parent_ops:
            for op in parent_ops:
                L.append(f"- file: {op.get('path')}")
                L.append(f"  anchor (old, verbatim from file):\n{str(op.get('old'))[:600]}")
                L.append(f"  replacement (new):\n{str(op.get('new'))[:900]}")
                L.append(f"  file context around the anchor:\n"
                         f"{self._context_for(str(op.get('path')), str(op.get('old')))}")
        else:
            L.append("(the parent is the unmutated library; propose the first edit)")
            skills = sorted(str(p.relative_to(self.repo_root))
                            for p in (self.repo_root / "skills").rglob("*.md"))[:40]
            L.append("Editable skill files (choose from these):")
            L.extend(f"- {s}" for s in skills)
        if inspire is not None and isinstance(inspire, dict) and inspire.get("ops"):
            L.append("")
            L.append("INSPIRATION candidate from another MAP-Elites island (do NOT copy;"
                     " borrow one idea if useful):")
            for op in inspire["ops"][:self.max_ops]:
                L.append(f"- {op.get('path')}: {str(op.get('new'))[:400]}")
        L += ["",
              "OUTPUT FORMAT (strict). Reply with ONE JSON object, no prose, no markdown:",
              '{"ops": [{"path": "skills/...", "old": "<verbatim anchor copied from the '
              'context above>", "new": "<replacement that contains the anchor plus the '
              'improvement>", "rationale": "<one sentence>"}], "rationale": "<one sentence>"}',
              "",
              "RULES:",
              "- 1 to 3 ops. `old` MUST be copied verbatim from the file context and be long"
              " enough to be unique in the file.",
              "- Only files under skills/ may be edited. tests/, kernel/, scripts/,"
              " skills/shared-references/schemas/, config and everything else are FROZEN;"
              " ops touching them are rejected by a mechanical guard, not by trust.",
              "- Prefer appending a short '> RSI note:' anchored on an existing heading or"
              " sentence; do not rewrite or delete existing normative content.",
              "- Never weaken a gate, an audit, a citation requirement, or the"
              " negative-result discipline.",
              "- Respond with ONLY the JSON object."]
        return "\n".join(L)

    # -- provider call --------------------------------------------------
    def _complete(self, prompt: str) -> str:
        text, rec = self.providers.complete(
            self.role, _MUTATOR_SYSTEM, prompt, temperature=0.5, max_tokens=2000,
            json_schema=_OPS_SCHEMA)
        usage = rec.as_dict() if hasattr(rec, "as_dict") else {}
        self.usage.append(usage)
        return text

    # -- payload -> Patch ----------------------------------------------
    def _payload_to_patch(self, payload: dict) -> Patch:
        if not isinstance(payload, dict):
            raise MutationParseError("payload_not_object")
        ops = payload.get("ops")
        if ops is None and all(k in payload for k in ("path", "old", "new")):
            ops = [payload]
        if not isinstance(ops, list) or not ops:
            raise MutationParseError("no_ops")
        kept, rejected = [], []
        for op in ops:
            why = op_error(op, root=self.repo_root) if isinstance(op, dict) else "malformed_op"
            if why:
                rejected.append({"path": op.get("path") if isinstance(op, dict) else None,
                                 "reason": why})
            elif len(kept) >= self.max_ops:
                # valid but over the op budget: record, don't discard the whole reply
                rejected.append({"path": op.get("path"), "reason": "too_many_ops"})
            else:
                kept.append({**op, "rationale": str(op.get("rationale", ""))[:300]})
        self.rejected.extend(rejected)
        if not kept:
            raise MutationParseError("all_ops_rejected", json.dumps(rejected)[:400])
        return Patch({"ops": kept, "rationale": str(payload.get("rationale", ""))[:500]})

    # -- mutator contract ----------------------------------------------
    def _fallback(self, parent: Patch, inspire, reason: str) -> Patch:
        self.fallbacks += 1
        self.last_fallback_reason = reason
        self.disclosure = f"llm_ideation_mutation_with_demo_fallback:{reason}"
        return self.fallback(parent, inspire)

    def __call__(self, parent: Patch, inspire=None) -> Patch:
        self.calls += 1
        prompt = self._build_prompt(parent, inspire)
        last: MutationParseError | None = None
        for attempt in range(self.attempts):
            ask = prompt
            if attempt:
                ask = (prompt + "\n\nYour previous reply was REJECTED (" +
                       (last.reason if last else "invalid") + "). Return ONLY one JSON "
                       "object with an `ops` array; no prose, no fences, no examples.")
            try:
                text = self._complete(ask)
            except Exception as e:  # host_mode/config/network: retrying cannot help
                self.last_error = f"provider_error: {e}"
                return self._fallback(parent, inspire, "provider_error")
            try:
                return self._payload_to_patch(_extract_patch_payload(text))
            except MutationParseError as e:
                last = e
                self.last_error = str(e)
        return self._fallback(parent, inspire, "parse_failure")


def _default_providers():
    """Indirection so tests can stub provider construction without keys."""
    from .providers import Providers
    return Providers()


def build_mutator(*, providers=None, repo_root: Path | None = None,
                  signals: list[dict] | None = None) -> tuple:
    """Choose the mutation operator and return (mutator, disclosure_info).

    Degradation is NEVER silent: every demo-template path carries a
    `demo_template:<reason>` disclosure code (project paradigm: doi_gate's
    `doi_online_unverified`, fairness's `scope=ledger_only`).
    """
    if os.environ.get("SCIFORGE_EVOLVE_MUTATOR", "").lower() == "demo":
        return _demo_mutator(), {"mode": "demo_template", "degraded": True,
                                 "disclosure": "demo_template:forced_by_env",
                                 "reason": "SCIFORGE_EVOLVE_MUTATOR=demo"}
    if providers is None:
        try:
            providers = _default_providers()
        except Exception as e:
            return _demo_mutator(), {"mode": "demo_template", "degraded": True,
                                     "disclosure": "demo_template:no_provider",
                                     "reason": str(e)[:300]}
    if getattr(providers, "host_mode", False):
        return _demo_mutator(), {"mode": "demo_template", "degraded": True,
                                 "disclosure": "demo_template:host_mode",
                                 "reason": "providers report host_mode (no API key / gateway);"
                                           " LLM work belongs to the host agent"}
    m = LLMMutator(providers, fallback=_demo_mutator(), repo_root=repo_root,
                   signals=signals)
    return m, m.info()


def _golden_checks(root: Path | None = None, fast: bool = False) -> list[dict]:
    """fast=True: only the quick gate subsets (demo/iteration); full = + ci_check.
    `submit` ALWAYS runs the full ci_check post-merge regardless of this flag."""
    cfg = _load_config()
    root = root or REPO_ROOT
    py = sys.executable  # the venv running the kernel — scratch gates must not use system python
    checks = []
    for c in cfg.get("gate_checks", []):
        if fast and c.get("id") == "ci_scratch":
            continue
        cmd = c.get("cmd", "").replace("${SCIFORGE_PY:-python3}", py)
        checks.append({**c, "cmd": cmd})
    if not fast:
        checks.append({"id": "ci_check",
                       "cmd": f"{py} {root / 'scripts' / 'ci_check.py'} --repo-root {root}",
                       "timeout": 1800, "hard": ["ci_check"]})
    return checks


def run_evolve_cli(a) -> int:
    ws = a.workspace
    (ws / ".sciforge").mkdir(parents=True, exist_ok=True)
    cfg = _load_config()
    # 1. signals from archives
    sigs = []
    if ws.is_dir():
        for run_dir in sorted(ws.iterdir()):
            if (run_dir / ".sciforge" / "events.ndjson").exists():
                sigs.append(audit_run(run_dir))
    if not sigs:
        # no archives yet: use a synthetic seed proposal to validate the machinery
        sigs = []
    # 2. proposals
    props = proposals_from_signals(sigs, REPO_ROOT) if sigs else []
    prop_file = a.proposes
    if prop_file and prop_file.exists():
        props = json.loads(prop_file.read_text())["proposals"]
    if not props:
        print(json.dumps({"status": "no_proposals",
                          "hint": "pass --proposes <patches.json> (from audit) or complete runs first"},
                         indent=2))
        return 1
    # 3. domain + shards — evolution runs on a SCRATCH checkout clone, never the
    # live repo (S16 hard line); gates also run inside it so they measure the PATCHED tree.
    evo_ws = _evo_workspace(cfg)
    evo_ws.mkdir(parents=True, exist_ok=True)
    scratch = evo_ws / f"checkout_{int(time.time())}"
    subprocess.run(["git", "clone", "-q", str(REPO_ROOT), str(scratch)], timeout=300, check=True)
    gate = GateDomain(_golden_checks(scratch, fast=getattr(a, "fast", False)))
    # One provider instance shared by judge + mutator (same credentials, same ledger).
    providers = None
    try:
        providers = _default_providers()
    except Exception:
        providers = None
    judge = None
    if providers is not None and not getattr(providers, "host_mode", True):
        try:
            judge = JudgeDomain(providers, rubric_path=cfg.get("rubric_path"))
        except Exception:
            judge = None
    domain = HybridDomain(gate, judge) if judge else gate
    seed = Patch({"ops": props[0]["ops"] if "ops" in props[0] else [props[0]]})
    # shard_check: candidate may only touch editable paths (structural guard;
    # EvolutionRun._mutate applies the same guard to every mutation as well).
    def shard_check(patch: Patch) -> bool:
        return not validate_patch(patch)
    mutator, mutator_info = build_mutator(providers=providers, repo_root=scratch,
                                          signals=sigs)
    er = EvolutionRun(scratch, domain, mutator, algorithm=a.algorithm,
                      budget=a.budget, seed_patch=seed, shard_check=shard_check)
    er.note("mutator_selected", **mutator_info)
    # rewire apply to scratch
    from . import evolve as evolve_mod
    orig_apply = evolve_mod.apply_patch
    orig_revert = evolve_mod.revert_patch
    def scratch_apply(ws, patch, checkout=None):
        return orig_apply(ws, patch, checkout=scratch)
    def scratch_revert(ws, applied):
        if applied:
            subprocess.run(["git", "checkout", "--", *applied], cwd=str(scratch), capture_output=True)
    evolve_mod.apply_patch = scratch_apply
    evolve_mod.revert_patch = scratch_revert
    try:
        result = er.run()
    finally:
        evolve_mod.apply_patch = orig_apply
        evolve_mod.revert_patch = orig_revert
        mutator_report = mutator.info() if hasattr(mutator, "info") else mutator_info
        er.note("mutator_summary", **mutator_report)
    # 5. winner -> extensions
    out = {"result_status": result.get("status"),
           "best_score": result.get("best_score"),
           "held_out": result.get("held_out"),
           "events": result.get("events"),
           "expanded": len(result.get("history", [])),
           "scratch": str(scratch),
           "mutator": mutator_report}
    if result.get("status") == "done" and result.get("best_score", 0) > 0.6:
        run_id = f"evo_{int(time.time())}"
        ext = ws / ".sciforge" / "skill-extensions" / run_id
        ext.mkdir(parents=True, exist_ok=True)
        (ext / "patch.json").write_text(json.dumps(result["best_patch"], indent=2, ensure_ascii=False))
        (ext / "meta.json").write_text(json.dumps({
            "run_id": run_id, "score": result["best_score"], "held_out": result.get("held_out"),
            "created_at": time.time(), "status": "PENDING_HUMAN_MERGE",
            "mutator": mutator_report}, indent=2))
        out["extension"] = str(ext)
        out["next"] = f"sciforge-kernel submit --workspace {ws} {run_id}"
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["result_status"] == "done" else 1


def _git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    # resolve REPO_ROOT at call time so tests/monkeypatching see the right tree
    return subprocess.run(["git", *args], cwd=str(cwd or REPO_ROOT),
                          capture_output=True, text=True)


def _run_ci_check(root: Path) -> subprocess.CompletedProcess:
    """CI on the patched tree. Indirection keeps tests network/subprocess-free."""
    return subprocess.run([sys.executable, str(Path(root) / "scripts" / "ci_check.py")],
                          capture_output=True, text=True, timeout=1800)


def _safe_branch_fragment(run_id: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", str(run_id)).strip("-.")
    return s[:80] or "run"


def _commit_cmd(msg: str) -> list[str]:
    return ["git", "-c", "user.name=sciforge-evolve", "-c",
            "user.email=evolve@sciforge.local", "commit", "-m", msg]


def submit_patch(a) -> int:
    """Human-authorized landing of an evolved skill patch.

    Default: land on an isolated `evolve/<run_id>` branch, run ci_check there,
    commit THERE, then return to the original branch — master never moves without
    a human merge. Output carries the reviewable diffstat and the exact merge /
    push / PR commands. Opt into the legacy direct-to-current-branch behavior with
    `--direct` (CLI) or SCIFORGE_EVOLVE_DIRECT=1 (unattended CI). The CLI parser
    lives in cli.py; this function reads `getattr(a, "direct", False)` so the flag
    works as soon as it is declared there.
    """
    ext = a.workspace / ".sciforge" / "skill-extensions" / a.run_id
    meta = json.loads((ext / "meta.json").read_text())
    if meta["status"] != "PENDING_HUMAN_MERGE":
        print(json.dumps({"status": "rejected", "reason": f"state={meta['status']}"}))
        return 1
    patch = Patch({"ops": json.loads((ext / "patch.json").read_text())})
    # Refuse malformed / frozen / traversal ops wholesale at the human boundary:
    # a human-authored patch.json gets no benefit of the doubt (mutator output is
    # additionally stripped, but submit must never apply an op it cannot audit).
    bad = validate_patch(patch)
    if bad:
        print(json.dumps({"status": "rejected", "reason": "invalid_patch",
                          "detail": bad}, indent=2, ensure_ascii=False))
        return 1
    msg = (f"evolve({a.run_id}): merge skill patch score={meta['score']:.2f} "
           f"held_out={meta.get('held_out')}")
    direct = bool(getattr(a, "direct", False)) or os.environ.get("SCIFORGE_EVOLVE_DIRECT") == "1"
    if direct:
        return _submit_direct(ext, meta, patch, msg)
    return _submit_branch(a, ext, meta, patch, msg)


def _submit_direct(ext: Path, meta: dict, patch: Patch, msg: str) -> int:
    """Legacy behavior: apply + ci + commit on the current branch (explicit opt-in)."""
    res = apply_patch(REPO_ROOT, patch, checkout=REPO_ROOT)
    if not res["ok"]:
        from .evolve import revert_patch
        revert_patch(REPO_ROOT, res.get("applied", []))  # partial apply is reverted
        print(json.dumps({"status": "rejected", "detail": res}, ensure_ascii=False))
        return 1
    ci = _run_ci_check(REPO_ROOT)
    if ci.returncode != 0:
        from .evolve import revert_patch
        revert_patch(REPO_ROOT, res["applied"])
        print(json.dumps({"status": "rolled_back", "reason": "ci_check failed post-merge",
                          "tail": (ci.stdout + ci.stderr)[-800:]}, ensure_ascii=False))
        return 1
    add = _git(["add", *res["applied"]], REPO_ROOT)
    if add.returncode != 0:
        print(json.dumps({"status": "error", "reason": "git_add_failed",
                          "tail": (add.stdout + add.stderr)[-400:]}, ensure_ascii=False))
        return 1
    commit = subprocess.run(_commit_cmd(msg), cwd=str(REPO_ROOT),
                            capture_output=True, text=True)
    if commit.returncode != 0:
        print(json.dumps({"status": "error", "reason": "commit_failed",
                          "tail": (commit.stdout + commit.stderr)[-400:]}, ensure_ascii=False))
        return 1
    meta["status"] = "MERGED"
    meta["merged_at"] = time.time()
    (ext / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({"status": "merged", "applied": res["applied"], "commit": msg},
                     ensure_ascii=False))
    return 0


def _submit_branch(a, ext: Path, meta: dict, patch: Patch, msg: str) -> int:
    """Apply+ci+commit on `evolve/<run_id>`; restore the original branch afterwards."""
    root = REPO_ROOT
    # Tracked-file changes only: untracked files are never staged by the
    # path-scoped `git add` below and do not compromise the review commit.
    dirty = [ln for ln in _git(["status", "--porcelain"], root).stdout.splitlines()
             if ln.strip() and not ln.startswith("??")]
    if dirty:
        print(json.dumps({"status": "rejected", "reason": "dirty_worktree",
                          "detail": dirty[:10],
                          "hint": "commit or stash your changes; a branch landing must be "
                                  "an isolated, reviewable commit"},
                         indent=2, ensure_ascii=False))
        return 1
    base_branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
    base_commit = _git(["rev-parse", "HEAD"], root).stdout.strip()
    detached = base_branch in ("", "HEAD")
    branch = f"evolve/{_safe_branch_fragment(a.run_id)}"
    if _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], root).returncode == 0:
        branch = f"{branch}-{int(time.time())}"  # never reuse/overwrite a review branch
    co = _git(["checkout", "-b", branch], root)
    if co.returncode != 0:
        print(json.dumps({"status": "error", "reason": "branch_create_failed",
                          "tail": (co.stdout + co.stderr)[-400:]}, ensure_ascii=False))
        return 1

    def _restore(drop_branch: bool):
        if detached:
            _git(["checkout", "--detach", base_commit], root)
        else:
            _git(["checkout", base_branch], root)
        if drop_branch:
            _git(["branch", "-d", branch], root)

    res = apply_patch(root, patch, checkout=root)  # real repo only at submit time
    if not res["ok"]:
        from .evolve import revert_patch
        revert_patch(root, res.get("applied", []))  # partial apply is reverted
        _restore(drop_branch=True)
        print(json.dumps({"status": "rejected", "detail": res}, ensure_ascii=False))
        return 1
    # CI gate MUST pass on the patched tree before the branch commit exists.
    ci = _run_ci_check(root)
    if ci.returncode != 0:
        from .evolve import revert_patch
        revert_patch(root, res["applied"])
        _restore(drop_branch=True)
        print(json.dumps({"status": "rolled_back", "reason": "ci_check failed pre-commit",
                          "tail": (ci.stdout + ci.stderr)[-800:]}, ensure_ascii=False))
        return 1
    add = _git(["add", *res["applied"]], root)
    if add.returncode != 0:
        from .evolve import revert_patch
        revert_patch(root, res["applied"])
        _restore(drop_branch=True)
        print(json.dumps({"status": "error", "reason": "git_add_failed",
                          "tail": (add.stdout + add.stderr)[-400:]}, ensure_ascii=False))
        return 1
    commit = subprocess.run(_commit_cmd(msg), cwd=str(root), capture_output=True, text=True)
    if commit.returncode != 0:
        from .evolve import revert_patch
        revert_patch(root, res["applied"])
        _restore(drop_branch=True)
        print(json.dumps({"status": "error", "reason": "commit_failed",
                          "tail": (commit.stdout + commit.stderr)[-400:]}, ensure_ascii=False))
        return 1
    branch_commit = _git(["rev-parse", "HEAD"], root).stdout.strip()
    diffstat = _git(["diff", "--stat", f"{base_commit}..{branch}"], root).stdout.strip()
    changed = [x for x in _git(["diff", "--name-only", f"{base_commit}..{branch}"],
                               root).stdout.strip().splitlines() if x]
    back = (_git(["checkout", "--detach", base_commit], root) if detached
            else _git(["checkout", base_branch], root))
    meta.update({"status": "BRANCH_READY", "branch": branch,
                 "base_branch": None if detached else base_branch,
                 "base_commit": base_commit, "branch_commit": branch_commit,
                 "diffstat": diffstat, "updated_at": time.time()})
    (ext / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    out = {
        "status": "branch_ready",
        "branch": branch,
        "base_branch": None if detached else base_branch,
        "base_commit": base_commit,
        "commit": branch_commit,
        "applied": res["applied"],
        "changed_files": changed,
        "diffstat": diffstat,
        "review_command": f"git diff {base_commit}..{branch}",
        "merge_command": f"git merge --no-ff {branch}",
        "push_command": f"git push -u origin {branch}",
        "pr_command": (f"gh pr create --head {branch} --base "
                       f"{base_branch if not detached else '<default>'} "
                       f"--title \"evolve: {a.run_id}\" --body-file /dev/stdin"),
        "note": "master untouched; merge is a human decision",
    }
    if back.returncode != 0:
        out["warning"] = "restore_failed: you are still on the evolution branch"
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def daily_digest(ws: Path) -> str:
    """Plain-text daily report (S17): runs, budgets, evolution rounds, pending merges."""
    lines = [f"# SciForge daily digest — {time.strftime('%Y-%m-%d')}", ""]
    n_runs = 0
    if ws.is_dir():
        for d in sorted(ws.iterdir()):
            rs = d / ".sciforge" / "RUNSTATE.json"
            if not rs.exists():
                continue
            n_runs += 1
            try:
                s = json.loads(rs.read_text())
                lines.append(f"- {s.get('run_id')}: phase {s.get('current_phase')} "
                             f"[{s.get('status')}] budget ${json.loads((d / '.sciforge' / 'verdicts' / 'RUN_BUDGET.json').read_text()).get('api_cost_usd', 0):.2f}")
            except Exception:
                lines.append(f"- {d.name}: (unreadable state)")
    ext = ws / ".sciforge" / "skill-extensions"
    if ext.exists():
        for e in sorted(ext.iterdir()):
            try:
                m = json.loads((e / "meta.json").read_text())
                lines.append(f"- evolution {e.name}: {m['status']} score={m['score']:.2f}")
            except Exception:
                pass
    lines.append(f"\ntotal runs: {n_runs}")
    return "\n".join(lines)
