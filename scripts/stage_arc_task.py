#!/usr/bin/env python3
"""Stage ARC-Bench tasks into run workspaces for the v1.8.0 evaluation loop.

Why this exists: an evaluation agent that has to fetch and parse the benchmark
itself spends its budget on plumbing and can silently grade against a different
task than the one it ran. Staging the official task + rubric on disk first makes
the题面 immutable for the run and lets the scorer read weights from the rubric
rather than from the assessor.

Task data comes from the HuggingFace dataset AIMING-Lab-UNC/ARC-Bench (MIT,
55 topics x 5 domains), already downloaded to /tmp/arc/<domain>.jsonl.

Usage:
  python scripts/stage_arc_task.py <TASK_ID> [<TASK_ID> ...]
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = Path("/tmp/arc")


def load_task(task_id: str) -> dict:
    domain = {"B": "biology", "M": "ml", "P": "physics",
              "Q": "quantum", "S": "statistics"}[task_id[0]]
    src = DATA / f"{domain}.jsonl"
    if not src.is_file():
        raise SystemExit(f"no downloaded data for {domain} at {src} "
                         f"(fetch it from HF first)")
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == task_id:
            return row
    raise SystemExit(f"{task_id} not found in {src}")


def rubric_of(task: dict) -> dict:
    """The rubric ships as a JSON string inside the task row."""
    raw = task.get("rubric")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        return json.loads(raw)
    raise SystemExit(f"{task['id']} carries no rubric payload")


def problem_md(task: dict) -> str:
    """A PROBLEM.md that freezes the Q-id and quotes the hypotheses verbatim.

    INV-G1 requires every artifact to reference a frozen problem anchor, so the
    anchor has to exist on disk before the run starts -- not be reconstructed
    later from memory.
    """
    hyps = task.get("hypotheses")
    if isinstance(hyps, str):
        try:
            hyps = json.loads(hyps)
        except ValueError:
            hyps = None
    lines = [
        f"# {task['id']} — {task['title']}",
        "",
        f"**Q-id (frozen at Phase 0, INV-G1):** `{task['id']}`",
        "",
        f"**Domain:** {task.get('domain')}  |  **Metric:** "
        f"`{task.get('metric_key')}` ({task.get('metric_direction')})  |  "
        f"**Est. wall clock:** {task.get('est_wall_clock_sec')}s  |  "
        f"**GPU required:** {task.get('gpu_required')}",
        "",
        "Source: ARC-Bench, task "
        f"`{task['id']}` (`results/benchmark/ARC_TASK.json`).",
        "",
        "## Research question (verbatim from the task)",
        "",
        f"> {(task.get('synthesis') or '').strip()}",
        "",
        "## Hypotheses (frozen at Phase 0)",
        "",
    ]
    if isinstance(hyps, list):
        for i, h in enumerate(hyps, 1):
            if isinstance(h, dict):
                text = h.get("hypothesis") or h.get("text") or h.get("statement")
                if text:
                    lines.append(f"- **H{i}** — {str(text).strip()}")
            elif isinstance(h, str):
                lines.append(f"- **H{i}** — {h.strip()}")
    elif isinstance(hyps, dict):
        for k in sorted(hyps):
            v = hyps[k]
            text = v.get("hypothesis") if isinstance(v, dict) else v
            lines.append(f"- **{k}** — {str(text).strip()}")
    lines += [
        "",
        "## Scope determination",
        "",
        "Every quantity in this task is computed from the task's own specification "
        "and public references; no wet-lab manipulation, culture, or assay is "
        "performed or claimed. Where a published figure cannot be reproduced with "
        "the software available on this machine, that limitation is recorded as a "
        "regime statement in the Limitations section — it is never papered over "
        "with a surrogate presented as the published result.",
        "",
    ]
    return "\n".join(lines)


def stage(task_id: str) -> Path:
    task = load_task(task_id)
    run = REPO / "runs" / task_id
    bench = run / "results" / "benchmark"
    if run.exists() and (bench / "ARC_TASK.json").is_file():
        print(f"{task_id}: already staged at {run} (left untouched)")
        return run
    bench.mkdir(parents=True, exist_ok=True)
    (bench / "ARC_TASK.json").write_text(
        json.dumps(task, indent=2, ensure_ascii=False) + "\n")
    (bench / "ARC_RUBRIC.json").write_text(
        json.dumps(rubric_of(task), indent=2, ensure_ascii=False) + "\n")
    if not (run / "PROBLEM.md").is_file():
        (run / "PROBLEM.md").write_text(problem_md(task))
    print(f"{task_id}: staged {task.get('domain')} task, "
          f"{task.get('rubric_num_leaves')} rubric leaves, "
          f"est {task.get('est_wall_clock_sec')}s -> {run}")
    return run


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    for tid in argv:
        stage(tid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
