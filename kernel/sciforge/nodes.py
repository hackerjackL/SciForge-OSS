"""Node registry + fork protocol (v1.7.2, adapted from XScientist ARA, Apache-2.0).

XScientist's core insight we port: a research run is a **forkable artifact**,
not a PDF. Every experiment node is content-addressed (code/inputs/outputs
sha256) with a re-execution hook, and manuscript claims anchor to node ids —
so a later agent resumes from a node instead of cold-starting, and a claim
can always be traced to the exact bytes that produced it.

Our adaptation (stdlib-only, kernel-owned):

- `.sciforge/nodes/NODES.json` — append-style registry:
    {id, kind, phase, code_sha, inputs_sha, outputs_sha, reexec_cmd,
     claim_ids, parent, status, ts}
  written by the experiment boundaries (6b/6c), ablation, rebuttal runs.
- `sciforge fork --node <id>` — new workspace seeded from a node's artifacts
  + its reexec hook; RUNSTATE starts at the node's phase (no cold start).
- claim anchors: `.sciforge/nodes/CLAIM_ANCHORS.json` — per claim
  {claim_id, node_id, tex_file, line, resolved, evidence_refs:[sha256:...]}
  (field set ported from XScientist ara.v1 claim.schema.json).
- failed branches are FIRST-CLASS nodes (status=failed) — never filtered,
  per the exploration-graph rule; the sota driver and memory consume them.

Design credit: protocol shape adapted from smileformylove/XScientist
(Apache-2.0); implementation here is original SciForge code.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

REGISTRY_REL = Path(".sciforge") / "nodes" / "NODES.json"
ANCHORS_REL = Path(".sciforge") / "nodes" / "CLAIM_ANCHORS.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha_dir_or_file(p: Path) -> str:
    if p.is_file():
        return sha256_file(p)
    if p.is_dir():
        h = hashlib.sha256()
        for f in sorted(p.rglob("*")):
            if f.is_file():
                h.update(str(f.relative_to(p)).encode())
                h.update(sha256_file(f).encode())
        return h.hexdigest()
    return ""


def load(ws: Path) -> dict:
    p = Path(ws) / REGISTRY_REL
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"schema_version": "1.0", "nodes": []}


def save(ws: Path, doc: dict) -> Path:
    p = Path(ws) / REGISTRY_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return p


def record_node(ws: Path, *, kind: str, phase: str, code: Path | list[Path],
                inputs: list[Path], outputs: list[Path], reexec_cmd: str,
                claim_ids: list[str] | None = None, parent: str | None = None,
                status: str = "pass") -> dict:
    """Register one experiment node with content hashes + reexec hook."""
    doc = load(ws)
    code_paths = code if isinstance(code, list) else [code]
    node = {
        "id": f"n{len(doc['nodes']) + 1:03d}",
        "kind": kind, "phase": phase, "status": status,
        "code_sha": {str(Path(c).name): _sha_dir_or_file(Path(c)) for c in code_paths},
        "inputs_sha": {str(Path(i).relative_to(ws)): _sha_dir_or_file(Path(i))
                       for i in inputs if Path(i).exists()},
        "outputs_sha": {str(Path(o).relative_to(ws)): _sha_dir_or_file(Path(o))
                        for o in outputs if Path(o).exists()},
        "reexec_cmd": reexec_cmd,
        "claim_ids": claim_ids or [],
        "parent": parent, "ts": time.time(),
    }
    doc["nodes"].append(node)
    save(ws, doc)
    return node


def auto_register(ws: Path, phase: str = "6c") -> list[dict]:
    """Production node registration (v1.7.2 adversarial-review fix): the
    kernel records a node for every experiment RESULT.json at the experiment
    boundaries — without this the registry stayed empty and
    claim_anchor_gate was structurally dead (always SKIP).
    """
    ws = Path(ws)
    exp = ws / "experiments"
    if not exp.is_dir():
        return []
    doc = load(ws)
    existing = {rel for n in doc["nodes"]
                for rel in (n.get("outputs_sha") or {})}
    registered = []
    for result in sorted(exp.rglob("RESULT.json")):
        rel = str(result.relative_to(ws))
        if rel in existing:
            continue
        group = result.parent
        code = [ws / "src"] if (ws / "src").is_dir() else []
        node = record_node(
            ws, kind=group.parent.name or "experiment", phase=phase,
            code=code or [result],
            inputs=[group],
            outputs=[result] + [p for p in sorted(group.glob("*.json"))
                                if p != result],
            reexec_cmd=f"cd {group.relative_to(ws)} && run (see DISPATCH.json)",
            status="pass" if '"status": "PASS"' in result.read_text(
                errors="replace") or '"status":"PASS"' in result.read_text(
                errors="replace") else "unknown")
        registered.append(node)
    return registered


def auto_anchor_claims(ws: Path) -> list[dict]:
    """Best-effort claim→node anchors (v1.7.2): map each polarity-positive
    claim to the node whose outputs the claim text actually cites; a claim
    citing no registered artifact stays unresolved (and the gate blocks the
    wrap-up if the paper cites it). Hosts may overwrite with exact anchors.
    """
    ws = Path(ws)
    claims_md = ws / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md"
    if not claims_md.exists():
        return []
    doc = load(ws)
    nodes_list = doc["nodes"]
    if not nodes_list:
        return []
    anchors = []
    blocks = re.split(r"(?m)^## ", claims_md.read_text(errors="replace"))[1:]
    for blk in blocks:
        head = blk.splitlines()[0] if blk else ""
        m = re.match(r"(C\d+)", head.strip())
        if not m or "polarity positive" not in head:
            continue
        body = blk
        node_id, resolved = "", False
        for n in nodes_list:
            for rel in (n.get("outputs_sha") or {}):
                if rel in body or Path(rel).name in body:
                    node_id, resolved = n["id"], True
                    break
            if resolved:
                break
        anchors.append({"claim_id": m.group(1), "node_id": node_id,
                        "tex_file": "paper/main.tex", "line": 0,
                        "resolved": resolved, "evidence_refs": [],
                        "context": body.splitlines()[0][:120] if body else ""})
    anchor_claims(ws, anchors)
    return anchors


def anchor_claims(ws: Path, anchors: list[dict]) -> Path:
    """Write claim→node anchors (XScientist ara.v1 claim field set)."""
    p = Path(ws) / ANCHORS_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema_version": "1.0", "claims": anchors},
                            indent=2, ensure_ascii=False))
    return p


def load_anchors(ws: Path) -> list[dict]:
    try:
        return json.loads((Path(ws) / ANCHORS_REL).read_text()).get("claims", [])
    except Exception:
        return []


def verify_anchors(ws: Path) -> list[str]:
    """Every resolved claim anchor must point at an existing node whose
    outputs still hash-match (a drifted result invalidates the anchor)."""
    problems = []
    nodes = {n["id"]: n for n in load(ws)["nodes"]}
    for a in load_anchors(ws):
        n = nodes.get(a.get("node_id"))
        if n is None:
            problems.append(f"claim {a.get('claim_id')}: node "
                            f"{a.get('node_id')} not in registry")
            continue
        for rel, sha in (n.get("outputs_sha") or {}).items():
            f = Path(ws) / rel
            if f.exists() and _sha_dir_or_file(f) != sha:
                problems.append(f"claim {a.get('claim_id')}: output {rel} "
                                f"drifted from node hash (result changed after "
                                f"the claim was anchored)")
        if a.get("resolved") is not True:
            problems.append(f"claim {a.get('claim_id')}: unresolved anchor")
    return problems


def fork(ws: Path, node_id: str, out: Path) -> dict:
    """Seed a NEW workspace from one node: copy its code+outputs+inputs,
    write a RUNSTATE at the node's phase, and record the fork provenance.
    The new run re-executes via the node's reexec hook — never cold-starts."""
    doc = load(ws)
    node = next((n for n in doc["nodes"] if n["id"] == node_id), None)
    if node is None:
        return {"ok": False, "error": f"node {node_id} not found"}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    copied = []
    for group in ("inputs_sha", "outputs_sha"):
        for rel in (node.get(group) or {}):
            src = Path(ws) / rel
            dst = out / rel
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    import shutil
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    import shutil
                    shutil.copy2(src, dst)
                copied.append(rel)
    for rel in (node.get("code_sha") or {}):
        src = Path(ws) / rel
        if not src.exists():
            src = Path(ws) / "src" / rel
        dst = out / "src" / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(src, dst)
            copied.append(f"src/{rel}")
    (out / ".sciforge").mkdir(parents=True, exist_ok=True)
    (out / ".sciforge" / "RUNSTATE.json").write_text(json.dumps({
        "schema_version": "2.0", "status": "running",
        "current_phase": node.get("phase", "6b"),
        "data": {"forked_from": {"workspace": str(ws), "node": node_id,
                                 "reexec_cmd": node.get("reexec_cmd"),
                                 "outputs_sha": node.get("outputs_sha")}},
    }, indent=2))
    (out / ".sciforge" / "nodes").mkdir(parents=True, exist_ok=True)
    (out / ".sciforge" / "nodes" / "NODES.json").write_text(json.dumps(
        {"schema_version": "1.0", "nodes": [node]}, indent=2))
    return {"ok": True, "out": str(out), "copied": copied,
            "reexec_cmd": node.get("reexec_cmd"),
            "resume_phase": node.get("phase")}
