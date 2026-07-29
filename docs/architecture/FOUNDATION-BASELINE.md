# Foundation Baseline

**Baseline date:** 2026-07-29  
**Baseline:** Level 11.8 — Foundation Baseline Finalization  
**Package version:** 0.1.12  
**Pre-foundation Git commit:** `e52b835` (`v0.1.12-189-ge52b835`)  
**Architecture re-audit:** **90/100 — CONDITIONAL GO**

## Approved scope

The baseline includes approved Phases 0–9 and Foundation Hardening Sprints 1–6:

1. Sprint 1 documented immutable foundation and architecture boundaries.
2. Sprint 2 hardened evidence digest and provenance verification.
3. Sprint 3 established strict deterministic canonical serialization.
4. Sprint 4 added independent issuer authenticity and fail-closed trust checks.
5. Sprint 5 added immutable, versioned trust-policy snapshots, lifecycle rules,
   canonical policy digests, and exact historical lookup.
6. Sprint 6 added deterministic, immutable verification manifests that bind
   evidence, policy snapshot metadata, results, and verification time.

## Authority and migration boundary

- The existing runtime remains the sole execution authority.
- AIOS, governance, readiness, trust-policy, and verification-manifest outputs are
  observations or evidence only.
- No runtime migration, execution path, signing, dual control, traffic cutover, or
  persistence backend was introduced by foundation hardening.
- CONDITIONAL GO approves the foundation baseline after operational closure; it
  does not approve migration or authority cutover.

## Re-audit outcome

The repository-wide re-audit verified authority retention, import isolation,
canonical serialization, integrity, provenance, authenticity, readiness,
trust-policy lifecycle, verification-manifest determinism, and historical replay.
Its remaining conditions were documentation currency, Git hygiene, development
tool availability, and reproducible full-suite validation.

## Known limitations

- Declared isolation remains explicitly unenforced.
- Evidence guarantees apply to captured observations and cannot prove capture
  completeness.
- Generic and feature-specific registries coexist.
- Historical replay requires the exact evidence and policy snapshot.
- Any future schema evolution must preserve explicit versioning and canonical
  digest rules.
- Migration requires a separately approved ADR, parity criteria, rollback design,
  and architecture review.

## Repository closure

- Architecture documentation under `docs/architecture/` is intentionally exposed
  by `.gitignore` for a commit-addressable baseline.
- Accidental root files containing redirected Git output were removed.
- No commit, tag, push, migration, or runtime change is performed by this sprint.

## Validation record

Commands executed from the repository root on 2026-07-29:

```text
python -m pip install "ruff>=0.9,<1"
python -m ruff check agent/src/aios agent/src/governance agent/src/integration agent/src/orchestration agent/src/registries agent/src/flags agent/tests/test_aios_registry_foundation.py agent/tests/test_evidence_verification_acceptance.py agent/tests/test_canonical_serialization_acceptance.py agent/tests/test_evidence_authenticity_acceptance.py agent/tests/test_trust_policy_lifecycle_acceptance.py agent/tests/test_verification_manifest_acceptance.py
python -m pytest agent/tests/test_aios_registry_foundation.py -q
python -m pytest agent/tests/test_evidence_verification_acceptance.py agent/tests/test_canonical_serialization_acceptance.py agent/tests/test_evidence_authenticity_acceptance.py agent/tests/test_trust_policy_lifecycle_acceptance.py agent/tests/test_verification_manifest_acceptance.py -q
python -m pytest agent/tests/test_aios_registry_foundation.py::test_foundation_import_boundary -q
python -m compileall -q agent
python -m py_compile agent/src/aios/provenance/serialization.py agent/src/aios/provenance/evidence.py agent/src/aios/provenance/authenticity.py agent/src/aios/provenance/manifest.py agent/src/aios/provenance/verification_manifest.py agent/src/governance/reporting/readiness.py
python -m pytest agent/tests -q
python -m pip install --user -e ".[dev]"
git diff --check
```

Summarized results:

- Ruff 0.16.0 installed successfully within the declared `ruff>=0.9,<1` range.
- Ruff executed and reported 100 existing foundation/test findings, predominantly
  missing final newlines and import formatting. No automatic source rewrite was
  performed during repository closure.
- Foundation suite: **18 passed**.
- Sprint 2–6 canonical/integrity/authenticity/lifecycle/manifest suite:
  **38 passed**.
- Dedicated foundation import-boundary test: **1 passed**.
- Full `agent/` compile validation: passed with exit code 0.
- Verification-chain `py_compile`: passed.
- Full `agent/tests` collection was blocked by absent declared base dependencies,
  including `fastmcp`, `defusedxml`, and `ccxt`. The attempted editable base/dev
  installation exceeded the available execution window, made no completed package
  progress, and its orphaned process was terminated. This is an environment/tooling
  blocker, not a test assertion failure.
- `git diff --check` passed with only a Windows LF-to-CRLF conversion warning.

## Release preparation

Recommended commit message:

```text
chore(architecture): finalize hardened foundation baseline
```

Recommended annotated tag:

```text
foundation-baseline-v0.1.12-level11.8
```

Recommended annotation:

```text
Level 11.8 finalized foundation baseline: approved Phases 0-9 and Sprints 1-6; architecture re-audit 90/100 CONDITIONAL GO; existing runtime authority retained; no migration
```
