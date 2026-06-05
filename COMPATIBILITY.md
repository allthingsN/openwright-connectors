# Compatibility matrix

Each connector declares the OpenWright **core** range it supports and the
**connector contract** version it targets. CI tests every connector against the
**min** and **latest** supported core (REPO-3) and regenerates this table.

Connector contract: **v1.0** (`openwright.connectors.CONTRACT_VERSION`).

| Connector | Version | Core range | Contract | Framework dep |
|-----------|---------|------------|----------|---------------|
| openwright-langgraph | 0.4.0 | `>=0.6,<0.8` | 1.0 | langgraph>=0.2 |
| openwright-openai-agents | 0.4.0 | `>=0.6,<0.8` | 1.0 | openai-agents (optional) |
| openwright-langfuse | 0.4.0 | `>=0.6,<0.8` | 1.0 | httpx>=0.27 |
| openwright-postgres | 0.4.0 | `>=0.6,<0.8` | 1.0 | psycopg>=3.1 |
| openwright-s3 | 0.4.0 | `>=0.6,<0.8` | 1.0 | boto3>=1.34 |
| openwright-github-action | 0.4.0 | `>=0.6,<0.8` | 1.0 | — |

> Bump a connector's row when its core range or contract target changes. CI fails
> if a connector's declared range doesn't match the cores it's tested against.
