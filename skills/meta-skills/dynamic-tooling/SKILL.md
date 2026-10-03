---
name: dynamic-tooling
version: 1.7.2
description: "Build custom ad-hoc tools (parsers, converters, small CLIs) the agent needs mid-run that aren't pre-provided. Invoke when no existing tool fits a pipeline step."
type: reference-skill
role: tool-builder
---

# Meta-Skill: Just-in-Time Dynamic Tooling

## Quick Reference

- **Purpose**: Generate throwaway tools at runtime to fill capability gaps
- **Input**: Tool description + interface contract
- **Output**: Executable Python module + registration info
- **Key**: 7 tool templates (symbolic-reasoner/statistical-modeler/knowledge-graph/formal-verifier/code-synthesizer/data-transformer/text-analyzer)

## Use When

When the AI scientist hits a compute or data-processing task that the standard sandbox libraries cannot handle — needing a domain-specific tool, adapter, or pipeline — use this skill.

Typical prompts:
- "I need a tool to process chemical molecular formulas"
- "This data format needs a custom parser"
- "write a custom tool for this data format"
- "create a graph analysis utility for this specific problem"
- "build a bridge between the sandbox output and the plotting engine"

This is the **force multiplier** meta-skill: it lets the system extend its own capabilities at runtime, ensuring no research problem ever hits the "tool unavailable" dead end.

## Job

Dynamically generate, test, and register a temporary or permanent tool (Python module, CLI wrapper, API adapter, or data pipeline) to fill a capability gap discovered during research. The tool is written by the AI, validated by execution, then made available to downstream skills.

Non-negotiable goals:
1. **Every tool is tested before registration** — the minimal smoke test must pass
2. **Every tool has a clear interface contract** — input schema, output schema, error modes
3. **Failed tools are diagnosed, not discarded** — errors are returned together with suggested fixes
4. **Tools are scoped** — temporary (session-only) or persistent (reused across sessions)

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | enum | `session` | `session` (temporary) or `persistent` (reusable) |
| `language` | enum | `python` | `python` / `julia` / `bash` |
| `smoke_test` | bool | `true` | Run the smoke test after generation |
| `max_retries` | int | `2` | Max generation+test rounds |

## Steps

### Step 1: Identify the Gap

Analyze the request and determine:
1. **What is missing** — a specific library function, data-format parser, visualization adapter, or compute pipeline
2. **Why existing tools are insufficient** — unsupported data format, missing library, performance requirement, domain-specific logic
3. **The tool's scope** — one-shot tool or reusable component
4. **Dependencies** — which libraries or external services the tool needs

If the gap can be filled by installing a standard library (pip install), **do not create a tool** — delegate to `/dynamic-sandbox` with the package list.

### Step 2: Design the Tool Interface

Define the tool's contract before writing code:

```
Tool Name: {name}
Purpose: {one-sentence description}
Input: {JSON schema or function signature}
Output: {JSON schema or return type}
Side Effects: {file I/O, network calls, state changes}
Error Modes: {what can go wrong and how it is reported}
```

### Step 2b: Tool Template Library (load on demand)

If the requested tool type matches one of the templates below, load the template directly instead of generating from scratch. Templates provide predefined input/output schemas, test cases, and error handling.

| Template type | Use case | Input | Output | Tech stack |
|---------------|----------|-------|--------|------------|
| **symbolic-reasoner** | Mathematical theorem proving, logic derivation verification | Mathematical statement + assumption set | Proof steps + verification status | SymPy/symengine |
| **statistical-modeler** | Hypothesis testing, regression analysis, causal inference | Data + test type | Test statistic + p-value + effect size | scipy.stats/statsmodels |
| **knowledge-graph** | Concept mapping, literature network analysis | Concept list + relation types | Knowledge graph (JSON/GraphML) | networkx |
| **formal-verifier** | Logic proposition verification, model checking | Logic proposition + inference rules | Verification passed / counterexample | Z3/pysat SMT solving |
| **code-synthesizer** | Auto-generating verification/simulation code | Problem description + parameters | Executable Python script | AST templates + jinja2 |
| **data-transformer** | Multi-source data format conversion | Source data + target format | Converted data | pandas |
| **text-analyzer** | Keyword extraction, topic modeling | Text + analysis type | Structured analysis result | sklearn/nltk |

**Template usage flow**:
1. Identify the template type the request matches
2. Load the template's input/output schema
3. Fill in the template parameters (domain-specific variable names, function names)
4. Execute Step 3 to generate the implementation
5. If no template matches, fall back to the generic design flow of Step 2

**Example**: user requests "verify the correctness of this mathematical derivation"
→ matches the `symbolic-reasoner` template
→ input: mathematical statement + assumption set
→ output: step-by-step verification result
→ use SymPy to generate the verification script

### Step 3: Generate the Implementation

Write the tool as a self-contained Python module:
- A single entry function (or a class with `__call__`)
- Type-annotated parameters and return values
- Docstring with a usage example
- Error handling for all identified error modes
- No hardcoded paths or credentials
- Version string (`__version__`)

**Code quality rules:**
- Every tool at most 200 lines (split into submodules if larger)
- Must pass `py_compile` before registration
- Must not import from outside the sandbox or installed libraries
- Must not execute shell commands unless explicitly authorized

### Step 4: Smoke Test

Run the tool against a minimal test case:
1. Write a test with known input and expected output
2. Import and invoke the tool's entry function
3. Compare actual output with expected output (floats within tolerance)
4. If the test fails, return the error with suggested fixes

**When the test passes:**
- Compute the SHA-256 hash of the source file
- Register in `tools/registry.json`

**When the test fails (retry at most max_retries times):**
- Return the traceback
- Suggest 3 possible fixes
- Let the caller decide whether to fix and retry

### Step 5: Register and Document

**Persistent tool:**
```json
{
  "name": "tool_name",
  "version": "1.0.0",
  "path": "tools/tool_name/tool_name.py",
  "hash": "sha256:...",
  "description": "...",
  "input_schema": "...",
  "output_schema": "...",
  "created_at": "2026-07-19T12:00:00Z",
  "usage_count": 0
}
```

**Temporary tool:**
- Write to `tools/temp/{session_id}_{tool_name}.py`
- Return the file path and usage instructions
- Do not register in `registry.json`

### Step 6: Return to the Caller

```json
{
  "status": "one of: created | updated | failed",
  "tool_name": "custom_parser",
  "path": "tools/custom_parser/custom_parser.py",
  "entry_point": "custom_parser.parse(input_data)",
  "smoke_test": "one of: passed | failed",
  "usage": "from tools.custom_parser import parse; result = parse(data)"
}
```

## Downstream Skill Invocation

- `/dynamic-sandbox` — uses the newly created tool to execute the computation
- `/unified-plotting` — the tool's plot output can be passed to this skill for rendering

## Shared Contract References

- [integration-contract](../../shared-references/integration-contract.md) — skill integration protocol
- [skill-config](../../shared-references/skill-config.md) — skill configuration contract
- [output-manifest](../../shared-references/output-manifest.md) — artifact structure contract
