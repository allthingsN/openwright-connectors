# Flagship lending-agent example (EX-1)

A high-risk consumer-lending agent that **composes the connectors** end to end —
the proof the ecosystem works, and the design-partner onboarding path.

- **Capture** (CONN-1, LangGraph): a credit-check tool call is auto-captured; the
  wedge controls (human approval, credit decision) are recorded with task linkage.
- **Durable storage** (CONN-3, Postgres): set `OPENWRIGHT_PG_DSN` to use it; else a
  file ledger.
- **Evidence + offline verify**: a signed report is produced and verified with no
  network and no raw payloads (`--deep` re-derives the verdicts).
- **Observability** (CONN-2, Langfuse): set `LANGFUSE_*` to back-link
  `openwright:*` verdicts onto the trace.
- **CI gate** (CONN-5, GitHub Action): requiring Art-14 **fires** because applicant
  #2 was never human-approved — the gap an auditor cares about.

```bash
./run_local.sh
# or, after `pip install openwright openwright-langgraph openwright-langfuse openwright-postgres openwright-github-action`:
python lending_agent.py
```

Acceptance: one command → evidence verifies offline → (traces + verdicts in
Langfuse) → CI gate fires on the un-approved decision. Artifacts land in `out/`.

*OpenWright produces evidence that controls were exercised. It is not, and does not
claim to be, a legal compliance certification.*
