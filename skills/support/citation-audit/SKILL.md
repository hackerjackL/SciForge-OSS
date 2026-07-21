---
name: citation-audit
type: reference-skill
role: bibliographic-integrity-auditor
---

# Citation Audit

## Quick Reference

- **Purpose**: 最终 3 层引用防幻觉验证 (arXiv→CrossRef→Semantic Scholar)
- **Input**: paper/main.tex + literature/references.bib
- **Output**: CITATION_AUDIT.md + CITATION_AUDIT.json
- **Key**: 每篇 \cite{key} 必须可解析至已验证的 .bib 条目

Verify every `\cite{...}` in a paper against three independent layers: existence, metadata correctness, and context appropriateness. This is the bibliographic-integrity layer of SciForge's evidence-and-claim assurance stack.

## Use When

Run **before submission**, after `paper-write` has produced the LaTeX draft and bib file, and after `paper-claim-audit` has verified numerical claims.

Typical prompts:

- "审查引用"
- "check citations"
- "citation audit"
- "verify references"
- "引用核对"

**Do not** run this on a half-written draft — most of the work is cross-checking each `\cite` against context, which is wasted on placeholder text.

## Job

For every cited bibliographic entry, invoke a fresh cross-model reviewer with web/DBLP/arXiv/EconLit/RePEc lookup to verify (1) the cited paper actually exists at the claimed arXiv ID / DOI / NBER number / venue, (2) author names / year / venue / title match canonical sources, and (3) the cited paper actually supports the claim it is being used to support. The non-negotiable goal: catch hallucinated authors, wrong years, fabricated venues, version mismatches, and — most dangerously — wrong-context citations where a real paper is cited to support a claim it does not actually establish.

## What This Skill Catches

The dangerous citation problems are **not** wildly fake citations — those are easy to spot. The dangerous ones are:

- **Wrong-context citations**: real paper, but the cited claim is not what that paper actually establishes (e.g., citing Self-Refine to support "self-feedback produces correlated errors" — Self-Refine actually argues the opposite).
- **Author hallucinations**: anonymous-author placeholders that slipped through, missing co-authors, wrong order.
- **Title drift**: arXiv v1 vs v3 with different titles silently merged.
- **Venue confusion**: arXiv preprint cited but the official venue is now CVPR/ICML/NeurIPS — using the wrong record.
- **Year mismatch**: arXiv 2023 preprint with 2024 conference acceptance, year reported inconsistently.
- **Phantom DOIs**: DOI looks real but does not resolve.
- **Self-citation drift**: your own prior work cited with year off by one.

**Economics-specific failure modes** (when target venue is AER / QJE / JPE / Econometrica / RES / JFE / JF / NBER or the paper cites economics literature):

- **NBER working paper vs published version**: an NBER working paper (nber.org/papers/wXXXXX) was later published in AER / QJE / JPE / Econometrica / RES — citing the working paper when the published version exists is a common reviewer flag. Rule: prefer the published version; cite the NBER number only when no published version exists or when the working paper's content differs materially from the published version (different sample, different specifications).
- **Econometrica / RES title drift**: the working paper title differs from the final published title (often subtitled "A Reappraisal" or with a colon clause added). Rule: use the published title; flag the working-paper title as `metadata_drift`.
- **AER P&P vs AER main**: American Economic Review Papers & Proceedings (P&P) is a separate, non-peer-reviewed venue from the main AER. Citing an AER P&P paper as if it were a mainline AER article is a severity-3 metadata error. Rule: distinguish `American Economic Review (Papers and Proceedings)` from `American Economic Review` in the venue field.
- **Journal of Finance / JFE / RFS citation style**: finance journals use `\citet` / `\citeauthor` heavily with explicit year; mismatched author-year pairs (e.g., "Fama and French (1993)" citing `fama_french_2015_five_factor`) are common. Rule: verify the author-year pair in prose matches the bib entry.
- **RePEc vs DBLP mismatch**: economics papers indexed in RePEc (ideas.repec.org) often have richer metadata than DBLP; when DBLP returns incomplete entries for economics papers, the reviewer should fall back to RePEc / EconLit / JSTOR.
- **EconLit / JSTOR canonical venue**: for older economics papers (pre-2000), DBLP coverage is thin; EconLit and JSTOR are the canonical sources. Rule: when DBLP returns no result for an economics paper, do not mark it as hallucinated — fall back to EconLit / JSTOR / publisher site before emitting REMOVE.
- **Working paper series citation**: SSRN / NBER / CEPR / IZA / WBER working paper series each have their own numbering; mixing SSRN ID with NBER number in the same bib entry is a metadata error.

## Configuration

- **CONTEXT_POLICY** = `fresh` — each audit run uses a new reviewer thread. Never reuse prior audit context.
- **WEB_SEARCH** = required — the reviewer must perform real web/DBLP/arXiv lookups, not pattern-match from memory.
- **OUTPUT** = `CITATION_AUDIT.md` — human-readable per-entry verdict report.
- **STATE** = `CITATION_AUDIT.json` — machine-readable verdict ledger consumable by downstream tools.
- **SOFT_ONLY** = `false` — when true (set via the `soft-only` flag), the audit runs all three layers normally but **forbids any `.bib` file mutation**. Findings that would otherwise mutate the bib (FIX / REPLACE / REMOVE) are translated into per-occurrence sentence-rewrite proposals against the citing `*.tex` files. Used by `/resubmit-pipeline` Phase 1 to honor the user's hard "freeze the bib" constraint.
- **RENDER_HTML** = `true` (default) — auto-render `CITATION_AUDIT.md` to HTML after writing the report. Full review gate applies (audit-class artifact). Set `false` to skip.
- **ECON_VENUES** (optional, default: empty) — explicit allowlist of economics venues the paper targets, in canonical form. When non-empty, enables the economics-specific failure modes (NBER-vs-published, AER P&P vs main, etc.) and triggers the EconLit / RePEc / JSTOR fallback chain when DBLP returns no result. Auto-detected from the paper's `\journal{}` field or `AGENT_DOC.md` when not set explicitly. Canonical keys: `AER`, `AER_PP`, `QJE`, `JPE`, `ECONOMETRICA`, `RES`, `RESTUD`, `JFE`, `JF`, `RFS`, `NBER`, `SSRN`, `CEPR`, `IZA`.
- **PREFER_PUBLISHED_OVER_WORKING_PAPER** (default: `true`) — when both an NBER / SSRN working paper and a published version exist, emit a `FIX` verdict pointing to the published version. Set to `false` only when the user explicitly wants to cite the working paper (e.g., for the working paper's unique content).

> **OSS discipline-agnostic note**: OSS has no per-discipline venue allowlists (no `CS_VENUES` / `PHYSICS_VENUES` / `ECON_VENUES`). The reviewer's per-axis logic (existence / metadata / context) is applied universally — the canonical venue map and fallback bibliography are loaded from `universal-retrieval`'s default OpenAlex/arXiv/CrossRef sources, NOT discipline-specific. See [`shared-references/discipline-context.md`](../../shared-references/discipline-context.md) for the OSS single-row (`general`) discipline contract.

## Workflow

### Step 1: Discover Bib File and Section Files

Locate:

- `references.bib` (or `paper.bib` / similar) under the paper directory
- All `*.tex` files containing `\cite{...}` calls (typically `sec/` or `sections/`)

If multiple bib files exist, audit each separately.

### Step 2: Extract All (cite-key, context) Pairs

For each `\cite{key1,key2,...}` invocation in the paper:

- Record the cite key
- Record the file + line number
- Record the surrounding sentence (≥ 1 full sentence around the cite, for context check)

Output a flat list of `(key, file, line, surrounding_sentence)` tuples. Also build the inverse: for each bib entry, the list of all places it is cited.

Define two protocol sets used throughout the rest of the workflow: `cited_keys` is the set of unique cite keys appearing in any `\cite{...}` invocation across the audited `*.tex` files (de-duplicated), and `bib_keys` is the set of keys parsed from the audited bib file(s). `cited_keys` drives Step 3 (audit only cited entries); `bib_keys \ cited_keys` is the uncited residual surfaced by the `--uncited` opt-in.

### Step 3: Send Each Entry to Fresh Cross-Model Reviewer

For each **cited** bib entry — i.e., each key in `cited_keys` with at least one extracted citation context — invoke a fresh reviewer thread (per-entry, or batch with explicit per-entry isolation). Do **not** send entries in `bib_keys \ cited_keys` to the reviewer; those are detect-only and surface only when `--uncited` is explicitly enabled.

The reviewer prompt structure:

- Role: auditing a bibliographic entry, using web/DBLP/arXiv/EconLit/RePEc search
- Inputs: the bib entry, plus all extracted contexts where this entry is cited, plus the target venue (so the reviewer knows whether economics-specific canonicalization applies)
- Verify three axes:
  1. **EXISTENCE**: does this paper exist at the claimed arXiv ID / DOI / NBER number / venue? Output: YES / NO / UNCERTAIN, with the verifying URL. For economics papers, search DBLP first; if no result, fall back to RePEc (ideas.repec.org), EconLit, JSTOR, or the publisher site (AEI / JSTOR / Wiley / Elsevier / Springer) before emitting NO.
  2. **METADATA**: are author names, year, venue, title correct? For each, output: correct / wrong: should be ... / typo: ...
     - **Venue canonicalization (economics venues)**: when the target venue is in the economics set, the reviewer MUST normalize the venue field to the canonical form before comparison. Canonical map:
       - `AER` → `American Economic Review`
       - `AER_PP` → `American Economic Review (Papers and Proceedings)` — distinct from mainline AER; never collapse the two
       - `QJE` → `Quarterly Journal of Economics`
       - `JPE` → `Journal of Political Economy`
       - `ECONOMETRICA` → `Econometrica`
       - `RES` / `RESTUD` → `Review of Economic Studies`
       - `JFE` → `Journal of Financial Economics`
       - `JF` → `Journal of Finance`
       - `RFS` → `Review of Financial Studies`
       - `NBER` → `NBER Working Paper Series` (with number `wXXXXX`)
       - `SSRN` → `SSRN Electronic Journal` (with SSRN ID)
       - `CEPR` → `CEPR Discussion Paper` (with number)
       - `IZA` → `IZA Discussion Paper` (with number)
     - **Working-paper-vs-published check**: if the entry is an NBER / SSRN / CEPR / IZA working paper, search for a published version in AER / QJE / JPE / Econometrica / RES / JFE / JF / RFS. If a published version exists and `PREFER_PUBLISHED_OVER_WORKING_PAPER = true`, emit `FIX` with `note: published version available at [venue] [year] [DOI]`.
     - **Author-year pair check (finance journals)**: when the bib entry is cited in prose as "Author1 and Author2 (YEAR)" or "Author1 et al. (YEAR)", verify the pair matches the bib entry. Mismatch (e.g., prose says "Fama and French (1993)" but bib entry is `fama_french_2015_five_factor`) → `FIX` with `note: author-year pair in prose does not match bib entry`.
  3. **CONTEXT**: for each use, does the cited paper actually support the surrounding claim? Output per-use: SUPPORTS / WEAK / WRONG, with one-sentence reasoning.
- Emit VERDICT: KEEP / FIX / REPLACE / REMOVE
  - `KEEP`: entry is clean, all uses are appropriate
  - `FIX`: metadata needs correction; uses are appropriate
  - `REPLACE`: cite is wrong-context, find a different paper that actually supports the claim
  - `REMOVE`: entry is hallucinated or unsupportable
- Be honest. If you cannot verify online, say UNCERTAIN; do not guess. For economics papers, DBLP coverage is thin pre-2000 — UNCERTAIN is acceptable when only DBLP returns no result and EconLit / JSTOR are also inaccessible.

Save traces per the review-tracing protocol.

### Step 4: Aggregate Verdicts

Build `CITATION_AUDIT.json` following the schema in "Submission Artifact Emission" below. Per-entry ledger data goes under `details.per_entry`. The top-level `verdict` is a single overall value (PASS / WARN / FAIL / NOT_APPLICABLE / BLOCKED / ERROR) derived from per-entry verdicts per the decision table; the top-level `summary` is a one-line human-readable string.

```json
{
  "details": {
    "total_entries": 29,
    "counts": { "KEEP": 11, "FIX": 14, "REPLACE": 3, "REMOVE": 1 },
    "per_entry": [
      {
        "key": "lu2024aiscientist",
        "verdict": "KEEP",
        "axis_failures": [],
        "uses": [
          {"file": "sections/1.intro.tex", "line": 11, "verdict": "SUPPORTS"},
          {"file": "sections/6.related.tex", "line": 8, "verdict": "SUPPORTS"}
        ]
      },
      {
        "key": "madaan2023selfrefine",
        "verdict": "FIX",
        "axis_failures": ["CONTEXT"],
        "uses": [
          {"file": "sections/2.overview.tex", "line": 42, "verdict": "WRONG", "note": "Self-Refine demonstrates iterative improvement, not correlated errors"},
          {"file": "sections/6.related.tex", "line": 13, "verdict": "SUPPORTS"}
        ]
      }
    ]
  }
}
```

### Step 5: Generate Human-Readable Report

Write `CITATION_AUDIT.md`:

```markdown
# Citation Audit Report

**Date**: 2026-04-19
**Bib file(s)**: references.bib
**Total entries**: 29

## Summary
| Verdict | Count |
|---------|------|
| KEEP    | 11   |
| FIX     | 14   |
| REPLACE | 3    |
| REMOVE  | 1    |

## Priority Fixes (CRITICAL — apply before submission)

### REMOVE: anon2025placeholder
- Author listed as "Anonymous" — canonical record exists with real authors and full title
- Title is incomplete
- ACTION: Replace key with the canonical citekey, update authors and title

### REPLACE-CONTEXT: example2023priorwork in sec/2.overview.tex:42
- Cited to support a specific technical claim
- The cited paper actually demonstrates a different (related but distinct) phenomenon
- ACTION: Rewrite the sentence; cite the prior work for what it actually establishes

[... continues for each entry ...]

## All-Clean Entries (no action needed)

[list of KEEP keys]
```

When `--uncited` is set, append a `## Uncited Entries (opt-in)` section after "All-Clean Entries".

### Step 6: Apply Fixes (Interactive)

For each FIX/REPLACE/REMOVE verdict, prompt the user:

```
Fix [key]?
  Change: <description of change>
  Files affected: references.bib + sec/X.tex:Y
[Apply / Skip / Defer]
```

If `AUTO_APPLY = true`, apply all FIX-level changes (metadata corrections only). REPLACE and REMOVE always require human approval — they involve content changes.

### Step 7: Recompile and Verify

Recompile the paper and confirm:

- No new `Citation undefined` warnings
- No `Reference undefined` warnings
- Page count unchanged or only minimally affected by metadata fixes

## Uncited Entry Detection (Opt-in)

**Default**: disabled. Existing users see no behavior change — only `\cite{...}` keys are audited, and bib entries with no `\cite` reference in the manuscript are silently ignored.

**Opt-in**: pass `--uncited` on invocation. The skill then performs a set-diff after Step 2 and reports bib entries that appear in any audited bib file(s) but are not cited anywhere in the paper. Detect-only — uncited entries are **not** sent to the cross-model reviewer, so there is no extra reviewer/web-lookup cost.

### Why opt-in

This skill's headline output is the three-axis audit on cited entries. Surfacing uncited bib entries by default would (a) change long-form output for every existing run, and (b) noise up the verdict for users who intentionally maintain a superset bib file (e.g., shared lab bib, in-progress section reorder where the cite has been removed but the entry intentionally retained). The flag preserves zero behavior change for existing callers.

### Effect when enabled

When `--uncited` is set:

- `CITATION_AUDIT.md` gains a `## Uncited Entries (opt-in)` section listing the keys with a one-line suggestion each: `prune` (entry is dead weight; recommend deleting) or `check` (entry might be intentional; flag for user review). Default suggestion is `prune`; only emit `check` when there is concrete local evidence (e.g., a TODO comment in a `.tex` file mentioning the key, or a recently removed `\cite` visible in `git diff`). Do not infer intent from the bib key string alone.
- `CITATION_AUDIT.json` `details` gains an `uncited_entries` array.
- The top-level `verdict` is **unchanged**: uncited entries do not upgrade or downgrade the PASS / WARN / FAIL / etc. classification.
- Verifier gates and downstream skills MUST NOT treat the presence of `uncited_entries` as a blocking signal.

### Fallback when bib enumeration fails

If `--uncited` is enabled but full bib-key enumeration fails:

- Do **not** alter the top-level `verdict`, `reason_code`, or `summary`.
- Emit `details.uncited_entries` as an empty array `[]`.
- Add `details.uncited_entries_status: "unavailable"` plus a one-line note explaining why.
- Verifier gates and downstream skills MUST treat `unavailable` the same as the field being absent: not blocking.

## Soft-Only Mode (Opt-in)

**Default**: disabled. The audit emits the standard `KEEP / FIX / REPLACE / REMOVE` per-entry verdicts and a downstream caller (or the `--apply` path of Step 6) is free to mutate the bib.

**Opt-in**: pass `soft-only` on invocation. This mode is designed for callers — notably `/resubmit-pipeline` Phase 1 — that operate under a **hard "freeze the bib" constraint**: if a citation is wrong-context, soften the surrounding sentence; do **not** change, add, or remove the cite itself.

### What soft-only changes

The audit semantics are **unchanged**: existence + metadata + context-appropriateness checks all run, the reviewer is still invoked once per cited entry, and the per-entry KEEP/FIX/REPLACE/REMOVE verdicts are still computed and emitted exactly as in default mode. Only the **action layer** changes — soft-only translates each base verdict into a text-rewrite proposal instead of a bib mutation.

### Verdict translation table

| Base verdict | Soft-only translation | Notes |
|---|---|---|
| `KEEP` | `keep_unchanged` | No action. Cite + sentence are both fine. |
| `FIX` (metadata wrong) | `keep_metadata_drift_acknowledged` | Bib stays as-is. Flag for human review at submission time. Append note: "metadata drift detected but not fixed under --soft-only". |
| `REPLACE` (wrong-context cite) | `soften_citing_sentence` | Per-occurrence sentence-rewrite proposal. For each `\cite{X}` in the body, locate the surrounding sentence and propose a softened version that does not claim what `X` actually establishes. |
| `REMOVE` (cite refers to nonexistent paper — i.e., hallucinated citation) | `drop_cite_in_body_only` | The bib entry is left untouched (per the `--soft-only` invariant), but **the inline `\cite{X}` references in the body MUST be removed and the surrounding sentence rewritten** so it no longer relies on a nonexistent paper. Two sub-strategies the rewriter may use: (a) drop the inline `\cite{X}` entirely and rephrase the sentence to remove the load-bearing claim, OR (b) re-attribute to a different in-bib source that genuinely supports the claim. **Never** leave a `\cite{X}` to a hallucinated paper in the body — that is a worse failure mode than removing the cite, because reviewers will check the reference and find nothing. |

### Hard guarantees under `soft-only`

- **No `.bib` file mutations under any circumstance.** Step 6 ("Apply fixes (interactive)") is bypassed for the bib file; only `*.tex` rewrite proposals are produced (and still require human approval before any text edit).
- If a downstream caller proposes a bib edit while `soft-only` is set, **refuse it**: emit a one-line refusal in the trace and continue to the next finding.
- The top-level `verdict` decision table is **unchanged**: a wrong-context cite still produces `FAIL` with `reason_code: wrong_context`. Soft-only does not silence the finding; it only constrains the action layer.
- `soft-only` composes with `--uncited`: both flags can be set together. Uncited entries remain detect-only and are not subject to soft-only translation (there is no citing sentence to soften).

## Submission Artifact Emission

This skill **always** writes `paper/CITATION_AUDIT.json`, regardless of caller or detector outcome. A paper with no `.bib` file or no `\cite{...}` usage emits verdict `NOT_APPLICABLE`; silent skip is forbidden. `paper-writing` Phase 6 and the verifier both rely on this artifact existing at a predictable path.

The artifact conforms to the schema in [`shared-references/assurance-contract.md`](../../shared-references/assurance-contract.md):

```json
{
  "audit_skill":      "citation-audit",
  "verdict":          "one of: PASS | WARN | FAIL | NOT_APPLICABLE | BLOCKED | ERROR",
  "reason_code":      "all_entries_keep | metadata_drift | wrong_context | hallucinated | working_paper_superseded | venue_canonicalization | ...",
  "summary":          "One-line human-readable verdict summary.",
  "audited_input_hashes": {
    "references.bib":             "sha256:...",
    "main.tex":                   "sha256:...",
    "sections/3.related.tex":     "sha256:..."
  },
  "trace_path":       ".sciforge/traces/citation-audit/<date>_run<NN>/",
  "thread_id":        "<reviewer thread id>",
  "reviewer_model":   "<model>",
  "reviewer_reasoning": "xhigh",
  "generated_at":     "<UTC ISO-8601>",
  "details": {
    "total_entries":  29,
    "per_entry":      [ { "key": "madaan2023selfrefine",
                          "verdict": "one of: KEEP | FIX | REPLACE | REMOVE",
                          "axis_failures": [ "one of: CONTEXT | METADATA | EXISTENCE" ],
                          "note": "..." } ]
  }
}
```

### `audited_input_hashes` scope

Hash the **declared input set** actually passed to this audit: the `.bib` file, `main.tex`, and every `sections/*.tex` file that supplied citation contexts. Do NOT hash extracted contexts from `/tmp` or other transient paths — if you need to stage extracted contexts, materialize them under `paper/.sciforge/` so the verifier can rehash reproducibly.

**Path convention**: keys are **paths relative to the paper directory** (no `paper/` prefix — the verifier already resolves relative to the paper dir; prefixing produces `paper/paper/...` and false-fails as STALE). Use **absolute paths** for any file outside the paper dir.

### Verdict decision table

| Input state                                                    | Verdict          | `reason_code` example |
|----------------------------------------------------------------|------------------|-----------------------|
| No `.bib` file or no `\cite{...}` usage                        | `NOT_APPLICABLE` | `no_citations`        |
| `.bib` file referenced but unreadable / missing                | `BLOCKED`        | `bib_unreadable`      |
| Every entry KEEP, all three axes green                         | `PASS`           | `all_entries_keep`    |
| Only FIX verdicts (metadata drift, no context errors)          | `WARN`           | `metadata_drift`      |
| Economics: working paper cited but published version exists    | `WARN`           | `working_paper_superseded` |
| Economics: AER P&P cited as mainline AER                       | `WARN`           | `venue_canonicalization` |
| Economics: author-year pair in prose does not match bib entry  | `WARN`           | `author_year_mismatch` |
| Any REPLACE or REMOVE (wrong-context or hallucinated entry)    | `FAIL`           | `wrong_context`       |
| Web lookups timed out / reviewer invocation failed             | `ERROR`          | `reviewer_error`      |

The `--uncited` flag does **not** appear in this table: uncited entries are advisory only and never alter the top-level verdict or reason_code.

**Economics-venue precedence**: working-paper-superseded, venue-canonicalization, and author-year-mismatch warnings are FIX-level (WARN), not FAIL — they reflect metadata drift, not hallucination or wrong-context. The reviewer's per-entry `note` field MUST include the canonical published reference (or corrected author-year pair) so the user can apply the FIX directly.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../../shared-references/output-language.md)** — respect the project's language setting

## Boundaries

**Never**:

- Reuse a prior reviewer thread — every audit run uses a fresh thread.
- Skip web lookups and pattern-match from memory — web access is required.
- Auto-apply REPLACE or REMOVE verdicts — they always require human approval.
- Silently skip writing `CITATION_AUDIT.json` — the artifact is mandatory regardless of outcome.
- Auto-enable uncited detection — it is opt-in only; never block on uncited entries.
- Mutate any `.bib` file while `--soft-only` is set.
- Emit REMOVE for an economics paper based solely on a DBLP no-result — must fall back to RePEc / EconLit / JSTOR first.
- Collapse AER P&P into mainline AER — they are distinct venues with different review processes.

**Always**:

- Treat wrong-context citations as more dangerous than metadata typos.
- Emit `CITATION_AUDIT.json` with a verdict for every run.
- Preserve existing callers' output exactly when `--uncited` is not set.
- Run once per submission — the audit is wall-clock expensive (web lookups for each entry).
- For economics venues, normalize the venue field to the canonical form before metadata comparison (see Step 3 reviewer prompt).
- For economics venues, search RePEc / EconLit / JSTOR as fallback when DBLP returns no result, before emitting a hallucination verdict.
- For working paper citations, check whether a published version exists and emit `working_paper_superseded` when one does.

## Known Limitations

- **DBLP coverage gap**: very recent papers (< 2 weeks) may not yet be in DBLP. Reviewer should fall back to arXiv.
- **Pre-print vs published**: when both exist, reviewer should prefer the published venue (ICML 2024 over arXiv 2401.xxxxx) but flag both.
- **Anthology vs OpenReview**: NeurIPS/ICLR papers have OpenReview entries before official proceedings; both are valid sources.
- **Multi-author truncation**: bib entries with 6+ authors using `and others` are conventional and not flagged unless the truncation hides a co-author the user explicitly cares about.
- **DBLP economics coverage gap (CRITICAL for econ venues)**: DBLP's coverage of economics journals (AER / QJE / JPE / Econometrica / RES / JFE / JF / RFS) is **thin**, especially for papers published before 2000 and for non-CS/ML economics subfields (macroeconomics, labor, development, public finance). The reviewer MUST fall back to RePEc (ideas.repec.org) / EconLit / JSTOR / the publisher site before emitting a REMOVE verdict on an economics paper. A "DBLP returned no result" finding for an economics paper should emit UNCERTAIN, not NO — only emit NO when at least two of {RePEc, EconLit, JSTOR, publisher site} also return no result.
- **NBER-number-to-published-version mapping**: there is no automated crosswalk from NBER working paper numbers to published versions; the reviewer must search by author + title to find the published version. False negatives (missing a published version) are possible — the user should treat `working_paper_superseded` warnings as advisory, not authoritative.
- **AER P&P detection**: distinguishing AER Papers & Proceedings from mainline AER relies on the bib entry's `journal` field; some legacy bib entries collapse both to `American Economic Review` without the P&P qualifier. The reviewer should check the page count (P&P papers are typically 4-8 pages; mainline AER papers are 20-40 pages) and the issue (P&P is always issue 2 of each volume) when the `journal` field is ambiguous.
- **RePEc vs DBLP metadata conflict**: when RePEc and DBLP return conflicting metadata for the same economics paper, prefer RePEc (it is the primary economics bibliography); emit a `FIX` with `note: DBLP metadata conflicts with RePEc; using RePEc as canonical`.

## Output Shape

- `CITATION_AUDIT.md` (human-readable report) at paper root
- `CITATION_AUDIT.json` (machine-readable ledger; schema above) at paper root
- `.sciforge/traces/citation-audit/<date>_runNN/` (per-entry review traces)
- Optional: applied fixes to `references.bib` + `sec/*.tex` (with `--apply` flag)
- Optional: `details.uncited_entries` field in JSON + `## Uncited Entries (opt-in)` MD section (with `--uncited` flag)
- `CITATION_AUDIT.html` (when `RENDER_HTML = true`, default) — auto-rendered single-file HTML view via `/render-html`. Full review gate. Sidecar `.review.json` carries render-fidelity verdict. **Non-blocking**: if `/render-html` fails, log the failure and treat the audit as complete — the JSON + MD ledger are the canonical outputs.

## Key Rules

- **Fresh reviewer thread per audit run** — never reuse prior review context.
- **Web access required** — the reviewer must do real lookups, not memory pattern-match.
- **Wrong-context > metadata** — a real paper used to support a wrong claim is more dangerous than a typo in author name.
- **REPLACE/REMOVE require human approval** — never auto-modify content claims.
- **Always emit, never block** — this skill always writes `CITATION_AUDIT.json` with a verdict; the decision to block finalization lives in `paper-writing` Phase 6 + the verifier, driven by the `assurance` level.
- **Run once per submission** — the audit is wall-clock expensive (web lookups for each entry); not for every save.
- **Uncited detection is opt-in only** — never auto-enable; never block on uncited entries; existing callers must observe identical output if they do not pass `--uncited`.
- **Under `--soft-only`, citation-audit emits text-rewrite proposals only; bib files are never mutated regardless of finding severity.**
- **For economics venues, RePEc / EconLit / JSTOR are canonical over DBLP** — never emit REMOVE based solely on a DBLP no-result for an economics paper.

## Comparison with Other Audit Skills

| Skill | What it audits | What it catches |
|-------|---------------|-----------------|
| `/experiment-audit` | Evaluation code | Fake ground truth, self-normalized scores, phantom results |
| `/result-to-claim` | Result-to-claim mapping | Claims unsupported by evidence |
| `/paper-claim-audit` | Numerical claims in manuscript | Number inflation, best-seed cherry-pick, config mismatch, pre-registration drift (econ) |
| `/citation-audit` | Bibliographic entries | Hallucinated refs, wrong-context citations, metadata errors, NBER-vs-published (econ) |

Together: code → result → numerical claim → cited claim. Each layer has cross-family review with no executor in the validator path.

## See Also

- `/paper-claim-audit` — sibling skill for numerical claim verification
- `/experiment-audit` — sibling skill for evaluation code integrity
- `/result-to-claim` — claim verdict assignment from results
- [`shared-references/citation-discipline.md`](../../shared-references/citation-discipline.md) — protocol document for citation hygiene
- [`shared-references/reviewer-independence.md`](../../shared-references/reviewer-independence.md) — cross-model review constraints
- [`shared-references/integration-contract.md`](../../shared-references/integration-contract.md) — reserved overlay rows for other discipline venue allowlists (CS-ML / Physics / General)
