# ADR-011: Local supervised training pilots

Status: Accepted for experimentation, 2026-10-05; user requested fine-tuning and independent inspection of data/.

Use an existing pretrained classifier and locally curated supervision. Permit explicitly marked engineering visual drafts and synthetic prototypes only in pilot mode; do not treat them as independent gold. Keep source-document hashes disjoint across splits, reject model predictions as targets, and keep synthetic examples out of evaluation.

Use the official Laya training implementation, local checkpoint/source fingerprints, separate validation and comparative evaluation. Preserve the default model and disabled acceptance gates. Candidates need demonstrated improvements on independently verified data before promotion; this pilot has not met that condition.

Raw surveys, crop evidence, transcriptions and model weights remain local and ignored. This local experiment does not register production fixtures, complete R0, approve the survey codebook, fine-tune PaddleOCR or supersede ADR-004/005. See docs/fine-tuning.md and the pilot report.
