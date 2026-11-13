"""Short loopback-only Prometheus scrape regression; no Kafka or Flink runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "flink_jobmanager_numRunningJobs",
    "flink_jobmanager_job_numberOfCompletedCheckpoints",
    "flink_jobmanager_job_lastCheckpointDuration",
    "flink_taskmanager_Status_JVM_Memory_Heap_Used",
    "flink_jobmanager_Status_JVM_Memory_Heap_Used",
    "flink_jobmanager_Status_JVM_CPU_Load",
    "flink_taskmanager_Status_JVM_CPU_Load",
    "flink_taskmanager_job_task_numRecordsIn",
    "flink_taskmanager_job_task_operator_currentInputWatermark",
    "flink_taskmanager_job_task_operator_pendingRecords",
    "flink_taskmanager_job_task_operator_eligible",
    "flink_taskmanager_job_task_operator_duplicate",
    "flink_taskmanager_job_task_operator_late",
}


def flink_block(path: Path) -> str:
    """Replay the real metric relabeling and bounds rather than a copied policy."""
    text = path.read_text(encoding="utf8")
    block = text.split("  - job_name: flink\n", 1)[1].split("\n  - job_name:", 1)[0]
    return "  - job_name: flink\n" + block.rstrip() + "\n"


def samples(count: int, phase: int, saved: Path | None) -> bytes:
    """Use retained label shapes with synthetic values; fill to the declared size."""
    rows: dict[str, str] = {}
    if saved is not None:
        source = cast(dict[str, object], json.loads(saved.read_bytes()))
        for labels in cast(list[dict[str, str]], source["data"]):
            name = labels.get("__name__", "")
            if not name.startswith("flink_") or "_split_" in name:
                continue
            attrs = ",".join(
                key + "=" + json.dumps(value, ensure_ascii=False)
                for key, value in sorted(labels.items())
                if key not in {"__name__", "instance", "job"}
            )
            rows[name + ("{" + attrs + "}" if attrs else "")] = "1"
    names = {key.split("{", 1)[0] for key in rows}
    for name in sorted(REQUIRED - names):
        rows[name] = "1"
    rows["flink_probe_phase"] = str(phase)
    if len(rows) > count:
        raise ValueError("fixture_inventory_exceeds_count")
    for index in range(count - len(rows)):
        rows[f'flink_probe_sample{{operator_name="lane_{index}"}}'] = "1"
    body = "".join(key + " " + value + "\n" for key, value in rows.items())
    # These would collide if split labels were stripped rather than dropped.
    body += "".join(
        f'flink_probe_split_noise{{split="{index}"}} 1\n' for index in range(100)
    )
    return body.encode("utf8")


def check(binary: Path, evidence: Path, saved: Path | None) -> None:
    """Reproduce old rejection, full admission, bounded refusal and recovery."""
    if os.name != "posix":
        raise ValueError("native_linux_probe_required")
    reload_signal = getattr(signal, "SIGHUP", None)
    if not isinstance(reload_signal, int):
        raise ValueError("sighup_required")
    evidence = evidence.resolve()
    evidence.mkdir(exist_ok=False)
    work = Path(tempfile.mkdtemp(prefix="fleet-flink-scrape-"))
    block = flink_block(ROOT / "runtime/continuous/prometheus.yml")
    if block != flink_block(ROOT / "runtime/observability/prometheus.yml"):
        raise ValueError("flink_scrape_policies_differ")
    body = samples(10638, 1, saved)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/metrics":
                self.send_error(404)
                return
            payload = body
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    target = f"127.0.0.1:{server.server_port}"
    block = block.replace("jobmanager:9249, taskmanager:9249", target)
    config = work / "prometheus.yml"

    def configure(limit: int) -> None:
        config.write_text(
            "global:\n  scrape_interval: 2s\n  evaluation_interval: 2s\n"
            + "rule_files: ["
            + str(ROOT / "runtime/observability/alerts.yml")
            + "]\n"
            + "scrape_configs:\n"
            + block.replace("sample_limit: 20000", f"sample_limit: {limit}"),
            encoding="utf8",
        )

    def query(expression: str) -> list[dict[str, object]]:
        with urlopen(
            f"http://127.0.0.1:{port}/api/v1/query?" + urlencode({"query": expression}),
            timeout=2,
        ) as response:
            row = json.loads(response.read(2 * 1024 * 1024))
        if row["status"] != "success":
            raise ValueError("probe_promql_failed")
        return cast(list[dict[str, object]], row["data"]["result"])

    def value(expression: str) -> float | None:
        result = query(expression)
        return float(cast(list[str], result[0]["value"])[1]) if result else None

    configure(4000)
    log = (evidence / "prometheus.log").open("x", encoding="utf8")
    process = subprocess.Popen(
        [
            str(binary),
            "--config.file=" + str(config),
            "--storage.tsdb.path=" + str(work / "tsdb"),
            f"--web.listen-address=127.0.0.1:{port}",
            "--storage.tsdb.retention.time=5m",
            "--storage.tsdb.retention.size=32MB",
            "--query.max-samples=100000",
            "--query.max-concurrency=2",
            "--log.format=json",
        ],
        env=dict(os.environ, GOMEMLIMIT="192MiB", GOMAXPROCS="2"),
        stdout=log,
        stderr=log,
    )
    deadline = time.monotonic() + 45
    peak_rss_kib = 0

    def wait_for(expression: str, expected: float) -> None:
        nonlocal peak_rss_kib
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ValueError("probe_prometheus_exited")
            status = Path(f"/proc/{process.pid}/status").read_text()
            rss = int(status.split("VmRSS:", 1)[1].split()[0])
            peak_rss_kib = max(peak_rss_kib, rss)
            if rss > 384 * 1024:
                raise ValueError("probe_memory_pressure")
            try:
                if value(expression) == expected:
                    return
            except OSError:
                pass
            time.sleep(0.2)
        raise ValueError("probe_deadline")

    try:
        wait_for('up{job="flink"}', 0)
        # The old guard must have actually attempted this fixture before failure.
        wait_for('scrape_samples_post_metric_relabeling{job="flink"}', 10638)
        if query("flink_probe_phase"):
            raise ValueError("old_failed_scrape_published_samples")
        body = samples(10638, 2, saved)
        configure(20000)
        process.send_signal(reload_signal)
        wait_for("flink_probe_phase", 2)
        wait_for('up{job="flink"}', 1)
        wait_for('count({job="flink",__name__=~"flink_.*"})', 10638)
        for name in REQUIRED:
            if value("count(" + name + ")") is None:
                raise ValueError("required_dashboard_metric_missing")
        if query("flink_probe_split_noise"):
            raise ValueError("split_filter_failed")
        body = samples(20001, 3, saved)
        wait_for('up{job="flink"}', 0)
        if value("flink_probe_phase") == 3:
            raise ValueError("overflow_published_samples")
        wait_for(
            'ALERTS{alertname="TelemetryTargetUnavailable",alertstate="firing",job="flink"}',
            1,
        )
        body = samples(10638, 4, saved)
        wait_for("flink_probe_phase", 4)
        wait_for('up{job="flink"}', 1)
        wait_for('count({job="flink",__name__=~"flink_.*"})', 10638)
        wait_for(
            'absent(ALERTS{alertname="TelemetryTargetUnavailable",alertstate="firing",job="flink"})',
            1,
        )
        report = {
            "status": "passed",
            "old_limit": 4000,
            "new_limit": 20000,
            "admitted_samples": 10638,
            "overflow_samples": 20001,
            "dropped_split_samples": 100,
            "required_metric_names": sorted(REQUIRED),
            "peak_rss_kib": peak_rss_kib,
            "prometheus_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "saved_inventory_sha256": None
            if saved is None
            else hashlib.sha256(saved.read_bytes()).hexdigest(),
            "values_are_synthetic": True,
        }
        (evidence / "complete.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--saved-series", type=Path)
    args = parser.parse_args()
    check(args.prometheus.resolve(), args.evidence, args.saved_series)
