# Architecture Decision Record Index

**Baseline:** Level 22 Operational Readiness Review — approved input to Level 23
**Status:** Level 23 governance closure pending architecture and release review
**Operational disposition:** **NOT READY — release and environment evidence incomplete**

This index records decisions already represented in the repository. It is not a
target architecture and does not authorize migration, enforcement, or runtime
cutover.

| ADR | Decision captured | Implemented foundation | Status |
|---|---|---|---|
| [ADR-000](ADR-000.md) | Immutable, deterministic foundation contracts | Phase 0 | Accepted as implemented |
| [ADR-001](ADR-001.md) | Generic content-addressed registry core | Phase 1 | Accepted as implemented |
| [ADR-002](ADR-002.md) | Governance decisions and appendable audit evidence | Phase 2 | Accepted as implemented |
| [ADR-003](ADR-003.md) | Observe-only policy evaluation under legacy authority | Phase 3 | Accepted as implemented |
| [ADR-004](ADR-004.md) | Content-addressed provenance and evidence | Phase 4 | Accepted as implemented |
| [ADR-005](ADR-005.md) | Research-only, non-authoritative runtime model | Phase 5 | Accepted as implemented |
| [ADR-006](ADR-006.md) | Observation-only lifecycle, health, and resource accounting | Phase 6 | Accepted as implemented |
| [ADR-007](ADR-007.md) | Read-only integration snapshots and ports | Phase 7 | Accepted as implemented |
| [ADR-008](ADR-008.md) | Shadow comparison and evidence-only readiness reports | Phase 8 | Accepted as implemented |
| [ADR-009](ADR-009.md) | Legacy runtime remains execution authority; no migration | Phase 9 | Accepted as implemented |
| [ADR-010](ADR-010.md) | Immutable trust-policy snapshots and historical lookup | Hardening Sprint 5 | Accepted as implemented |
| [ADR-011](ADR-011.md) | Evidence-only verification manifests and replay | Hardening Sprint 6 | Accepted as implemented |
| [ADR-012](ADR-012.md) | Immutable observation archive and deterministic audit chain | Phase 11 | Pending architecture review |
| [ADR-013](ADR-013.md) | Evidence analytics and policy insights | Phase 12 | Pending architecture review |
| [ADR-014](ADR-014.md) | Deterministic evidence-layer integration and validation | Phase 13 | Pending architecture review |
| [ADR-015](ADR-015.md) | Read-only runtime event adaptation and event identity | Level 18 | Pending architecture review |
| [ADR-016](ADR-016.md) | Evidence-only runtime integration harness and sequence scope | Level 19 | Pending architecture review |
| [ADR-017](ADR-017.md) | Controlled shadow assessment vocabulary | Level 20 | Pending architecture review |
| [ADR-018](ADR-018.md) | Coverage, distribution, and trend semantics | Level 21 | Pending architecture review |

## Reading rules

- “Accepted” means the ADR describes approved code already present; it does not
  authorize runtime migration.
- The source of truth for behavior remains the implementation and tests.
- Any future enforcement, orchestration authority, migration, or cutover needs a
  separate decision and approval.
- ADR-015 through ADR-018 document currently uncommitted Level 18–21 material. They
  remain pending and do not make that material certified or release-addressable.
