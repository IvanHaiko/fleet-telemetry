"""Aggregate live continuous counters; no event or vehicle metric labels."""

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from runtime.clickhouse.transport import HttpConfig, _request
from runtime.continuous.kafka import Kafka
from telemetry.continuous_archive import object_row, require


def run(config_path: Path, state: Path, port: int, host: str = "0.0.0.0") -> None:
    config = object_row(json.loads(config_path.read_bytes()))
    source = object_row(config["source"])
    kafka = Kafka(
        cast(str, config["bootstrap"]),
        cast(str, source["cluster_id"]),
        config.get("kafka_connection"),
    )
    consumer = kafka.consumer(cast(str, config["run_id"]) + "-metrics-v1")
    reader = HttpConfig(**cast(dict[str, str | int], config["reader"]))  # type: ignore[arg-type]
    snapshot = b"telemetry_continuous_collection_ok 0\n"
    lock = threading.Lock()

    def collect() -> None:
        nonlocal snapshot
        while True:
            values: dict[str, int | float] = {"collection_ok": 0}
            try:
                require(
                    kafka.describe(cast(str, source["topic"])) == source,
                    "metrics_source_changed",
                )
                positions = kafka.positions(
                    cast(str, source["topic"]), dict.fromkeys(map(str, range(18)), 0)
                )
                values["input_records"] = sum(
                    consumer.get_watermark_offsets(p, timeout=5, cached=False)[1]
                    for p in positions
                )
                archive = object_row(
                    json.loads((state / "archive/cursor.json").read_bytes())
                )
                values["archived_records"] = sum(
                    cast(int, object_row(v)["next"])
                    for v in object_row(archive["partitions"]).values()
                )
                raw = _request(
                    reader,
                    "SELECT kind, "
                    "uniqExact(tuple(output_partition,output_offset)) AS facts "
                    "FROM continuous_facts_v1 WHERE run_id={run:String} "
                    "GROUP BY kind SETTINGS max_execution_time=10,"
                    "max_memory_usage=268435456 FORMAT JSONEachRow",
                    b"",
                    parameters={
                        "database": reader.database,
                        "param_run": cast(str, config["run_id"]),
                    },
                )
                totals = {
                    json.loads(row)["kind"]: json.loads(row)["facts"]
                    for row in raw.splitlines()
                }
                for kind in ("event", "window", "invalid"):
                    values[kind + "_facts"] = int(totals.get(kind, 0))
                raw = _request(
                    reader,
                    "SELECT uniqExact(JSONExtractString(fact_json,'event','event_id')) "
                    "AS measurements FROM continuous_facts_v1 "
                    "WHERE run_id={run:String} AND kind='event' "
                    "SETTINGS max_execution_time=10,max_memory_usage=268435456 "
                    "FORMAT JSONEachRow",
                    b"",
                    parameters={
                        "database": reader.database,
                        "param_run": cast(str, config["run_id"]),
                    },
                )
                values["unique_measurements"] = int(json.loads(raw)["measurements"])
                raw = _request(
                    reader,
                    "SELECT JSONExtractString(fact_json,'disposition') AS disposition, "
                    "uniqExact(tuple(output_partition,output_offset)) AS facts "
                    "FROM continuous_facts_v1 WHERE run_id={run:String} "
                    "AND kind='event' "
                    "GROUP BY disposition SETTINGS max_execution_time=10,"
                    "max_memory_usage=268435456 FORMAT JSONEachRow",
                    b"",
                    parameters={
                        "database": reader.database,
                        "param_run": cast(str, config["run_id"]),
                    },
                )
                counts = {
                    json.loads(row)["disposition"]: json.loads(row)["facts"]
                    for row in raw.splitlines()
                }
                for kind in ("eligible", "late", "duplicate", "conflict"):
                    values[kind + "_deliveries"] = int(counts.get(kind, 0))
                values["archive_lag_records"] = (
                    values["input_records"] - values["archived_records"]
                )
                values["collection_ok"] = 1
                values["observed_unix_seconds"] = time.time()
            except (OSError, ValueError, RuntimeError):
                # Failed reads do not turn stale counts into a successful sample.
                pass
            except Exception as error:
                # Native SDK exceptions are not stable public Python subclasses.
                print(
                    json.dumps(
                        {
                            "event": "continuous_metrics_unavailable",
                            "exception": type(error).__name__,
                        }
                    ),
                    flush=True,
                )
            body = "".join(
                f"# TYPE telemetry_continuous_{k} gauge\ntelemetry_continuous_{k} {v}\n"
                for k, v in sorted(values.items())
            ).encode()
            with lock:
                snapshot = body
            time.sleep(30)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/metrics":
                self.send_error(404)
                return
            with lock:
                body = snapshot
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    threading.Thread(target=collect, daemon=True).start()
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18766)
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="0.0.0.0")
    args = parser.parse_args()
    run(args.config, args.state, args.port, args.host)
