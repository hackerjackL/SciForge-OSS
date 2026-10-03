"""Multi-source scheduling for the daemon (v1.7.2, D6).

The daemon used to accept only hand-POSTed problems. Real research operations
feed from several streams: a bench topic list (ARC-Bench style), an inbox
directory a human or another system drops briefings into, and (planned)
remote queues. A source registry makes each stream a first-class, auditable
producer:

  .sciforge/SOURCES.json (archive-level):
    [{"id": "arc-ml", "kind": "jsonl", "path": ".../topics.jsonl",
      "fields": {"problem": "topic", "id": "id"}, "poll_s": 3600,
      "seen": [ids already enqueued]}]

Kinds: jsonl (one problem object per line), inbox (each *.md file = one
briefing; consumed = moved to inbox/done/), manual (no polling).
The daemon polls each source on its interval and enqueues unseen problems —
dedup by source id + problem id, so a restart never double-queues.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

REGISTRY_REL = Path("SOURCES.json")


def load_registry(archive: Path) -> list[dict]:
    try:
        return json.loads((Path(archive) / REGISTRY_REL).read_text())
    except Exception:
        return []


def save_registry(archive: Path, sources: list[dict]) -> Path:
    p = Path(archive) / REGISTRY_REL
    p.write_text(json.dumps(sources, indent=2, ensure_ascii=False))
    return p


def poll_source(src: dict) -> list[dict]:
    """Unseen problems from one source: [{id, problem, source_id}]."""
    seen = set(src.get("seen", []))
    fields = src.get("fields", {"problem": "problem", "id": "id"})
    out = []
    kind, path = src.get("kind", "manual"), Path(src.get("path", ""))
    if kind == "jsonl" and path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = str(d.get(fields.get("id", "id"), ""))
            prob = d.get(fields.get("problem", "problem"), "")
            if pid and prob and pid not in seen:
                out.append({"id": pid, "problem": prob,
                            "source_id": src.get("id")})
    elif kind == "inbox" and path.is_dir():
        for f in sorted(path.glob("*.md")):
            pid = f.stem
            if pid in seen:
                continue
            out.append({"id": pid, "problem": f.read_text(errors="replace")[:4000],
                        "source_id": src.get("id"), "_consume": str(f)})
    return out


def mark_seen(src: dict, ids: list[str], consumed_paths: list[str]) -> dict:
    src.setdefault("seen", [])
    src["seen"] = sorted(set(src["seen"]) | set(ids))
    for cp in consumed_paths:
        p = Path(cp)
        if p.exists():
            done = p.parent / "done"
            done.mkdir(exist_ok=True)
            shutil.move(str(p), str(done / p.name))
    src["last_poll"] = time.time()
    return src


def poll_all(archive: Path) -> tuple[list[dict], list[dict]]:
    """-> (new problems to enqueue, updated registry)."""
    sources = load_registry(archive)
    new, updated = [], []
    for src in sources:
        if src.get("kind") == "manual":
            updated.append(src)
            continue
        due = time.time() - src.get("last_poll", 0) >= src.get("poll_s", 3600)
        if not due:
            updated.append(src)
            continue
        items = poll_source(src)
        consumed = [i.pop("_consume") for i in items if "_consume" in i]
        if items:
            new += items
            mark_seen(src, [i["id"] for i in items], consumed)
        else:
            src["last_poll"] = time.time()
        updated.append(src)
    save_registry(archive, updated)
    return new, updated
