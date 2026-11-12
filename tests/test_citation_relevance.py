"""Tests for scripts/citation_relevance_gate.py — the topic-relevance gate.

Real-run defect this gate closes (S01, ARC-Bench bootstrap-coverage study):
the retrieval query ``all:"BCa" OR all:"bias-corrected and accelerated"``
collided with BCA = Binary Collision Approximation (planetary sputtering) and
BCA = Body Composition Assessment (mmWave imaging). Four off-topic entries
entered references.bib and every pre-existing citation gate passed them.

Regression data: tests/fixtures/citation_relevance/ holds VERBATIM copies of
the real S01 artifacts (references.bib, domain-signature.json, and the
title/abstract subset of verified_papers.json). runs/ is a gitignored
evaluation product, so the tests never read it.

False-positive control is tested as hard as detection: legitimate
cross-disciplinary citations (bootstrap for ML / econometrics / ecology)
must NOT fail, and a missing domain signature must SKIP, not FAIL.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import citation_relevance_gate as crg  # noqa: E402
import gate_all  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "citation_relevance"

OFF_TOPIC_KEYS = {
    "jggi2026limitations",      # BCA sputtering, Icarus (planetary science)
    "senne2026nonintrusive",    # BCA body composition, mmWave imaging
    "tai2023cancernet",         # Cancer-Net BCa-S breast-cancer radiomics
    "tramontina2022radiation",  # MD radiation damage in nanoparticles
}


# ---------------------------------------------------------------------------
# workspace builders
# ---------------------------------------------------------------------------

def _s01_ws(tmp_path: Path) -> Path:
    """A workspace holding the REAL S01 regression data."""
    ws = tmp_path / "S01"
    (ws / ".sciforge" / "refine-logs").mkdir(parents=True)
    (ws / "literature").mkdir(parents=True)
    shutil.copy(FIXTURES / "domain-signature.json",
                ws / ".sciforge" / "refine-logs" / "domain-signature.json")
    shutil.copy(FIXTURES / "references.bib", ws / "literature" / "references.bib")
    shutil.copy(FIXTURES / "verified_papers.json",
                ws / "literature" / "verified_papers.json")
    return ws


def _mini_ws(tmp_path: Path, bib: str, signature: dict | None = None,
             papers: list | None = None) -> Path:
    ws = tmp_path / "Q"
    (ws / "literature").mkdir(parents=True)
    (ws / "literature" / "references.bib").write_text(bib, encoding="utf-8")
    if signature is not None:
        (ws / ".sciforge" / "refine-logs").mkdir(parents=True)
        (ws / ".sciforge" / "refine-logs" / "domain-signature.json").write_text(
            json.dumps(signature), encoding="utf-8")
    if papers is not None:
        (ws / "literature" / "verified_papers.json").write_text(
            json.dumps(papers), encoding="utf-8")
    return ws


def _stats_signature() -> dict:
    return json.loads((FIXTURES / "domain-signature.json").read_text())


def _findings(report: dict) -> dict[str, dict]:
    return {r["key"]: r for r in report["findings"]}


# ---------------------------------------------------------------------------
# 1. REAL-DATA regression: the four S01 off-topic entries must be caught
# ---------------------------------------------------------------------------

def test_real_s01_offtopic_entries_detected(tmp_path):
    ws = _s01_ws(tmp_path)
    status, report = crg.check(ws)
    assert status == "FAIL"
    rows = _findings(report)
    flagged = {k for k, r in rows.items() if r["classification"] == "off_topic"}
    assert flagged == OFF_TOPIC_KEYS, (
        f"expected exactly the 4 real off-topic keys, got {sorted(flagged)}")
    for k in OFF_TOPIC_KEYS:
        assert rows[k]["reason_code"] == "citation_off_domain"
        assert rows[k]["detail"], "each detection must carry a reason"


def test_real_s01_relevant_entries_not_flagged(tmp_path):
    """All 17 on-topic entries (incl. cross-disciplinary bootstrap-for-DML,
    trade econometrics, ecology Shannon-index CIs) must NOT be off_topic."""
    ws = _s01_ws(tmp_path)
    _, report = crg.check(ws)
    rows = _findings(report)
    assert report["entries"] == 21
    for k, r in rows.items():
        if k not in OFF_TOPIC_KEYS:
            assert r["classification"] != "off_topic", (
                f"false positive on legitimate citation {k}: {r['detail']}")


def test_real_s01_bca_collision_specifics(tmp_path):
    """The two named exemplars from the defect report are detected, and the
    planetary one is caught via BOTH its venue (Icarus) and its abbreviation
    expansion (Binary collision approximation)."""
    ws = _s01_ws(tmp_path)
    _, report = crg.check(ws)
    rows = _findings(report)
    jggi = rows["jggi2026limitations"]
    assert jggi["classification"] == "off_topic"
    assert "icarus" in jggi["detail"].lower()
    assert "binary collision approximation" in jggi["detail"].lower()
    senne = rows["senne2026nonintrusive"]
    assert senne["classification"] == "off_topic"
    assert "body composition" in senne["detail"].lower()


def test_real_s01_cli_exit_and_json(tmp_path):
    ws = _s01_ws(tmp_path)
    p = subprocess.run(
        [sys.executable, str(SCRIPTS / "citation_relevance_gate.py"),
         str(ws), "--json"],
        capture_output=True, text=True, timeout=60)
    assert p.returncode == 2
    doc = json.loads(p.stdout)
    assert doc["status"] == "FAIL"
    assert doc["off_topic"] == 4
    assert doc["primary_domain"] == "statistics_resampling"


# ---------------------------------------------------------------------------
# 2. false-positive control: legitimate cross-disciplinary citations
# ---------------------------------------------------------------------------

ML_BOOTSTRAP_BIB = """@inproceedings{ml2024bootstrap,
  author = {A. Researcher and B. Scientist},
  title = {Bootstrap Confidence Intervals for Deep Neural Network Predictions},
  booktitle = {Advances in Neural Information Processing Systems},
  year = {2024},
  doi = {10.5555/example.neurips},
}
"""

ECONOMETRICS_BIB = """@article{econ2023wild,
  author = {C. Economist},
  title = {Wild bootstrap inference for heteroskedastic regression models},
  journal = {Journal of Econometrics},
  year = {2023},
  doi = {10.1016/j.jeconom.2023.01.001},
}
"""

ECOLOGY_BIB = """@article{eco2022shannon,
  author = {D. Ecologist},
  title = {New confidence interval methods for the Shannon diversity index},
  journal = {Ecological Indicators},
  year = {2022},
  doi = {10.1016/j.ecolind.2022.01.001},
}
"""


@pytest.mark.parametrize("bib,key", [
    (ML_BOOTSTRAP_BIB, "ml2024bootstrap"),
    (ECONOMETRICS_BIB, "econ2023wild"),
    (ECOLOGY_BIB, "eco2022shannon"),
])
def test_cross_disciplinary_citations_not_failed(tmp_path, bib, key):
    """A bootstrap/CI paper in an ML, econometrics, or ecology venue is a
    LEGAL citation for a statistics run: it must never be off_topic, even
    though its venue belongs to another discipline."""
    ws = _mini_ws(tmp_path, bib, signature=_stats_signature())
    status, report = crg.check(ws)
    assert status != "FAIL", f"false FAIL on {key}"
    row = _findings(report)[key]
    assert row["classification"] in ("relevant", "uncertain")


def test_not_in_standard_methods_is_not_failure(tmp_path):
    """A statistics paper about a method NOT in the standard_methods literal
    list (permutation tests) is still on-domain and must pass."""
    bib = """@article{perm2021test,
  author = {E. Statistician},
  title = {Permutation tests for two-sample location problems},
  journal = {Computational Statistics & Data Analysis},
  year = {2021},
  doi = {10.1016/j.csda.2021.01.001},
}
"""
    ws = _mini_ws(tmp_path, bib, signature=_stats_signature())
    status, report = crg.check(ws)
    assert status == "PASS"
    assert _findings(report)["perm2021test"]["classification"] == "relevant"


def test_generic_word_alone_is_not_home_evidence(tmp_path):
    """'regression' / 'study' appear in the mmWave and cancer abstracts too;
    a title with ONLY generic quantitative words and a foreign abstract must
    still be caught (guards the exact senne/tai false-negative path)."""
    papers = [{
        "key": "generic2026study",
        "title": "A regression study of tissue composition",
        "abstract": ("We assess body composition from mmWave scans. "
                     "Body fat percentage and visceral adipose tissue are "
                     "estimated from bioimpedance-validated clinical imaging "
                     "of a patient cohort; MRI and computed tomography are "
                     "the gold standard."),
    }]
    bib = """@misc{generic2026study,
  author = {F. Author},
  title = {A regression study of tissue composition},
  year = {2026},
  doi = {10.48550/arXiv.2601.00001},
}
"""
    ws = _mini_ws(tmp_path, bib, signature=_stats_signature(), papers=papers)
    status, report = crg.check(ws)
    assert status == "FAIL"
    assert _findings(report)["generic2026study"]["classification"] == "off_topic"


def test_ambiguous_entry_is_warn_not_fail(tmp_path):
    """No home signal AND no dominant foreign signal => uncertain/WARN with
    disclosure, never FAIL (a thin-metadata entry is not proof of irrelevance)."""
    bib = """@misc{thin2020note,
  author = {G. Author},
  title = {A note on adaptive procedures},
  year = {2020},
  doi = {10.48550/arXiv.2001.00001},
}
"""
    ws = _mini_ws(tmp_path, bib, signature=_stats_signature())
    status, report = crg.check(ws)
    assert status == "WARN"
    row = _findings(report)["thin2020note"]
    assert row["classification"] == "uncertain"
    assert row["reason_code"] == "citation_relevance_uncertain"


# ---------------------------------------------------------------------------
# 3. BCa/BCA discrimination mechanics
# ---------------------------------------------------------------------------

def test_bca_method_token_contributes_bootstrap_not_bca():
    sig = _stats_signature()
    words = crg.method_words(sig)
    assert "bootstrap" in words          # from bca_bootstrap / percentile_bootstrap
    assert "studentized" in words
    assert "bca" not in words            # the collision token is never evidence
    assert "study" not in words          # generic fragment dropped


def test_bca_statistics_entry_passes(tmp_path):
    """A genuine BCa-bootstrap paper (mixed-case BCa, statistics vocabulary)
    must be relevant — the gate must not punish the acronym itself."""
    bib = """@article{bca2020coverage,
  author = {H. Statistician},
  title = {BCa bootstrap confidence intervals under skewness},
  journal = {Journal of Statistical Computation and Simulation},
  year = {2020},
  doi = {10.1080/00949655.2020.0000001},
}
"""
    ws = _mini_ws(tmp_path, bib, signature=_stats_signature())
    status, report = crg.check(ws)
    assert status == "PASS"
    assert _findings(report)["bca2020coverage"]["classification"] == "relevant"


def test_expansion_context_discriminates_same_acronym():
    """Identical acronym, different expansion -> different discipline."""
    stat = crg.expansion_hits("Bias-corrected and accelerated (BCa) intervals")
    phys = crg.expansion_hits("Binary collision approximation (BCA) codes")
    med = crg.expansion_hits("Body composition assessment (BCA) from scans")
    assert any(h.startswith("statistics:") for v in stat.values() for h in v) or stat == {}
    assert any(h.startswith("physics_materials:") for v in phys.values() for h in v)
    assert any(h.startswith("medical_imaging:") for v in med.values() for h in v)


def test_multireading_expansion_not_foreign_when_home_reading_exists():
    """'Double Machine Learning (DML)' reads as statistics AND ML; for a
    statistics run it must not count as foreign counter-evidence."""
    exp = crg.expansion_hits("Double Machine Learning (DML) estimation")
    assert "DML" in exp
    assert any(h.startswith("statistics:") for h in exp["DML"])


# ---------------------------------------------------------------------------
# 4. SKIP semantics
# ---------------------------------------------------------------------------

def test_missing_domain_signature_skips(tmp_path):
    bib = ML_BOOTSTRAP_BIB
    ws = _mini_ws(tmp_path, bib, signature=None)
    status, report = crg.check(ws)
    assert status == "SKIP"
    assert "domain-signature" in report["note"]


def test_missing_bib_skips(tmp_path):
    ws = tmp_path / "Q"
    (ws / ".sciforge" / "refine-logs").mkdir(parents=True)
    (ws / ".sciforge" / "refine-logs" / "domain-signature.json").write_text(
        json.dumps(_stats_signature()), encoding="utf-8")
    status, report = crg.check(ws)
    assert status == "SKIP"


def test_unreadable_signature_skips(tmp_path):
    ws = _mini_ws(tmp_path, ML_BOOTSTRAP_BIB)
    (ws / ".sciforge" / "refine-logs").mkdir(parents=True)
    (ws / ".sciforge" / "refine-logs" / "domain-signature.json").write_text(
        "{not json", encoding="utf-8")
    status, _ = crg.check(ws)
    assert status == "SKIP"


def test_cli_skip_exit_zero(tmp_path):
    ws = _mini_ws(tmp_path, ML_BOOTSTRAP_BIB, signature=None)
    p = subprocess.run(
        [sys.executable, str(SCRIPTS / "citation_relevance_gate.py"), str(ws)],
        capture_output=True, text=True, timeout=60)
    assert p.returncode == 0
    assert "SKIP" in p.stdout


# ---------------------------------------------------------------------------
# 5. gate_all wiring
# ---------------------------------------------------------------------------

def test_registered_in_gate_all():
    assert "citation_relevance" in gate_all.GATE_NAMES
    phase = dict((n, p) for n, p, _ in gate_all.GATES)["citation_relevance"]
    assert phase == "4broad"


def test_gate_all_reports_fail_on_real_data(tmp_path, capsys):
    ws = _s01_ws(tmp_path)
    rc = gate_all.main([str(ws), "--offline", "--json",
                        "--only", "citation_relevance"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    row = {r["gate"]: r for r in report["gates"]}["citation_relevance"]
    assert row["status"] == "FAIL"
    assert row["reason_code"] == "citation_off_domain"


def test_gate_all_skip_without_signature(tmp_path, capsys):
    ws = _mini_ws(tmp_path, ML_BOOTSTRAP_BIB, signature=None)
    rc = gate_all.main([str(ws), "--offline", "--json",
                        "--only", "citation_relevance"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    row = {r["gate"]: r for r in report["gates"]}["citation_relevance"]
    assert row["status"] == "SKIP"


def test_gate_all_pass_on_clean_corpus(tmp_path, capsys):
    bib = ECONOMETRICS_BIB + "\n" + ML_BOOTSTRAP_BIB
    ws = _mini_ws(tmp_path, bib, signature=_stats_signature())
    rc = gate_all.main([str(ws), "--offline", "--json",
                        "--only", "citation_relevance"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    row = {r["gate"]: r for r in report["gates"]}["citation_relevance"]
    assert row["status"] in ("PASS", "WARN")
    assert row["status"] != "FAIL"
