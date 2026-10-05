# Documentation audit — 2026-10-05

Reviewed the architecture, sequences, accuracy/data/testing plans, reason registry,
annotation workflow, data dictionary, CI/observability specifications,
handwriting posture, ADR-004/005/009/010 and the implemented-file contracts.
This audit covers the experimental benchmark, crop flow and classifier training.
It does not certify the planned production extractor.

| Document requirement | Implementation / remaining gap |
|---|---|
| ADR-004: handwriting review-only | All model decisions remain review; v2 records HANDWRITING_SUSPECTED when the input kind declares handwriting |
| ADR-005: calibration before acceptance | Auto-accept remains disabled, including after training; no trained candidate is promoted |
| reason-codes.md: canonical tokens | Replaced LOW_OCR_CONFIDENCE with OCR_CONFIDENCE_LOW and UNRESOLVED_DITTO with DITTO_UNRESOLVED; registered experimental additions |
| Invalid numeric / unknown vocabulary | INVALID_NUMERIC accompanies detailed failures; invalid/unconfigured OCR values use unknown state |
| Explicit page coordinates | New evidence carries coordinate_system=image_top_left_normalized; flow version bumped to 2, preserving old journals |
| Immutable human provenance | Corrections append chained revisions and preserve original OCR/crops; this is experimental provenance, not the planned full production DAG |
| data-plan: private local experiments | User-authorized local trials only; raw PDFs, crops, draft labels and weights stay ignored. Production fixture approvals remain pending |
| Training/holdout separation | Enforce source-document/group hashes across train/validation/holdout; reject model outputs as targets |
| Gold vs pilot | Draft visual/synthetic supervision requires --pilot; synthetic examples cannot be evaluation cases |
| ci-spec: docs gate | Implemented scripts/check_docs_contract.py and added it to CI; this checks mirrored sections/status, not GitNexus roles |
| Per-file docs | Added responsibility contracts for every non-trivial implemented file; status remains IMPLEMENTED |
| Laya modality | Corrected handwriting-decision-tree.md: Laya consumes text, not document images |
| Production L0–L5 / templates / row detection | Still SPEC. The crop experiment bypasses registration, row detection and canonical Household/Member exports |
| Full R0/G1–G7 and compatibility spike | Not complete; benchmark CI does not establish R0 exit or production calibration |

The field IDs and categories in flow_rules_v1.json remain an experimental draft.
They do not replace the survey-owned field catalog or vocabularies. No template,
codebook, fixture-classification or accuracy gate is silently marked complete.
See [fine-tuning guide](fine-tuning.md) and
[pilot report](test-results/fine-tuning-pilot-2026-10-05.md).

Verification: 41 regression tests, Ruff lint/format checks and the implemented-file
docs gate pass. A real v2 reclassification of the prior 23 crop observations
retained 23 reviews / 0 accepted, marked all 20 declared handwriting crops,
and attached explicit coordinate tags to every evidence record.
