"""Conformance + wedge acceptance for openwright-openai-agents (no SDK needed)."""

from __future__ import annotations

from datetime import timedelta

from openwright.crosswalk import ControlStatus, evaluate
from openwright.crosswalk_loader import load_builtin
from openwright.ledger import InMemoryLedgerBackend, Ledger
from openwright.sdk import EvidenceClient

from openwright_openai_agents import connector


def test_conforms():
    from openwright_conformance import run_conformance

    run_conformance(connector, group="openwright.source_connectors", name="openai_agents",
                    modules=["openwright_openai_agents"])


def test_wedge_evidence_matches_langgraph_shape():
    led = Ledger(InMemoryLedgerBackend(), retention=timedelta(days=200))
    client = EvidenceClient(led, agent_id="loan-agent")

    with connector.instrument(client, thread_id="loan-1") as run:
        run.on_tool_call("credit_check", "score 742")  # hashed, never raw
        run.record_risk_classification("high", rationale="consumer credit decision")
        appr = run.record_human_approval(reviewer="alice@bank", rationale="reviewed")
        run.record_decision(output="APPROVED", risk_classification="high",
                            rationale="ok", approval_ref=appr.event_id, control="art-14-human-oversight")

    tool_ev = next(e for e in led.events() if e.kind == "tool_call")
    assert tool_ev.io.output_ref.startswith("sha256:")
    res = evaluate(load_builtin("eu-ai-act"), list(led.events()))
    s = {c.control_id: c.status for c in res.controls}
    assert s["art-14-human-oversight"] == ControlStatus.SATISFIED
