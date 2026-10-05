# ADR-010: Local OCR and classifier trial

Status: Accepted for experimentation, 2026-10-04.

The user authorized building PaddleOCR → deterministic validation → Laya → human review. Test existing checkpoints on annotated survey answer crops before considering fine-tuning. Keep transcription and category suggestions separate. Preserve original observations and evidence, and append human corrections with provenance. No model result is automatically accepted. Draft occupation categories require a survey codebook before accuracy evaluation.

This adds an experimental CLI, not the production registration, table extraction or handwriting acceptance path. ADR-004 and ADR-005 remain in force for production. Simulated smoke tests validate wiring only; real checkpoint trials and independently labeled holdout results remain necessary.

See [flow guide](../flow.md).
