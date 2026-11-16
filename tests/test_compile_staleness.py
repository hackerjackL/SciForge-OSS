"""Tests for the compiled-PDF staleness check in scripts/gate_all.py.

Why this exists: `compile_audit` used to read PAPER_COMPILE.json's self-reported
warning count and pass. That certifies the compile the verdict *describes*, not
the manuscript currently on disk. A real ARC-Bench run (ML04) regenerated its
experiments at 20:23 and its LaTeX tables at 20:25 but never recompiled after
20:15, so its shipped PDF reported an H1 gap of 0.0273 while results.json said
0.031833 -- and PAPER_COMPILE.json still read `warnings: 0, verdict: PASS`.
Nothing in the battery noticed, because no gate compared the PDF against the
artifacts it certifies.

The check is FAIL, not WARN: a PDF that contradicts results.json is an integrity
failure, and WARN is how the contradiction shipped in the first place. The
false-positive surface (a non-preserving `cp -r` resets every mtime) is bounded
by the returned paths, which name exactly what to recompile.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import gate_all  # noqa: E402


class _Opts:
    timeout = 60


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "Q001"
    (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    return ws


def _pdf(ws: Path, date: str) -> Path:
    """A byte-level stand-in for main.pdf carrying one /CreationDate.

    The gate reads the embedded date from raw bytes precisely so it survives a
    file copy, so a synthetic document with the real PDF date string is enough
    to exercise the parser -- no LaTeX toolchain required.
    """
    p = ws / "paper"
    p.mkdir(parents=True, exist_ok=True)
    body = (b"%PDF-1.5\n"
            b"<< /Type /Catalog >>\n"
            + f"/CreationDate (D:{date})".encode()
            + b"\n%%EOF\n")
    (p / "main.pdf").write_bytes(body)
    return p / "main.pdf"


def _compile_verdict(ws: Path, warnings: int = 0) -> None:
    (ws / ".sciforge" / "verdicts" / "PAPER_COMPILE.json").write_text(json.dumps({
        "verdict": "PASS", "zero_warnings": warnings == 0, "zero_errors": True,
        "warnings": warnings, "pages": 12, "pdf_path": "paper/main.pdf",
        "generated_at": "2026-11-16T12:18:56Z",
    }), encoding="utf-8")


def _run(ws: Path) -> dict:
    return gate_all.gate_compile_audit(ws, _Opts())


# ---------------------------------------------------------------------------
# date parsing
# ---------------------------------------------------------------------------

def test_pdf_creation_date_offset_is_applied(tmp_path):
    """A PDF stamped 20:15:21+08:00 is 12:15:21Z, not 20:15:21Z.

    Getting the offset backwards would make every non-UTC machine's PDF look
    eight hours stale (or fresh), i.e. the check would be wrong everywhere
    except UTC.
    """
    ws = _ws(tmp_path)
    pdf = _pdf(ws, "20261116201521+08'00'")
    ts = gate_all._pdf_creation_ts(pdf)
    got = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
    assert got.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-16 12:15:21", got


def test_pdf_creation_date_negative_offset(tmp_path):
    ws = _ws(tmp_path)
    pdf = _pdf(ws, "20261116071521-05'00'")
    got = datetime.datetime.fromtimestamp(
        gate_all._pdf_creation_ts(pdf), datetime.timezone.utc)
    assert got.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-16 12:15:21", got


def test_pdf_creation_date_missing_returns_none(tmp_path):
    ws = _ws(tmp_path)
    p = ws / "paper"
    p.mkdir(parents=True)
    (p / "main.pdf").write_bytes(b"%PDF-1.5\nno date here\n%%EOF\n")
    assert gate_all._pdf_creation_ts(p / "main.pdf") is None


# ---------------------------------------------------------------------------
# the gate itself
# ---------------------------------------------------------------------------

def test_pdf_older_than_results_fails(tmp_path):
    """The measured ML04 shape: sources regenerated after the last compile."""
    ws = _ws(tmp_path)
    _pdf(ws, "20261116121521+00'00'")          # compiled 12:15:21Z
    _compile_verdict(ws)
    # results written 9 minutes later, as in the real run
    res = ws / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "results.json").write_text("{}", encoding="utf-8")
    later = time.time() + 600
    os.utime(res / "results.json", (later, later))

    r = _run(ws)
    assert r["status"] == "FAIL"
    assert r["reason_code"] == "compiled_pdf_stale"
    # the detail must name the offender, not just count it
    assert "results/results.json" in r["detail"]
    assert "recompile" in r["detail"]


def test_pdf_newer_than_all_sources_passes(tmp_path):
    """Negative case: a workspace compiled after its last regeneration."""
    ws = _ws(tmp_path)
    _pdf(ws, "20990101000000+00'00'")          # far future => newest
    _compile_verdict(ws)
    res = ws / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "results.json").write_text("{}", encoding="utf-8")
    exp = ws / "experiments" / "full" / "group_main"
    exp.mkdir(parents=True)
    (exp / "RESULT.json").write_text("{}", encoding="utf-8")

    r = _run(ws)
    assert r["status"] == "PASS", r
    assert r["reason_code"] == "ok"
    assert "postdates" in r["detail"]


def test_missing_pdf_skips_not_fails(tmp_path):
    """Absence is already a hard failure in submission_ready at 15.5.

    Failing it here as well duplicates that verdict -- and the shipped e2e
    fixture (a PASS PAPER_COMPILE.json with no main.pdf) proved it: this leg
    added a second FAIL where one already existed. Nothing to compare
    freshness against, so SKIP.
    """
    ws = _ws(tmp_path)
    _compile_verdict(ws)
    r = _run(ws)
    assert r["status"] == "SKIP"
    assert r["reason_code"] == "compiled_pdf_absent"
    assert "submission_ready" in r["detail"]


def test_unparseable_pdf_date_warns_not_fails(tmp_path):
    """No /CreationDate => we cannot check; that is a disclosure, not a pass
    and not a spurious failure."""
    ws = _ws(tmp_path)
    _pdf(ws, "not-a-date")
    _compile_verdict(ws)
    r = _run(ws)
    assert r["status"] == "WARN"
    assert r["reason_code"] == "pdf_creation_date_unreadable"


def test_post_phase13_artifacts_do_not_count_as_stale(tmp_path):
    """.sciforge/, logs/, .smoke-out/, results/benchmark/ and __pycache__ are
    written after phase 13 by design. Counting them would fail every healthy
    run -- and results/benchmark/ is written by the *evaluator* (task spec,
    rubric, assessment), which necessarily postdates the manuscript."""
    ws = _ws(tmp_path)
    _pdf(ws, "20990101000000+00'00'")
    _compile_verdict(ws)
    future = time.time() + 600
    for rel in (".sciforge/verdicts/FAIRNESS.json",
                "logs/run.log",
                ".smoke-out/group_main/RESULT.json",
                "experiments/full/__pycache__/run_group.cpython-314.pyc",
                "results/benchmark/ASSESSMENT.json",
                "results/benchmark/ARC_RUBRIC.json"):
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        os.utime(p, (future, future))
    r = _run(ws)
    assert r["status"] == "PASS", r


def test_strict_warning_failure_takes_precedence(tmp_path):
    """A stale PDF must not mask a zero-warning violation, and vice versa."""
    ws = _ws(tmp_path)
    _pdf(ws, "20260101000000+00'00'")          # ancient => stale too
    _compile_verdict(ws, warnings=3)
    r = _run(ws)
    assert r["status"] == "FAIL"
    assert r["reason_code"] == "compile_warnings_strict"


def test_only_compile_audit_reports_the_reason(tmp_path, capsys):
    ws = _ws(tmp_path)
    _pdf(ws, "20261116121521+00'00'")
    _compile_verdict(ws)
    res = ws / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "results.json").write_text("{}", encoding="utf-8")
    later = time.time() + 600
    os.utime(res / "results.json", (later, later))

    rc = gate_all.main([str(ws), "--offline", "--only", "compile_audit", "--json"])
    report = json.loads(capsys.readouterr().out)
    row = {g["gate"]: g for g in report["gates"]}["compile_audit"]
    assert row["status"] == "FAIL"
    assert row["reason_code"] == "compiled_pdf_stale"
    assert rc == report["exit_code"] != 0


# ---------------------------------------------------------------------------
# rendered figures must postdate the experiments they plot
# ---------------------------------------------------------------------------

def _touch(p: Path, when: float) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}", encoding="utf-8")
    os.utime(p, (when, when))


BASE = 1_800_000_000.0


def test_figure_older_than_experiments_is_stale(tmp_path):
    """The measured ML04 shape: figures rendered at 20:08, experiments re-run
    at 20:23. The figure is older than the PDF too, so comparing figure-vs-PDF
    misses it completely -- the invariant is figure-vs-experiment."""
    ws = _ws(tmp_path)
    _pdf(ws, "20990101000000+00'00'")          # PDF newer than everything
    _compile_verdict(ws)
    _touch(ws / "experiments" / "full" / "group_main" / "RESULT.json", BASE + 900)
    _touch(ws / "figures" / "fig1_main" / "output.pdf", BASE)
    _touch(ws / "figures" / "fig1_main" / "figure_audit.json", BASE + 950)

    stale, newest = gate_all._stale_figures(ws)
    assert newest is not None
    assert [p.name for p in stale] == ["output.pdf"]
    r = _run(ws)
    assert r["status"] == "FAIL"
    assert r["reason_code"] == "compiled_pdf_stale"
    assert "superseded numbers" in r["detail"]
    assert "figures/fig1_main/output.pdf" in r["detail"]


def test_figure_newer_than_experiments_is_fresh(tmp_path):
    ws = _ws(tmp_path)
    _pdf(ws, "20990101000000+00'00'")
    _compile_verdict(ws)
    _touch(ws / "experiments" / "full" / "group_main" / "RESULT.json", BASE)
    _touch(ws / "figures" / "fig1_main" / "output.pdf", BASE + 900)
    stale, _ = gate_all._stale_figures(ws)
    assert stale == []
    r = _run(ws)
    assert r["status"] == "PASS", r


def test_figure_audit_side_effects_do_not_count(tmp_path):
    """figure_audit.py rewrites figure_audit.json / text_layout.json in place,
    so re-running an audit standalone would make them newer than the manuscript
    without the rendered figure changing. Only the rendered output compares."""
    ws = _ws(tmp_path)
    _pdf(ws, "20990101000000+00'00'")
    _compile_verdict(ws)
    _touch(ws / "experiments" / "full" / "group_main" / "RESULT.json", BASE)
    _touch(ws / "figures" / "fig1_main" / "output.pdf", BASE + 900)
    for side in ("figure_audit.json", "text_layout.json", "render.log",
                 "caption.txt", "spec.recipe.json"):
        _touch(ws / "figures" / "fig1_main" / side, BASE + 5000)
    stale, _ = gate_all._stale_figures(ws)
    assert stale == []
    r = _run(ws)
    assert r["status"] == "PASS", r


def test_no_experiments_means_no_figure_staleness(tmp_path):
    """A theory-only workspace has no RESULT.json, so there is nothing for a
    figure to be stale against -- must not invent a comparison."""
    ws = _ws(tmp_path)
    _pdf(ws, "20990101000000+00'00'")
    _compile_verdict(ws)
    _touch(ws / "figures" / "fig1_main" / "output.pdf", BASE)
    stale, newest = gate_all._stale_figures(ws)
    assert stale == [] and newest is None
    r = _run(ws)
    assert r["status"] == "PASS", r
