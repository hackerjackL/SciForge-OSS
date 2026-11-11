"""v1.7.4 debt-payment regressions.

J1  Layer-3 (Semantic Scholar) availability must be disclosed, never silently
    dropped or fabricated. ``CITATION_AUDIT.schema.json`` gains the
    ``verification_depth`` / ``layers_verified`` / ``layer3_status`` /
    ``layer3_detail`` vocabulary; a degraded (2-layer) verdict validates, a
    fabricated depth claim is rejected, and the pre-v1.7.4 fixture still
    validates unchanged. Contract docs must document every enum value.

J2a ``smoke_gate._find_smoke`` let a single root-level ``.SMOKE.json`` satisfy
    every dispatched group (the anti-laundering rule in its own docstring).
    A record now belongs to at most one group, and the un-named root-level
    catch-all is restricted to single-group runs. Both the negative case
    (shared record across groups -> FAIL) and the legitimate single-group /
    ``_ungrouped`` shapes are pinned.

J2b ``paper-writing/SKILL.md`` advertised 8 leakage classes while the scanner
    emits 12 (A-L) plus ``I-frontmatter``. A drift test derives the class set
    from ``leakage_scan.CLASSES`` and the runtime ``version`` field, never from
    a hard-coded literal.

J2c The scanner docstring version and the version it writes into the verdict
    must agree (checked by running the scanner, not by trusting either text).

J2d ``REPRODUCE.md`` documents the ``gate_all.py`` Mode-A entry point; the
    option list is cross-checked against gate_all's own argparse options.

stdlib + pytest only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
SKILLS = REPO_ROOT / "skills"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_verdicts  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


smoke = _load("smoke_gate_v174", SCRIPTS / "smoke_gate.py")
leak = _load("leakage_scan_v174", SCRIPTS / "leakage_scan.py")

CITATION_SCHEMA = "CITATION_AUDIT.schema.json"
CITATION_SKILL = SKILLS / "support" / "citation-audit" / "SKILL.md"
UNIVERSAL_SKILL = SKILLS / "meta-skills" / "universal-retrieval" / "SKILL.md"
PAPER_WRITING_SKILL = SKILLS / "support" / "paper-writing" / "SKILL.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
REPRODUCE_MD = REPO_ROOT / "REPRODUCE.md"

DEPTH_VALUES = {"3-layer", "2-layer-degraded", "not_attempted"}
LAYER_VALUES = {"arxiv", "crossref", "semantic_scholar"}
LAYER3_VALUES = {
    "verified",
    "not_required",
    "unavailable_rate_limited",
    "unavailable_network",
    "unavailable_no_credentials",
    "unavailable_error",
    "not_attempted",
}


# ===========================================================================
# J1 — verification-depth disclosure contract
# ===========================================================================
def _schema() -> dict:
    schema, error = validate_verdicts.load_schema(CITATION_SCHEMA)
    assert error is None, error
    return schema


def _citation_doc(**overrides) -> dict:
    doc = {
        "audit_skill": "citation-audit",
        "verdict": "PASS",
        "reason_code": "all_entries_keep",
        "summary": "2 entries audited; arXiv + CrossRef passed, Layer 3 unavailable.",
        "audited_input_hashes": {"references.bib": "sha256:" + "a" * 64},
        "trace_path": ".sciforge/traces/citation-audit/run01",
        "thread_id": "thread-1",
        "reviewer_model": "reviewer",
        "reviewer_reasoning": "xhigh",
        "generated_at": "2026-11-11T00:00:00Z",
        "verification_depth": "2-layer-degraded",
        "layers_verified": ["arxiv", "crossref"],
        "layer3_status": "unavailable_rate_limited",
        "layer3_detail": "HTTP 429 from api.semanticscholar.org after 3 attempts",
        "details": {"total_entries": 2, "per_entry": []},
    }
    doc.update(overrides)
    return doc


def _validate(tmp_path: Path, doc: dict) -> tuple[str, list[str]]:
    path = tmp_path / "CITATION_AUDIT.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return validate_verdicts.validate_json_file("CITATION_AUDIT.json", path)


def test_citation_schema_lints_and_declares_depth_vocabulary():
    schema = _schema()
    assert validate_verdicts.lint_schema(schema) == []
    props = schema["properties"]
    assert set(props["verification_depth"]["enum"]) == DEPTH_VALUES
    assert set(props["layers_verified"]["items"]["enum"]) == LAYER_VALUES
    assert set(props["layer3_status"]["enum"]) == LAYER3_VALUES
    # Backward compatibility: pre-v1.7.4 artifacts omit the fields.
    assert "verification_depth" not in schema["required"]


def test_degraded_two_layer_verdict_validates(tmp_path: Path):
    status, notes = _validate(tmp_path, _citation_doc())
    assert status == "PASS", notes


def test_three_layer_verdict_validates(tmp_path: Path):
    doc = _citation_doc(verification_depth="3-layer",
                        layers_verified=["arxiv", "crossref", "semantic_scholar"],
                        layer3_status="verified")
    doc.pop("layer3_detail")
    status, notes = _validate(tmp_path, doc)
    assert status == "PASS", notes


def test_not_attempted_verdict_validates_with_empty_layers(tmp_path: Path):
    doc = _citation_doc(verdict="NOT_APPLICABLE", reason_code="no_citations",
                        verification_depth="not_attempted", layers_verified=[],
                        layer3_status="not_attempted")
    doc.pop("layer3_detail")
    status, notes = _validate(tmp_path, doc)
    assert status == "PASS", notes


@pytest.mark.parametrize("field,value", [
    ("verification_depth", "3-layer-claimed"),
    ("layer3_status", "unavailable_429"),
])
def test_unknown_disclosure_vocabulary_is_rejected(tmp_path: Path, field, value):
    """A raw HTTP code or invented depth token must fail, so the vocabulary
    stays machine-checkable (the 429 cause belongs in ``layer3_detail``)."""
    status, notes = _validate(tmp_path, _citation_doc(**{field: value}))
    assert status == "FAIL"
    assert any(field in note for note in notes)


def test_layers_verified_rejects_invented_layer(tmp_path: Path):
    status, notes = _validate(
        tmp_path, _citation_doc(layers_verified=["arxiv", "openalex"]))
    assert status == "FAIL"
    assert any("layers_verified" in note for note in notes)


def test_pre_v174_fixture_still_validates():
    """Existing artifacts without the new fields must keep passing."""
    fixture = (REPO_ROOT / "fixtures" / "e2e_minimal" / ".sciforge" /
               "verdicts" / "CITATION_AUDIT.json")
    status, notes = validate_verdicts.validate_json_file(
        "CITATION_AUDIT.json", fixture)
    assert status == "PASS", notes


@pytest.mark.parametrize("doc,values", [
    (CITATION_SKILL, DEPTH_VALUES | LAYER_VALUES | LAYER3_VALUES),
    (UNIVERSAL_SKILL, DEPTH_VALUES | LAYER_VALUES | LAYER3_VALUES),
])
def test_contract_docs_document_every_enum_value(doc: Path, values: set[str]):
    """Drift guard: schema vocabulary added without doc coverage fails here."""
    text = doc.read_text(encoding="utf-8")
    missing = sorted(v for v in values if v not in text)
    assert not missing, f"{doc.name} does not document {missing}"


def test_claude_memory_rule_matches_the_disclosure_contract():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "2-layer-degraded" in text
    for field in ("verification_depth", "layers_verified", "layer3_status",
                  "layer3_detail"):
        assert field in text
    assert "CITATION_AUDIT.schema.json" in text


def test_unconditional_three_layer_claim_is_gone():
    """The old absolute claim must not survive in the contract docs."""
    for doc in (UNIVERSAL_SKILL, CITATION_SKILL):
        text = doc.read_text(encoding="utf-8")
        assert "The 3-layer anti-hallucination protocol is mandatory" not in text


# ===========================================================================
# J2a — one smoke record must not launder several groups
# ===========================================================================
FAKE_SANDBOX = lambda _ws: ["/usr/bin/env"]  # noqa: E731


def _write_script(ws: Path, rel: str = "src/experiments/full/g1.py",
                  source: str = 'print("smoke ok")\n') -> str:
    path = ws / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_smoke(path: Path, script: str, sha: str,
                 experiment_id: str = "g1") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "experiment_id": experiment_id,
        "smoke_result": "PASS",
        "status_row_written": True,
        "script": script,
        "script_sha256": sha,
        "executed_at": "2026-11-11T00:00:00Z",
    }), encoding="utf-8")


def _dispatch_two_groups(ws: Path) -> Path:
    full = ws / "experiments" / "full"
    for group in ("g1", "g2"):
        gdir = full / group
        gdir.mkdir(parents=True)
        (gdir / "DISPATCH.json").write_text("{}", encoding="utf-8")
        (gdir / "STATUS.json").write_text('{"state": "done"}', encoding="utf-8")
    return full


def test_shared_root_smoke_cannot_launder_two_groups(tmp_path: Path, capsys):
    """NEGATIVE: two dispatched groups + one root-level shared record. The
    gate must refuse — neither group may cite the same proof."""
    full = _dispatch_two_groups(tmp_path)
    sha = _write_script(tmp_path)
    _write_smoke(full / "shared.SMOKE.json", "src/experiments/full/g1.py", sha,
                 experiment_id="shared")

    doc = smoke.check(tmp_path, sandbox_wrap=FAKE_SANDBOX)

    assert doc["verdict"] == "FAIL", doc
    assert {g["group"] for g in doc["groups"]} == {"g1", "g2"}
    assert all(g["smoke"] is None for g in doc["groups"]), doc["groups"]
    assert all("missing_smoke" in (g.get("record") or {}).get("reason_codes", [])
               for g in doc["groups"])
    assert smoke.main([str(tmp_path), "--json"]) == 2
    capsys.readouterr()


def test_group_named_root_smoke_covers_only_its_group(tmp_path: Path):
    """NEGATIVE variant: a root-level record named after g1 satisfies g1 but
    must not be re-used for g2."""
    full = _dispatch_two_groups(tmp_path)
    sha = _write_script(tmp_path)
    _write_smoke(full / "g1.SMOKE.json", "src/experiments/full/g1.py", sha)

    doc = smoke.check(tmp_path, sandbox_wrap=FAKE_SANDBOX)
    by_group = {g["group"]: g for g in doc["groups"]}

    assert doc["verdict"] == "FAIL"
    assert by_group["g1"]["smoke"] == "experiments/full/g1.SMOKE.json"
    assert by_group["g2"]["smoke"] is None
    assert "missing_smoke" in by_group["g2"]["record"]["reason_codes"]


def test_single_group_root_smoke_is_still_accepted(tmp_path: Path):
    """POSITIVE: the legitimate single-group shape (record at full/ root)."""
    full = tmp_path / "experiments" / "full"
    gdir = full / "g1"
    gdir.mkdir(parents=True)
    (gdir / "DISPATCH.json").write_text("{}", encoding="utf-8")
    sha = _write_script(tmp_path)
    _write_smoke(full / "shared.SMOKE.json", "src/experiments/full/g1.py", sha)

    doc = smoke.check(tmp_path, sandbox_wrap=FAKE_SANDBOX)
    assert doc["verdict"] == "PASS", doc
    assert doc["groups"][0]["smoke"] == "experiments/full/shared.SMOKE.json"
    assert doc["executed"] == 1


def test_ungrouped_results_at_full_root_are_still_accepted(tmp_path: Path):
    """POSITIVE: experiments/full/ holding results directly (no group dirs)
    is a legal shape; its smoke must still be found beside it."""
    full = tmp_path / "experiments" / "full"
    full.mkdir(parents=True)
    sha = _write_script(tmp_path, rel="experiments/full/run.py")
    (full / "x.SMOKE.json").write_text(json.dumps({
        "experiment_id": "x", "smoke_result": "PASS",
        "status_row_written": True,
        "script": "experiments/full/run.py",
        "script_sha256": sha,
    }), encoding="utf-8")

    doc = smoke.check(tmp_path, sandbox_wrap=FAKE_SANDBOX)
    assert doc["verdict"] == "PASS", doc
    assert doc["groups"][0]["group"] == "full"
    assert doc["groups"][0]["smoke"] == "experiments/full/x.SMOKE.json"


def test_find_smoke_never_returns_a_consumed_record(tmp_path: Path):
    """Unit-level invariant behind the gate: with a shared ``consumed`` set a
    record can be claimed once and never a second time."""
    full = tmp_path / "experiments" / "full"
    full.mkdir(parents=True)
    rec = {"path": full / "shared.SMOKE.json", "data": {}, "unreadable": False}
    rec["path"].write_text("{}", encoding="utf-8")
    consumed: set[Path] = set()

    first, _ = smoke._find_smoke("g1", full / "g1", full, [rec], n_groups=1,
                                 consumed=consumed)
    second, _ = smoke._find_smoke("g2", full / "g2", full, [rec], n_groups=1,
                                  consumed=consumed)

    assert first is rec
    assert second is None
    assert consumed == {rec["path"]}


# ===========================================================================
# J2b / J2c — leakage class table + scanner version consistency
# ===========================================================================
def _scanner_classes() -> set[str]:
    classes = set(leak.CLASSES)
    source = (SCRIPTS / "leakage_scan.py").read_text(encoding="utf-8")
    classes.update(re.findall(r'"class":\s*"([^"]+)"', source))
    return classes


def _paper_writing_class_labels() -> set[str]:
    text = PAPER_WRITING_SKILL.read_text(encoding="utf-8")
    return set(re.findall(r"^\|\s*\*\*([A-Z](?:-frontmatter)?)\*\*\s*\|",
                          text, re.M))


def test_paper_writing_documents_every_scanner_class():
    labels = _paper_writing_class_labels()
    expected = _scanner_classes()
    assert len(leak.CLASSES) == 12, sorted(leak.CLASSES)
    assert {label for label in labels if label != "I-frontmatter"} == \
        set(leak.CLASSES), (labels, expected)
    assert "I-frontmatter" in labels


def _runtime_scanner_version(tmp_path: Path) -> str:
    ws = tmp_path / "ws"
    paper = ws / "paper"
    paper.mkdir(parents=True)
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "The numerical experiment uses a fixed seed.\n"
        "\\end{document}\n",
        encoding="utf-8")
    assert leak.main([str(ws), "--write-verdict"]) == 0
    verdict = json.loads((paper / "LEAKAGE_SCRUB.json").read_text())
    return verdict["version"]


def test_scanner_version_is_consistent_everywhere(tmp_path: Path):
    """The version written into the verdict is the single source of truth:
    the module docstring and paper-writing's scrub-gate section must agree."""
    version = _runtime_scanner_version(tmp_path)
    assert version in leak.__doc__, (version, leak.__doc__[:200])
    assert version in PAPER_WRITING_SKILL.read_text(encoding="utf-8")


# ===========================================================================
# J2d — REPRODUCE.md documents the gate_all Mode-A entry point
# ===========================================================================
def test_reproduce_documents_gate_all_and_its_real_options():
    text = REPRODUCE_MD.read_text(encoding="utf-8")
    gate_src = (SCRIPTS / "gate_all.py").read_text(encoding="utf-8")

    assert "gate_all.py" in text
    for option in ("--json", "--only", "--skip", "--offline",
                   "--integrity-llm", "--timeout", "--list"):
        assert option in text, f"REPRODUCE.md missing {option}"
        assert f'"{option}"' in gate_src, f"gate_all.py has no {option}"
    assert "UNPROTECTED" in text
    assert "该保证" in text  # explains that UNPROTECTED means the guarantee is absent