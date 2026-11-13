"""Run one bounded probe and verify its external observations and environment."""

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import cast

from bootstrap import HERE, command, environment, obj, owned_path, paths, sha256, text


class ProfileCommandError(ValueError):
    """Keep the actual failing preflight command in the retained report."""

    def __init__(self, result: dict[str, object]) -> None:
        super().__init__("profile_command_failed")
        self.result = result


def require(condition: bool, reason: str) -> None:
    """Keep verification active with optimized Python."""
    if not condition:
        raise ValueError(reason)


def worker_result(result: dict[str, object]) -> None:
    """Literal boundary expectations, independent of the worker's conversion."""
    expected: list[object] = [
        {
            "kind": "timestamp",
            "label": label,
            "event_ms": value,
            "assigned_ms": value,
            "worker_python": "3.12.13",
        }
        for label, value in (
            ("pre-epoch", -1),
            ("epoch", 0),
            ("before-edge", 9999),
            ("edge", 10000),
            ("after-edge", 10000),
        )
    ]
    expected.append({"kind": "invalid", "label": "invalid"})
    rows = result.get("rows")
    if not isinstance(rows, list):
        raise ValueError("missing_worker_rows")
    require(
        sorted(json.dumps(v, sort_keys=True) for v in cast(list[object], rows))
        == sorted(json.dumps(v, sort_keys=True) for v in expected),
        "worker_boundary_result_differs",
    )
    require(result.get("status") == "worker_probe_completed", "incomplete_worker")


def expected_kafka(topic: str, events: Path) -> list[object]:
    """Compare original source key/value hashes at each explicit offset."""
    import hashlib

    with events.open("rb") as source:
        data = source.read(3 * 65536 + 4)
    values = data.splitlines()
    require(
        len(data) <= 3 * 65536 + 3 and len(values) == 3, "three_event_input_required"
    )
    expected: list[object] = []
    for offset, wire in enumerate(values):
        raw: object = json.loads(wire)
        vehicle = text(obj(raw)["vehicle_id"])
        expected.append(
            {
                "topic": topic,
                "partition": 0,
                "offset": offset,
                "key_sha256": hashlib.sha256(vehicle.encode()).hexdigest(),
                "value_sha256": hashlib.sha256(wire).hexdigest(),
            }
        )
    return expected


def checked_command(
    args: list[str], env: dict[str, str], cwd: Path
) -> dict[str, object]:
    """Require both successful exit and completed owned process-group shutdown."""
    result = command(args, env, cwd, timeout=180)
    if (
        result["exit_code"] != 0
        or result["timed_out"]
        or not result["owned_process_group_ended"]
    ):
        raise ProfileCommandError(result)
    return result


def inventory(directory: Path, env: dict[str, str]) -> dict[str, object]:
    """Bind installed packages, JARs and native extensions to the locked profile."""
    selected = paths(directory)
    python = selected["venv"] / "bin/python"
    query = (
        "import importlib.metadata as m,json,platform,sys; "
        "print(json.dumps({'python':platform.python_version(),'prefix':sys.prefix,"
        "'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))"
    )
    result = checked_command([str(python), "-B", "-c", query], env, HERE)
    raw: object = json.loads(text(result["stdout"]))
    actual = obj(raw)
    require(actual["python"] == "3.12.13", "wrong_python")
    require(actual["prefix"] == str(selected["venv"]), "wrong_environment")
    package_rows = obj(actual["packages"])
    normalized = {
        k.lower().replace("_", "-").replace(".", "-"): v
        for k, v in package_rows.items()
    }
    lock: object = tomllib.loads((HERE / "uv.lock").read_text())
    packages = obj(lock)["package"]
    if not isinstance(packages, list):
        raise ValueError("invalid_dependency_lock")
    expected = {}
    for raw_package in cast(list[object], packages):
        package = obj(raw_package)
        if "sdist" in package or "wheels" in package:
            expected[text(package["name"])] = text(package["version"])
    require(normalized == expected, "installed_package_graph_differs")
    pins = obj(json.loads((HERE / "artifacts.json").read_bytes()))
    connector = obj(obj(pins["artifacts"])["kafka_sql"])
    require(
        sha256(selected["connector"]) == text(connector["sha256"]),
        "connector_hash_differs",
    )
    java = checked_command(
        [str(selected["java_home"] / "bin/java"), "-version"], env, HERE
    )
    require("17.0.20.1" in text(java["stderr"]), "wrong_java")
    actual["java"] = java
    actual["input_hashes"] = input_hashes(directory)
    return actual


def input_hashes(directory: Path) -> dict[str, str]:
    """Record the JAR/native binary boundary independently of package versions."""
    selected = paths(directory)
    files = {
        p
        for p in selected["venv"].rglob("*")
        if p.is_file()
        and (p.suffix in {".jar", ".so"} or p.name in {"METADATA", "RECORD"})
    }
    files.update(
        (selected["connector"], selected["python"], selected["java_home"] / "bin/java")
    )
    files.update(selected["java_home"].rglob("*.jar"))
    files.add(selected["java_home"] / "lib/server/libjvm.so")
    return {str(p.relative_to(directory)): sha256(p) for p in sorted(files)}


def execute(
    directory: Path, output: Path, kind: str, topic: str | None, events: Path | None
) -> None:
    """Retain a fresh report, including actual failed commands and source hashes."""
    directory, output = owned_path(directory), owned_path(output)
    require(not output.exists(), "fresh_probe_report_required")
    selected = paths(directory)
    env = environment(directory)
    env["JAVA_TOOL_OPTIONS"] = "-Xmx1024m"
    source_paths = [
        *HERE.glob("*.py"),
        HERE / "pyproject.toml",
        HERE / "uv.lock",
        HERE / "artifacts.json",
    ]
    before = {p.name: sha256(p) for p in source_paths}
    report: dict[str, object] = {"status": "incomplete", "source_before": before}
    try:
        report["environment"] = inventory(directory, env)
        python = selected["venv"] / "bin/python"
        scratch = directory / "runs" / (kind + "-" + output.stem)
        args = [
            str(python),
            "-B",
            str(HERE / (kind + "_probe.py")),
            "--scratch",
            str(scratch),
        ]
        expected: list[object] = []
        if kind == "kafka":
            require(topic is not None and events is not None, "kafka_input_required")
            if topic is None or events is None:
                raise ValueError("kafka_input_required")
            expected = expected_kafka(topic, events)
            report["expected_events_sha256"] = sha256(events)
            args += [
                "--connector",
                str(selected["connector"]),
                "--topic",
                topic,
                "--end",
                "3",
            ]
        result = command(args, env, HERE, timeout=180)
        report["execution"] = result
        require(
            result["exit_code"] == 0
            and not result["timed_out"]
            and bool(result["owned_process_group_ended"]),
            "probe_execution_failed",
        )
        decoded: object = json.loads(text(result["stdout"]))
        value = obj(decoded)
        if kind == "worker":
            worker_result(value)
        else:
            rows = value.get("rows")
            require(isinstance(rows, list), "missing_kafka_rows")
            require(
                value.get("status") == "kafka_probe_completed" and rows == expected,
                "kafka_source_positions_or_bytes_differ",
            )
            require(
                events is not None
                and sha256(events) == report["expected_events_sha256"],
                "expected_source_changed",
            )
        report["result"] = value
        report["status"] = kind + "_probe_verified"
    except ProfileCommandError as error:
        report["failed_preflight"] = error.result
        report["failure_reason"] = str(error)
        raise
    except ValueError as error:
        report["failure_reason"] = str(error)
        raise
    except (OSError, KeyError) as error:
        report["failure_reason"] = type(error).__name__
        raise
    finally:
        report["source_after"] = {p.name: sha256(p) for p in source_paths}
        report["source_unchanged"] = before == report["source_after"]
        if "environment" in report:
            report["runtime_after"] = input_hashes(directory)
            report["runtime_unchanged"] = (
                obj(report["environment"])["input_hashes"] == report["runtime_after"]
            )
        with output.open("x") as out:
            json.dump(report, out, indent=2)
    require(bool(report["source_unchanged"]), "probe_source_changed")
    require(bool(report["runtime_unchanged"]), "runtime_inputs_changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("worker", "kafka"), required=True)
    parser.add_argument("--topic")
    parser.add_argument("--expected-events", type=Path)
    args = parser.parse_args()
    try:
        execute(
            args.directory, args.output, args.kind, args.topic, args.expected_events
        )
        print(json.dumps({"status": args.kind + "_probe_verified"}))
        return 0
    except (OSError, ValueError, KeyError):
        print(
            json.dumps({"status": "failed", "reason": "compatibility_check_failed"}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
