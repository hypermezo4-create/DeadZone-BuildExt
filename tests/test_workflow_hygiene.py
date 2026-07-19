from __future__ import annotations

from pathlib import Path
import re

import yaml


WORKFLOW_DIR = Path(".github/workflows")
PRODUCTION = ("gamingplus.yml", "lite.yml", "frameworkpatcher.yml")
PINNED_ACTION = re.compile(r"uses:\s+[^\s@]+@[a-f0-9]{40}\s*$")


def _text(name: str) -> str:
    return (WORKFLOW_DIR / name).read_text(encoding="utf-8")


def test_workflows_parse_and_actions_are_immutable() -> None:
    for workflow in WORKFLOW_DIR.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        assert isinstance(parsed, dict) and parsed.get("name")
        for line in text.splitlines():
            if "uses:" in line:
                assert PINNED_ACTION.search(line), f"mutable action reference in {workflow.name}: {line}"


def test_production_workflows_keep_manual_dispatch_and_hardening() -> None:
    for name in PRODUCTION:
        text = _text(name)
        parsed = yaml.safe_load(text)
        job = parsed["jobs"]["build"]
        assert "workflow_dispatch:" in text
        assert parsed["permissions"] == {"contents": "read"}
        assert parsed["concurrency"]["cancel-in-progress"] is False
        assert int(job["timeout-minutes"]) > 0
        assert "persist-credentials: false" in text
        assert "Remove temporary secrets" in text
        assert "deadzone-result-${{ inputs.request_id }}" in text
        assert "retention-days: 1" in text
        assert "provider\": \"google_drive" in text or "validate_result_contract.py" in text


def test_job_environment_contains_no_github_secrets() -> None:
    for name in PRODUCTION:
        parsed = yaml.safe_load(_text(name))
        env = parsed["jobs"]["build"].get("env", {})
        assert all("secrets." not in str(value) for value in env.values())


def test_gamingplus_and_lite_use_pinned_engines_and_secure_contract() -> None:
    expected = {
        "gamingplus.yml": ("8f2ca0bf55202f13a8a455e4ec8574806099f38a", "gamingplus", "DZ-GP"),
        "lite.yml": ("b0d02fb3a69e52d330f6ec525b786097d4342c1f", "lite", "DZ-LT"),
    }
    for name, (sha, project, prefix) in expected.items():
        text = _text(name)
        assert f"ref: {sha}" in text
        assert f"^{prefix}-[0-9]{{8}}-[0-9]{{4}}$" in text
        assert "python3 scripts/validate_rom_url.py \"$INPUT_URL\"" in text
        assert f"--project {project}" in text
        assert "verified-rom-input" in text
        assert "sudo -E bash" not in text and "sudo bash" not in text
        for stage in ("preparing", "loading_engine", "installing_tools", "building", "packaging", "preparing_upload", "uploading", "finalizing"):
            assert f"emit_stage.sh {stage} " in text


def test_no_pixeldrain_or_mutable_engine_refs() -> None:
    joined = "\n".join(_text(name).lower() for name in PRODUCTION)
    assert "pixeldrain" not in joined
    assert "ref: main" not in joined
    assert "@v4" not in joined and "@master" not in joined and "@main" not in joined


def test_every_tee_pipeline_is_fail_closed() -> None:
    for name in PRODUCTION:
        text = _text(name)
        for block in text.split("- name:")[1:]:
            if "| tee" in block:
                assert "set -Eeuo pipefail" in block or "set -euo pipefail" in block, f"tee without pipefail in {name}"


def test_frameworkpatcher_preserves_features_and_verifies_drive() -> None:
    text = _text("frameworkpatcher.yml")
    for feature in ("disable_signature_verification", "cn_notification_fix", "disable_secure_flag", "kaorios_toolbox", "add_gboard"):
        assert feature in text
    assert "71ffca6fd8cafea71e19d3181c2da3e8f44c35fb" in text
    assert "64cf3b19eeeba6685185bf11260b2728ad26f9e3" in text
    assert "python3 ../scripts/rclone_telemetry.py" in text
    assert "rclone --config \"$config_path\" size \"$remote_path\" --json" in text
    assert "Remote checksum verification failed" in text
    assert "--project frameworkpatcher" in text
    failure = text.split("Telemetry - failure", 1)[1].split("Telemetry - cancelled", 1)[0]
    cancelled = text.split("Telemetry - cancelled", 1)[1]
    assert "../scripts/send_telemetry.py" not in failure
    assert "../scripts/send_telemetry.py" not in cancelled


def test_rclone_helper_is_immutable_and_keeps_upload_stage() -> None:
    text = Path("scripts/rclone_telemetry.py").read_text(encoding="utf-8")
    assert '"--immutable"' in text
    assert "preparing_upload" not in text
