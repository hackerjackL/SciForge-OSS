"""EventLog cross-process serialisation (v1.7.4).

Before the write lock, three concurrent writers each synced to the same head
and computed prev_hash from it: all 121 events landed but the chain broke at
seq 2 and 78 seq values were duplicated. recover() then reports the log as
tampered and refuses to rebuild the run, so `daemon --workers N` was unusable
on a shared workspace. These tests reproduce that scenario for real (separate
processes, not threads) and pin the single-process behaviour that must not move.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "kernel"))

from sciforge.state import EventLog, GENESIS_HASH  # noqa: E402

_CHILD = '''
import sys, os
sys.path.insert(0, sys.argv[2])
from sciforge.state import EventLog
from pathlib import Path
log = EventLog(Path(sys.argv[1]))
for i in range(int(sys.argv[3])):
    log.emit("1", "burst", {"i": i, "pid": os.getpid()})
'''


def _spawn_writers(ws: Path, n_proc: int, per_proc: int) -> None:
    procs = [subprocess.Popen(
        [sys.executable, "-c", _CHILD, str(ws), str(REPO / "kernel"), str(per_proc)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(n_proc)]
    for p in procs:
        out, err = p.communicate(timeout=180)
        assert p.returncode == 0, err.decode()[-800:]


@pytest.mark.skipif(sys.platform == "win32", reason="flock is POSIX-only")
def test_concurrent_writers_keep_the_chain_intact(tmp_path):
    """The real defect: concurrent emits must not fork prev_hash or reuse seq."""
    EventLog(tmp_path).emit("0", "run_started", {"run_id": "X"})
    _spawn_writers(tmp_path, n_proc=3, per_proc=25)

    log = EventLog(tmp_path)
    events = log.replay()
    verdict = log.verify_chain()
    assert len(events) == 1 + 3 * 25
    assert verdict["ok"], verdict
    seqs = [e["seq"] for e in events]
    assert len(set(seqs)) == len(seqs), "duplicate seq across processes"
    assert seqs == list(range(1, len(seqs) + 1)), "seq must stay contiguous"


@pytest.mark.skipif(sys.platform == "win32", reason="flock is POSIX-only")
def test_concurrent_writers_on_a_fresh_log(tmp_path):
    """No pre-existing event: the first writer must establish genesis exactly once."""
    _spawn_writers(tmp_path, n_proc=3, per_proc=10)
    log = EventLog(tmp_path)
    events = log.replay()
    assert len(events) == 30
    assert log.verify_chain()["ok"]
    assert events[0]["prev_hash"] == GENESIS_HASH
    assert sum(1 for e in events if e["prev_hash"] == GENESIS_HASH) == 1


def test_single_process_emit_is_unchanged(tmp_path):
    """The lock must not alter the ordinary path: contiguous seq, linked hashes."""
    log = EventLog(tmp_path)
    a = log.emit("0", "run_started", {})
    b = log.emit("1", "phase_done", {"x": 1})
    assert a["seq"] == 1 and b["seq"] == 2
    assert a["prev_hash"] == GENESIS_HASH
    assert b["prev_hash"] == a["hash"]
    assert log.verify_chain()["ok"]
    assert len(log.replay()) == 2


def test_two_instances_in_one_process_still_interleave_correctly(tmp_path):
    """Independent instances keep their own offsets but share the file."""
    a, b = EventLog(tmp_path), EventLog(tmp_path)
    e1 = a.emit("0", "run_started", {})
    e2 = b.emit("1", "x", {})
    e3 = a.emit("2", "y", {})
    assert [e1["seq"], e2["seq"], e3["seq"]] == [1, 2, 3]
    assert e2["prev_hash"] == e1["hash"]
    assert e3["prev_hash"] == e2["hash"]
    assert EventLog(tmp_path).verify_chain()["ok"]


def test_lock_file_is_a_sidecar_not_the_log_itself(tmp_path):
    """Locking events.ndjson directly would complicate offset/inode tracking."""
    log = EventLog(tmp_path)
    log.emit("0", "run_started", {})
    assert (tmp_path / ".sciforge" / "events.ndjson.lock").exists()
    # the log itself stays plain NDJSON, one object per line
    lines = (tmp_path / ".sciforge" / "events.ndjson").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["kind"] == "run_started"


def test_legacy_chainless_log_keeps_appending_without_chain_fields(tmp_path):
    """Backward compatibility: a pre-chain log must not gain a mixed suffix."""
    d = tmp_path / ".sciforge"
    d.mkdir(parents=True)
    (d / "events.ndjson").write_text(
        json.dumps({"seq": 1, "ts": 0, "phase": "0", "kind": "run_started",
                    "payload": {}}) + "\n")
    log = EventLog(tmp_path)
    ev = log.emit("1", "phase_done", {})
    assert "prev_hash" not in ev and "hash" not in ev
    assert log.verify_chain()["legacy"] is True
    assert log.verify_chain()["ok"] is True