"""`sciforge serve` — headless daemon for overnight/queue autonomy (EvoScientist/DeepScientist lesson).

Zero-GUI by design: the daemon is a loopback HTTP control surface + queue
worker fleet. Browsers/curl/SSH-tunnel are optional; `run`/`resume`/`status`
CLI commands talk to the same files the daemon owns (RUNSTATE/events/verdicts),
so a queue client can be a one-line curl:

    TOKEN=$(cat runs/.sciforge-daemon/token)
    curl -H "Authorization: Bearer $TOKEN" -X POST localhost:4510/runs \
         -d '{"problem": "..."}'                    -> run_id queued
    curl localhost:4510/runs/<id>                   -> RUNSTATE + trail + queue state
    curl -H "Authorization: Bearer $TOKEN" -X POST \
         localhost:4510/runs/<id>/approve -d '{"checkpoint": "idea-pick"}'
    curl localhost:4510/daily                       -> evolution digest (S17)

v1.7.3 hardening (defects 1+2):
  - the queue is a SQLite ledger (`<archive>/.sciforge-daemon/queue.sqlite3`),
    so a daemon restart never loses or silently duplicates work;
  - a configurable worker pool (`--workers N`) runs independent runs in
    independent workspaces, each protected by the kernel's OS file lock;
  - a crashed run is isolated: the worker loop survives, the queue row is
    marked failed, and RUNSTATE is moved to an identifiable
    `paused_blocked / daemon_worker_crash` state instead of dangling;
  - rows orphaned by a dead worker are re-queued on restart (lease + pid
    liveness + workspace-lock probe) — crash takeover;
  - every state-changing endpoint requires the per-start bearer token, which
    is written to `<archive>/.sciforge-daemon/token` with mode 0600. Read-only
    endpoints (/health, /runs, /daily) stay open.

Worker semantics: `--workers` concurrent runs (default 1, budget isolation),
manual-host protocol for LLM phases unless --host claude given. Stdlib
http.server + sqlite3. This is the "runs on a Linux GPU box without X11"
answer to the project goal.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import socket
import sqlite3
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .pipeline import DispatchError, Kernel
from .state import (RunState, holder_alive, lock_owned_by_this_process,
                    pid_alive, release_lock)

STATE_DIR = ".sciforge-daemon"
MAX_ATTEMPTS = 3          # project-wide 3-round cap per failure type
LEASE_SECONDS = 120.0
SOURCES_POLL_SECONDS = 10.0

QUEUED, RUNNING, DONE = "queued", "running", "done"
BLOCKED, FAILED, CANCELLED = "blocked", "failed", "cancelled"

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def valid_run_id(run_id: object) -> bool:
    """run_id becomes a directory name: reject separators / traversal."""
    return isinstance(run_id, str) and bool(_RUN_ID_RE.match(run_id))


class QueueStore:
    """Durable run queue (SQLite). One row per run_id; enqueue is idempotent.

    States: queued -> running -> done | blocked | failed; queued|blocked ->
    cancelled; blocked|failed -> queued (explicit resume / crash takeover).
    """

    SCHEMA = (
        "CREATE TABLE IF NOT EXISTS runs ("
        "run_id TEXT PRIMARY KEY,"
        "problem TEXT NOT NULL,"
        "effort TEXT NOT NULL DEFAULT 'balanced',"
        "state TEXT NOT NULL DEFAULT 'queued',"
        "enqueued_at REAL NOT NULL,"
        "started_at REAL,"
        "finished_at REAL,"
        "updated_at REAL NOT NULL,"
        "worker TEXT,"
        "worker_host TEXT,"
        "worker_pid INTEGER,"
        "lease_until REAL,"
        "attempts INTEGER NOT NULL DEFAULT 0,"
        "result TEXT,"
        "last_error TEXT)")
    INDEX = ("CREATE INDEX IF NOT EXISTS runs_state_idx "
             "ON runs(state, enqueued_at)")

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), timeout=30,
                                     check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout=30000")
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        with self._lock:
            self._conn.execute(self.SCHEMA)
            self._conn.execute(self.INDEX)
            self._conn.commit()

    # ---------- helpers ----------
    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        out = dict(row)
        if out.get("result"):
            try:
                out["result"] = json.loads(out["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        return out

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---------- queue ops ----------
    def enqueue(self, run_id: str, problem: str, effort: str = "balanced") -> tuple[dict, bool]:
        """-> (record, created). Duplicate run_id (any state) is not re-queued."""
        now = time.time()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                cur = self._conn.execute(
                    "INSERT INTO runs(run_id,problem,effort,state,enqueued_at,updated_at) "
                    "VALUES(?,?,?,'queued',?,?) ON CONFLICT(run_id) DO NOTHING",
                    (run_id, problem, effort, now, now))
                created = cur.rowcount == 1
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            rec = self.get(run_id)
        assert rec is not None
        return rec, created

    def get(self, run_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return self._row(row)

    def list(self, state: str | None = None, limit: int = 500) -> list[dict]:
        with self._lock:
            if state:
                rows = self._conn.execute(
                    "SELECT * FROM runs WHERE state=? ORDER BY enqueued_at, run_id "
                    "LIMIT ?", (state, limit)).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM runs ORDER BY enqueued_at, run_id LIMIT ?",
                    (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def counts(self) -> dict:
        with self._lock:
            rows = self._conn.execute(
                "SELECT state, COUNT(*) AS n FROM runs GROUP BY state").fetchall()
        return {r["state"]: r["n"] for r in rows}

    def claim(self, worker: str, lease_seconds: float = LEASE_SECONDS) -> dict | None:
        """Atomically take the oldest queued row (BEGIN IMMEDIATE serializes
        threads AND processes sharing the DB)."""
        now = time.time()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT run_id FROM runs WHERE state='queued' "
                    "ORDER BY enqueued_at, run_id LIMIT 1").fetchone()
                if row is None:
                    self._conn.commit()
                    return None
                rid = row["run_id"]
                self._conn.execute(
                    "UPDATE runs SET state='running', worker=?, worker_host=?, "
                    "worker_pid=?, lease_until=?, started_at=COALESCE(started_at,?), "
                    "updated_at=?, attempts=attempts+1 "
                    "WHERE run_id=? AND state='queued'",
                    (worker, socket.gethostname(), os.getpid(),
                     now + lease_seconds, now, now, rid))
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            return self.get(rid)

    def heartbeat(self, run_id: str, worker: str,
                  lease_seconds: float = LEASE_SECONDS) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE runs SET lease_until=?, updated_at=? "
                "WHERE run_id=? AND worker=? AND state='running'",
                (time.time() + lease_seconds, time.time(), run_id, worker))
            self._conn.commit()
            return cur.rowcount == 1

    def finish(self, run_id: str, state: str, result: dict | None = None,
               error: str | None = None) -> None:
        now = time.time()
        blob = json.dumps(result, ensure_ascii=False, default=str) if result is not None else None
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET state=?, finished_at=?, updated_at=?, result=?, "
                "last_error=?, worker=NULL, lease_until=NULL WHERE run_id=?",
                (state, now, now, blob, error, run_id))
            self._conn.commit()

    def requeue(self, run_id: str, reset_attempts: bool = True,
                note: str | None = None) -> dict | None:
        now = time.time()
        with self._lock:
            if reset_attempts:
                self._conn.execute(
                    "UPDATE runs SET state='queued', worker=NULL, worker_host=NULL, "
                    "worker_pid=NULL, lease_until=NULL, finished_at=NULL, "
                    "updated_at=?, attempts=0, "
                    "last_error=COALESCE(?, last_error) WHERE run_id=?",
                    (now, note, run_id))
            else:
                self._conn.execute(
                    "UPDATE runs SET state='queued', worker=NULL, worker_host=NULL, "
                    "worker_pid=NULL, lease_until=NULL, finished_at=NULL, updated_at=?, "
                    "last_error=COALESCE(?, last_error) WHERE run_id=?",
                    (now, note, run_id))
            self._conn.commit()
        return self.get(run_id)

    def cancel(self, run_id: str, note: str | None = None) -> dict | None:
        now = time.time()
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET state='cancelled', finished_at=?, updated_at=?, "
                "last_error=COALESCE(?, last_error), worker=NULL, lease_until=NULL "
                "WHERE run_id=? AND state IN ('queued','blocked','failed')",
                (now, now, note, run_id))
            self._conn.commit()
        return self.get(run_id)

    def recover_stale(self, archive: Path) -> list[dict]:
        """Crash takeover at daemon start: rows left 'running' by a dead worker
        go back to the queue (unless a live kernel still owns the workspace or
        the worker pid is still alive on this host). Attempts cap -> failed."""
        archive = Path(archive)
        recovered: list[dict] = []
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM runs WHERE state='running'").fetchall()
        for row in rows:
            rec = self._row(row) or {}
            rid = rec.get("run_id")
            if not rid:
                continue
            host = rec.get("worker_host")
            wpid = rec.get("worker_pid")
            if host and host != socket.gethostname():
                continue  # a different machine owns this row (shared archive)
            if wpid and int(wpid) != os.getpid() and pid_alive(wpid):
                continue  # live foreign daemon
            ws = archive / rid
            if holder_alive(ws):
                continue  # a live kernel (manual CLI or another daemon) owns it
            if int(rec.get("attempts") or 0) >= MAX_ATTEMPTS:
                self.finish(rid, FAILED, error=(
                    "worker crashed repeatedly; max attempts reached "
                    f"({MAX_ATTEMPTS})"))
            else:
                self.requeue(rid, reset_attempts=False,
                             note="recovered after worker crash")
            updated = self.get(rid)
            if updated:
                recovered.append(updated)
        return recovered


class Daemon:
    def __init__(self, archive: Path, host: str = "manual", effort: str = "balanced",
                 concurrency: int = 1, token: str | None = None,
                 queue_db: Path | None = None, poll_interval: float = 1.0,
                 lease_seconds: float = LEASE_SECONDS):
        self.archive = Path(archive)
        self.archive.mkdir(parents=True, exist_ok=True)
        self.host = host
        self.effort = effort
        self.concurrency = max(1, int(concurrency))
        self.poll_interval = max(0.01, float(poll_interval))
        self.lease_seconds = float(lease_seconds)
        self.state_dir = self.archive / STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.store = QueueStore(queue_db or (self.state_dir / "queue.sqlite3"))
        self.stop = False
        self._active: dict[str, dict] = {}
        self._active_lock = threading.Lock()
        self._threads: list[threading.Thread] = []
        self._sources_lock = threading.Lock()
        self._last_sources_poll = 0.0
        self.token = token or secrets.token_urlsafe(32)
        self.token_path = self.state_dir / "token"
        self._write_token()

    # ---------- auth ----------
    def _write_token(self) -> None:
        """0600 token file: the only state-changing credential. A fresh token
        per daemon start (one-time credential; restart invalidates clients)."""
        fd = os.open(self.token_path,
                     os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, (self.token + "\n").encode())
        finally:
            os.close(fd)
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:  # Windows: chmod only maps to the read-only bit
            pass

    # ---------- queue facade (kept for API compatibility) ----------
    @property
    def queue(self) -> list[dict]:
        return self.store.list(QUEUED)

    def enqueue(self, run_id: str, problem: str) -> dict:
        if not valid_run_id(run_id):
            raise ValueError(f"invalid run_id: {run_id!r}")
        rec, created = self.store.enqueue(run_id, problem, self.effort)
        rec = dict(rec)
        rec["duplicate"] = not created
        self._snapshot()
        return rec

    @property
    def active(self) -> str | None:
        with self._active_lock:
            return next(iter(self._active), None)

    def active_records(self) -> list[dict]:
        with self._active_lock:
            return [{"run_id": rid, **meta} for rid, meta in sorted(self._active.items())]

    def _snapshot(self) -> None:
        """Human/tooling-readable mirror of the durable queue (the sqlite DB is
        authoritative; this file is derived and safe to delete)."""
        try:
            (self.archive / "queue.json").write_text(json.dumps(
                {"queue": self.queue, "active": [r["run_id"] for r in self.active_records()],
                 "states": self.store.counts(), "updated_at": time.time()},
                indent=2, ensure_ascii=False))
        except Exception:
            pass  # derived mirror only; the sqlite ledger is authoritative

    # ---------- worker ----------
    def start_workers(self) -> list[dict]:
        self.stop = False
        recovered = self.store.recover_stale(self.archive)
        for i in range(self.concurrency):
            wid = f"worker-{i}"
            t = threading.Thread(target=self.work, args=(wid,), daemon=True,
                                 name=f"sciforge-{wid}")
            t.start()
            self._threads.append(t)
        self._snapshot()
        return recovered

    def stop_workers(self, timeout: float = 10.0) -> None:
        self.stop = True
        for t in self._threads:
            t.join(timeout=timeout)
        self._threads.clear()

    def work(self, worker_id: str = "worker-0") -> None:
        """Worker loop: neither a crashed run nor a thread-level blast kills the
        loop (exception isolation at both levels)."""
        while not self.stop:
            try:
                item = self.store.claim(worker_id, self.lease_seconds)
            except Exception:  # DB busy/corrupt: retry instead of losing a worker
                time.sleep(self.poll_interval)
                continue
            if item is None:
                self._maybe_poll_sources()
                time.sleep(self.poll_interval)
                continue
            try:
                self.run_one(item, worker_id)
            except Exception:  # last-resort isolation (run_one has its own)
                try:
                    self.store.finish(item["run_id"], FAILED,
                                      error="worker loop crashed")
                except Exception:
                    pass

    def run_one(self, item: dict, worker_id: str = "worker-0") -> dict:
        rid = item["run_id"]
        if not valid_run_id(rid):
            self.store.finish(rid, FAILED, error=f"unsafe run_id: {rid!r}")
            return {"run_id": rid, "state": FAILED, "error": "unsafe run_id"}
        ws = self.archive / rid
        with self._active_lock:
            self._active[rid] = {"worker": worker_id, "pid": os.getpid(),
                                 "started_at": time.time()}
        terminal, error, result = FAILED, None, None
        try:
            k = Kernel(ws)
            k.start(rid, item["problem"], item.get("effort") or self.effort,
                    host=self.host)
            while not self.stop:
                self.store.heartbeat(rid, worker_id, self.lease_seconds)
                r = k.step()
                result = r
                status = r.get("status")
                if status in ("done", "blocked", "error",
                              "blocked_checkpoint", "halted"):
                    terminal = {"done": DONE, "blocked": BLOCKED,
                                "error": FAILED, "blocked_checkpoint": BLOCKED,
                                "halted": BLOCKED}[status]
                    if terminal == FAILED:
                        error = r.get("reason") or r.get("notes")
                    break
            else:
                terminal, error = BLOCKED, "daemon stopping"
        except DispatchError as e:
            # a live kernel (manual CLI / another daemon) owns the workspace
            if "holds this workspace" in str(e):
                terminal, error = BLOCKED, str(e)
            else:
                terminal, error = FAILED, f"{type(e).__name__}: {e}"
                self._record_crash(ws, rid, error)
        except Exception as e:  # noqa: BLE001 — one run must never kill the worker
            terminal, error = FAILED, f"{type(e).__name__}: {e}"
            self._record_crash(ws, rid, error)
        finally:
            try:
                self.store.finish(rid, terminal, result=result, error=error)
            except Exception:
                pass  # row stays 'running'; restart takeover will recover it
            with self._active_lock:
                self._active.pop(rid, None)
            self._snapshot()
        return {"run_id": rid, "state": terminal, "error": error}

    def _record_crash(self, ws: Path, rid: str, error: str) -> None:
        """Make a crashed run identifiable instead of leaving RUNSTATE dangling.
        RUNSTATE's status enum is schema-frozen, so the crash lands as
        paused_blocked + reason_code=daemon_worker_crash (plus an event and the
        legacy daemon-error.txt). Never touch state owned by another process."""
        try:
            (ws / ".sciforge").mkdir(parents=True, exist_ok=True)
            (ws / ".sciforge" / "daemon-error.txt").write_text(
                error + "\n" + traceback.format_exc())
        except OSError:
            pass
        if holder_alive(ws) and not lock_owned_by_this_process(ws):
            return  # someone else drives this workspace; do not forge its state
        try:
            rs = RunState(ws)
            if rs.data and rs.status not in ("completed", "killed"):
                from .state import EventLog
                log = EventLog(ws)
                # A broken chain outranks the crash as the reason to record:
                # labelling a tampered run "daemon_worker_crash" would hide the
                # integrity failure, and appending to a compromised ledger
                # extends it. Report the break and leave the log untouched.
                if log.verify_chain().get("ok", True):
                    rs.status = "paused_blocked"
                    rs.update(reason_code="daemon_worker_crash")
                    rs.write()
                    log.emit(rs.data.get("current_phase", "?"),
                             "daemon_error",
                             {"error": error, "run_id": rid,
                              "worker_crash": True})
                else:
                    rs.status = "paused_blocked"
                    rs.update(reason_code="event_log_integrity_broken")
                    rs.write()
        except Exception:
            pass
        try:
            release_lock(ws)  # a crashed worker must not keep the flock
        except Exception:
            pass

    def _maybe_poll_sources(self) -> None:
        now = time.time()
        with self._sources_lock:
            if now - self._last_sources_poll < SOURCES_POLL_SECONDS:
                return
            self._last_sources_poll = now
        # v1.7.2 (D6): idle moments poll the source registry — bench topic
        # lists / inbox briefings become first-class producers with
        # dedup-by-id (plus the durable queue's own run_id uniqueness).
        try:
            from . import sources as src_mod
            new, _ = src_mod.poll_all(self.archive)
            for prob in new:
                rid = f"{prob['source_id']}_{prob['id']}"
                if not valid_run_id(rid):  # source ids become directory names
                    rid = re.sub(r"[^A-Za-z0-9._-]+", "_", rid).strip("._-") or \
                        f"Q{int(time.time() * 1000)}"
                self.enqueue(rid, prob["problem"])
        except Exception:
            pass

    # ---------- HTTP ----------
    def handler(self):
        daemon = self

        class H(BaseHTTPRequestHandler):
            def _send(self, code: int, obj):
                body = json.dumps(obj, indent=2, ensure_ascii=False,
                                  default=str).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _authorized(self) -> bool:
                hdr = self.headers.get("authorization", "") or ""
                token = hdr[7:].strip() if hdr[:7].lower() == "bearer " else ""
                if not token:
                    token = (self.headers.get("x-sciforge-token") or "").strip()
                if not token:
                    self._send(401, {
                        "error": "missing token",
                        "hint": "Authorization: Bearer <token> "
                                f"(token file: {daemon.token_path})"})
                    return False
                if not hmac.compare_digest(token, daemon.token):
                    self._send(403, {"error": "invalid token"})
                    return False
                return True

            def _parts(self) -> list[str]:
                return [p for p in urlsplit(self.path).path.split("/") if p]

            def _body(self):
                try:
                    n = int(self.headers.get("content-length") or 0)
                except ValueError:
                    self._send(400, {"error": "bad content-length"})
                    return None
                if n > 1_048_576:
                    self._send(413, {"error": "body too large"})
                    return None
                raw = self.rfile.read(n) if n else b"{}"
                try:
                    body = json.loads(raw or b"{}")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._send(400, {"error": "invalid JSON body"})
                    return None
                if not isinstance(body, dict):
                    self._send(400, {"error": "JSON body must be an object"})
                    return None
                return body

            # ---- read-only surface (no token: status pages / monitors) ----
            def do_GET(self):
                parts = self._parts()
                if parts == ["health"]:
                    counts = daemon.store.counts()
                    return self._send(200, {
                        "ok": True, "pid": os.getpid(),
                        "concurrency": daemon.concurrency,
                        "active": daemon.active,
                        "active_runs": daemon.active_records(),
                        "queued": counts.get(QUEUED, 0),
                        "states": counts,
                        "auth": "bearer-token",
                    })
                if parts in (["queue"], ["runs"]):
                    state = None
                    q = urlsplit(self.path).query
                    if q.startswith("state="):
                        state = q.split("=", 1)[1]
                    return self._send(200, {"runs": daemon.store.list(state)})
                if len(parts) == 2 and parts[0] == "runs":
                    rid = parts[1]
                    if not valid_run_id(rid):
                        return self._send(404, {"error": "not found"})
                    rs = RunState(daemon.archive / rid)
                    trail = {}
                    try:
                        ev = daemon.archive / rid / ".sciforge" / "events.ndjson"
                        kinds = {}
                        for line in ev.read_text().splitlines():
                            kind = json.loads(line)["kind"]
                            kinds[kind] = kinds.get(kind, 0) + 1
                        trail = kinds
                    except Exception:
                        pass
                    return self._send(200, {"runstate": rs.data, "trail": trail,
                                            "queue": daemon.store.get(rid)})
                if parts == ["daily"]:
                    from .evolve_cli import daily_digest
                    return self._send(200, {"digest": daily_digest(daemon.archive)})
                return self._send(404, {"error": "not found"})

            # ---- state-changing surface (bearer token required) ----
            def do_POST(self):
                if not self._authorized():
                    return
                body = self._body()
                if body is None:
                    return
                parts = self._parts()
                if parts == ["runs"]:
                    problem = body.get("problem")
                    if not isinstance(problem, str) or not problem.strip():
                        return self._send(400, {"error": "problem is required"})
                    rid = body.get("run_id") or f"Q{int(time.time() * 1000)}"
                    if not valid_run_id(rid):
                        return self._send(400, {"error": "invalid run_id"})
                    rec = daemon.enqueue(rid, problem)
                    return self._send(201 if not rec.get("duplicate") else 409, rec)
                if len(parts) == 3 and parts[0] == "runs":
                    rid, action = parts[1], parts[2]
                    if not valid_run_id(rid):
                        return self._send(404, {"error": "not found"})
                    if action in ("approve", "deny"):
                        return self._decide(rid, action, body)
                    if action == "resume":
                        cur = daemon.store.get(rid)
                        if cur is None:
                            return self._send(404, {"error": "run not found"})
                        if cur.get("state") not in (BLOCKED, FAILED):
                            return self._send(409, {
                                "error": "only blocked/failed runs can be resumed",
                                "run": cur})
                        rec = daemon.store.requeue(rid, note="resume requested via api")
                        daemon._snapshot()
                        return self._send(202, rec)
                    if action == "cancel":
                        cur = daemon.store.get(rid)
                        if cur is None:
                            return self._send(404, {"error": "run not found"})
                        if cur.get("state") not in (QUEUED, BLOCKED, FAILED):
                            return self._send(409, {
                                "error": f"cannot cancel a {cur.get('state')} run",
                                "run": cur})
                        rec = daemon.store.cancel(rid, note="cancel requested via api")
                        daemon._snapshot()
                        return self._send(200, rec)
                return self._send(404, {"error": "not found"})

            def _decide(self, rid: str, action: str, body: dict):
                checkpoint = body.get("checkpoint")
                if not isinstance(checkpoint, str) or not checkpoint.strip():
                    return self._send(400, {"error": "checkpoint is required"})
                ws = daemon.archive / rid
                if not (ws / ".sciforge").exists():
                    return self._send(404, {"error": "run workspace not found"})
                approved = bool(body.get("approved", True)) if action == "approve" else False
                # Never trust a body-supplied identity: log the actual channel.
                peer = self.client_address[0] if self.client_address else "?"
                decided_by = f"daemon-api@{peer}"
                try:
                    k = Kernel(ws)
                    rec = k.appr.decide(checkpoint, approved,
                                        decided_by=decided_by,
                                        rs=RunState(ws),
                                        note=str(body.get("note", "")))
                except KeyError as e:
                    return self._send(409, {"error": str(e)})
                except PermissionError as e:
                    return self._send(403, {"error": str(e)})
                except Exception as e:  # noqa: BLE001
                    return self._send(500, {"error": f"{type(e).__name__}: {e}"})
                requeued = False
                if approved:
                    q = daemon.store.get(rid)
                    if q is not None and q.get("state") in (BLOCKED, FAILED):
                        q2 = daemon.store.requeue(rid, note="human approved checkpoint")
                        requeued = bool(q2 and q2.get("state") == QUEUED)
                        daemon._snapshot()
                return self._send(200, {"decision": rec, "requeued": requeued})

            def log_message(self, *a):  # quiet
                pass

        return H


def serve(archive: Path, host: str = "127.0.0.1", port: int = 4510,
          run_host: str = "manual", effort: str = "balanced",
          concurrency: int = 1) -> None:
    archive = Path(archive)
    d = Daemon(archive, host=run_host, effort=effort, concurrency=concurrency)
    # cross-process limiter: workers and host children inherit this env var, so
    # one shared 429 cooldown covers the whole fleet (defect-4 fix).
    os.environ.setdefault("SCIFORGE_LIMITER_DB",
                          str(d.state_dir / "ratelimits.sqlite3"))
    recovered = d.start_workers()
    srv = ThreadingHTTPServer((host, port), d.handler())
    print(f"sciforge daemon on http://{host}:{port} "
          f"(loopback; archive={archive}; workers={d.concurrency})")
    print(f"worker takeover on start: {len(recovered)} crashed run(s) re-queued")
    print(f"auth token: {d.token_path} (mode 0600); send "
          "'Authorization: Bearer <token>' on state-changing requests")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        d.stop_workers()
        srv.server_close()