"""Conformance + wedge acceptance for openwright-langgraph.

Acceptance: a human-approved high-risk decision yields Art-14 satisfied (and the
tool call is auto-captured), an un-approved one is flagged — verified offline.
"""

from __future__ import annotations

from datetime import timedelta

from openwright.crosswalk import ControlStatus, evaluate
from openwright.crosswalk_loader import load_builtin
from openwright.ledger import InMemoryLedgerBackend, Ledger
from openwright.report import build_report
from openwright.sdk import EvidenceClient
from openwright.signing import InMemoryKeySource
from openwright.verify import verify_report

from openwright_langgraph import connector


def test_conforms():
    from openwright_conformance import run_conformance

    run_conformance(connector, group="openwright.source_connectors", name="langgraph",
                    modules=["openwright_langgraph"])


def _client():
    led = Ledger(InMemoryLedgerBackend(), retention=timedelta(days=200))
    return led, EvidenceClient(led, agent_id="loan-agent")


def _art14(led):
    res = evaluate(load_builtin("eu-ai-act"), list(led.events()))
    return res, {c.control_id: c.status for c in res.controls}["art-14-human-oversight"]


def test_approved_decision_satisfies_art14_and_captures_tool():
    from langchain_core.tools import tool

    @tool
    def credit_check(applicant: str) -> str:
        """Look up a credit score."""
        return "score 742"

    led, client = _client()
    with connector.instrument(client, thread_id="loan-1") as run:
        # auto-capture: invoking a LangChain tool with the connector's callbacks
        # records a tool_call event (payload hashed, never raw).
        credit_check.invoke({"applicant": "A"}, config={"callbacks": run.callbacks})
        run.record_risk_classification("high", rationale="consumer credit decision")
        appr = run.record_human_approval(reviewer="alice@bank", rationale="reviewed KYC")
        run.record_decision(output="APPROVED at 6.2% APR", risk_classification="high",
                            rationale="score above threshold", approval_ref=appr.event_id,
                            control="art-14-human-oversight")

    kinds = [e.kind for e in led.events()]
    assert "tool_call" in kinds  # the callback handler captured the tool use
    # no raw payload in the ledger — only a hash reference
    tool_ev = next(e for e in led.events() if e.kind == "tool_call")
    assert tool_ev.io.output_ref.startswith("sha256:")

    res, art14 = _art14(led)
    assert art14 == ControlStatus.SATISFIED
    key = InMemoryKeySource()
    assert verify_report(build_report(led, res, key, scope_description="lg approved"),
                         trusted_public_key_raw=key.public_key_raw()).valid


def test_unapproved_decision_is_flagged():
    led, client = _client()
    with connector.instrument(client, thread_id="loan-2") as run:
        run.record_risk_classification("high", rationale="consumer credit decision")
        run.record_decision(output="DENIED", risk_classification="high",
                            rationale="auto-denied", control="art-14-human-oversight")
    _res, art14 = _art14(led)
    assert art14 == ControlStatus.NOT_SATISFIED
