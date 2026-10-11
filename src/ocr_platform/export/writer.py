"""Export Engine — per-household JSON + long/wide CSV + ZIP."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any


class ExportEngine:
    """Write structured outputs from an evidence store."""

    def __init__(self, db_path: Path | str, out_dir: Path):
        self.db_path = str(db_path)
        self.out_dir = Path(out_dir)
        self.json_dir = self.out_dir / "households_json"
        self.csv_dir = self.out_dir / "csv"
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

    def export(self, run_id: str, col_keys: list[str]) -> dict[str, str] | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT * FROM evidence_log WHERE run_id=?", (run_id,)
        ).fetchall()
        if not rows:
            conn.close()
            return None

        evidence = [dict(r) for r in rows]

        # Long CSV (cell-level)
        import pandas as pd
        df = pd.DataFrame(evidence)
        long_csv = self.csv_dir / "extracted_cells_long.csv"
        df.to_csv(long_csv, index=False, encoding="utf-8-sig")

        # Anomaly CSV
        anomalies = conn.execute(
            "SELECT * FROM qa_anomalies WHERE run_id=?", (run_id,)
        ).fetchall()
        anom_path = None
        if anomalies:
            anom_path = self.csv_dir / "qa_anomalies.csv"
            pd.DataFrame([dict(r) for r in anomalies]).to_csv(anom_path, index=False, encoding="utf-8-sig")

        # Wide CSV (one row per household member)
        wide = df.pivot_table(
            index=["doc_id", "row_idx"], columns="field_key",
            values="value", aggfunc="first",
        ).reset_index()
        wide_csv = self.csv_dir / "households_wide.csv"
        wide.to_csv(wide_csv, index=False, encoding="utf-8-sig")

        # Per-household JSON
        for doc_id in sorted(df["doc_id"].unique()):
            doc_df = df[df["doc_id"] == doc_id]
            members = []
            for ri in sorted(doc_df["row_idx"].unique()):
                row = doc_df[doc_df["row_idx"] == ri]
                m = {}
                for fk in col_keys:
                    match = row[row["field_key"] == fk]
                    m[fk] = match["value"].iloc[0] if len(match) else ""
                m["row_idx"] = int(ri)
                if "score" in row.columns and len(row):
                    m["composite_score"] = float(row["score"].iloc[0])
                if "route" in row.columns and len(row):
                    m["route"] = row["route"].iloc[0]
                if "low_conf" in row.columns and len(row):
                    m["low_confidence_fields"] = [
                        fk for fk in col_keys
                        if len(row[(row["field_key"] == fk) & (row["low_conf"] == 1)])
                    ]
                members.append(m)
            hh = {
                "doc_id": doc_id,
                "run_id": run_id,
                "total_members": len(members),
                "members": members,
                "qa_anomalies": [dict(r) for r in anomalies] if anomalies else [],
            }
            jp = self.json_dir / f"{doc_id}_household.json"
            jp.write_text(json.dumps(hh, ensure_ascii=False, indent=2), encoding="utf-8")

        conn.close()
        print(f"  [M10] Exported {len(evidence)} cells across {df['doc_id'].nunique()} docs.")
        print(f"  [M10] JSON → {self.json_dir}")
        print(f"  [M10] CSV  → {self.csv_dir}")
        return {
            "long_csv": str(long_csv),
            "wide_csv": str(wide_csv),
            "json_dir": str(self.json_dir),
            "anomalies_csv": str(anom_path) if anom_path else "",
        }

    def make_zip(self, run_id: str) -> Path:
        zip_path = self.out_dir / f"{run_id}_output.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(self.out_dir.rglob("*")):
                if f.is_file() and f != zip_path:
                    zf.write(f, f.relative_to(self.out_dir))
        print(f"  [M10] ZIP: {zip_path} ({zip_path.stat().st_size // 1024} KB)")
        return zip_path
