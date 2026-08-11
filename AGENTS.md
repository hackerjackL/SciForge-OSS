# AGENTS.md — SciForge-OSS

Skill-driven, domain-agnostic "AI Scientist" framework. **No build step** — the product is markdown skills + Python/JS tooling. Node ≥18 for `bin/sciforge.js`; Python 3 stdlib for the CI gate.

## Commands
- Full gate (CI `.workflow/ci.yml` and pre-commit share this single entry): `python3 scripts/ci_check.py` — markdown link integrity, version consistency, plotting `--doctor`, pytest suite. Exit 0 required; missing pytest is a FAIL, not a skip.
- Tests: `pytest tests/` (verdict validator + security self-test run via ci_check).
- Plotting toolchain self-check: `python scripts/plotting/render_figure.py --doctor` (needs d2/graphviz/rsvg-convert/poppler/texlive + matplotlib/numpy/Pillow; code contains zero absolute paths).
- CLI: `node bin/sciforge.js tools-check|tools-install|init`.
- No lint/format tool configured — match surrounding style manually.

## Layout
- `skills/orchestrator/auto-pipeline/SKILL.md` — the only entry: one research question per run, 21-phase DAG, delegates every phase to a sub-skill (never does research itself).
- `skills/support/` — phase skills; `skills/meta-skills/` — cross-cutting; `skills/shared-references/` — contract layer (`*-contract.md`, `schemas/`).
- `scripts/` — `ci_check.py`, `verifiers/`, `plotting/` (`render_figure.py` = single figure entry, dual PDF+SVG + embedded Nature-grade audit), `eval/`.
- `fixtures/e2e_minimal/` — mock pipeline workspace consumed by tests.

## Gotchas
- Pipeline run artifacts (`.sciforge/`, `derivations/`, `paper/`, `figures/`, `methods/`, `literature/`, `audit_report/`, `results/`, `output/`, `tools/`, `review-stage/`) are gitignored: runs happen outside the repo (e.g. `/root/autodl-tmp/<problem_id>`); never git-add/commit `problems/*` run output.
- Version bumps must sync `package.json` + `CITATION.cff` + semver lines in BOTH `README.md` and `README.zh.md`, or ci_check fails.
- Forced human checkpoints (Phase 3→4 idea pick, Phase 5→6 method approval) and the 3-round fallback limit are non-negotiable; INV-G1 freezes the Q-id anchor referenced by every downstream artifact.
- OSS is discipline-agnostic (`general` row only — no per-discipline branches), single unified `elsarticle` template, 3-fidelity claims.
- Deliverables are the skill assets (SKILL.md, shared-references contracts, `render_figure.py`/`figure_audit.py`) — sample/figure-lab test figures are validation scaffolding, not products; don't over-iterate on them.
- Machine-readable verdicts must match the JSON Schemas in `skills/shared-references/schemas/` (enforced by `scripts/validate_verdicts.py`).
- `AGENT_GUIDE.md` is the authoritative agent-facing doc — keep it in sync with pipeline changes.
