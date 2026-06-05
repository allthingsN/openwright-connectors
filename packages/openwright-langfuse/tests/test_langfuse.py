"""Conformance + request-shape behavior (httpx mock transport) for openwright-langfuse."""

from __future__ import annotations

import base64
import json

import httpx

from openwright_conformance import run_conformance
from openwright_langfuse import forwarder

CONFIG = {"host": "https://cloud.langfuse.test", "public_key": "pk", "secret_key": "sk"}


def test_conforms():
    run_conformance(forwarder, group="openwright.forwarders", name="langfuse", modules=["openwright_langfuse"])


def test_forward_injects_auth_and_ingestion_version():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["iv"] = request.headers.get("x-langfuse-ingestion-version")
        return httpx.Response(207)

    cfg = {**CONFIG, "_transport": httpx.MockTransport(handler)}
    res = forwarder.forward(b"\x00otlp-bytes", config=cfg)
    assert res.ok
    assert seen["url"].endswith("/api/public/otel/v1/traces")
    assert seen["auth"] == "Basic " + base64.b64encode(b"pk:sk").decode()
    assert seen["iv"] == "4"


def test_backlink_posts_openwright_verdict_scores():
    posted = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/public/scores"
        posted.append(json.loads(request.content))
        return httpx.Response(201)

    cfg = {**CONFIG, "trace_id": "tr_123", "_transport": httpx.MockTransport(handler)}
    report = {"controls": [
        {"control_id": "art-14-human-oversight", "status": "satisfied", "reason": "approved"},
        {"control_id": "art-27-fria", "status": "not_satisfied", "reason": "no FRIA"},
    ]}
    res = forwarder.backlink(report, config=cfg)
    assert res.ok and res.url == "https://cloud.langfuse.test/trace/tr_123"
    names = {p["name"]: p["value"] for p in posted}
    assert names == {"openwright:art-14-human-oversight": "satisfied", "openwright:art-27-fria": "not_satisfied"}
    assert all(p["traceId"] == "tr_123" for p in posted)


def test_pull_yields_events_from_scores():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [
            {"name": "hallucination", "value": 0.1, "traceId": "tr_1", "timestamp": "2026-05-28T00:00:00Z"},
        ]})

    cfg = {**CONFIG, "_transport": httpx.MockTransport(handler)}
    events = list(forwarder.pull(config=cfg))
    assert len(events) == 1
    assert events[0].kind == "conformance_finding"
    assert events[0].attributes["score_name"] == "hallucination"
