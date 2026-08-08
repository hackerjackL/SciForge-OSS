# Citation Discipline (SciForge-OSS — Condensed)

> **Core**: Every citation must pass 3 layers of anti-hallucination verification. No paper is ever fabricated from memory.

## 3-Layer Anti-Hallucination Verification Protocol

### Layer 1: arXiv Batch Verification
- Collect arXiv IDs and query `http://export.arxiv.org/api/query` in batches of 40
- Verify that the title, authors, abstract, and category match
- Status: `verified` / `unverified` / `error`

### Layer 2: CrossRef DOI Verification
- For papers with a DOI, query `https://api.crossref.org/works/{doi}`
- Verify that the DOI resolves, the title matches, and at least one author matches
- Status: `verified` / `unverified` / `error`

### Layer 3: Semantic Scholar Fuzzy Matching
- Query `https://api.semanticscholar.org/graph/v1/paper/search?query={title}`
- Verify that the title, authors, and year match
- Status: `verified` / `unverified` / `error`

## Final Verification Checklist

- Every citation uses `\cite{key}`, and the key exists in `references.bib`
- Every citation passes at least 1 layer of verification (preferably all 3 layers)
- No `\cite{TODO}`, `\cite{forthcoming}`, or `\cite{arxiv:TODO}`
- Every citation is actually cited in the body text (no orphan citations)
- BibTeX entries are generated from verified sources, never hand-written

## BibTeX Management Rules

- BibTeX is generated automatically from arXiv/CrossRef/S2, never hand-written
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

- **3-layer verification**: arXiv → CrossRef → Semantic Scholar
- **Forbidden**: `\cite{TODO}`, `\cite{forthcoming}`, hand-written BibTeX
- **Mandatory**: every citation passes at least 1 layer of verification
- **Output**: `literature/references.bib` + `VERIFICATION_LOG.md`
