# Testing strategy and evidence

## Single-machine starter checks, 2026-11-11

The [local starter](local-development.md) has its own synthetic source-to-Kafka/
Flink/readback boundary. Its verifier must reconcile the current delivery run's
complete original events, IDs, clocks, nullable values and calculated power.
Repeats may share identity, but old runs, missing measurements, boolean numeric
values, changed clocks/power and invalid source coordinates must refuse.
The two focused tests reuse the existing canonical synthetic fixture; they do
not establish arbitrary-source admission, archive/SQL coverage or recovery.

Actual startup/job/readback and resource observations are recorded in the local
guide. Existing bounded acceptance profiles remain separate historical evidence.

## Publication maintenance checks, 2026-11-11

The publication preparation report owns the actual
maintenance commands and results. The root type-check lane explicitly checks
the library, root APIs and tests; imported runtime modules retain their typed
interfaces but need separate explicit checks in their supported Linux/optional
dependency environments. Markdown prose and checksummed standalone contribution
material are outside the Python formatter's scope.

Existing tests cover the extracted preparation, processing and output contracts.
The source-export regression additionally requires the root license and public
documentation screenshots while excluding a screenshot outside that allowlist.
Kafka coordinator regressions exercise the corrected package-qualified import.
Windows symlink privilege denial skips only the existing symlink-dependent case;
other I/O failures still fail, and Linux exercises the refusal itself.

No source, identity, clock, serialization, retained-data or recovery policy is
changed by this maintenance increment. Component runtime/failure matrices are
not implied by offline tests or source-level equivalence checks.

## Bounded F09 stream reference checks, 2026-11-11

The [offline stream increment](guides/f09-stream-replay.md#verification-and-remaining-integration)
passes 93 selected new/regression cases under pinned Linux Python 3.13.1,
pytest 9.1.1, Ruff 0.16.5 and strict mypy 1.15.0. Checks cover strict identities,
wire/context validation, deterministic preparation, refused tampering/overwrite,
past-only association, distinct gap/age boundaries, duplicate safety and
conflicting/out-of-order refusal. Two added regression cases cover manifest
write/close failure without publishing completion after a review finding.
Another direct processor regression checks shared mask/ordinal consistency:
an internal battery hole requires its mask and accepted points cannot be masked.
Tests were authored with implementation.
Separate native CLI workers have source-only inputs and observed permission
denials; this does not establish blind test independence.

A protected 60-second F09 comparison yields 1,017 selected observations and
538 complete GPS-centred inspections equal to the retained historical result.
Two preparations are byte-identical and reference CLI facts agree with the
processor. This establishes the declared offline interval only. Full-recording
performance, independently authenticated producer/clock admission, Kafka/Flink
delivery/recovery, archive coverage and SQL/Grafana integration are untested here.

## Integrated MVP evidence, 2026-11-10

The [MVP criteria](roadmap.md#integrated-mvp-priority-2026-11-10) under
[ADR-0048](adr/0048-integrated-mvp-and-evidence-preservation.md) require one
source-to-query profile, not the union of unrelated component experiments.
This section specifies required future evidence; no additional runtime check
or milestone acceptance is asserted by the documentation update.

Start with one bounded F09 interval and an expected result based on the reviewed
source streams. Preserve the existing separate identity, timestamp, association
and unknown-value invariants. Verify GPS, battery and recorded-state values
through actual Kafka input, independent archive readback, Flink facts and complete
SQL reader readback. Query the processing-backed datasource and observe an
advancing map/state/history; preloaded research tables are useful reference data
but cannot be the tested output. Compare content and identities as well as totals.

Extend the same path to one complete native-paced recording with declared
selection/quality coverage, then the reviewed SITL profile. Recompute resource
and state bounds for the admitted streams: battery-only rates, deduplication
limits and previous load results do not establish mixed-telemetry capacity.
Keep all existing operating guards until an explicit supported change is tested.

Use existing fixtures and failure mechanisms to establish duplicate-safe serving,
recovery across the SQL-ACK/cursor window, source pause/resume with truthful
availability labels, and isolated reconstruction from verified archive evidence.
State unsupported Flink/broker/host recovery separately. Do not add a separate
formal acceptance pipeline or redundant unit test for each helper or dashboard.

Collect the [run evidence inventory](deployment-and-terraform.md#run-evidence-and-retention-policy-2026-11-10)
before traffic and check it at shutdown: original source/schema lineage,
observation coverage, rejected/late evidence, processing outputs, exact versions,
ACKs/cursors/reconciliation and operational history. Demonstrate recovery/readback
for the declared evidence boundary. Missing metrics, source gaps, unknown clocks
and a deliberately partial recording stay explicit; hashes, healthy containers
or successful checkpoint counts alone cannot certify end-to-end completeness.

Monitoring must expose admission, processing, archive and serving progress/loss
indicators, checkpoint errors, Kafka health and the selected host/resource
budgets. Verify stale/missing collection behavior as well as populated queries.
Keep IDs/coordinates out of metric labels. Record latency denominators, collection
intervals and clock error bounds; do not label historical source age or Grafana
refresh time as pipeline latency.

## Attended F09 Kafka/Flink startup, 2026-11-10

The replay continuation
checks live TLS cluster/endpoint identity, eighteen-partition cross-host ISR=2,
fresh group offsets and all 56 running Flink tasks before native-time publication.
All 11,723 prepared envelopes retain their identities/content under the new
delivery scope. A bounded ongoing observer compares complete committed output
events with prepared input: 477 distinct events match and are eligible, with
nine window facts observed. This non-atomic prefix is not final reconciliation.
The ongoing snapshot has successful checkpoints alongside three earlier failures
whose details are unavailable at inspection. No restore, archive/SQL integration,
GPS replay or terminal-window completeness is demonstrated by these checks.

## Offline coach dashboard preparation, 2026-11-10

After explicit startup authorization, the PC execution
adds complete 21,054-row F09 SQL admission/readback through separate roles,
valid plugin signature and healthy datasource checks. All 23 monitoring queries
execute through Prometheus/Grafana with six UP targets. All 20 analytics targets
execute directly and through Grafana at three native-time cursors (60 checks),
including NULL preservation for the unmatched first battery observation.
Absent processing metrics are reported as absent. These checks do not establish
rendered panels or an integrated progressing F09 GPS/state replay.

The two prepared dashboards pass structural, layout,
datasource-reference, read-only query-budget and offline-map checks. The retained
F09 original checksum and full 21,054-row projection pass, including native span
and preservation of NULL battery values for unmatched observations. Ten existing
recording/association tests pass. Configuration checks do not start services.
SQL/PromQL execution, rendered Grafana panels and an integrated progressing F09
GPS/state replay are deliberately untested while the maintainer's startup gate
remains closed; no previous runtime evidence is extended to these new files.

## Live Grafana position connection, 2026-11-04

The [UI evidence](guides/continuous-position.md#live-grafana-screen) verifies all ten
live datasource queries through Grafana, including numeric native-clock frames
for four rendered XY charts. Browser checks observe LIVE, CONNECTED and current
SQL values. A focused missing-file-after-stat regression covers the reproduced
collector-status replacement race; existing live/identity tests still pass
(17 total). The repaired store resumes its retained cursors and catches up.
Frontend version/reduction settings were corrected after populated backend
frames initially rendered empty charts/unknown string stats. No new universal
source, physical clock or flight-safety evidence follows from this UI result.

## Guarded continuous position, 2026-11-04

The [continuous execution](guides/continuous-position.md#actual-execution-2026-11-04)
checks actual source stop/resume until SQL independently observes heartbeat
loss, NULL current values and a newer measurement on resume. A store SIGKILL
after SQL acknowledgement but before cursor publication reproduces the retry
window; restart revalidates retained archive and preserves logical results.
An independent 78-delivery source/raw/S3/Flink/SQL prefix matches complete
content and source identity while acquisition continues. A reproduced queued
EOF defect now resets assignment only to inspected retained intervals; source
gap checks are unchanged. Existing live/contract regressions pass, including
the original short-profile offset guard. Future records and untested Flink,
broker, host and ambiguous collector-publication recovery remain outside this evidence.

## Bounded live position source to SQL, 2026-11-04

The [execution record](guides/live-position-source-query.md#checks-and-operational-boundaries)
adds two pure contract/conversion/conflict tests, existing live HTTP/freshness
regressions and one actual finite SITL pipeline. The producer retains selected
raw packets before publication. Independent native Kafka reads, original packet
decoding, exact source-offset/fact reconciliation, separate S3 reader and full
typed/raw SQL readback establish 16 measurements across 18 deliveries. Flink
emits during capture; repeated SQL batches preserve logical results. No count-only
or FINISHED-only success, continuous recovery or capacity claim follows.

## Live PX4 MAVLink, 2026-11-04

The [live-source evidence](guides/live-px4-mavlink.md#actual-interruption-and-recovery-evidence)
combines three focused projection tests with existing HTTP/freshness regressions
and one actual isolated PX4 SITL. It checks native units/sentinels, exact raw GPS
time representation, source filtering, position duplicate/clock/conflict refusal,
receiver-epoch-independent identity and separate expiry. A bounded public drill
observes sender silence/resume and gateway restart while the source is silent;
new packets must restore confidence. Browser checks observe loss/reconnection
and cleared values on restart. These are simulator/application checks, not RF,
physical sample timing, broad wire anti-replay or durable recovery evidence.

## Two-recording shared view, 2026-11-04

The [second-source evidence](guides/two-recording-view.md#verification) adds complete
original F01 timestamp/state-field comparison, repeat preparation, source-bound
identity separation and missing/empty-stream NULL projection. Existing binary
service-frame tests cover both registered checksum exceptions without changing
ordinary input budgets. Shared SQL admission checks every row through admin and
SELECT-only reader; actual repeats add no rows, a conflicting registry refuses
and a zero-row reader INSERT is denied. Constant SQL fixtures, actual queries
at native-time bounds and browser source switching establish this bounded
historical view. No live gateway or real-source Kafka/archive/Flink claim follows.

## Supported recording connection, 2026-11-04

The [combined inspection](guides/recording-connection.md#verification-2026-11-04) checks
separate stream unknowns, NULL value preservation, replay stability, duplicate
identity/ordinal refusal and non-destructive output refusal. Two actual original-
file deliveries and sampled combined SQL/Grafana checks complement these tests.
They do not admit a second source, validate physical clocks or establish real-
source Kafka/archive/Flink integration. Existing full-table evidence is retained.

## Live interface follow-up, 2026-10-27

The live UI record checks startup-frontier classification,
duplicate non-renewal, monotonic age, clock skew refusal, additive HTTP fields,
collector outage and heartbeat loss/recovery on small authored inputs. Actual
browser scripts are exercised with deterministic Node DOM/clock tests, plus a
headless Chrome fixture with fully intercepted HTTP and a narrow viewport.
No real gateway, full Kafka/Flink graph or sustained browser latency is claimed.

## Flink scrape-budget regression, 2026-10-27

The short scrape replay uses the pinned Prometheus
binary, historical label shapes with synthetic values and one loopback-only
fixture. It verifies old-limit rejection, exact 10,638-sample admission,
preservation of thirteen dashboard metric names, split-family removal,
20,001-sample failure, unavailable alert and subsequent resolution/recovery.
Pinned `promtool test rules runtime/observability/alerts-test.yml` checks the
16,000 boundary, thirty-second warning, resolution and unavailable/missing data.
Both complete scrape configurations pass promtool syntax/rule checks. No full
Flink/Kafka/Grafana runtime or workload capacity claim follows from this probe.

## Offline two-host preparation, 2026-10-27

`tests/test_split_preparation.py` checks the new portable Kafka renderer without
Docker, Kafka, networking or installed client SDKs. It establishes one shared
cluster/controller bootstrap across both recipes, exact node ownership and host
racks, non-loopback advertised endpoints, mandatory mutual TLS/hostname checking,
missing-bind refusal, file hashes and refusal to overwrite an existing candidate.
Invalid or identical host addresses and unrelated project names refuse before
creating files. These checks do not establish certificate validity, live rack
placement, target runtime support, replication, recovery or throughput.
The transfer runbook defines the deferred two-host tiny-fixture,
TLS-denial, broker-return and Wi-Fi interruption checks under proposed ADR-0039.

The client configuration follow-up checks
native/JVM TLS separation, unchanged local defaults, incomplete/downgraded
settings, unsafe endpoints/paths and metadata identity refusal. Mocked SDK
responses establish option propagation across native admin/consumer/producer;
they do not establish a TLS handshake. The five selected configuration/archive/
serving/latest-state modules pass 22 checks on Linux without JVM/services.
Actual mounted-certificate Flink source and both sink checks remain deferred.

The [complete two-host setup](guides/two-host-setup.md) adds focused checks for service
placement, explicit submission, local checkpoint/storage mounts, image inventory,
cross-host credential isolation, mismatched cluster refusal, source ZIP inclusion
of untracked code, exclusion of retained/private material and corruption refusal.
A 64-record/64-vehicle authored fixture yields 128 measurements across eighteen
lanes. Generated host overlays pass Compose syntax validation without an engine
startup; a fresh native-Linux PKI probe issues and verifies all thirteen leaf
certificates using installed OpenSSL/keytool. These are configuration/crypto-file
checks, not live Kafka TLS, WSL routing or target recovery evidence.

## Integrated slice evidence, 2026-10-26

The finite source-to-query run uses one session,
the existing authored fixture and independent window reference. Real Kafka/S3,
per-offset Flink byte receipts, successful job completion and complete canonical
sink readback establish the path. Three exact SQL reports survive changed-batch
retries after an acknowledged upstream write with injected caller connection
loss. Merges are stopped; exact sums/means and valid/missing counts are checked.
One focused regression refuses missing/competing processing facts. Existing
component/failure suites remain historical evidence; none is claimed rerun or
blind here. The linked ledger keeps archive-only replay into serving, positive
online-late integration and production recovery gates open.

## Bounded M4 acceptance, 2026-10-26

The completed M4 ledger reuses accepted component failure
proofs and adds actual Kafka-inaccessible archive-only serving replay, unchanged
original target, strict immutable run receipts, full canonical/processing report
admission and storage/serving replacement. Deliberate missing/conflicting facts,
wrong/incomplete receipts, receipt overwrite and unsealed reports refuse; no
success file or missing-fact seal is produced. Four new methods reuse the Graph
fixture and cover source/target separation, exact reference facts, typed receipt
integrity and canonical omission. The cumulative final M4 suite has 107 methods:
Linux has no skips, Windows retains seven explicit existing skips; Ruff and strict
typing pass. This is single-session coherent-increment verification, with no
new independent/blind claim. Online-late M5 and production gates remain explicit.

## M5 targeted reliability evidence, 2026-10-26

The [M5 ledger](case-studies/m5-reliability.md) reuses accepted producer/sink/rebuild/conflict
proofs and adds actual missing cases: online idle/late/horizon SQL, two-member
rebalance, failed/repaired checkpoint, TaskManager state versus backlog, archive
outage, missing restore state and Flink source retention loss. A new source
expiry probe returns false success, justifying focused regression escalation.
Two small tests cover retained bounds and exact source receipt reconciliation;
actual preflight/post-admission refusals, a retained pre-repair checkpoint cold
restore and the normal two-partition SQL scenario verify the narrow repair.
No new generic runners, dependency resolution or routine blind-role cycle is
added. Existing M4 suites are not claimed freshly rerun. Production durability,
full disk erasure and a continuous checkpoint-to-SQL transaction remain untested.

## Continuous preparation, 2026-10-27

The continuous calibration checks more than 32 unique
events through eighteen partitions, immutable segmented archival, long-lived
checkpointed Flink and paged ClickHouse reconciliation. It records real failed
startup attempts, checkpoint-12 restoration, protected worker cursor reuse and
explicit identity replay. Exact emitted window sums pass, but the high observed
late rate exposed post-source watermark placement under backlog. The subsequent
partition regression passes zero late events and exact
window sums. Its separate 2.084 GB load failed at the identity-state cap;
full-path reconciliation did not execute.
No throughput capacity, large-load latency distribution, complete new-runtime
failure matrix or M6 acceptance follows from this calibration.

## Verification effort proportional to risk

Current delivery policy, 2026-10-26: prioritize a working source-to-query
scenario, three useful queries and meaningful failure evidence. Verification
should protect that result without becoming a separate platform project.
See [the contributor guide](../CONTRIBUTING.md) and
[the active plan](roadmap.md#active-continuation-and-proportional-delivery-2026-10-26).

Small reversible changes normally use one session and relevant existing checks.
Medium changes use a stated scope, implementation and focused validation.
Review a completed meaningful increment at the level justified by its concrete
risk; do not impose a separate formal acceptance cycle on every helper or module.
Strict independent frozen tests and isolated roles are reserved for cases where
blindness or enforced read-only review is necessary to establish an identified
property. Name that property and consequence before using the strict workflow.
The component's name or the mere possibility of an error is not enough.

Reuse existing fixtures and successful evidence. Add tests for uncovered
invariants, credible failure risks or reproduced regressions, not test counts.
Do not rerun unrelated successful suites or live failure matrices after an
unrelated edit. Run relevant checks again when code changes, failures or an
unresolved concern justify them. Keep exact identity/content comparisons,
duplicate safety, physical time/units, provenance and detectable loss; reducing
ceremony does not justify weaker assertions or bypassing operational safeguards.

This dated policy governs process selection for new work. Earlier per-increment
frozen-test and restricted-review procedures below describe their original
admission scopes; they do not automatically apply to every subsequent change.
Their results and failures remain intact. Milestone behavior/evidence criteria,
security boundaries, retained data and publication restrictions remain unchanged.

## What tests must establish

The bounded persistent M3 acceptance now combines
real two-partition Kafka watermark observations, exact independent-reference
comparison, TaskManager/cold checkpoint-state restore and actual state refusal
with measured cgroup/process evidence. A separate restricted Tester froze nine
report consistency tests before implementation; those alone prove no runtime
behavior. Read-only project checks and a separate restricted final review
inspect actual raw observations and retained failures. The stock connector
cold-completion failure and independently reproduced narrow backport are
recorded in [ADR-0023](adr/0023-bounded-kafka-enumerator-backport.md).
These local proofs do not establish hosted CI, production capacity or sink
exactly-once behavior. Earlier experiment claims below remain scoped to their
own inputs, runtime and failure boundary.

The proposed [archive v1 design](reference/archive-format-v1.md) supplies public byte
vectors, schemas, limits and failure outcomes for the next archive boundary.
It does not add executable tests or claim independent verification. Before an
archive implementation, a restricted independent Tester must derive and freeze
the focused suite from the public contract/interfaces and selected existing
synthetic fixtures using the current external workflow. Preserve null/empty
values and ordered repeated headers; compare exact observation keys/content,
not counts or event IDs alone. Exercise conditional-create races, orphan/seal/
commit crash windows, backend restart, trusted-root corruption, coverage holes
and source-inaccessible rebuild. Verify real permission denials and retain a
separate read-only review; shared-access sessions do not establish isolation.
The complete finite catalog and trusted recovery descriptor precede the first
offset commit. Live storage/SDK adoption and archive acceptance remain open.

Every test states an invariant, the boundary it exercises and the evidence needed to detect a violation. A successful process exit, equal row counts or a healthy dashboard alone does not establish correctness.

Keep the suite purposeful: reuse existing cases and add a test only when a
meaningful invariant, credible failure risk or regression is otherwise
uncovered. Test counts and coverage percentages are not reasons to duplicate
checks or mirror implementation details. This maintainer preference is also
recorded in [the contributor guide](../CONTRIBUTING.md).

Most of this strategy is planned. The first M1 slice now has local unit and
contract tests for pure synthetic battery normalization and the bounded ULog
value policy on authored synthetic cases; see the
synthetic evidence and ULog slice evidence.
The [bounded conversion slice](guides/bounded-conversion.md) adds local framing,
pinned-reader integration and file/run tests with independent authored binaries.
The manual Kafka compatibility probe now checks
three-event admission/clean-consumer-reopen against a real local broker, plus
an unavailable endpoint. The consumer recovery check
adds actual process exits before/after commit and corrupt checkpoint refusals.
A graceful broker restart check compares the captured
records, topic UUID and stored next offset before/after restart on the same volume.
The retention-gap check lets required records expire in
a fresh topic and verifies explicit missing-interval failure without offset reset.
The [SIGKILL follow-up](case-studies/kafka-broker-sigkill.md) confirms an abrupt JVM exit and
compares captured records, identities and stored next offset after startup on the
same volume. It does not simulate power or disk loss.
The consolidated local matrix adds producer exit after
ACK before durable receipt, exact-byte retry across new producer sessions,
missing/extra/semantic-conflict reconciliation and finite unavailable/queue-full
failure. It reruns the earlier transport cases and both M1 profiles together,
including consumer acceptance checks under Python optimization.
The later isolated acceptance cycle freezes tests
before candidate exposure, records real permission denials and uses a separate
read-only oracle/final review. Failed oracles and superseding versions are kept
distinct. It adds coverage for conflicts among repeated extra identities without
equating successful Linux interface tests with Windows publication support.
The offline consumer audit adds focused exact-byte/context
checks, prior-receipt/replay accounting and safe CLI refusal under `-S -O`. Its
new fixture is derived from the existing authored synthetic receipt with explicit
synthetic experiment identities; its exact LF bytes are protected from Git newline
conversion. It reuses the M1 reference job and does not duplicate normalization
assertions. Old real-boundary receipts are inspected without a new broker run.
The producer audit reuses that reference source
and adds coverage for the two recorded attempts, offset/hash coverage, safe JSON
parsing and coordinated manifest/evidence changes. Its bundle derives from the
existing authored synthetic experiment with explicit synthetic context and
sanitary relative command paths; it is materialized into protocol artifacts in
test scratch. No producer networking or consumer tests are duplicated.
The acceptance cycle adds seven metric-schema/cardinality
cases and checks actual cumulative snapshots against native callbacks, timed-out
queues, process exits and verified broker commits. A fresh full broker matrix
includes publication-manifest regeneration; CI configuration is still distinct
from hosted execution. Original event/receipt formats remain regression inputs.
A service CI lane, general crash recovery, benchmark results
and pipeline recovery guarantees remain absent. Performance
numbers in future reports must come from declared experiments.

## Reference scenario and accounting

The [canonical reader](guides/canonical-reader.md) reuses published-vector and current
producer roundtrips, then checks optional-field compatibility and independent
identity/time relations. New focused cases cover malformed ignored extensions
and bounded JSONL failure without partial success; native producer-policy tests
are not duplicated. This validates envelopes individually, not entire datasets
or cross-record conflicts.

[Read-only run verification](guides/run-verification.md) regenerates expected files
from the external job/source rather than trusting stored hashes. Its focused
tampering/incomplete-output check asserts failures preserve supplied artifacts;
existing replay and CLI checks establish successful verification.

Build a small synthetic reference dataset first: two pseudonymous vehicles, known battery values and timestamps spanning several ten-second windows. Add labeled duplicate, conflict, null, malformed, missing, delayed and out-of-order cases one at a time. Keep source bytes / specification, ordinals, fixed anchors, seed, expected identities and expected calculations under version control where rights permit.

The reference calculator must be independent of production aggregation logic. Pin input order and explicit watermark advances for deterministic operator tests. For actual Kafka runs, capture enough arrival and watermark context to explain online late decisions; an offline full-history calculation is not automatically the online oracle.

The first [M3 reference slice](reference/m3-window-reference.md) accepts at most 1024
explicit trace steps and 1 MiB of observation bytes. Independently authored
tests precede its implementation and retain literal window/time expectations.
It calculates exact sums and non-null counts, separates full-trace conflict
reconciliation from expiring dedup state, and requires finite EOF. A reference
pass is no evidence of watermark generation, partition idleness or checkpoint
restore. Those checks must exercise the selected Flink runtime separately.

The PyFlink compatibility profile now exercises
real Python SDK worker execution, literal integer timestamp boundaries, pre-watermark
invalid side output, and a finite Kafka Table/DataStream metadata bridge.
It compares each source position/key/value hash with the verified synthetic
run and independently checks unchanged consumer progress. Dedicated setup tests
cover corrupt cached archives, path-scope refusal and stale-lock refusal before
installation. The Python 3.12 dependency
graph and SDK-aware type checks remain separate from M1's Python 3.13 checks;
the module-size guard includes both. Compatibility success does not establish
window/deduplication correctness, idleness or checkpoint/source recovery.

The finite battery operator checks now compare real
managed-state output with the existing independent reference. Clean, conflicting
and empty collections cover pre-epoch/exact-boundary time, multiple measurements
per window, null/zero values, delivery-only and numeric-spelling duplicates,
invalid source/run bounds, whole-run conflict invalidation and actual terminal
expiry callbacks. Three focused refusal tests cover pre-submission input/scope
limits and incomplete disposition evidence. Periodic watermarks are disabled
and observed downstream values are checked; late arrivals, intermediate expiry,
idleness and checkpoint/source recovery are explicitly outside this run.
These checks reuse the existing runtime and fixtures in one session; they do
not constitute independent blind tests or enforced read-only review.

The intermediate-watermark checks now pace finite
input against actual downstream progress and compare its captured trace with
the unchanged reference. Authored assertions distinguish 9998/9999 window
closure and 599999/600000 identity expiry, duplicate-before-late routing, late
first observations beyond expiry and conflicts after cleanup. A small stalled
watermark fixture must fail at its fourth identity under a three-entry state
limit, with the actual failing process retained. A source-startup cancellation
case checks thread/listener cleanup. These operator checks do not demonstrate
partition idleness, checkpointability of the test source or state/source restore.

The checkpoint recovery checks use a separate
restricted blind Tester before candidate exposure and freeze 75 public-contract
cases. A normal project copy preserves the full frozen test AST. Pure validator
success proves evidence consistency only; actual Kafka/REST/process/state
observations and unchanged-reference comparison establish the runtime result.
Parent live checks enforce read-only source/frozen inputs and retain raw failed
attempts. A separate restricted read-only Reviewer inspects the final candidate,
baseline, diff, frozen suite and all failures. Two behavior repairs were used.

The isolated final run checkpoints at next 3, kills an independent Python worker,
restores source and managed identities/aggregates together at 3, and completes
with nine observations, eight unique identities and two exact windows. Physical
uncheckpointed suffix diagnostics remain distinct from selected successful output;
they are not a transactional sink. The initial shared-broker preservation failure
must be included in original-scope acceptance even when final technical checks
pass. Historical successful receipts cannot prove current Kafka retention.

The [retention incident follow-up](case-studies/kafka-retention-incident.md) adds five offline
quarantine cases: a process-launch tripwire and absent source files prove early
refusal, output stays absent, optimized Python retains the matrix gate, both
restart modes refuse and the CLI reports a fixed reason. The existing optional
Kafka client needs no broker. This does not prove Docker-level enforcement,
production retention sizing or archive durability. Long downtime, size/archival
pressure and an exercised response remain production gates.

The proposed [archive recovery scenario](reference/archive-recovery-contract.md#required-expiry-and-restore-scenario)
adds a distinct future acceptance boundary: independent readback, observed
source-offset expiry, normal recovery refusal, then an archive-only rebuild into
a new run with source Kafka inaccessible. Freeze contract/oracle inputs before
candidate exposure through the external restricted workflow; documentation
examples are not frozen tests or independent verification. Reuse one tiny
observation/identity oracle across writer crash windows and changed batching.
Require exact bytes and observation keys, source hashes and stable measurement
content, not equal counts alone. Missing/corrupt objects, conflicting overlaps
and loss after preflight must visibly fail without successful final output.

The [production gate](guides/production-recovery-gate.md) separately requires measured
outage/repair/catch-up and storage bounds, archive failure-domain evidence,
remaining-time freshness and response under time/byte/disk pressure. Unknown
inputs must block a healthy/admitted result. A timed drill must prove endangered
bytes survived, and a connector test must exercise real out-of-range handling;
neither a mocked offset guard nor delivered alert proves those properties.
No such runtime checks ran for this documentation increment. Link, arithmetic
and scope checks validate only document consistency, not production behavior.

Under [ADR-0020](adr/0020-bounded-tests-and-s3-archive.md), tiny fixtures remain
the default; the larger local planning envelope is about 10-50 GB, with a
conservative 50 GiB ceiling for retained Kafka test data. Check all copies and
actual free space before a larger run; do not create a 50 GiB fixture just to
exercise the bound. Before ordinary non-expiring fixture topics are adopted,
verify effective settings and refusal on insufficient retained-data/disk budget.
Use separate disposable topics for intentional retention expiry. Final S3
acceptance adds actual upload/readback and archive-only replay; local compatible
storage alone does not establish those results. A Docker authorization system
or multi-broker capacity benchmark is not a prerequisite for this local scope.

The [implemented fixture profile](guides/local-kafka-fixture-profile.md) adds 19 policy
cases and a real three-record broker matrix: effective settings, consumer
interruption, producer retry, intentional expiry/refusal and old Kafka transport
timestamps surviving cleanup/restart. All 443 root cases pass. Storage refusal
is checked before creation/publication; it is not a quota or proof of 50 GiB
workstation capacity.

For each bounded run define:

- `S`: expected native source record positions from the manifest.
- `A`: distinct canonical event identities acknowledged by Kafka, with expected semantic content.
- `O`: observed Kafka records identified by topic, partition and offset; this includes repeated event identities.
- `V`: valid unique measurements, `Q`: rejected/conflicting evidence, and `L`: valid late measurements. Within this document `V` includes `L`.
- `E`: valid unique measurements eligible for online windows under the declared policy; thus `E = V - L`.
- `D`: logically unique event facts visible through the approved analytical query. Event facts preserve valid late measurements with a disposition, so the proposed event-level target is `D = V`.

If M4 chooses a different physical disposition table layout, the reconciliation query must still reconstruct `V` and `L`. Quarantine records are not event facts. A conflict invalidates the run even if one of its variants was already written.

Reconcile native parse outcomes against `S`, publication identities against `A`, archive offsets against `O`, and unique event facts against `V`. Compare window facts with a reference aggregate over `E`. Use both count and content checks: equal counts can conceal one missing identity and one unexpected identity. Report missing, extra, conflicting, pending and intentionally excluded records separately.

The acknowledged set `A` is a lower bound during an ambiguous producer failure: Kafka may have stored a record whose acknowledgement was lost. Resolve uncertain publication attempts by inspecting observed records and comparing their identities with the source manifest's expected canonical output. Only after retries and drain may the run assert full admission; absence from the local acknowledgement ledger alone is not proof of broker loss.

Retried attempts, committed archive records and unique measurements have different denominators. Duplicate classification precedes window eligibility: copies still in dedup state are duplicate observations; an expired-state copy may reach late handling. Reconciliation collapses all copies by identity and checks that none changes the approved result.

## Test layers

| Layer | Boundary | Observable invariant | First milestone |
| --- | --- | --- | --- |
| Unit | Pure normalization, clock mapping, identity, calculations | Pinned inputs produce the independently specified output or rejection | M1 |
| Contract | Serialization and old/new readers | Types, UTC precision, units, nulls and compatible optional fields retain meaning | M1 |
| Deterministic replay | Source bytes through bounded converter | Ordered identities and normalized stable content match across fresh runs | M1 |
| Kafka integration | Producer, broker, consumer offsets | Acknowledged identities are consumable within retention; progress resumes at the declared boundary | M2 |
| Flink integration | Timestamp assignment, keyed state and windows | Dispositions and aggregates match controlled event-time expectations | M3 |
| Archive integration | Object bytes, receipts and offsets | Unique offset coverage is complete and object checksums agree after retries | M4 |
| Sink integration | Acknowledgement, persisted rows and approved queries | Retries never change unique-read results; conflicts remain detectable | M4 |
| End-to-end | One bounded source-to-query run | Identity sets, stable content and aggregates reconcile after drain | M4 |
| Reliability | Restart and failure boundaries | Recovery meets the same invariant or reports an explicit unrecoverable gap | M5 |
| Load | Declared workload and resource budget | Results remain correct and latency / pressure are measured without hidden drops | M6 |

Mocks support pure error-handling tests but cannot prove broker persistence, checkpoint restore, object durability or ClickHouse query behavior. Use real pinned services for those integration boundaries.

## Required cases

The 2026-10-27 real ULog acquisition adds restricted
research evidence, not another passing runtime fixture. Exact member size/hash,
ZIP CRC32, complete frame boundaries, 39 declared battery fields and selected
GPS/battery summaries were checked with the existing pinned reader. The original
canonical gate refused `input_size_limit`; the file also exceeds its frame bounds,
contains Q messages and declares a different firmware. No canonical replay or
source-to-query result ran. Before adopting it, establish the bounded format and
firmware/time profile, then reconcile two conversions and the independent reader.
GPS offset variation is not a measured UTC accuracy bound. Keep the original
and research outputs ignored and retain the existing synthetic acceptance scope.
The later F09 research profile
reconciles two local conversions and independent-reader admission under a
separate lineage; the source producer and actual UTC remain unverified.

Before accepting the proposed `ulog-battery-v1` mapping, add independent
firmware-specific fixtures proving sample-time precedence and publication-time
fallback only without sample time, required UTC source timestamps with explicit
anchors, each supported native current sign, invalid/sentinel negative values,
native scaling/sentinels, and
the proposed admission of structurally valid `connected=false` records with
`source_battery_disconnected`. Invalid required values must still be rejected.
Tie these expectations to reviewed firmware/message definitions and a local
discovery result. Add old/new producer-reader compatibility fixtures for the
selected schema and semantic projection. Documentation patch `1.0.1` alone is
no compatibility evidence; synthetic output remains `1.0.0`. Binary parsing,
source attribution and general reader-compatibility checks remain future
acceptance work. The pure value tests below do not satisfy those boundaries.

[ADR-0007](adr/0007-ulog-battery-value-policy.md) and the
[primary firmware policy](data-contracts.md#primary-firmware-value-policy-proposed)
now have [22 literal review cases](../tests/fixtures/ulog-battery-policy-v1.json)
and [independently authored expected partial results](../tests/fixtures/expected-ulog-battery-policy-v1.json).
They specify nine admissions and thirteen rejections, including exact `-1`
versus other negative current, zero/negative zero, valid disconnected values,
unknown required voltage, missing native fields and invalid connection types.
All values are project-authored synthetic examples, not log derivatives.
The [pure ULog unit/contract tests](../tests/test_ulog_normalization.py) now assert
all 22 outcomes and [independent golden IDs](../tests/fixtures/expected-ulog-battery-identities-v1.json).
They also check nonfinite/coerced values, manifest/delivery scope, anchors,
timestamp boundaries, sample-time guards, stream/ordinal identity and two delivery
runs. These are plain Python native-shaped records, not binary parser tests.
The isolated parser probe now exercises embedded
types, explicit boolean conversion, malformed/truncated input and parser recovery
in a separate Python 3.13 environment. Its twelve authored binary experiments
show silent tail omission and ordinal shifts after a skipped middle record;
the probe itself does not execute canonical mapping or validate a runtime bridge.
The subsequent [ADR-0008](adr/0008-ulog-input-integrity-gate.md) boundary now has
separate executable framing/reader tests, and
[ADR-0009](adr/0009-bounded-local-conversion.md) adds bounded conversion tests.
General reader compatibility remains untested. No charging case is claimed for the
reviewed native path; the accepted synthetic mapping retains both canonical
current signs.

## Implemented bounded local boundary

The gate checks registered source hash/size, complete headers/payloads, supported
flags and bounded nested definitions, subscriptions and data lengths. Its subset
is `B`, `F`, `I`, `M`, `P`, `A`, `D`, `L`, `S`, `O`, bounded to 16 MiB and
100,000 total frames. [ADR-0010](adr/0010-ulog-nested-and-service-frames.md) adds
explicit depth, expanded-field and qualified-name limits, retaining embedded
padding and rejecting undefined/cyclic definitions even when unsubscribed.
Focused service-frame checks cover continuation, metadata ambiguity, UTF-8,
severity and sync magic; a sync marker never permits corruption recovery.
Independent authored binaries exercise truncation, corrupt lengths, unsupported
messages/flags and clean-boundary cuts against external expectations. A receipt
registered after device acquisition cannot establish loss-free acquisition.

Reader tests run against the optional pyulog `1.2.2` / NumPy `2.3.5` combination.
They check exact complete-definition digests, required embedded types, explicit
NumPy scalar conversion and native boolean `0`/`1`, original selected ordinals
including invalid voltage rows, decreasing/equal selected timestamps, and count
reconciliation for all framed streams. Parser exceptions, reported corruption
and mismatched counts fail the whole source; tests verify raw diagnostics do
not escape. Firmware metadata checks and nonempty producer attestations do not
independently prove producer identity or permission to use a real log.

Converter tests exercise strict versioned jobs, duplicate JSON keys, nonfinite
values, external source expectations, outcome counts, artifact hashes and stable
semantic content across distinct delivery runs. Whole-source failures must leave
no final output directory; value rejections retain their original source index.
The writer stages completed artifacts beside the destination and refuses existing
targets. Windows directory rename and Linux atomic no-replace publication must
preserve even a late-created empty destination. The Linux follow-up
adds independent process competition and focused unsupported-operation checks;
both dependency profiles and Windows regressions remain required. The destination
name matches `dataset_run_id`; the serialized-output budget is 64 MiB. This is a
bounded local file result, not a tested crash-recovery or service-concurrency guarantee.

The [conversion guide](guides/bounded-conversion.md) owns exact commands, final check
results and environment limitations. Do not infer final suite counts from the
earlier pure-slice or isolated research reports. The [shared M1 command and CI
guide](guides/m1-checks.md) records two successful fresh local environment runs and the
prepared workflow. A shared Python runner now configures four Windows/Linux
dependency lanes, reusing the existing behavioral suite and checking the runner
with Ruff and strict mypy. Hosted CI execution and service tests remain pending.

| Scenario | Injection | Expected invariant and evidence |
| --- | --- | --- |
| Replay determinism | Two runs with different ingestion clocks and replay speed | Stable identities/content match; delivery fields differ intentionally; no measurement timestamp rewrite |
| Duplicate within horizon | Same identity/content before state expiry | Duplicate counter rises, unique measurement and window counts do not |
| Duplicate outside horizon | Replay after event-time state cleanup | Online disposition follows late policy; unique serving result and full-run reconciliation remain correct |
| Identity conflict | Same identity with a changed voltage | Conflict evidence is preserved, release of the run fails, no last-write-wins success |
| Out-of-order but eligible | Permute arrival within the configured watermark bound | Window membership and aggregate match the controlled reference |
| Late after close | Deliver a valid event after its window closes | Late evidence contains watermark/window context; closed online output is unchanged |
| Window boundaries | Values just before, at and just after the interval edge | Membership follows start-inclusive/end-exclusive rule after declared millisecond conversion |
| Idle and resumed partition | Pause one input, then resume old events | Watermark can progress after idleness; resumed older events receive visible late dispositions |
| Bad clock | Missing anchor, boot reset, far-future native time | Rejection before watermark assignment; other vehicles' windows are not prematurely closed |
| Missing / null values | Remove a known record, then separately null a measurement | Known source loss appears as a missing identity; null counts are not zero-value samples |
| Malformed input | Invalid JSON, binary parse failure, unsupported event type | Safe source/offset evidence and reason are preserved; no recursive quarantine loop |
| Schema evolution | Old/new reader and writer fixture matrix | Optional additions remain readable; breaking change is rejected or isolated in a new major topic |
| Producer failure | Stop between acknowledgement and durable local publication progress | Retry may add observations, but bounded identity reconciliation detects neither hidden loss nor inflated unique results |
| Kafka consumer failure | Stop before / after processing and offset commit; trigger rebalance | Resume behavior matches the declared commit boundary; replay is visible and does not lose acknowledged work |
| Kafka retention gap | Request an offset deliberately removed by retention | Explicit failure with missing interval, never silent jump to latest |
| Flink process failure | Terminate after a completed checkpoint with work in flight | State and offsets restore consistently; drained normalized outputs match reference |
| Failed checkpoint | Block state storage or interrupt snapshot persistence | No incomplete checkpoint is treated as recoverable; age/failure metrics rise |
| Archive writer crash | Interrupt object write, receipt write and offset commit independently | Restart verifies / repairs receipts and offset coverage, tolerates overlapping batches, rejects checksum conflict |
| Sink outage | Reject connections and then recover | Backpressure / retry metrics rise; recovery drains pending writes without hidden loss |
| Ambiguous sink commit | Persist a batch but drop its acknowledgement | Retry does not inflate approved query results, even with changed batching and before background merges |
| Window write retry | Repeat a complete aggregate replacement | One logical window result; no double-counted incremental sum |
| Long replay | Rebuild beyond Kafka and sink retry-dedup windows into a new run | Archived source/events remain sufficient; no mixture with original run; stable-content comparison passes |
| Disk or resource pressure | Bounded storage/memory limit or controlled slowdown | Errors/backpressure are visible; run stops before uncontrolled disk exhaustion; no success claim with pending data |

Use targeted failure points or test proxies only when simple process control cannot exercise the boundary. Do not build a general chaos platform. Repeat timing-sensitive cases enough to establish the observed failure window and disclose the number of repetitions.

## What can be claimed after testing

The two-input idle/resume experiment compares actual
global-watermark observations and exact window-close values with literal
expectations and the unchanged reference. It exercises active minima, idle
exclusion, resumed late/duplicate precedence and final-window retention during
all-input silence. Two loopback sources isolate this SDK/operator boundary;
they do not establish Kafka split assignment/idleness, rebalances or persistent
recovery. The timing-sensitive scenario is repeated on a fresh scratch path.
This author experiment does not claim blind testing or restricted independent
review. Keep those limitations alongside successful reference comparisons.

| Evidence | Permitted claim | Limitation |
| --- | --- | --- |
| Identity vector and replay tests | Deterministic identity and semantic content for pinned fixtures / versions | Does not prove all public logs map correctly |
| Flink reference and restore tests | Consistent managed-state recovery in the tested configuration | Does not establish exactly-once external writes |
| Sink retry and unique-query tests | Duplicate-safe logical reads for the tested keys / policies | Physical rows may repeat; bypassing the approved query can inflate counts |
| Full-run identity and aggregate reconciliation | No missing/extra valid identities or incorrect aggregates in that bounded experiment | Not a universal no-data-loss guarantee |
| Single-node restart tests | Recovery from tested process failures with preserved volumes | Does not prove host-loss, replication or disaster recovery |

Do not use a passing happy-path integration test to advertise unrestricted reliability. Keep the guarantee, tested failure model, versions and known exceptions together.

## Benchmarks

Establish the first baseline after correctness tests pass. Treat possible target thresholds as proposals until a representative workload and workstation budget exist.

| Metric | Definition and reporting rule |
| --- | --- |
| Throughput | Separately report attempted observations, Kafka-acknowledged observations, distinct admitted events and distinct query-visible events per second; state interval and byte volume |
| Visibility latency | Time from adapter admission to first successful observation through the approved unique-read query; p50/p95/p99 plus sample count and polling resolution |
| Freshness | Sink visibility minus physical source time only for a trustworthy live clock; report historical source age separately |
| Consumer lag | Partition end offset minus committed progress, sampled over time; identify whether pending sink work is excluded |
| Event-time progress | Per-input/operator watermark and distance from expected source progress, interpreted separately for historical runs |
| Checkpoints | Completed/failed count, age of last success, duration distribution and state bytes for the declared checkpoint interval |
| Recovery | Failure-to-restored-processing time, plus separate failure-to-backlog-drained time; define failure detection and drain criteria |
| Data quality | Invalid, late, duplicate, missing and conflicting counts/rates with explicitly different observation / event denominators |
| Resource use | Container and host CPU, current/peak RAM, disk usage/growth, I/O and network; include WSL limits and storage placement |

Use a monotonic clock for local elapsed intervals; cross-process timestamps require a documented synchronized clock and uncertainty estimate. Account for probe overhead and query polling. Do not report high-precision latency below the resolution of the measurement method.

Each report records source checksums, generator and seed, payload size, event mix, vehicle count and skew, partitions, concurrency, replay rate, duplicate/late rates, all version pins, CPU/RAM/storage, resource limits, warm-up, measurement period, drain period and repetitions. Include failures and incomplete observations; do not omit slow runs without a stated reason.

The initial M6 exporter checks establish literal snapshot
arithmetic, fixed labels, bounded invalid/stale input refusal and actual HTTP
fault/repair with safe causes. They do not establish live collection, dashboard
queries or a load baseline. Missing samples stay unknown; repeated callback
snapshots cannot be summed or treated as monotonic throughput counters.

The subsequent M6 local monitoring checks validate
native metrics during the existing exact online scenario, all twelve panel
queries through Prometheus and Grafana, finite Grafana points and actual labels.
A real serving stop/start must change target health, fire/resolve the alert and
preserve complete SQL content. Reporter recovery and SQL readiness are separate
observations. Preserve rejected collector data after any identity-label defect;
corrected collection uses a fresh TSDB. These checks do not establish workload
percentiles, committed source lag, archive coverage or resource peaks.

The [first component replay baseline](case-studies/m6-transport-benchmark.md) now records
three real Kafka/ClickHouse repetitions with explicit duplicate-heavy scope,
byte/content reconciliation, raw first-visible latency samples and cgroup /
sampled resource boundaries. Percentiles/rates are recalculated from raw results;
slow repetitions and failed harness attempts are retained. Batch-correlated
first-burst samples do not establish full-pipeline or steady-stream capacity.

The subsequent bounded full-path timing check exercises
all five actual services three times at the current 32-observation source bound.
Exact source receipts, archive coverage, reference windows and complete SQL
content must reconcile before timing succeeds. A known-clock test distinguishes
ACK and unique-visible denominators and keeps a batch observation separate from
per-event percentile samples. The default four-observation profile also passes.
Sustained fleet capacity and checkpoint/recovery load remain outside this check.

Increase one dimension at a time. Publish raw summaries or bounded artifacts that allow recalculation, with safe identifiers. Report a local saturation point only if measured; do not extrapolate a single workstation into fleet-scale capacity.

## Evidence packaging and CI

The M4 foundation checks use separate restricted
Tester/Implementer CLI sessions with observed permission denials, frozen public
inputs and separate read-only review. Original contradictory or incomplete
test versions and their failures remain retained; reviewed supersessions follow
the unchanged contracts. The final storage and codec sets pass deterministic
acceptance. `scripts/check-m4.py` reruns the existing toolchain and 40 offline
methods from the adopted fixture copies; their test-method ASTs match the
frozen sources. Real-SDK redirect/ambient/deadline and real-backend
race/permission/replacement checks remain separate evidence, not fake-SDK claims.
Archive/rebuild and serving still require their own checks.

The 2026-10-21 maintenance review preserves
existing conversion scenarios while separating shared setup, publication
failures and CLI checks. It adds only malformed-context and metric-overflow
regressions. `scripts/check-m1.py` now checks the internal `telemetry/` package
and rejects owned Python modules with 500 or more lines before environment
setup. The size limit is a maintenance guard; semantic module boundaries and
observable invariants remain the review criteria.

The M2 compatibility plan defines the transport
evidence: exact key/value reconciliation, uncertain publication outcomes,
consumer receipt/commit windows, retained-volume restart and explicit retention
gaps. The first local experiment executes exact
admission and clean consumer reopen. The
receipt recovery follow-up now exercises the two
consumer process exit windows. The broker restart check
now reconciles retained records across one graceful restart. The
retention-gap follow-up observes actual time expiry and
refusal without advancing committed progress. The [SIGKILL follow-up](case-studies/kafka-broker-sigkill.md)
now verifies one abrupt broker JVM exit with the same retained records and stored
progress after startup. The consolidated cycle exercises
producer ACK-before-receipt failure and bounded unavailable/queue-full outcomes.
Lost broker ACKs and rebalances remain planned. Reuse M1
fixtures and reader coverage rather than duplicating producer-policy tests;
add transport tests only when that implementation is authorized.

Each implementation report should include the invariant, exact check command, environment, input/configuration hashes, expected/actual counts and content comparison, safe failure logs, outcome and remaining limitation. Store small approved fixtures and readable reports in Git; keep large data and sensitive evidence outside it with checksummed references.

M1 adds fast unit / contract / replay checks. M2-M4 add a bounded service-integration lane. M5 supplies repeatable reliability commands, and M6 load tests run explicitly with recorded hardware rather than as an unstable per-change gate. M7 rehearses the documented clean setup and consolidates CI. Do not introduce test infrastructure before there is behavior to test.

Terraform has a separate M8 validation lane: formatting, locked provider initialization, validation, reviewed plan, positive/negative access probes, drift check and controlled teardown when cloud execution is authorized. None of these cloud checks has run at Stage 0.

## Bounded M4 graph and coordination checks

The graph increment adds 21 independently authored frozen
methods before candidate exposure. They cover root trust, exact references,
source/job admission, coverage/overlap conflicts, publication faults, progress
ordering and incomplete reconstruction. The combined offline command now runs
61 methods: all pass on restricted Linux; native Windows Python 3.13 reports
one explicit symlink-fixture privilege skip, with that original case executed
fully in Linux. Parent-authored receipt-time and platform checks supplement
independent coverage and retain the original failures.

A separate restricted reconstruction process has observed private oracle,
converter-output and network denials. Its file-transport result independently
reconciles seven observations, three unique golden measurements and two blobs.
Separate real local S3 checks use reader credentials, a fresh reader process
and a retained-volume backend restart. Synthetic source/progress ports and
Windows S3 process access are not represented as actual Kafka commits or a
single isolated S3/Kafka-expiry recovery drill. Those gates remain required.

The bounded Kafka read checks add five independent frozen
port methods, bringing offline M4 to 66. The adopted copy has the same complete
AST as the frozen original. The actual Windows SDK candidate is rejected after
a broker/SDK byte-level UUID mismatch; record payload agreement does not waive
that failure. A separate real consumer demonstrates reset-disabled fetch refusal
after expiry, but the intended integrated native-reader acceptance did not
complete. Require a Linux full-UUID compatibility gate and a separate historical
Windows identity audit before reusing those claims. Original failures, the
explicit narrow repair-budget exception and review evidence stay retained.

The subsequent Linux reader verification
reuses the same frozen tests and unmodified candidate on CPython 3.13.1. All 66
offline M4 methods pass without skips. Real broker checks compare the full UUID
against Kafka CLI, reconcile four exact observations, expire the same topic
after a successful real preflight, and observe actual native fetch refusal
without changing committed progress. Trusted-parent live checks and separate
read-only evidence review do not establish new blind native tests or restricted
live filesystem/network isolation. The native candidate remains unadopted;
explicit platform/ABI guards and native-boundary tests are the next gate.

## Windows UUID repair verification, 2026-10-24

The [repair evidence](case-studies/windows-kafka-uuid-repair.md) adds a separate restricted
Tester before implementation, frozen literal signed-half/string checks and
malformed/lazy/no-client guard checks. The five methods require the actual SDK
for native probes and pass normally/optimized on Linux and corrected Windows;
stock Windows failure is mandatory evidence, not a skip. Windows integration
independently compares complete broker CLI identities, exact observations,
post-preflight expiry refusal and unchanged committed progress, then reuses
producer retry and consumer interruption checks. Two final builds must match
exact artifact hashes; pure/guard tests cannot replace AdminClient evidence.
Existing Linux regression remains 411 passed/32 optional ULog skips and M4's
66 methods pass. The report records all harness/build failures and the one
recipe-only repair. Separate read-only review, scope/frozen hashes and final
deterministic acceptance close only this bounded repair, not complete M4.

## Historical identity audit and upstream packaging, 2026-10-24

The audit uses broker-owned persisted metadata,
read-only mount inspection and a repeated byte/hash pass, plus a separate
integer-mask/sign calculation against every saved identity. It records exact
source hashes/pointers and six explicit command-topic bindings; 11 half-cut
negative inputs retain their observed refusal. Copied source/test caches and
embedded stdout are not promoted into complete historical coverage.

The contribution reuses the previously independent frozen native constructor
method with the same complete AST. Real stock Windows failure, corrected
Windows normal/optimized success and stock Linux success are required; pytest
also discovers the method. A separate actual broker comparison supplies the
independent full UUID oracle. Source-only upstream exports are apply/reverse
checked at pinned commits; no new blind Tester claim, upstream MSVC/full-CI
claim or runtime migration follows. A separate enforced read-only review checks
the audit and shareable package. Maintained project runtime code is unchanged.

## Guarded native reader admission, 2026-10-26

The native admission evidence adds seven
independent methods, bringing offline M4 to 73. The Tester receives only public
contracts before candidate exposure. Preserve original mock/API failures and
withdrawn oracle interpretations; the final superseding version corrects only
the SDK-root `TopicCollection` mock and retains every original assertion.
The adopted suite has the same complete AST after formatting/lint annotations.
Restricted read-only execution and review require observed write denials and
unchanged candidate/frozen hashes. Actual SDK guard probes separately exercise
stock Windows refusal, corrected Windows admission and stock Linux admission.

Each live platform compares complete topic UUIDs with Kafka CLI, reads four
exact observations, and demonstrates reset-disabled fetch refusal after a real
successful preflight and controlled expiry. Fresh preflight also refuses; original
committed progress stays zero. Mocked tests and trusted-parent live verification
remain distinct. Linux has no skips; Windows has one existing symlink-privilege
skip in the full suite and none in the seven native methods. No Kafka/S3 commit
ordering, archive-only expiry reconstruction or complete process deadline follows.

## Supervised archive runtime, 2026-10-26

The runtime evidence adds 12 independently frozen methods
for finite source/commit behavior, fresh bounded S3 lookup/inventory, exclusive
root retention and deadline/protocol/descendant handling. The original incomplete
transport interface and subsequent three timing-literal adjudications retain all
versions/results. Final adopted tests preserve the complete v4 AST. The separate
read-only Reviewer must assess these adjudications and the explicitly extended
runtime repair budget, including the original failed denials/checks.

Read-only Linux runs pass frozen normal/optimized, 85 combined methods, Ruff on
39 files and strict typing on 18 shared plus 8 Linux modules. Windows shared
checks pass with 7 explicit skips; Linux-only code is additionally typed with
the Linux target. A missing-mypy default-interpreter failure remains retained;
the successful run uses the existing project environment without installation.

Real boundaries separately prove role permissions, original input/root/oracle
access denial, observed writer exit at each fault gate, changed-batch retry,
actual commit progress, post-preflight expiry/fetch refusal and Kafka-off S3
reconstruction. The independent observer compares all seven observations,
three unique measurements, original blobs and exact rational reference results.
Storage replacement repeats fresh reconstruction. Corrupt/missing/untrusted
inputs produce no completion marker; real continuously trickled HTTP is stopped
by the supervisor deadline. Trusted-parent live harnesses are distinct from the
blind Tester and enforced read-only review. No serving, performance, hosted-CI,
host-loss or production capacity/response claim follows.

## Serving compatibility experiment, 2026-10-26

The serving report records real synchronous insert
success followed by dropped client responses, changed-batch retries, six physical
rows per table with merges stopped, exact golden identity/content comparison and
unchanged three-query results before/after merges. A separate guard rejects
conflicts even for empty query results; a conflicting superseded revision stays
fatal. Complete replacements, run/pipeline isolation and a synthetic late fact
pass. A fresh process reads unchanged results after container replacement on the
same volume, and separate role-denial checks repeat. These are one-session live
observations. No independent Tester, frozen acceptance or restricted Reviewer
ran; strict independent admission is still required before adopting the sink.

The subsequent pure projection gate uses a separate
restricted Tester before candidate exposure, public existing Graph fixtures and
seven frozen methods for full canonical semantics, exact precision refusal,
original/target lineage, duplicates/rebatching, fresh graph failures and no partial
return. Relevant existing graph/canonical checks are reused. Normal/optimized
execution, read-only review and deterministic acceptance are required. This
does not retroactively make the earlier live ClickHouse probe independent.

The event sink gate freezes nine independent coordinator/HTTP
methods before candidate exposure. A later explicit formatter adjudication changes
only the contract clause and SQL matcher from toString to toDecimalString(...,6)
after actual pinned-server scale loss; v1 and all failed/passing results remain.
Final v2 methods pass normal/-O, combined Linux has 102 methods without skips,
and Windows has 102 methods with 7 existing skips. Adopted ASTs match frozen v2.
Real local checks separately establish lost ACK after actual two-row INSERT,
singleton retry with five physical copies/three exact facts before merges,
full lineage/time/number readback, schema and data mismatch refusals, role
denials and fresh process/container replacement. An explicit parent omission
fault tests detectable missing sink data; it is not observed database loss.
Strict read-only review and deterministic admission are the final gates.

## Continuous partition-watermark regression, 2026-10-27

The backlog correction and load record adds an actual
18-partition backlog oracle: all 20,128 distinct deliveries must be eligible,
with zero late events, 2,048 closed and 128 open windows. Complete ACK/archive/SQL
byte reconciliation and exact rational sums pass. This oracle checks admission
independently of the observed watermark, unlike merely explaining late facts.
The real execution graph must retain eighteen FORWARD lanes from source through
watermark assignment; reduced parallelism and a pre-watermark shuffle are refused.
The separate 2.084 GB workload failed at the per-vehicle identity-state cap
after ten restorations. Preserve its 2,000,128 ACKs/archive cursor records,
323,584 SQL measurements, 39 completed / 48 failed checkpoints and eleven
retained state-limit exception entries. Count agreement at the archive cursor
is not an independent whole-ledger byte comparison; no final reconciliation
report was produced. Diagnose cleanup/watermark progress before another load.


## Continuous identity-state regression, 2026-10-27

The [state-limit investigation](case-studies/m6-identity-state-limit.md) adds eight purposeful
checks in `runtime/pyflink/test_continuous.py`. A checkpoint-shaped trace reaches
the actual 4096 cap; advancing exact expiry releases an entry. A one-Hz trace
bounds retained state at 603 under a progressing watermark. Actual small Flink
jobs compare the failing cross-partition minimum with isolated branches and
check duplicate/conflict/late results, unique windows, final zero state and the
production bundle size 128. The generated eighteen-branch plan is checked before
submission. The earlier eighteen-FORWARD-lane oracle remains historical v2
evidence; v3 deliberately gathers only a selected partition before assigning
time, and forbids merging different partition watermarks before keyed state.
Checkpoint copies establish count/cardinality agreement and advancing cleanup.
They do not certify every future expiry timer: 729 checkpoint-45 buckets lack a
matched JVM timer in the private decoder, all beyond the inferred watermark.
The actual-runtime expiry probe passes but is not a v3 restore proof. Full Kafka,
production memory/PID limits, checkpoint restore and large-load reconciliation
remain open; no new 2 GB run was performed.


## V3 full-path restoration preflight

The new isolated v3 check, separately authorized by the
maintainer, runs the actual eighteen-partition graph and existing workers.
Exact independent ACK/archive/SQL byte and rational-window comparisons pass
20512 deliveries: 20256 eligible, 128 duplicate after restore and 128 late after
expiry, with 20128 closed and 128 open windows. Unequal final frontiers test the
verifier's owning-partition closure rule. Copied restored state has 5172 IDs;
after event-time advances, all 128 vehicles retain only their one new ID, with
exact counters/buckets and matching expiry timers. No EOF is used for cleanup.
Cgroup peaks stay below 4 GiB and OOM/PID-limit counters remain zero. The restore
includes four recorded restorations due to temporary resource acquisition
failures, not a claim of seamless recovery. The old v2 binary-reader uncertainty
is not resolved by this new result. A new 2 GB run has started; publication,
archive counts or a RUNNING job are not substitutes for its final reconciliation.


## Battery RPC optimization verification

The performance record retains a frozen v3 operator
and identical synthetic inputs for actual SDK RPC counting and semantic-output
hash comparison. The measured operator interval and JVM-startup-inclusive wall
time are reported separately; neither is a full-cluster capacity claim. The
initial map-cache experiment is rejected after a longer known-key-index check.
Nine v4 tests pass in separate Python workers, including count/cardinality,
actual guard=4096, exact/subsecond expiry, duplicate/conflict/late routing,
independent partition topology and bundle-128 operation with forced cache
eviction across sixteen keys. A separate bounded native-Linux savepoint probe
checks retained v4 identity/window state; failed harness attempts remain evidence
and are not counted as passing checks. No 2 GB rerun or old-state migration is
claimed, and all persistent services are stopped.


## Independent live heartbeat checks

`tests/test_link_watch.py` tests silence without input/watermark progress,
replay/future/old-session refusal, fixed fleet bounds, receive-delay accounting,
monitor pause/restart and actual authenticated HTTP loss/recovery. The
connection-monitoring record
binds the separate 128-vehicle one-Hz container trace and distinguishes local
API visibility from browser/radio latency. No analytical or deduplication code
is changed. Actual radio/gateway dropout, sustained capacity and durable
notification delivery remain required before real-device adoption.


## Actual Flink-to-live latency

The execution record retains unsuccessful full-graph attempts
and the passing 2048-event/128-per-second publication-to-API trace, with all-event
visibility, p50/p95/p99, duplicate refusal and first visibility before checkpoint.
Eleven SDK tests cover existing invariants plus native watermark/key/expiry and
plan guards; five projection/HTTP checks cover stale/repeated/conflicting input
and server failure. Actual native checkpoint restores retain duplicate behavior.
Browser visibility is sampled separately from API latency. Historical SQL/S3,
real-radio transit, long-duration retention and saturation are not revalidated
by this small Kafka/Flink/API check.

## Bounded Gold overview

The Gold overview checks exercise identity and coordinate deduplication, conflicts, unsupported events and the input limit using the canonical example and a mocked ClickHouse transport. Source completeness and concurrent updates remain unverified; the separate isolated ClickHouse test is described below.

The synthetic position Gold checks cover stable replay, changed clock identity, unit mapping, invalid fix/time/identity and conflicting measurements. A fresh ClickHouse integration test checks mixed battery and position fixtures and duplicate physical rows using a SELECT-only reader. It does not exercise Flink, source/archive reconciliation or live-device ingestion.

## Restricted F09 flight view

The state checks and evidence
add original framing/parser equality for two exact-file streams, byte-identical
preparations, complete SQL typed/raw readback through admin and reader,
record-count/change arithmetic, duplicate/tamper/overwrite refusal and
SELECT-only denial. Actual Grafana queries are compared with prepared records.
These initial checks do not verify physical clock alignment, flight duration or
physical phases.

The state association evidence
adds direct original-frame checks for all selected native timestamps, two
identical association reconstructions, complete SQL readback and a separate
ASOF predecessor lookup for 42,108 pairs. Focused tests establish past-only and
inclusive-age matching, NULL unknowns, dropout-mask edges and ambiguous-clock
refusal. Grafana queries and a local browser verify actual values, age and status
panels. The same masks are reused in the ASOF check; no blind independence,
physical synchronization or flight-phase validation is claimed.

The real-flight evidence includes full source checksum/framing and selected-stream count, two deterministic preparations, every stored identity/hash and typed-field readback, SELECT-only refusal, signed plugin/connection checks, real Grafana SQL and headless marker-to-chart navigation with external browser requests blocked. It does not prove live-device, archive, Kafka/Flink, production recovery or multi-browser behavior.
