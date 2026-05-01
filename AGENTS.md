# Repository Instructions

## Scope
This repository contains a `uv`-managed Python check-in automation project.

## Safety
- Do **not** commit `checkin.toml`, `.env*`, secret keys, or cookie values.
- Keep local runtime artifacts out of Git: `.playwright/`, `.hermes/`, `.venv/`, cache directories, and temporary files.
- If you need to show example configuration, update `checkin.example.toml` instead of the live config.

## Project Conventions
- Use `uv run checkin ...` for local execution.
- Keep site-specific logic inside `checkin/sites/`.
- Preserve redaction behavior for cookies and other secrets in logged output.
- When changing config schema or site behavior, update `README.md` and `checkin.example.toml` together.

## Check-in Notes
- NodeSeek currently expects a mobile Safari-style `user_agent`.
- V2EX currently uses the `A2` cookie plus a matching Safari `user_agent`.

## Git Workflow
- Make small, focused commits.
- Before pushing, verify `git status` contains only intended tracked files.
