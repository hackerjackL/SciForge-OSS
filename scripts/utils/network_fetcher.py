#!/usr/bin/env python3
"""SciForge-OSS network_fetcher — autonomous network bootstrap + resilient downloader.

Zero paid-API dependency. Detects connectivity to HuggingFace / ModelScope / GitHub /
CrossRef / arXiv; when direct access fails (timeout / connection error), it
automatically starts or discovers the local `mihomo` proxy and retries through it.
Used by dataset acquisition (HLE / PaperBench / NatureBench) and citation
verification.

Usage (CLI):
    python3 scripts/utils/network_fetcher.py check [url...]
    python3 scripts/utils/network_fetcher.py fetch <url> <out_path> [--timeout 60]

Usage (module):
    from utils.network_fetcher import get_session, fetch, connectivity_report
"""
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

DEFAULT_PROXY_PORT = 8099           # mihomo mixed-port in this environment
PROXY_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")
MIHOMO_PATHS = ("/usr/local/bin/mihomo", "/usr/bin/mihomo", "/opt/mihomo/mihomo")
MIHOMO_CONFIG_DIRS = ("/root/.config/mihomo", "/etc/mihomo")


def _log(msg: str) -> None:
    sys.stderr.write(f"[network_fetcher] {msg}\n")


def mihomo_running() -> bool:
    """True if a mihomo (or clash-family) process is alive."""
    try:
        subprocess.run(["pgrep", "-x", "mihomo"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _find_mihomo_bin() -> str | None:
    for p in MIHOMO_PATHS:
        if os.path.exists(p):
            return p
    return None


def _find_mihomo_config() -> str | None:
    for d in MIHOMO_CONFIG_DIRS:
        if os.path.exists(os.path.join(d, "config.yaml")):
            return d
    return None


def start_mihomo() -> bool:
    """Start mihomo in background (setsid) if the binary + config exist."""
    if mihomo_running():
        return True
    bin_path = _find_mihomo_bin()
    cfg_dir = _find_mihomo_config()
    if not bin_path or not cfg_dir:
        _log("mihomo binary/config not found — cannot self-bootstrap")
        return False
    try:
        log_path = os.path.join(cfg_dir, "mihomo.log")
        with open(log_path, "a") as lf:
            subprocess.Popen(
                [bin_path, "-d", cfg_dir],
                stdout=lf, stderr=lf, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        # wait up to ~6s for the proxy port to open
        for _ in range(12):
            if _probe(f"http://127.0.0.1:{DEFAULT_PROXY_PORT}"):
                _log(f"mihomo started, proxy ready on 127.0.0.1:{DEFAULT_PROXY_PORT}")
                return True
            time.sleep(0.5)
        _log("mihomo process launched but proxy port not ready yet")
        return False
    except Exception as e:  # pragma: no cover
        _log(f"failed to start mihomo: {e}")
        return False


def _probe(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


def proxy_url() -> str | None:
    """Return a usable proxy URL: env first, else the default mihomo port."""
    for k in PROXY_ENV_KEYS:
        v = os.environ.get(k)
        if v:
            return v
    return f"http://127.0.0.1:{DEFAULT_PROXY_PORT}"


def get_session(direct_first: bool = True):
    """Return (opener, used_proxy) — an opener that transparently falls back to proxy."""
    if direct_first:
        try:
            return urllib.request.build_opener(), None
        except Exception:
            pass
    # build opener with proxy handler
    p = proxy_url()
    if p:
        ph = urllib.request.ProxyHandler({
            "http": p, "https": p,
        })
        return urllib.request.build_opener(ph), p
    return urllib.request.build_opener(), None


def fetch(url: str, out_path: str, timeout: float = 60.0,
          max_retries: int = 3, use_proxy_fallback: bool = True) -> bool:
    """Download `url` to `out_path` with autonomous proxy fallback.

    Order: direct → (start mihomo if needed) → proxy → retry.
    Returns True on success.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        opener, _ = get_session(direct_first=(attempts == 1))
        try:
            with opener.open(url, timeout=timeout) as r, open(out_path, "wb") as f:
                f.write(r.read())
            _log(f"downloaded {url} -> {out_path} ({os.path.getsize(out_path)} bytes)")
            return True
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            _log(f"attempt {attempts} failed for {url}: {e}")
            if use_proxy_fallback and not mihomo_running():
                _log("direct failed — attempting mihomo self-bootstrap")
                start_mihomo()
                time.sleep(1.0)
    return False


def connectivity_report(urls: list[str] | None = None) -> dict:
    """Check each URL direct vs proxy; return per-URL {direct, proxy, ok}."""
    urls = urls or [
        "https://huggingface.co",
        "https://www.modelscope.cn",
        "https://github.com",
        "https://api.crossref.org",
        "https://export.arxiv.org",
    ]
    report = {"mihomo_running": mihomo_running(), "proxy": proxy_url(), "urls": {}}
    for u in urls:
        d = _probe(u)
        p = _probe(u) if d else False
        if not p and proxy_url():
            try:
                opener, _ = get_session(direct_first=False)
                with opener.open(u, timeout=5):
                    p = True
            except Exception:
                p = False
        report["urls"][u] = {"direct": d, "proxy": p, "ok": d or p}
    return report


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "check":
        rep = connectivity_report(argv[2:] or None)
        import json
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0 if all(v["ok"] for v in rep["urls"].values()) else 1
    if len(argv) >= 4 and argv[1] == "fetch":
        return 0 if fetch(argv[2], argv[3]) else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
