# openwright-langfuse

A **Langfuse forwarder** for [OpenWright](https://github.com/allthingsN/openwright):
keep your traces in Langfuse *and* attach the OpenWright verdicts back to them.

- **forward** — co-ingest a telemetry batch to Langfuse unchanged (Basic auth +
  `x-langfuse-ingestion-version: 4`).
- **backlink** — push `openwright:<control>` scores (the verdicts) onto the trace,
  with the reason as a comment; returns a deep-link.
- **pull** — read Langfuse scores/evals back as `ComplianceEvent`s (evals-as-evidence).

```python
from openwright.connectors import load
fwd = load("openwright.forwarders", "langfuse")
cfg = {"host": "https://cloud.langfuse.com", "public_key": "pk-…", "secret_key": "sk-…", "trace_id": trace_id}
fwd.backlink(report, config=cfg)   # openwright:* verdicts now on the Langfuse trace
```

No partnership or endorsement implied; built on Langfuse's public HTTP API. No
crypto is reimplemented here.
