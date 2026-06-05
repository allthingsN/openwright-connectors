# openwright-openai-agents

An **OpenAI Agents SDK source connector** for
[OpenWright](https://github.com/allthingsN/openwright): capture an Agents-SDK
lending agent's runtime (tools, handoffs, guardrail/approval events, the credit
decision) as the same wedge evidence the LangGraph connector produces.

```python
from openwright.connectors import load
conn = load("openwright.source_connectors", "openai_agents")
with conn.instrument(client, thread_id="loan-42") as run:
    # from your tools / hooks:
    run.on_tool_call("credit_check", result)
    appr = run.record_human_approval(reviewer="alice@bank", rationale="reviewed")
    run.record_decision(output="APPROVED", risk_classification="high",
                        approval_ref=appr.event_id, control="art-14-human-oversight")
```

The helper recorders work without the SDK installed; SDK-level auto-capture
attaches (best-effort) when `openai-agents` is present. Payloads are hashed; no
crypto is reimplemented. Not affiliated with OpenAI.
