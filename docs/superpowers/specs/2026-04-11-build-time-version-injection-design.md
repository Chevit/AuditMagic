# Build-time Version Injection Design

**Date:** 2026-04-11
**Scope:** Automatically inject the version from the git tag into `version.py` during the GitHub Actions build, removing the need to manually update `version.py` before each release.

---

## Problem

`version.py` currently holds the version as a hardcoded string (`__version__ = "1.0.18"`). The release process requires manually updating this file before tagging, which is error-prone — it's easy to forget or mismatch the tag.

---

## Solution

Option A: build-time injection. `version.py` in source keeps a `"0.0.0-dev"` placeholder. The `build-windows` CI job overwrites the placeholder with the real version extracted from the git tag, immediately before running PyInstaller. Manual `workflow_dispatch` runs are not affected — the placeholder is left unchanged.

---

## Changes

### `src/version.py`

Change the version string to a dev placeholder:

```python
__version__ = "0.0.0-dev"
```

No other changes to this file.

### `.github/workflows/build.yml`

Add one step to the `build-windows` job, positioned **before** the `Build executable` step:

```yaml
- name: Inject version from tag
  if: startsWith(github.ref, 'refs/tags/')
  shell: pwsh
  run: |
    $version = "${{ github.ref_name }}" -replace '^v', ''
    (Get-Content src\version.py) -replace '__version__ = ".*"', "__version__ = `"$version`"" | Set-Content src\version.py
```

**How it works:**
- `github.ref_name` on a `v1.0.19` tag push resolves to `v1.0.19`
- The `-replace '^v', ''` strips the leading `v` → `1.0.19`
- The regex replaces the full `__version__ = "..."` line in `version.py`
- The `if:` condition ensures this only runs on tag-triggered builds, not `workflow_dispatch`

---

## Updated Release Process

Before:
1. Update `__version__` in `version.py`
2. Commit the bump
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push --tags`

After:
1. Tag: `git tag vX.Y.Z`
2. Push: `git push && git push --tags`

Steps 1 and 2 (manual version bump + commit) are eliminated.

---

## Out of Scope

- Changing the `test` job (it doesn't use `__version__`)
- Injecting version on `workflow_dispatch` runs
- Any changes to `update_checker.py` or version display logic
