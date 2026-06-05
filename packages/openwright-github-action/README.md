# openwright-github-action

A reusable **GitHub Action** + `ReportExporter` that turns an OpenWright evidence
pack into a CI gate: it verifies the report offline (`--deep`), **fails the build**
if a required control isn't satisfied, writes SARIF for code scanning, and adds a
control table to the run summary.

```yaml
# .github/workflows/evidence-gate.yml
- uses: allthingsN/openwright-connectors/packages/openwright-github-action@main
  with:
    report: out/report.json
    pubkey: out/public_key.pem
    require: art-14-human-oversight,art-12-record-keeping
```

Or locally via the exporter:

```bash
openwright export out/report.json --to github -c require=art-14-human-oversight -c sarif=out.sarif.json
```

Verification is core's `openwright verify`; this package only gates + annotates.
