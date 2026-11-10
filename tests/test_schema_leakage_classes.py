"""Regression test: LEAKAGE_SCRUB.schema.json must cover every class the
scanner can emit.

The failure this prevents: ``scripts/leakage_scan.py`` grew classes I/J/K/L
after the schema was frozen at A-H. A real class-K hit (SCI body voice, project
hard rule 4) therefore produced a verdict that ``validate_verdicts.py --strict``
rejected at the phase-13 boundary — the pipeline blocked itself on its own
schema. The class set here is derived from the scanner (its ``CLASSES`` table
plus the literal class labels in its source), never hard-coded, so a future
class cannot drift away from the schema again.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
SCHEMA_NAME = "LEAKAGE_SCRUB.schema.json"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_verdicts  # noqa: E402


def _load_scanner():
    spec = importlib.util.spec_from_file_location(
        "leakage_scan_under_test", SCRIPTS / "leakage_scan.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scanner_classes() -> set[str]:
    """Every class label the scanner can put into ``classes_seen``.

    ``CLASSES`` supplies the single-letter classes; a source scan picks up
    literal labels emitted outside that table (the ``I-frontmatter`` sub-check
    of class I).
    """
    classes = set(_load_scanner().CLASSES)
    source = (SCRIPTS / "leakage_scan.py").read_text(encoding="utf-8")
    classes.update(re.findall(r'"class":\s*"([^"]+)"', source))
    return classes


def _schema_items() -> dict:
    schema = json.loads(
        (REPO_ROOT / "skills" / "shared-references" / "schemas"
         / SCHEMA_NAME).read_text(encoding="utf-8"))
    return schema["properties"]["classes_seen"]["items"]


def test_schema_enum_matches_scanner_classes():
    items = _schema_items()
    assert "enum" in items, (
        "classes_seen.items must use an enum: an explicit allowed set is what "
        "this regression test can compare against the scanner")
    assert set(items["enum"]) == scanner_classes()


def test_schema_uses_only_supported_subset_keywords():
    schema, error = validate_verdicts.load_schema(SCHEMA_NAME)
    assert error is None, error
    assert validate_verdicts.lint_schema(schema) == []


def test_all_scanner_classes_validate_as_a_verdict(tmp_path):
    verdict = {
        "gate": "pipeline-leakage-scrub",
        "version": "v3.6-mech",
        "status": "FAIL",
        "hits_found": len(scanner_classes()),
        "hits_scrubbed": 0,
        "hits_remaining": len(scanner_classes()),
        "classes_seen": sorted(scanner_classes()),
        "checked_files": ["paper/main.tex"],
        "scrubbed_to": "neutral academic prose",
    }
    path = tmp_path / SCHEMA_NAME.replace(".schema.json", ".json")
    path.write_text(json.dumps(verdict), encoding="utf-8")
    status, notes = validate_verdicts.validate_json_file(SCHEMA_NAME.replace(
        ".schema.json", ".json"), path)
    assert status == "PASS", notes


def test_scanner_output_with_k_and_l_hits_passes_schema(tmp_path):
    """End-to-end: real class K/L/I-frontmatter hits produce a schema-valid
    verdict (the exact case that used to block the phase-13 boundary)."""
    ws = tmp_path / "Q001"
    paper = ws / "paper"
    paper.mkdir(parents=True)
    (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\author{Alice Example}\n"
        "\\affiliation{Example University}\n"
        "\\begin{document}\n"
        "We apologize for the limited scope.\n"
        "The comparison ran in our workspace.\n"
        "\\end{document}\n",
        encoding="utf-8")

    scanner = _load_scanner()
    scanner.main([str(ws), "--write-verdict"])  # hits are expected (exit 2)

    produced = json.loads(
        (paper / "LEAKAGE_SCRUB.json").read_text(encoding="utf-8"))
    assert {"K", "L"} <= set(produced["classes_seen"]), produced
    verdict_path = ws / ".sciforge" / "verdicts" / "LEAKAGE_SCRUB.json"
    assert verdict_path.is_file()
    status, notes = validate_verdicts.validate_json_file(
        "LEAKAGE_SCRUB.json", verdict_path)
    assert status == "PASS", notes