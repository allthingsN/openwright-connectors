from openwright_conformance import run_conformance
from openwright_template import connector


def test_template_conforms():
    run_conformance(
        connector,
        group="openwright.report_exporters",
        name="template",
        modules=["openwright_template"],
    )
