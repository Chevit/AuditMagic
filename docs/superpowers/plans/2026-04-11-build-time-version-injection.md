# Build-time Version Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the manual version-bump step from the release process by having GitHub Actions inject the git tag version into `version.py` at build time.

**Architecture:** Two file changes — `src/version.py` gets a `0.0.0-dev` placeholder, and `.github/workflows/build.yml` gets a PowerShell step (gated on tag triggers) that rewrites the placeholder with the real version before PyInstaller runs. CLAUDE.md release docs are updated to match.

**Tech Stack:** GitHub Actions, PowerShell, PyInstaller

---

## Files Modified

- Modify: `src/version.py` — replace hardcoded version with `0.0.0-dev` placeholder
- Modify: `.github/workflows/build.yml` — add `Inject version from tag` step before `Build executable`
- Modify: `CLAUDE.md` — update Release Process section to remove manual bump steps

---

## Task 1: Set Dev Placeholder in `version.py`

**Files:**
- Modify: `src/version.py`

- [ ] **Step 1: Update the version string**

Replace the current hardcoded version with the dev placeholder. Final file content:

```python
"""Application version. Single source of truth for versioning."""

__version__ = "0.0.0-dev"
__author__ = "Che"
__email__ = "che.audit.magic@gmail.com"
```

- [ ] **Step 2: Verify the app still reads the version correctly**

```bash
.venv/Scripts/python -c "from version import __version__; print(__version__)"
```

Expected output:
```
0.0.0-dev
```

- [ ] **Step 3: Run the test suite to confirm nothing broke**

```bash
set QT_QPA_PLATFORM=offscreen && .venv\Scripts\pytest tests\ -v --tb=short 2>&1 | tail -5
```

Expected:
```
160 passed in ...
```

- [ ] **Step 4: Commit**

```bash
git add src/version.py
git commit -m "chore: set version placeholder for build-time injection"
```

---

## Task 2: Add Injection Step to GitHub Actions + Update Docs

**Files:**
- Modify: `.github/workflows/build.yml:59` — insert step before `Build executable`
- Modify: `CLAUDE.md:371-375` — update Release Process

- [ ] **Step 1: Add the injection step to `build.yml`**

In `.github/workflows/build.yml`, insert the new step between `Install dependencies` (line 53) and `Build executable` (line 59). The final `build-windows` steps section must look exactly like this:

```yaml
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Set up virtual environment
        run: python -m venv .venv

      - name: Install dependencies
        run: |
          .venv\Scripts\python -m pip install --upgrade pip
          .venv\Scripts\pip install -r requirements.txt
          .venv\Scripts\pip install pyinstaller

      - name: Inject version from tag
        if: startsWith(github.ref, 'refs/tags/')
        shell: pwsh
        run: |
          $version = "${{ github.ref_name }}" -replace '^v', ''
          (Get-Content src\version.py) -replace '__version__ = ".*"', "__version__ = `"$version`"" | Set-Content src\version.py

      - name: Build executable
        run: .venv\Scripts\pyinstaller AuditMagic.spec

      - name: Upload Release Asset
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: dist/AuditMagic.exe
          generate_release_notes: true
```

- [ ] **Step 2: Validate the YAML is syntactically correct**

```bash
.venv/Scripts/python -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml')); print('YAML OK')"
```

Expected:
```
YAML OK
```

If `yaml` is not available: `pip install pyyaml` first, or use an online YAML validator.

- [ ] **Step 3: Update the Release Process in `CLAUDE.md`**

Find the `### Release Process` section (around line 370) and replace:

```markdown
### Release Process
1. Update `__version__` in `version.py`
2. Commit: `git commit -am "Bump version to X.Y.Z"`
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push --tags`
5. GitHub Actions builds `.exe` and creates a release automatically
```

With:

```markdown
### Release Process
1. Tag: `git tag vX.Y.Z`
2. Push: `git push && git push --tags`
3. GitHub Actions injects the version from the tag, builds `.exe`, and creates a release automatically

> Note: `version.py` holds a `0.0.0-dev` placeholder in source. The real version is injected by CI at build time — do not manually edit `__version__` before tagging.
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml CLAUDE.md
git commit -m "feat: inject version from git tag at build time

Removes the manual version-bump step from the release process.
version.py holds 0.0.0-dev in source; the build-windows CI job
rewrites it with the tag version before running PyInstaller.
workflow_dispatch runs are unaffected."
```

---

## Success Criteria

- [ ] `python -c "from version import __version__; print(__version__)"` prints `0.0.0-dev`
- [ ] All 160 tests still pass
- [ ] `.github/workflows/build.yml` YAML is valid
- [ ] The `Inject version from tag` step appears between `Install dependencies` and `Build executable` in `build-windows`
- [ ] CLAUDE.md Release Process no longer mentions manually editing `version.py`
