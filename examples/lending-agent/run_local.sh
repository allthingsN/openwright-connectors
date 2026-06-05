#!/usr/bin/env bash
# Flagship lending-agent demo (EX-1): capture → evidence → verify → (Langfuse) → CI gate.
#
#   ./run_local.sh
#
# Installs the core + the connectors it composes, then runs the agent end to end.
# Optional: set OPENWRIGHT_PG_DSN to use the Postgres ledger connector, and
# LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_TRACE_ID to
# back-link verdicts into Langfuse.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

PY="${PYTHON:-python3}"
"$PY" -m pip install --quiet --upgrade pip
# Core (the contract floor) + the connectors this example composes.
"$PY" -m pip install --quiet "openwright-core>=0.6,<0.7"
"$PY" -m pip install --quiet "$ROOT/packages/openwright-langgraph" \
                              "$ROOT/packages/openwright-langfuse" \
                              "$ROOT/packages/openwright-postgres" \
                              "$ROOT/packages/openwright-github-action"

echo "== installed connectors =="
openwright connectors list || true
echo "== run the lending agent =="
"$PY" "$HERE/lending_agent.py"
echo "== verify the evidence pack yourself, offline =="
openwright verify "$HERE/out/report.json" --pubkey "$HERE/out/public_key.pem" --deep
