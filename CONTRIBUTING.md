# Contributing to SciForge-OSS

Thanks for your interest! SciForge-OSS is a **pure-Skill-driven universal AI Scientist framework** — "AI for Scientist Anything": one universal 21-phase pipeline, any scientific domain.

> 中文使用者：README.zh.md 有完整的中文说明；本贡献指南以英文为准（repo 的 skill 与契约文档均为英文）。

## How to contribute

### 1. Open an issue

- **Bug report**: what happened, repro steps, expected behavior.
- **Feature request**: the capability, the use case, the expected effect.
- **Skill improvement**: which SKILL.md / contract, and the concrete wording change.

### 2. Pull requests

1. Fork the repository and branch: `feat/your-feature` or `fix/your-fix`.
2. Make the change (scope rules below).
3. **Run the local gates before pushing** — a PR that fails them will not be reviewed:
   ```bash
   python3 scripts/ci_check.py          # links + version consistency + plotting + full test suite
   python3 -m pytest tests/ -q          # (also runs inside ci_check.py)
   ```
4. If you touched the release surface, follow `VERSIONING.md` (single version number across all 27 files + CHANGELOG entry).
5. Open the PR with a clear description of the problem and the fix.
6. **Freeze convention**: once a PR is opened, treat its commits as frozen — further changes go into a NEW PR. (Repeated squash-merges racing late pushes dropped commits in the past; this convention exists because of that.)

### 3. Scope rules

- **Skills are English-only pure Markdown.** Every `SKILL.md` and shared contract is consumed by arbitrary AI agents: no CJK text, no executable code blocks that the agent must run (tooling lives in `scripts/`, not in skills). Keep machine-readable identifiers (artifact names, field names, `/skill-name` tokens, paths) byte-exact when editing around them.
- **Single-authority rule for layout**: `shared-references/output-protocol.md` owns the workspace directory tree; `shared-references/artifact-registry.md` owns artifact contracts. A new machine-readable verdict must be added to the `verdicts/` tree FIRST, then registered (registry row + `schemas/<NAME>.schema.json` + entry in `scripts/validate_verdicts.py`) — see `schemas/README.md`.
- **Discipline-agnostic**: never hardcode domain knowledge into the framework; domain adaptation happens at runtime via the domain signature.
- **DAG architecture**: keep the pipeline a bounded, budget-carrying DAG (every loop-back has a budget and an exhaustion exit — see the Loop-Back Registry in `auto-pipeline/SKILL.md`).
- **Tooling changes** (`scripts/`, `tests/`, `fixtures/`): keep `ci_check.py` green, add/extend tests for behavior changes, stdlib-only Python unless a dependency is justified in INSTALL.md.

### 4. SKILL.md writing conventions

Each SKILL.md contains:

- `---` frontmatter: `name`, `version` (repo-wide single version), `description`, `type`, `role`
- `# Title`
- `## Quick Reference` — purpose / input / output / key invariants
- `## Use When` — trigger conditions + typical prompts
- `## Job` — the non-negotiable goal
- `## Workflow` — numbered steps
- `## Boundaries` — never/always rules
- `## Output Protocols` — pointer-load `shared-references/output-protocol.md` (do not inline-copy its rules)
- `## See Also` — relative links to contracts

Rules of thumb: every registered artifact a skill writes must be declared in its output section with a link back to the artifact registry; every artifact it reads must appear in its inputs. Prose schemas are not contracts — if a downstream skill gates on it, it needs a registry row (and for verdicts, a schema).

## Code of conduct

- Respect every contributor.
- Keep discussions constructive and technical.
