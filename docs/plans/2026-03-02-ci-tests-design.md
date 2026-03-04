# CI Test Gate Design

**Date:** 2026-03-02

## Goal

Run `pytest` on every push and pull request, and enforce it as a mandatory first step before any release build.

## Approach

Approach A: dedicated `test.yml` for CI + `test` job added to `build.yml`.

- `test.yml` catches regressions on every push and PR to any branch.
- `build.yml` adds the same `test` job so release builds cannot proceed if tests fail.

## New file: `.github/workflows/test.yml`

- **Triggers:** `push` and `pull_request` on all branches
- **Runner:** `ubuntu-latest`, Python 3.14
- **Steps:** checkout → setup-python → `pip install -r requirements-dev.txt` → `pytest tests/ -v`
- **Environment:** `QT_QPA_PLATFORM=offscreen` (prevents Qt from crashing on headless Linux)

## Changes to `.github/workflows/build.yml`

- Add a new `test` job (identical setup to `test.yml`) running on `ubuntu-latest`
- Add `needs: [test]` to `build-windows`, `build-macos`, and `build-linux`
- No trigger changes — build still only fires on `v*` tags and `workflow_dispatch`

## What does NOT change

- The self-hosted `build-windows` job is not used for testing; `ubuntu-latest` is used for the gate
- No test result artifacts or coverage reports (YAGNI)
- No branch protection rules (out of scope — handled in GitHub repo settings)
