# DeadZone BuildExt

Public GitHub Actions launcher for DeadZone ROM build services.

The build engines and modification sources are maintained in private repositories. This repository contains only the public workflow entry points required to start and monitor builds.

## Available workflows

- DeadZone GamingPlus Xiaomi Build

## Architecture

- One public launcher repository
- Multiple private build engines
- Separate workflow entry point for each build type
- Private engine checkout using a repository-scoped read-only token
- Shared secrets for notifications and cloud upload
- Designed to support additional build engines without exposing private source code

## Required Actions secrets

- `GAMINGPLUS_ENGINE_REPOSITORY`
- `PRIVATE_REPO_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `RCLONE_CONFIG_BASE64`
- `RCLONE_REMOTE_NAME`
- `RCLONE_UPLOAD_DIR`

## Status

The GamingPlus launcher is configured. Add the required secrets before running the workflow.
