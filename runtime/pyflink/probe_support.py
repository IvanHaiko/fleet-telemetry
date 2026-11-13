"""Small embedded-runtime configuration shared by the two bounded probes."""

import json
import sys
from collections.abc import Iterable
from pathlib import Path

from pyflink.common import Configuration
from pyflink.datastream import (
    DataStream,
    RuntimeExecutionMode,
    StreamExecutionEnvironment,
)
from pyflink.datastream.data_stream import CloseableIterator


def execution_environment(scratch: Path, slots: int = 1) -> StreamExecutionEnvironment:
    """Use bounded local slots, process workers, explicit Python and loopback RPC."""
    scratch.mkdir(parents=True, exist_ok=False)
    config = Configuration()
    for key, value in {
        "jobmanager.bind-host": "127.0.0.1",
        "jobmanager.rpc.address": "127.0.0.1",
        "taskmanager.bind-host": "127.0.0.1",
        "taskmanager.host": "127.0.0.1",
        "rest.bind-address": "127.0.0.1",
        "rest.address": "127.0.0.1",
        "rest.bind-port": "0",
        "taskmanager.memory.process.size": "1024m",
        "io.tmp.dirs": str(scratch),
        "python.executable": sys.executable,
        "python.client.executable": sys.executable,
        "python.execution-mode": "process",
    }.items():
        config.set_string(key, value)
    config.set_integer("taskmanager.numberOfTaskSlots", slots)
    config.set_integer("python.fn-execution.bundle.size", 1)
    env = StreamExecutionEnvironment.get_execution_environment(config)
    env.set_parallelism(1)
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
    env.add_python_file(str(Path(__file__).resolve()))
    return env


def collected_json(values: Iterable[object], maximum: int) -> list[object]:
    """Bound probe output; callers must consume finite EOF, not just N rows."""
    result: list[object] = []
    for value in values:
        if (
            not isinstance(value, str)
            or len(result) >= maximum
            or len(value.encode()) > 65536
        ):
            raise ValueError("probe_output_limit")
        decoded: object = json.loads(value)
        result.append(decoded)
    return result


def collect_output(stream: DataStream, maximum: int, name: str) -> list[object]:
    """Require the finite iterator API and always close the Flink result handle."""
    iterator = stream.execute_and_collect(job_execution_name=name)
    if not isinstance(iterator, CloseableIterator):
        raise ValueError("unexpected_result_handle")
    with iterator as rows:
        return collected_json(rows, maximum)
