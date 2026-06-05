# Security

OpenWright connectors handle evidence about high-risk AI systems. Two properties
matter most:

- **Hashes-only.** Connectors must never write raw prompts/PII into the ledger —
  payloads are hashed (`sha256:` references) via core. Report a connector that
  leaks raw payloads as a security issue.
- **No crypto re-implementation.** Connectors call core for canonical JSON, Merkle
  hashing, and Ed25519 signing; they never roll their own. This keeps a single
  byte-exact crypto core (the trust model's foundation).

## Reporting a vulnerability

Please report security issues privately to the maintainers (see CODEOWNERS) rather
than opening a public issue. Include the connector, version, and a reproduction.

Connectors are built on open surfaces (OTel, public APIs, framework hooks); no
partnership or endorsement is implied with any third party.
