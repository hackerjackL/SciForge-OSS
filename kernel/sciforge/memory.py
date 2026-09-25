"""Experience replay with vector search (S18) — stdlib embeddings, no torch.

LESSONS.json per run (contract existing since v1.4.0) now becomes QUERYABLE:
- embed: hashing-trick bag-of-words → L2-normalized dense vector (deterministic,
  stdlib, model-agnostic; if sentence-transformers is installed the kernel uses
  it automatically for real embeddings).
- index: cross-run archive directory → JSONL of {text, vec, meta, run_id}.
- query: top-k cosine — Phase 2 ideation priors and Phase 6b `avoid` exclusions
  consume real retrievable lessons, not "remember to read LESSONS.json".
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _hash_vec(text: str) -> list[float]:
    """Deterministic hashing-trick embedding (md5-based; stable across processes)."""
    v = [0.0] * DIM
    toks = _TOKEN.findall(text.lower())
    for t in toks:
        h = int(hashlib.md5(t.encode()).hexdigest()[:4], 16) % DIM
        v[h] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


_ST_MODEL = None


def embed(text: str) -> list[float]:
    global _ST_MODEL
    if _ST_MODEL is False:
        return _hash_vec(text)
    if _ST_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer  # optional upgrade
            _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _ST_MODEL = False
            return _hash_vec(text)
    emb = _ST_MODEL.encode(text).tolist()
    n = math.sqrt(sum(x * x for x in emb)) or 1.0
    return [x / n for x in emb]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def build_index(archive_dir: Path, out: Path) -> int:
    """Scan sibling runs' LESSONS.json; one entry per lesson with embedding."""
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w") as f:
        for run in sorted(Path(archive_dir).iterdir()):
            for cand in (run / "output" / "LESSONS.json", run / ".sciforge" / "verdicts" / "LESSONS.json"):
                if not cand.exists():
                    continue
                try:
                    d = json.loads(cand.read_text())
                except Exception:
                    continue
                for bucket in ("failed_experiments", "idea_rollbacks", "code_errors", "lessons", "what_worked"):
                    for item in d.get(bucket, []):
                        text = json.dumps(item, ensure_ascii=False) if not isinstance(item, str) else item
                        if not text.strip():
                            continue
                        f.write(json.dumps({"text": text[:800], "vec": embed(text),
                                            "bucket": bucket, "run_id": d.get("run_id", run.name)}) + "\n")
                        n += 1
    return n


def query(index: Path, text: str, k: int = 8, min_sim: float = 0.3) -> list[dict]:
    if not Path(index).exists():
        return []
    q = embed(text)
    scored = []
    with open(index) as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            s = cosine(q, e["vec"])
            if s >= min_sim:
                scored.append({**e, "sim": round(s, 3), "vec": None})
    scored.sort(key=lambda x: -x["sim"])
    return scored[:k]
