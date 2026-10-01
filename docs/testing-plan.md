# Testing plan — ocr-platform

Consolidated test strategy. Each file spec under `docs/files/**` owns its own `## Tests` list (42 specs carry one); this doc is the **map** — the test levels, the cross-cutting fail-closed gates every level must honor, the fixture taxonomy, and the R0 exit gate. It exists so "is R0 done?" has one answerable definition instead of 42 scattered lists.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **R0 exit gate:** smoke fixture end-to-end; provenance completeness 100% on accepted; ruff/pytest green (`market-roadmap.md:34`)

---

## 1. Test levels

| Level | Scope | Runs against | Examples (from specs) |
|---|---|---|---|
| **Unit** | one module, pure logic | mocks | reason codes unique/stable; PDF bottom-left → image top-left conversion; overlap ≥0.80 accepts |
| **Contract** | adapter shape / schema | mock backend | OCR adapter observation shape; rule schema + pass/fail vectors; config unknown-key rejection |
| **Determinism** | byte/hash stability | real render, CPU | render determinism at fixed DPI/colorspace; `run_id` stable for identical bytes+config |
| **Property** | invariants over generated input | synthetic | populated-row predicate on synthetic ink; present-without-evidence construction always fails |
| **Integration** | multi-stage pipeline | smoke fixture | classify → render → (mock/real) OCR → decide → validate → export |
| **Golden** | end-to-end output snapshot | labeled fixtures | full `result.json` + `provenance.json` vs approved snapshot |

> R0 runs Unit + Contract + Determinism + Property + smoke Integration. Golden-on-gold-set is a **flip** prerequisite (calibration, not R0 exit) — see `accuracy-plan.md §4`.

---

## 2. Cross-cutting fail-closed gates

Every level must uphold these. They are the invariants the whole spec set repeats; tests assert them, not just document them.

| Gate | Assertion | Owning specs |
|---|---|---|
| **G1 Provenance completeness** | an accepted/validated value **cannot serialize** without a complete evidence chain; construction of present-without-evidence fails | `validator.py.md`, `models.py` (schemas), `export/*` |
| **G2 Fail-closed disposition** | unknown code → never canonical; unresolved ditto → review; unknown/deprecated template → rejected; unclassified/expired/hash-mismatch → rejected | `reason-codes.md`, `acceptance_policy.py.md`, `manifest.py.md` |
| **G3 R0 flags disabled** | OCR/native auto-accept disabled in R0 forces review regardless of confidence | `acceptance_policy.py.md`, `adr-005` |
| **G4 Run identity** | identical bytes+config → identical `run_id`; different config → different `run_id`; retry does not change `run_id` | `pipeline.py.md`, `hashing.py.md` |
| **G5 Coordinate SoT** | cross-system ops without explicit conversion are rejected; `page-box normalize` recorded as explicit provenance op, never omitted | `coordinates.py.md`, `runtime.yaml.md` |
| **G6 PII-free logs** | no emitted log line contains a known fixture PII value | `observability.md`, ADR-007 |
| **G7 Page-set integrity** | page-level review blocks child field accept; extra/missing/duplicate page → review reason | `state_machine.py.md`, `reason-codes.md §2.1` |

---

## 3. Fixture taxonomy

Fixtures are labeled and never mixed across trust boundaries (`market-roadmap.md:93`, `data-plan.md`).

| Fixture class | Purpose | PII | Notes |
|---|---|---|---|
| `smoke` | R0 exit-gate end-to-end; fast | none / synthetic | `synthetic_baseline_approved` template package (RG-20) |
| `layout_ref` | geometry / annotation source | approved-redacted | refs 95–99 reconciliation (`annotate_template.py.md:13`) |
| `gold` | calibration precision/holdout | approved-redacted | ≥50–100 labeled + ≥30 holdout (does not exist yet, RG-16) |
| `dev-gold` | day-to-day review-rate tracking | approved-redacted | ceiling starts ≤40% (RG-17) |
| `synthetic-ink` | property tests (row projection) | none | generated patterns, no corpus |

**Enforced separation:** smoke-vs-gold labels are checked (`Unit: smoke vs gold labels enforced`); production never uses an unclassified loader mode without explicit allow.

---

## 4. Determinism harness

The determinism level reads its tolerances from `configs/runtime.yaml comparison_policy` (single SoT — the spike and the hasher read the same block).

- N≥3 repeated CPU runs on the same fixture → canonical-JSON identical; `cpu_render_pixel_tolerance == 0`.
- Non-float artifacts compared byte-for-byte; float/GPU paths only within declared `gpu_float_*` tol (unused in R0).
- This is the same check `scripts/run_spike.py` gates C1/C2 on — the spike proves it once at pin-time; CI re-proves it per commit.

---

## 5. R0 exit gate (definition of done)

R0 ships when **all** hold:

1. `ruff` clean, `pytest` green.
2. Smoke fixture runs end-to-end through all pipeline stages.
3. Provenance completeness **100%** on every accepted value (G1).
4. Gates G1–G7 have passing tests.
5. Compatibility spike recorded a **go** (or conditional-go with caveats) — `run_spike.py` matrix (RG-01…RG-05).

**Not** required for R0 exit (these gate the auto-accept *flip*, not R0): gold set, calibration report, 97% precision sign-off (`accuracy-plan.md §4`, ADR-005, RG-15…RG-17).

---

## 6. What is deliberately not tested in R0

| Deferred | Why | Milestone |
|---|---|---|
| Auto-accept precision on gold | no gold set yet; flip-gated | flip |
| GPU determinism | CPU-only R0 | R0.5/R1 |
| Affine registration residual threshold | needs E2 evidence | R0.5 |
| API / job-store / concurrency | not built | R1 |
| Multi-tenant access control | single-operator R0 | R2 |

---

## Related documents

- Per-file test lists: `docs/files/**` `## Tests` sections (source of truth for concrete cases)
- Codes asserted by tests: `docs/reason-codes.md`
- Determinism tolerances: `docs/files/configs/runtime.yaml.md`
- Spike go/no-go: `docs/files/scripts/run_spike.py.md`
- Calibration (flip) gate: `docs/accuracy-plan.md`
- Open test-blocking unknowns: `docs/research-gaps.md`
- Log PII enforcement: `docs/observability.md`
- Glossary: `docs/glossary.md`
