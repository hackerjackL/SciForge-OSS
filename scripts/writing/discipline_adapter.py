#!/usr/bin/env python3
"""SciForge-OSS multi-disciplinary writing Adapter — Phase 6.

Discipline detection + writing-style Adapter dispatch for the single-agent
pipeline. Given the domain signature / problem text, classifies into one of the
three adapter families and returns the writing constraints that MUST be applied
during paper-writing:

  - STEM            : passive voice, rigorous derivation, quantitative comparison
  - Med/Bio         : controlled-comparison emphasis, statistical significance
                      (p-value), data-compliance + ethics statement
  - Humanities/SS   : concept-evolution analysis, source/史料 chains, qualitative
                      argumentation frameworks

Output is a JSON adapter contract consumed by `/paper-writing` (Section style,
forced slots, tone rules, forbidden phrasings).

CLI:
    python3 scripts/writing/discipline_adapter.py detect "<problem text or signature>"
    python3 scripts/writing/discipline_adapter.py adapter <stem|medbio|humanities>
"""
import argparse
import json
import re
import sys

STEM_KEYWORDS = [
    "theorem", "lemma", "proof", "derivation", "differential", "equation",
    "simulation", "numerical", "convergence", "optimization", "gradient",
    "quantum", "entropy", "band structure", "eigenvalue", "symmetric",
    "particle", "field theory", "algorithm", "complexity", "matrix",
]
MEDBIO_KEYWORDS = [
    "clinical", "patient", "trial", "cohort", "p-value", "significance",
    "dose", "efficacy", "safety", "biomarker", "protein", "peptide",
    "enzyme", "cell", "gene", "mutation", "assay", "treatment", "placebo",
    "ethics", "irb", "consent", "prevalence", "mortality",
]
HUMANITIES_KEYWORDS = [
    "discourse", "narrative", "hermeneutic", "historical", "archive",
    "textual", "manuscript", "philosophy", "ethics of", "concept",
    "ideology", "discourse analysis", "interpretation", "cultural",
    "literary", "rhetoric", "genealogy", "source-critical",
]

ADAPTERS = {
    "stem": {
        "family": "STEM",
        "tone": ["passive voice preferred", "objective, restrained claims",
                 "quantitative precision (units, error bars)"],
        "structure": ["Formalization", "Derivation", "Main Results",
                      "Verification / Numerical Checks", "Discussion"],
        "forced_slots": ["derivation_log", "verification_evidence"],
        "forbidden": ["anecdotal evidence", "unsupported superlatives"],
        "citation": "author-year or numeric; formula-heavy",
    },
    "medbio": {
        "family": "Med/Bio",
        "tone": ["controlled-comparison framing", "statistical significance explicit",
                 "clinical/translational relevance stated"],
        "structure": ["Methods (cohort/assay)", "Results (statistical)",
                      "Discussion (comparison to prior trials)", "Ethics & Compliance"],
        "forced_slots": ["statistical_significance", "ethics_statement",
                         "data_compliance", "limitations"],
        "forbidden": ["overclaiming efficacy from non-significant results",
                      "missing p-value or CI"],
        "citation": "journal style; CONSORT/PRISMA reporting norms",
    },
    "humanities": {
        "family": "Humanities/Social Science",
        "tone": ["concept-evolution analysis", "source-critical argumentation",
                 "qualitative framework with logical structure"],
        "structure": ["Introduction (problem + historiography)", "Conceptual Framework",
                      "Source Analysis / Interpretation", "Discussion", "Conclusion"],
        "forced_slots": ["source_chain", "concept_definition",
                         "interpretive_scope_boundary"],
        "forbidden": ["fabricated quotes", "anachronistic reading",
                      "overgeneralization beyond sources"],
        "citation": "footnote/author-date with archival provenance",
    },
}


def detect(problem_text: str) -> dict:
    t = problem_text.lower()
    score = {
        "stem": sum(1 for k in STEM_KEYWORDS if k in t),
        "medbio": sum(1 for k in MEDBIO_KEYWORDS if k in t),
        "humanities": sum(1 for k in HUMANITIES_KEYWORDS if k in t),
    }
    best = max(score, key=score.get)
    # tie / no-signal default: stem (formal default); medbio if any bio signal
    if score[best] == 0:
        best = "stem"
    return {"detected": best, "scores": score, "adapter": ADAPTERS[best]}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "detect" and len(argv) >= 3:
        print(json.dumps(detect(argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "adapter" and len(argv) >= 3:
        fam = argv[2].lower()
        key = {"med": "medbio", "bio": "medbio", "medbio": "medbio",
               "humanities": "humanities", "humanities": "humanities",
               "stem": "stem"}.get(fam, fam)
        if key not in ADAPTERS:
            print(json.dumps({"error": f"unknown adapter: {fam}; "
                                       f"choose {list(ADAPTERS)}"}, ensure_ascii=False))
            return 2
        print(json.dumps(ADAPTERS[key], ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
