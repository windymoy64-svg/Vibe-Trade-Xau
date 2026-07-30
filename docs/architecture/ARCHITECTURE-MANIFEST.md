# Architecture Manifest

**Manifest status:** Foundation finalized; Levels 18–21 pending architecture review
**Repository:** Vibe-Trading-XAUUSD  
**Architecture audit:** **CONDITIONAL GO — 90/100**  
**Runtime impact of this manifest:** None

This manifest describes architecture already represented in the repository. It
does not promote the foundation into an authoritative runtime.

## Approved baseline

- Phases 0–9 establish immutable contracts, registries, governance evidence,
  observe-only policy evaluation, provenance, research observations, read-only
  integration, shadow comparison, and retained existing-runtime authority.
- Hardening Sprint 2 strengthened evidence integrity and provenance verification.
- Sprint 3 established strict canonical serialization.
- Sprint 4 separated issuer authenticity from evidence integrity.
- Sprint 5 introduced immutable, versioned trust-policy snapshots and historical
  lookup.
- Sprint 6 introduced immutable verification manifests and historical replay.
- The repository-wide re-audit scored the architecture 90/100 and issued a
  CONDITIONAL GO with repository-hygiene conditions only.

## Authority model

- The existing/legacy runtime is the execution authority.
- AIOS policy evaluation is observe-only and cannot widen a legacy decision.
- Research runtime manifests, supervisors, and shadow reports explicitly reject
  or disclaim authoritative/executable status.
- Governance and provenance supply decisions and evidence; they do not execute.

## Dependency rules

- Foundation contracts are immutable and deterministic.
- The AIOS, governance, and registry foundation may not import agent, swarm,
  live, tools, providers, trading, frontend, API, deployments, or experiments.
  This is enforced by `test_foundation_import_boundary`.
- Runtime dependencies are represented as exact resource/version/digest
  references before execution; the manifest itself does not resolve or execute.
- Integration depends on externally supplied observations rather than runtime
  mutation APIs.

## Registry model

- Registry identity is a stable namespaced `ResourceId` plus semantic version.
- Records carry ownership, compatibility, lifecycle, labels, metadata, creation
  identity/time, and a deterministic seal digest.
- Memory and atomic file stores implement the same structural protocol.
- Duplicate publication and corrupt/unsupported persisted records fail closed.
- The generic registry does not automatically replace the repository’s existing
  feature-specific registries.

## Governance model

- Governance outcomes are explicit contracts rather than implicit booleans.
- Audit events flow through sink abstractions, including JSONL and composite
  sinks; reporting consumes evidence.
- Local AIOS evaluation is deterministic and observe-only.
- Existing deny decisions are preserved. Evaluation errors are represented as
  errors rather than permits.
- There is no AIOS enforcement or command path in the documented foundation.

## Integration model

- Existing runtime observations enter through read-only adapters.
- Observations become immutable canonical snapshots with authority metadata and
  optional previous-digest chaining.
- Snapshots can be exported as content-addressed evidence.
- Comparison ports and shadow coordination operate on captured data, not live
  runtime control surfaces.

## Observation model

- Runtime context is research-only and timestamped in UTC.
- Isolation is declared but explicitly unenforced.
- Health, resource accounting, lifecycle proposals, policy decisions, and
  provenance are observations.
- Canonical serialization and SHA-256 digests provide integrity and comparison
  anchors; they do not prove enforcement or execution.
- Authenticity verification resolves an issuer against one explicit trust-policy
  snapshot identified by policy ID, version, and canonical digest.
- Verification manifests bind evidence, policy metadata, result, and timestamp
  into deterministic evidence-only audit artifacts.

## Orchestration model

- The implemented AIOS supervisor observes; it does not schedule, provision,
  restart, terminate, or remediate.
- Lifecycle validation describes valid transitions but does not apply them.
- Shadow coordination compares already captured observations.
- Operational orchestration remains with existing runtime paths outside this
  foundation.

## Migration boundaries

- No runtime migration is approved or implemented by Phases 0–9 documentation.
- No dual-write, dual-control, traffic routing, enforcement cutover, or automatic
  fallback is authorized.
- The existing runtime remains authoritative while AIOS outputs remain evidence.
- Migration requires a future approved ADR, quantified acceptance criteria,
  rollback design, and explicit architecture approval for migration.

## Manifest invariants

1. Foundation code does not become authoritative by being imported.
2. Evidence generation never implies execution permission.
3. Declared isolation is not represented as enforced isolation.
4. A legacy deny cannot become a permit through observe-only comparison.
5. CONDITIONAL GO applies only to the evidence foundation; it does not approve
   migration or authority cutover.
6. Trust policy and verification manifest behavior is governed by ADR-010 and
   ADR-011.
7. Runtime-event identity is `(source_id, sequence_id, event_id)`; sequence scope is
   one source stream, as documented by ADR-015.
8. Shadow assessments use the closed `approve`, `deny`, `hold`, `unknown` vocabulary
   and never replace the existing-runtime decision, as documented by ADR-017.
9. Coverage and trends describe supplied evidence only and cannot establish capture
   completeness, population representativeness, or operational health.
10. Public Levels 18–21 contracts remain at their baseline semantics until an
    explicitly versioned, architecture-approved successor exists.

## Pending Levels 18–21 records

- ADR-015 documents Level 18 read-only runtime adaptation.
- ADR-016 documents Level 19 batch ingestion and deterministic replay.
- ADR-017 documents Level 20 controlled shadow comparison.
- ADR-018 documents Level 21 evidence-only aggregate metrics.
- These records describe pending, currently uncommitted material. They add no runtime
  authority and do not authorize release, deployment, migration, or Level 24.
