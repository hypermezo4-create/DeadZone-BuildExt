#!/usr/bin/env bash
set -Eeuo pipefail

stage_key="${1:?stage key is required}"
stage_state="${2:?stage state is required}"
completed_stages="${3:?completed stage count is required}"
message="${4:-}"

if [[ "$stage_state" == "in_progress" ]]; then
  stage_started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    printf 'DZ_CURRENT_STAGE_KEY=%s\n' "$stage_key"
    printf 'DZ_COMPLETED_STAGES=%s\n' "$completed_stages"
    printf 'DZ_STAGE_STARTED_AT=%s\n' "$stage_started_at"
  } >> "$GITHUB_ENV"
else
  stage_started_at="${DZ_STAGE_STARTED_AT:-${BUILD_STARTED_AT:-}}"
fi

python3 scripts/send_telemetry.py \
  --request-id "${REQUEST_ID:?request ID is required}" \
  --stage-key "$stage_key" \
  --stage-state "$stage_state" \
  --completed-stages "$completed_stages" \
  --total-stages 8 \
  --build-started-at "${BUILD_STARTED_AT:-}" \
  --stage-started-at "$stage_started_at" \
  --message "$message" || printf '%s\n' 'Telemetry delivery failed; build result is unchanged.' >&2
