# <path relative to repo root>

> One file = one bounded responsibility. Copy this template for every planned file.
> Fill every section. No empty Infrastructure. Status starts as `SPEC` until code exists and GitNexus verifies.

## Role

<!-- One paragraph: what this file is responsible for. What it must NOT do (point at the neighboring file that owns that). -->

## Contracts

<!-- Inputs/outputs, schemas enforced, invariants. Cite design-doc sections or sibling .md IDs. -->
- **Invariants:**
- **Outputs:**
- **Forbidden:**

## Infrastructure

<!-- Runtime deps, model files, config files, env vars, object store/DB, CLI. "none" only if truly hermetic. -->
- **Python deps:**
- **Config/artifacts:**
- **Models/external:**
- **Env vars:**

## Depends on

<!-- Other files in this tree (callers/callees). Keep honest — GitNexus context() verifies this. -->
- **Calls:**
- **Called by:**

## Tests

<!-- Required unit/integration tests from design Verification Strategy. -->

## Milestone

<!-- R0 | R1 | R2 | R3 | R4 | R5 -->

## Status

<!-- SPEC | IMPLEMENTED | VERIFIED (GitNexus coverage + role check passed) -->

## Owner

<!-- engineering | survey | platform. Use `survey` for field-catalog / template content deliverables. -->

---

### Template-only extensions (config/template artifacts)

When the file is under `templates/` or is a typed-boundary artifact, also fill:

## Boundary classes

<!-- Which of: FIELD · CHECKBOX_OPTION · CHECKBOX_GROUP · TABLE · TABLE_ROW · TABLE_CELL · LEGEND · ANCHOR apply; coordinate system. -->

## Entity owner

<!-- document | household | member | education — field_id prefix must match. -->
