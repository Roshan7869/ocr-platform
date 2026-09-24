# scripts/extract.py

## Role

CLI entrypoint for the R0 single-process extractor: load classified fixture or user PDF path, run pipeline, write canonical JSON export + review-candidate file. Thin wrapper — all logic in `worker/pipeline.py` and export modules.

## Contracts

- **Invariants:**
  - Args: input path or `--fixture <id>`, `--template` (default approved FAMILY_SURVEY_V1 hash), `--out` dir, `--policy` version.
  - Refuses inputs failing `fixtures/loader.py` classification when `--fixture` used; raw path mode marks run as `user_input` and requires explicit `--allow-unclassified` (R0 default deny for production-like files).
  - Exit codes: 0 success (accepted + review files written), 2 validation/provenance failure, 3 spike/pins missing, 4 usage.
  - Prints run_id, template hash, policy version, counts (accepted / review / errored).
  - Docker `ENTRYPOINT` targets this script.
- **Outputs:** files under `--out`: `result.json`, `review_candidates.json`, optional `provenance.json`.
- **Forbidden:** hidden flags that disable provenance validator; auto-accept overrides.

## Infrastructure

- **Python deps:** project package
- **Config/artifacts:** `configs/runtime.yaml`, `configs/acceptance_policy_v1.yaml`, template package
- **Models/external:** pins from models.py (post-spike)
- **Env vars:** none required

## Depends on

- **Calls:** `worker/pipeline.py`, `export/json_export.py`, `export/review_candidates.py`, `fixtures/loader.py`
- **Called by:** humans, docker ENTRYPOINT, CI smoke

## Tests

- Unit: arg validation / exit codes (subprocess)
- Integration: extract on one smoke fixture → both JSON files; provenance validator pass
- Integration: missing pins → exit 3

## Milestone

R0

## Status

SPEC

## Owner

engineering
