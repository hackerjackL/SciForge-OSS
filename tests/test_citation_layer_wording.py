"""v1.7.4 drift guard: the citation docs describe ONE verification contract.

Contract (CLAUDE.md hard rule 5): arXiv existence + CrossRef DOI/metadata are
mandatory; Semantic Scholar fuzzy matching is Layer 3, runs whenever reachable,
and any degradation is disclosed in ``CITATION_AUDIT.json``
(``verification_depth`` / ``layers_verified`` / ``layer3_status`` /
``layer3_detail``). Claiming three layers that did not run is a fabricated
audit record.

Docs that still promise an unconditional three-layer pass either stall a
Mode-A host agent (it cannot satisfy the promise while the S2 API is rate
limited) or invite it to fake the audit. This test prevents the wording from
drifting back:

  1. contradiction phrases must not appear in the canonical docs (skill
     library, root SKILL.md, the researcher agent prompt, the parity doc, the
     e2e fixture's evaluation review);
  2. the replacement terminology must actually be present where the contract
     lives (``citation-discipline.md`` and the auto-pipeline orchestrator);
  3. the disclosure vocabulary is derived from
     ``CITATION_AUDIT.schema.json`` — the single source of truth — so a schema
     change without doc coverage fails here instead of shipping silently.

Note on scope: the scan deliberately covers only files this contract owns.
README.md / README.zh.md / AGENT_GUIDE.md / CHANGELOG.md carried their own
three-layer marketing lines in v1.7.3; they are version-pinned release docs
owned by the release pass, so they are not asserted here. Extend
``_canonical_docs`` when they are migrated.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
DOCS = REPO_ROOT / "docs"
ORCHESTRATOR = SKILLS / "orchestrator" / "auto-pipeline" / "SKILL.md"
CITATION_DISCIPLINE = SKILLS / "shared-references" / "citation-discipline.md"
CITATION_SCHEMA = (SKILLS / "shared-references" / "schemas"
                   / "CITATION_AUDIT.schema.json")
EVALUATION_REVIEW = (REPO_ROOT / "fixtures" / "e2e_minimal" / ".sciforge"
                     / "verdicts" / "EVALUATION_REVIEW.json")

# Phrases that assert an unconditional three-layer pass. They are matched
# case-insensitively and must never reappear in the canonical docs. The bare
# enum token ``"3-layer"`` is legitimate schema vocabulary (it names the depth
# actually achieved), so only the prose claims are forbidden.
FORBIDDEN_CLAIMS = [
    r"3-layer\s+anti-hallucination",
    r"3-layer\s+verification",
    r"3-layer-verified",
    r"3-layer\s+citation",
    r"three-layer\s+(?:anti-hallucination|citation)",
    r"3\s+layers?\s+of\s+anti-hallucination",
    r"all\s+3\s+layers",
    r"3-layer[^\n]{0,40}\bmandatory\b",
    r"3\s*层(?:引用|防幻觉|验证)",
]
FORBIDDEN_RE = re.compile("|".join(FORBIDDEN_CLAIMS), re.IGNORECASE)

# Positive contract vocabulary every reader of the protocol must see.
REQUIRED_TERMS = (
    "multi-layer",
    "Semantic Scholar",
    "Layer 3",
    "2-layer-degraded",
    "verification_depth",
    "layers_verified",
    "layer3_status",
    "layer3_detail",
)


def _canonical_docs() -> list[Path]:
    docs = sorted(SKILLS.rglob("*.md"))
    docs.extend([
        REPO_ROOT / "SKILL.md",
        DOCS / "agents" / "sciforge-researcher.md",
        DOCS / "SCIENTISTTWO_PARITY.md",
    ])
    return [path for path in docs if path.is_file()]


def _schema() -> dict:
    return json.loads(CITATION_SCHEMA.read_text(encoding="utf-8"))


def _enum(path: tuple[str, ...]) -> set[str]:
    node = _schema()
    for key in path:
        node = node[key]
    return set(node)


DEPTH_ENUM = ("properties", "verification_depth", "enum")
LAYERS_ENUM = ("properties", "layers_verified", "items", "enum")
LAYER3_ENUM = ("properties", "layer3_status", "enum")


@pytest.mark.parametrize("doc", _canonical_docs(),
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_unconditional_three_layer_claim(doc: Path):
    text = doc.read_text(encoding="utf-8")
    match = FORBIDDEN_RE.search(text)
    assert match is None, (
        f"{doc.relative_to(REPO_ROOT)} still claims an unconditional "
        f"three-layer pass: {match.group(0)!r}. The contract is multi-layer: "
        "arXiv + CrossRef mandatory, Semantic Scholar Layer 3 when reachable, "
        "degradation disclosed in CITATION_AUDIT.json.")


@pytest.mark.parametrize("doc", [CITATION_DISCIPLINE, ORCHESTRATOR],
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_protocol_docs_carry_the_new_contract(doc: Path):
    text = doc.read_text(encoding="utf-8")
    missing = [term for term in REQUIRED_TERMS if term not in text]
    assert not missing, f"{doc.name} is missing contract terms: {missing}"
    assert "arXiv" in text and "CrossRef" in text
    assert "fabricat" in text.lower(), (
        "the no-fabricated-audit rule (claiming layers that did not run) "
        "must be stated where the protocol lives")


def test_disclosure_vocabulary_matches_the_schema():
    """Derive the enums from the schema, never hard-code them: adding a value
    to the schema without documenting it in the protocol doc fails here. The
    orchestrator points at the protocol doc, so it must carry the field names
    (pinned by ``test_protocol_docs_carry_the_new_contract``), not every value."""
    text = CITATION_DISCIPLINE.read_text(encoding="utf-8")
    for path in (DEPTH_ENUM, LAYERS_ENUM, LAYER3_ENUM):
        missing = sorted(value for value in _enum(path) if value not in text)
        assert not missing, (
            f"{CITATION_DISCIPLINE.name} does not document "
            f"{'.'.join(path)} values: {missing}")


def test_orchestrator_gate_stays_non_skippable():
    """Degradable Layer 3 must not soften the gate itself: the citation gate
    remains non-skippable, the degraded pass is 'two mandatory layers + a
    disclosed Layer 3', never 'verification optional'."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "non-skippable" in text
    assert "multi-layer citation verification passed" in text
    assert "must run even for theory-only" in text


def test_gate_requires_degradation_to_be_disclosed():
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "Semantic Scholar Layer 3 completed or its absence disclosed" in text


def test_source_audit_axes_are_distinguished_from_retrieval_layers():
    """The citation-audit skill's 'three axes' (existence/metadata/context)
    always run; only retrieval layers degrade. The protocol doc must keep the
    two concepts apart so 'three layers' cannot creep back as an alias."""
    text = CITATION_DISCIPLINE.read_text(encoding="utf-8")
    assert "three audit axes" in text
    for axis in ("EXISTENCE", "METADATA", "CONTEXT"):
        assert axis in text


def test_root_skill_md_uses_multi_layer_wording():
    text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "multi-layer" in text
    assert FORBIDDEN_RE.search(text) is None


def test_researcher_agent_prompt_states_the_disclosure():
    text = (DOCS / "agents" / "sciforge-researcher.md").read_text(
        encoding="utf-8")
    assert "multi-layer" in text
    assert "Layer 3 when reachable" in text
    assert "CITATION_AUDIT.json" in text


def test_e2e_fixture_evaluation_review_makes_no_layer_count_claim():
    """The fixture is asserted by the smoke/gate tests; its justification must
    not claim a depth the accompanying pre-v1.7.4 CITATION_AUDIT.json cannot
    evidence."""
    text = EVALUATION_REVIEW.read_text(encoding="utf-8")
    assert "3-layer" not in text
    assert "verified references" in text