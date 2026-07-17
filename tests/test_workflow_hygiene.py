from __future__ import annotations

from pathlib import Path

import yaml


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


def test_workflows_parse_and_keep_signed_telemetry() -> None:
    gamingplus = (WORKFLOW_DIR / "gamingplus.yml").read_text(encoding="utf-8")
    frameworkpatcher = (WORKFLOW_DIR / "frameworkpatcher.yml").read_text(encoding="utf-8")
    assert yaml.safe_load(gamingplus)["name"] == "DeadZone GamingPlus Xiaomi Build"
    assert yaml.safe_load(frameworkpatcher)["name"] == "DeadZone FrameworkPatcher Build"
    for text in (gamingplus, frameworkpatcher):
        assert "BUILD_PROGRESS_SECRET" in text
        assert "CONTROL_BOT_TELEMETRY_URL" in text
        assert "python3 ../scripts/send_telemetry.py" in text


def test_frameworkpatcher_workflow_keeps_rom_version_and_rclone_telemetry() -> None:
    text = (WORKFLOW_DIR / "frameworkpatcher.yml").read_text(encoding="utf-8")
    engine_block = text.split("Run hardened FrameworkPatcher engine", 1)[1].split(
        "Reject false success and verify module contents", 1
    )[0]
    assert "rom_version:" in text
    assert "config[\"rom_version\"]" in engine_block
    assert "config[\"request_id\"]" not in engine_block
    assert "python3 ../scripts/rclone_telemetry.py" in text
    assert "rclone copyto" not in text
