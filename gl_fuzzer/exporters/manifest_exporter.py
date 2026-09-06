"""Audit Ground-Truth Manifest exporter in JSON and Parquet formats."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Tuple
import pyarrow as pa
import pyarrow.parquet as pq

from gl_fuzzer.models.manifest import GroundTruthManifest


class ManifestExporter:
    """Exports GroundTruthManifest with cryptographic SHA-256 seal."""

    @classmethod
    def export_json(cls, manifest: GroundTruthManifest, output_path: str | Path) -> Tuple[Path, str]:
        """Writes formatted JSON manifest and computes SHA-256 hash."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        data = manifest.model_dump(mode="json")
        json_bytes = json.dumps(data, indent=2).encode("utf-8")

        manifest_hash = hashlib.sha256(json_bytes).hexdigest()
        data["manifest_sha256"] = manifest_hash

        # Re-write with hash included
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Write standard detached checksum file
        sha_path = out_path.with_name(out_path.name + ".sha256")
        with open(out_path, "rb") as f_in, open(sha_path, "w", encoding="utf-8") as f_out:
            file_digest = hashlib.sha256(f_in.read()).hexdigest()
            f_out.write(f"{file_digest}  {out_path.name}\n")

        return out_path, manifest_hash

    @classmethod
    def export_parquet(cls, manifest: GroundTruthManifest, output_path: str | Path) -> Tuple[Path, str]:
        """Writes anomaly records to a flat Parquet table for direct ML model evaluation."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for anom in manifest.anomalies:
            rows.append({
                "anomaly_id": anom.anomaly_id,
                "anomaly_type": anom.anomaly_type.value,
                "sox_control": anom.sox_control,
                "audit_script": anom.audit_script,
                "risk_level": anom.risk_level,
                "description": anom.description,
                "affected_entry_ids": ",".join(anom.affected_entry_ids),
                "affected_line_ids": ",".join(anom.affected_line_ids),
                "parameters_json": json.dumps(anom.parameters),
                "forensic_indicator": anom.forensic_indicator,
            })

        schema = pa.schema([
            ("anomaly_id", pa.string()),
            ("anomaly_type", pa.string()),
            ("sox_control", pa.string()),
            ("audit_script", pa.string()),
            ("risk_level", pa.string()),
            ("description", pa.string()),
            ("affected_entry_ids", pa.string()),
            ("affected_line_ids", pa.string()),
            ("parameters_json", pa.string()),
            ("forensic_indicator", pa.string()),
        ])

        table = pa.Table.from_pylist(rows, schema=schema)
        pq.write_table(table, out_path, compression="snappy")

        hasher = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return out_path, hasher.hexdigest()
