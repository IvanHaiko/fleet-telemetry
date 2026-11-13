# Bounded canonical battery reader

## Scope — 2026-10-20

[`telemetry_reader.py`](../../telemetry_reader.py) implements
`battery-envelope-reader-v1` under
[ADR-0011](../adr/0011-bounded-canonical-battery-reader.md). It independently reads
schema `1.0.0` battery events for `battery-v1` / `ulog-battery-v1` before a
future transport consumer admits them. No service or dependency is added.

```python
from telemetry_reader import read_battery_event

event = read_battery_event(serialized_utf8_event)
```

The pure API accepts immutable UTF-8 bytes capped at 64 KiB and returns a typed
recognized envelope or raises `EnvelopeError` with safe reason/field codes.
Required fields, supported versions, printable ASCII identifiers and numeric
types are checked. UTC is reproduced independently with integer microseconds
and exact six-digit `Z` timestamps; date overflow fails safely. The positional
event-ID recipe and supported source/privacy/delivery/time-kind relationships
are checked without calling native normalizers.

## Compatibility and limits

Canonical voltage is finite/nonnegative, current finite/signed or null, and
remaining null or in `[0, 1]`. Negative current means charging for both lineages;
native sentinels, native zero-voltage policy and firmware scaling must not be
applied again to canonical values. Producer correctness remains separate.

Unknown optional fields at all object levels are tolerated and omitted from
the recognized projection. Missing optional payload fields become null. No
missing-value or connection flag is invented. Distinct opaque quality flags
are retained in input order; the supported fixed-anchor profiles require
`synthetic_time_anchor`. Ignored extension text/numbers still need valid UTF-8
and finite JSON; duplicate keys fail anywhere. Numeric booleans fail known
integer/measurement fields. Future schema/mapping versions are unsupported;
extra-field tolerance does not establish future-version compatibility.

A matching positional ID does not authenticate payloads, producer attribution,
rights, native sample availability or complete source acquisition. Raw bytes
should be archived separately from this recognized projection. For exact
job/source reconciliation use the [run verifier](run-verification.md).

```powershell
.venv/Scripts/python.exe -S telemetry_reader.py PATH/TO/events.jsonl
```

JSONL inspection is limited to 64 MiB and 100,000 physical records, with the
per-event bound. LF/CRLF delimiters work; blank records fail. Empty files are
valid with zero records, as in an all-rejected conversion. Success exits 0 with
`status: validated` and `records`. Failure exits 2 with a safe stderr diagnostic
and zero-based file record position, without partial success or payload stdout.
Input files are not rewritten. Actual reads are bounded and file-size changes
detected; same-size concurrent rewrites are not. Use stable trusted local files.

This is per-envelope admission, without deduplication, cross-record clock/order
or conflict checks. Two valid different payloads under the same positional ID
can pass individually. `validated` is not a completed canonical run release.
Whole-run reconciliation remains in conversion/exact verification; transport
deduplication remains future work. Actual-source ULog adoption stays proposed.

## Evidence and file inventory

Existing published-vector, two-delivery golden and nine admitted authored ULog
cases now roundtrip through the reader. The existing provenance case checks the
restricted/historical combination and canonical negative current. Existing
standard-library CLI coverage includes conversion, exact verification and
reading. Four focused reader tests address tolerant optional fields, invalid
ID/time/unit/profile relations, malformed ignored JSON values and bounded JSONL
failure. There is no duplicate producer-policy suite or copied flight fixture.

The shared command now includes the reader's `-S` smoke check and its type/lint
scope, also used by the prepared CI:

```powershell
./scripts/check-m1.ps1 -Profile ulog -Offline
```

Exact outcomes and hashes are retained in ignored
`.local-discovery/canonical-reader-verification.json`.

The final shared run passed **335 tests**, lock consistency, Ruff, formatting
(12 files) and strict mypy (12 source files). Conversion, exact verification and
canonical reading all passed with `-S`. Independent focused checks reported
192 passed before the final existing provenance-case extension; review found no
blocker. The sandbox used workspace `TEMP`/`TMP` and `UV_LINK_MODE=copy`, with no
new package. Current evidence does not imply a hosted CI or Linux run.
The retained verifier command is
`.venv/Scripts/python.exe .local-discovery/verify_canonical_reader.py`. It
resolved 345 local links/anchors, confirmed the dependency lock is unchanged,
and matched all three converter artifacts byte-for-byte to the prior v2 run.

| Files | Change |
| --- | --- |
| [telemetry_reader.py](../../telemetry_reader.py), [test_reader.py](../../tests/test_reader.py) | Pure reader, bounded JSONL command and focused boundary cases |
| [test_normalization.py](../../tests/test_normalization.py), [test_ulog_normalization.py](../../tests/test_ulog_normalization.py), [test_conversion.py](../../tests/test_conversion.py) | Existing golden/producer/CLI checks extended |
| [pyproject.toml](../../pyproject.toml), [check-m1.ps1](../../scripts/check-m1.ps1) | Type/lint and standard-library smoke scope; dependencies unchanged |
| [ADR-0011](../adr/0011-bounded-canonical-battery-reader.md) | Supported contract and compatibility decision |
| [README](../../README.md), [contracts](../data-contracts.md), [architecture](../architecture.md), [roadmap](../roadmap.md), [testing strategy](../testing-strategy.md), [setup guide](m1-checks.md), [this guide](canonical-reader.md) | Current capability and admission/evidence limits |

Producer code, fixtures, wire version and converter artifact bytes are unchanged.
Rollback removes the reader and its checks without a measurement/persistent-state
migration. Git metadata is absent; no commit or publication was made. Hosted CI
and actual-source acceptance remain open. The next technical step toward M2 is
a broker/client compatibility decision and bounded synthetic-event ingestion;
infrastructure launch is outside this reader increment.
