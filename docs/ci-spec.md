# CI pipeline — ocr-platform

Automated enforcement of the docs contract and quality gates. The R0 exit gate requires "ruff/pytest green" — this spec defines what that means operationally.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Triggers

**Current experimental CI (2026-10-05):** the benchmark workflow runs lint,
formatting, regression tests and `scripts/check_docs_contract.py` on push/PR.
The production spike, nightly determinism, Docker smoke and GitNexus verification
below remain planned. Green experimental CI is not a full R0 exit gate.

| Trigger | What runs | Why |
|---|---|---|
| **Pull request** | Lint + unit + contract + property + docs-gate | Fast feedback; no expensive integration |
| **Merge to main** | Full suite + determinism + spike matrix (CPU) | Prove the commit didn't break determinism |
| **Nightly** | Full suite + spike matrix (CPU) + determinism (N=3) | Catch dependency drift; re-prove determinism |
| **Release tag** | Full suite + spike matrix + Docker build + smoke | Gate for any deployment |

---

## 2. Pipeline stages

### 2.1 Lint (PR, merge, nightly, release)

```bash
ruff check .
ruff format --check .
```

**Gate:** Zero errors. Warnings allowed only with `# noqa: <rule>` + justification.

### 2.2 Unit tests (PR, merge, nightly, release)

```bash
pytest tests/unit -x -q
```

**Gate:** 100% pass. No skips allowed in CI (use `@pytest.mark.skipif` for optional deps only).

### 2.3 Contract tests (PR, merge, nightly, release)

```bash
pytest tests/contract -x -q
```

**Gate:** 100% pass. Schema shapes, enum vocabularies, config validation.

### 2.4 Property tests (PR, merge, nightly, release)

```bash
pytest tests/property -x -q
```

**Gate:** 100% pass. Invariants over generated input (provenance completeness, fail-closed).

### 2.5 Integration tests (merge, nightly, release)

```bash
pytest tests/integration -x -q --fixture smoke-001
```

**Gate:** 100% pass. Smoke fixture end-to-end through all pipeline stages.

### 2.6 Determinism check (merge, nightly, release)

```bash
python scripts/run_spike.py --matrix cpu --repeat 3
```

**Gate:** Exit 0 (go). Canonical JSON identical across N=3 runs. `cpu_render_pixel_tolerance == 0`.

### 2.7 Docs gate (PR, merge, nightly, release)

```bash
python scripts/check_docs_contract.py
```

**Gate:** Every non-trivial source/config/template file has a sibling `.md` in `docs/files/`. New file without spec = fail.

### 2.8 Docker build (release only)

```bash
docker build -f docker/Dockerfile --target cpu-runtime .
docker build -f docker/Dockerfile --target gpu-runtime .
```

**Gate:** Both targets build successfully. CPU target runs smoke fixture.

---

## 3. Pre-commit hooks

Defined in `.pre-commit-config.yaml`:

| Hook | What it catches |
|---|---|
| `ruff` | Linting + formatting |
| `mypy` | Type errors (strict mode) |
| `check-docs-contract` | Missing `.md` for new source files |
| `check-glossary` | New term used in code but not in glossary |

**Install:** `pre-commit install`

---

## 4. Environment parity

| Aspect | Dev laptop | CI | Production container |
|---|---|---|---|
| Python | 3.12.3 | 3.11 (pinned) | 3.11 (pinned) |
| PaddleOCR | Not installed | Installed (pinned) | Installed (pinned) |
| PaddlePaddle | Not installed | Installed (pinned) | Installed (pinned) |
| GPU | None | None | CUDA (pinned) |
| Fixtures | Local | CI secrets | Mounted volume |

**Rule:** CI must pass with the same Python version as production (3.11). Dev laptop may differ but must not block CI.

---

## 5. Failure handling

| Failure | Action |
|---|---|
| Lint | Fix formatting; no merge until clean |
| Unit/contract/property | Fix code; no merge until green |
| Integration | Fix code or fixture; no merge until green |
| Determinism | Investigate; likely dependency drift or non-deterministic code |
| Docs gate | Add missing `.md`; no merge until complete |
| Docker build | Fix Dockerfile; no release until build succeeds |

---

## 6. CI configuration

```yaml
# .github/workflows/ci.yml
name: ci
on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: "0 2 * * *"  # Nightly at 2 AM

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit tests/contract tests/property -x -q

  integration:
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' || github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration -x -q --fixture smoke-001
      - run: python scripts/run_spike.py --matrix cpu --repeat 3

  docs-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: python scripts/check_docs_contract.py
```

---

## 7. Related documents

- Testing plan: `docs/testing-plan.md`
- R0 exit gate: `docs/testing-plan.md §5`
- Spike matrix: `docs/files/scripts/run_spike.py.md`
- Docs contract: `docs/files/README.md`
