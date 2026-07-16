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

