<h1 align="center">🔌 OpenWright Connectors</h1>

<p align="center">Modular, independently-installable connectors for
<a href="https://github.com/allthingsN/openwright"><b>OpenWright</b></a> — the agent evidence layer.</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://github.com/allthingsN/openwright-connectors/actions"><img src="https://github.com/allthingsN/openwright-connectors/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/allthingsN/openwright"><img src="https://img.shields.io/badge/core-openwright--core%20%E2%89%A50.6-16a34a" alt="core"></a>
</p>

Connectors plug into core through the stable `openwright.connectors` contract (v1.0) and
**entry points** — so `openwright.instrument("langgraph")` and `openwright connectors list`
discover them automatically. **Core never depends on a connector**: adding or removing one
needs zero core change, and a connector never imports another connector (enforced in CI).

```mermaid
flowchart LR
    A("🤖 your agent"):::agent -->|"source connector<br/>langgraph · openai-agents"| CORE
    CORE(["openwright-core<br/><i>ledger · Merkle · crosswalks · verifier</i>"]):::core
    CORE -->|"ledger_backends"| PG("postgres<br/>durable ledger"):::store
    CORE -->|"checkpoint_stores"| S3("s3 — Object-Lock / WORM"):::store
    CORE -->|"forwarders"| LF("langfuse<br/>back-link verdicts"):::fwd
    CORE -->|"report_exporters"| GH("github-action<br/>CI gate · SARIF"):::exp

    classDef agent fill:#eef2ff,stroke:#6366f1,color:#312e81;
    classDef core fill:#dcfce7,stroke:#16a34a,color:#064e3b;
    classDef store fill:#064e3b,stroke:#10b981,color:#d1fae5;
    classDef fwd fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef exp fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e;
```

## Packages

| Package | Type | What it does |
|---|---|---|
| [`openwright-langgraph`](packages/openwright-langgraph) | source | Capture LangGraph agent decisions, tools, and human-in-the-loop approvals as evidence. |
| [`openwright-openai-agents`](packages/openwright-openai-agents) | source | Same, for the OpenAI Agents SDK (one-line `instrument("openai-agents")`). |
| [`openwright-langfuse`](packages/openwright-langfuse) | forwarder | Co-ingest to Langfuse + back-link `openwright:*` verdicts. |
| [`openwright-postgres`](packages/openwright-postgres) | storage | Durable, multi-writer PostgreSQL ledger backend. |
| [`openwright-s3`](packages/openwright-s3) | storage | S3 checkpoint store with Object-Lock / WORM chain-of-custody. |
| [`openwright-github-action`](packages/openwright-github-action) | exporter | CI evidence gate: fail the build on unsatisfied controls + upload SARIF. |
| [`_template`](packages/_template) | — | Copy-to-start a new connector. |

## Quickstart

```bash
pip install openwright-core openwright-langgraph openwright-langfuse openwright-postgres
openwright connectors list                 # see what's installed
examples/lending-agent/run_local.sh        # capture → evidence → verify → (Langfuse) → CI gate
```

See [`examples/lending-agent/`](examples/lending-agent) for the flagship demo composing the
connectors end-to-end, and [openwright-examples](https://github.com/allthingsN/openwright-examples)
for before/after integrations on real agents.

## Principles

- **Modular** — each `packages/*` is an independently-publishable `openwright-<name>`
  distribution depending on `openwright-core>=0.6,<0.8` (the contract floor).
- **Decoupled** — a connector imports only the public `openwright` / `openwright.connectors`
  API, never another connector (enforced by `.importlinter` in CI).
- **Conformant** — every connector passes the shared conformance harness (`conformance/`):
  it implements its contract, registers its entry point, and preserves the invariants —
  **hashes-only** (no raw PII in events), **no crypto re-implementation** (call core),
  append-only, the boundary statement, and the additive (never-blocking) path.

Built on open surfaces (OTel, public APIs, framework hooks); **no partnership or endorsement**
is implied (Langfuse, AWS, OpenAI, GitHub). Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

> *OpenWright produces evidence that controls were exercised. It is not, and does not claim to
> be, a legal compliance certification.*
