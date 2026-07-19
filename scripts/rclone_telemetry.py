from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SIZE_RE = re.compile(r"(?P<value>[0-9.]+)\s*(?P<unit>B|KiB|MiB|GiB|TiB|KB|MB|GB|TB)")
ETA_RE = re.compile(r"ETA\s+(?P<value>.+)$")
TRANSFERRED_RE = re.compile(
    r"Transferred:\s+(?P<processed>[^/]+)/\s+(?P<total>[^,]+),\s+(?P<percent>\d+)%.*?(?:,\s+(?P<speed>[^,]+?))?(?:,\s+ETA\s+(?P<eta>.+))?$"
)


def _positive_int(value: str | None) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return max(int(float(raw)), 0)


def _optional_float(value: str | None) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return float(raw)


def _parse_size(value: str | None) -> int | None:
    if not value:
        return None
    match = SIZE_RE.search(value.replace(",", " "))
    if not match:
        return None
    amount = float(match.group("value"))
    unit = match.group("unit")
    factor = {
        "B": 1,
        "KB": 1000**1,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "KiB": 1024**1,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
    }.get(unit)
    if not factor:
        return None
    return int(amount * factor)


def _parse_eta(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    if text.lower() in {"unknown", "calculating", "n/a"}:
        return None
    seconds = 0
    m = re.fullmatch(r"(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?", text.replace(" ", ""))
    if not m:
        return None
    if m.group("h"):
        seconds += int(m.group("h")) * 3600
    if m.group("m"):
        seconds += int(m.group("m")) * 60
    if m.group("s"):
        seconds += int(m.group("s"))
    return seconds


def _send_update(*, request_id: str, stage_key: str, stage_state: str, completed_stages: int, total_stages: int, message: str | None = None, processed_bytes: int | None = None, total_bytes: int | None = None, bytes_per_second: float | None = None, eta_seconds: int | None = None, artifact_size: int | None = None, build_started_at: str | None = None, stage_started_at: str | None = None) -> None:
    secret = str(os.environ.get("BUILD_PROGRESS_SECRET", "")).strip()
    if not secret:
        return
    payload = {
        "schema_version": "1.0",
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage_key": stage_key,
        "stage_state": stage_state,
        "completed_stages": completed_stages,
        "total_stages": total_stages,
        "processed_bytes": processed_bytes,
        "total_bytes": total_bytes,
        "bytes_per_second": bytes_per_second,
        "eta_seconds": eta_seconds,
        "artifact_size": artifact_size,
        "message": message,
        "build_started_at": build_started_at,
        "stage_started_at": stage_started_at,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        os.environ.get("CONTROL_BOT_TELEMETRY_URL", "https://deadzonebot.fly.dev/telemetry"),
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-DeadZone-Signature": signature},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
    except Exception:
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--build-started-at")
    parser.add_argument("--stage-started-at")
    parser.add_argument("--stage-key", default="uploading")
    parser.add_argument("--completed-stages", type=int, default=0)
    parser.add_argument("--total-stages", type=int, default=0)
    args = parser.parse_args(argv)

    artifact_size = Path(args.source).stat().st_size

    command = [
        "rclone",
        "copyto",
        args.source,
        args.destination,
        "--config",
        args.config,
        "--checkers",
        "4",
        "--transfers",
        "1",
        "--immutable",
        "--stats",
        "10s",
        "--stats-one-line",
        "--stats-log-level",
        "NOTICE",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    last_emit = 0.0
    last_percent = -1
    last_stats = {
        "processed_bytes": 0,
        "bytes_per_second": None,
        "eta_seconds": None,
    }
    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(line)
        match = TRANSFERRED_RE.search(line)
        if not match:
            continue
        processed = _parse_size(match.group("processed"))
        total = _parse_size(match.group("total")) or artifact_size
        percent = int(match.group("percent"))
        speed = _parse_size(match.group("speed"))
        eta = _parse_eta(match.group("eta"))
        now = time.monotonic()
        if processed is not None:
            last_stats["processed_bytes"] = processed
        if speed is not None:
            last_stats["bytes_per_second"] = float(speed)
        if eta is not None:
            last_stats["eta_seconds"] = eta
        if now - last_emit >= 10 or percent != last_percent:
            last_emit = now
            last_percent = percent
            _send_update(
                request_id=args.request_id,
                stage_key=args.stage_key,
                stage_state="in_progress",
                completed_stages=args.completed_stages,
                total_stages=args.total_stages,
                message="Uploading to Google Drive.",
                processed_bytes=last_stats["processed_bytes"],
                total_bytes=total,
                bytes_per_second=last_stats["bytes_per_second"],
                eta_seconds=last_stats["eta_seconds"],
                artifact_size=artifact_size,
                build_started_at=args.build_started_at,
                stage_started_at=args.stage_started_at,
            )

    return_code = process.wait()
    if return_code == 0:
        _send_update(
            request_id=args.request_id,
            stage_key=args.stage_key,
            stage_state="success",
            completed_stages=args.completed_stages,
            total_stages=args.total_stages,
            message="Google Drive upload completed.",
            processed_bytes=artifact_size,
            total_bytes=artifact_size,
            bytes_per_second=last_stats["bytes_per_second"],
            eta_seconds=0,
            artifact_size=artifact_size,
            build_started_at=args.build_started_at,
            stage_started_at=args.stage_started_at,
        )
    else:
        _send_update(
            request_id=args.request_id,
            stage_key=args.stage_key,
            stage_state="failed",
            completed_stages=args.completed_stages,
            total_stages=args.total_stages,
            message="The Google Drive upload failed.",
            processed_bytes=last_stats["processed_bytes"],
            total_bytes=artifact_size,
            bytes_per_second=last_stats["bytes_per_second"],
            eta_seconds=last_stats["eta_seconds"],
            artifact_size=artifact_size,
            build_started_at=args.build_started_at,
            stage_started_at=args.stage_started_at,
        )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
