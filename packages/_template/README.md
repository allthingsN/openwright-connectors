# openwright-template

Starter for a new OpenWright connector. Copy this directory to
`packages/openwright-<name>`, then:

1. Rename `openwright_template` → `openwright_<name>` (dir, package, `pyproject` name + wheel target).
2. Pick the contract you implement and set the right `[project.entry-points."<group>"]`.
3. Implement it (call `openwright` for any hashing/Merkle/signing — never reimplement crypto).
4. Make `pytest` pass — it runs the shared conformance harness.
5. Set your core-compat range (`openwright-core>=0.6,<0.7`) and add a row to `COMPATIBILITY.md`.

A connector is "done" only when it passes conformance + the decoupling guard and
preserves the invariants (hashes-only, append-only, no crypto re-impl, boundary statement).
