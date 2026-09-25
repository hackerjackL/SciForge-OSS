"""Verified-reference cache (S24) — PaperQA2 lesson: cache what was verified.

universal-retrieval's 3-layer anti-hallucination verification (arXiv+CrossRef+S2)
is API-expensive and network-flaky (proxy-dependent). The cache stores
(lookup_key -> verification result) in SQLite with TTL, so:
  - a second run verifying the same DOI/arXiv-id costs 0 API calls,
  - a WARNed/failed verification is NOT cached positive (failure is cached only
    as "recently failed" to avoid hammering),
  - the cache is local to the machine (no privacy leak), keyed by normalized id.

Consumed by host skills via `sciforge-kernel cache lookup/put` CLI or import.
stdlib sqlite3 — no new deps.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / ".sciforge-cache" / "litcache.sqlite3"

TTL_OK = 30 * 86400        # verified references rarely change; 30 days
TTL_FAIL = 6 * 3600        # failed lookups: retry after 6h, not never


def _key(kind: str, ident: str) -> str:
    ident = (ident or "").strip().lower()
    ident = re.sub(r"^https?://(dx\.)?doi\.org/", "", ident)
    ident = re.sub(r"^arxiv:(\d{4}\.\d{4,5})", r"\1", ident)
    return f"{kind}:{ident}"


def _conn(db: Path):
    db.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db, timeout=30)
    c.execute("CREATE TABLE IF NOT EXISTS refs ("
              "k TEXT PRIMARY KEY, payload TEXT, status TEXT,"
              "hits INTEGER DEFAULT 1, updated REAL)")
    return c


def lookup(ident: str, kind: str = "auto", db: Path = DEFAULT_DB) -> dict | None:
    if kind == "auto":
        kind = ("arxiv" if re.match(r"^\d{4}\.\d{4,5}", ident) else
                "doi" if "/" in ident or ident.startswith("10.") else "title")
    k = _key(kind, ident)
    c = _conn(db)
    try:
        row = c.execute("SELECT payload,status,updated FROM refs WHERE k=?", (k,)).fetchone()
    finally:
        c.close()
    if not row:
        return None
    payload, status, updated = row
    ttl = TTL_OK if status == "verified" else TTL_FAIL
    if time.time() - updated > ttl:
        return None  # expired => re-verify
    return {"key": k, "status": status, "payload": json.loads(payload), "cached": True}


def put(ident: str, verified: bool, payload: dict, kind: str = "auto",
        db: Path = DEFAULT_DB) -> dict:
    if kind == "auto":
        kind = ("arxiv" if re.match(r"^\d{4}\.\d{4,5}", ident) else
                "doi" if "/" in ident or ident.startswith("10.") else "title")
    k = _key(kind, ident)
    c = _conn(db)
    try:
        c.execute("INSERT INTO refs(k,payload,status,updated) VALUES(?,?,?,?) "
                  "ON CONFLICT(k) DO UPDATE SET payload=excluded.payload,"
                  "status=excluded.status, updated=excluded.updated, hits=hits+1",
                  (k, json.dumps(payload, ensure_ascii=False),
                   "verified" if verified else "failed", time.time()))
        c.commit()
    finally:
        c.close()
    return {"key": k, "status": "verified" if verified else "failed"}


def stats(db: Path = DEFAULT_DB) -> dict:
    c = _conn(db)
    try:
        n_v = c.execute("SELECT count(*) FROM refs WHERE status='verified'").fetchone()[0]
        n_f = c.execute("SELECT count(*) FROM refs WHERE status='failed'").fetchone()[0]
        hits = c.execute("SELECT sum(hits) FROM refs").fetchone()[0] or 0
    finally:
        c.close()
    return {"verified": n_v, "failed": n_f, "total_lookups_served": int(hits), "db": str(db)}
