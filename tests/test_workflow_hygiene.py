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
        assert "Checkout DeadZone-BuildExt launcher" in text
        assert "python3 scripts/send_telemetry.py" in text


def test_lite_workflow_uses_an_isolated_engine_and_verified_contract() -> None:
    text = (WORKFLOW_DIR / "lite.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    assert workflow["name"] == "DeadZone Lite Xiaomi Build"
    assert workflow["run-name"] == "DeadZone Lite  ${{ inputs.request_id }}"
    assert "^DZ-LT-[0-9]{8}-[0-9]{4}$" in text
    assert "path: toolbuild" in text
    assert "LITE_RCLONE_UPLOAD_DIR" in text
    assert "deadzone-result-${{ inputs.request_id }}" in text
    for stage in ("preparing", "loading_engine", "installing_tools", "building", "packaging", "preparing_upload", "uploading", "finalizing"):
        assert f"stage-key {stage}" in text


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


def test_workflows_persist_the_real_terminal_stage_context() -> None:
    for workflow_name in ("gamingplus.yml", "frameworkpatcher.yml"):
        text = (WORKFLOW_DIR / workflow_name).read_text(encoding="utf-8")
        assert "DZ_CURRENT_STAGE_KEY" in text
        assert "DZ_COMPLETED_STAGES" in text
        assert "DZ_STAGE_STARTED_AT" in text
        assert "BUILD_STARTED_AT" in text
        assert "--stage-key finalizing" in text
        assert "--stage-key \"$DZ_CURRENT_STAGE_KEY\"" in text
        assert "--completed-stages \"$DZ_COMPLETED_STAGES\"" in text
        assert "--stage-started-at \"$DZ_STAGE_STARTED_AT\"" in text

        failure_block = text.split("Telemetry - failure", 1)[1].split("Telemetry - cancelled", 1)[0]
        cancelled_block = text.split("Telemetry - cancelled", 1)[1]
        assert "--stage-key finalizing" not in failure_block
        assert "--stage-key finalizing" not in cancelled_block
        assert "--completed-stages 7" not in failure_block
        assert "--completed-stages 7" not in cancelled_block
        assert "--stage-key \"$DZ_CURRENT_STAGE_KEY\"" in failure_block
        assert "--stage-key \"$DZ_CURRENT_STAGE_KEY\"" in cancelled_block
        assert "--completed-stages \"$DZ_COMPLETED_STAGES\"" in failure_block
        assert "--completed-stages \"$DZ_COMPLETED_STAGES\"" in cancelled_block


def test_frameworkpatcher_upload_stage_is_explicit_and_forward_only() -> None:
    text = (WORKFLOW_DIR / "frameworkpatcher.yml").read_text(encoding="utf-8")
    assert "Telemetry - uploading" in text
    assert "stage-key uploading" in text
    assert "DZ_COMPLETED_STAGES=6" in text
    assert '--stage-started-at "$DZ_STAGE_STARTED_AT"' in text

    upload_block = text.split("Telemetry - uploading", 1)[1].split("Upload output to Google Drive", 1)[0]
    assert "--stage-key uploading" in upload_block
    assert "--completed-stages 6" in upload_block
    assert "--stage-key preparing_upload" not in upload_block
    assert "--completed-stages 5" not in upload_block
    assert "preparing_upload" not in (WORKFLOW_DIR / "frameworkpatcher.yml").read_text(encoding="utf-8").split("Upload output to Google Drive", 1)[1].split("Telemetry - finalizing start", 1)[0]


def test_rclone_helper_does_not_emit_preparing_upload() -> None:
    text = Path("scripts/rclone_telemetry.py").read_text(encoding="utf-8")
    assert "preparing_upload" not in text
