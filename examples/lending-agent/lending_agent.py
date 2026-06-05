"""Flagship lending-agent example (EX-1): the ecosystem, end to end.

A high-risk consumer-lending agent, captured with the **LangGraph** source
connector, written to a durable ledger (file by default; **Postgres** if
``OPENWRIGHT_PG_DSN`` is set — CONN-3), turned into a signed evidence pack and
verified offline, with the **GitHub-Action** exporter run as a local CI gate
(CONN-5) and — if ``LANGFUSE_*`` env is set — the ``openwright:*`` verdicts
back-linked to the trace via the **Langfuse** forwarder (CONN-2).

Two applicants: #1 is human-approved (Art-14 satisfied for it); #2 is NOT approved
(the gap an auditor cares about), so the CI gate fires.

Run:  python lending_agent.py   (or ./run_local.sh)
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path

from langchain_core.tools import tool

from openwright.connectors import load, resolve_backend
from openwright.crosswalk import evaluate
from openwright.crosswalk_loader import load_builtin
from openwright.ledger import FileLedgerBackend, Ledger
from openwright.report import build_report
from openwright.sdk import EvidenceClient
from openwright.signing import FileKeySource, generate_private_key_pem, public_key_pem
from openwright.verify import verify_report

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


@tool
def credit_check(applicant: str) -> str:
    """Look up an applicant's credit score (stand-in)."""
    return {"alice": "score 742", "bob": "score 588"}.get(applicant, "score 700")


def main() -> int:
    # --- durable storage: Postgres connector if configured, else file ledger ---
    pg = os.environ.get("OPENWRIGHT_PG_DSN")
    if pg:
        backend = resolve_backend("openwright.ledger_backends", pg)
        print(f"[storage] Postgres ledger via openwright-postgres ({pg.split('@')[-1]})")
    else:
        backend = FileLedgerBackend(str(OUT / "ledger"))
        print("[storage] file ledger (set OPENWRIGHT_PG_DSN to use the Postgres connector)")
    ledger = Ledger(backend, origin="openwright/lending-agent", retention=timedelta(days=200))

    key_path = OUT / "signing_key.pem"
    key_path.write_bytes(generate_private_key_pem())
    key = FileKeySource(str(key_path))
    (OUT / "public_key.pem").write_bytes(public_key_pem(key.public_key_raw()))

    client = EvidenceClient(ledger, agent_id="lending-agent")
    langgraph = load("openwright.source_connectors", "langgraph")

    # --- applicant #1: reviewed + approved (Art-14 satisfied for this decision) ---
    with langgraph.instrument(client, thread_id="loan-alice") as run:
        credit_check.invoke({"applicant": "alice"}, config={"callbacks": run.callbacks})
        run.record_risk_classification("high", rationale="consumer credit decision")
        appr = run.record_human_approval(reviewer="reviewer@bank", rationale="reviewed KYC + income")
        run.record_decision(output="APPROVED at 6.2% APR", risk_classification="high",
                            rationale="score above threshold", approval_ref=appr.event_id,
                            control="art-14-human-oversight")

    # --- applicant #2: NO human approval (the gap) ---
    with langgraph.instrument(client, thread_id="loan-bob") as run:
        credit_check.invoke({"applicant": "bob"}, config={"callbacks": run.callbacks})
        run.record_risk_classification("high", rationale="consumer credit decision")
        run.record_decision(output="DENIED", risk_classification="high",
                            rationale="auto-denied below threshold", control="art-14-human-oversight")

    # --- signed evidence pack + offline verification ---
    result = evaluate(load_builtin("eu-ai-act"), list(ledger.events()))
    report = build_report(ledger, result, key, scope_description="High-risk consumer lending agent")
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    vr = verify_report(report, trusted_public_key_raw=key.public_key_raw())
    print(f"[verify] offline VALID={vr.valid}; "
          f"Art-14={next(c['status'] for c in report['controls'] if c['control_id']=='art-14-human-oversight')}")

    # --- optional: back-link openwright:* verdicts into Langfuse (CONN-2) ---
    if os.environ.get("LANGFUSE_HOST") and os.environ.get("LANGFUSE_PUBLIC_KEY"):
        fwd = load("openwright.forwarders", "langfuse")
        res = fwd.backlink(report, config={
            "host": os.environ["LANGFUSE_HOST"],
            "public_key": os.environ["LANGFUSE_PUBLIC_KEY"],
            "secret_key": os.environ.get("LANGFUSE_SECRET_KEY", ""),
            "trace_id": os.environ.get("LANGFUSE_TRACE_ID"),
        })
        print(f"[langfuse] {res.detail}{(' ' + res.url) if res.url else ''}")

    # --- CI gate (CONN-5): require Art-14 — fires because #2 was not approved ---
    gate = load("openwright.report_exporters", "github")
    gated = gate.export(report, config={"require": "art-14-human-oversight",
                                        "sarif": str(OUT / "report.sarif.json")})
    print(f"[ci-gate] require art-14-human-oversight -> {'PASS' if gated.ok else 'FAIL'} ({gated.detail})")
    print(f"[artifacts] {OUT}/report.json, public_key.pem, report.sarif.json")

    # Verify-it-yourself: openwright verify out/report.json --pubkey out/public_key.pem --deep
    return 0 if (vr.valid and not gated.ok) else 1  # demo expects the gate to fire


if __name__ == "__main__":
    raise SystemExit(main())
