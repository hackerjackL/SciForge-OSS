"""Run state + event-sourcing for the SciForge kernel (S01/S02).

The event log (.sciforge/events.ndjson) is the durable truth; RUNSTATE.json is
a derived snapshot rewritten at every boundary. A crashed run recovers by
replaying events: status interrupted -> resume from next_action. This mirrors
ScienceDiscovery's events.ndjson + `interrupted` lifecycle and DeepScientist's
replayable quest state, but for our 26-node DAG.

Stdlib only. Every event carries: seq, ts, phase, kind, payload.

v1.7.4 integrity + performance:
  - Events written by this module carry a sha256 hash chain (`prev_hash` +
    `hash` over seq/ts/phase/kind/payload/prev_hash). A same-user agent can no
    longer advance the pipeline by appending a bare `checkpoint_cleared` /
    `phase_done` line: the chain check detects the forged/missing link and
    `recover()` refuses to trust the log. Legacy logs (pre-v1.7.4, no chain
    fields) are recognised explicitly and still replay (marked `legacy`);
    chain-less events are never mistaken for a break. This is tamper-EVIDENT,
    not tamper-proof: no secret is involved, so a determined agent that
    rewrites the whole file with a recomputed chain is out of this threat
    model (same uid; the same agent could patch this source file).
  - `replay()` is incremental: it keeps the parsed event list and the file
    offset in memory and only reads/parses the newly appended tail. A
    truncated/replaced file invalidates the offset and falls back to a full
    re-read; a torn final line is skipped (and left pending) exactly as the
    old full-scan code did.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

try:  # POSIX advisory locks; the primary atomicity mechanism
    import fcntl as _fcntl
except ImportError:  # Windows
    _fcntl = None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# Fixed anchor for the first chained event (conventional all-zero digest).
GENESIS_HASH = "0" * 64

# The fields an event's own hash commits to. `hash` is excluded (it is the
# digest itself); everything else that identifies the event is covered.
_HASHED_FIELDS = ("seq", "ts", "phase", "kind", "payload", "prev_hash")


def event_hash(ev: dict) -> str:
    """Canonical digest of an event's committed fields (key order independent)."""
    core = {k: ev.get(k) for k in _HASHED_FIELDS}
    if core.get("payload") is None:
        core["payload"] = {}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class EventChainError(RuntimeError):
    """A chained event log failed verification (forgery / tampering)."""

    def __init__(self, integrity: dict):
        self.integrity = integrity or {}
        super().__init__(
            "event log hash chain broken at index "
            f"{self.integrity.get('broken_at')} (seq "
            f"{self.integrity.get('broken_seq')}): "
            f"{self.integrity.get('reason')}")


def _seq_of(ev: dict):
    try:
        return int(ev.get("seq"))
    except (TypeError, ValueError):
        return None


def _parse_event_lines(raw: bytes) -> list[dict]:
    """All parseable events from raw NDJSON bytes (torn lines skipped)."""
    out: list[dict] = []
    for line in raw.split(b"\n"):
        text = line.strip()
        if not text:
            continue
        try:
            ev = json.loads(text.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue  # torn write during crash; skip, keep replaying
        if isinstance(ev, dict):
            out.append(ev)
    return out


def _verify_events(events: list[dict]) -> dict:
    """Validate a parsed event sequence. Pure; used by verify_chain().

    Returns ok/legacy/total/broken_at(0-based index)/broken_seq/reason/head_hash.
    A log with NO chain fields anywhere is a legitimate legacy log (pre-v1.7.4)
    and verifies as `legacy: True, ok: True`. Once chain fields appear, every
    event must carry a valid link — a missing/mismatched link, or a chainless
    event after a chained one, is a break (first one reported).
    """
    out = {"ok": True, "legacy": False, "total": len(events),
           "broken_at": None, "broken_seq": None, "reason": "",
           "head_hash": GENESIS_HASH}
    if not events:
        return out
    if not any(("prev_hash" in e) or ("hash" in e) for e in events):
        out["legacy"] = True
        return out
    prev = GENESIS_HASH
    for i, ev in enumerate(events):
        if "prev_hash" not in ev or "hash" not in ev:
            out.update(ok=False, broken_at=i, broken_seq=_seq_of(ev),
                       reason="chain fields missing (mixed or forged event)")
            return out
        if ev.get("prev_hash") != prev:
            out.update(ok=False, broken_at=i, broken_seq=_seq_of(ev),
                       reason="prev_hash mismatch (event inserted/reordered)")
            return out
        if event_hash(ev) != ev.get("hash"):
            out.update(ok=False, broken_at=i, broken_seq=_seq_of(ev),
                       reason="event hash mismatch (content tampered)")
            return out
        prev = ev["hash"]
    out["head_hash"] = prev
    return out


class EventLog:
    """Append-only NDJSON event stream; replay = authoritative state rebuild.

    Incremental: the parsed events + byte offset are cached per instance, so
    replay() only reads the tail appended since the previous call. Instances
    never share mutable state — two EventLogs on the same file each track their
    own offset and re-synchronise from disk before every emit/replay.
    """

    def __init__(self, ws: Path):
        self.ws = Path(ws)
        self.path = self.ws / ".sciforge" / "events.ndjson"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._parse_count = 0  # test/diagnostics: cumulative, survives resets
        self._reset()
        self._sync()

    # ---- internal cache ----
    def _reset(self) -> None:
        self._events: list[dict] = []
        self._seq = 0
        self._offset = 0
        self._file_id = None
        self._prefix_len = 0
        self._prefix_sig = None
        self._head_hash = GENESIS_HASH
        self._legacy = False
        self._chain_ok = True
        self._broken_at = None
        self._broken_seq = None
        self._break_reason = ""

    def _mark_broken(self, idx: int, ev: dict, reason: str) -> None:
        if self._chain_ok:  # report the FIRST break only
            self._chain_ok = False
            self._broken_at = idx
            self._broken_seq = _seq_of(ev)
            self._break_reason = reason

    def _absorb(self, ev: dict) -> None:
        """Append one parsed event to the cache and extend the chain state."""
        idx = len(self._events)
        self._events.append(ev)
        self._parse_count += 1
        seq = _seq_of(ev)
        if seq is not None:
            self._seq = max(self._seq, seq)
        chained = ("prev_hash" in ev) or ("hash" in ev)
        if idx == 0 and not chained:
            self._legacy = True
            self._head_hash = GENESIS_HASH
            return
        if self._legacy:
            if chained:
                self._mark_broken(idx, ev,
                                  "chained event appended to a legacy log")
            return
        if "prev_hash" not in ev or "hash" not in ev:
            self._mark_broken(idx, ev,
                              "chain fields missing (mixed or forged event)")
        elif ev.get("prev_hash") != self._head_hash:
            self._mark_broken(idx, ev,
                              "prev_hash mismatch (event inserted/reordered)")
        elif event_hash(ev) != ev.get("hash"):
            self._mark_broken(idx, ev,
                              "event hash mismatch (content tampered)")
        if isinstance(ev.get("hash"), str):
            # Follow the stored link even after a break: subsequent events are
            # judged against what is on disk, not against our expectation.
            self._head_hash = ev["hash"]

    def _prefix_signature(self, n: int):
        """sha256 of the first n bytes (n bounded by the consumed prefix)."""
        if n <= 0:
            return hashlib.sha256(b"").hexdigest()
        try:
            with open(self.path, "rb") as f:
                return hashlib.sha256(f.read(n)).hexdigest()
        except OSError:
            return None

    def _record_prefix(self) -> None:
        """Extend the stable-prefix fingerprint to min(4096, consumed bytes).

        Only ever covers bytes we have already consumed, so normal appends
        (which grow the file past the recorded prefix) cannot invalidate it;
        an in-place rewrite of the consumed region changes it and forces a
        full re-read.
        """
        if self._offset <= self._prefix_len or self._prefix_len >= 4096:
            return
        new_len = min(4096, self._offset)
        sig = self._prefix_signature(new_len)
        if sig is not None:
            self._prefix_len, self._prefix_sig = new_len, sig

    def _sync(self) -> list[dict]:
        """Read and absorb only the file tail appended since the last call."""
        if not self.path.exists():
            if self._events or self._offset or self._file_id is not None:
                self._reset()
            return self._events
        try:
            st = self.path.stat()
        except OSError:
            return self._events
        ident = (st.st_dev, st.st_ino)
        reset = False
        if self._file_id is not None and ident != self._file_id:
            reset = True            # replaced (atomic rename / new inode)
        elif st.st_size < self._offset:
            reset = True            # truncated
        elif self._prefix_len and self._prefix_sig is not None:
            if self._prefix_signature(self._prefix_len) != self._prefix_sig:
                reset = True        # consumed region rewritten in place
        if reset:
            self._file_id = None
            self._prefix_len = 0
            self._prefix_sig = None
            self._reset()
        if self._file_id is None:
            self._file_id = ident
        if st.st_size <= self._offset:
            self._record_prefix()
            return self._events
        with open(self.path, "rb") as f:
            f.seek(self._offset)
            chunk = f.read()
        pos = 0
        consumed = 0
        n = len(chunk)
        while pos < n:
            nl = chunk.find(b"\n", pos)
            has_nl = nl != -1
            end = (nl + 1) if has_nl else n
            raw = chunk[pos:nl] if has_nl else chunk[pos:]
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                consumed = end
                pos = end
                continue
            try:
                ev = json.loads(text)
            except (json.JSONDecodeError, UnicodeDecodeError):
                consumed = end
                pos = end
                if not has_nl:
                    # Incomplete final line (crash mid-write): skip it but do
                    # NOT consume it, so a later completed write is still read.
                    consumed = chunk.rfind(b"\n", 0, n) + 1 if b"\n" in chunk else 0
                    break
                continue
            if isinstance(ev, dict):
                self._absorb(ev)
            consumed = end
            pos = end
        self._offset += consumed
        self._record_prefix()
        return self._events

    # ---- public API ----
    def emit(self, phase: str, kind: str, payload: dict | None = None) -> dict:
        self._sync()  # another instance may have appended since our last look
        self._seq += 1
        ev = {"seq": self._seq, "ts": time.time(), "phase": phase, "kind": kind,
              "payload": payload or {}}
        if not self._legacy:
            ev["prev_hash"] = self._head_hash
            ev["hash"] = event_hash(ev)
        # A crashed writer may have left an unterminated fragment; terminate it
        # so this event starts on its own (invalid) line instead of being
        # concatenated into it. The fragment is skipped by replay either way.
        sep = ""
        try:
            if self.path.exists() and self.path.stat().st_size > 0:
                with open(self.path, "rb") as f:
                    f.seek(-1, os.SEEK_END)
                    if f.read(1) != b"\n":
                        sep = "\n"
        except OSError:
            sep = ""
        line = sep + json.dumps(ev, ensure_ascii=False) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
        try:
            self._offset = self.path.stat().st_size
        except OSError:
            self._offset += len(line.encode("utf-8"))
        self._record_prefix()
        self._absorb(ev)
        return ev

    def replay(self, strict: bool = False):
        """All events (full list contract preserved); reads only the new tail.

        strict=True raises EventChainError instead of returning events from a
        chained log that failed verification.
        """
        self._sync()
        if strict and not self._chain_ok:
            raise EventChainError(self.integrity())
        return list(self._events)

    def integrity(self) -> dict:
        """Cached chain state (updated by the incremental sync)."""
        self._sync()
        return {"ok": self._chain_ok, "legacy": self._legacy,
                "total": len(self._events), "broken_at": self._broken_at,
                "broken_seq": self._broken_seq, "reason": self._break_reason,
                "head_hash": self._head_hash}

    def verify_chain(self) -> dict:
        """Authoritative fresh scan of the file on disk (not the cache)."""
        try:
            raw = self.path.read_bytes()
        except OSError:
            raw = b""
        return _verify_events(_parse_event_lines(raw))


class RunState:
    """RUNSTATE.json v2 — derived snapshot + resume contract (output-protocol compatible)."""

    FILENAME = "RUNSTATE.json"

    def __init__(self, ws: Path):
        self.ws = Path(ws)
        self.path = self.ws / ".sciforge" / self.FILENAME
        self.data = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.data = {}

    # ---- lifecycle status: exactly the registered RUNSTATE.schema.json enum ----
    STATUS = ("running", "paused_checkpoint", "paused_blocked", "completed", "killed")

    @property
    def status(self) -> str:
        return self.data.get("status", "created")

    @status.setter
    def status(self, v: str):
        assert v in self.STATUS, v
        self.data["status"] = v

    def update(self, *, phase: str | None = None, next_action: str | None = None,
               last_boundary: str | None = None, pending: list | None = None,
               budget_snapshot: dict | None = None, verdict: str | None = None,
               reason_code: str | None = None):
        d = self.data
        if phase is not None:
            d["current_phase"] = phase
        if next_action is not None:
            d["next_action"] = next_action
        if last_boundary is not None:
            d["last_completed_boundary"] = last_boundary
        if pending is not None:
            d["pending_approvals"] = pending
        if budget_snapshot is not None:
            d["budget_snapshot"] = budget_snapshot
        if verdict is not None:
            d["phase_verdicts"] = d.get("phase_verdicts", {})
            d["phase_verdicts"][d.get("current_phase", "")] = verdict
        if reason_code is not None:
            d["reason_code"] = reason_code
        d["schema_version"] = "2.0"
        d["updated_at"] = time.time()

    def write(self):
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
        os.replace(tmp, self.path)  # atomic: torn RUNSTATE can never strand a run

    @classmethod
    def open_workspace(cls, ws: Path, run_id: str, problem: str) -> "RunState":
        ws = Path(ws)
        (ws / ".sciforge" / "verdicts").mkdir(parents=True, exist_ok=True)
        (ws / ".sciforge" / "logs").mkdir(parents=True, exist_ok=True)
        (ws / ".sciforge" / "refine-logs").mkdir(parents=True, exist_ok=True)
        rs = cls(ws)
        if rs.data and rs.status not in ("completed", "failed", "cancelled"):
            raise FileExistsError(
                f"workspace {ws} has live run {rs.data.get('run_id')} ({rs.status}); "
                "use `sciforge resume` or a fresh dir")
        rs.data = {"run_id": run_id, "problem": problem,
                   "problem_hash": None, "phase_order_source": "kernel/config/phasegraph.json",
                   "created_at": time.time()}
        return rs


# ---------------- kernel lock (atomic, pid-reuse safe) ----------------
#
# v1.7.3 defect-3 fix. The old lock was a pid file probed with os.kill(pid, 0):
# (a) a dead holder's pid can be reused by an unrelated process -> a false
# "alive", and (b) two processes could both pass recover() before either
# wrote the file (TOCTOU). The lock is now an OS advisory lock (fcntl.flock on
# POSIX) held for the lifetime of the owning process, with an in-file JSON
# identity (pid + process start time + random nonce) so a probe can detect pid
# reuse. Stale files are harmless: correctness comes from the OS lock, never
# from the file's existence. Plain-pid files written by v1.7.2 or earlier are
# still understood (pid probe) for crash recovery. On Windows (no fcntl) the
# degraded path is O_CREAT|O_EXCL creation + the same pid/start identity.

LOCK_FILENAME = "kernel.lock"


class LockHeldError(RuntimeError):
    """Another live process already owns this workspace's kernel lock."""


_lock_registry: dict[str, dict] = {}
_registry_guard = threading.Lock()


def _lock_path(ws: Path) -> Path:
    return Path(ws) / ".sciforge" / LOCK_FILENAME


def pid_alive(pid: int | None) -> bool:
    """Cross-platform liveness probe. os.kill(pid, 0) is NOT safe on Windows
    (CPython maps any non-console signal to TerminateProcess — probing would
    kill the target), so Windows uses OpenProcess+WaitForSingleObject."""
    if pid is None:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        return _win_pid_alive(pid)
    try:
        os.kill(pid, 0)  # 0 = liveness probe, sends nothing
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except OSError:
        return False
    return True


def _win_pid_alive(pid: int) -> bool:
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        SYNCHRONIZE = 0x00100000
        handle = k32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        try:
            return k32.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return False


def proc_start_time(pid: int) -> str | None:
    """Stable identity for a pid (defeats pid reuse). Linux: /proc starttime;
    macOS/BSD: `ps -o lstart=`; Windows: GetProcessTimes via ctypes. Returns
    None when the platform cannot answer — callers then fall back to the OS
    lock (POSIX) or a pessimistic pid check."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if sys.platform.startswith("win"):
        return _win_proc_start(pid)
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists():
        try:
            raw = stat.read_text()
            # comm (field 2) may contain spaces/parens -> split after last ')'
            rest = raw[raw.rfind(")") + 2:]
            return rest.split()[19]  # field 22 = starttime
        except (OSError, IndexError):
            return None
    try:
        out = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"})
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _win_proc_start(pid: int) -> str | None:
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            creation, exit_, kernel, user = (wintypes.FILETIME() for _ in range(4))
            ok = k32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_),
                                     ctypes.byref(kernel), ctypes.byref(user))
            if not ok:
                return None
            return str((creation.dwHighDateTime << 32) | creation.dwLowDateTime)
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return None


def _read_lock_file(lock: Path) -> tuple[str | None, object]:
    """-> (kind, data): ('json', dict) | ('legacy', raw text) | (None, None)."""
    try:
        raw = lock.read_text()
    except OSError:
        return None, None
    raw = raw.strip()
    if not raw:
        return "json", {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return "legacy", raw
    if isinstance(data, dict):
        return "json", data
    return "legacy", raw


def _flock_probe(lock: Path) -> bool | None:
    """Definitive POSIX probe: True = some live process holds the OS lock.
    None = unsupported platform."""
    if _fcntl is None:
        return None
    try:
        fd = os.open(lock, os.O_RDWR)
    except OSError:
        return None
    try:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        except OSError:
            return True
        try:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        except OSError:
            pass
        return False
    finally:
        os.close(fd)


def holder_alive(ws: Path) -> bool:
    """True only when a *live* process owns the workspace kernel lock.

    New-format locks validate pid + process start time (pid reuse => False);
    when identity is unavailable the OS flock probe is authoritative. Legacy
    bare-pid files keep the old pid probe so pre-v1.7.3 crash recovery and its
    regression tests behave identically."""
    lock = _lock_path(ws)
    kind, data = _read_lock_file(lock)
    if kind is None:
        return False
    if kind == "legacy":
        try:
            pid = int(str(data).split()[0])
        except (ValueError, IndexError):
            probe = _flock_probe(lock)
            return bool(probe) if probe is not None else False
        return pid_alive(pid)
    if not isinstance(data, dict) or data.get("released"):
        return False
    pid = data.get("pid")
    if not isinstance(pid, int) or not pid_alive(pid):
        return False
    stored_start = data.get("start")
    if stored_start is not None:
        actual = proc_start_time(pid)
        if actual is not None:
            return str(actual) == str(stored_start)
    probe = _flock_probe(lock)
    if probe is not None:
        return probe
    return True  # pid alive, identity unverifiable on this platform


def lock_owned_by_this_process(ws: Path) -> bool:
    key = str(Path(ws).resolve())
    with _registry_guard:
        rec = _lock_registry.get(key)
    if rec is None:
        return False
    if rec.get("fd") is not None:
        return True  # the OS lock cannot be held by anyone else
    kind, data = _read_lock_file(_lock_path(ws))
    return (kind == "json" and isinstance(data, dict)
            and data.get("nonce") == rec.get("nonce"))


def _payload(nonce: str) -> dict:
    return {"pid": os.getpid(), "nonce": nonce,
            "start": proc_start_time(os.getpid()),
            "host": socket.gethostname(), "acquired_at": time.time(),
            "lock_version": 2}


def _write_payload(fd: int, payload: dict) -> None:
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, json.dumps(payload).encode())
    os.fsync(fd)


def take_lock(ws: Path) -> dict:
    """Atomically acquire the workspace lock (raises LockHeldError on a live
    holder). Reentrant for the same process+workspace: the held fd is reused.
    Returns the lock payload (pid/nonce/start) for diagnostics."""
    ws = Path(ws)
    lock = _lock_path(ws)
    lock.parent.mkdir(parents=True, exist_ok=True)
    key = str(ws.resolve())
    with _registry_guard:
        existing = _lock_registry.get(key)
    if existing is not None:
        payload = _payload(existing["nonce"])
        if existing.get("fd") is not None:
            _write_payload(existing["fd"], payload)
        return payload
    if _fcntl is not None:
        return _take_flock(ws, lock, key)
    return _take_exclusive(ws, lock, key)


def _take_flock(ws: Path, lock: Path, key: str) -> dict:
    for _ in range(8):
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise LockHeldError(
                f"workspace {ws} is locked by another live kernel process")
        # unlink-vs-lock race: the path may have been replaced while we waited
        try:
            st = os.stat(lock)
        except FileNotFoundError:
            os.close(fd)
            continue
        fst = os.fstat(fd)
        if (st.st_dev, st.st_ino) != (fst.st_dev, fst.st_ino):
            os.close(fd)
            continue
        nonce = secrets.token_hex(16)
        payload = _payload(nonce)
        try:
            _write_payload(fd, payload)
        except OSError:
            os.close(fd)
            raise
        with _registry_guard:
            _lock_registry[key] = {"fd": fd, "nonce": nonce, "pid": os.getpid()}
        return payload
    raise LockHeldError(f"workspace {ws}: lock file replaced during acquisition")


def _take_exclusive(ws: Path, lock: Path, key: str) -> dict:
    """Windows/degraded path: O_CREAT|O_EXCL is the atomic primitive; stale
    files are reclaimed only when no live holder is detected."""
    nonce = secrets.token_hex(16)
    payload = _payload(nonce)
    for _ in range(4):
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            if holder_alive(ws):
                raise LockHeldError(
                    f"workspace {ws} is locked by another live kernel process")
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
            continue
        try:
            os.write(fd, json.dumps(payload).encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        with _registry_guard:
            _lock_registry[key] = {"fd": None, "nonce": nonce, "pid": os.getpid()}
        return payload
    raise LockHeldError(f"workspace {ws}: could not acquire lock after stale-file retries")


def release_lock(ws: Path):
    """Release only OUR lock (never a successor's). Unlink happens before the
    fd close so a racing opener detects the inode swap and retries."""
    ws = Path(ws)
    lock = _lock_path(ws)
    key = str(ws.resolve())
    with _registry_guard:
        rec = _lock_registry.pop(key, None)
    if rec is None:
        kind, data = _read_lock_file(lock)
        if kind == "json" and isinstance(data, dict):
            if data.get("pid") != os.getpid():
                return
        elif kind == "legacy":
            if str(data).strip() != str(os.getpid()):
                return
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
        return
    kind, data = _read_lock_file(lock)
    ours = (kind == "json" and isinstance(data, dict)
            and data.get("nonce") == rec.get("nonce"))
    if ours:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
    if rec.get("fd") is not None:
        try:
            os.close(rec["fd"])
        except OSError:
            pass


def _close_registry_fds():  # pytest/daemon process teardown hygiene
    with _registry_guard:
        recs = list(_lock_registry.values())
        _lock_registry.clear()
    for rec in recs:
        if rec.get("fd") is not None:
            try:
                os.close(rec["fd"])
            except OSError:
                pass


atexit.register(_close_registry_fds)


def _claim_or_owned(ws: Path) -> bool:
    if lock_owned_by_this_process(ws):
        return True
    try:
        take_lock(ws)
        return True
    except LockHeldError:
        return False


def recover(log: EventLog, rs: RunState, ws: Path) -> str:
    """Startup recovery protocol. Returns: fresh | resume | completed | wait |
    integrity_broken.

    Process death mid-run => stale lock => `running` status is stale, replay
    decides the resume point (dangling boundaries are redone). The lock is now
    claimed atomically BEFORE any state/log mutation, so two processes racing
    on the same crashed workspace cannot both return "resume" (the second gets
    "wait"). Mirrors SciDis: `interrupted` runs recover after process failure;
    DeepScientist: events are replayable, so the log outranks any snapshot.

    v1.7.4: the hash chain is verified BEFORE any state is rebuilt. A chained
    log with a missing/mismatched link (a forged or edited event) is never
    trusted: the run is marked paused_blocked with
    reason_code=event_log_integrity_broken and "integrity_broken" is returned.
    Legacy chainless logs (pre-v1.7.4) verify as `legacy` and proceed.
    """
    ws = Path(ws)
    if not rs.data:
        return "fresh" if _claim_or_owned(ws) else "wait"
    integrity = log.verify_chain()
    if not integrity.get("ok", True):
        rs.status = "paused_blocked"
        rs.update(reason_code="event_log_integrity_broken")
        try:
            rs.write()
        except Exception:
            pass
        return "integrity_broken"
    if rs.status in ("completed", "killed"):
        return "completed"

    owned = lock_owned_by_this_process(ws)
    alive = owned or holder_alive(ws)

    if rs.status == "paused_checkpoint" and not Approvals_pending(ws):
        # human decided elsewhere (approve wrote the log); resume into running
        if alive and not owned:
            return "wait"
        if not owned and not _claim_or_owned(ws):
            return "wait"
        rs.status = "running"
        rs.write()
        return "resume"

    if rs.status == "running":
        if owned:
            return "resume"  # reentrant resume inside the owning process
        if alive:
            return "wait"  # another kernel owns this workspace
        if not _claim_or_owned(ws):
            return "wait"  # lost the race against another recovering process
        last = log.replay()
        uncommitted = [e for e in last if e["kind"] == "phase_done"]
        committed = {e["payload"].get("phase") for e in last if e["kind"] == "boundary_committed"}
        dangling = [e["payload"]["phase"] for e in uncommitted
                    if e["payload"].get("phase") not in committed]
        rs.update(next_action=f"redo boundaries: {dangling}" if dangling else rs.data.get("next_action", ""))
        log.emit(rs.data.get("current_phase", "?"), "recovered",
                 {"from": "crash", "dangling_boundaries": dangling})
        return "resume"

    # paused_blocked / created / other intermediate states
    if alive and not owned:
        return "wait"
    if not owned and not _claim_or_owned(ws):
        return "wait"
    return "resume"


def open_checkpoint_requests(ws: Path) -> dict[str, dict]:
    """Kernel-issued checkpoint requests that are still open, from the event
    ledger (the durable truth). A request is cleared only by a later
    checkpoint_cleared / checkpoint_skipped for the same checkpoint; when both
    carry an epoch nonce they must match. Deleting or forging the mutable
    PENDING_APPROVAL file therefore cannot clear a real request."""
    out: dict[str, dict] = {}
    try:
        log = EventLog(ws)
        events = log.replay()
        trust_clears = log.verify_chain().get("ok", True)
    except Exception:
        return out
    for ev in events:
        kind = ev.get("kind")
        pl = ev.get("payload") or {}
        ck = pl.get("checkpoint")
        if not ck:
            continue
        ck = str(ck)
        if kind == "checkpoint_requested":
            out[ck] = ev
        elif kind in ("checkpoint_cleared", "checkpoint_skipped"):
            # v1.7.4 fail-closed: on a broken hash chain the clear/skip
            # evidence itself is untrustworthy, so every issued request stays
            # open (a forged clear cannot close a real epoch).
            if not trust_clears:
                continue
            cur = out.get(ck)
            if cur is None:
                continue
            cur_nonce = (cur.get("payload") or {}).get("nonce")
            ev_nonce = pl.get("nonce")
            if cur_nonce and ev_nonce and cur_nonce != ev_nonce:
                continue  # a different epoch's clear
            out.pop(ck, None)
    return out


def Approvals_pending(ws: Path) -> bool:
    """Fail-closed: a kernel-issued request that was never cleared keeps the
    run blocked even if its approval file was deleted or hand-edited."""
    if open_checkpoint_requests(ws):
        return True
    d = Path(ws) / ".sciforge" / "approvals"
    if not d.exists():
        return False
    for f in d.glob("*.json"):
        try:
            if json.loads(f.read_text()).get("status") == "PENDING":
                return True
        except Exception:
            continue
    return False
