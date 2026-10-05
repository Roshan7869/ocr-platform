# ADR-009: Benchmark before engine selection

## Status

Accepted — 2026-10-03 (user authorized implementation).

## Context

The 1,446 local PDFs are a sample of a corpus in the lakhs. The planned Paddle
engine has no demonstrated advantage on handwritten answers. Correction labor
must be measured alongside processing cost and throughput.

## Decision

Build an independent evaluation package for Tesseract, pinned Google Document AI,
and a pinned existing local vision model on the same verified answer crops.
Use document-level holdout, failure-aware scores, and explicit scale assumptions.
Do not train from scratch or select a winner without measured results.

This experimental local vision adapter does not enable production handwriting
acceptance. ADR-004's review-only posture and ADR-005's calibration gates remain
in force. Production engine specifications change only after evidence supports it.

## Consequences

Evaluation can proceed without the unimplemented production schemas/Paddle spike.
Human labels and engine configuration are required inputs. Answer crops isolate
recognition; full-page costs, registration, marks, and member-row extraction need
separate validation before deployment. See `docs/benchmark.md`.
