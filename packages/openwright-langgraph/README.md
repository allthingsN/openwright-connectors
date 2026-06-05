# openwright-langgraph

A **LangGraph source connector** for
[OpenWright](https://github.com/allthingsN/openwright): capture a LangGraph
lending/underwriting agent's runtime behavior as signed, control-mapped evidence —
tool and model calls automatically, plus the wedge controls (**human-in-the-loop
approval** and the **credit decision**).

```python
from openwright.connectors import load
conn = load("openwright.source_connectors", "langgraph")

with conn.instrument(client, thread_id="loan-42") as run:
    graph.invoke(state, config={"callbacks": run.callbacks,
                                "configurable": {"thread_id": "loan-42"}})
    # when the reviewer approves and you resume the graph:
    appr = run.record_human_approval(reviewer="alice@bank", rationale="reviewed KYC")
    run.record_decision(output="APPROVED", risk_classification="high",
                        approval_ref=appr.event_id, control="art-14-human-oversight")
```

A human-approved high-risk decision yields **Art-14 satisfied**; an un-approved one
is flagged. Payloads are hashed (`sha256:` references) — no raw prompts/PII enter
the ledger. Built on LangChain's callback API + the OpenWright SDK; no crypto is
reimplemented. Not affiliated with LangChain/LangGraph.
