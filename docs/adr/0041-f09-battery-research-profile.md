# ADR-0041: Isolated F09 battery research profile

**Status:** Proposed for the authorized local experiment; real-source adoption
remains open. No accepted measurement semantics are superseded.

The retained F09 source exceeds the existing small-reader limits and contains
default parameters and binary multi-info chunks. A candidate-specific profile
may use higher explicit input/frame limits only for the registered F09 checksum,
validate the additional service structures, and reconcile the original complete
file before assigning selected-stream ordinals. Never strip frames or trust a
filtered parser alone. Retain the existing smaller defaults for other sources.
Resource limits bound inputs and indexing, not process RSS; the full upstream
reader can use substantially more memory. Stop visibly on any unsupported input.

The exact firmware and source checksum select a new normalization lineage;
do not relabel the existing firmware mapping. Battery timestamps remain source
publication time under a fixed synthetic anchor. The conservative current
policy rejects undocumented negative values other than `-1`; it does not infer
charging. Metadata and field definitions do not establish the actual physical
producer, so the outcome remains restricted research, not producer adoption.
Retain dropout counts and make no completeness claim beyond registered bytes.

Alternatives include raising global limits (expands every input's resource
exposure), parsing a shortened derivative (loses original ordinal evidence),
or writing a new semantic parser (higher maintenance). The selected isolated
profile retains the upstream parser and existing boundary checks. No dependency,
service or cloud resource is added. Roll back the profile without deleting
retained input or runs. Verify malformed extra service messages, limits,
ordinals, compatibility, two deliveries and independent reader reconciliation
before reporting an executable result.
