"""Experiment execution layer (S06/S07/S10).

- Worker pool with per-seed jobs and STATUS.json aggregation (AI-Scientist v2 lesson).
- Background dispatch: nohup + STATUS.json polling per the contract; kernel owns
  the queue so >60s experiments never block the foreground (v1.5.0 rule, now code).
- Sandbox policy: macOS `sandbox-exec` (Seatbelt), Linux `bwrap` (bubblewrap) when
  available; deny network + workspace-rooted writes for agent-authored scripts by
  default, allow-list overrides recorded in events (ScienceDiscovery sandbox lesson).
- Device scheduling: wraps scripts/detect_device.py, persists DEVICE profile,
  planner maps backend by domain+machine (GPU/NPU/CPU/MPS), never hardcodes cuda.

Pre-dispatch security scan (S04) is mandatory here: every agent-authored script
passes scripts/security_scan.py before it may run anywhere.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
from .gates import security_scan_script  # noqa: E402


# ---------------- sandbox policy (S07) ----------------
def sandbox_cmd(workspace: Path, net: bool = False) -> list[str] | None:
    """Return a sandbox wrapper prefix, or None if no sandbox available (then WARN)."""
    sysname = platform.system()
    ws = str(workspace.resolve())
    if sysname == "Darwin":
        if not shutil.which("sandbox-exec"):
            return None
        prof = (
            "(version 1)(allow file-read*)(allow process-fork)(allow signal *)"
            f"(allow file-write* (subpath \"{ws}\")(subpath \"/tmp\"))"
            + ("(allow network*)" if net else "(deny network*)")
        )
        return ["sandbox-exec", "-p", prof]
    if sysname == "Linux":
        bwrap = shutil.which("bwrap")
        if not bwrap:
            return None
        cmd = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
               "--bind", ws, ws, "--bind", "/tmp", "/tmp", "--unshare-pid"]
        if not net:
            cmd += ["--unshare-net"]
        return cmd
    # Windows/WSL: document WSL2; kernel degrades to unsandboxed + WARN
    return None


class SandboxWarning(RuntimeError):
    pass


# ---------------- device planner (S10) ----------------
def plan_device(workspace: Path, needs_gpu: bool | None = None) -> dict:
    """domain-driven device selection, reusing the registered detector."""
    p = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "detect_device.py")],
                       capture_output=True, text=True, timeout=60)
    try:
        dev = json.loads(p.stdout)
    except json.JSONDecodeError:
        dev = {"device": "cpu", "raw": p.stdout[:500]}
    profile = {"schema_version": "1.0", "probed_at": time.time(), **dev}
    if needs_gpu and dev.get("device") not in ("cuda", "rocm", "npu", "mps"):
        profile["warn"] = "gpu_required_but_absent — auto-fallback CPU (never blocks per contract)"
    out = workspace / ".sciforge" / "verdicts" / "DEVICE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2))
    return profile


# ---------------- experiment dispatch ----------------
def dispatch(ws: Path, script: Path, args: list[str] | None = None, *,
             background: bool = True, net: bool = False, env: dict | None = None,
             group: str | None = None, seed: int | None = None) -> dict:
    """Scan-gate -> sandbox-wrap -> background (nohup, returns immediately) or foreground.

    STATUS contract (background-dispatch-protocol.md): per-job STATUS.json +
    group-level aggregation at Phase 10 read time.
    """
    # mandatory security gate (S04): unscanned code does not run, period
    scan = security_scan_script(script)
    if scan["status"] != "PASS":
        return {"dispatched": False, "blocked_by": "security_scan", "detail": scan}

    sb = sandbox_cmd(ws, net=net)
    base = [sys.executable, str(script), *(args or [])]
    cmd = (sb or []) + base
    e = dict(os.environ)
    e.update(env or {})
    e.setdefault("MPLBACKEND", "Agg")  # headless default
    run_id = f"{group or 'exp'}_{'s' + str(seed) if seed is not None else 'r0'}_{int(time.time())}"
    logdir = ws / "logs"
    logdir.mkdir(exist_ok=True)
    status = {"run_id": run_id, "script": str(script), "group": group, "seed": seed,
              "state": "running", "started_at": time.time(),
              "sandbox": bool(sb), "log": str(logdir / f"{run_id}.log")}
    st_file = logdir / f"{run_id}.STATUS.json"
    if background:
        with open(logdir / f"{run_id}.log", "wb") as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, cwd=str(ws), env=e,
                                    stdin=subprocess.DEVNULL,
                                    start_new_session=True)  # survive kernel exit
        status["pid"] = proc.pid
    else:
        t0 = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600,
                              cwd=str(ws), env=e)
        status.update(state="done" if proc.returncode == 0 else "failed",
                      returncode=proc.returncode, duration_s=round(time.time() - t0, 1),
                      stdout_tail=proc.stdout[-2000:], stderr_tail=proc.stderr[-2000:])
    st_file.write_text(json.dumps(status, indent=2))
    return {"dispatched": True, **status, "sandboxed": bool(sb)}


def group_status(ws: Path, group: str) -> dict:
    """Aggregate STATUS.json files of one experiment group (Phase 10 contract read)."""
    runs = []
    for f in sorted((ws / "logs").glob(f"{group}_*.STATUS.json")):
        try:
            s = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        # liveness check for 'running' entries whose pid died unrecorded
        if s.get("state") == "running" and s.get("pid"):
            try:
                os.kill(int(s["pid"]), 0)
            except (ProcessLookupError, PermissionError):
                s["state"] = "exited_unrecorded"
        runs.append(s)
    done = [r for r in runs if r.get("state") in ("done", "failed")]
    return {"group": group, "total": len(runs), "completed": len(done),
            "failed": sum(1 for r in runs if r.get("state") == "failed"),
            "runs": runs}


def worker_pool(ws: Path, jobs: list[dict], max_workers: int = 4) -> list[dict]:
    """Foreground-capable parallel seed runs (toy stage; full stage uses dispatch bg)."""
    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(dispatch, ws, Path(j["script"]), j.get("args"),
                         background=False, group=j.get("group"), seed=j.get("seed"),
                         net=j.get("net", False)) for j in jobs]
        for f in futs:
            out.append(f.result())
    return out
