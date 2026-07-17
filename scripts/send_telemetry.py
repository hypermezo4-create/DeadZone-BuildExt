from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import urllib.request
from datetime import datetime, timezone


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--stage-key", required=True)
    parser.add_argument("--stage-state", required=True)
    parser.add_argument("--completed-stages", required=True)
    parser.add_argument("--total-stages", required=True)
    parser.add_argument("--message", default="")
    parser.add_argument("--processed-bytes")
    parser.add_argument("--total-bytes")
    parser.add_argument("--bytes-per-second")
    parser.add_argument("--eta-seconds")
    parser.add_argument("--artifact-size")
    parser.add_argument("--build-started-at")
    parser.add_argument("--stage-started-at")
    parser.add_argument(
        "--telemetry-url",
        default=os.environ.get("CONTROL_BOT_TELEMETRY_URL", "https://deadzonebot.fly.dev/telemetry"),
    )
    args = parser.parse_args(argv)

    secret = str(os.environ.get("BUILD_PROGRESS_SECRET", "")).strip()
    if not secret:
        return 0

    payload = {
        "schema_version": "1.0",
        "request_id": args.request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage_key": args.stage_key,
        "stage_state": args.stage_state,
        "completed_stages": int(args.completed_stages),
        "total_stages": int(args.total_stages),
        "processed_bytes": _positive_int(args.processed_bytes),
        "total_bytes": _positive_int(args.total_bytes),
        "bytes_per_second": _optional_float(args.bytes_per_second),
        "eta_seconds": _positive_int(args.eta_seconds),
        "artifact_size": _positive_int(args.artifact_size),
        "message": args.message or None,
        "build_started_at": args.build_started_at or None,
        "stage_started_at": args.stage_started_at or None,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        args.telemetry_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-DeadZone-Signature": signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
