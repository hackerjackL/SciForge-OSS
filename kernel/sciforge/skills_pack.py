"""Skill packaging with frozen revisions (S14).

Lesson from ScienceDiscovery's progressive disclosure, adapted to our CLI (no UI):
- A skill package is addressed by (skill_id, revision, package_hash) — the hash
  locks SKILL.md + references at run start, so mid-run disk edits cannot change
  what the model reads (anti drift + replayability).
- The prompt stays light: pointer paths + hash, never full content inlined
  (matches our own methodology-and-context-contract).
- A writable extensions area is reserved (self-evolution output goes THERE,
  never into the frozen tree) — the substrate for S15.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def package_hash(skill_dir: Path) -> str:
    """Deterministic hash over all .md files in a skill package (sorted order)."""
    h = hashlib.sha256()
    for p in sorted(skill_dir.rglob("*.md")):
        h.update(str(p.relative_to(skill_dir)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def stage(ws: Path, skill_paths: list[str]) -> dict:
    """Copy selected skill packages into the workspace's frozen snapshot.

    Returns manifest {skill_id: {revision, hash, path}}. Files staged 0444 (read-only).
    """
    snap = ws / ".sciforge" / "skills-snapshot"
    ext = ws / ".sciforge" / "skill-extensions"  # writable self-evolution area (S15)
    manifest: dict[str, dict] = {}
    for rel in skill_paths:
        src = (REPO_ROOT / rel)
        if not src.exists():
            continue
        skill_id = src.parent.name if src.name == "SKILL.md" else src.name
        dst_dir = snap / skill_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst_dir, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst_dir / src.name)
        digest = package_hash(dst_dir)
        manifest[skill_id] = {"revision": digest, "package_hash": digest,
                              "source": rel, "staged_at": time.time()}
        for f in dst_dir.rglob("*"):
            if f.is_file():
                os.chmod(f, 0o444)  # frozen tree is read-only at host level too
    ext.mkdir(parents=True, exist_ok=True)
    (snap / "MANIFEST.json").write_text(json.dumps({
        "schema_version": "1.0",
        "repo_revision": _repo_revision(),
        "skills": manifest}, indent=2))
    return manifest


def verify(ws: Path) -> dict:
    """Re-hash the staged tree against MANIFEST: any edit = integrity FAIL."""
    snap = ws / ".sciforge" / "skills-snapshot"
    mf = snap / "MANIFEST.json"
    if not mf.exists():
        return {"integrity": "NOT_STAGED"}
    man = json.loads(mf.read_text())
    bad = []
    for sid, info in man["skills"].items():
        d = snap / sid
        if not d.exists():
            bad.append((sid, "missing"))
            continue
        if package_hash(d) != info["package_hash"]:
            bad.append((sid, "hash_mismatch"))
    return {"integrity": "PASS" if not bad else "FAIL", "violations": bad}


def _repo_revision() -> str:
    try:
        return subprocess_rev()
    except Exception:
        return "unknown"


def subprocess_rev() -> str:
    import subprocess
    return subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
