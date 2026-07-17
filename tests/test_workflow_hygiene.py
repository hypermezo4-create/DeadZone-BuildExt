from __future__ import annotations

from pathlib import Path


WORKFLOW_DIR = Path(".github/workflows")


def test_no_unsafe_global_pip_install_usage() -> None:
    for workflow in WORKFLOW_DIR.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "pip install --user" not in text
        assert "python3 -m pip install --disable-pip-version-check" not in text
        for line in text.splitlines():
            if "pip install" not in line:
                continue
            assert "python3 -m venv" in text, f"{workflow.name} uses pip install without a venv"
            assert ".venv/bin" in text, f"{workflow.name} does not publish the virtualenv to PATH"
