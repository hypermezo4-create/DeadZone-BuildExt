from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.validate_result_contract import ContractError, load_contract, validate_contract


BASE = {
    "schema_version": "1.0",
    "request_id": "DZ-GP-20260719-0001",
    "project": "gamingplus",
    "status": "success",
    "provider": "google_drive",
    "url": "https://drive.google.com/file/d/abc/view",
    "file_name": "DeadZone_GamingPlus.zip",
    "size": 42,
    "sha256": "a" * 64,
    "completed_at": "2026-07-19T10:00:00+00:00",
    "os": "HyperOS",
    "codename": "garnet",
}


def test_accepts_exact_google_drive_contract() -> None:
    assert validate_contract(BASE, request_id=BASE["request_id"], project="gamingplus") == BASE


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "pixeldrain"),
        ("url", "https://example.com/file.zip"),
        ("file_name", "../rom.zip"),
        ("size", 0),
        ("sha256", "A" * 64),
        ("completed_at", "yesterday"),
    ],
)
def test_rejects_untrusted_values(field: str, value: object) -> None:
    data = deepcopy(BASE)
    data[field] = value
    with pytest.raises(ContractError):
        validate_contract(data, request_id=BASE["request_id"], project="gamingplus")


def test_rejects_mismatched_request_and_extra_fields() -> None:
    with pytest.raises(ContractError):
        validate_contract(BASE, request_id="DZ-GP-20260719-9999", project="gamingplus")
    data = deepcopy(BASE)
    data["token"] = "unexpected"
    with pytest.raises(ContractError):
        validate_contract(data, request_id=BASE["request_id"], project="gamingplus")


def test_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text('{"status":"success","status":"failure"}', encoding="utf-8")
    with pytest.raises(ContractError):
        load_contract(path)
