# Mandatory Startup Protocol (SciForge-OSS)

> **Status**: Every skill MUST execute this protocol at startup. This is the **concrete mechanism** that makes domain adaptation automatic and unavoidable.
>
> **Core principle**: No skill is allowed to start without first checking and consuming the domain signature. If the signature exists, it MUST be applied. If it doesn't exist, the skill MUST log a warning and use defaults.

## The Protocol

Every skill MUST execute the following 5 steps in order at startup:

### Step 1: Check Domain Signature

```
Action: Check if refine-logs/domain-signature.json exists
If EXISTS → proceed to Step 2
If NOT EXISTS → log WARNING: "No domain signature found. Using default behavior."
           → proceed to Step 5 (use defaults)
```

### Step 2: Read Domain Signature

```
Action: Read refine-logs/domain-signature.json
Output: domain_signature object
Fields to extract:
  - domain_profile.evidence_type
  - domain_profile.primary_domain
  - methodology_profile.verification_approach
  - writing_profile.style
  - writing_profile.citation_format
  - failure_mode_profile.common_failures
  - data_profile.data_availability
```

### Step 3: Look Up Consumption Rules

```
Action: Query shared-references/domain-signature-consumer.md for this skill's consumption rules
Source: domain-signature-consumer.md → skill-specific section
Output: consumption_rules object (weights, failure modes, style selections)
```

### Step 4: Apply Consumption Rules

```
Action: Apply the consumption rules to this skill's behavior
Mandatory: Write a log entry showing what was applied:
  "Domain adaptation applied: [skill_name] → [field] = [value]"
```

### Step 5: Proceed with Adapted Behavior

```
Action: Execute the skill's main workflow with adapted parameters
If any rule application fails: log WARNING, continue with defaults
```

## Skill-Specific Startup Details

### /idea-discovery

```python
def startup():
    signature = read_domain_signature()
    if signature:
        evidence_type = signature["domain_profile"]["evidence_type"]
        weights = get_perspective_weights(evidence_type)
        log(f"Domain adaptation: idea-discovery → evidence_type={evidence_type} → weights={weights}")
        return weights
    else:
        log("WARNING: No domain signature. Using default perspective weights.")
        return DEFAULT_WEIGHTS
```

### /adversarial-falsification

```python
def startup():
    signature = read_domain_signature()
    if signature:
        failure_modes = signature["failure_mode_profile"]["common_failures"]
        catalog_modes = load_from_failure_mode_catalog(failure_modes)
        log(f"Domain adaptation: adversarial-falsification → loaded {len(catalog_modes)} domain-specific failure modes")
        return catalog_modes
    else:
        log("WARNING: No domain signature. Using universal failure modes only.")
        return UNIVERSAL_FAILURE_MODES
```

### /paper-writing

```python
def startup():
    signature = read_domain_signature()
    if signature:
        style = signature["writing_profile"]["style"]
        citation = signature["writing_profile"]["citation_format"]
        log(f"Domain adaptation: paper-writing → style={style}, citation={citation}")
        return {"style": style, "citation": citation}
    else:
        log("WARNING: No domain signature. Using default academic style.")
        return DEFAULT_STYLE
```

### /novelty-check

```python
def startup():
    signature = read_domain_signature()
    if signature:
        domain = signature["domain_profile"]["primary_domain"]
        weights = get_novelty_weights(domain)
        log(f"Domain adaptation: novelty-check → domain={domain} → weights={weights}")
        return weights
    else:
        log("WARNING: No domain signature. Using default novelty weights.")
        return DEFAULT_WEIGHTS
```

### /result-to-claim

```python
def startup():
    signature = read_domain_signature()
    if signature:
        data_avail = signature["data_profile"]["data_availability"]
        confidence_factor = get_confidence_factor(data_avail)
        log(f"Domain adaptation: result-to-claim → data_availability={data_avail} → confidence_factor={confidence_factor}")
        return confidence_factor
    else:
        log("WARNING: No domain signature. Using default confidence factor.")
        return DEFAULT_CONFIDENCE
```

## Verification

After each skill completes its startup, the orchestrator verifies:

1. The skill's startup log is written to `refine-logs/startup-log.md`
2. The log contains the domain adaptation entry (if signature existed)
3. If the log shows "WARNING: No domain signature", the orchestrator continues (graceful degradation)

## Failure Mode

If the startup protocol fails at any step:
1. Log the error with the specific step number
2. Continue with default behavior
3. The pipeline does NOT break — the skill executes with defaults

## See Also

- [`domain-signature-consumer.md`](domain-signature-consumer.md) — consumption rules per skill
- [`../meta-skills/domain-signature/SKILL.md`](../meta-skills/domain-signature/SKILL.md) — produces the signature
- [`../orchestrator/auto-pipeline/SKILL.md`](../orchestrator/auto-pipeline/SKILL.md) — graceful degradation protocol