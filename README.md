# DeadZone BuildExt

`DeadZone-BuildExt` is the GitHub Actions launcher repository used by DeadZone Control Bot V2. The launcher remains responsible for dispatching the real GamingPlus build against the private engine repository while preserving the existing build, pack, upload, and notification behavior.

## GamingPlus Dispatch Contract

`gamingplus.yml` now accepts these `workflow_dispatch` inputs:

- `request_id` (required): exact control-plane identifier in the form `DZ-GP-YYYYMMDD-NNNN`
- `input_url` (required): ROM source URL
- `builder_name` (optional): builder display name
- `builder_id` (optional): preserved for backward compatibility with existing manual or legacy launch paths

The workflow run name contract is:

`DeadZone GamingPlus  <request_id>`

This deterministic run name is how DeadZone Control Bot V2 correlates a dispatch to the exact GitHub Actions run without relying on time-only matching.

## Manual Dispatch Example

Manual dispatch from the GitHub UI remains supported. Supply:

- `request_id`: `DZ-GP-20260716-0001`
- `input_url`: `https://example.com/rom.zip`
- `builder_name`: `manual`

The workflow validates `request_id` before checking out the private GamingPlus engine repository.

## Relationship To DeadZone Control Bot

The control bot dispatches:

```json
{
  "ref": "main",
  "inputs": {
    "request_id": "DZ-GP-20260716-0001",
    "input_url": "https://example.com/rom.zip",
    "builder_name": "mezo"
  }
}
```

`builder_id` may still be used by manual workflows or older tooling, but V2 correlation depends on `request_id`.

## Production delivery contract

GamingPlus, Lite, and FrameworkPatcher deliver final archives only through Google Drive. Each workflow verifies the remote object count, exact size, checksum, and approved Drive link before exposing the single short-lived artifact `deadzone-result-<request_id>` to the control bot. A successful workflow without a matching verified contract is not a successful DeadZone delivery.

The ROM workflows validate public HTTPS input before private engine checkout. GamingPlus is pinned to `5b34e25316da9723f36488255a1dcf0ee6f03bf0`, Lite to `4b61c1103f79df3cf59ad13ec9bfc8b6d6cc5931`, the FrameworkPatcher engine to `71ffca6fd8cafea71e19d3181c2da3e8f44c35fb`, and its module template to `64cf3b19eeeba6685185bf11260b2728ad26f9e3`.

Required secret concepts remain backward compatible:

- `PRIVATE_REPO_TOKEN`
- `GAMINGPLUS_ENGINE_REPOSITORY` and `LITE_ENGINE_REPOSITORY`
- `RCLONE_CONFIG_BASE64`, `RCLONE_REMOTE_NAME`, and `RCLONE_UPLOAD_DIR`
- `LITE_RCLONE_UPLOAD_DIR`
- `BUILD_PROGRESS_SECRET`
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID`

Drive paths are immutable and request-scoped. ROM engines use `<upload-root>/<project>/<request-id>/<os>/<codename>/<file.zip>`; FrameworkPatcher uses `<upload-root>/frameworkpatcher/<request-id>/Android<version>/<device>/<file.zip>`. Temporary rclone configuration is created only under `RUNNER_TEMP` with mode `0600` and removed on every terminal path.
