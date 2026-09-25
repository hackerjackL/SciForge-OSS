"""Proxy auto-discovery for literature retrieval (S24).

The old contract hardcoded http://127.0.0.1:8099 (mihomo). Reality: Clash for
Windows/macOS/Verge use 7890/7897/7891...; env vars may already be set. The
kernel discovers a working proxy by probing candidate endpoints against a real
API target, and universal-retrieval consumes the result instead of a magic port.

Probes: try GET https://api.crossref.org/ (fast, no key) — direct, then each
proxy candidate. First success wins. Results cached per process.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

CANDIDATE_PORTS = (7890, 7897, 7891, 1087, 8099, 8118, 8888)
TEST_URLS = ("https://api.crossref.org/", "https://api.semanticscholar.org/graph/v1/papers/search?q=x&limit=1")


def _ok_via(proxies: dict | None, url: str = TEST_URLS[0], timeout: int = 10) -> bool:
    try:
        if proxies:
            # urllib needs explicit ProxyHandler or *_proxy env respected by default opener
            req = urllib.request.Request(url, method="GET", headers={"user-agent": "sciforge-kernel"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
            with opener.open(req, timeout=timeout) as r:
                return r.status < 500
        req = urllib.request.Request(url, headers={"user-agent": "sciforge-kernel"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — fixed https targets
            return r.status < 500
    except Exception:
        return False


def discover(write_to: Path | None = None) -> dict:
    """Returns {"proxy": url|None, "direct_ok": bool, "tested": [...]}."""
    env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or os.environ.get("ALL_PROXY")
    tested = []
    if _ok_via(None):
        result = {"proxy": None, "direct_ok": True, "tested": ["direct"],
                  "env_proxy_present": bool(env_proxy)}
    else:
        result = {"proxy": None, "direct_ok": False, "tested": ["direct"]}
        candidates = ([env_proxy] if env_proxy else []) + [f"http://127.0.0.1:{p}" for p in CANDIDATE_PORTS]
        for c in candidates:
            if not c:
                continue
            pr = {"http": c, "https": c}
            tested.append(c)
            if _ok_via(pr):
                result = {"proxy": c, "direct_ok": False, "tested": tested}
                break
    if write_to:
        write_to.parent.mkdir(parents=True, exist_ok=True)
        write_to.write_text(json.dumps(result, indent=2))
    return result


def export_env(result: dict) -> dict:
    """env dict for subprocess dispatch (universal-retrieval scripts honor these)."""
    if result.get("proxy"):
        return {"HTTP_PROXY": result["proxy"], "HTTPS_PROXY": result["proxy"],
                "http_proxy": result["proxy"], "https_proxy": result["proxy"]}
    return {}
