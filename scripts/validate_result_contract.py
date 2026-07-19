#!/usr/bin/env python3
"""Validate and copy the single trusted DeadZone build result contract."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


COMMON_FIELDS = {
    "schema_version",
    "request_id",
    "project",
    "status",
    "provider",
    "url",
    "file_name",
    "size",
    "sha256",
    "completed_at",
}
PROJECT_FIELDS = {
    "gamingplus": {"os", "codename"},
    "lite": {"os", "codename"},
    "frameworkpatcher": {"android_version", "device_name", "rom_version", "features"},
}
REQUEST_PATTERNS = {
    "gamingplus": re.compile(r"^DZ-GP-[0-9]{8}-[0-9]{4}$"),
    "lite": re.compile(r"^DZ-LT-[0-9]{8}-[0-9]{4}$"),
    "frameworkpatcher": re.compile(r"^DZ-FP-[0-9]{8}-[0-9]{4}$"),
}
SAFE_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.zip$")
SAFE_METADATA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ ()+-]{0,127}$")
SAFE_CODENAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


class ContractError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _valid_google_url(value: object) -> bool:
    if not isinstance(value, str) or value != value.strip():
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"drive.google.com", "docs.google.com"}
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and bool(parsed.path and parsed.path != "/")
    )


def validate_contract(data: object, *, request_id: str, project: str) -> dict[str, object]:
    if project not in PROJECT_FIELDS:
        raise ContractError("unsupported registry project")
    if not isinstance(data, dict):
        raise ContractError("result contract must be a JSON object")
    expected_fields = COMMON_FIELDS | PROJECT_FIELDS[project]
    if set(data) != expected_fields:
        missing = sorted(expected_fields - set(data))
        extra = sorted(set(data) - expected_fields)
        raise ContractError(f"contract fields mismatch; missing={missing}, extra={extra}")
    if not REQUEST_PATTERNS[project].fullmatch(request_id) or data["request_id"] != request_id:
        raise ContractError("request_id does not match the workflow input")
    if data["schema_version"] != "1.0" or data["project"] != project:
        raise ContractError("schema version or project does not match")
    if data["status"] != "success" or data["provider"] != "google_drive":
        raise ContractError("only successful Google Drive delivery is trusted")
    if not _valid_google_url(data["url"]):
        raise ContractError("delivery URL is not an approved Google Drive URL")
    if not isinstance(data["file_name"], str) or not SAFE_FILE.fullmatch(data["file_name"]):
        raise ContractError("file_name is unsafe or is not a ZIP")
    if isinstance(data["size"], bool) or not isinstance(data["size"], int) or data["size"] <= 0:
        raise ContractError("size must be a positive integer")
    if not isinstance(data["sha256"], str) or not SHA256.fullmatch(data["sha256"]):
        raise ContractError("sha256 is invalid")
    if not isinstance(data["completed_at"], str):
        raise ContractError("completed_at is missing")
    try:
        completed_at = datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("completed_at is invalid") from exc
    if completed_at.tzinfo is None:
        raise ContractError("completed_at must include a timezone")

    if project in {"gamingplus", "lite"}:
        if not isinstance(data["os"], str) or not SAFE_METADATA.fullmatch(data["os"]):
            raise ContractError("OS metadata is invalid")
        if not isinstance(data["codename"], str) or not SAFE_CODENAME.fullmatch(data["codename"]):
            raise ContractError("codename metadata is invalid")
    else:
        for name in ("android_version", "device_name", "rom_version"):
            if not isinstance(data[name], str) or not SAFE_METADATA.fullmatch(data[name]):
                raise ContractError(f"{name} metadata is invalid")
        features = data["features"]
        if not isinstance(features, list) or len(features) > 16 or any(
            not isinstance(item, str) or not re.fullmatch(r"^[a-z0-9_]{1,64}$", item) for item in features
        ):
            raise ContractError("features metadata is invalid")
        if len(features) != len(set(features)):
            raise ContractError("features metadata contains duplicates")
    return data


def load_contract(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("result contract cannot be read as strict JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--project", required=True, choices=sorted(PROJECT_FIELDS))
    args = parser.parse_args(argv)
    try:
        contract = validate_contract(load_contract(args.input), request_id=args.request_id, project=args.project)
    except ContractError as exc:
        parser.error(str(exc))
    args.output.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
