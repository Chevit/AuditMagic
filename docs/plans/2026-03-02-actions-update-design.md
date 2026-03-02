# GitHub Actions Version Update Design

**Date:** 2026-03-02

## Goal

Update all GitHub Actions to their latest stable versions and add pip caching to reduce CI install time.

## Approach

Approach A: bump `actions/checkout` to v6 and `actions/setup-python` to v6 with `cache: 'pip'`. No venv-level caching (YAGNI). `softprops/action-gh-release@v2` is already current.

## Changes

### `actions/checkout`: v4 → v6

All 5 occurrences across both workflow files:
- `.github/workflows/build.yml`: `test` job, `build-windows`, `build-macos`, `build-linux`
- `.github/workflows/test.yml`: `test` job

### `actions/setup-python`: v4 → v6 + `cache: 'pip'`

All 4 occurrences (jobs that use `setup-python`):
- `.github/workflows/build.yml`: `test` job, `build-macos`, `build-linux`
- `.github/workflows/test.yml`: `test` job

Each becomes:
```yaml
- name: Set up Python
  uses: actions/setup-python@v6
  with:
    python-version: '3.11'
    cache: 'pip'
```

### No change

- `build-windows` (self-hosted): no `setup-python`, only `checkout` is updated
- `softprops/action-gh-release@v2`: already on the latest major version
