# Contributing a connector

A connector is an independently-publishable `openwright-<name>` package that
implements one connector contract and is discovered by core via an entry point.

## Start from the template

```bash
cp -r packages/_template packages/openwright-<name>
```

Then:

1. **Rename** the package: directory, `src/openwright_<name>/`, `pyproject` `name`
   and wheel target.
2. **Pick the contract** and declare the matching entry point in `pyproject`:
   - `SourceConnector` → `[project.entry-points."openwright.source_connectors"]`
   - `Forwarder` → `openwright.forwarders`
   - `ReportExporter` → `openwright.report_exporters`
   - storage factory (`from_uri`) → `openwright.ledger_backends` / `openwright.checkpoint_stores`
3. **Declare the contract version** you target (`CONTRACT_VERSION` on the class or
   module). Depend on `openwright-core>=0.6,<0.7`.
4. **Implement it**, honoring the invariants below.
5. **Pass conformance**: `pytest` runs the shared harness (`openwright_conformance`).

## Invariants (non-negotiable — conformance + review enforce these)

- **Hashes-only.** Never put raw prompts/PII into a `ComplianceEvent`. Hash payloads
  with `openwright.canonical.hash_payload`.
- **No crypto re-implementation.** Call core for canonical JSON / Merkle / signing.
  Don't `import hashlib`/`cryptography` to roll your own (the harness scans for this).
- **Append-only**, **boundary statement** in any artifact you emit, and an
  **additive evidence path** — a connector must never drop or alter the host app's
  primary telemetry.
- **Decoupled.** Import only the public `openwright` / `openwright.connectors` API.
  Never import another connector (`.importlinter` fails CI if you do).

## Conformance checklist

- [ ] Entry point declared in the right group; `openwright connectors list` shows it.
- [ ] Implements its contract (`run_conformance(...)` passes).
- [ ] `CONTRACT_VERSION` declared and compatible with core.
- [ ] Hashes-only + no crypto re-impl.
- [ ] Core-compat range set; a row added to `COMPATIBILITY.md`.
- [ ] A runnable quickstart in the package README.
