"""Langfuse forwarder for OpenWright (CONN-2).

The downstream-observability pattern as a :class:`Forwarder`:

* ``forward``  — co-ingest a telemetry batch to Langfuse **unchanged**, injecting
  Basic auth + ``x-langfuse-ingestion-version: 4`` (Langfuse is HTTP-only).
* ``backlink`` — push ``openwright:<control>`` **scores** (the verdicts) onto the
  Langfuse trace via the public API, with the reason as a comment, and return a
  deep-link to the trace.
* ``pull``     — read Langfuse scores/evals and yield them as ``ComplianceEvent``s
  (evals-as-evidence).

No crypto here; payloads are hashed by the source connector before they become
events. ``config`` carries ``host``, ``public_key``, ``secret_key`` and per-call
fields (``trace_id`` for ``backlink``). Pass ``_transport`` (an httpx transport)
to talk to a stub in tests.
"""

from __future__ import annotations

import base64
from typing import Any, Iterable

from openwright.connectors import CONTRACT_VERSION, ExportResult

__all__ = ["LangfuseForwarder", "forwarder", "CONTRACT_VERSION"]


class LangfuseForwarder:
    name = "langfuse"
    CONTRACT_VERSION = CONTRACT_VERSION

    def _client(self, config: dict):
        import httpx

        host = str(config["host"]).rstrip("/")
        token = base64.b64encode(
            f"{config['public_key']}:{config['secret_key']}".encode("utf-8")
        ).decode("ascii")
        headers = {
            "Authorization": f"Basic {token}",
            "x-langfuse-ingestion-version": "4",
        }
        return httpx.Client(
            base_url=host, headers=headers, timeout=config.get("timeout", 10),
            transport=config.get("_transport"),
        )

    def forward(self, payload: Any, *, config: dict) -> ExportResult:
        path = config.get("ingest_path", "/api/public/otel/v1/traces")
        with self._client(config) as c:
            if isinstance(payload, (bytes, bytearray)):
                r = c.post(path, content=bytes(payload),
                           headers={"Content-Type": "application/x-protobuf"})
            else:
                r = c.post(path, json=payload)
        return ExportResult(ok=r.is_success, detail=f"forward -> HTTP {r.status_code}")

    def backlink(self, report: dict, *, config: dict) -> ExportResult:
        trace_id = config.get("trace_id")
        oks: list[bool] = []
        with self._client(config) as c:
            for ctrl in report.get("controls", []):
                body = {
                    "traceId": trace_id,
                    "name": f"openwright:{ctrl['control_id']}",
                    "value": ctrl["status"],
                    "dataType": "CATEGORICAL",
                    "comment": (ctrl.get("reason") or "")[:500],
                }
                oks.append(c.post("/api/public/scores", json=body).is_success)
        url = f"{str(config['host']).rstrip('/')}/trace/{trace_id}" if trace_id else None
        ok = all(oks) if oks else True
        return ExportResult(ok=ok, detail=f"back-linked {sum(oks)}/{len(oks)} verdict(s)", url=url)

    def pull(self, *, config: dict) -> Iterable[Any]:
        from openwright.canonical import to_rfc3339
        from openwright.events import ComplianceEvent, EventKind

        with self._client(config) as c:
            r = c.get("/api/public/scores", params={"limit": config.get("limit", 50)})
            r.raise_for_status()
            for sc in r.json().get("data", []):
                yield ComplianceEvent(
                    timestamp=to_rfc3339(sc.get("timestamp") or "1970-01-01T00:00:00.000000000Z"),
                    kind=EventKind.CONFORMANCE_FINDING,
                    actor={"agent_id": "langfuse"},
                    source={"format": "langfuse"},
                    attributes={
                        "score_name": sc.get("name"),
                        "value": str(sc.get("value")),
                        "trace_id": sc.get("traceId"),
                    },
                )


#: The object the ``openwright.forwarders:langfuse`` entry point loads to.
forwarder = LangfuseForwarder()
