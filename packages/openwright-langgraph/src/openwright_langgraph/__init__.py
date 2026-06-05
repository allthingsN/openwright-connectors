"""LangGraph source connector for OpenWright (CONN-1) — wedge-critical capture.

Instruments LangGraph lending/underwriting agents: tool calls and model calls are
captured automatically via a LangChain callback handler, and the wedge controls —
**human-in-the-loop approval** and the **credit decision** — are recorded through
the SDK with correct thread/task linkage. Payloads are hashed (never stored raw).
No crypto is reimplemented; hashing is core's ``hash_payload``.

Usage::

    from openwright.connectors import load
    conn = load("openwright.source_connectors", "langgraph")
    with conn.instrument(client, thread_id="loan-42", context_id="loan-42") as run:
        graph.invoke(state, config={"callbacks": run.callbacks,
                                    "configurable": {"thread_id": "loan-42"}})
        # human-in-the-loop: when the reviewer approves and you resume the graph
        appr = run.record_human_approval(reviewer="alice@bank", rationale="reviewed KYC")
        run.record_decision(output="APPROVED", risk_classification="high",
                            approval_ref=appr.event_id, control="art-14-human-oversight")
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Dict, List

from langchain_core.callbacks import BaseCallbackHandler

from openwright.canonical import hash_payload
from openwright.connectors import CONTRACT_VERSION
from openwright.events import ComplianceEvent, EventKind

__all__ = ["LangGraphConnector", "OpenWrightCallbackHandler", "InstrumentedRun", "connector",
           "CONTRACT_VERSION", "auto_instrument", "InstrumentHandle"]


class OpenWrightCallbackHandler(BaseCallbackHandler):
    """Maps LangGraph/LangChain tool + LLM runtime events to ComplianceEvents.

    Tool/LLM payloads are hashed into ``sha256:`` references — the ledger never
    holds raw prompts/outputs (hashes-only invariant)."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self._tools: Dict[Any, str] = {}

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs):  # noqa: D401
        self._tools[run_id] = (serialized or {}).get("name") or "tool"

    def on_tool_end(self, output, *, run_id=None, **kwargs):
        name = self._tools.pop(run_id, "tool")
        self.client.record(ComplianceEvent(
            timestamp=self.client._clock(),
            kind=EventKind.TOOL_CALL,
            actor=self.client._actor(),
            provenance=self.client._provenance({}),
            tool={"name": name, "call_id": str(run_id) if run_id else None},
            io={"output_ref": hash_payload(str(output))},
            source={"format": "langgraph"},
        ))

    def on_llm_end(self, response, *, run_id=None, **kwargs):
        model = None
        try:
            model = (response.llm_output or {}).get("model_name")
        except Exception:  # noqa: BLE001
            pass
        self.client.record(ComplianceEvent(
            timestamp=self.client._clock(),
            kind=EventKind.LLM_CALL,
            actor=self.client._actor(),
            provenance=self.client._provenance({}),
            model={"response_model": model} if model else None,
            io={"output_ref": hash_payload(str(response))},
            source={"format": "langgraph"},
        ))


@dataclass
class InstrumentedRun:
    """Hands the caller the callbacks to attach + a thin recorder for the wedge
    controls (delegates to the SDK with the active task scope)."""

    callbacks: List[BaseCallbackHandler]
    client: Any

    def record_human_approval(self, **kw):
        return self.client.record_human_approval(**kw)

    def record_decision(self, **kw):
        return self.client.record_decision(**kw)

    def record_risk_classification(self, *args, **kw):
        return self.client.record_risk_classification(*args, **kw)


class LangGraphConnector:
    name = "langgraph"
    CONTRACT_VERSION = CONTRACT_VERSION

    @contextlib.contextmanager
    def instrument(self, client: Any, *, thread_id: str = "langgraph-task",
                   context_id: str = None, **opts: Any):
        """Context manager: sets the A2A task scope (thread_id) and yields an
        :class:`InstrumentedRun` with the callback handler to attach to the graph."""
        handler = OpenWrightCallbackHandler(client)
        with client.task(thread_id, context_id=context_id or thread_id, root_task_id=thread_id):
            yield InstrumentedRun(callbacks=[handler], client=client)


#: The object the ``openwright.source_connectors:langgraph`` entry point loads to.
connector = LangGraphConnector()


# ── one-import integration: `openwright.instrument("langgraph")` ──────────────
# LangChain has no global callback registry, so capture attaches via a callback
# handler you pass once to graph.invoke(config={"callbacks": handle.callbacks}).
# The runtime owns the ledger/key/checkpoint, so there's no setup to write.

class InstrumentHandle:
    """Returned by ``auto_instrument``: ``.callbacks`` to attach to the graph, plus
    ``record_*`` recorders and ``checkpoint()`` (delegates to the runtime)."""

    def __init__(self, runtime, thread_id, decision_tools, control):
        self.runtime = runtime
        self.client = runtime.client
        self.callbacks = [_DecisionAwareHandler(runtime.client, set(decision_tools), control)]
        self._scope = runtime.client.task(thread_id, context_id=thread_id, root_task_id=thread_id)
        self._scope.__enter__()

    def record_human_approval(self, **kw): return self.client.record_human_approval(**kw)
    def record_decision(self, **kw): return self.client.record_decision(**kw)
    def record_risk_classification(self, *a, **k): return self.client.record_risk_classification(*a, **k)
    def checkpoint(self): return self.runtime.checkpoint()


class _DecisionAwareHandler(OpenWrightCallbackHandler):
    """Tool/LLM capture + auto-records a decision when a configured decision tool ends."""

    def __init__(self, client, decision_tools, control):
        super().__init__(client)
        self._decision_tools = decision_tools
        self._control = control

    def on_tool_end(self, output, *, run_id=None, **kwargs):
        name = self._tools.get(run_id, "tool")
        super().on_tool_end(output, run_id=run_id, **kwargs)
        if name in self._decision_tools:
            self.client.record_decision(output=str(output), risk_classification="high",
                                        rationale="agent action (auto-captured)", control=self._control)


def auto_instrument(runtime, *, thread_id="langgraph", decision_tools=(),
                    control="art-14-human-oversight"):
    """Return an :class:`InstrumentHandle`; attach ``handle.callbacks`` to your graph
    run. The runtime supplies the ledger/key/checkpoint store, so there's no wiring."""
    return InstrumentHandle(runtime, thread_id, decision_tools, control)
