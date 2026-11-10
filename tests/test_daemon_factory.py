"""v1.7.3 hardening tests — daemon queue/workers/auth, atomic lock, shared limiter.

Covers the four defects fixed this iteration:
  1. durable queue + multi-worker + crash isolation/takeover (daemon.py)
  2. bearer-token auth on every state-changing HTTP endpoint (daemon.py)
     + approval-path anti-forgery (approvals.py/state.py)
  3. atomic, pid-reuse-safe kernel lock (state.py)
  4. cross-process rate-limit / 429 cooldown (limiter.py)

Negative tests are explicit: no-token /approve must be rejected, and two
processes racing for the same workspace lock must yield exactly one winner.
"""
from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNEL_DIR = REPO_ROOT / "kernel"

if sys.version_info < (3, 10):
    pytest.skip("kernel requires Python >= 3.10 (X | Y syntax)", allow_module_level=True)

sys.path.insert(0, str(KERNEL_DIR))

from sciforge import daemon as daemon_mod  # noqa: E402
from sciforge import state  # noqa: E402
from sciforge.approvals import Approvals  # noqa: E402
from sciforge.daemon import Daemon, QueueStore  # noqa: E402
from sciforge.limiter import Limiter, self_test as limiter_self_test  # noqa: E402
from sciforge.pipeline import Kernel  # noqa: E402
from sciforge.state import EventLog, RunState  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _daemon(tmp_path: Path, **kw) -> Daemon:
    kw.setdefault("token", "test-token")
    kw.setdefault("poll_interval", 0.01)
    return Daemon(tmp_path / "runs", **kw)


def _start_http(d: Daemon):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), d.handler())
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _req(url: str, method: str = "GET", body=None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read() or b"{}")
        except Exception:
            payload = {}
        return e.code, payload


def _pending_ws(tmp_path: Path, rid: str = "RID"):
    ws = tmp_path / "runs" / rid
    ws.mkdir(parents=True)
    k = Kernel(ws)
    k.start(rid, "problem", "lite", host="manual")
    k.appr.request("idea-pick", "3", {"digest": "candidate"}, k.rs)
    return ws, k


def _run_child(code: str, *args: str, timeout: float = 20.0):
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code), *args],
                          capture_output=True, text=True, timeout=timeout)


# ---------------------------------------------------------------------------
# defect 1 — durable queue, multi-worker, crash isolation / takeover
# ---------------------------------------------------------------------------

def test_queue_persists_and_dedups_across_restart(tmp_path: Path):
    d1 = _daemon(tmp_path)
    rec = d1.enqueue("Q1", "problem one")
    assert rec["state"] == "queued" and rec["duplicate"] is False
    assert d1.enqueue("Q1", "problem one again")["duplicate"] is True
    assert len(d1.queue) == 1
    assert (tmp_path / "runs" / "queue.json").exists()  # derived, human-readable mirror
    d1.store.close()

    d2 = _daemon(tmp_path)  # restart: the queue survives on disk
    q = d2.queue
    assert [r["run_id"] for r in q] == ["Q1"]
    assert q[0]["problem"] == "problem one"
    assert d2.enqueue("Q1", "x")["duplicate"] is True
    assert len(d2.queue) == 1


def test_claim_is_atomic_under_threads(tmp_path: Path):
    store = QueueStore(tmp_path / "q.sqlite3")
    for i in range(12):
        store.enqueue(f"R{i:02d}", f"p{i}")
    claimed: list[str] = []
    guard = threading.Lock()

    def worker(wid: str):
        while True:
            rec = store.claim(wid, lease_seconds=60)
            if rec is None:
                return
            with guard:
                claimed.append(rec["run_id"])
            time.sleep(0.002)

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert sorted(claimed) == sorted(f"R{i:02d}" for i in range(12))
    assert len(claimed) == len(set(claimed)), "a row was claimed twice"
    assert store.counts().get("running") == 12


def test_worker_crash_isolated_and_identifiable(tmp_path: Path, monkeypatch):
    d = _daemon(tmp_path)
    d.store.enqueue("CRASH1", "boom")
    item = d.store.claim("w0", 60)

    class Boom:
        def __init__(self, ws):
            self.ws = Path(ws)
            (self.ws / ".sciforge").mkdir(parents=True, exist_ok=True)
            rs = RunState(self.ws)
            rs.data = {"run_id": "CRASH1", "problem": "boom"}
            rs.status = "running"
            rs.write()

        def start(self, *a, **k):
            raise RuntimeError("kaboom")

        def step(self):
            return {"status": "done"}

    monkeypatch.setattr(daemon_mod, "Kernel", Boom)
    out = d.run_one(item, "w0")
    assert out["state"] == "failed" and "kaboom" in out["error"]
    row = d.store.get("CRASH1")
    assert row["state"] == "failed" and "kaboom" in row["last_error"]
    rs = RunState(tmp_path / "runs" / "CRASH1")
    assert rs.status == "paused_blocked"  # identifiable, not dangling
    assert rs.data.get("reason_code") == "daemon_worker_crash"
    err = tmp_path / "runs" / "CRASH1" / ".sciforge" / "daemon-error.txt"
    assert err.exists() and "kaboom" in err.read_text()


def test_worker_loop_survives_crash_and_finishes_next_run(tmp_path: Path, monkeypatch):
    d = _daemon(tmp_path)
    d.store.enqueue("BAD", "x")
    d.store.enqueue("GOOD", "y")

    class Flaky:
        def __init__(self, ws):
            self.ws = Path(ws)

        def start(self, *a, **k):
            if "BAD" in str(self.ws):
                raise RuntimeError("nope")

        def step(self):
            return {"status": "done"}

    monkeypatch.setattr(daemon_mod, "Kernel", Flaky)
    t = threading.Thread(target=d.work, args=("w0",), daemon=True)
    t.start()
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            rows = {r["run_id"]: r["state"] for r in d.store.list()}
            if rows.get("BAD") == "failed" and rows.get("GOOD") == "done":
                break
            time.sleep(0.02)
    finally:
        d.stop = True
        t.join(5)
    rows = {r["run_id"]: r["state"] for r in d.store.list()}
    assert rows["BAD"] == "failed"
    assert rows["GOOD"] == "done", "one crashed run killed the worker loop"


def test_worker_loop_survives_a_thread_level_blast(tmp_path: Path, monkeypatch):
    d = _daemon(tmp_path)
    d.store.enqueue("A", "a")
    d.store.enqueue("B", "b")

    class Done:
        def __init__(self, ws):
            pass

        def start(self, *a, **k):
            pass

        def step(self):
            return {"status": "done"}

    real_run_one = daemon_mod.Daemon.run_one
    calls = {"n": 0}

    def flaky(self, item, worker_id="worker-0"):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("thread-level blast")  # outside run_one's guard
        return real_run_one(self, item, worker_id)

    monkeypatch.setattr(daemon_mod.Daemon, "run_one", flaky)
    monkeypatch.setattr(daemon_mod, "Kernel", Done)
    t = threading.Thread(target=d.work, args=("w0",), daemon=True)
    t.start()
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            rows = {r["run_id"]: r["state"] for r in d.store.list()}
            if rows.get("A") == "failed" and rows.get("B") == "done":
                break
            time.sleep(0.02)
    finally:
        d.stop = True
        t.join(5)
    rows = {r["run_id"]: r["state"] for r in d.store.list()}
    assert rows["A"] == "failed"
    assert rows["B"] == "done", "a thread-level failure killed the worker loop"


def test_multi_worker_concurrency(tmp_path: Path, monkeypatch):
    d = _daemon(tmp_path, concurrency=2)
    for i in range(2):
        d.store.enqueue(f"P{i}", f"p{i}")
    barrier = threading.Barrier(2, timeout=5)

    class Parallel:
        live = 0
        peak = 0
        guard = threading.Lock()

        def __init__(self, ws):
            pass

        def start(self, *a, **k):
            pass

        def step(self):
            with Parallel.guard:
                Parallel.live += 1
                Parallel.peak = max(Parallel.peak, Parallel.live)
            try:
                barrier.wait()  # only two concurrent workers can pass together
            except threading.BrokenBarrierError:
                pass
            with Parallel.guard:
                Parallel.live -= 1
            return {"status": "done"}

    monkeypatch.setattr(daemon_mod, "Kernel", Parallel)
    d.start_workers()
    try:
        deadline = time.time() + 10
        while time.time() < deadline and d.store.counts().get("done", 0) < 2:
            time.sleep(0.02)
    finally:
        d.stop_workers()
    assert d.store.counts().get("done", 0) == 2
    assert Parallel.peak >= 2, "workers ran serially despite concurrency=2"


def test_crash_takeover_requeues_dead_worker(tmp_path: Path):
    archive = tmp_path / "runs"
    d = _daemon(tmp_path)
    d.store.enqueue("RID", "p")
    assert d.store.claim("w0", 60)["state"] == "running"
    with d.store._lock:  # simulate the daemon process dying mid-run
        d.store._conn.execute(
            "UPDATE runs SET worker_pid=999999999, worker_host=?, lease_until=0 "
            "WHERE run_id='RID'", (socket.gethostname(),))
        d.store._conn.commit()
    d2 = _daemon(tmp_path)
    recovered = d2.store.recover_stale(archive)
    assert [r["run_id"] for r in recovered] == ["RID"]
    row = d2.store.get("RID")
    assert row["state"] == "queued"
    assert "recovered" in (row["last_error"] or "")


def test_crash_takeover_does_not_steal_live_worker_pid(tmp_path: Path):
    archive = tmp_path / "runs"
    d = _daemon(tmp_path)
    d.store.enqueue("RID", "p")
    d.store.claim("w0", 60)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with d.store._lock:
            d.store._conn.execute(
                "UPDATE runs SET worker_pid=?, worker_host=? WHERE run_id='RID'",
                (child.pid, socket.gethostname()))
            d.store._conn.commit()
        assert d.store.recover_stale(archive) == []
        assert d.store.get("RID")["state"] == "running"
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_crash_takeover_keeps_run_with_live_workspace_lock(tmp_path: Path):
    archive = tmp_path / "runs"
    d = _daemon(tmp_path)
    d.store.enqueue("RID", "p")
    d.store.claim("w0", 60)
    ws = archive / "RID"
    state.take_lock(ws)  # another live kernel owns this workspace
    try:
        with d.store._lock:
            d.store._conn.execute(
                "UPDATE runs SET worker_pid=999999999, worker_host=? WHERE run_id='RID'",
                (socket.gethostname(),))
            d.store._conn.commit()
        assert d.store.recover_stale(archive) == []
        assert d.store.get("RID")["state"] == "running"
    finally:
        state.release_lock(ws)


# ---------------------------------------------------------------------------
# defect 2 — HTTP bearer-token auth on every state-changing endpoint
# ---------------------------------------------------------------------------

def test_http_mutations_require_token(tmp_path: Path):
    d = _daemon(tmp_path)
    srv, base = _start_http(d)
    try:
        code, _ = _req(base + "/runs", "POST", {"problem": "x"})
        assert code == 401, "unauthenticated POST /runs must be rejected"
        assert d.queue == []
        code, _ = _req(base + "/runs", "POST", {"problem": "x"}, token="wrong")
        assert code == 403
        assert d.queue == []
        code, body = _req(base + "/runs", "POST",
                          {"problem": "x", "run_id": "Q1"}, token="test-token")
        assert code == 201 and body["run_id"] == "Q1"
        assert len(d.queue) == 1
        code, body = _req(base + "/runs", "POST",
                          {"problem": "x", "run_id": "Q1"}, token="test-token")
        assert code == 409 and body["duplicate"] is True
        assert len(d.queue) == 1
        code, body = _req(base + "/health")  # reads stay open
        assert code == 200 and body["ok"] is True and body["queued"] == 1
        code, body = _req(base + "/runs")
        assert code == 200 and [r["run_id"] for r in body["runs"]] == ["Q1"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_http_approve_requires_token_and_applies_decision(tmp_path: Path):
    ws, k = _pending_ws(tmp_path)
    d = _daemon(tmp_path)
    d.store.enqueue("RID", "problem")
    d.store.claim("w0", 60)
    d.store.finish("RID", "blocked")
    srv, base = _start_http(d)
    try:
        # NEGATIVE: a local process without the token cannot self-approve.
        code, _ = _req(base + "/runs/RID/approve", "POST",
                       {"checkpoint": "idea-pick"})
        assert code == 401
        assert any(r["checkpoint"] == "idea-pick" for r in k.appr.pending_records())
        assert d.store.get("RID")["state"] == "blocked"

        # POSITIVE: with the token the decision lands and the run is re-queued.
        code, body = _req(base + "/runs/RID/approve", "POST",
                          {"checkpoint": "idea-pick", "decided_by": "spoofed-agent"},
                          token="test-token")
        assert code == 200 and body["requeued"] is True
        assert k.appr.pending_records() == []
        assert d.store.get("RID")["state"] == "queued"
        log = (ws / ".sciforge" / "APPROVAL_LOG.txt").read_text()
        assert "decision=APPROVE" in log
        assert "daemon-api@" in log and "spoofed-agent" not in log
    finally:
        srv.shutdown()
        srv.server_close()


def test_http_deny_requires_token_and_records_denial(tmp_path: Path):
    ws, k = _pending_ws(tmp_path)
    d = _daemon(tmp_path)
    srv, base = _start_http(d)
    try:
        code, _ = _req(base + "/runs/RID/deny", "POST", {"checkpoint": "idea-pick"})
        assert code == 401
        code, body = _req(base + "/runs/RID/deny", "POST",
                          {"checkpoint": "idea-pick"}, token="test-token")
        assert code == 200 and body["decision"]["status"] == "DENIED"
        assert any(r["checkpoint"] == "idea-pick" for r in k.appr.pending_records()) is False
    finally:
        srv.shutdown()
        srv.server_close()


def test_http_cannot_approve_a_forged_pending_file(tmp_path: Path):
    ws = tmp_path / "runs" / "RID"
    (ws / ".sciforge" / "approvals").mkdir(parents=True)
    (ws / ".sciforge" / "approvals" / "phase_5.json").write_text(json.dumps(
        {"checkpoint": "method-approval", "phase": "5", "status": "PENDING",
         "nonce": "forged", "payload": {}}))
    d = _daemon(tmp_path)
    srv, base = _start_http(d)
    try:
        code, body = _req(base + "/runs/RID/approve", "POST",
                          {"checkpoint": "method-approval"}, token="test-token")
        assert code == 409, body  # no kernel-issued request epoch => rejected
        assert json.loads((ws / ".sciforge" / "approvals" / "phase_5.json").read_text()
                          )["status"] == "PENDING"
    finally:
        srv.shutdown()
        srv.server_close()


def test_http_rejects_unsafe_run_ids(tmp_path: Path):
    d = _daemon(tmp_path)
    srv, base = _start_http(d)
    try:
        code, _ = _req(base + "/runs", "POST",
                       {"problem": "x", "run_id": "../evil"}, token="test-token")
        assert code == 400
        assert d.queue == []
        code, _ = _req(base + "/runs/..")
        assert code == 404
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.mark.skipif(sys.platform.startswith("win"),
                    reason="POSIX file modes; Windows chmod is degraded")
def test_token_file_is_private(tmp_path: Path):
    d = _daemon(tmp_path)
    mode = stat.S_IMODE(os.stat(d.token_path).st_mode)
    assert mode == 0o600, oct(mode)
    assert d.token_path.read_text().strip() == "test-token"


# ---------------------------------------------------------------------------
# approval-path anti-forgery (approvals.py / state.py)
# ---------------------------------------------------------------------------

def test_forged_pending_file_without_request_cannot_be_approved(tmp_path: Path):
    ws = tmp_path / "ws"
    (ws / ".sciforge" / "approvals").mkdir(parents=True)
    (ws / ".sciforge" / "approvals" / "phase_9.json").write_text(json.dumps(
        {"checkpoint": "method-approval", "phase": "9", "status": "PENDING",
         "nonce": "forged", "payload": {}}))
    ap = Approvals(ws)
    with pytest.raises(KeyError):
        ap.decide("method-approval", True, "agent", RunState(ws))
    pend = ap.pending_records()
    assert pend and pend[0]["checkpoint"] == "method-approval"
    assert pend[0].get("unverified") is True  # fail-closed, but unapprovable


def test_deleting_pending_file_does_not_unblock_the_run(tmp_path: Path):
    ws, k = _pending_ws(tmp_path)
    for f in (ws / ".sciforge" / "approvals").glob("*.json"):
        f.unlink()
    assert state.Approvals_pending(ws) is True
    pend = k.appr.pending_records()
    assert any(p["checkpoint"] == "idea-pick" and p.get("source") == "event_log"
               for p in pend)
    rec = k.appr.decide("idea-pick", True, "human", k.rs)  # rebuilt from ledger
    assert rec["status"] == "APPROVED"
    assert k.appr.pending_records() == []
    assert state.Approvals_pending(ws) is False


def test_hand_written_approval_log_line_is_ignored(tmp_path: Path):
    ws, k = _pending_ws(tmp_path)
    (ws / ".sciforge" / "APPROVAL_LOG.txt").write_text(
        "2026-01-01T00:00:00Z checkpoint=idea-pick decision=APPROVE "
        "by=agent phase=3 note=self-approved\n")
    assert "decision=APPROVE" not in k.appr.log.read_text()
    assert k._checkpoint_satisfied("idea-pick", "3") is False
    k.appr.decide("idea-pick", True, "human", k.rs)
    assert "decision=APPROVE" in k.appr.log.read_text()
    assert k._checkpoint_satisfied("idea-pick", "3") is True


def test_hand_edited_approved_status_is_still_pending(tmp_path: Path):
    ws, k = _pending_ws(tmp_path)
    f = next((ws / ".sciforge" / "approvals").glob("*.json"))
    rec = json.loads(f.read_text())
    rec["status"] = "APPROVED"  # bypass attempt: skip decide()
    f.write_text(json.dumps(rec))
    assert state.Approvals_pending(ws) is True
    assert any(p["checkpoint"] == "idea-pick" for p in k.appr.pending_records())
    k.rs.status = "paused_checkpoint"
    k.rs.write()
    assert k.step()["status"] == "blocked_checkpoint"


def test_tampered_pending_nonce_is_rejected(tmp_path: Path):
    ws, k = _pending_ws(tmp_path)
    f = next((ws / ".sciforge" / "approvals").glob("*.json"))
    rec = json.loads(f.read_text())
    rec["nonce"] = "forged-epoch"
    f.write_text(json.dumps(rec))
    with pytest.raises(PermissionError):
        k.appr.decide("idea-pick", True, "agent", k.rs)


def test_human_skip_stays_verified(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    k = Kernel(ws)
    k.start("SKIP1", "p", "lite", host="manual", human_skip=True)
    k.appr.skipped("human_skip", "idea-pick", "3", k.rs)
    assert "human_skip=True" in k.appr.log.read_text()
    # a forged skip line is still filtered out
    (ws / ".sciforge" / "APPROVAL_LOG.txt").write_text(
        "2026-01-01T00:00:00Z checkpoint=method-approval human_skip=True "
        "human_review_status=EXPLICIT_SKIP\n")
    assert "human_skip=True" not in k.appr.log.read_text()


# ---------------------------------------------------------------------------
# defect 3 — atomic lock, pid-reuse immunity, single winner across processes
# ---------------------------------------------------------------------------

def test_lock_payload_has_pid_nonce_and_start(tmp_path: Path):
    payload = state.take_lock(tmp_path)
    assert payload["pid"] == os.getpid()
    assert len(payload["nonce"]) >= 16
    assert payload.get("start")
    on_disk = json.loads((tmp_path / ".sciforge" / "kernel.lock").read_text())
    assert on_disk["nonce"] == payload["nonce"]
    assert state.holder_alive(tmp_path) is True
    state.release_lock(tmp_path)
    assert state.holder_alive(tmp_path) is False
    assert not (tmp_path / ".sciforge" / "kernel.lock").exists()


def test_pid_reuse_is_not_mistaken_for_a_live_holder(tmp_path: Path):
    ws = tmp_path
    (ws / ".sciforge").mkdir(parents=True)
    (ws / ".sciforge" / "kernel.lock").write_text(json.dumps({
        "pid": os.getpid(), "nonce": "deadbeef", "start": "not-our-start",
        "host": socket.gethostname(), "lock_version": 2}))
    assert state.holder_alive(ws) is False, "pid reuse must not fake a live holder"
    payload = state.take_lock(ws)  # stale identity must be stealable
    assert payload["nonce"] != "deadbeef"
    state.release_lock(ws)


def test_two_processes_race_for_lock_only_one_wins(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    gate = tmp_path / "go"
    script = tmp_path / "lock_race.py"
    script.write_text(textwrap.dedent(f"""
        import sys, time
        from pathlib import Path
        sys.path.insert(0, {str(KERNEL_DIR)!r})
        from sciforge import state
        ws, gate = Path(sys.argv[1]), Path(sys.argv[2])
        while not gate.exists():
            time.sleep(0.005)
        try:
            state.take_lock(ws)
        except state.LockHeldError:
            print("HELD", flush=True)
            sys.exit(0)
        print("OK", flush=True)
        time.sleep(0.8)  # hold long enough for every sibling to try
    """))
    procs = [subprocess.Popen([sys.executable, str(script), str(ws), str(gate)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
             for _ in range(4)]
    gate.write_text("go")
    outs, errs = [], []
    for p in procs:
        out, err = p.communicate(timeout=20)
        outs.append(out.strip())
        errs.append(err)
    assert outs.count("OK") == 1, (outs, errs)
    assert outs.count("HELD") == 3, (outs, errs)


def test_child_death_releases_lock(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    code = f"""
        import os, sys
        from pathlib import Path
        sys.path.insert(0, {str(KERNEL_DIR)!r})
        from sciforge import state
        state.take_lock(Path(sys.argv[1]))
        os._exit(0)  # die WITHOUT release_lock: stale file, released flock
    """
    subprocess.run([sys.executable, "-c", textwrap.dedent(code), str(ws)],
                   check=True, timeout=20)
    assert (ws / ".sciforge" / "kernel.lock").exists()
    assert state.holder_alive(ws) is False
    payload = state.take_lock(ws)  # takeover must succeed
    assert payload["pid"] == os.getpid()
    state.release_lock(ws)


def test_recover_waits_while_another_process_holds_the_lock(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".sciforge").mkdir()
    rs = RunState(ws)
    rs.data = {"run_id": "X", "current_phase": "1"}
    rs.status = "running"
    rs.write()
    code = f"""
        import sys, time
        from pathlib import Path
        sys.path.insert(0, {str(KERNEL_DIR)!r})
        from sciforge import state
        state.take_lock(Path(sys.argv[1]))
        print("LOCKED", flush=True)
        time.sleep(2.0)
    """
    child = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code), str(ws)],
                             stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "LOCKED"
        assert state.recover(EventLog(ws), RunState(ws), ws) == "wait"
    finally:
        child.kill()
        child.wait(timeout=5)


# ---------------------------------------------------------------------------
# defect 4 — cross-process shared limiter / 429 cooldown
# ---------------------------------------------------------------------------

_MANIFEST = {"limits": {"k": {"min_interval_s": 0.0,
                              "default_retry_after_s": 2,
                              "max_cooldown_s": 5}}}


def test_shared_limiter_429_cooldown_is_cross_process(tmp_path: Path):
    db = tmp_path / "limits.sqlite3"
    parent = Limiter(_MANIFEST, shared_db=db)
    assert parent.wait_time("k") == 0.0
    code = f"""
        import sys
        sys.path.insert(0, {str(KERNEL_DIR)!r})
        from sciforge.limiter import Limiter
        lim = Limiter({_MANIFEST!r}, shared_db=r"{db}")
        lim.report_upstream_429("k", retry_after_s=1.0)
    """
    _run_child(code)
    assert parent.wait_time("k") > 0.4, "child's 429 cooldown was not shared"
    waited = parent.acquire("k", timeout_s=5)
    assert waited > 0.3, "parent did not block on the child's cooldown"


def test_shared_limiter_pacing_is_cross_process(tmp_path: Path):
    db = tmp_path / "limits.sqlite3"
    manifest = {"limits": {"k": {"min_interval_s": 0.7}}}
    code = f"""
        import sys
        sys.path.insert(0, {str(KERNEL_DIR)!r})
        from sciforge.limiter import Limiter
        lim = Limiter({manifest!r}, shared_db=r"{db}")
        lim.acquire("k")
    """
    _run_child(code)
    parent = Limiter(manifest, shared_db=db)
    waited = parent.acquire("k", timeout_s=5)
    assert waited > 0.2, "child's pacing clock was not shared (waited %.3fs)" % waited


def test_limiter_without_shared_db_stays_process_local(tmp_path: Path):
    lim = Limiter({"limits": {"arxiv": {"min_interval_s": 2}}})
    assert lim.shared_db is None
    assert lim.wait_time("unlisted-key") == 0.0
    lim.report_upstream_429("arxiv", retry_after_s=0.3)
    assert lim.wait_time("arxiv") > 0.15
    n, fails = limiter_self_test()
    assert n == 0, fails


def test_limiter_env_var_wires_shared_backend(tmp_path: Path, monkeypatch):
    from sciforge import limiter as lim_mod
    db = tmp_path / "env-limits.sqlite3"
    monkeypatch.setenv("SCIFORGE_LIMITER_DB", str(db))
    lim_mod.reset_default_limiter()
    try:
        lim = lim_mod.limiter()
        assert lim.shared_db == db
        lim.report_upstream_429("k", retry_after_s=0.6)
        assert lim.wait_time("k") > 0.2
    finally:
        lim_mod.reset_default_limiter()