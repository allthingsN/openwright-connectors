"""Conformance + gating behavior for openwright-github-action."""

from __future__ import annotations

import json

from openwright_conformance import run_conformance
from openwright_github import exporter


def test_conforms():
    run_conformance(exporter, group="openwright.report_exporters", name="github", modules=["openwright_github"])


def _report():
    def ctrl(cid, status):
        return {
            "control_id": cid, "status": status, "title": cid, "requirement": "req",
            "reason": "because", "citation": {"instrument": "X", "url": "https://x"},
        }
    return {"controls": [ctrl("art-12", "satisfied"), ctrl("art-14", "not_satisfied")]}


def test_gate_fails_on_unsatisfied_required_control(tmp_path):
    sarif = tmp_path / "out.sarif.json"
    res = exporter.export(_report(), config={"require": "art-14", "sarif": str(sarif)})
    assert res.ok is False and "art-14" in res.detail
    # SARIF written + lists the failing control
    data = json.loads(sarif.read_text())
    assert data["version"] == "2.1.0"
    rule_ids = [r["id"] for r in data["runs"][0]["tool"]["driver"]["rules"]]
    assert "art-14" in rule_ids


def test_gate_passes_when_required_controls_satisfied():
    res = exporter.export(_report(), config={"require": "art-12"})
    assert res.ok is True and "satisfied" in res.detail
