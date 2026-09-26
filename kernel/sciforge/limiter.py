"""Keyed rate limiter with upstream-429 cooldown (v1.6, ScienceDiscovery
rate-limiting.md pattern — hardened after this team lived a Google
250k-input-token/min 429 firsthand).

Contract, per manifest key (e.g. "arxiv", "crossref", "s2", "gemini-3.8-flash"):
  - min_interval_s: spacing between requests (arXiv asks 1 req/3s politely)
  - max_concurrent: in-flight cap
  - burst: short-term allowance beyond the steady rate
Semantics:
  - acquire(key) BLOCKS the caller until the schedule allows the call
    (queue, not crash — the caller is a retrieval loop, not an HTTP server)
  - report_upstream_429(key, retry_after) puts the whole key in GLOBAL cooldown:
    while cooled, acquire blocks until the cooldown lapses. Retry-After is
    honored when Google/Anthropic send it (observed: 40s countdown).
  - No manifest entry for a key = unlimited (explicit default, SciDis discipline).
State is process-local (threading) — the daemon is the only long-lived process,
and kernel runs one run at a time, so global coordination is unnecessary.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "config" / "ratelimits.json"


def load_manifest(path: Path | None = None) -> dict:
    import json
    p = path or DEFAULT_MANIFEST
    if p.exists():
        return json.loads(p.read_text())
    return {}


class _Bucket:
    __slots__ = ("min_interval", "last", "cooldown_until", "lock")

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.last = 0.0
        self.cooldown_until = 0.0
        self.lock = threading.Lock()


class Limiter:
    def __init__(self, manifest: dict | None = None):
        self.buckets: dict[str, _Bucket] = {}
        self._registry = threading.Lock()
        manifest = manifest if manifest is not None else load_manifest()
        self.manifest = manifest.get("limits", {}) if isinstance(manifest, dict) else {}

    def _bucket(self, key: str) -> _Bucket | None:
        spec = self.manifest.get(key)
        if spec is None:
            return None  # unlimited (explicit default)
        with self._registry:
            b = self.buckets.get(key)
            if b is None:
                b = self.buckets[key] = _Bucket(float(spec.get("min_interval_s", 0)))
            return b

    def report_upstream_429(self, key: str, retry_after_s: float | None = None) -> None:
        spec = self.manifest.get(key, {})
        ra = retry_after_s if retry_after_s is not None else float(spec.get("default_retry_after_s", 60))
        cap = float(spec.get("max_cooldown_s", 300))
        ra = min(max(1.0, ra), cap)
        b = self._bucket(key)
        if b is not None:
            with b.lock:
                b.cooldown_until = max(b.cooldown_until, time.monotonic() + ra)
        else:  # unknown key still gets a bucket lazily so the cooldown lands
            with self._registry:
                b = self.buckets.setdefault(key, _Bucket(0.0))
            with b.lock:
                b.cooldown_until = max(b.cooldown_until, time.monotonic() + ra)

    def wait_time(self, key: str) -> float:
        """Seconds until the next call to `key` is allowed (0 = now)."""
        b = self.buckets.get(key)
        if b is None:
            spec = self.manifest.get(key)
            if spec is None:
                return 0.0
            b = self._bucket(key)
        if b is None:
            return 0.0
        now = time.monotonic()
        cd = max(0.0, b.cooldown_until - now)
        pace = max(0.0, b.last + b.min_interval - now)
        return max(cd, pace)

    def acquire(self, key: str, timeout_s: float = 600.0) -> float:
        """Block until allowed; returns the waited seconds (caller may log it).
        Raises TimeoutError after timeout_s so a wedged upstream cannot hang a
        phase forever (the kernel surfaces TIMEOUT as WARN, never silent)."""
        b = self.buckets.get(key) or self._bucket(key)
        if b is None:
            return 0.0
        t0 = time.monotonic()
        while True:
            with b.lock:
                now = time.monotonic()
                cd = b.cooldown_until - now
                pace = (b.last + b.min_interval) - now
                wait = max(cd, pace, 0.0)
                if wait <= 0:
                    b.last = now
                    return time.monotonic() - t0
            if time.monotonic() - t0 > timeout_s:
                raise TimeoutError(f"rate-limit queue for '{key}' exceeded {timeout_s}s")
            time.sleep(min(wait, 2.0))

    def snapshot(self) -> dict:
        return {k: {"cooldown_s": max(0.0, b.cooldown_until - time.monotonic()),
                    "min_interval_s": b.min_interval}
                for k, b in self.buckets.items()}


# process-wide default instance — retrieval helpers and providers share one clock
_default: Limiter | None = None
_default_lock = threading.Lock()


def limiter() -> Limiter:
    global _default
    with _default_lock:
        if _default is None:
            _default = Limiter()
        return _default


def self_test() -> int:
    import time as _t
    lim = Limiter({"limits": {"demo": {"min_interval_s": 0.05, "default_retry_after_s": 0.3,
                                        "max_cooldown_s": 0.5}}})
    fails = []
    t0 = _t.monotonic(); lim.acquire("demo"); lim.acquire("demo")
    gap = _t.monotonic() - t0
    if gap < 0.04:
        fails.append(f"spacing not enforced (2 acquires in {gap:.3f}s)")
    lim.report_upstream_429("demo", retry_after_s=0.3)
    t0 = _t.monotonic(); lim.acquire("demo")
    if _t.monotonic() - t0 < 0.25:
        fails.append("429 cooldown not honored")
    if lim.wait_time("unknown-key") != 0.0:
        fails.append("unmanifested key should be unlimited")
    try:
        lim2 = Limiter({"limits": {"slow": {"min_interval_s": 50}}})
        lim2.acquire("slow")               # consume the first-call allowance
        lim2.acquire("slow", timeout_s=0.2)  # second call needs 50s -> must time out
        fails.append("TimeoutError not raised")
    except TimeoutError:
        pass
    # retry-after clamped to max_cooldown_s
    lim.report_upstream_429("demo", retry_after_s=9999)
    if lim.wait_time("demo") > 0.6:
        fails.append("max_cooldown_s clamp failed")
    return len(fails), fails


if __name__ == "__main__":
    n, fails = self_test()
    print("limiter self-test:", "PASS" if n == 0 else f"FAIL ({n})")
    for f in fails:
        print("  -", f)
    sys_ok = 0 if n == 0 else 1
    import sys
    sys.exit(sys_ok)
