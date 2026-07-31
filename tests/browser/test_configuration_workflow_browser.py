"""Opt-in authenticated browser acceptance for the deployed CRS workstation.

Run only with an isolated test account and a non-production database. This file
does not contain credentials and is excluded from the default safe collection.
"""

import os

import pytest


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.getenv("CRS_BROWSER_BASE_URL"),
    reason="Set CRS_BROWSER_BASE_URL for target-workstation browser acceptance.",
)
def test_configuration_workflow_browser_acceptance():
    pytest.importorskip("playwright.sync_api")
    pytest.skip(
        "Use the controlled browser acceptance procedure in "
        "project_docs/configuration_ux_redesign/06_ACCESSIBILITY_REPORT.md; "
        "credentials must never be embedded in the repository."
    )

