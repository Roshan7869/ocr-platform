"""SQLite evidence store with WAL mode.

Tables:
  evidence_log   — per-cell OCR results + Laya decisions + composite scores
  qa_anomalies   — relational QA flags
  laya_decisions — structured Laya layer outputs per cell
  run_meta       — run-level metadata (documents processed, timestamps)
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class EvidenceStore:
    """Thread-safe SQLite store with WAL mode."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS run_meta (
                    run_id TEXT PRIMARY KEY,
                    started_at REAL,
                    finished_at REAL,
                    doc_count INTEGER DEFAULT 0,
                    cell_count INTEGER DEFAULT 0,
                    auto_count INTEGER DEFAULT 0,
                    low_conf_count INTEGER DEFAULT 0,
                    qa_flag_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                );
                CREATE TABLE IF NOT EXISTS evidence_log (
                    doc_id TEXT, run_id TEXT, cell_id TEXT, row_idx INT, field_key TEXT,
                    value TEXT, conf_visual REAL, p_prior REAL, s_spatial REAL,
                    c_consistency REAL, score REAL, route TEXT, reason TEXT,
                    low_conf INTEGER, glyph_type TEXT, engine TEXT,
                    is_ditto INTEGER, inherited_from TEXT, norm_flag TEXT,
                    created_at REAL DEFAULT (strftime('%s','now'))
                );
                CREATE TABLE IF NOT EXISTS laya_decisions (
                    doc_id TEXT, run_id TEXT, cell_id TEXT, row_idx INT, field_key TEXT,
                    layer TEXT, decision TEXT, confidence REAL, details TEXT,
                    created_at REAL DEFAULT (strftime('%s','now'))
                );
                CREATE TABLE IF NOT EXISTS qa_anomalies (
                    anomaly_id TEXT PRIMARY KEY, doc_id TEXT, run_id TEXT,
                    row_idx INT, field_key TEXT, rule TEXT, severity TEXT,
                    current_value TEXT, ctx TEXT, explanation TEXT,
                    created_at REAL DEFAULT (strftime('%s','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence_log(run_id);
                CREATE INDEX IF NOT EXISTS idx_laya_run ON laya_decisions(run_id);
                CREATE INDEX IF NOT EXISTS idx_qa_run ON qa_anomalies(run_id);
            """)

    def start_run(self, run_id: str, doc_count: int = 0) -> None:
        with sqlite3.connect(self.db_path) as c:
            c.execute("INSERT OR REPLACE INTO run_meta VALUES (?, ?, NULL, ?, 0, 0, 0, 0, 'running')",
                      (run_id, time.time(), doc_count))

    def finish_run(self, run_id: str) -> None:
        with sqlite3.connect(self.db_path) as c:
            c.execute("UPDATE run_meta SET finished_at=?, status='done' WHERE run_id=?", (time.time(), run_id))

    def log_cell(self, run_id: str, cell: dict, ocr_res: dict, laya_decision: dict,
                 norm_value: str, is_ditto: bool = False,
                 inherited_from: str = "", norm_flag: str = "") -> None:
        """Log a single cell's evidence."""
        arb = ocr_res.get("resolved", "")
        arb_conf = max((c.get("conf", 0.0) for c in ocr_res.get("candidates", [])), default=0.0)
        row = {
            "doc_id": cell.get("doc_id", ""),
            "run_id": run_id,
            "cell_id": cell.get("cell_id", ""),
            "row_idx": cell.get("row_idx", 0),
            "field_key": cell.get("field_key", ""),
            "value": norm_value,
            "conf_visual": arb_conf,
            "p_prior": laya_decision.get("p_prior", 0.0),
            "s_spatial": laya_decision.get("s_spatial", 1.0),
            "c_consistency": laya_decision.get("c_consistency", 0.85 if is_ditto else 1.0),
            "score": laya_decision.get("composite_score", 0.0),
            "route": laya_decision.get("route", "low_confidence"),
            "reason": laya_decision.get("reason", ""),
            "low_conf": 1 if laya_decision.get("requires_human", True) else 0,
            "glyph_type": laya_decision.get("glyph_type", ""),
            "engine": ocr_res.get("engine", ""),
            "is_ditto": 1 if is_ditto else 0,
            "inherited_from": inherited_from,
            "norm_flag": norm_flag,
        }
        cols = list(row.keys())
        placeholders = ",".join("?" * len(cols))
        with sqlite3.connect(self.db_path) as c:
            c.execute(f"INSERT INTO evidence_log ({','.join(cols)}) VALUES ({placeholders})",
                      list(row.values()))
            # Log each Laya layer
            for layer_name, layer_data in laya_decision.get("laya_layers", {}).items():
                details = str(layer_data).replace("'", '"')
                c.execute(
                    "INSERT INTO laya_decisions (doc_id, run_id, cell_id, row_idx, field_key, layer, decision, confidence, details) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        cell.get("doc_id", ""), run_id, cell.get("cell_id", ""),
                        cell.get("row_idx", 0), cell.get("field_key", ""),
                        layer_name,
                        layer_data.get("decision", ""),
                        layer_data.get("confidence", 0.0),
                        details,
                    ),
                )

    def log_qa_anomaly(self, anomaly: dict, run_id: str) -> None:
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT OR REPLACE INTO qa_anomalies VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    anomaly["anomaly_id"],
                    anomaly["doc_id"],
                    run_id,
                    anomaly["row_idx"],
                    anomaly["field_key"],
                    anomaly["rule"],
                    anomaly["severity"],
                    anomaly["value"],
                    anomaly["ctx"],
                    anomaly["explanation"],
                    time.time(),
                ),
            )

    def get_run_summary(self, run_id: str) -> dict:
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM run_meta WHERE run_id=?", (run_id,)).fetchone()
            if row:
                return dict(row)
            return {}

    def get_evidence(self, run_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute("SELECT * FROM evidence_log WHERE run_id=?", (run_id,)).fetchall()]

    def get_qa_anomalies(self, run_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute("SELECT * FROM qa_anomalies WHERE run_id=?", (run_id,)).fetchall()]
