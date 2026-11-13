"""Create and reconcile one isolated F09 ClickHouse research database."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from runtime.clickhouse.transport import HttpConfig, _request
from telemetry.conversion_contract import json_object
from ulog_integrity import F09_SOURCE_ID

DATABASE = "f09_flight_analytics_v1"
EXPECTED = 21054


def load(prepared: Path, port: int) -> None:
    """Load a fresh scope; never replace a prior database or print measurements."""
    password = os.environ["FLIGHT_CH_ADMIN_PASSWORD"]
    reader_password = os.environ["FLIGHT_CH_READER_PASSWORD"]
    if len(reader_password) < 16 or len(password) < 16 or password == reader_password:
        raise ValueError("invalid_credentials")
    manifest = json_object((prepared / "manifest.json").read_bytes())
    data = (prepared / "gps.jsonl").read_bytes()
    if (
        manifest.get("source_id") != F09_SOURCE_ID
        or manifest.get("records") != EXPECTED
        or manifest.get("rows_sha256") != hashlib.sha256(data).hexdigest()
    ):
        raise ValueError("prepared_data_mismatch")
    lines = data.splitlines()
    if len(lines) != EXPECTED:
        raise ValueError("prepared_record_count")
    entries = [json_object(line) for line in lines]
    if [row.get("source_ordinal") for row in entries] != list(range(EXPECTED)):
        raise ValueError("prepared_ordinal_mismatch")
    expected = {
        str(row["event_id"]): hashlib.sha256(line).hexdigest().upper()
        for row, line in zip(entries, lines, strict=True)
    }
    if len(expected) != EXPECTED:
        raise ValueError("prepared_identity_conflict")
    admin = HttpConfig(port, "default", "flight_admin", password, timeout_seconds=15)
    exists = _request(
        admin,
        "SELECT count() FROM system.databases "
        "WHERE name={name:String} FORMAT TabSeparated",
        b"",
        parameters={"param_name": DATABASE},
    )
    if exists.strip() != b"0":
        raise ValueError("database_exists")
    _request(admin, f"CREATE DATABASE {DATABASE}", b"", write=True)
    _request(
        admin,
        Path("runtime/flight_analytics/gps-v1.sql").read_text(encoding="utf-8"),
        b"",
        write=True,
    )
    for start in range(0, len(entries), 500):
        batch = []
        for row, raw in zip(
            entries[start : start + 500], lines[start : start + 500], strict=True
        ):
            batch.append(
                json.dumps(
                    {**row, "row_json": raw.decode("utf-8")},
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode()
                + b"\n"
            )
        _request(
            admin,
            f"INSERT INTO {DATABASE}.gps_v1 "
            "SETTINGS date_time_input_format='best_effort' FORMAT JSONEachRow",
            b"".join(batch),
            write=True,
        )
    result = _request(
        admin,
        f"SELECT event_id, hex(SHA256(row_json)) AS sha256 FROM {DATABASE}.gps_v1 "
        "ORDER BY event_id FORMAT JSONEachRow",
        b"",
    )
    actual_rows = [json_object(line) for line in result.splitlines()]
    actual = {str(row["event_id"]): str(row["sha256"]) for row in actual_rows}
    if len(actual_rows) != EXPECTED or actual != expected:
        raise ValueError("sql_readback_mismatch")
    typed_body = _request(
        admin,
        f"SELECT * EXCEPT(row_json) FROM {DATABASE}.gps_v1 "
        "ORDER BY source_ordinal FORMAT JSONEachRow",
        b"",
    )
    typed_rows = [json_object(line) for line in typed_body.splitlines()]
    if len(typed_rows) != len(entries):
        raise ValueError("typed_readback_count")
    for original, actual_row in zip(entries, typed_rows, strict=True):
        stamp = actual_row.get("gps_utc")
        if isinstance(stamp, str):
            actual_row["gps_utc"] = (
                datetime.fromisoformat(stamp)
                .replace(tzinfo=UTC)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            )
        if actual_row != original:
            raise ValueError("typed_readback_mismatch")
    _request(
        admin,
        "CREATE USER flight_reader IDENTIFIED WITH sha256_password "
        "BY {password:String}",
        b"",
        write=True,
        parameters={"param_password": reader_password},
    )
    _request(
        admin, f"GRANT SELECT ON {DATABASE}.gps_v1 TO flight_reader", b"", write=True
    )
    reader = HttpConfig(
        port, DATABASE, "flight_reader", reader_password, timeout_seconds=15
    )
    count = _request(
        reader, f"SELECT count() FROM {DATABASE}.gps_v1 FORMAT TabSeparated", b""
    )
    if count.strip() != str(EXPECTED).encode():
        raise ValueError("reader_reconciliation")
    print(
        json.dumps(
            {
                "status": "verified",
                "rows": EXPECTED,
                "identities_and_json_hashes_match": True,
                "database": DATABASE,
                "privacy": "restricted",
            }
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--port", type=int, default=28132)
    args = parser.parse_args()
    load(args.prepared, args.port)
