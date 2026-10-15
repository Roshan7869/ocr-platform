"""PII-free structured run logging (observability.md sections 1 and 3 subset).

The provenance graph is the audit trail; runtime logs carry only ids,
hashes, reason codes, counts, and timings. Signatures accept PII-safe
scalars exclusively — there is deliberately no ``**kwargs`` passthrough,
so a caller cannot smuggle a field value, crop text, or path into a
record. Each record is one JSON object carrying ``run_id``.
"""

from __future__ import annotations

import json
import logging
import time

logger = logging.getLogger("ocr_platform.observability")

EVENT_RUN_START = "run.start"
EVENT_RUN_ERRORED = "run.errored"
EVENT_FIELD_DECISION = "field.decision"
EVENT_RUN_COMPLETE = "run.complete"


def _emit(event: str, run_id: str, fields: dict) -> None:
    record = {"event": event, "run_id": run_id, **fields}
    logger.info(json.dumps(record, sort_keys=True))


def emit_run_start(*, run_id: str) -> None:
    """Catalog ``run.start``: run identity only (hashes stay in artifacts)."""
    _emit(EVENT_RUN_START, run_id, {"wall_time": round(time.time(), 3)})


def emit_run_errored(*, run_id: str, reason_code: str) -> None:
    """Catalog ``run.errored``: reason code only, never document content."""
    _emit(EVENT_RUN_ERRORED, run_id, {"reason_code": reason_code})


def emit_field_decision(
    *,
    run_id: str,
    field_id: str,
    disposition: str,
    primary_reason: str,
    accepted_by: str,
) -> None:
    """Catalog ``field.decision``: ids, disposition, codes — never values."""
    _emit(
        EVENT_FIELD_DECISION,
        run_id,
        {
            "field_id": field_id,
            "disposition": disposition,
            "primary_reason": primary_reason,
            "accepted_by": accepted_by,
        },
    )


def emit_run_complete(
    *,
    run_id: str,
    accepted: int,
    review: int,
    errored: int,
    wall_ms: int,
) -> None:
    """Catalog ``run.complete``: aggregate counts and wall time only."""
    _emit(
        EVENT_RUN_COMPLETE,
        run_id,
        {
            "accepted": accepted,
            "review": review,
            "errored": errored,
            "wall_ms": wall_ms,
        },
    )
