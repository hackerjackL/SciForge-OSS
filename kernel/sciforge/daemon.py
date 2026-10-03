"""`sciforge serve` — headless daemon for overnight/queue autonomy (EvoScientist/DeepScientist lesson).

Zero-GUI by design: the daemon is a loopback HTTP control surface + queue
worker. Browsers/curl/SSH-tunnel are optional; `run`/`resume`/`status` CLI
commands talk to the same files the daemon owns (RUNSTATE/events/verdicts),
so a queue client can be a one-line curl:

    POST /runs {"problem": "...", "effort": "lite"}   -> run_id queued
    GET  /runs/<id>                                   -> RUNSTATE + trail
    POST /runs/<id>/approve {"checkpoint": "idea-pick"}-> human decision (S05)
    GET  /daily                                       -> evolution digest (S17)

Worker semantics: one run at a time per daemon (budget isolation), manual-host
protocol for LLM phases unless --host claude given. Stdlib http.server. This is
the "runs on a Linux GPU box without X11" answer to the project goal.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .pipeline import Kernel, PhaseGraph
from .state import RunState


class Daemon:
    def __init__(self, archive: Path, host: str = "manual", effort: str="balanced"):
        self.archive = Path(archive)
        self.archive.mkdir(parents=True, exist_ok=True)
        self.host = host
        self.effort = effort
        self.queue: list[dict] = []
        self.active: str | None = None
        self.stop = False
        self._lock = threading.Lock()

    # ---------- queue ops ----------
    def enqueue(self, run_id: str, problem: str) -> dict:
        with self._lock:
            rec = {"run_id": run_id, "problem": problem, "queued_at": time.time()}
            self.queue.append(rec)
            self._persist_queue()
        return rec

    def _persist_queue(self):
        (self.archive / "queue.json").write_text(json.dumps(
            {"queue": self.queue, "active": self.active}, indent=2))

    def _next(self):
        with self._lock:
            return self.queue.pop(0) if self.queue else None

    # ---------- worker ----------
    def work(self):
        while not self.stop:
            if self.active:
                time.sleep(2)
                continue
            item = self._next()
            if not item:
                # v1.7.2 (D6): idle moments poll the source registry — bench
                # topic lists / inbox briefings become first-class producers
                # with dedup-by-id, so restarts never double-queue.
                try:
                    from . import sources as src_mod
                    new, _ = src_mod.poll_all(self.archive)
                    for prob in new:
                        self.enqueue(f"{prob['source_id']}_{prob['id']}",
                                     prob["problem"])
                except Exception:
                    pass
                time.sleep(2)
                continue
            ws = self.archive / item["run_id"]
            self.active = item["run_id"]
            self._persist_queue()
            try:
                k = Kernel(ws)
                k.start(item["run_id"], item["problem"], self.effort, host=self.host)
                # headless loop; blocked_on_checkpoint surfaces as halted state
                while True:
                    r = k.step()
                    if r["status"] in ("done", "blocked", "error", "blocked_checkpoint", "halted"):
                        break
            except Exception as e:
                (ws / ".sciforge" / "daemon-error.txt").write_text(str(e))
            self.active = None
            self._persist_queue()

    # ---------- HTTP ----------
    def handler(self):
        daemon = self

        class H(BaseHTTPRequestHandler):
            def _send(self, code: int, obj):
                body = json.dumps(obj, indent=2, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/health":
                    return self._send(200, {"ok": True, "active": daemon.active,
                                            "queued": len(daemon.queue)})
                if self.path.startswith("/runs/"):
                    rid = self.path.split("/")[2]
                    rs = RunState(daemon.archive / rid)
                    trail = {}
                    try:
                        ev = daemon.archive / rid / ".sciforge" / "events.ndjson"
                        kinds = {}
                        for line in ev.read_text().splitlines():
                            k = json.loads(line)["kind"]
                            kinds[k] = kinds.get(k, 0) + 1
                        trail = kinds
                    except Exception:
                        pass
                    return self._send(200, {"runstate": rs.data, "trail": trail})
                if self.path == "/daily":
                    from .evolve_cli import daily_digest
                    return self._send(200, {"digest": daily_digest(daemon.archive)})
                return self._send(404, {"error": "not found"})

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/runs":
                    rid = body.get("run_id") or f"Q{int(time.time()) % 100000:05d}"
                    rec = daemon.enqueue(rid, body.get("problem", rid))
                    return self._send(201, rec)
                if self.path.startswith("/runs/") and self.path.endswith("/approve"):
                    rid = self.path.split("/")[2]
                    from .approvals import Approvals
                    k = Kernel(daemon.archive / rid)
                    try:
                        rec = daemon_approve(k, body)
                        return self._send(200, rec)
                    except Exception as e:
                        return self._send(409, {"error": str(e)})
                return self._send(404, {"error": "not found"})

            def log_message(self, *a):  # quiet
                pass

        def daemon_approve(k: Kernel, body: dict):
            ck = body.get("checkpoint")
            approved = bool(body.get("approved", True))
            return k.appr.decide(ck, approved, decided_by=body.get("decided_by", "api"),
                                 rs=k.rs, note=body.get("note", ""))

        return H


def serve(archive: Path, host: str = "127.0.0.1", port: int = 4510,
          run_host: str = "manual", effort: str = "balanced") -> None:
    d = Daemon(archive, host=run_host, effort=effort)
    threading.Thread(target=d.work, daemon=True).start()
    srv = ThreadingHTTPServer((host, port), d.handler())
    print(f"sciforge daemon on http://{host}:{port} (loopback; archive={archive})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        d.stop = True
        srv.shutdown()
