#!/usr/bin/env python3
"""Citation topic-relevance gate (v1.7.4 follow-up; model-agnostic, stdlib-only).

Why this gate exists (real-run defect, S01): the retrieval query
``all:"BCa" OR all:"bias-corrected and accelerated"`` collided with the arXiv
abbreviation BCA = *Binary Collision Approximation* (planetary sputtering) and
BCA = *Body Composition Assessment* (mmWave medical imaging). Four off-topic
entries entered ``literature/references.bib`` (19% of the corpus), and every
existing citation gate passed them: gap_gate checks the gap report, doi_gate
checks DOI resolution, citation_support checks sentence-level attribution —
none checks whether a reference belongs to the run's domain at all. Existence
verification and topic relevance are orthogonal axes; a real paper about
planetary sputtering is still a wrong citation for a bootstrap-coverage study.

Design — how BCa (statistics) is separated from BCA (sputtering) without NLP
---------------------------------------------------------------------------
Naive keyword matching fails by construction here: ``bca_bootstrap`` in the
domain signature's standard_methods contains the very token that collided.
So bare acronyms are NEVER evidence, in either direction. Relevance is decided
by a conjunction of independent signals:

  1. Domain-affinity lexicon. The signature's ``primary_domain`` is mapped to
     a family of discipline vocabularies (statistics / physics-materials /
     medical-imaging / ...). Each vocabulary is a set of multi-word phrases
     and unambiguous unigrams; ``bca``/``BCA`` appear in NO vocabulary.
     Method tokens from ``standard_methods`` contribute only their non-acronym
     words (``bca_bootstrap`` -> ``bootstrap``; ``studentized_bootstrap`` ->
     ``studentized``), which is the semantic-adjacency signal.
  2. Venue discipline. ``journal``/``booktitle`` (and, when present, the DOI's
     journal slug, e.g. ``j.icarus``) are matched against venue vocabularies.
     ``Icarus`` is planetary science regardless of what the title says.
  3. Abbreviation-expansion context. When an acronym token from the query or
     the title (detected as a short mixed-case/all-caps token) is expanded in
     the abstract — ``Binary collision approximation (BCA)`` /
     ``Body composition assessment (BCA)`` — the expansion's own words are
     scored. An expansion that lands wholly in a foreign discipline is strong
     counter-evidence even when a stray generic word ("simulation", "model")
     overlaps the home domain.

Verdicts are graded to control false positives (a gate that flags legitimate
interdisciplinary citations is itself a defect):

  relevant      home-domain evidence present, no dominant foreign signal -> PASS
  uncertain     thin/ambiguous evidence (no home hit AND no foreign hit, or
                home hit coexisting with a strong foreign venue/expansion)
                -> WARN + disclosure, never FAIL: cross-disciplinary citations
                (bootstrap applied to ML, econometrics, ecology) are legal and
                MUST NOT fail merely for missing a standard_methods literal.
  off_topic     zero home-domain evidence AND (a foreign-discipline venue OR
                >= FOREIGN_MIN distinct foreign-discipline content terms OR a
                foreign abbreviation expansion) -> FAIL + reason_code.

The FAIL bar is deliberately conjunctive: BOTH the home signal must be absent
AND an independent foreign signal must be present. A bootstrap-for-ML paper
has home terms (bootstrap, confidence interval, coverage) and passes even
though its venue is an ML conference.

Inputs
------
  <ws>/.sciforge/refine-logs/domain-signature.json   (Phase 1b product; the
      domain-learner contract guarantees domain_profile/methodology_profile;
      missing file -> SKIP, because runs predating Phase 1b have no declared
      domain to check against)
  <ws>/literature/references.bib                     (missing -> SKIP)
  <ws>/literature/verified_papers.json               (optional enrichment:
      abstracts/keywords when the bib carries only titles)

Usage: python3 scripts/citation_relevance_gate.py <workspace> [--json]
                                                   [--write-verdict]
Exit: 0 = PASS/WARN/SKIP, 2 = FAIL. Stdlib only; no network, no LLM.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Discipline vocabularies.
#
# Curation rules (false-positive control):
#   * multi-word phrases are preferred over unigrams;
#   * a unigram is admitted only if it is (near-)unambiguous across the
#     disciplines modeled here ("bootstrap" yes, "model"/"simulation" no);
#   * bare acronyms ("bca", "md", "ci", "np") are NEVER admitted — they are
#     exactly the collision surface this gate exists for.
# ---------------------------------------------------------------------------

VOCAB = {
    "statistics": {
        "phrases": [
            "confidence interval", "confidence intervals", "coverage probability",
            "empirical coverage", "coverage error", "nominal coverage",
            "monte carlo", "resampling", "sampling distribution",
            "standard error", "hypothesis test", "statistical inference",
            "trimmed mean", "sample mean", "population mean", "heavy tail",
            "heavy-tailed", "light-tailed", "finite-sample", "asymptotic",
            "bias-corrected", "bias correction", "confidence set",
            "prediction interval", "credible set", "quantile regression",
            "simultaneous confidence", "confidence band", "coverage calibration",
            "robust statistics", "student-t", "central limit",
            "edgeworth expansion", "double machine learning",
        ],
        "terms": [
            "bootstrap", "bootstrapping", "bootstraps", "jackknife",
            "studentized", "percentile", "estimator", "estimand", "coverage",
            "quantile", "quantiles", "skewness", "kurtosis", "lognormal",
            "gaussian", "median", "variance", "covariance", "likelihood",
            "bayesian", "posterior", "econometric",
            "econometrics", "censoring", "wild bootstrap", "resample",
            "resamples", "pivotal", "pivot", "statistic",
            "statistics", "statistical", "nonparametric", "semiparametric",
            "biostatistics", "biometrika", "heteroskedastic", "heteroscedastic",
            # NOTE: generic words (regression, inference, simulation, model,
            # study, interval, ...) are deliberately NOT home evidence: the
            # mmWave body-composition paper says "regression" and the cancer
            # paper says "study". Home membership needs a discipline-specific
            # term, not a word every quantitative science shares.
        ],
        "venues": [
            "annals of statistics", "journal of the american statistical",
            "jasa", "biometrika", "biometrics", "bernoulli", "statistica sinica",
            "computational statistics", "statistics and computing",
            "journal of computational and graphical", "statistical science",
            "journal of statistical", "statistics & probability",
            "statistics and probability", "econometrica", "econometrics",
            "journal of econometrics", "econometric theory", "technometrics",
            "communications in statistics", "statistical methods",
            "journal of the royal statistical", "jrss", "scandinavian journal of statistics",
            "electronic journal of statistics",
            "international statistical review", "metrika", "astat",
        ],
    },
    "physics_materials": {
        "phrases": [
            "binary collision approximation", "molecular dynamics",
            "sputter yield", "sputtering yield", "ion irradiation",
            "radiation damage", "collision cascade", "point defects",
            "primary knock-on", "displacements per atom", "surface binding",
            "core-shell nanoparticle", "stacking faults", "crystal lattice",
            "nuclear energy", "stopping power",
        ],
        "terms": [
            "sputtering", "sputtered", "sputter", "irradiation", "nanoparticle",
            "nanoparticles", "interstitial", "interstitials", "vacancy",
            "vacancies", "divacancy", "divacancies", "lattice", "crystal",
            "crystalline", "bcc", "fcc", "enstatite", "plagioclase",
            "mineral", "minerals", "planetary", "regolith", "asteroid",
            "ejecta", "recoil", "implantation", "fluence", "keV", "kev",
            "sdtrimsp", "trimsp", "srim", "angstrom", "angstroms",
            "astrophysical", "astrophysics", "moon", "lunar", "mercury",
            "silicate", "amorphization", "blistering", "backscattering",
        ],
        "venues": [
            "icarus", "planetary and space science", "planetary science",
            "nuclear instruments", "nuclear materials", "journal of nuclear",
            "physical review", "phys. rev", "applied physics",
            "journal of applied physics", "surface science", "radiation effects",
            "radiation physics", "computational materials science",
            "modelling and simulation in materials", "acta materialia",
            "journal of physics", "philosophical magazine", "vacuum",
        ],
    },
    "medical_imaging": {
        "phrases": [
            "body composition", "body fat", "breast cancer", "cancer grade",
            "diffusion imaging", "magnetic resonance", "medical imaging",
            "radiomic features", "deep radiomic", "mmwave scan",
            "millimeter wave", "point clouds", "bioimpedance",
            "clinical imaging", "tumor grading", "tumour grading",
            "treatment planning", "computed tomography",
        ],
        "terms": [
            "mmwave", "radiomic", "radiomics", "mri", "biopsy", "tumor",
            "tumour", "cancer", "carcinoma", "oncology", "clinical", "cohort",
            "patient", "patients", "imaging", "ultrasound", "tomography",
            "bioimpedance", "adipose", "visceral", "bmi", "chemotherapy",
            "diagnosis", "prognosis", "histopathology", "lesion", "lesions",
            "mammography", "ct", "pet", "segmentation",
        ],
        "venues": [
            "medical image analysis", "ieee transactions on medical imaging",
            "radiology", "medical physics", "journal of medical imaging",
            "miccai", "nature medicine", "the lancet", "bmj",
            "computerized medical imaging", "ieee journal of biomedical",
        ],
    },
    "machine_learning": {
        "phrases": [
            "deep learning", "neural network", "neural networks",
            "machine learning", "representation learning", "reinforcement learning",
            "training set", "test set", "cross-validation", "gradient descent",
            "language model", "computer vision",
        ],
        "terms": [
            "classifier", "classification", "convolutional", "transformer",
            "transformers", "backpropagation", "embedding", "embeddings",
            "supervised", "unsupervised", "dataset", "benchmark", "accuracy",
            "overfitting", "regularization", "hyperparameter", "hyperparameters",
            "pytorch", "tensorflow", "gpu", "encoder", "decoder", "attention",
        ],
        "venues": [
            "neurips", "neural information processing", "icml",
            "international conference on machine learning", "iclr",
            "learning representations", "journal of machine learning",
            "jmlr", "machine learning", "aaai", "cvpr", "eccv", "iccv",
            "transactions on pattern analysis", "pmlr",
        ],
    },
    "biology_ecology": {
        "phrases": [
            "species diversity", "shannon index", "simpson index",
            "community ecology", "population dynamics", "gene expression",
        ],
        "terms": [
            "ecology", "ecological", "biodiversity", "species", "abundance",
            "entomology", "insect", "insects", "genomic", "genomics", "allele",
            "phylogenetic", "habitat", "fauna", "flora",
        ],
        "venues": [
            "ecology", "ecological", "journal of animal ecology",
            "ecological indicators", "biodiversity", "entomologia",
            "neotropical entomology", "journal of insect", "plos one",
            "methods in ecology",
        ],
    },
}

# primary_domain prefix -> home discipline family. Unknown domains fall back
# to a generic-scientific home built from the signature's own method words
# (so the gate degrades to "does the entry mention any declared method
# vocabulary", never to guessing a discipline).
DOMAIN_FAMILY = [
    ("statistic", "statistics"), ("resampl", "statistics"),
    ("econometr", "statistics"), ("probabilit", "statistics"),
    ("physics", "physics_materials"), ("material", "physics_materials"),
    ("astr", "physics_materials"), ("planet", "physics_materials"),
    ("medic", "medical_imaging"), ("radiolog", "medical_imaging"),
    ("clinical", "medical_imaging"), ("health", "medical_imaging"),
    ("machine_learning", "machine_learning"), ("ml_", "machine_learning"),
    ("deep_learning", "machine_learning"), ("cs_ml", "machine_learning"),
    ("computer", "machine_learning"), ("ai_", "machine_learning"),
    ("bio", "biology_ecology"), ("ecolog", "biology_ecology"),
]

# Minimum number of DISTINCT foreign content terms (phrases count 2) needed
# for the content-only off-topic route, on top of zero home evidence.
FOREIGN_MIN = 4

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.I)
FIELD_RE = re.compile(r"(\w+)\s*=\s*[\{\"]([^\}\"]*)[\}\"]", re.I)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")
ACRO_RE = re.compile(r"\b([A-Z]{2,6}|[A-Z][a-z]?[A-Z][A-Za-z]{0,4})\b")


def parse_bib(text: str) -> list[dict]:
    entries = []
    for m in ENTRY_RE.finditer(text):
        kind, key = m.group(1).lower(), m.group(2).strip()
        start = m.end()
        depth, i = 1, start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i]
        fields = {k.lower(): v for k, v in FIELD_RE.findall(body)}
        entries.append({"kind": kind, "key": key, **fields})
    return entries


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower())


def _vocab_hits(text: str, vocab: dict) -> tuple[list[str], int]:
    """Return (matched items, weighted score). Phrases weigh 2, terms 1."""
    hits, score = [], 0
    for ph in vocab["phrases"]:
        if ph in text:
            hits.append(ph)
            score += 2
    tokens = set(t.lower() for t in TOKEN_RE.findall(text))
    for term in vocab["terms"]:
        if " " in term:
            if term in text:
                hits.append(term)
                score += 2
        elif term in tokens:
            hits.append(term)
            score += 1
    return hits, score


def _venue_family(venue_text: str) -> tuple[str | None, list[str]]:
    hits_by_family = {}
    for fam, vocab in VOCAB.items():
        hits = [v for v in vocab["venues"] if v in venue_text]
        if hits:
            hits_by_family[fam] = hits
    if not hits_by_family:
        return None, []
    # longest venue match wins ("journal of nuclear materials" beats "stat")
    fam = max(hits_by_family, key=lambda f: max(len(h) for h in hits_by_family[f]))
    return fam, hits_by_family[fam]


def method_words(signature: dict) -> set[str]:
    """Non-acronym content words from standard_methods (semantic adjacency).

    ``bca_bootstrap`` contributes ``bootstrap``, never ``bca`` — a token of
    <= 3 letters is treated as an acronym fragment and dropped, which is the
    specific fix for the BCa/BCA collision. Generic words (``study`` from
    ``monte_carlo_coverage_study``, ``robust``/``location`` from
    ``robust_location_estimators``) are ALSO dropped: a cancer-imaging paper
    says "study" too, and a generic word must never establish domain
    membership on its own.
    """
    generic = {"study", "studies", "monte", "carlo", "model", "models",
               "method", "methods", "analysis", "based", "general", "new",
               "approach", "estimators", "robust", "location", "theory",
               "design", "test", "tests", "data", "using", "with"}
    words: set[str] = set()
    mp = signature.get("methodology_profile") or {}
    for m in mp.get("standard_methods") or []:
        for w in re.split(r"[^A-Za-z]+", str(m)):
            wl = w.lower()
            if len(wl) > 3 and wl not in generic:
                words.add(wl)
    return words


def home_family(signature: dict) -> str | None:
    dp = signature.get("domain_profile") or {}
    dom = _norm(str(dp.get("primary_domain") or ""))
    for prefix, fam in DOMAIN_FAMILY:
        if prefix in dom:
            return fam
    return None


def expansion_hits(text: str) -> dict[str, list[str]]:
    """Find ``<expansion> (ACRO)`` or ``ACRO (<expansion>)`` patterns and score
    the expansion words per discipline. Only the expansion — not the whole
    abstract — is scored, so a stray generic word elsewhere cannot dilute it.
    Returned entries are ``"family:expansion"`` strings.
    """
    out: dict[str, list[str]] = {}
    # expansion before the parenthesized acronym: "Binary collision approximation (BCA)"
    pre = re.compile(r"\b([A-Za-z][A-Za-z\- ]{6,60}?)\s*\(([A-Z]{2,6}|[A-Z][a-z][A-Z][A-Za-z]{0,3})\)")
    # acronym before the parenthesized expansion: "BCA (binary collision approximation)"
    post = re.compile(r"\b([A-Z]{2,6}|[A-Z][a-z][A-Z][A-Za-z]{0,3})\s*\(([A-Za-z][A-Za-z\- ]{6,60}?)\)")
    spans = []
    for m in pre.finditer(text):
        spans.append((m.group(2), m.group(1)))
    for m in post.finditer(text):
        spans.append((m.group(1), m.group(2)))
    for acro, exp in spans:
        el = _norm(exp)
        for fam, vocab in VOCAB.items():
            hits, score = _vocab_hits(el, vocab)
            if score >= 2:
                out.setdefault(acro, []).append(f"{fam}:{el.strip()}")
    return out


def classify(entry: dict, signature: dict, extra: dict | None) -> dict:
    fam = home_family(signature)
    mwords = method_words(signature)
    title = entry.get("title") or ""
    abstract = (extra or {}).get("abstract") or entry.get("abstract") or ""
    keywords = (extra or {}).get("keywords") or entry.get("keywords") or ""
    if isinstance(keywords, list):
        keywords = "; ".join(str(k) for k in keywords)
    venue = " ".join(str(entry.get(k) or "") for k in ("journal", "booktitle", "publisher"))
    venue = _norm(venue)
    doi = _norm(entry.get("doi") or "")
    # DOI journal slug as venue evidence (10.1016/j.icarus... -> "icarus")
    doi_slug = ""
    m = re.search(r"/j\.([a-z]+)", doi)
    if m:
        doi_slug = m.group(1)
    content = _norm(" . ".join([title, str(keywords), abstract]))
    title_l = _norm(title)
    venue_fam, venue_hits = _venue_family(venue + " " + doi_slug)

    home_vocab = VOCAB.get(fam) if fam else None
    if home_vocab is not None:
        home_hits, home_score = _vocab_hits(content, home_vocab)
        home_title_hits, _ = _vocab_hits(title_l, home_vocab)
        # A venue IN the home discipline is itself home evidence: a paper in
        # "Computational Statistics & Data Analysis" belongs to statistics
        # even when its title uses none of the lexicon's terms (e.g.
        # "Permutation tests for two-sample location problems").
        if venue_fam == fam and venue_hits:
            home_score += 2
            home_hits = sorted(set(home_hits) | {f"venue:{venue_hits[0]}"})
    else:
        # unknown domain: adjacency to declared method words is the only home
        # signal; foreign vocabularies are still consulted for counter-evidence
        toks = set(t.lower() for t in TOKEN_RE.findall(content))
        home_hits = sorted(toks & mwords)
        home_score = len(home_hits)
        home_title_hits = sorted(set(t.lower() for t in TOKEN_RE.findall(title_l)) & mwords)
    # declared-method adjacency (non-acronym words) adds to the home signal
    toks = set(t.lower() for t in TOKEN_RE.findall(content))
    adj = sorted(toks & mwords)
    home_score += len(adj)
    home_hits = sorted(set(home_hits) | set(adj))

    foreign = {}
    for f, vocab in VOCAB.items():
        if f == fam:
            continue
        hits, score = _vocab_hits(content, vocab)
        if score:
            foreign[f] = {"hits": hits, "score": score}

    foreign_venue = venue_fam is not None and venue_fam != fam
    exp = expansion_hits(title + " . " + abstract)
    # An expansion is FOREIGN only when NONE of its discipline readings is the
    # home family: "Double Machine Learning (DML)" reads as both statistics
    # and ML, and for a statistics run that is a home expansion, not counter-
    # evidence. Only unambiguously-foreign expansions (BCA -> sputtering,
    # BCA -> body composition, MRI -> imaging) count against the entry.
    foreign_exp = {a: v for a, v in exp.items()
                   if fam and not any(h.startswith(fam + ":") for h in v)} if fam else exp

    # strongest foreign content family (excluding the home family)
    top_foreign = max(foreign.items(), key=lambda kv: kv[1]["score"]) if foreign else (None, {"hits": [], "score": 0})
    tf_fam, tf = top_foreign

    if home_score == 0:
        if foreign_venue or (tf["score"] >= FOREIGN_MIN) or foreign_exp:
            reasons = []
            if foreign_venue:
                reasons.append(f"venue '{venue.strip() or doi_slug}' belongs to {venue_fam}")
            if tf["score"] >= FOREIGN_MIN:
                reasons.append(f"{tf['score']} weighted {tf_fam} terms ({', '.join(tf['hits'][:8])})")
            if foreign_exp:
                reasons.append("abbreviation expands in a foreign discipline: "
                               + "; ".join(f"{a} -> {v[0]}" for a, v in list(foreign_exp.items())[:2]))
            return {"key": entry["key"], "classification": "off_topic",
                    "reason_code": "citation_off_domain",
                    "home_family": fam, "home_score": 0,
                    "foreign_family": venue_fam or tf_fam,
                    "detail": "; ".join(reasons), "title": title}
        return {"key": entry["key"], "classification": "uncertain",
                "reason_code": "citation_relevance_uncertain",
                "home_family": fam, "home_score": 0,
                "foreign_family": tf_fam,
                "detail": "no declared-domain vocabulary and no dominant foreign signal; "
                          "manual relevance check advised (interdisciplinary citations are legal)",
                "title": title}

    # home evidence exists; a strongly foreign venue or expansion alongside it
    # is a disclosure, not a failure (e.g. a statistics method in an ML venue)
    if foreign_venue or foreign_exp:
        which = (f"venue in {venue_fam}" if foreign_venue else "")
        if foreign_exp:
            which += ("; " if which else "") + "foreign abbreviation expansion present"
        return {"key": entry["key"], "classification": "uncertain",
                "reason_code": "citation_cross_domain_disclosure",
                "home_family": fam, "home_score": home_score,
                "foreign_family": venue_fam,
                "detail": f"home-domain evidence ({', '.join(home_hits[:6])}) coexists with {which}",
                "title": title}
    return {"key": entry["key"], "classification": "relevant",
            "reason_code": "ok", "home_family": fam, "home_score": home_score,
            "foreign_family": None,
            "detail": f"home evidence: {', '.join(home_hits[:8])}", "title": title}


def check(ws: Path) -> tuple[str, dict]:
    sig_path = ws / ".sciforge" / "refine-logs" / "domain-signature.json"
    bib_path = ws / "literature" / "references.bib"
    if not sig_path.is_file():
        return "SKIP", {"note": "domain-signature.json absent (run predates Phase 1b); "
                                "no declared domain to check relevance against"}
    try:
        signature = json.loads(sig_path.read_text(errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        return "SKIP", {"note": f"domain-signature.json unreadable: {exc}"}
    if not isinstance(signature, dict):
        return "SKIP", {"note": "domain-signature.json is not an object"}
    if not bib_path.is_file():
        return "SKIP", {"note": "no references.bib yet"}
    entries = parse_bib(bib_path.read_text(errors="replace"))
    if not entries:
        return "SKIP", {"note": "empty bibliography"}

    extras: dict[str, dict] = {}
    vp = ws / "literature" / "verified_papers.json"
    if vp.is_file():
        try:
            papers = json.loads(vp.read_text(errors="replace"))
            if isinstance(papers, list):
                for p in papers:
                    if isinstance(p, dict) and p.get("key"):
                        extras[p["key"]] = p
        except (OSError, json.JSONDecodeError):
            pass

    rows = [classify(e, signature, extras.get(e["key"])) for e in entries]
    off = [r for r in rows if r["classification"] == "off_topic"]
    unc = [r for r in rows if r["classification"] == "uncertain"]
    status = "FAIL" if off else ("WARN" if unc else "PASS")
    return status, {
        "entries": len(rows),
        "relevant": len(rows) - len(off) - len(unc),
        "off_topic": len(off),
        "uncertain": len(unc),
        "home_family": home_family(signature),
        "primary_domain": (signature.get("domain_profile") or {}).get("primary_domain"),
        "findings": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write-verdict", action="store_true")
    args = ap.parse_args()
    status, report = check(args.workspace)
    if args.write_verdict:
        vd = args.workspace / ".sciforge" / "verdicts"
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "CITATION_RELEVANCE.json").write_text(json.dumps(
            {"schema_version": "1.0", "gate": "citation_relevance",
             "status": status, **report}, indent=2, ensure_ascii=False))
    if args.json:
        print(json.dumps({"status": status, **report}, indent=2, ensure_ascii=False))
    else:
        if status == "SKIP":
            print(f"citation_relevance SKIP: {report.get('note')}")
        else:
            print(f"citation_relevance {status}: {report['entries']} entries, "
                  f"{report['relevant']} relevant, {report['uncertain']} uncertain, "
                  f"{report['off_topic']} off-topic "
                  f"(domain={report['primary_domain']}, family={report['home_family']})")
            for r in report["findings"]:
                if r["classification"] != "relevant":
                    print(f"  - {r['key']} [{r['classification']}] {r['reason_code']}: {r['detail']}")
    return 2 if status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
