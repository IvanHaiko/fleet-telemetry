# ADR-0004: Deliver locally first and reserve Terraform for a gated AWS stage

**Status:** Accepted for local-first sequencing and infrastructure ownership. AWS services, resource topology and Terraform/provider versions remain proposed until optional M8.

**Date:** 2026-10-19

## Context

The first engineering risk is incorrect handling of measurement identity, event time and recovery. Deploying cloud infrastructure before resolving those questions would add cost and permissions work without stronger correctness evidence. The Windows workstation also has an unmeasured resource budget.

Terraform remains relevant to a reproducible Data Platform Engineering portfolio, but its role should be concrete rather than a directory of unused examples.

## Decision

Use incremental Docker Compose execution with Linux containers on Windows / WSL2 for M2-M7. M1 remains infrastructure-free. Capture host requirements and resource measurements before claiming a supported capacity.

Include optional M8 for Terraform-managed AWS infrastructure after the local release. Start with a private archive and least-privilege workload access if that demonstrates a useful independent storage / restore boundary. Choose any compute or managed streaming services only after comparing cost, operational effort and actual requirements in a new ADR.

Compose owns local runtime resources. Terraform owns approved cloud infrastructure, not record replay, SQL data mutations or a shell-driven local environment. State backend bootstrap, workload lifecycle, application deployment and data migration have separate documented ownership.

M8 requires a cloud objective, budget, version pins, secure locked state, reviewed plan, separate cloud execution authorization, compatibility tests, drift evidence and a deliberate teardown / retention procedure. Stage 0 creates documentation only.

## Alternatives

- **Cloud-first managed services:** reduces some local hosting work, but adds costs and platform-specific constraints before the core behavior is understood.
- **Terraform-managed local containers:** exercises Terraform syntax but duplicates Compose responsibilities without demonstrating cloud lifecycle or security engineering.
- **Kubernetes from the beginning:** introduces scheduling, networking and storage operations that are unnecessary for a single bounded slice.
- **No infrastructure-as-code path:** adequate for local correctness, but leaves a future cloud demo dependent on manual setup. Keep Terraform as a defined extension with an acceptance gate.

## Consequences

Local development stays accessible and the Version 1 release does not depend on AWS spending. Cloud work is deferred rather than forgotten: it has a milestone, ownership rules and concrete evidence requirements.

Compose does not prove production availability. Local storage APIs and single-node failures do not demonstrate AWS equivalence. M8 must retest data access, sink/storage compatibility, state security and teardown in its selected environment. Infrastructure code will be added only when that work is authorized and reviewable.

## Related documents

### Archive service selection follow-up, 2026-10-22

[ADR-0020](0020-bounded-tests-and-s3-archive.md) selects Amazon S3 as the final
archive target, superseding only that unresolved AWS service choice. Local-first
sequencing, cloud execution authorization, cost/lifecycle review and Terraform
ownership remain intact; no cloud resource is created by the selection.

[Deployment and Terraform](../deployment-and-terraform.md), [roadmap](../roadmap.md), [architecture](../architecture.md).
