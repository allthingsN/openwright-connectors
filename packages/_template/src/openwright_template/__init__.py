"""Template OpenWright connector — copy to start a new one.

Replace this with your connector. Pick the contract you implement
(SourceConnector / Forwarder / ReportExporter / a storage backend factory),
declare the matching entry point in pyproject, and keep the invariants:
hashes-only, no crypto re-implementation (call ``openwright``), append-only,
boundary statement in emitted artifacts, additive evidence path.
"""

from __future__ import annotations

from openwright.connectors import CONTRACT_VERSION, ExportResult

# Declare the contract version you target so core can warn on a major mismatch.
__all__ = ["Connector", "connector", "CONTRACT_VERSION"]


class Connector:
    """A no-op ReportExporter, just enough to pass conformance. Replace me."""

    name = "template"
    CONTRACT_VERSION = CONTRACT_VERSION

    def export(self, report: dict, *, config: dict) -> ExportResult:
        return ExportResult(ok=True, detail="template connector did nothing (replace me)")


#: The object the entry point loads to.
connector = Connector()
