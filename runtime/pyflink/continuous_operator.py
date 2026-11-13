"""Continuous canonical admission and bounded event-time battery state."""

import hashlib
import json
import logging
from collections.abc import Iterator
from fractions import Fraction
from itertools import islice
from typing import cast

from pyflink.common import Row, Types
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream import OutputTag
from pyflink.datastream.functions import (
    KeyedProcessFunction,
    ProcessFunction,
    RuntimeContext,
)
from pyflink.datastream.state import (
    ValueState,
    ValueStateDescriptor,
)
from telemetry.conversion_contract import SEMANTIC_FIELDS
from telemetry.serving_projection import _semantic_json
from telemetry_reader import EnvelopeError, read_battery_event
from telemetry_reference import epoch_milliseconds

type Document = dict[str, object]
type VehicleState = tuple[dict[str, str], dict[int, str], dict[int, str], int]
VEHICLE_STATE = Types.TUPLE(
    [
        Types.MAP(Types.STRING(), Types.STRING()),
        Types.MAP(Types.LONG(), Types.STRING()),
        Types.MAP(Types.LONG(), Types.STRING()),
        Types.LONG(),
    ]
)
TIMED = Types.TUPLE([Types.STRING(), Types.STRING(), Types.LONG(), Types.STRING()])
INVALID = OutputTag("continuous-invalid-v1", Types.STRING())
PARTITION_OUTPUTS = tuple(
    OutputTag(f"continuous-partition-{partition}-v3", TIMED) for partition in range(18)
)
WINDOW = 10_000
HORIZON = 600_000
METRICS = ("voltage_v", "current_a", "remaining_fraction")


def packet(kind: str, run: str, **values: object) -> str:
    return json.dumps(
        {
            "format_version": "continuous-processing-v1",
            "run_id": run,
            "kind": kind,
            **values,
        },
        sort_keys=True,
        allow_nan=False,
    )


def semantic(event: Document) -> str:
    value = {key: event[key] for key in SEMANTIC_FIELDS}
    value["quality_flags"] = sorted(cast(list[str], event["quality_flags"]))
    return _semantic_json(value)


class Gate(ProcessFunction):
    def __init__(self, config: Document) -> None:
        self.config = config

    def open(self, runtime_context: RuntimeContext) -> None:
        if runtime_context.get_number_of_parallel_subtasks() != 18:
            raise ValueError("continuous_partition_parallelism")
        self.partition: int | None = None
        group = runtime_context.get_metrics_group()
        self.admitted = group.counter("admitted")
        self.invalid = group.counter("invalid")

    def process_element(
        self, value: Row, ctx: ProcessFunction.Context
    ) -> Iterator[tuple[OutputTag, str | tuple[str, str, int, str]]]:
        key, wire, topic, partition, offset = tuple(value)
        if not isinstance(wire, (bytes, bytearray)) or len(wire) > 65536:
            raise ValueError("continuous_transport_bound")
        if topic != self.config["input_topic"] or not 0 <= partition < 18 or offset < 0:
            raise ValueError("continuous_source_coordinate")
        if self.partition is not None and self.partition != partition:
            raise ValueError("continuous_mixed_partition_lane")
        self.partition = partition
        source = {
            **cast(Document, self.config["source"]),
            "partition": partition,
            "offset": offset,
        }
        try:
            event = read_battery_event(bytes(wire))
            vehicles = cast(dict[str, str], self.config["source_logs"])
            if (
                event["delivery"]["dataset_run_id"] != self.config["run_id"]
                or event["vehicle_id"] not in vehicles
                or event["source_log_id"] != vehicles[event["vehicle_id"]]
                or key != event["vehicle_id"].encode()
                or int(hashlib.sha256(event["vehicle_id"].encode()).hexdigest(), 16)
                % 18
                != partition
                or not cast(str, self.config["timestamp_min"])
                <= event["source_timestamp"]
                <= cast(str, self.config["timestamp_max"])
            ):
                raise EnvelopeError("continuous_scope", "event")
        except EnvelopeError:
            self.invalid.inc()
            yield (
                INVALID,
                packet(
                    "invalid",
                    cast(str, self.config["run_id"]),
                    source=source,
                    wire_sha256=hashlib.sha256(wire).hexdigest(),
                    reason="canonical_admission",
                ),
            )
            return
        self.admitted.inc()
        yield (
            PARTITION_OUTPUTS[partition],
            (
                event["vehicle_id"],
                json.dumps(event, sort_keys=True),
                epoch_milliseconds(event["source_timestamp"]),
                json.dumps(source, sort_keys=True),
            ),
        )


class Timestamp(TimestampAssigner):
    def extract_timestamp(
        self, value: tuple[str, str, int, str], record_timestamp: int
    ) -> int:
        return value[2]


class Battery(KeyedProcessFunction):
    def __init__(self, run: str, limit: int = 4096) -> None:
        self.run, self.limit = run, limit

    def open(self, runtime_context: RuntimeContext) -> None:
        # The SDK caches the decoded value and checkpoints its buffered updates.
        # No application cache or state outside Flink is authoritative.
        self.state: ValueState[VehicleState] = runtime_context.get_state(
            ValueStateDescriptor("continuous-vehicle-state-v4", VEHICLE_STATE)
        )
        group = runtime_context.get_metrics_group()
        self.counters = {
            name: group.counter(name)
            for name in (
                "eligible",
                "duplicate",
                "late",
                "conflict",
                "expired",
                "state_limit",
            )
        }

    def process_element(
        self, value: tuple[str, str, int, str], ctx: KeyedProcessFunction.Context
    ) -> Iterator[str]:
        vehicle, wire, stamp, source = value
        identities, expiries, windows, count = self.state.value() or ({}, {}, {}, 0)
        event = cast(Document, json.loads(wire))
        event_id = cast(str, event["event_id"])
        meaning = semantic(event)
        signature = hashlib.sha256(meaning.encode()).hexdigest()
        watermark = cast(int, ctx.timer_service().current_watermark())  # type: ignore[no-untyped-call]
        start = stamp // WINDOW * WINDOW
        prior_wire = identities.get(event_id)
        prior = cast(list[int | str], json.loads(prior_wire)) if prior_wire else None
        if prior and cast(int, prior[1]) <= watermark:
            del identities[event_id]
            count -= 1
            prior = None
        if prior:
            kind = "duplicate" if prior[0] == signature else "conflict"
        else:
            kind = "late" if watermark >= start + WINDOW - 1 else "eligible"
            expiry = stamp + HORIZON
            if expiry > watermark:
                if count >= self.limit:
                    self.counters["state_limit"].inc()
                    retained = [
                        cast(int, json.loads(stored)[1])
                        for stored in islice(identities.values(), self.limit + 1)
                    ]
                    logging.getLogger(__name__).error(
                        "continuous_identity_state_limit run=%s vehicle_id=%s "
                        "watermark_ms=%d measurement_ms=%d retained_ids=%d limit=%d "
                        "observed_ids=%d due_ids=%d earliest_expiry_ms=%s",
                        self.run,
                        vehicle,
                        watermark,
                        stamp,
                        count,
                        self.limit,
                        len(retained),
                        sum(expiry <= watermark for expiry in retained),
                        min(retained, default=None),
                    )
                    raise ValueError("continuous_identity_state_limit")
                identities[event_id] = json.dumps([signature, expiry])
                count += 1
                bucket = (expiry + 999) // 1000 * 1000
                ids = cast(list[str], json.loads(expiries.get(bucket) or "[]"))
                if event_id not in ids:
                    ids.append(event_id)
                expiries[bucket] = json.dumps(ids)
                ctx.timer_service().register_event_time_timer(bucket)
            if kind == "eligible":
                window = cast(Document, json.loads(windows.get(start) or "{}"))
                window.setdefault("unique_events", 0)
                window.setdefault("measures", {name: [0, "0"] for name in METRICS})
                window["unique_events"] = cast(int, window["unique_events"]) + 1
                measures = cast(dict[str, list[int | str]], window["measures"])
                for name in METRICS:
                    number = cast(dict[str, float | None], event["payload"])[name]
                    if number is not None:
                        measures[name] = [
                            cast(int, measures[name][0]) + 1,
                            str(Fraction(measures[name][1]) + Fraction(str(number))),
                        ]
                windows[start] = json.dumps(window)
                ctx.timer_service().register_event_time_timer(start + WINDOW - 1)
        self.state.update((identities, expiries, windows, count))
        self.counters[kind].inc()
        yield packet(
            "event",
            self.run,
            event=event,
            source=json.loads(source),
            disposition=kind,
            semantic_json=meaning,
            semantic_sha256=signature,
            watermark_ms=watermark,
        )

    def on_timer(
        self, timestamp: int, ctx: KeyedProcessFunction.OnTimerContext
    ) -> Iterator[str]:
        identities, expiries, windows, count = self.state.value() or ({}, {}, {}, 0)
        start = timestamp - WINDOW + 1
        stored = windows.pop(start, None)
        bucket = expiries.pop(timestamp, None)
        if stored is None and bucket is None:
            return
        ids = cast(list[str], json.loads(bucket or "[]"))
        for event_id in ids:
            prior = identities.get(event_id)
            if prior and json.loads(prior)[1] <= timestamp:
                del identities[event_id]
                count -= 1
                self.counters["expired"].inc()
        if not identities and not expiries and not windows:
            self.state.clear()
        else:
            self.state.update((identities, expiries, windows, count))
        if stored is not None:
            yield packet(
                "window",
                self.run,
                vehicle_id=ctx.get_current_key(),  # type: ignore[no-untyped-call]
                start_ms=start,
                end_ms=start + WINDOW,
                **json.loads(stored),
            )
