# DeadZone BuildExt

Public GitHub Actions launcher for DeadZone ROM build services.

The build engines and modification sources are maintained in private repositories. This repository contains only the public workflow entry points required to start and monitor builds.

## Architecture

- One public launcher repository
- Multiple private build engines
- Separate workflow entry point for each build type
- Shared secrets for private checkout, notifications, and cloud upload
- Designed to support additional build engines without exposing private source code

## Status

Initial setup in progress.
