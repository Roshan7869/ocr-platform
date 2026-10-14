# R0 Remediation Execution Plan — ocr-platform

> Designed via **adaptive-imagining-cat** Phases 0–3 (first-principles → state analysis → typed DAG).
> Execution vehicle: **ruflo swarm** (hierarchical · specialized · maxAgents=5 · raft consensus) + **claude-flow** coordination + **gstack** skills for verification.
> **Status: DRAFT — awaiting approval** (NEXUS protocol: present plan before execution).
> Authoritative definition of done: `docs/testing-plan.md §5`. All findings verified against the working tree on **2026-10-14**.

---

## Verdict

R0 is **not ready**. Of the 5 exit gates in `testing-plan.md §5`: **1 pass · 1 partial · 3 fail.**
`pytest` is green (200 passed); every other gate is open. HEAD (`a9a99f2e`) also lags the tree by **8 untracked source files + ~14 docs contracts**.

## Exit-gate status (verified)

| # | Gate (`testing-plan.md §5`) | Status | Root cause |
|---|---|---|---|
| 1 | `ruff` clean + `pytest` green | ❌ | pytest 200 ✅; ruff **163** errors (93 `src/` · 18 `tests/` · 38 root-kaggle · 5 notebook · 4 `scripts/` · 1 config); `format --check` fails because `[tool.ruff]` (`pyproject.toml:181`) has no `exclude`, so ruff 0.17.0 lints `.ipynb`/`.md` |
| 2 | smoke fixture runs e2e | ❌ | `import paddle` → `ImportError: forward_complete_op_role` (paddlepaddle 3.3.1 + paddlepaddle-gpu 2.6.2 conflict; `pass_utils.py` lacks the symbol its own `pipeline_1f1b.py:25` imports); `fixtures/fixture_manifest.json` empty → demo extracts 0 cells |
| 3 | provenance 100% on accepted (G1) | ✅ | enforced by construction + passing tests |
| 4 | gates G1–G7 have passing tests | ⚠️ | G1/G2/G4/G5/G7 covered; **G3** (flags-disabled→review, `orchestrator/pipeline.py:685`) and **G6** (no fixture-PII in logs, `observability.md:21`) untested; **G6 is vacuous** — `src/` uses `print()`, zero stdlib logging |
| 5 | spike recorded a go | ❌ | `scripts/run_spike.py` ABSENT · `configs/runtime.yaml` ABSENT |

## Structural gaps (block the "green CI" claim)

- `.github/workflows/ci.yml` ABSENT — only `benchmark.yml` exists; `ci-spec.md §6` pipeline unimplemented.
- `tests/` flat (9 files) — no `unit/` `contract/` `property/` `integration/` that `ci-spec.md §6` runs.
- `docker/Dockerfile` — **0 `FROM … AS` targets** (no `cpu-runtime`/`gpu-runtime`, `ci-spec.md §2.8`); `ENTRYPOINT` → `scripts/extract.py` which **does not exist**.
- 8 untracked source files + ~14 docs contracts uncommitted (tree diverges from HEAD).

---

## Phase 0 — Baseline (unblocks everything)

| Task | Action | Verify (pass/fail) |
|---|---|---|
| **A0** | Commit the untracked provenance work (`schemas/{decision,evidence,job,provenance}.py`, `provenance/{hashing,validator}.py`, `render/coordinates.py`, `tests/test_provenance.py` + ~14 `docs/files/**`) as a `chore:` baseline | `git status` clean · `pytest` still 200 passed · new files get `docs/files/` siblings (docs-gate) |

Everything below depends on a clean, consistent tree.

---

## Swarm topology (ruflo)

```
                 ┌─────────────────────┐
                 │  coordinator (main) │  decompose · assign · verify · reconcile
                 └──────────┬──────────┘
         ┌──────────────┬───┴────┬──────────────┬─────────────┐
         ▼              ▼        ▼              ▼             ▼
   [A env-fixer] [B lint]  [C test-author] [E infra]   [D spike-builder]
   coder+          coder     tester          devops       coder+architect
   investigate                                                    │
         │                                                         │ (after A)
         └──────────────► gate-2 verify ◄─────────────────────────┘
                              ▼
                       [reviewer/qa]  Phase 5 — re-run all 5 gates
```

- **Topology:** hierarchical · strategy specialized · maxAgents 5 · consensus raft (ruflo `guidance_workflow` swarm default).
- **Parallel:** B, C, E run concurrently and independent of A. D waits on A (needs working paddle + a classified fixture).
- **gstack skills:** `/investigate` (paddle root-cause) · `/qa` (test + gate verify) · `/security-scan` (G6 PII) · `/ship` (post-green commit/PR).

---

## Work-stream DAG (tasks ≤ 1 hr, each with a pass/fail gate)

### Stream A — Environment & Gate-2 (`env-fixer`: coder + investigate)

| Task | Action | Verify |
|---|---|---|
| **A1** | Resolve paddle: `pip uninstall paddlepaddle-gpu` (2.6.2), confirm paddlepaddle 3.3.1 imports clean; **fallback** = apply notebook cell-2 monkeypatch as a documented compat shim | `python -c "import paddle, paddleocr; PaddleOCR(lang='hi'); PaddleOCR(lang='en')"` inits both backends, no ImportError |
| **A2** | Populate `fixtures/fixture_manifest.json` with a classified two-page smoke fixture (confirm one exists; if not, classify one via `fixtures/loader.py` → escalate if blocked) | loader accepts it · demo run extracts **> 0 cells** · both OCR backends report ready |

### Stream B — Lint & Config (`lint-fixer`: coder) — independent

| Task | Action | Verify |
|---|---|---|
| **B1** | Scope `[tool.ruff]` (`pyproject.toml:181`): add `exclude` for `.ipynb`/`.md` + per-file-ignores for `kaggle_notebook.py`/`kaggle_run.py` (30 `invalid-syntax` from `!pip` lines) | `ruff format --check .` no longer fails on non-`.py` |
| **B2** | Clear **93** `src/` errors (26 `UP037` · 15 `F401` · 9 `BLE001` · 7 `I001` · 6 `RUF012` · 5 `UP035`/`RUF046` · 5 `F841` …) — many auto-fixable via `ruff check --fix` | `ruff check src` = **0** |
| **B3** | Clear `tests/` (18) + `scripts/` (4) + `configs/ (1)` | `ruff check .` = **0** |

### Stream C — Gate-4 test coverage (`test-author`: tester) — independent

| Task | Action | Verify |
|---|---|---|
| **C1** | Write **G3** test: `allow_auto_accept=False` ⇒ every cell `disposition == "review"` (`orchestrator/pipeline.py:685`) | test RED without guard, GREEN with it |
| **C2** | Write **G6** test — **decision-dependent** (see below): either introduce a stdlib-logging surface then `caplog`-assert no fixture-PII, or scope to `capsys` print-capture | injected PII value is caught; assertion fails when PII present |
| **C3** | Restructure flat `tests/` → `unit/` `contract/` `property/` `integration/` per `ci-spec.md §6` | `pytest tests/unit tests/contract tests/property -q` all green |

### Stream E — Infra / CI / Docker (`infra-builder`: devops) — independent

| Task | Action | Verify |
|---|---|---|
| **E1** | Author `.github/workflows/ci.yml` per `ci-spec.md §6` (lint → unit/contract/property → integration + determinism → docs-gate; Python **3.11** pinned) | YAML valid · docs-gate step calls existing `scripts/check_docs_contract.py` |
| **E2** | Add `cpu-runtime` + `gpu-runtime` targets to `docker/Dockerfile` (`ci-spec.md §2.8`) | `docker build --target cpu-runtime .` succeeds |
| **E3** | Implement `scripts/extract.py` per `extract.py.md` (args, exit codes 0/2/3/4, writes `result.json`+`review_candidates.json`; Docker `ENTRYPOINT` target) | subprocess exit codes correct · missing pins → exit 3 |

### Stream D — Gate-5 spike (`spike-builder`: coder + architect) — **after A**

| Task | Action | Verify |
|---|---|---|
| **D1** | Author `configs/runtime.yaml` per normative key set (`runtime.yaml.md`) — comparison_policy is the SoT the spike + hasher both read | loader validates: rejects unknown/missing keys (fail-closed) |
| **D2** | Implement `scripts/run_spike.py` per C1–C8 criteria (`run_spike.py.md`): N≥3 CPU determinism, canonical-JSON compare, min CPU resolution, python reconciliation, single rec model + checksum, rasterizer, license, RACE strategy | exit **0** go (or conditional-go with `caveats[]`) · C1 `cpu_render_pixel_tolerance == 0` |

---

## Phase 5 — Verify (reviewer/qa)

Re-run the full exit gate and record the result:

1. `ruff check .` = 0 · `ruff format --check .` clean · `pytest` green.
2. Smoke fixture e2e with **real** det+rec (non-zero cells).
3. Provenance 100% on accepted (G1) — still green.
4. G1–G7 each have a passing test.
5. Spike matrix recorded **go** (or conditional-go with caveats) — **or** formally deferred per your decision below.

---

## Decisions (resolved 2026-10-14)

1. **Spike is IN scope** — honor `testing-plan.md §5` as the SoT ("one answerable definition"). Stream D ships.
2. **G6 = add minimal logging + caplog** — implement the `observability.md §3` log-event catalog on a stdlib `logging` surface, then `caplog`-assert no fixture-PII value in any record. `observability.md §1` is the spec: allowed = `run_id`, `document_content_hash`, `configuration_fingerprint`, model pin ids, policy version, timings; **forbidden** = OCR text / recognized values, file paths embedding PII.

## Additional findings (2026-10-14 verification)

- **`src/ocr_platform/fixtures/loader.py` is ABSENT** — yet `run_spike.py.md` and `extract.py.md` both list it under **Depends on**. Stream A2 is therefore **build-the-loader**, not "populate the manifest".
- **`fixtures/` holds zero documents** — only the empty `fixture_manifest.json`. No classified two-page smoke fixture exists anywhere in the repo. Candidate source material: root `page98.jpg` / `page98_crop.jpg`, `WARD-42/`. Manifest notes require classification (`synthetic | approved_redacted`) + sha256 of exact bytes before loader use — so **A2 needs a source document and a classification decision**.
- **`observability.md §3`** already enumerates the R0 log-event catalog, so C2 implements a spec rather than inventing one.
- **`pyproject.toml`** lists `paddleocr>=3.0,<4` + `paddlepaddle>=3.0,<4` as *hard* dependencies (not a `spike` extra) with "do not pin until spike" comments; `pip check` reports unrelated pre-existing conflicts (`cachetools`, `rich`, `websockets`) that are not blockers.

---

## Fastest path to green (if spike is deferred)

A0 → {A1, A2} ∥ {B1, B2, B3} ∥ {C1, C3} ∥ {E1, E2, E3} → Phase 5. Gates 1/2/3/4 go green without D; gate 5 becomes a recorded caveat.
