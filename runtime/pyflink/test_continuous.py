"""Regression for cross-partition retention, expiry accounting and fixed routing."""

import copy
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

import pytest
from pyflink.common import Configuration, Duration, Row, Types, WatermarkStrategy
from pyflink.datastream import DataStream, StreamExecutionEnvironment
from pyflink.datastream.functions import (
    KeyedProcessFunction,
    MapFunction,
    ProcessFunction,
)
from pyflink.datastream.state import ValueState
from pyflink.metrics import Counter
from tests.test_reference import event

import continuous_job
from continuous_job import check_partition_plan, partition_battery, partition_watermarks
from continuous_operator import (
    INVALID,
    PARTITION_OUTPUTS,
    TIMED,
    Battery,
    Gate,
    Timestamp,
    VehicleState,
)
from probe_support import collect_output, execution_environment


class EventVehicle(TypedDict):
    vehicle_id: str


class Fact(TypedDict, total=False):
    kind: str
    event: EventVehicle
    vehicle_id: str
    disposition: str
    vehicle: str
    count: int
    unique_events: int


class MemoryVehicleState:
    def __init__(self) -> None:
        self.data: VehicleState | None = None

    def value(self) -> VehicleState | None:
        return self.data

    def update(self, value: VehicleState) -> None:
        self.data = value

    def clear(self) -> None:
        self.data = None


def state_data(battery: Battery) -> VehicleState:
    return battery.state.value() or ({}, {}, {}, 0)


class Count:
    def __init__(self) -> None:
        self.number = 0

    def value(self) -> int:
        return self.number

    def update(self, value: int) -> None:
        self.number = value

    def inc(self) -> None:
        self.number += 1


class Context:
    def __init__(self) -> None:
        self.watermark = -(2**63)
        self.timers: set[int] = set()

    def timer_service(self) -> "Context":
        return self

    def current_watermark(self) -> int:
        return self.watermark

    def register_event_time_timer(self, stamp: int) -> None:
        self.timers.add(stamp)

    def get_current_key(self) -> str:
        return "vehicle-a"


def memory_battery() -> tuple[Battery, Context]:
    battery = Battery("test")
    battery.state = cast(ValueState[VehicleState], MemoryVehicleState())
    battery.counters = {
        name: cast(Counter, Count())
        for name in (
            "eligible",
            "duplicate",
            "conflict",
            "late",
            "expired",
            "state_limit",
        )
    }
    return battery, Context()


def value(
    index: int, stamp: int, vehicle: str = "vehicle-a"
) -> tuple[str, str, int, str]:
    doc = event(
        index,
        datetime.fromtimestamp(stamp / 1000, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        vehicle=vehicle,
    )
    return vehicle, json.dumps(doc), stamp, "{}"


def apply(battery: Battery, ctx: Context, row: tuple[str, str, int, str]) -> str:
    result = list(battery.process_element(row, cast(KeyedProcessFunction.Context, ctx)))
    return cast(str, json.loads(result[0])["disposition"])


def advance(battery: Battery, ctx: Context, watermark: int) -> None:
    ctx.watermark = watermark
    while due := sorted(t for t in ctx.timers if t <= watermark):
        for stamp in due:
            ctx.timers.remove(stamp)
            list(
                battery.on_timer(stamp, cast(KeyedProcessFunction.OnTimerContext, ctx))
            )
    assert state_data(battery)[3] == len(state_data(battery)[0])


def test_actual_4096_guard_reproduces_with_600_second_global_lag() -> None:
    battery, ctx = memory_battery()
    # Same frontier as retained checkpoint-45: slow partition at 1856 s,
    # two-second allowance and Flink's inclusive millisecond boundary.
    ctx.watermark = -2001
    for index in range(4096):
        advance(battery, ctx, min(1_853_999, (1254 + index) * 1000 - 2001))
        assert apply(battery, ctx, value(index, (1254 + index) * 1000)) == "eligible"
    assert state_data(battery)[3] == 4096
    with pytest.raises(ValueError, match="continuous_identity_state_limit"):
        apply(battery, ctx, value(4096, 5_350_000))
    assert len(state_data(battery)[0]) == 4096
    # All registered expiry timers are still in the future. A 600 s horizon
    # never promises a 600-entry cap while the watermark lags by 3496 s.
    assert min(state_data(battery)[1]) == 1_854_000
    advance(battery, ctx, 1_854_000)
    assert state_data(battery)[3] == 4095
    assert apply(battery, ctx, value(4096, 5_350_000)) == "eligible"


def test_partition_progress_bounds_state_and_preserves_duplicates() -> None:
    battery, ctx = memory_battery()
    peak = 0
    for index in range(6000):
        advance(battery, ctx, index * 1000 - 2001)
        row = value(index, index * 1000)
        assert apply(battery, ctx, row) == "eligible"
        assert apply(battery, ctx, row) == "duplicate"
        peak = max(peak, state_data(battery)[3] or 0)
        assert len(state_data(battery)[1]) <= 603
    assert peak == 603
    assert cast(Count, battery.counters["expired"]).value() == 5397
    advance(battery, ctx, 7_000_000)
    assert state_data(battery)[3] == 0
    assert not state_data(battery)[1]
    assert not state_data(battery)[2]
    assert apply(battery, ctx, value(0, 0)) == "late"
    assert state_data(battery)[3] == 0


def test_subsecond_expiry_stale_bucket_and_conflict() -> None:
    battery, ctx = memory_battery()
    row = value(0, 123)
    assert apply(battery, ctx, row) == "eligible"
    changed = json.loads(row[1])
    changed["payload"]["voltage_v"] = 9.9
    assert (
        apply(battery, ctx, (row[0], json.dumps(changed), row[2], row[3])) == "conflict"
    )
    advance(battery, ctx, 600122)
    assert apply(battery, ctx, row) == "duplicate"
    # Exact semantic expiry can precede the rounded bucket callback.
    ctx.watermark = 600123
    assert apply(battery, ctx, row) == "late"
    assert state_data(battery)[3] == 0
    advance(battery, ctx, 601000)
    assert state_data(battery)[3] == 0


class Delay(MapFunction):
    def map(self, row: tuple[str, str, int, str]) -> tuple[str, str, int, str]:
        time.sleep(0.12)
        return row


class ObservedBattery(Battery):
    def __init__(self, run: str) -> None:
        super().__init__(run, limit=8)

    def process_element(
        self, row: tuple[str, str, int, str], ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        yield from super().process_element(row, ctx)
        count = state_data(self)[3] or 0
        yield json.dumps({"kind": "state", "count": count, "vehicle": row[0]})

    def on_timer(
        self, stamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        yield from super().on_timer(stamp, ctx)
        key = cast(str, ctx.get_current_key())  # type: ignore[no-untyped-call]
        count = state_data(self)[3] or 0
        yield json.dumps(
            {
                "kind": "state",
                "count": count,
                "vehicle": key,
            }
        )


def native_time_jar(env: StreamExecutionEnvironment, directory: Path) -> None:
    output = directory / "partition-time"
    subprocess.run(
        [
            "bash",
            str(Path(__file__).with_name("build-partition-time.sh")),
            str(Path(sys.prefix).parent),
            str(output),
        ],
        check=True,
    )
    # The real SDK environment owns class loading and ships the artifact.
    env.add_jars((output / "partition-time.jar").resolve().as_uri())


@pytest.mark.parametrize(
    ("merged", "native", "lanes"),
    [
        (True, False, 1),
        (False, False, 1),
        (False, True, 1),
        (False, True, 2),
        (False, True, 4),
    ],
    ids=[
        "old-merged",
        "python-branches",
        "native-branches",
        "native-two-lanes",
        "native-four-lanes",
    ],
)
def test_real_flink_partition_branches_expire_while_other_partition_lags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    merged: bool,
    native: bool,
    lanes: int,
) -> None:
    monkeypatch.setattr(continuous_job, "Battery", ObservedBattery)
    env = execution_environment(tmp_path / "flink", slots=lanes)
    if native:
        native_time_jar(env, tmp_path)
    env.set_max_parallelism(128)
    env.get_config().set_auto_watermark_interval(20)
    for name in ("continuous_job.py", "continuous_operator.py"):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    fast = [value(i, i * 100_000) for i in range(24)]
    fast.insert(2, fast[1])
    changed = fast[1]
    doc = copy.deepcopy(json.loads(changed[1]))
    doc["payload"]["voltage_v"] = 9.9
    fast.insert(3, (changed[0], json.dumps(doc), changed[2], changed[3]))
    fast.append(fast[0])
    slow = [value(100, 0, "vehicle-b") for _ in range(24)]
    branches: list[DataStream] = []
    for partition, rows in enumerate((fast, slow)):
        source = env.from_collection(rows, type_info=TIMED).map(
            Delay(), output_type=TIMED
        )
        if merged:
            timed = source.assign_timestamps_and_watermarks(
                WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(2))
                .with_idleness(Duration.of_seconds(30))
                .with_timestamp_assigner(Timestamp())
            ).set_parallelism(1)
            partition_watermarks(timed)
            branches.append(timed)
        else:
            branches.append(
                partition_battery(source, "small-skew", partition, native, lanes)
            )
    joined = branches[0].union(branches[1])
    if merged:
        old = joined.key_by(lambda row: row[0], key_type=Types.STRING()).process(
            ObservedBattery("old-skew"), output_type=Types.STRING()
        )
        with pytest.raises(Exception, match="continuous_identity_state_limit"):
            collect_output(old, 1000, "old-partition-retention")
        return
    output = cast(list[Fact], collect_output(joined, 1000, "partition-retention"))
    (tmp_path / "trace.json").write_text(json.dumps(output, indent=2))
    facts = [r for r in output if r["kind"] == "event"]
    a = [r for r in facts if r["event"]["vehicle_id"] == "vehicle-a"]
    assert [r["disposition"] for r in a].count("eligible") == 24
    assert [r["disposition"] for r in a].count("duplicate") == 1
    assert [r["disposition"] for r in a].count("conflict") == 1
    assert a[-1]["disposition"] == "late"
    states = [r for r in output if r["kind"] == "state" and r["vehicle"] == "vehicle-a"]
    assert max(r["count"] for r in states) <= 8
    assert states[-1]["count"] == 0
    windows = [
        r for r in output if r["kind"] == "window" and r["vehicle_id"] == "vehicle-a"
    ]
    assert len(windows) == 24
    assert sum(r["unique_events"] for r in windows) == 24


def test_gate_routes_only_fixed_vehicle_partition() -> None:
    vehicle = "stream-vehicle-0000"
    doc = event(0, vehicle=vehicle)
    partition = int(hashlib.sha256(vehicle.encode()).hexdigest(), 16) % 18
    config: dict[str, object] = {
        "input_topic": "input",
        "source": {},
        "run_id": "test-run",
        "source_logs": {vehicle: doc["source_log_id"]},
        "timestamp_min": "1969-12-31T00:00:00.000000Z",
        "timestamp_max": "1970-01-02T00:00:00.000000Z",
    }
    for supplied in (partition, (partition + 1) % 18):
        gate = Gate(config)
        gate.partition = None
        gate.admitted, gate.invalid = cast(Counter, Count()), cast(Counter, Count())
        raw = Row(vehicle.encode(), json.dumps(doc).encode(), "input", supplied, 0)  # type: ignore[no-untyped-call]
        output = list(
            gate.process_element(raw, cast(ProcessFunction.Context, Context()))
        )
        assert len(output) == 1
        assert output[0][0] is (
            PARTITION_OUTPUTS[partition] if supplied == partition else INVALID
        )
        assert cast(Count, gate.admitted).value() == int(supplied == partition)


@pytest.mark.parametrize(
    ("native", "lanes"),
    [(False, 1), (True, 1), (True, 2), (True, 4)],
    ids=["python-plan", "native-plan", "native-two-lane-plan", "native-four-lane-plan"],
)
def test_full_partition_plan_and_guard(
    tmp_path: Path, native: bool, lanes: int
) -> None:
    env = execution_environment(tmp_path / "plan")
    if native:
        native_time_jar(env, tmp_path)
    raw = env.from_collection(
        [(b"key", b"{}", "input", 0, 0)],
        type_info=Types.ROW(
            [
                Types.PRIMITIVE_ARRAY(Types.BYTE()),
                Types.PRIMITIVE_ARRAY(Types.BYTE()),
                Types.STRING(),
                Types.INT(),
                Types.LONG(),
            ]
        ),
    )
    gated = raw.process(Gate({}), output_type=TIMED).set_parallelism(18)
    branches = [
        partition_battery(
            continuous_job.native_side_output(gated, tag)
            if native
            else gated.get_side_output(tag),
            "plan",
            p,
            native,
            lanes,
        )
        for p, tag in enumerate(PARTITION_OUTPUTS)
    ]
    branches[0].union(*branches[1:]).print()
    plan = env.get_execution_plan()
    (tmp_path / "plan.json").write_text(plan)
    check_partition_plan(plan, native, lanes)
    changed = json.loads(plan)
    node = next(
        n
        for n in changed["nodes"]
        if (
            n["type"].startswith("continuous-partition-time-")
            if native
            else n["type"] == "Remove-Timestamp"
        )
    )
    node["parallelism"] = 2
    with pytest.raises(ValueError, match="continuous_partition_plan_parallelism"):
        check_partition_plan(json.dumps(changed), native, lanes)
    changed = json.loads(plan)
    battery = next(
        n
        for n in changed["nodes"]
        if n["type"].startswith("continuous-partition-battery-")
    )
    battery["predecessors"].append(dict(battery["predecessors"][0]))
    with pytest.raises(ValueError, match="continuous_partition_plan_state_merge"):
        check_partition_plan(json.dumps(changed), native, lanes)


class BundledBattery(ObservedBattery):
    def __init__(self, run: str) -> None:
        Battery.__init__(self, run, limit=256)


class ShortDelay(MapFunction):
    def map(self, row: tuple[str, str, int, str]) -> tuple[str, str, int, str]:
        time.sleep(0.002)
        return row


@pytest.mark.parametrize("cache_entries", [1000, 1])
def test_real_bundle_128_drains_expiry_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cache_entries: int
) -> None:
    # Exercise production bundle size and cache eviction between sixteen keys.
    monkeypatch.setattr(continuous_job, "Battery", BundledBattery)
    env = execution_environment(tmp_path / "bundled")
    settings = Configuration()
    settings.set_integer("python.fn-execution.bundle.size", 128)
    settings.set_integer("python.fn-execution.bundle.time", 100)
    settings.set_integer("python.state.cache-size", cache_entries)
    env.configure(settings)
    env.get_config().set_auto_watermark_interval(50)
    for name in ("continuous_job.py", "continuous_operator.py"):
        env.add_python_file(str(Path(__file__).with_name(name).resolve()))
    source = env.from_collection(
        [value(i, (i // 16) * 10000, vehicle=f"vehicle-{i % 16}") for i in range(512)],
        type_info=TIMED,
    )
    source = source.map(ShortDelay(), output_type=TIMED)
    output = cast(
        list[Fact],
        collect_output(
            partition_battery(source, "bundle-128", 0), 4096, "bundle-expiry"
        ),
    )
    (tmp_path / "trace.json").write_text(json.dumps(output, indent=2))
    states = [r for r in output if r["kind"] == "state"]
    assert max(r["count"] for r in states) <= 256
    last = {r["vehicle"]: r["count"] for r in states}
    assert len(last) == 16 and set(last.values()) == {0}
    assert len([r for r in output if r["kind"] == "event"]) == 512
    assert sum(r["unique_events"] for r in output if r["kind"] == "window") == 512
