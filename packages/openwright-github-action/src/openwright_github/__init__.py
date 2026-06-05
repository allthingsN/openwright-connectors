"""GitHub-CI evidence-gate exporter for OpenWright (CONN-5): shift-left gating.

A :class:`ReportExporter` that gates a build on control results: it fails when a
required control isn't ``satisfied``, writes SARIF (for code-scanning), and — when
running inside GitHub Actions — appends a control table to the step summary. The
companion ``action.yml`` wraps ``openwright verify --deep`` + this exporter.

No crypto here: verification is core's ``openwright verify``; this only consumes a
report and gates/annotates.
"""

from __future__ import annotations

import json
import os

from openwright.connectors import CONTRACT_VERSION, ExportResult
from openwright.report import to_sarif

__all__ = ["GitHubActionExporter", "exporter", "CONTRACT_VERSION"]


class GitHubActionExporter:
    name = "github"
    CONTRACT_VERSION = CONTRACT_VERSION

    def export(self, report: dict, *, config: dict) -> ExportResult:
        statuses = {c["control_id"]: c["status"] for c in report.get("controls", [])}
        required = [r.strip() for r in str(config.get("require", "")).split(",") if r.strip()]
        required = required or list(statuses)  # default: every control must be satisfied
        failures = [cid for cid in required if statuses.get(cid) != "satisfied"]

        sarif_path = config.get("sarif")
        if sarif_path:
            with open(sarif_path, "w", encoding="utf-8") as fh:
                json.dump(to_sarif(report), fh, indent=2)

        # GitHub Actions step summary (a control table) + error annotations.
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write("### OpenWright evidence gate\n\n| Control | Status |\n|---|---|\n")
                for cid in sorted(statuses):
                    fh.write(f"| `{cid}` | {statuses[cid]} |\n")
        for cid in failures:
            print(f"::error title=OpenWright::required control {cid} is {statuses.get(cid, 'absent')}")

        ok = not failures
        detail = "all required controls satisfied" if ok else f"unsatisfied required control(s): {failures}"
        return ExportResult(ok=ok, detail=detail)


#: The object the ``openwright.report_exporters:github`` entry point loads to.
exporter = GitHubActionExporter()
