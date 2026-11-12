#!/usr/bin/env python3
"""Full-code smoke gate, kernel-enforced (v1.6 A3; v1.7.3 real re-execution).

The contract (experiment-execution Step 5.0) makes .SMOKE.json load-bearing
evidence: "a full dispatch that completes without first writing .SMOKE.json is
invalid regardless of whether the experiment ultimately succeeded" — the buried-
subsection skip was a real, observed failure (Q-SGD-BS-GAP ran 184s with no
smoke). prose said MANDATORY; here the kernel checks it at the 6c boundary.

v1.7.3 upgrade — a JSON file claiming PASS is no longer sufficient:
  1. record checks (unchanged): every experiments/full/**/DISPATCH.json /
     STATUS.json group must have a sibling {experiment_id}.SMOKE.json with
     smoke_result=PASS and status_row_written=true. A smoke record belongs to
     at most one group; a root-level record with an un-related name is only a
     catch-all for single-group runs (v1.7.4), so one shared file cannot
     launder several groups.
  2. freshness cross-validation: the smoke record should carry the tested
     script's content hash (`script` + `script_sha256`) and execution time.
     A script whose current bytes differ from the recorded hash is a STALE
     smoke => FAIL. Without a hash we fall back to executed_at vs mtime and
     disclose `smoke_no_script_hash` (WARN), never a silent PASS.
  3. real re-execution: when the tested script/command can be derived, the
     smoke slice is executed once inside the kernel sandbox
     (kernel/sciforge/execution.py: Seatbelt/bwrap) with a hard timeout.
     non-zero exit, a Python traceback, or timeout => FAIL. This closes the
     "wrote a JSON instead of running the code" cheat.
  4. honest degradation: if the script is missing, no hash/command can be
     derived, or no sandbox is available, the gate reports WARN + a
     reason_code (exit 0 so legacy runs are not hard-broken) and records the
     disclosure in stdout. It never reports PASS for an unexecuted smoke.

Usage: python3 scripts/smoke_gate.py <workspace> [--timeout S] [--no-exec]
       [--allow-unsandboxed] [--json]
Exit: 0 PASS/WARN/SKIP, 2 FAIL (missing/failed/stale smokes or re-exec failure).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNEL = REPO_ROOT / "kernel"
TRACEBACK_MARK = "Traceback (most recent call last)"
STEP_FLAGS = ("--max-steps", "--max_steps", "--steps", "--max-epochs",
              "--max_epochs", "--epochs", "--max-batches", "--max_batches",
              "--limit")
SANDBOX_ERR_RE = re.compile(r"^\s*(sandbox-exec|bwrap):", re.M)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _load_json(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_hash(v) -> str:
    s = str(v or "").strip().lower()
    return s[7:] if s.startswith("sha256:") else s


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _group_match(a, b) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a.startswith("group_"):
        a = a[6:]
    if b.startswith("group_"):
        b = b[6:]
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4:
        return a in b or b in a
    return False


def _parse_time(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# artifact discovery
# ---------------------------------------------------------------------------
def _smoke_records(ws: Path) -> list[dict]:
    out = []
    for f in sorted((ws / "experiments" / "full").rglob("*.SMOKE.json")):
        d = _load_json(f)
        if isinstance(d, dict):
            out.append({"path": f, "data": d, "unreadable": False})
        else:
            out.append({"path": f, "data": {"smoke_result": "FAIL",
                                            "fail_code": "unreadable_smoke_file"},
                        "unreadable": True})
    return out


def _dispatch_records(ws: Path) -> list[dict]:
    out = []
    root = ws / "experiments" / "full"
    paths = sorted(set(root.rglob("DISPATCH.json")) |
                   set(root.rglob("FULL_EXPERIMENT_DISPATCH.json")))
    for f in paths:
        d = _load_json(f)
        out.append({"path": f, "data": d if isinstance(d, dict) else {}})
    return out


def _find_smoke(group: str, group_dir: Path, full: Path,
                smokes: list[dict], n_groups: int = 1,
                consumed: set[Path] | None = None) -> tuple[dict | None, list[str]]:
    """Prefer a smoke living beside its group. A single global smoke may cover
    a single-group run (disclosed); with several dispatched groups every group
    needs its own sibling smoke — one file must not launder the others.

    A record belongs to at most one group. `consumed` carries the records
    already assigned in this gate run (defence in depth), and the un-named
    root-level catch-all is restricted to single-group runs: in a multi-group
    run a root-level file is only admitted when its name binds it to this
    group (`<group>.SMOKE.json`), so one shared record cannot satisfy two
    groups. The `_ungrouped` shape (results directly under experiments/full/)
    stays legal because there the group dir IS the root and the sibling rules
    apply first.
    """
    taken = consumed if consumed is not None else set()

    def take(rec: dict, notes: list[str]) -> tuple[dict, list[str]]:
        taken.add(rec["path"])
        return rec, notes

    for rec in smokes:
        if rec["path"] in taken:
            continue
        if rec["path"].parent == group_dir and rec["path"].name == f"{group}.SMOKE.json":
            return take(rec, [])
    for rec in smokes:
        if rec["path"] in taken:
            continue
        if rec["path"].parent == group_dir:
            return take(rec, [])
    for rec in smokes:
        if rec["path"] in taken:
            continue
        if rec["path"].parent == full and rec["path"].name == f"{group}.SMOKE.json":
            return take(rec, [])
    if n_groups <= 1:
        for rec in smokes:
            if rec["path"] in taken:
                continue
            if rec["path"].parent == full:
                return take(rec, [])
    if len(smokes) == 1 and n_groups <= 1 and smokes[0]["path"] not in taken:
        return take(smokes[0], ["smoke_matched_by_fallback"])
    return None, []


def _resolve_rel(ws: Path, rel: str) -> Path | None:
    rel = str(rel).strip()
    if not rel:
        return None
    p = Path(rel)
    tries = [p] if p.is_absolute() else [ws / p]
    if not p.is_absolute() and rel.startswith("code/"):
        tries += [ws / "src" / rel[5:], ws / rel[5:], ws / "experiments" / rel[5:]]
    for t in tries:
        if t.is_file():
            return t
    name = p.name
    for base in (ws / "src", ws / "experiments", ws / "code"):
        if base.is_dir():
            hits = sorted(base.rglob(name))
            if hits:
                return hits[0]
    return None


def _resolve_script(ws: Path, group: str, group_dir: Path,
                    smoke: dict, dispatch: dict, matrix: dict | None) -> Path | None:
    declared = []
    for src in (smoke, dispatch):
        for key in ("script", "script_path", "target_script"):
            v = src.get(key) if isinstance(src, dict) else None
            if isinstance(v, str) and v:
                declared.append(v)
    groups = (matrix or {}).get("groups") if isinstance(matrix, dict) else None
    for g in groups or []:
        if isinstance(g, dict) and _group_match(group, g.get("name", "")):
            if isinstance(g.get("script"), str):
                declared.append(g["script"])
    for rel in declared:
        p = _resolve_rel(ws, rel)
        if p:
            return p
    # convention: src/experiments/full/<group>.py or the group dir's sole .py
    for cand in (ws / "src" / "experiments" / "full" / f"{group}.py",
                 ws / "experiments" / "full" / f"{group}.py",
                 ws / "src" / "experiments" / "full" / f"group_{group}.py"):
        if cand.is_file():
            return cand
    if group_dir.is_dir():
        pys = sorted(group_dir.glob("*.py"))
        if len(pys) == 1:
            return pys[0]
    return None


def _detect_step_flag(script: Path) -> str | None:
    try:
        text = script.read_text(errors="replace")[:300000]
    except OSError:
        return None
    for flag in STEP_FLAGS:
        if flag in text:
            return flag
    return None


def _command_for(ws: Path, group: str, smoke: dict, dispatch: dict,
                 script: Path | None) -> tuple[list[str] | None, list[str]]:
    cmd = smoke.get("smoke_cmd") or smoke.get("reexec_cmd") or \
        (dispatch.get("smoke_cmd") if isinstance(dispatch, dict) else None)
    subst = {"python": sys.executable, "script": str(script or ""),
             "workspace": str(ws), "group": group}
    if isinstance(cmd, str) and cmd.strip():
        try:
            return shlex.split(cmd.format(**subst)), []
        except (KeyError, ValueError):
            return None, ["smoke_cmd_unresolvable"]
    if isinstance(cmd, list) and cmd:
        try:
            return [str(x).format(**subst) for x in cmd], []
        except (KeyError, ValueError):
            return None, ["smoke_cmd_unresolvable"]
    if script is None:
        return None, ["smoke_script_missing"]
    args = smoke.get("smoke_args") or (dispatch.get("smoke_args")
                                       if isinstance(dispatch, dict) else None) or []
    if isinstance(args, str):
        args = shlex.split(args)
    if not isinstance(args, list):
        args = []
    reasons: list[str] = []
    if not args:
        flag = _detect_step_flag(script)
        if flag:
            args = [flag, "1"]
        else:
            reasons.append("no_step_cap_flag")
    return [sys.executable, str(script), *[str(a) for a in args]], reasons


# ---------------------------------------------------------------------------
# freshness: recorded hash / timestamp vs the script on disk
# ---------------------------------------------------------------------------
def _freshness(script: Path | None, smoke: dict) -> dict:
    recorded = (smoke.get("script_sha256") or smoke.get("script_sha")
                or smoke.get("code_sha"))
    if isinstance(recorded, dict):
        picked = None
        if script is not None:
            for k, v in recorded.items():
                if Path(str(k)).name == script.name:
                    picked = v
                    break
        recorded = picked if picked is not None else next(iter(recorded.values()), None)
    if isinstance(recorded, str) and recorded.strip():
        if script is None:
            return {"status": "WARN", "reason_codes": ["smoke_script_missing"],
                    "recorded_sha256": _norm_hash(recorded)}
        try:
            actual = _sha256_file(script)
        except OSError:
            return {"status": "WARN", "reason_codes": ["smoke_script_missing"]}
        if _norm_hash(recorded) != actual:
            return {"status": "FAIL",
                    "reason_codes": ["stale_smoke_script_hash_mismatch"],
                    "recorded_sha256": _norm_hash(recorded), "actual_sha256": actual}
        return {"status": "PASS", "reason_codes": [], "actual_sha256": actual}
    # no content hash: executed_at vs mtime is a cheap but weaker signal
    ts = _parse_time(smoke.get("executed_at") or smoke.get("executed"))
    if script is not None and ts is not None:
        try:
            if script.stat().st_mtime > ts + 2:
                return {"status": "FAIL",
                        "reason_codes": ["stale_smoke_script_newer_than_smoke"],
                        "script_mtime": script.stat().st_mtime, "executed_at": ts}
        except OSError:
            return {"status": "WARN", "reason_codes": ["smoke_script_missing"]}
        return {"status": "WARN", "reason_codes": ["smoke_no_script_hash"]}
    return {"status": "WARN", "reason_codes": ["smoke_unbound_to_script"]}


# ---------------------------------------------------------------------------
# sandbox + execution
# ---------------------------------------------------------------------------
def _seatbelt_profile(ws: Path) -> list[str]:
    """Fallback profile: execution.sandbox_cmd's `(allow signal *)` is rejected
    by newer macOS Seatbelt parsers (observed on Darwin 27)."""
    prof = ("(version 1)(allow file-read*)(allow process*)(allow signal)"
            f'(allow file-write* (subpath "{ws.resolve()}") '
            '(subpath "/tmp")(subpath "/private/tmp"))(deny network*)')
    return ["sandbox-exec", "-p", prof]


def _probe(prefix: list[str]) -> bool:
    true_bin = "/usr/bin/true" if Path("/usr/bin/true").exists() else "/bin/true"
    try:
        p = subprocess.run(prefix + [true_bin], capture_output=True, text=True,
                           timeout=5, stdin=subprocess.DEVNULL)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _sandbox_prefix(ws: Path, sandbox_wrap=None):
    if sandbox_wrap is not None:
        return sandbox_wrap(ws)
    if str(KERNEL) not in sys.path:
        sys.path.insert(0, str(KERNEL))
    try:
        from sciforge.execution import sandbox_cmd
        prefix = sandbox_cmd(ws, net=False)
    except Exception:
        return None
    if not prefix:
        return None
    prog = Path(prefix[0]).name
    if prog == "sandbox-exec":
        if _probe(prefix):
            return prefix
        fallback = _seatbelt_profile(ws)
        return fallback if _probe(fallback) else None
    if prog == "bwrap":
        return prefix if _probe(prefix) else None
    return prefix


def _invoke(ws: Path, prefix: list[str], argv: list[str], timeout: float) -> dict:
    env = dict(os.environ)
    env.setdefault("MPLBACKEND", "Agg")
    env["SCIFORGE_SMOKE"] = "1"
    py_path = env.get("PYTHONPATH", "")
    parts = [str(KERNEL)]
    # macOS sandbox-exec resolves the venv shim before exec, so a sandboxed
    # .venv/bin/python behaves as the system interpreter and cannot import the
    # venv's packages (S01 real run: every re-execution died on "No module
    # named numpy" while the same command passed unsandboxed). Carry the venv
    # site-packages across explicitly.
    if prefix:
        try:
            if str(KERNEL) not in sys.path:
                sys.path.insert(0, str(KERNEL))
            from sciforge.execution import venv_site_packages
            parts = venv_site_packages(argv[0]) + parts
        except Exception:
            pass
    if py_path:
        parts.append(py_path)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    t0 = time.monotonic()
    try:
        p = subprocess.run(prefix + argv, cwd=str(ws), capture_output=True,
                           text=True, timeout=timeout, env=env,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "reason_codes": ["smoke_timeout"],
                "timeout_s": timeout, "duration_s": round(time.monotonic() - t0, 2)}
    except OSError as e:
        return {"status": "WARN", "reason_codes": ["sandbox_execution_failed"],
                "detail": str(e), "duration_s": round(time.monotonic() - t0, 2)}
    err = (p.stderr or "") + "\n" + (p.stdout or "")
    result = {"returncode": p.returncode,
              "duration_s": round(time.monotonic() - t0, 2),
              "stdout_tail": (p.stdout or "")[-2000:],
              "stderr_tail": (p.stderr or "")[-2000:]}
    if p.returncode != 0 and SANDBOX_ERR_RE.search(p.stderr or ""):
        result.update(status="WARN", reason_codes=["sandbox_execution_failed"])
        return result
    if p.returncode != 0:
        result.update(status="FAIL", reason_codes=["smoke_nonzero_exit"])
        return result
    if TRACEBACK_MARK in err:
        result.update(status="FAIL", reason_codes=["smoke_traceback"])
        return result
    result.update(status="PASS", reason_codes=[])
    return result


def _execute(ws: Path, argv: list[str], timeout: float, sandbox_wrap,
             allow_unsandboxed: bool) -> dict:
    prefix = _sandbox_prefix(ws, sandbox_wrap)
    if prefix is None:
        if not allow_unsandboxed:
            return {"executed": False, "status": "WARN",
                    "reason_codes": ["sandbox_unavailable"]}
        res = _invoke(ws, [], argv, timeout)
        res["executed"] = True
        res["reason_codes"] = sorted(set(res.get("reason_codes", []) +
                                         ["executed_unsandboxed"]))
        if res.get("status") == "PASS":
            res["status"] = "WARN"  # ran, but outside the kernel sandbox
        return res
    res = _invoke(ws, prefix, argv, timeout)
    if "sandbox_execution_failed" in res.get("reason_codes", []) and allow_unsandboxed:
        retry = _invoke(ws, [], argv, timeout)
        retry["executed"] = True
        retry["reason_codes"] = sorted(set(retry.get("reason_codes", []) +
                                           ["executed_unsandboxed"]))
        if retry.get("status") == "PASS":
            retry["status"] = "WARN"
        return retry
    res["executed"] = res.get("status") != "WARN" or \
        "sandbox_execution_failed" not in res.get("reason_codes", [])
    return res


# ---------------------------------------------------------------------------
# gate driver
# ---------------------------------------------------------------------------
# Reasons for "nothing was proved" that the agent cannot manufacture: this
# machine has no sandbox, the sandbox tool itself errored, record-only mode was
# requested, the gate's own execution budget ran out, or the security scanner
# could not be imported. These stay WARN — they are honest disclosures about
# the environment or the invocation, not about the agent's work.
UNPROVABLE_FOR_ENVIRONMENT = frozenset({
    "sandbox_unavailable", "sandbox_execution_failed", "reexec_disabled",
    "execution_budget_exhausted", "security_scan_unavailable",
})


def _smoke_evidence(doc: dict) -> str:
    """Classify one group's smoke evidence: "verified", "excused" or "none".

    verified — the gate proved the smoke itself: the recorded sha256 matched
               the script bytes on disk, or the slice was really re-executed
               (including outside the sandbox, which is separately disclosed).
    excused  — nothing was proved, for a reason the agent cannot fake.
    none     — nothing was proved and the reason IS agent-controllable (no
               script declared or found, no hash, no runnable command).
               Omitting those fields would otherwise let the 6c boundary rest
               entirely on a self-written "smoke_result": "PASS" string.
    """
    if (doc.get("freshness") or {}).get("status") == "PASS":
        return "verified"
    ex = doc.get("execution") or {}
    if ex.get("executed") is True:
        return "verified"
    if UNPROVABLE_FOR_ENVIRONMENT & set(ex.get("reason_codes") or []):
        return "excused"
    return "none"


def check(ws: Path, *, execute: bool = True, timeout: float = 90.0,
          total_timeout: float = 300.0, max_executions: int = 8,
          allow_unsandboxed: bool = False, sandbox_wrap=None,
          security_scan: bool = True) -> dict:
    ws = Path(ws)
    full = ws / "experiments" / "full"
    if not full.is_dir():
        return {"verdict": "SKIP", "reason_codes": ["no_full_experiments"],
                "groups": [], "executed": 0}
    markers = sorted(list(full.rglob("DISPATCH.json")) +
                     list(full.rglob("FULL_EXPERIMENT_DISPATCH.json")) +
                     list(full.rglob("STATUS.json")))
    # A marker sitting directly in experiments/full/ is the stage-level
    # aggregate, not a group, whenever at least one subdirectory is itself a
    # group. Counting the aggregate as a group made the S01 run demand a
    # `full.SMOKE.json` next to per-group smokes that were all present — a
    # false positive on a normal layout. With no subdirectory groups the root
    # marker IS the only group, which the single-group path below handles.
    sub_markers = [m for m in markers if m.parent != full]
    chosen = sub_markers if sub_markers else markers
    groups = sorted({m.parent.name for m in chosen})
    if not groups and not any(full.rglob("*.py")):
        return {"verdict": "SKIP", "reason_codes": ["nothing_dispatched"],
                "groups": [], "executed": 0}

    smokes = _smoke_records(ws)
    dispatches = _dispatch_records(ws)
    matrix = _load_json(ws / ".sciforge" / "verdicts" / "EXPERIMENT_MATRIX.json")
    executions = 0
    started = time.monotonic()
    group_docs: list[dict] = []
    consumed_smokes: set[Path] = set()  # one smoke record -> at most one group

    for g in groups or ["_ungrouped"]:
        group_dir = full / g if g != "_ungrouped" else full
        label = g if g != "_ungrouped" else "full"
        doc = {"group": label, "smoke": None, "record": None,
               "freshness": None, "execution": None, "problems": [],
               "notes": []}
        smoke, match_notes = _find_smoke(label, group_dir, full, smokes,
                                        n_groups=len(groups),
                                        consumed=consumed_smokes)
        doc["notes"] += match_notes
        doc["problems"] += match_notes
        if smoke is None:
            doc["problems"].append(
                f"group '{label}': no {label}.SMOKE.json — smoke gate skipped "
                f"(buried-subsection failure class; Step 5.0 is load-bearing)")
            doc["record"] = {"status": "FAIL", "reason_codes": ["missing_smoke"]}
            group_docs.append(doc)
            continue
        doc["smoke"] = str(smoke["path"].relative_to(ws))
        s = smoke["data"]
        rec_reasons: list[str] = []
        if smoke["unreadable"]:
            rec_reasons.append("unreadable_smoke_file")
        elif s.get("smoke_result") != "PASS":
            rec_reasons.append("smoke_result_not_pass")
        elif s.get("status_row_written") is not True:
            rec_reasons.append("status_row_missing")
        doc["record"] = {"status": "FAIL" if rec_reasons else "PASS",
                         "reason_codes": rec_reasons}
        if rec_reasons:
            doc["problems"].append(
                f"group '{label}': smoke_result={s.get('smoke_result')} "
                f"fail_code={s.get('fail_code')} "
                f"status_row_written={s.get('status_row_written')!r}")
            group_docs.append(doc)
            continue

        dispatch = next((d["data"] for d in dispatches
                         if d["path"].parent == smoke["path"].parent), {})
        script = _resolve_script(ws, label, group_dir, s, dispatch, matrix)
        fresh = _freshness(script, s)
        try:
            rel_script = str(script.relative_to(ws)) if script else None
        except ValueError:
            rel_script = str(script) if script else None
        doc["freshness"] = {**fresh, "script": rel_script}
        if fresh["status"] == "FAIL":
            doc["problems"].append(
                f"group '{label}': stale smoke — "
                + ", ".join(fresh["reason_codes"]))
            group_docs.append(doc)
            continue

        if not execute:
            doc["execution"] = {"executed": False, "status": "WARN",
                                "reason_codes": ["reexec_disabled"]}
            group_docs.append(doc)
            continue
        if executions >= max_executions or \
                time.monotonic() - started > total_timeout:
            doc["execution"] = {"executed": False, "status": "WARN",
                                "reason_codes": ["execution_budget_exhausted"]}
            group_docs.append(doc)
            continue
        argv, cmd_reasons = _command_for(ws, label, s, dispatch, script)
        if argv is None:
            doc["execution"] = {"executed": False, "status": "WARN",
                                "reason_codes": cmd_reasons or ["smoke_cmd_unresolvable"]}
            group_docs.append(doc)
            continue
        if security_scan and script is not None:
            if str(KERNEL) not in sys.path:
                sys.path.insert(0, str(KERNEL))
            try:
                from sciforge.gates import security_scan_script
                scan = security_scan_script(script)
                if scan.get("status") != "PASS":
                    doc["execution"] = {"executed": False, "status": "FAIL",
                                        "reason_codes": ["security_scan_blocked"],
                                        "detail": (scan.get("output") or "")[-1000:]}
                    group_docs.append(doc)
                    continue
            except Exception:
                doc["execution"] = {"executed": False, "status": "WARN",
                                    "reason_codes": ["security_scan_unavailable"]}
                group_docs.append(doc)
                continue
        per_timeout = max(1.0, min(float(timeout), 600.0))
        res = _execute(ws, argv, per_timeout, sandbox_wrap, allow_unsandboxed)
        if res.get("executed"):
            executions += 1
        # command-resolution notes (e.g. no_step_cap_flag) are disclosures,
        # not execution outcomes; keep them out of the WARN/FAIL reason set.
        res["notes"] = sorted(set(res.get("notes", []) + cmd_reasons))
        doc["execution"] = res
        if res.get("status") == "FAIL":
            doc["problems"].append(
                f"group '{label}': real smoke re-execution failed — "
                + ", ".join(res["reason_codes"]))
        group_docs.append(doc)

    fail = any((d.get("record") or {}).get("status") == "FAIL" or
               (d.get("freshness") or {}).get("status") == "FAIL" or
               (d.get("execution") or {}).get("status") == "FAIL"
               for d in group_docs)
    warn = any((d.get("freshness") or {}).get("status") == "WARN" or
               (d.get("execution") or {}).get("status") == "WARN" or
               d.get("problems") for d in group_docs)
    reasons = sorted({r for d in group_docs
                      for r in (d.get("record") or {}).get("reason_codes", []) +
                      (d.get("freshness") or {}).get("reason_codes", []) +
                      (d.get("execution") or {}).get("reason_codes", []) +
                      d.get("notes", [])})
    # Positive-evidence rule: a smoke record that is neither hash-verified nor
    # actually re-executed proves nothing — the boundary would then rest
    # entirely on the agent's own `"smoke_result": "PASS"` string, which is
    # exactly the failure mode this gate exists to close. Omitting `script` /
    # `script_sha256` is agent-controllable, so it cannot be a disclosure;
    # only reasons the agent cannot fake (no sandbox on this machine, the
    # caller passed --no-exec, the gate's own budget ran out) stay WARN.
    zero_evidence = [d.get("group") or "?" for d in group_docs
                     if _smoke_evidence(d) == "none"]
    if zero_evidence:
        fail = True
        reasons = sorted(set(reasons) | {"smoke_no_positive_evidence"})
    return {"verdict": "FAIL" if fail else ("WARN" if warn else "PASS"),
            "reason_codes": reasons, "groups": group_docs,
            "executed": executions}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--timeout", type=float, default=90.0,
                    help="per-group re-execution timeout in seconds (max 600)")
    ap.add_argument("--total-timeout", type=float, default=300.0,
                    help="re-execution budget across all groups")
    ap.add_argument("--max-executions", type=int, default=8)
    ap.add_argument("--no-exec", action="store_true",
                    help="record-only mode (discloses reexec_disabled WARN)")
    ap.add_argument("--allow-unsandboxed", action="store_true",
                    help="if no sandbox exists, execute anyway and disclose "
                         "executed_unsandboxed (never silent)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = check(args.workspace, execute=not args.no_exec, timeout=args.timeout,
                total_timeout=args.total_timeout,
                max_executions=args.max_executions,
                allow_unsandboxed=args.allow_unsandboxed)
    if args.json:
        print(json.dumps(doc, indent=2))
        return 0 if doc["verdict"] in ("PASS", "WARN", "SKIP") else 2
    if doc["verdict"] == "SKIP":
        print(f"smoke_gate: SKIP ({doc['reason_codes'][0] if doc['reason_codes'] else 'no full experiments'})")
        return 0
    if doc["verdict"] == "FAIL":
        print("smoke_gate: FAIL —")
        for d in doc["groups"]:
            for p in d.get("problems", []):
                print(f"  - {p}")
        return 2
    if doc["verdict"] == "WARN":
        print(f"smoke_gate: WARN — reason_codes={','.join(doc['reason_codes'])}")
        for d in doc["groups"]:
            ex = d.get("execution") or {}
            print(f"  - {d['group']}: record={d['record']['status']} "
                  f"freshness={(d.get('freshness') or {}).get('status')} "
                  f"executed={ex.get('executed')} "
                  f"reasons={','.join(ex.get('reason_codes', [])) or '-'}")
        return 0
    print(f"smoke_gate: PASS — {doc['executed']} smoke slice(s) re-executed in sandbox")
    return 0


if __name__ == "__main__":
    sys.exit(main())