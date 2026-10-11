"""Relational QA — household-level integrity checks.

Rules:
  - Exactly one head (स्वयं/मुखिया/HEAD/SELF)
  - Father (पिता) must be ≥ 18
  - Wife (पत्नी) must be female (महिला)
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QAAnomaly:
    anomaly_id: str
    doc_id: str
    row_idx: int
    field_key: str
    rule: str
    severity: str
    value: str
    ctx: str
    explanation: str


class RelationalQA:
    """Validate household business rules after all members are extracted."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS qa_anomalies (
                    anomaly_id TEXT PRIMARY KEY, doc_id TEXT, run_id TEXT,
                    row_idx INT, field_key TEXT, rule TEXT, severity TEXT,
                    current_value TEXT, ctx TEXT, explanation TEXT,
                    created_at REAL DEFAULT (strftime('%s','now'))
                )
            """)

    def validate(self, doc_id: str, run_id: str, members: list[dict[str, Any]]) -> list[QAAnomaly]:
        anoms: list[QAAnomaly] = []

        # Rule 1: exactly one head
        heads = [
            i for i, m in enumerate(members)
            if m.get("relation", "").strip() in ("स्वयं", "मुखिया", "HEAD", "SELF")
        ]
        if len(heads) != 1:
            anoms.append(QAAnomaly(
                anomaly_id=f"{doc_id}_head_count", doc_id=doc_id, row_idx=-1,
                field_key="relation", rule="head_count", severity="critical",
                value=str(len(heads)), ctx=f"heads={heads}",
                explanation=f"Expected 1 head, found {len(heads)}",
            ))

        # Rule 2: father must be ≥ 18
        for i, m in enumerate(members):
            try:
                age = int(m.get("age", 0))
            except (TypeError, ValueError):
                continue
            if m.get("relation", "").strip() == "पिता" and age < 18:
                anoms.append(QAAnomaly(
                    anomaly_id=f"{doc_id}_pita_{i}", doc_id=doc_id, row_idx=i,
                    field_key="age", rule="father_age", severity="high",
                    value=str(age), ctx="relation=पिता",
                    explanation="Father under 18",
                ))

        # Rule 3: wife must be female
        for i, m in enumerate(members):
            if m.get("relation", "").strip() == "पत्नी" and m.get("gender", "").strip() == "पुरुष":
                anoms.append(QAAnomaly(
                    anomaly_id=f"{doc_id}_wife_{i}", doc_id=doc_id, row_idx=i,
                    field_key="gender", rule="wife_gender", severity="high",
                    value=m.get("gender", ""), ctx="relation=पत्नी",
                    explanation="Wife gender recorded as male",
                ))

        # Persist
        with sqlite3.connect(self.db_path) as c:
            for a in anoms:
                c.execute(
                    "INSERT OR REPLACE INTO qa_anomalies VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (a.anomaly_id, a.doc_id, run_id, a.row_idx, a.field_key,
                     a.rule, a.severity, a.value, a.ctx, a.explanation, None),
                )
        return anoms
