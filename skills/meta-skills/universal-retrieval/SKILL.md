---
name: universal-retrieval
version: 1.2.1
description: "Literature search + 3-layer anti-hallucination citation verification (arXiv→CrossRef→Semantic Scholar) + v3.2 proxy auto-mount + filter-chain integrity audit. Phase 4 (MANDATORY, never skipped). Invoke for any literature/citation work."
type: reference-skill
role: academic-retriever
---

# Meta-Skill: Universal Academic Retrieval

## Quick Reference

- **Purpose**: Multi-source academic search + 3-layer anti-hallucination citation verification
- **Input**: Search query
- **Output**: references.bib + landscape_report.md + VERIFICATION_LOG.md
- **Key**: 6 sources (arXiv→S2→CrossRef→PubMed→Web→OpenAlex); every citation must pass verification

## Use When

Use this skill whenever the AI scientist needs to find, verify, or retrieve real academic references for any scientific question — regardless of discipline.

Typical prompts:
- "Find references on this topic"
- "search for papers on quantum entanglement"
- "find recent work on this topic"
- "verify if this paper exists"
- "get the DOI for this reference"

This is the **anti-hallucination** meta-skill: every citation in the final output must have a real, verifiable academic source. No paper is ever fabricated from memory.

## Job

Provide a unified multi-source academic search interface that routes queries to the most suitable databases, verifies every candidate paper via real APIs, and returns structured, citable results.

**The skill does not interpret paper content — it only retrieves, verifies, and formats metadata.**

Non-negotiable goals:
1. **Every paper in the output carries a real-existence verification tag** — no paper is included on faith
2. **No paper is silently dropped** — every candidate paper is either verified or explicitly marked unverifiable
3. **The 3-layer anti-hallucination protocol is mandatory** — arXiv batch check → CrossRef DOI → Semantic Scholar fuzzy match
4. **Every citation carries a verifiable DOI or arXiv ID** — no "forthcoming"/"submitted" entries without verification

## Data Sources

Search in priority order. All sources are optional — if a source is unavailable, skip it silently and continue to the next.

| Priority | Source | Provides | Coverage |
|--------|----|---------|---------|
| 1 | **arXiv API** | Preprint metadata (title, abstract, authors, categories, PDF URL) | All STEM fields, fastest updates |
| 2 | **Semantic Scholar API** | Published papers, citation counts, venue, TLDR | Broad CS + science, best for impact |
| 3 | **CrossRef API** | DOI resolution, journal metadata, author names | All published journals |
| 4 | **PubMed API** | Biomedical literature | Biology, medicine, neuroscience |
| 5 | **Web Search** | General web + Google Scholar | Anything not covered by the APIs above |
| 6 | **OpenAlex API** | Open scholarly graph, author disambiguation | All disciplines, best for citation networks |

## 3-Layer Anti-Hallucination Verification Protocol

Every candidate paper **must** pass the layers below before entering the final report:

### Layer 1: arXiv Batch Verification
- Collect the arXiv IDs of all candidate papers
- Query `http://export.arxiv.org/api/query` in batches of 40 IDs
- Verify: title, authors, abstract, categories are consistent
- Status: `verified` / `unverified` / `error`

### Layer 2: CrossRef DOI Verification
- For papers with a DOI, query `https://api.crossref.org/works/{doi}`
- Verify: DOI resolves, title matches, at least one author matches
- Status: `verified` / `unverified` / `error`

### Layer 3: Semantic Scholar Fuzzy Match
- For papers not verified by Layers 1-2, query the Semantic Scholar API by title
- Use fuzzy matching (threshold ≥ 0.6)
- Verify: at least 2 metadata fields match (authors, year, venue, title)
- Status: `verified` / `unverified` / `error`

### Final Verdict
- `PASS` — passes at least 2 of the 3 layers
- `WARN` — passes 1 layer, or partial match in 2 layers
- `BLOCKED` — passes 0 layers, or fatal mismatch
- `ERROR` — API failure, cannot determine

## OSS Single-Activity-Bar Strategy (upgrade supplement)

OSS is discipline-agnostic and real research problems span 10+ fields, so **source priorities must not be hard-switched by discipline** (the main repo SciForge has different source priorities + citation windows for 4 disciplines; OSS does not). OSS uses **unified priority** (arXiv → S2 → CrossRef → PubMed → Web → OpenAlex, see table above) and applies the same parameter set to all problems:

- **Unified citation window** `min_year=2020` (the main repo uses 6/12/18-month windows varying by discipline; OSS uses a unified absolute year)
- **Recency hard gate (v5.0 — prevents "stale literature")**: **papers from the last 2 years must be ≥ 40%** of retrieved results (`recency_ratio` written to `landscape_report.md` and to verification output `time_span.recency_ratio`). If below → WARN + **automatically trigger one re-retrieval with a narrower window** (`min_year = current year - 2`, merged and deduplicated with original results); if still <40% after re-retrieval and the direction is active → mark `recency_gap` and report to the caller (this signal is consumed by the `/novelty-check` collision audit). Exception: classical/foundational fields (e.g., classical-theorem textual research in pure mathematics) may tolerate low recency, but the reason must be stated in the report
- **Unified source priority** (priority 1-6 in the table above, no discipline switching)
- **Unified retrieval count** `max_papers=30` (the main repo varies by discipline; OSS is unified)
- **Unified verification level** `verification_level=full` (the 3-layer anti-hallucination protocol is mandatory; no discipline downgrade path)

**OSS has no `discipline-context` source-priority override** — see the OSS one-line contract in [`discipline-context.md`](../../shared-references/discipline-context.md): all problems uniformly use the `general` row, i.e., the unified priority above. If you encounter legacy code migrated from the main repo that references `DISCIPLINE_CONTEXT.source_priorities`, **delete that branch** — OSS has no such discipline-switching logic.

## Network Proxy Contract (v2.2 — mihomo mandatory)

**Literature search is never skipped** (see [`auto-pipeline/SKILL.md`](../../orchestrator/auto-pipeline/SKILL.md) Phase 4 v2.2: it must run even for theory-only, to avoid duplicate proofs). To reach arxiv/S2/crossref/pubmed/openalex, this skill goes through the **mihomo proxy**:

| Setting | Value | Notes |
|------|-----|------|
| Proxy address | `http://127.0.0.1:8099` (default; auto-probed at startup, see "Proxy Auto-Detection" below) | mihomo mixed port (HTTP + SOCKS5); fall back through the candidate sequence if probing fails |
| Mode | `rule` (rule mode) | Default rule mode; CN domains go direct, external traffic goes through the proxy |
| How to enable | Set `http_proxy`/`https_proxy` environment variables on all HTTP requests OR pass `proxies={"http": "...", "https": "..."}` explicitly in the request library | Supported by both Python `urllib`/`requests` |
| Failure fallback | If the proxy times out, retry the single query in the background via `nohup` (long tasks run in background, foreground continues with other sources) | Follow [`background-dispatch-protocol.md`](../../shared-references/background-dispatch-protocol.md) |

**Hard rule**: all external API calls (arxiv export, S2 graph, crossref works, pubmed eutils, openalex) **must go through the proxy**. No direct external connections (direct arxiv/s2/crossref connections time out in CN environments). The proxy routes automatically via mihomo rule mode — academic API domains go through the proxy, CN domains go direct.

### Proxy Auto-Detection (auto-mount — user hard requirement: detect and mount autonomously, never skip due to network)

This skill **does not assume a fixed proxy port**; at startup it autonomously probes and mounts the proxy per the protocol below (even though mihomo defaults to `8099`, reachability must be tested live — never assumed from config):

1. **Explicit config first**: if the environment variables `http_proxy`/`https_proxy`/`ALL_PROXY` are already set, or `literature/.proxy-resolved.json` exists with `detected_at` < 1h old, use it directly and skip probing.
2. **Candidate port probing** (in priority order, try one by one until the first reachable): `8099` (mihomo mixed-port default) → `7890` (Clash legacy HTTP) → `7892` (Clash SOCKS) → `1080` → `8080`.
3. **Probing method**: for each candidate `http://127.0.0.1:<port>`, issue a TCP connection probe with `python3` (`socket.connect_ex(('127.0.0.1',<port>)`, `timeout=2s`, return 0 means reachable); after TCP succeeds, send one GET to `http://export.arxiv.org/` via that proxy (`timeout=3s`, expect 2xx/3xx) to confirm the proxy really forwards external traffic. The first candidate passing both checks is selected.
4. **Mount**: once selected, write `literature/.proxy-resolved.json`:
   ```json
   {"proxy":"http://127.0.0.1:<port>","port":<port>,"detected_at":"<ISO8601>","probed":["8099","7890","7892","1080","8080"],"method":"tcp+http","tcp_ok":true,"http_forward_ok":true}
   ```
   and set `http_proxy`/`https_proxy` to that address for all subsequent requests (`requests`: pass `proxies={"http":...,"https":...}`; `urllib`: use `ProxyHandler`).
5. **All candidates unreachable** → **never give up, never skip Phase 4**: (a) first try direct connection once (`timeout=10s`); (b) if direct also fails → enable `nohup` background retries for that source (see "Network Timeout Handling"), record `source_status: proxy_unavailable` in `VERIFICATION_LOG.md`, downgrade the overall Phase 4 verdict to `WARN` (degrade to searching available sources) — **Phase 4 itself is never downgraded to `SKIP`/`NOT_APPLICABLE`/`BLOCKED`-by-network**.
6. **Re-probing**: if a mounted proxy times out 2 consecutive times during requests, delete `.proxy-resolved.json` and return to step 2 to re-probe (mihomo may have restarted on a different port).

**Strictly forbidden**: skipping any of literature search, filter-chain integrity audit, or dataset downloads due to network problems. Network issues may only downgrade the verdict from `PASS` to `WARN` — never to `SKIP`/`NOT_APPLICABLE`/`BLOCKED` for network reasons.

**Network timeout handling** (user requirement: if timeouts persist even with the VPN up, download in the background via nohup first and work on other things in parallel):
1. Set `timeout=30s` on each API request; on timeout, retry once (a different endpoint).
2. If a whole batch (e.g., the arxiv 40-ID batch) times out, run that batch query in the background via `nohup`, writing results to `literature/.pending/`, and continue with other sources (S2/crossref/pubmed) in the foreground.
3. Collect the background query results at Phase 10 (result-to-claim) or Phase 15 (citation-audit).
4. If a source is unavailable throughout (even via proxy), record `source_status: unavailable` in `VERIFICATION_LOG.md` and **do not skip Phase 4** — degrade to searching available sources + WARN.

## Filter-Chain Integrity Audit (v2.2 — real + complete)

After literature search completes and before entering Phase 5, the **filter-chain integrity audit** must pass — verifying that the filtered citations are both "real" and "complete":

### Authenticity check (every citation is real)
- Every `references.bib` entry passes at least 1 of the 3 verification layers (arxiv/s2/crossref) — see the 3-layer protocol above
- No `\cite{TODO}`, `\cite{forthcoming}`, or hand-written BibTeX (except special handling for books/technical reports)
- `VERIFICATION_LOG.md` records the verification status + layers passed for each entry

### Completeness check (coverage is complete)
- **Core claim coverage**: every core claim of the idea in `FINAL_PROPOSAL.md` is supported by at least 1 citation OR marked `[needs-citation]` for human follow-up
- **No orphan citations**: every key in `references.bib` appears in the body text `\cite{}` at least once (and vice versa — no `\cite` points to a nonexistent key)
- **Sub-direction coverage**: if `landscape_report.md` identifies N research sub-directions, at least N-1 must have citation coverage (one "gap" is allowed as this work's contribution)
- **Time coverage**: citations must not all concentrate in a single year (if all fall in one year, WARN — classic literature may be missing)

### Verification output
The filter-chain integrity audit writes to `literature/FILTER_CHAIN_AUDIT.json`:
```json
{
  "audit_verdict": "PASS | WARN | FAIL",
  "authenticity": {"verified_count": N, "unverified_count": M, "details": [...]},
  "coverage": {
    "core_claims_covered": X,
    "core_claims_uncovered": Y,
    "orphan_citations": Z,
    "orphan_refs": W,
    "subdirections_covered": K,
    "subdirections_total": T,
    "time_span": {"min_year": ..., "max_year": ..., "concentration_warn": bool}
  },
  "unavailable_sources": ["arxiv" | "s2" | ...],
  "recommendation": "PROCEED | NEEDS_HUMAN_LIT_supplement | BLOCKED"
}
```

- `PASS` → Phase 5 proceeds
- `WARN` → Phase 5 proceeds, but the `NEEDS_HUMAN_LIT_supplement` flag is passed to `PIPELINE_STATUS.json` (human supplements the literature later)
- `FAIL` (no core claim covered OR all citations unverified) → fall back to Phase 4 re-search (up to 3 rounds)

## Configuration

| Parameter | Type | Default | Description |
|------|------|------|------|
| `sources` | list | `["arxiv", "semantic_scholar", "crossref", "pubmed", "web", "openalex"]` | Which sources to search — OSS defaults to all 6 sources (the main repo defaults to 4; OpenAlex was added in a main-repo upgrade; OSS already includes it) |
| `max_papers` | int | `30` | Maximum papers in the final output (OSS unified, does not vary by discipline) |
| `min_year` | int | `2020` | Earliest publication year considered (OSS unified absolute year, not discipline-specific citation windows) |
| `verification_level` | enum | `full` | `full` (3 layers, OSS mandatory default), `quick` (arXiv only), `none` (no verification, **not recommended in OSS** — breaks the downstream `/citation-audit` 3-layer contract) |

## Steps

### Step 1: Parse the Search Query

Extract from the request:
1. **Research topic** — the core scientific question or field
2. **Sub-topics** — specific aspects to explore
3. **Time range** — how recent the papers should be
4. **Type** — survey, original research, methodology, dataset
5. **Constraints** — specific authors, venues, or methods to include/exclude

### Step 2: Multi-Source Search

Execute searches in priority order:
1. arXiv API — structured query with category filters
2. Semantic Scholar — filtered by research field
3. CrossRef — DOI-based metadata query
4. Web Search — topics not covered by the academic APIs

Deduplicate by arXiv ID or DOI.

### Step 3: 3-Layer Verification

Run the 3-layer verification protocol on every candidate paper:
1. If it has an arXiv ID → Layer 1 (arXiv)
2. If it has a DOI → Layer 2 (CrossRef)
3. If still unverified → Layer 3 (Semantic Scholar)
4. Compute the final verdict

**Special handling:**
- Books: verify via CrossRef ISBN query
- Technical reports: verify via web search + institutional repositories
- Conference papers: verify via Semantic Scholar venue filters

### Step 4: Synthesize the Survey Report

Organize verified papers into a structured survey:
1. **Sub-direction clustering** — group by research sub-field
2. **Methodology families** — group by method (theory, experiment, simulation)
3. **Timeline map** — how the field evolved over time
4. **Gap identification** — which questions remain unanswered

### Step 5: Generate Citation Artifacts

For each verified paper:
1. Generate the BibTeX entry → `literature/references.bib`
2. Generate structured JSON → `literature/verified_papers.json`
3. Write the verification status → `literature/VERIFICATION_LOG.md`

## Output Artifacts

- `literature/landscape_report.md` — structured survey report
- `literature/references.bib` — BibTeX for all verified papers
- `literature/verified_papers.json` — structured metadata
- `literature/VERIFICATION_LOG.md` — verification status per paper
- `literature/unverified_papers.json` — papers that failed verification (with reasons)

## Downstream Skill Invocation

- `/theory-derivation` — after the literature survey, guide derivations with the citations found
- `/paper-writing` — literature artifacts feed directly into paper writing

## Shared Contract References

- [citation-discipline](../../shared-references/citation-discipline.md) — 3-layer anti-hallucination verification protocol
- [discipline-context](../../shared-references/discipline-context.md) — discipline-aware search routing
- [output-manifest](../../shared-references/output-manifest.md) — artifact structure contract
