"""Probe and recover exactly three verified synthetic events on the local broker."""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

from confluent_kafka import (
    OFFSET_INVALID,
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
    TopicCollection,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient
from confluent_kafka.admin._topic import TopicDescription
from confluent_kafka.cimpl import NewTopic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kafka_probe_contract import (  # noqa: E402
    ENDPOINT,
    MAX_RECEIPT_BYTES,
    RECEIPT_VERSION,
    Fixture,
    ProbeError,
    RetentionGapError,
    acknowledgements,
    check_receipt,
    consumer_config,
    fixture,
    observation,
    receipt,
    report_for,
    serialized,
)
from kafka_topic_policy import (  # noqa: E402
    FixturePolicyError,
    admit_fixture,
    topic_config,
    verify_topic_config,
)

from telemetry.validation import InvalidInput  # noqa: E402
from telemetry_convert import ConversionError  # noqa: E402
from telemetry_metrics import MetricsError, emit_metrics  # noqa: E402
from telemetry_reader import (  # noqa: E402
    EnvelopeError,
)
from ulog_integrity import InputIntegrityError  # noqa: E402


def identity(admin: AdminClient, topic: str) -> tuple[str, str]:
    """Read cluster identity and the topic UUID through typed metadata."""
    metadata = admin.list_topics(timeout=10)
    cluster: object = metadata.cluster_id
    if not isinstance(cluster, str) or not cluster or len(metadata.brokers) != 1:
        raise ProbeError("unexpected_cluster_metadata")
    if any(b.host != "127.0.0.1" or b.port != 19092 for b in metadata.brokers.values()):
        raise ProbeError("unexpected_advertised_listener")
    description: object = admin.describe_topics(
        TopicCollection([topic]), request_timeout=10
    )[topic].result(timeout=12)
    if (
        not isinstance(description, TopicDescription)
        or description.name != topic
        or len(description.partitions) != 1
        or description.partitions[0].id != 0
    ):
        raise ProbeError("unexpected_topic_description")
    return cluster, str(description.topic_id)


def progress(consumer: Consumer, topic: str) -> int:
    """Return only a successful explicit broker commit lookup."""
    committed = consumer.committed([TopicPartition(topic, 0)], timeout=10)
    if (
        len(committed) != 1
        or committed[0].error is not None
        or committed[0].topic != topic
        or committed[0].partition != 0
    ):
        raise ProbeError("offset_lookup_not_confirmed")
    return committed[0].offset


def commit_next(consumer: Consumer, topic: str, offset: int) -> None:
    """Check partition-level acknowledgement and the stored next offset."""
    result = consumer.commit(
        offsets=[TopicPartition(topic, 0, offset)], asynchronous=False
    )
    if (
        result is None
        or len(result) != 1
        or result[0].error is not None
        or result[0].topic != topic
        or result[0].partition != 0
        or result[0].offset != offset
        or progress(consumer, topic) != offset
    ):
        raise ProbeError("offset_commit_not_confirmed")
    emit_metrics(
        "consumer",
        "commit_confirmed",
        committed_next_offset=offset,
        captured_end_offset=3,
        captured_lag_records=3 - offset,
    )


def retained_interval(consumer: Consumer, topic: str) -> None:
    """Refuse missing retained coverage rather than resetting an offset."""
    low, high = consumer.get_watermark_offsets(TopicPartition(topic, 0), timeout=10)
    if low > 0 or high < 3:
        raise RetentionGapError(low, high)
    if (low, high) != (0, 3):
        raise ProbeError("retention_interval_changed")


def observe(
    consumer: Consumer, topic: str, data: Fixture, start: int
) -> list[dict[str, object]]:
    """Read the declared interval with exact source comparisons and a deadline."""
    consumer.assign([TopicPartition(topic, 0, start)])
    rows: list[dict[str, object]] = []
    deadline = time.monotonic() + 15
    while start + len(rows) < 3:
        if time.monotonic() > deadline:
            raise ProbeError("consumer_deadline_exceeded")
        message = consumer.poll(1)
        if message is None:
            continue
        if message.error() is not None:
            raise ProbeError("consumer_record_error")
        index = start + len(rows)
        if (message.topic(), message.partition(), message.offset()) != (
            topic,
            0,
            index,
        ):
            raise ProbeError("unexpected_observation_position")
        if message.value() != data.values[index] or message.key() != data.keys[index]:
            raise ProbeError("observation_bytes_differ")
        rows.append(observation(data, index))
    return rows


def publish(admin: AdminClient, topic: str, data: Fixture) -> None:
    """Create only a fresh topic, and require all three delivery callbacks."""
    if topic in admin.list_topics(timeout=10).topics:
        raise ProbeError("experiment_topic_exists")
    admit_fixture(admin, data.values, data.keys)
    admin.create_topics(
        [
            NewTopic(
                topic,
                num_partitions=1,
                replication_factor=1,
                config=topic_config(),
            )
        ],
        request_timeout=10,
    )[topic].result(timeout=12)
    verify_topic_config(admin, topic)
    delivered: list[dict[str, object]] = []

    def callback(position: int) -> Callable[[KafkaError | None, Message], None]:
        def complete(error: KafkaError | None, message: Message) -> None:
            delivered.append(
                {
                    "input_position": position,
                    "acknowledged": error is None,
                    "error_code": error.code() if error is not None else None,
                    "partition": message.partition(),
                    "offset": message.offset(),
                }
            )

        return complete

    producer = Producer(
        {
            "bootstrap.servers": ENDPOINT,
            "enable.idempotence": True,
            "acks": "all",
            "max.in.flight.requests.per.connection": 5,
            "message.timeout.ms": 5000,
            "queue.buffering.max.messages": 1000,
            "queue.buffering.max.kbytes": 4096,
        }
    )
    for index, value in enumerate(data.values):
        producer.produce(
            topic, key=data.keys[index], value=value, on_delivery=callback(index)
        )
        producer.poll(0)
    pending = producer.flush(10)
    delivered.sort(key=lambda row: int(str(row["input_position"])))
    complete = pending == 0 and delivered == acknowledgements()
    emit_metrics(
        "probe_producer",
        "completed" if complete else "failed",
        attempted_records=len(data.values),
        enqueued_records=len(data.values),
        acknowledged_records=sum(r["acknowledged"] is True for r in delivered),
        callback_errors=sum(r["acknowledged"] is False for r in delivered),
        pending_records=pending,
    )
    if not complete:
        raise ProbeError("publication_incomplete_or_uncertain")


def reopen(config: dict[str, object], topic: str) -> None:
    """Verify clean reopen at the captured end without automatic reset."""
    consumer = Consumer(config)
    try:
        if progress(consumer, topic) != 3:
            raise ProbeError("reopened_progress_differs")
        consumer.assign([TopicPartition(topic, 0, 3)])
        if consumer.poll(1) is not None:
            raise ProbeError("unexpected_record_after_committed_end")
    finally:
        consumer.close()


def probe(
    run: Path,
    job: Path,
    experiment: str,
    output: Path,
    resume: Path | None = None,
    crash_at: str | None = None,
) -> dict[str, object]:
    """Admit or recover this fixed fixture, preserving all prior receipt bytes."""
    started = time.monotonic()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", experiment):
        raise ProbeError("invalid_experiment_id")
    if resume is not None and crash_at is not None:
        raise ProbeError("resume_failpoint_not_supported")
    final = output.with_name(output.name + ".committed.json")
    if output.exists() or final.exists() or not output.parent.is_dir():
        raise ProbeError("receipt_destination_unavailable")
    data = fixture(job, run)
    topic = f"m2.{experiment}.telemetry.canonical.v1"
    admin = AdminClient({"bootstrap.servers": ENDPOINT, "socket.timeout.ms": 10000})
    if resume is None:
        publish(admin, topic, data)
    ids = identity(admin, topic)
    original = report_for(data, experiment, topic, ids)
    prior = check_receipt(resume, original) if resume is not None else None
    config = consumer_config(experiment)
    consumer = Consumer(config)
    try:
        retained_interval(consumer, topic)
        if resume is None:
            if progress(consumer, topic) != OFFSET_INVALID:
                raise ProbeError("experiment_group_progress_exists")
            consumer.assign([TopicPartition(topic, 0, 0)])
            commit_next(consumer, topic, 0)
            start = 0
        else:
            start = progress(consumer, topic)
            if start not in (0, 3):
                raise ProbeError("committed_offset_outside_receipt_boundary")
        rows = observe(consumer, topic, data, start)
        report = dict(original)
        if resume is not None:
            report.update(
                {
                    "status": "recovery_observed_before_commit",
                    "prior_receipt_sha256": hashlib.sha256(prior or b"").hexdigest(),
                    "resume_from_offset": start,
                    "observed_this_attempt": rows,
                    "replayed_observations": len(rows),
                    "unique_events": 3,
                }
            )
        receipt(output, report)
        emit_metrics(
            "consumer",
            "receipt_persisted",
            observed_records=len(rows),
            replayed_observations=len(rows) if resume is not None else 0,
            committed_next_offset=start,
            captured_end_offset=3,
            captured_lag_records=3 - start,
        )
        if crash_at == "before-commit":
            os._exit(86)
        if identity(admin, topic) != ids:
            raise ProbeError("topic_identity_changed")
        retained_interval(consumer, topic)
        if start == 0:
            commit_next(consumer, topic, 3)
        if crash_at == "after-commit":
            os._exit(87)
    finally:
        consumer.close()
    reopen(config, topic)
    report["status"] = (
        "consumer_receipt_recovery_verified"
        if resume is not None
        else "admission_and_clean_consumer_reopen_verified"
    )
    report["committed_next_offset"] = 3
    receipt(final, report)
    emit_metrics(
        "consumer",
        "completed",
        observed_records=len(rows),
        replayed_observations=len(rows) if resume is not None else 0,
        committed_next_offset=3,
        captured_end_offset=3,
        captured_lag_records=0,
        duration_seconds=time.monotonic() - started,
    )
    return {
        "status": report["status"],
        "acknowledged": 3,
        "committed_next_offset": 3,
        "replayed_observations": len(rows) if resume is not None else 0,
        "unique_events": 3,
        "receipt": str(final),
    }


def main() -> int:
    """Run the narrow local command; crash flags deliberately bypass cleanup."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--resume-receipt", type=Path)
    parser.add_argument("--crash-at", choices=("before-commit", "after-commit"))
    args = parser.parse_args()
    try:
        result = probe(
            args.run,
            args.job,
            args.experiment,
            args.receipt,
            args.resume_receipt,
            args.crash_at,
        )
    except RetentionGapError as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason": str(exc),
                    "required_interval": [0, 3],
                    "retained_interval": exc.retained_interval,
                    "missing_intervals": exc.missing_intervals,
                }
            ),
            file=sys.stderr,
        )
        return 2
    except (
        ProbeError,
        FixturePolicyError,
        ConversionError,
        EnvelopeError,
        MetricsError,
        InvalidInput,
        InputIntegrityError,
    ) as exc:
        reason = (
            exc.reason
            if isinstance(
                exc, (ConversionError, EnvelopeError, InvalidInput, InputIntegrityError)
            )
            else str(exc)
        )
        print(json.dumps({"status": "failed", "reason": reason}), file=sys.stderr)
        return 2
    except (KafkaException, OSError, TimeoutError, BufferError):
        print(
            json.dumps({"status": "failed", "reason": "transport_or_receipt_failure"}),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "ENDPOINT",
    "MAX_RECEIPT_BYTES",
    "RECEIPT_VERSION",
    "Fixture",
    "ProbeError",
    "RetentionGapError",
    "acknowledgements",
    "check_receipt",
    "consumer_config",
    "fixture",
    "observation",
    "receipt",
    "report_for",
    "serialized",
    "identity",
    "progress",
    "commit_next",
    "retained_interval",
    "observe",
    "publish",
    "reopen",
    "probe",
    "main",
]
