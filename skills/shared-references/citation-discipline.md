# Citation Discipline (SciForge-OSS — Condensed)

> **Core**: Every citation must pass multi-layer anti-hallucination verification: arXiv existence + CrossRef DOI/metadata are mandatory, Semantic Scholar fuzzy matching is Layer 3 and runs whenever reachable, and any missing layer is disclosed. No paper is ever fabricated from memory.

## Multi-Layer Anti-Hallucination Verification Protocol (arXiv + CrossRef mandatory, Semantic Scholar Layer 3 when reachable)

### Layer 1: arXiv Batch Verification (required)
- Collect arXiv IDs and query `http://export.arxiv.org/api/query` in batches of 40
- Verify that the title, authors, abstract, and category match
- Status: `verified` / `unverified` / `error`

### Layer 2: CrossRef DOI Verification (required)
- For papers with a DOI, query `https://api.crossref.org/works/{doi}`
- Verify that the DOI resolves, the title matches, and at least one author matches
- Status: `verified` / `unverified` / `error`

### Layer 3: Semantic Scholar Fuzzy Matching (when reachable)
- Query `https://api.semanticscholar.org/graph/v1/paper/search?query={title}`
- Verify that the title, authors, and year match
- Status: `verified` / `unverified` / `error`
- **Credentials**: when `SEMANTIC_SCHOLAR_API_KEY` or `S2_API_KEY` is set, send it as the `x-api-key` header on every Semantic Scholar request (an authenticated quota is the documented cure for 429s)
- **Retry budget**: 3 attempts with backoff; a persistent 429 is `unavailable_rate_limited`, a timeout/DNS/5xx is `unavailable_network`

## Verification Depth and Degraded Mode (v1.7.4 — disclosure is mandatory)

The two mandatory layers (arXiv existence + CrossRef DOI/metadata) already block fabricated references, the dominant threat. Layer 3 adds fuzzy title matching plus venue/citation-count cross-checks. When Layer 3 cannot run, the audit **degrades to two layers and records exactly that** — the audit is not "unverified", and it is never reported as 3-layer.

The **three audit axes** (EXISTENCE / METADATA / CONTEXT, see `/citation-audit`) always run and are a different concept from these **retrieval layers**; only Layer 3 of the retrieval chain can degrade.

Every run MUST write this telemetry into `CITATION_AUDIT.json`:

| Field | Allowed values | Meaning |
|-------|----------------|---------|
| `verification_depth` | `3-layer` / `2-layer-degraded` / `not_attempted` | Depth actually achieved |
| `layers_verified` | subset of `["arxiv", "crossref", "semantic_scholar"]` | Layers that actually executed |
| `layer3_status` | `verified` / `not_required` / `unavailable_rate_limited` / `unavailable_network` / `unavailable_no_credentials` / `unavailable_error` / `not_attempted` | Layer 3 outcome and, when unavailable, why |
| `layer3_detail` | free string | Raw cause (e.g. `HTTP 429 ... after 3 attempts`) so the disclosure itself is auditable |

- **Never fabricate the audit record.** Writing `verification_depth: "3-layer"` or `layer3_status: "verified"` when Layer 3 did not run is worse than a citation error — it is a falsified audit and MUST be treated as `FAIL`.
- **Recovery is mandatory.** When Semantic Scholar becomes reachable again (API key configured, rate limit lifted), re-run Layer 3 for entries verified in degraded mode, upgrade `verification_depth` to `3-layer`, and clear the disclosure.

## Final Verification Checklist

- Every citation uses `\cite{key}`, and the key exists in `references.bib`
- Every citation passes the two mandatory layers (arXiv existence + CrossRef DOI/metadata); Layer 3 (Semantic Scholar fuzzy match) runs whenever reachable, and any degradation is disclosed in `CITATION_AUDIT.json`
- No `\cite{TODO}`, `\cite{forthcoming}`, or `\cite{arxiv:TODO}`
- Every citation is actually cited in the body text (no orphan citations)
- BibTeX entries are generated from verified sources, never hand-written

## BibTeX Management Rules

- BibTeX is generated automatically from arXiv/CrossRef (plus Semantic Scholar when reachable), never hand-written
- Every entry includes the `verification_status: verified` tag
- The same paper uses a unified key with no duplicates
- Entries that cannot be verified are not included

## Common Template

```
@article{key,
  author    = {Author, A. and Author, B.},
  title     = {Title},
  journal   = {Journal},
  year      = {2024},
  volume    = {N},
  pages     = {X--Y},
  doi       = {10.xxx/xxxxx},
  verification_status = {verified}
}
```

## Quick Reference

- **Multi-layer verification**: arXiv existence + CrossRef DOI/metadata (mandatory) → Semantic Scholar fuzzy matching (Layer 3, when reachable; 2-layer degraded mode disclosed in `CITATION_AUDIT.json`)
- **Forbidden**: `\cite{TODO}`, `\cite{forthcoming}`, hand-written BibTeX
- **Mandatory**: every citation passes the two mandatory layers; a missing Layer 3 is disclosed, never fabricated
- **Output**: `literature/references.bib` + `VERIFICATION_LOG.md`
