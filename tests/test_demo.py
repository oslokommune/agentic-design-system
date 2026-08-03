"""The demo page must render end to end from the committed spec."""

from __future__ import annotations

import json
import subprocess
import sys

from conftest import REPO_ROOT

DEMO_SCRIPT = REPO_ROOT / "demo" / "render_demo.py"


def test_demo_renders(tmp_path):
    result = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "overrides 1" in result.stdout

    html = (REPO_ROOT / "demo" / "out.html").read_text(encoding="utf-8")
    for marker in (
        "ds-button ds-button--primary ds-button--md",
        "ds-tag--success",
        "ds-alert--warning",
        'class="ds-alert__icon"',
        "ds-card__heading",
        "ds-card__actions",
        "ds-o-promo-banner-campaign-gradient",
        "tokens.css",
        "components.css",
    ):
        assert marker in html, marker

    report = json.loads((REPO_ROOT / "demo" / "build" / "overrides-report.json").read_text())
    assert report["count"] == 1
