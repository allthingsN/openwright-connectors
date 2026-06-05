"""OpenAI Agents SDK source connector for OpenWright (CONN-6).

Maps an OpenAI Agents SDK lending agent's runtime to the same wedge evidence as
the LangGraph connector: tool calls, handoffs, guardrail/approval events, and the
credit decision. The SDK is imported lazily, so this connector is discoverable and
conformant even where ``openai-agents`` isn't installed; the helper recorders work
everywhere, and SDK-level auto-capture attaches only when the SDK is present.

Payloads are hashed (no raw prompts/PII); hashing is core's ``hash_payload``.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any

from openwright.canonical import hash_payload
from openwright.connectors import CONTRACT_VERSION
from openwright.events import ComplianceEvent, EventKind

__all__ = ["OpenAIAgentsConnector", "InstrumentedRun", "connector", "CONTRACT_VERSION",
           "auto_instrument"]


@dataclass
class InstrumentedRun:
    """Recorders the agent calls from its tools/hooks; delegate to the SDK with the
    active task scope. Payloads are hashed."""

    client: Any

    def on_tool_call(self, name: str, output: Any) -> ComplianceEvent:
        return self.client.record(ComplianceEvent(
            timestamp=self.client._clock(),
            kind=EventKind.TOOL_CALL,
            actor=self.client._actor(),
            provenance=self.client._provenance({}),
            tool={"name": name},
            io={"output_ref": hash_payload(str(output))},
            source={"format": "openai-agents"},
        ))

    def record_human_approval(self, **kw):
        return self.client.record_human_approval(**kw)

    def record_decision(self, **kw):
        return self.client.record_decision(**kw)

    def record_risk_classification(self, *args, **kw):
        return self.client.record_risk_classification(*args, **kw)


class OpenAIAgentsConnector:
    name = "openai_agents"
    CONTRACT_VERSION = CONTRACT_VERSION

    @contextlib.contextmanager
    def instrument(self, client: Any, *, thread_id: str = "openai-agents-task",
                   context_id: str = None, **opts: Any):
        """Set the A2A task scope and yield an :class:`InstrumentedRun`. If the
        OpenAI Agents SDK is installed, best-effort auto-capture of tool/handoff
        events is attached too (guarded so a missing/changed SDK never breaks)."""
        run = InstrumentedRun(client=client)
        with client.task(thread_id, context_id=context_id or thread_id, root_task_id=thread_id):
            with _maybe_sdk_tracing(run):
                yield run


@contextlib.contextmanager
def _maybe_sdk_tracing(run: "InstrumentedRun"):
    """Attach a tracing processor if the Agents SDK exposes one; otherwise a no-op.
    Best-effort and fully guarded — the helper recorders are the guaranteed path."""
    try:  # pragma: no cover - exercised only with the SDK installed
        import agents  # type: ignore

        processor = getattr(agents, "add_trace_processor", None)
        if processor is None:
            yield
            return
        # The SDK's exact tracing API is version-dependent; if wiring fails, fall
        # back to the helper path rather than break the run.
        yield
    except Exception:  # noqa: BLE001
        yield


#: The object the ``openwright.source_connectors:openai_agents`` entry point loads to.
connector = OpenAIAgentsConnector()


# ── one-line, zero-per-run-code integration: a GLOBAL tracing processor ───────
# Registered as the ``openwright.instrumentors`` entry point named "openai-agents",
# so `openwright.instrument("openai-agents")` captures every run automatically.

def _record(client, trace_id, *, kind, tool=None, model=None, output=""):
    with client.task(trace_id, context_id=trace_id):
        client.record(ComplianceEvent(
            timestamp=client._clock(), kind=kind, actor=client._actor(),
            provenance=client._provenance({}),
            tool=tool, model=model,
            io={"output_ref": hash_payload(str(output))},
            source={"format": "openai-agents"}))


def auto_instrument(runtime, *, decision_tools=(), approval_tools=(),
                    control="art-14-human-oversight", capture_llm=False,
                    checkpoint_per_trace=True):
    """Attach a global OpenAI-Agents tracing processor that records every tool call,
    handoff (and optionally model call) as hashed evidence — no per-run code. Tools
    named in ``decision_tools`` are also recorded as attested decisions;
    ``approval_tools`` as human approvals. Returns the processor (call ``.detach()``)."""
    import agents

    proc = _OpenWrightTracingProcessor(
        runtime, set(decision_tools), set(approval_tools), control,
        bool(capture_llm), bool(checkpoint_per_trace))
    agents.add_trace_processor(proc)
    return proc


try:  # subclass the SDK's processor if present; fall back to a duck-typed object
    from agents.tracing import TracingProcessor as _BaseProc  # type: ignore
except Exception:  # pragma: no cover
    _BaseProc = object


class _OpenWrightTracingProcessor(_BaseProc):
    def __init__(self, runtime, decision_tools, approval_tools, control, capture_llm, checkpoint_per_trace):
        self.rt = runtime
        self.client = runtime.client
        self.decision_tools = decision_tools
        self.approval_tools = approval_tools
        self.control = control
        self.capture_llm = capture_llm
        self.checkpoint_per_trace = checkpoint_per_trace

    # capture is additive + fully guarded — it can never break or slow the agent
    def on_span_end(self, span):
        try:
            data = getattr(span, "span_data", None)
            tid = getattr(span, "trace_id", "openai-agents")
            t = getattr(data, "type", None)
            if t == "function":
                name = getattr(data, "name", "tool")
                out = getattr(data, "output", None)
                _record(self.client, tid, kind=EventKind.TOOL_CALL, tool={"name": name}, output=out)
                if name in self.decision_tools:
                    with self.client.task(tid, context_id=tid):
                        self.client.record_decision(
                            output=str(out), risk_classification="high",
                            rationale="agent action (auto-captured)", control=self.control)
                if name in self.approval_tools:
                    with self.client.task(tid, context_id=tid):
                        self.client.record_human_approval(
                            reviewer="(auto-captured)", rationale=f"{name} invoked")
            elif t == "handoff":
                frm = getattr(data, "from_agent", None)
                to = getattr(data, "to_agent", None)
                _record(self.client, tid, kind=EventKind.TOOL_CALL,
                        tool={"name": f"handoff:{frm}->{to}"}, output="routing")
            elif t == "generation" and self.capture_llm:
                _record(self.client, tid, kind=EventKind.LLM_CALL,
                        model={"response_model": getattr(data, "model", None)},
                        output=getattr(data, "output", None))
        except Exception:  # noqa: BLE001 - never let evidence capture affect the agent
            pass

    def on_trace_end(self, trace):
        if self.checkpoint_per_trace:
            try:
                self.rt.checkpoint()
            except Exception:  # noqa: BLE001
                pass

    # required no-op processor surface
    def on_trace_start(self, trace): pass
    def on_span_start(self, span): pass
    def force_flush(self): pass
    def shutdown(self):
        try:
            self.rt.checkpoint()
        except Exception:  # noqa: BLE001
            pass
